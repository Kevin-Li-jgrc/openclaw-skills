from __future__ import annotations

import re
from typing import Any

from rules_structure import result
from rules_review_semantics import active_code, manual_result


BUILTIN_VALUE_OBJECTS = {"SerialNumber"}
LOCAL_VARIABLE_DECLARATION = re.compile(
    r"^\s*(?:Dim|Static)\s+"
    r"(?P<names>[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)"
    r"\s+As\s+[A-Za-z_][A-Za-z0-9_.]*(?:\([^\r\n]*\))?",
    re.IGNORECASE | re.MULTILINE,
)
PUBLIC_VARIABLE_DECLARATION = re.compile(
    r"^\s*Public\s+(?:Shared\s+)?(?:Dim\s+)?"
    r"(?P<names>[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)"
    r"\s+As\s+[A-Za-z_][A-Za-z0-9_.]*(?:\([^\r\n]*\))?",
    re.IGNORECASE | re.MULTILINE,
)
DYNAMIC_BINDING = re.compile(
    r"\b(?:CallByName|CreateObject|FindObject|GetObject)\b|"
    r"\b(?:Controls|Items)\s*\(",
    re.IGNORECASE,
)


def probe_maps(facts: dict[str, Any]) -> tuple[dict[str, int], set[int]]:
    by_name: dict[str, int] = {}
    ids: set[int] = set()
    for probe in facts.get("probes", []):
        if isinstance(probe.get("name"), str) and isinstance(probe.get("id"), int):
            by_name[probe["name"]] = probe["id"]
            ids.add(probe["id"])
    return by_name, ids


def declared_names(code: str, pattern: re.Pattern[str]) -> set[str]:
    names: set[str] = set()
    for match in pattern.finditer(str(code or "")):
        names.update(name.strip().casefold() for name in match.group("names").split(","))
    return names


def check_probe_name_id_unique(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    names: set[str] = set()
    ids: set[int] = set()
    evidence: list[dict[str, Any]] = []
    for probe in facts.get("probes", []):
        name, probe_id = probe.get("name"), probe.get("id")
        if name in names or probe_id in ids or not name or probe_id is None:
            evidence.append({"object": name, "id": probe_id})
        names.add(name)
        ids.add(probe_id)
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_measurement_probe_exists(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    probe_by_name, _ = probe_maps(facts)
    known_names = {
        str(item.get("name") or "").casefold()
        for section in (
            "operations",
            "parts",
            "measurements",
            "master_sets",
            "tags",
            "features",
            "io_objects",
        )
        for item in facts.get(section, [])
        if str(item.get("name") or "").strip()
    }
    known_names.update(name.casefold() for name in BUILTIN_VALUE_OBJECTS)
    global_code = "\n".join(
        (
            str(facts.get("code_module", {}).get("code") or ""),
            str(facts.get("probe_code") or ""),
        )
    )
    public_variables = declared_names(global_code, PUBLIC_VARIABLE_DECLARATION)
    known_references = {
        *(str(item).casefold() for item in probe_by_name),
        *known_names,
        *public_variables,
    }
    evidence: list[dict[str, Any]] = []
    for measurement in facts.get("measurements", []):
        local_variables = declared_names(
            str(measurement.get("equation") or ""), LOCAL_VARIABLE_DECLARATION
        )
        missing = [
            name
            for name in measurement.get("equation_sources", [])
            if str(name).casefold() not in known_references | local_variables
        ]
        if missing:
            evidence.append(
                {
                    "object": measurement.get("name"),
                    "unresolved_reference_names": missing,
                    "reason": "reference_is_not_probe_or_declared_custom_variable",
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_bound_probe_ids_exist(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    _, known_ids = probe_maps(facts)
    evidence: list[dict[str, Any]] = []
    for measurement in facts.get("measurements", []):
        missing = sorted(set(measurement.get("bound_probe_ids", [])) - known_ids)
        if missing:
            evidence.append({"object": measurement.get("name"), "missing_probe_ids": missing})
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_measurement_probe_binding(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    probe_by_name, _ = probe_maps(facts)
    evidence: list[dict[str, Any]] = []
    for measurement in facts.get("measurements", []):
        expected = {
            probe_by_name[name]
            for name in measurement.get("equation_sources", [])
            if name in probe_by_name
        }
        actual = set(measurement.get("bound_probe_ids", []))
        if expected and actual != expected:
            evidence.append(
                {
                    "object": measurement.get("name"),
                    "expected_probe_ids": sorted(expected),
                    "actual_probe_ids": sorted(actual),
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_binding_ambiguity(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    for measurement in facts.get("measurements", []):
        equation = str(measurement.get("equation") or "")
        if DYNAMIC_BINDING.search(active_code(equation)):
            return manual_result(
                rule,
                object_name=str(measurement.get("name") or "Measurement"),
                file="VGA.xml",
                reason="dynamic_or_indirect_object_lookup",
                missing_evidence="运行时动态对象名称及最终绑定的 Probe",
                manual_action="在 VGAGE 中触发该 Measurement，并核对运行时实际读取对象与绑定 Probe",
                probe_sources=sorted(set(measurement.get("equation_sources", [])), key=str.casefold),
                bound_probe_ids=measurement.get("bound_probe_ids", []),
            )
    return result(rule, "PASS", [])
