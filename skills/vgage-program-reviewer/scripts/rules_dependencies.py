from __future__ import annotations

from typing import Any

from rules_binding import probe_maps
from rules_structure import is_offline_gage, result


BUILTIN_OBJECTS = {
    "cbool",
    "cbyte",
    "cchar",
    "cdate",
    "cdbl",
    "cdec",
    "cint",
    "clng",
    "cobj",
    "csbyte",
    "cshort",
    "csng",
    "cstr",
    "cuint",
    "culng",
    "cushort",
    "convert",
    "datetime",
    "io",
    "math",
    "me",
    "mybase",
    "now",
    "outputwindow",
    "system",
    "vga",
}


def injected_object_names(facts: dict[str, Any]) -> set[str]:
    names = set(BUILTIN_OBJECTS)
    names.update(
        str(name).casefold()
        for name in facts.get("probe_code_functions", [])
        if str(name).strip()
    )
    for section in (
        "operations",
        "parts",
        "measurements",
        "probes",
        "master_sets",
        "features",
        "tags",
        "io_objects",
    ):
        names.update(
            str(item.get("name") or "").casefold()
            for item in facts.get(section, [])
            if str(item.get("name") or "").strip()
        )
    return names


def check_probe_equation_objects(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    known = injected_object_names(facts)
    evidence: list[dict[str, Any]] = []
    for probe in facts.get("probes", []):
        missing = sorted(
            {
                str(name)
                for name in probe.get("object_sources", probe.get("equation_sources", []))
                if str(name).casefold() not in known
            },
            key=str.casefold,
        )
        if missing:
            evidence.append(
                {
                    "object": probe.get("name"),
                    "missing_objects": missing,
                    "equation": probe.get("equation"),
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def computed_probe_expectations(facts: dict[str, Any]) -> list[tuple[dict[str, Any], set[int]]]:
    by_name, _ = probe_maps(facts)
    return [
        (
            probe,
            {by_name[name] for name in probe.get("equation_sources", []) if name in by_name},
        )
        for probe in facts.get("probes", [])
    ]


def check_direct_probe_dependencies(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    evidence = [
        {"object": probe.get("name"), "actual_dependency_ids": probe.get("dependency_ids", [])}
        for probe, expected in computed_probe_expectations(facts)
        if not expected and probe.get("dependency_ids")
    ]
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_computed_probe_dependencies(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    for probe, expected in computed_probe_expectations(facts):
        actual = set(probe.get("dependency_ids", []))
        missing = expected - actual
        if expected and missing:
            evidence.append({"object": probe.get("name"), "missing_dependency_ids": sorted(missing)})
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_no_extra_probe_dependencies(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    for probe, expected in computed_probe_expectations(facts):
        raw = probe.get("dependency_ids", [])
        actual = set(raw)
        extra = actual - expected
        if expected and (extra or len(raw) != len(actual)):
            evidence.append(
                {
                    "object": probe.get("name"),
                    "extra_dependency_ids": sorted(extra),
                    "duplicate_ids": len(raw) != len(actual),
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_probe_dependency_cycles(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    by_id = {probe.get("id"): probe for probe in facts.get("probes", [])}
    graph = {probe_id: set(probe.get("dependency_ids", [])) & set(by_id) for probe_id, probe in by_id.items()}
    evidence: list[dict[str, Any]] = []

    def visit(node: int, path: list[int]) -> None:
        if node in path:
            cycle = path[path.index(node):] + [node]
            if {"cycle_ids": cycle} not in evidence:
                evidence.append({"cycle_ids": cycle})
            return
        for child in graph.get(node, set()):
            visit(child, path + [node])

    for node in graph:
        visit(node, [])
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def measurement_expectations(facts: dict[str, Any]) -> list[tuple[dict[str, Any], set[int]]]:
    by_name = {
        measurement.get("name"): measurement.get("id")
        for measurement in facts.get("measurements", [])
        if measurement.get("name") and isinstance(measurement.get("id"), int)
    }
    return [
        (
            measurement,
            {by_name[name] for name in measurement.get("equation_sources", []) if name in by_name},
        )
        for measurement in facts.get("measurements", [])
    ]


def check_measurement_dependencies(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    for measurement, expected in measurement_expectations(facts):
        actual = set(measurement.get("dependency_ids", []))
        if expected != actual:
            evidence.append(
                {
                    "object": measurement.get("name"),
                    "expected_dependency_ids": sorted(expected),
                    "actual_dependency_ids": sorted(actual),
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_summary_measurement_rtg0(facts: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
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
    evidence = [
        {"object": measurement.get("name"), "ready_to_gage": measurement.get("ready_to_gage")}
        for measurement, expected in measurement_expectations(facts)
        if expected and measurement.get("ready_to_gage") != 0
    ]
    return result(rule, "FAIL" if evidence else "PASS", evidence)
