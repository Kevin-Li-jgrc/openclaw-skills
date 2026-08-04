from __future__ import annotations

import math
import re
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HANDLE_TARGET = re.compile(
    r"\bHandles\s+([A-Za-z_][A-Za-z0-9_]*)\.[A-Za-z_][A-Za-z0-9_]*",
    re.IGNORECASE,
)
CONTROL_PROPERTY_TARGET = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\."
    r"(?:Visible|Text|BackColor|ForeColor|Enabled|Checked|SelectedIndex|Value)\b",
    re.IGNORECASE,
)
LOCAL_NAME = re.compile(r"\b(?:ByVal|ByRef|Dim|Const)\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)


def gage_type(facts: dict[str, Any]) -> str:
    return str(facts.get("vga", {}).get("GageType") or "").strip().casefold()


def is_offline_gage(facts: dict[str, Any]) -> bool:
    return gage_type(facts) == "offline"


def result(
    rule: dict[str, Any],
    status: str,
    evidence: list[dict[str, Any]],
    exception_reason: str | None = None,
) -> dict[str, Any]:
    item = {
        "rule_id": rule["rule_id"],
        "status": status,
        "severity": rule["severity"],
        "title": rule["title"],
        "sources": rule["sources"],
        "evidence": evidence,
        "impact": rule["fail_condition"] if status == "FAIL" else "",
        "recommendation": "按规则证据修正副本并重新检查" if status == "FAIL" else "",
    }
    if exception_reason:
        item["exception_reason"] = exception_reason
    return item


def check_project_parse(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    evidence = [
        {
            "file": item.get("relative_path"),
            "message": item.get("message"),
        }
        for item in facts.get("parse_errors", [])
    ]
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_project_structure(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    required = {"vga.xml", "io.xml", "codemodule.vgs"}
    names = {
        str(item.get("relative_path") or "").rsplit("/", 1)[-1].casefold()
        for item in facts.get("files", [])
    }
    missing = sorted(required - names)
    parse_errors = facts.get("parse_errors", [])
    if missing or parse_errors:
        evidence = []
        if missing:
            evidence.append({"missing_required_files": missing})
        evidence.extend(
            {"file": item.get("relative_path"), "message": item.get("message")}
            for item in parse_errors
        )
        return result(rule, "FAIL", evidence)

    recognized = {
        key: len(facts.get(key, []))
        for key in ("parts", "measurements", "probes", "features", "tags", "io_points")
    }
    return result(
        rule,
        "PASS",
        [{"required_files": sorted(required), "recognized_objects": recognized}],
    )


def active(item: dict[str, Any]) -> bool:
    return str(item.get("raw_attributes", {}).get("Active", "True")).casefold() != "false"


def finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def check_measurement_runtime_fields(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    non_numeric_types = {"datetime", "date", "time", "string", "text", "boolean"}
    evidence: list[dict[str, Any]] = []
    for measurement in facts.get("measurements", []):
        if not active(measurement):
            continue
        if str(measurement.get("type") or "").casefold() in non_numeric_types:
            continue

        name = measurement.get("name")
        if not str(measurement.get("equation") or "").strip():
            evidence.append({"object": name, "field": "Equation", "reason": "missing"})

        attributes = measurement.get("raw_attributes", {})
        usl_raw = attributes.get("USL")
        lsl_raw = attributes.get("LSL")
        has_usl = str(usl_raw or "").strip() != ""
        has_lsl = str(lsl_raw or "").strip() != ""
        if has_usl != has_lsl:
            evidence.append(
                {"object": name, "fields": ["USL", "LSL"], "reason": "not_configured_as_pair"}
            )
        elif has_usl and has_lsl:
            usl = finite_number(usl_raw)
            lsl = finite_number(lsl_raw)
            if usl is None or lsl is None:
                evidence.append(
                    {
                        "object": name,
                        "USL": usl_raw,
                        "LSL": lsl_raw,
                        "reason": "not_finite_numbers",
                    }
                )
            elif usl < lsl:
                evidence.append(
                    {"object": name, "USL": usl, "LSL": lsl, "reason": "USL_less_than_LSL"}
                )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_probe_runtime_fields(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    evidence: list[dict[str, Any]] = []
    for probe in facts.get("probes", []):
        if not active(probe):
            continue
        missing = []
        if not isinstance(probe.get("id"), int):
            missing.append("Id")
        if not str(probe.get("name") or "").strip():
            missing.append("Name")
        if not str(probe.get("type") or "").strip():
            missing.append("Type")
        if not str(probe.get("equation") or "").strip():
            missing.append("Equation")
        if missing:
            evidence.append({"object": probe.get("name"), "missing_fields": missing})
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_form_references(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    evidence: list[dict[str, Any]] = []

    form_files = {
        str(form.get("relative_path") or "").rsplit("/", 1)[-1][:-4].casefold()
        for form in facts.get("forms", [])
        if str(form.get("relative_path") or "").casefold().endswith(".xml")
    }
    for declared_form in facts.get("screens", []):
        if str(declared_form).casefold() not in form_files:
            evidence.append(
                {
                    "file": "Screens.xml",
                    "object": declared_form,
                    "reason": "declared_form_file_missing",
                }
            )

    global_names = {"vga", "me", "mybase"}
    for collection in (
        "operations",
        "parts",
        "measurements",
        "probes",
        "master_sets",
        "features",
        "tags",
    ):
        global_names.update(
            str(item.get("name") or "").casefold()
            for item in facts.get(collection, [])
            if str(item.get("name") or "").strip()
        )

    for form in facts.get("forms", []):
        relative_path = form.get("relative_path")
        objects = form.get("objects", [])
        object_names: set[str] = set()
        for item in objects:
            name = str(item.get("name") or "").strip()
            serialized_name = str(item.get("serialized_name") or "").strip()
            folded = name.casefold()
            if not IDENTIFIER.fullmatch(name):
                evidence.append(
                    {"file": relative_path, "object": name, "reason": "invalid_object_name"}
                )
            if folded in object_names:
                evidence.append(
                    {"file": relative_path, "object": name, "reason": "duplicate_object_name"}
                )
            object_names.add(folded)
            if serialized_name and serialized_name.casefold() != folded:
                evidence.append(
                    {
                        "file": relative_path,
                        "object": name,
                        "serialized_name": serialized_name,
                        "reason": "serialized_name_mismatch",
                    }
                )

        code = str(form.get("code") or "")
        allowed_names = object_names | global_names | {
            match.casefold() for match in LOCAL_NAME.findall(code)
        }
        for target in sorted(set(HANDLE_TARGET.findall(code)), key=str.casefold):
            if target.casefold() not in allowed_names:
                evidence.append(
                    {
                        "file": relative_path,
                        "object": target,
                        "reason": "dangling_event_target",
                    }
                )
        handled_targets = {target.casefold() for target in HANDLE_TARGET.findall(code)}
        for target in sorted(set(CONTROL_PROPERTY_TARGET.findall(code)), key=str.casefold):
            folded = target.casefold()
            if folded not in allowed_names and folded not in handled_targets:
                evidence.append(
                    {
                        "file": relative_path,
                        "object": target,
                        "reason": "dangling_control_reference",
                    }
                )

    return result(rule, "FAIL" if evidence else "PASS", evidence)
