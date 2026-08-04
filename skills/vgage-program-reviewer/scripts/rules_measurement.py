from __future__ import annotations

import re
from typing import Any

from rules_structure import is_offline_gage, result


RETURN_ZERO = re.compile(r"^\s*Return\s+0(?:\.0+)?\s*$", re.IGNORECASE | re.MULTILINE)
FUNCTION_BOUNDARY = re.compile(
    r"^\s*(?:(?:Public|Private|Protected|Friend|Shared)\s+)*(?:Function|Sub)\b|"
    r"^\s*End\s+(?:Function|Sub)\s*$",
    re.IGNORECASE,
)
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FEATURE_TYPES = {
    "point",
    "circle",
    "bestfitcircle",
    "plane",
    "bestfitplane",
    "sphere",
    "bestfitsphere",
    "bestfitsphere2",
    "line",
    "bestfitline",
    "cylinder",
    "bestfitcylinder",
}
VB_KEYWORDS = {
    "and", "as", "boolean", "byref", "byval", "class", "const", "date", "dim",
    "double", "else", "end", "false", "for", "function", "if", "integer", "loop",
    "me", "module", "namespace", "new", "next", "not", "nothing", "object", "or",
    "private", "public", "return", "select", "shared", "string", "sub", "then", "true",
    "while",
}


def active(item: dict[str, Any]) -> bool:
    return str(item.get("raw_attributes", {}).get("Active", "True")).lower() != "false"


def deterministic_direct_zero(equation: str) -> bool:
    executable_lines: list[str] = []
    for raw_line in str(equation or "").splitlines():
        line = raw_line.split("'", 1)[0].strip()
        if not line or FUNCTION_BOUNDARY.search(line):
            continue
        executable_lines.append(line)
    return len(executable_lines) == 1 and RETURN_ZERO.fullmatch(executable_lines[0]) is not None


def contains_return_zero(equation: str) -> bool:
    return any(
        RETURN_ZERO.fullmatch(raw_line.split("'", 1)[0].strip()) is not None
        for raw_line in str(equation or "").splitlines()
    )


def dynamic_imbus_exemption(probe: dict[str, Any], facts: dict[str, Any]) -> bool:
    modules = {
        str(item.get("module_name") or "").casefold(): item
        for item in facts.get("imbus_modules", [])
        if str(item.get("module_name") or "").strip()
    }
    referenced = [
        modules[str(name).casefold()]
        for name in probe.get("object_sources", [])
        if str(name).casefold() in modules
    ]
    return bool(referenced) and all(item.get("dynamic_being_used") is True for item in referenced)


def dimensional(probe: dict[str, Any]) -> bool | None:
    probe_type = str(probe.get("type") or "").lower()
    symbol = str(probe.get("symbol") or "").lower()
    if "angle" in probe_type or "temperature" in probe_type or symbol in {"angle", "temperature"}:
        return False
    if "distance" in probe_type or symbol in {
        "distance", "diameter", "radius", "length", "height", "width", "centerpoint"
    }:
        return True
    return None


def check_dynamic_data_cycles(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    evidence = []
    for probe in facts.get("probes", []):
        if probe.get("save_dynamic_data") is not True:
            continue
        cycles = probe.get("number_of_cycles_to_save")
        if not isinstance(cycles, int) or cycles > 50 or cycles < 0:
            evidence.append({"object": probe.get("name"), "number_of_cycles_to_save": cycles})
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_dimensional_digits(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    evidence = [
        {"object": probe.get("name"), "digits": probe.get("digits")}
        for probe in facts.get("probes", [])
        if active(probe) and dimensional(probe) is True and probe.get("digits") != 4
    ]
    unknown = [probe.get("name") for probe in facts.get("probes", []) if active(probe) and dimensional(probe) is None]
    if evidence:
        return result(rule, "FAIL", evidence)
    if unknown:
        return result(rule, "MANUAL_VERIFY", [{"objects": unknown, "reason": "Probe measurement meaning is ambiguous"}])
    return result(rule, "PASS", [])


def check_probe_return_zero(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    exceptions = context.get("rule_exceptions", {})
    evidence = [
        {
            "object": probe.get("name"),
            "equation": probe.get("equation"),
            "reason": "deterministic_direct_return_zero",
        }
        for probe in facts.get("probes", [])
        if active(probe)
        and not dynamic_imbus_exemption(probe, facts)
        and deterministic_direct_zero(str(probe.get("equation") or ""))
    ]
    if evidence and rule["rule_id"] not in exceptions:
        return result(rule, "FAIL", evidence)
    return result(rule, "PASS", evidence if evidence else [])


def check_measurement_return_zero(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    exceptions = context.get("rule_exceptions", {})
    evidence = []
    for measurement in facts.get("measurements", []):
        if not active(measurement):
            continue
        measurement_type = str(measurement.get("type") or "").strip().casefold()
        equation = str(measurement.get("equation") or "")
        invalid = (
            measurement_type == "double" and contains_return_zero(equation)
        ) or (
            measurement_type == "integer" and deterministic_direct_zero(equation)
        )
        if invalid:
            evidence.append(
                {
                    "object": measurement.get("name"),
                    "measurement_type": measurement.get("type"),
                    "equation": equation,
                    "reason": (
                        "double_measurement_contains_return_zero"
                        if measurement_type == "double"
                        else "integer_measurement_direct_return_zero"
                    ),
                }
            )
    if evidence and rule["rule_id"] not in exceptions:
        return result(rule, "FAIL", evidence)
    return result(rule, "PASS", evidence if evidence else [])


def check_evaluate_when_selected(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if is_offline_gage(facts):
        return result(
            rule,
            "PASS",
            [{
                "file": "VGA.xml",
                "gage_type": facts.get("vga", {}).get("GageType"),
                "reason": "offline_gage_exemption",
            }],
        )
    evidence = []
    evaluate_exempt_types = {"datetime", "date", "time"}
    for measurement in facts.get("measurements", []):
        if not active(measurement):
            continue
        if str(measurement.get("type") or "").strip().casefold() in evaluate_exempt_types:
            continue
        effective = measurement.get("effective_evaluate_when_selected")
        if effective is None:
            raw = measurement.get("evaluate_when_selected")
            effective = True if raw is None else raw
        if effective is True:
            evidence.append({
                "file": "VGA.xml",
                "object": measurement.get("name"),
                "raw_value": measurement.get("raw_attributes", {}).get("EvaluateWhenSelected"),
                "effective_evaluate_when_selected": True,
            })
    exception = context.get("rule_exceptions", {}).get(rule["rule_id"])
    if evidence and not str(exception or "").strip():
        return result(rule, "FAIL", evidence)
    return result(rule, "PASS", evidence if evidence else [])


def check_measurement_operation(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    operation_exempt_types = {"datetime", "date", "time", "string", "text", "boolean"}
    known_operation_ids = {
        operation.get("id") for operation in facts.get("operations", [])
        if isinstance(operation.get("id"), int)
    }
    evidence = [
        {
            "object": measurement.get("name"),
            "operation": measurement.get("operation"),
            "operation_id": measurement.get("operation_id"),
        }
        for measurement in facts.get("measurements", [])
        if active(measurement)
        and str(measurement.get("type") or "").casefold() not in operation_exempt_types
        and not str(measurement.get("operation") or "").strip()
        and (
            not isinstance(measurement.get("operation_id"), int)
            or (
                bool(known_operation_ids)
                and measurement.get("operation_id") not in known_operation_ids
            )
        )
    ]
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_masterset_text(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    evidence = [
        {"file": "VGA.xml", "object": master.get("name"), "missing_fields": ["Text"]}
        for master in facts.get("master_sets", [])
        if not str(master.get("text") or "").strip()
    ]
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_feature_names(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    evidence = [
        {"object": feature.get("name")}
        for feature in facts.get("features", [])
        if re.fullmatch(r"(?:Feature|Circle|Point|Line|Plane|Sphere)\d*", str(feature.get("name") or ""), re.I)
    ]
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_feature_types(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    evidence = [
        {
            "object": feature.get("name"),
            "feature_type": feature.get("type"),
            "reason": "vector_is_not_persistable" if str(feature.get("type") or "").casefold() == "vector" else "unknown_feature_type",
        }
        for feature in facts.get("features", [])
        if str(feature.get("type") or "").casefold() not in FEATURE_TYPES
    ]
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_feature_global_names(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    other_names: dict[str, list[dict[str, str]]] = {}
    for section in (
        "operations",
        "parts",
        "measurements",
        "probes",
        "master_sets",
        "tags",
        "io_objects",
    ):
        for item in facts.get(section, []):
            name = str(item.get("name") or "").strip()
            if name:
                other_names.setdefault(name.casefold(), []).append({"section": section, "name": name})

    feature_counts: dict[str, int] = {}
    for feature in facts.get("features", []):
        name = str(feature.get("name") or "").strip()
        feature_counts[name.casefold()] = feature_counts.get(name.casefold(), 0) + 1

    evidence: list[dict[str, Any]] = []
    for feature in facts.get("features", []):
        name = str(feature.get("name") or "").strip()
        folded = name.casefold()
        if not IDENTIFIER.fullmatch(name) or folded in VB_KEYWORDS:
            evidence.append({"object": name, "reason": "invalid_script_identifier"})
        collisions = other_names.get(folded, [])
        if feature_counts.get(folded, 0) > 1:
            collisions = collisions + [{"section": "features", "name": name}]
        if collisions:
            evidence.append(
                {"object": name, "reason": "global_name_collision", "collisions": collisions}
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)
