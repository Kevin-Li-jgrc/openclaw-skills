from __future__ import annotations

import ipaddress
import re
from typing import Any

from rules_structure import result


CJK = re.compile(r"[\u3400-\u9fff]")
ENGLISH = re.compile(r"[A-Za-z]")
CHANNEL_SENSOR = re.compile(r"^\s*\d+\s*\[([A-Za-z_][A-Za-z0-9_]*)\]\s*$")
CHANNEL_MAPPING = re.compile(r"^\s*(\d+)\s*\[([A-Za-z_][A-Za-z0-9_]*)\]\s*$")
COM_PORT = re.compile(r"\bCOM\s*\d+\b", re.I)
USB_MARKER = re.compile(r"(?<![A-Za-z])USB(?![A-Za-z])", re.I)
IPV4_CANDIDATE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
IMBUS_DISTANCE_MODULE = re.compile(r"^IMB_im(?:1|2|4|8)$", re.I)


def has_tag(value: Any) -> bool:
    return str(value or "").strip().lower() not in {"", "(none)", "none"}


def has_imbus_connection_marker(value: Any) -> bool:
    text = str(value or "")
    if COM_PORT.search(text) or USB_MARKER.search(text):
        return True
    for candidate in IPV4_CANDIDATE.findall(text):
        try:
            ipaddress.ip_address(candidate)
            return True
        except ValueError:
            continue
    return False


def check_io_comment_tag_symmetry(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    region = context.get("project_region", "unknown")
    evidence = []
    for index, point in enumerate(facts.get("io_points", [])):
        comment = str(point.get("description") or "").strip()
        tag_present = has_tag(point.get("vga_tag"))
        mismatch = bool(comment) != tag_present
        invalid_overseas = region == "overseas" and bool(comment) and (CJK.search(comment) or not ENGLISH.search(comment))
        if mismatch or invalid_overseas:
            evidence.append(
                {
                    "object": f"IO point {index}",
                    "description": comment,
                    "vga_tag": point.get("vga_tag"),
                    "reason": "comment/tag mismatch" if mismatch else "overseas comment is not English",
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_imbus_text_and_channels(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    evidence = []
    for index, point in enumerate(facts.get("io_points", [])):
        is_imbus = "imb" in str(point.get("module_type") or "").lower() or "imbus" in str(point.get("bus_name") or "").lower()
        if not is_imbus:
            continue
        bus_marker_valid = has_imbus_connection_marker(point.get("bus_text"))
        channel_text_valid = CHANNEL_SENSOR.fullmatch(str(point.get("text") or "")) is not None
        if not bus_marker_valid or not channel_text_valid:
            evidence.append(
                {
                    "object": f"IO point {index}",
                    "bus_text": point.get("bus_text"),
                    "text": point.get("text"),
                    "reason": (
                        "missing_imbus_connection_marker"
                        if not bus_marker_valid
                        else "invalid_channel_sensor_text"
                    ),
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_orbit_probe_names(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    probe_names = {probe.get("name") for probe in facts.get("probes", [])}
    evidence = []
    for index, point in enumerate(facts.get("io_points", [])):
        is_orbit = "orbit" in " ".join(
            str(point.get(key) or "").lower() for key in ("bus_name", "module_name", "module_type")
        )
        if not is_orbit:
            continue
        match = CHANNEL_SENSOR.fullmatch(str(point.get("text") or ""))
        if match is None or match.group(1) not in probe_names:
            evidence.append({"object": f"Orbit point {index}", "text": point.get("text")})
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_tag_semantics(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    region = context.get("project_region", "unknown")
    evidence = []
    for tag in facts.get("tags", []):
        name = str(tag.get("name") or "").strip()
        description = str(tag.get("description") or "").strip()
        generic = not name or re.fullmatch(r"Tag\d*", name, re.I) is not None
        missing_domestic_chinese = region == "domestic" and not CJK.search(description)
        if generic or missing_domestic_chinese:
            evidence.append({"object": name, "description": description})
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def imbus_distance_points(facts: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        point
        for point in facts.get("io_points", [])
        if IMBUS_DISTANCE_MODULE.fullmatch(str(point.get("module_type") or ""))
    ]


def no_imbus_distance_module(facts: dict[str, Any]) -> bool:
    return not any(
        IMBUS_DISTANCE_MODULE.fullmatch(str(item.get("type") or ""))
        for item in facts.get("io_objects", [])
    ) and not imbus_distance_points(facts)


def check_imbus_probe_mapping(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    if no_imbus_distance_module(facts):
        return result(rule, "PASS", [{"reason": "no_imbus_distance_module"}])

    probe_names = {
        str(probe.get("name") or "").casefold()
        for probe in facts.get("probes", [])
        if str(probe.get("name") or "").strip()
    }
    evidence: list[dict[str, Any]] = []
    occupied: set[tuple[str, int]] = set()
    mapped_probes: set[str] = set()
    for point in imbus_distance_points(facts):
        text = str(point.get("text") or "").strip()
        if not text or text.casefold() == "empty":
            continue
        match = CHANNEL_MAPPING.fullmatch(text)
        base = {
            "module": point.get("module_name"),
            "channel_index": point.get("channel_index"),
            "text": text,
        }
        if match is None:
            evidence.append({**base, "reason": "invalid_channel_probe_text"})
            continue
        channel = int(match.group(1))
        probe_name = match.group(2)
        key = (str(point.get("module_name") or "").casefold(), channel)
        if channel != point.get("channel_index"):
            evidence.append({**base, "parsed_channel": channel, "reason": "channel_index_mismatch"})
        capacity = point.get("module_capacity")
        if not isinstance(capacity, int) or not 0 <= channel < capacity:
            evidence.append({**base, "parsed_channel": channel, "capacity": capacity, "reason": "channel_out_of_range"})
        if probe_name.casefold() not in probe_names:
            evidence.append({**base, "probe": probe_name, "reason": "probe_not_found"})
        if key in occupied:
            evidence.append({**base, "reason": "duplicate_module_channel"})
        occupied.add(key)
        if probe_name.casefold() in mapped_probes:
            evidence.append({**base, "probe": probe_name, "reason": "probe_mapped_more_than_once"})
        mapped_probes.add(probe_name.casefold())
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_imbus_probe_equations(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    if no_imbus_distance_module(facts):
        return result(rule, "PASS", [{"reason": "no_imbus_distance_module"}])

    probes = {
        str(probe.get("name") or "").casefold(): probe
        for probe in facts.get("probes", [])
        if str(probe.get("name") or "").strip()
    }
    evidence: list[dict[str, Any]] = []
    for point in imbus_distance_points(facts):
        text = str(point.get("text") or "").strip()
        match = CHANNEL_MAPPING.fullmatch(text)
        if match is None:
            continue
        channel = int(match.group(1))
        probe_name = match.group(2)
        probe = probes.get(probe_name.casefold())
        if probe is None:
            continue
        expected = f"Return {point.get('module_name')}({channel}).Value"
        equation = str(probe.get("equation") or "")
        access = re.search(
            rf"\b{re.escape(str(point.get('module_name') or ''))}\s*\(\s*{channel}\s*\)\.Value\b",
            equation,
            re.I,
        )
        combined = re.fullmatch(r"p\d+[nc]\d+", probe_name, re.I) is not None
        if access is None or combined:
            evidence.append(
                {
                    "object": probe_name,
                    "module": point.get("module_name"),
                    "channel": channel,
                    "equation": equation,
                    "expected_equation": expected,
                    "reason": "combined_probe_occupies_channel" if combined else "probe_equation_mapping_mismatch",
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)
