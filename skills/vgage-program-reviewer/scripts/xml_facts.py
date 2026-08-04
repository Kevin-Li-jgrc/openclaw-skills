from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


OBJECT_VALUE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.(?:Value|Average)\b")
OBJECT_MEMBER = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^()\r\n]*\))?\."
    r"[A-Za-z_][A-Za-z0-9_]*\b"
)
CALLABLE_DECLARATION = re.compile(
    r"^\s*(?:Public\s+|Private\s+|Protected\s+|Friend\s+|Shared\s+)*"
    r"(?:Function|Sub)\s+([A-Za-z_][A-Za-z0-9_]*)\b",
    re.IGNORECASE | re.MULTILINE,
)
IMBUS_CAPACITY = re.compile(r"^IMB_im(1|2|4|8)$", re.IGNORECASE)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def integer(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def number(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def boolean(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def child_ids(element: ET.Element, child_name: str) -> list[int]:
    for child in element:
        if local_name(child.tag) != child_name:
            continue
        values: list[int] = []
        for item in child:
            if local_name(item.tag) == "Id" and integer(item.text) is not None:
                values.append(int(item.text))
        return values
    return []


def parse_xml(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def parse_vga(root: ET.Element) -> dict[str, Any]:
    result: dict[str, Any] = {
        "vga": dict(root.attrib),
        "operations": [],
        "parts": [],
        "measurements": [],
        "probes": [],
        "probe_code": "",
        "probe_code_functions": [],
        "master_sets": [],
        "features": [],
        "tags": [],
        "auto_archive": {
            "network_folder": root.attrib.get("NetworkFolder", root.attrib.get("Network folder")),
            "raw_attributes": dict(root.attrib),
        },
    }

    for section in root:
        section_name = local_name(section.tag)
        if section_name == "Operations":
            for operation in section:
                result["operations"].append(
                    {
                        "id": integer(operation.attrib.get("Id")),
                        "name": operation.attrib.get("Name", local_name(operation.tag)),
                        "raw_attributes": dict(operation.attrib),
                    }
                )
        elif section_name == "Probes":
            result["probe_code"] = str(section.attrib.get("Code") or "")
            result["probe_code_functions"] = sorted(
                set(CALLABLE_DECLARATION.findall(result["probe_code"])),
                key=str.casefold,
            )
            for probe in section:
                equation = probe.attrib.get("Equation", "")
                result["probes"].append(
                    {
                        "id": integer(probe.attrib.get("Id")),
                        "name": probe.attrib.get("Name", local_name(probe.tag)),
                        "text": probe.attrib.get("Text"),
                        "type": probe.attrib.get("Type", local_name(probe.tag)),
                        "equation": equation,
                        "equation_sources": OBJECT_VALUE.findall(equation),
                        "object_sources": sorted(set(OBJECT_MEMBER.findall(equation))),
                        "dependency_ids": child_ids(probe, "Dependencies"),
                        "digits": integer(probe.attrib.get("Digits")),
                        "encoder": probe.attrib.get("Encoder"),
                        "symbol": probe.attrib.get("Symbol"),
                        "save_dynamic_data": boolean(probe.attrib.get("SaveDynamicData")),
                        "number_of_cycles_to_save": integer(probe.attrib.get("NumberOfCyclesToSave")),
                        "raw_attributes": dict(probe.attrib),
                    }
                )
        elif section_name == "Parts":
            for part in section:
                part_fact = {
                    "id": integer(part.attrib.get("Id")),
                    "name": part.attrib.get("Name", local_name(part.tag)),
                    "text": part.attrib.get("Text"),
                    "description": part.attrib.get("Description"),
                    "raw_attributes": dict(part.attrib),
                }
                result["parts"].append(part_fact)
                for child in part:
                    if local_name(child.tag) != "Measurements":
                        continue
                    for measurement in child:
                        equation = measurement.attrib.get("Equation", "")
                        result["measurements"].append(
                            {
                                "id": integer(measurement.attrib.get("Id")),
                                "part_id": part_fact["id"],
                                "part_name": part_fact["name"],
                                "name": measurement.attrib.get("Name", local_name(measurement.tag)),
                                "text": measurement.attrib.get("Text"),
                                "type": measurement.attrib.get("Type", local_name(measurement.tag)),
                                "equation": equation,
                                "equation_sources": OBJECT_VALUE.findall(equation),
                                "object_sources": sorted(set(OBJECT_MEMBER.findall(equation))),
                                "bound_probe_ids": child_ids(measurement, "Probes"),
                                "dependency_ids": child_ids(measurement, "Dependencies"),
                                "symbol": measurement.attrib.get("Symbol"),
                                "nominal": number(measurement.attrib.get("Nominal")),
                                "operation": measurement.attrib.get("Operation", measurement.attrib.get("OP")),
                                "operation_id": integer(measurement.attrib.get("OperationId")),
                                "evaluate_when_selected": boolean(measurement.attrib.get("EvaluateWhenSelected")),
                                "effective_evaluate_when_selected": (
                                    boolean(measurement.attrib.get("EvaluateWhenSelected"))
                                    if "EvaluateWhenSelected" in measurement.attrib
                                    else True
                                ),
                                "ready_to_gage": integer(measurement.attrib.get("ReadyToGage")),
                                "raw_attributes": dict(measurement.attrib),
                            }
                        )
        elif section_name == "Tags":
            for tag in section:
                result["tags"].append(
                    {
                        "id": integer(tag.attrib.get("Id")),
                        "name": tag.attrib.get("Name", local_name(tag.tag)),
                        "description": tag.attrib.get("Description"),
                        "raw_attributes": dict(tag.attrib),
                    }
                )
        elif section_name in {"Mastering", "MasterSets"}:
            for master_set in section:
                if section_name == "Mastering" and not local_name(master_set.tag).casefold().startswith(
                    "masterset"
                ):
                    continue
                master_set_fact = {
                    "id": integer(master_set.attrib.get("Id")),
                    "name": master_set.attrib.get("Name", local_name(master_set.tag)),
                    "text": master_set.attrib.get("Text"),
                    "description": master_set.attrib.get("Description"),
                    "raw_attributes": dict(master_set.attrib),
                    "masters": [],
                }
                for master in master_set:
                    master_fact = {
                        "id": integer(master.attrib.get("Id")),
                        "name": master.attrib.get("Name", local_name(master.tag)),
                        "raw_attributes": dict(master.attrib),
                        "probes": [],
                    }
                    for master_probe in master:
                        if local_name(master_probe.tag) != "Probe":
                            continue
                        master_fact["probes"].append(
                            {
                                "id": integer(master_probe.attrib.get("Id")),
                                "type": master_probe.attrib.get("Type"),
                                "cert_point": master_probe.attrib.get("CertPoint"),
                                "nominal_size": number(master_probe.attrib.get("NominalSize")),
                                "actual_size": number(master_probe.attrib.get("ActualSize")),
                                "raw_attributes": dict(master_probe.attrib),
                            }
                        )
                    master_set_fact["masters"].append(master_fact)
                result["master_sets"].append(master_set_fact)
        elif section_name == "Features":
            for feature in section:
                result["features"].append(
                    {
                        "id": integer(feature.attrib.get("Id")),
                        "name": feature.attrib.get("Name", local_name(feature.tag)),
                        "text": feature.attrib.get("Text"),
                        "type": feature.attrib.get("Type", local_name(feature.tag)),
                        "raw_attributes": dict(feature.attrib),
                    }
                )
        elif section_name in {"AutoArchive", "Auto-Archive"}:
            result["auto_archive"] = {
                "network_folder": section.attrib.get("NetworkFolder", section.attrib.get("Network folder")),
                "raw_attributes": dict(section.attrib),
            }
    return result


def parse_io(root: ET.Element) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []

    def walk(element: ET.Element, ancestors: list[ET.Element]) -> None:
        if local_name(element.tag) == "Value":
            bus = next((item for item in reversed(ancestors) if item.attrib.get("Type") == "IMBus"), None)
            module = ancestors[-1] if ancestors else None
            module_type = module.attrib.get("Type") if module is not None else None
            capacity_match = IMBUS_CAPACITY.fullmatch(str(module_type or ""))
            siblings = list(module) if module is not None else []
            points.append(
                {
                    "text": element.attrib.get("Text"),
                    "description": element.attrib.get("Description", element.attrib.get("Comment")),
                    "vga_tag": element.attrib.get("VgaTag", element.attrib.get("VGATag")),
                    "enabled": boolean(element.attrib.get("Enabled")),
                    "bus_name": bus.attrib.get("Name") if bus is not None else None,
                    "bus_text": bus.attrib.get("Text") if bus is not None else None,
                    "module_name": module.attrib.get("Name") if module is not None else None,
                    "module_type": module_type,
                    "module_capacity": int(capacity_match.group(1)) if capacity_match else None,
                    "channel_index": siblings.index(element) if element in siblings else None,
                    "raw_attributes": dict(element.attrib),
                }
            )
        for child in element:
            walk(child, ancestors + [element])

    walk(root, [])
    return points


def parse_io_objects(root: ET.Element) -> list[dict[str, Any]]:
    return [
        {
            "name": str(element.attrib.get("Name") or "").strip(),
            "type": element.attrib.get("Type", local_name(element.tag)),
            "text": element.attrib.get("Text"),
            "raw_attributes": dict(element.attrib),
        }
        for element in root.iter()
        if str(element.attrib.get("Name") or "").strip()
    ]


def parse_imbus_modules(root: ET.Element) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for bus in root.iter():
        if str(bus.attrib.get("Type") or "").casefold() != "imbus":
            continue
        dynamic_being_used = boolean(bus.attrib.get("DynamicBeingUsed")) is True
        for module in bus:
            module_name = str(module.attrib.get("Name") or "").strip()
            if not module_name:
                continue
            modules.append(
                {
                    "module_name": module_name,
                    "module_type": module.attrib.get("Type", local_name(module.tag)),
                    "bus_name": str(bus.attrib.get("Name") or "").strip() or None,
                    "dynamic_being_used": dynamic_being_used,
                    "raw_bus_attributes": dict(bus.attrib),
                    "raw_module_attributes": dict(module.attrib),
                }
            )
    return modules


def parse_screens(root: ET.Element) -> list[str]:
    return [
        str(element.attrib.get("Name") or "").strip()
        for element in root.iter()
        if local_name(element.tag) == "Form"
        and str(element.attrib.get("Name") or "").strip()
    ]


def direct_property(element: ET.Element, property_name: str) -> str | None:
    for child in element:
        if local_name(child.tag) != "Property":
            continue
        if child.attrib.get("name") == property_name:
            return child.text
    return None


def parse_form(root: ET.Element, relative_path: str) -> dict[str, Any]:
    objects = []
    code_blocks = []
    for element in root.iter():
        name = local_name(element.tag)
        if name == "Object":
            mappings = {}
            for mapping_name in ("Part", "Measurement", "Nest", "Machine", "Fixture"):
                mapping_value = str(direct_property(element, mapping_name) or "").strip()
                if mapping_value:
                    mappings[mapping_name] = mapping_value
            objects.append(
                {
                    "name": element.attrib.get("name"),
                    "serialized_name": direct_property(element, "Name"),
                    "mappings": mappings,
                }
            )
        elif name == "Property" and element.attrib.get("name") == "Code":
            if str(element.text or "").strip():
                code_blocks.append(str(element.text))
    return {
        "relative_path": relative_path,
        "objects": objects,
        "code": "\n".join(code_blocks),
    }
