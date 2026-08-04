from __future__ import annotations

import math
import re
from typing import Any

from rules_code import source_blocks
from rules_structure import result


NUMBER_LITERAL = re.compile(
    r"(?<![A-Za-z_])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?(?![A-Za-z_])"
)
FORMULA_CONTROL = re.compile(
    r"\b(?:AddHandler|RemoveHandler)\b|"
    r"\.\s*(?:Refresh|Evaluate|AfterUpdate|AfterEvaluate)\s*\(|"
    r"\bThread(?:ing)?\.Thread\.Sleep\b",
    re.IGNORECASE,
)
MEMBER_ASSIGNMENT = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*[A-Za-z_][A-Za-z0-9_]*\s*=",
    re.IGNORECASE,
)
PC_SYMBOL = re.compile(r"^p\d+c\d+$", re.IGNORECASE)
PLACEHOLDER_MAPPING = re.compile(r"^\([^()]+\)$")
SETUP_NAME = "setupfeatureprobegeometry"
SETUP_CALL = re.compile(r"\bSetupFeatureProbeGeometry\s*\(", re.IGNORECASE)
GEOMETRY_MUTATION = re.compile(r"\.\s*(?:AddPoint|ClearPoints|Recalc)\s*\(", re.IGNORECASE)
NOMINAL_SUBTRACTION = re.compile(r"-\s*Me\s*\.\s*Nominal\b", re.IGNORECASE)
TEMPERATURE_TERM = re.compile(r"\b(?:Temperature|Temp(?:erature)?Comp|Thermal)\w*\b|温度|温补", re.IGNORECASE)
ITEM_NUMBER = re.compile(r"\bF\s*0*(\d+)\b|#\s*0*(\d+)\b", re.IGNORECASE)
PLACEHOLDER = re.compile(r"^(?:-|N/?A|None|Unknown|TODO|TBD|未定义|待定)$", re.IGNORECASE)
PARAMETER_PERSISTENCE = re.compile(
    r"\bSetValue(?:As[A-Za-z]+)?\s*\(\s*[\"'][^\"']*"
    r"(?:Temperature|Temp|Thermal|温补|温度)[^\"']*(?:Coeff(?:icient)?|Factor|参数|系数)[^\"']*[\"']",
    re.IGNORECASE,
)
MEASUREMENT_SYMBOL_HINTS = (
    # Specific compound terms must precede their generic suffixes.
    (re.compile(r"\bTotal\s*Runout\b|全跳动", re.IGNORECASE), "TotalRunout"),
    (
        re.compile(
            r"\b(?:Center\s*Point|Centre\s*Point|CenterPoint|CentrePoint)\b|中心点|中心偏移",
            re.IGNORECASE,
        ),
        "CenterPoint",
    ),
    (re.compile(r"\bCylindricity\b|圆柱度", re.IGNORECASE), "Cylindricity"),
    (re.compile(r"\bParallelism\b|平行度", re.IGNORECASE), "Parallelism"),
    (re.compile(r"\bFlatness\b|平面度", re.IGNORECASE), "Flatness"),
    (re.compile(r"\bOvality\b|椭圆度", re.IGNORECASE), "Ovality"),
    (re.compile(r"\bRoundness\b|圆度", re.IGNORECASE), "Roundness"),
    (re.compile(r"\bRunout\b|圆跳动|跳动", re.IGNORECASE), "Runout"),
    (re.compile(r"\bTemperature\b|温度", re.IGNORECASE), "Temperature"),
    (re.compile(r"\b(?:Diameter|Dia)\b|直径|内径|外径|孔径", re.IGNORECASE), "Diameter"),
    (
        re.compile(
            r"\b(?:Distance|Width|Height|Depth)\b|距离|长度|高度|宽度|深度|厚度|间距",
            re.IGNORECASE,
        ),
        "Distance",
    ),
    (re.compile(r"\b(?:Angle|Degree)\b|角度", re.IGNORECASE), "Angle"),
)


def infer_measurement_symbol(measurement: dict[str, Any]) -> str | None:
    semantic_text = " ".join(
        str(measurement.get(field) or "").strip() for field in ("name", "text")
    )
    return next(
        (symbol for pattern, symbol in MEASUREMENT_SYMBOL_HINTS if pattern.search(semantic_text)),
        None,
    )


def active_code(code: str) -> str:
    """Remove VB comments and string contents while preserving line positions."""
    rendered: list[str] = []
    for raw_line in str(code or "").splitlines():
        line: list[str] = []
        in_string = False
        index = 0
        while index < len(raw_line):
            char = raw_line[index]
            if in_string:
                if char == '"':
                    if index + 1 < len(raw_line) and raw_line[index + 1] == '"':
                        line.extend("  ")
                        index += 2
                        continue
                    in_string = False
                line.append(" ")
            elif char == '"':
                in_string = True
                line.append(" ")
            elif char == "'":
                line.extend(" " * (len(raw_line) - index))
                break
            else:
                line.append(char)
            index += 1
        rendered.append("".join(line))
    return "\n".join(rendered)


def uncommented_code(code: str) -> str:
    rendered: list[str] = []
    for raw_line in str(code or "").splitlines():
        in_string = False
        index = 0
        while index < len(raw_line):
            char = raw_line[index]
            if char == '"':
                if in_string and index + 1 < len(raw_line) and raw_line[index + 1] == '"':
                    index += 2
                    continue
                in_string = not in_string
            elif char == "'" and not in_string:
                raw_line = raw_line[:index]
                break
            index += 1
        rendered.append(raw_line)
    return "\n".join(rendered)


def manual_result(
    rule: dict[str, Any],
    *,
    object_name: str | None = None,
    file: str | None = None,
    reason: str,
    missing_evidence: str,
    manual_action: str,
    **details: Any,
) -> dict[str, Any]:
    evidence = {
        "reason": reason,
        "missing_evidence": missing_evidence,
        "manual_action": manual_action,
        **details,
    }
    if object_name:
        evidence["object"] = object_name
    if file:
        evidence["file"] = file
    return result(rule, "MANUAL_VERIFY", [evidence])


def actionable_evidence(
    *,
    object_name: str | None = None,
    file: str | None = None,
    reason: str,
    missing_evidence: str,
    manual_action: str,
    **details: Any,
) -> dict[str, Any]:
    evidence = {
        "reason": reason,
        "missing_evidence": missing_evidence,
        "manual_action": manual_action,
        **details,
    }
    if object_name:
        evidence["object"] = object_name
    if file:
        evidence["file"] = file
    return evidence


def check_form_object_mappings(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    names: dict[str, set[str]] = {
        "Part": {
            str(item.get("name") or "").casefold()
            for item in facts.get("parts", [])
            if str(item.get("name") or "").strip()
        },
        "Measurement": {
            str(item.get("name") or "").casefold()
            for item in facts.get("measurements", [])
            if str(item.get("name") or "").strip()
        },
    }
    all_object_names = {
        str(item.get("name") or "").casefold()
        for collection in (
            "operations",
            "parts",
            "measurements",
            "probes",
            "master_sets",
            "features",
            "tags",
            "io_objects",
        )
        for item in facts.get(collection, [])
        if str(item.get("name") or "").strip()
    }
    all_object_names.update(
        str(item.get("name") or item.get("serialized_name") or "").casefold()
        for form in facts.get("forms", [])
        for item in form.get("objects", [])
        if str(item.get("name") or item.get("serialized_name") or "").strip()
    )
    for mapping_name in ("Nest", "Machine", "Fixture"):
        names[mapping_name] = all_object_names

    checked = 0
    evidence: list[dict[str, Any]] = []
    for form in facts.get("forms", []):
        for item in form.get("objects", []):
            for mapping_name, raw_value in item.get("mappings", {}).items():
                value = str(raw_value or "").strip()
                if mapping_name not in names or not value or PLACEHOLDER_MAPPING.fullmatch(value):
                    continue
                checked += 1
                if value.casefold() not in names[mapping_name]:
                    evidence.append(
                        {
                            "file": form.get("relative_path"),
                            "object": item.get("name") or item.get("serialized_name"),
                            "mapping": mapping_name,
                            "target": value,
                            "reason": "mapping_target_not_found",
                        }
                    )
    if checked == 0:
        return result(rule, "NOT_APPLICABLE", [], "未发现可解析的 Form 对象映射")
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_formula_surface(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    evidence: list[dict[str, Any]] = []
    for section, surface in (("measurements", "Measurement"), ("probes", "Probe")):
        for item in facts.get(section, []):
            equation = str(item.get("equation") or "")
            for line_number, line in enumerate(active_code(equation).splitlines(), 1):
                match = FORMULA_CONTROL.search(line)
                if match is None:
                    assignment = MEMBER_ASSIGNMENT.search(line)
                    if assignment and assignment.group(1).casefold() not in {"me", "mybase"}:
                        match = assignment
                if match:
                    evidence.append(
                        {
                            "file": "VGA.xml",
                            "surface": surface,
                            "object": item.get("name"),
                            "line": line_number,
                            "snippet": match.group(0).strip(),
                            "reason": "control_action_in_formula_surface",
                        }
                    )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_nominal_literal(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    evidence: list[dict[str, Any]] = []
    for measurement in facts.get("measurements", []):
        nominal = measurement.get("nominal")
        if not isinstance(nominal, (int, float)) or not math.isfinite(float(nominal)):
            continue
        nominal = float(nominal)
        if math.isclose(nominal, 0.0, abs_tol=1e-12):
            continue
        for line_number, line in enumerate(active_code(str(measurement.get("equation") or "")).splitlines(), 1):
            for match in NUMBER_LITERAL.finditer(line):
                literal = float(match.group(0))
                if math.isclose(literal, nominal, rel_tol=1e-12, abs_tol=1e-12):
                    evidence.append(
                        {
                            "file": "VGA.xml",
                            "object": measurement.get("name"),
                            "line": line_number,
                            "literal": literal,
                            "nominal": nominal,
                            "reason": "formula_literal_matches_measurement_nominal",
                        }
                    )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_probe_symbol_convention(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    checked = 0
    evidence: list[dict[str, Any]] = []
    for probe in facts.get("probes", []):
        name = str(probe.get("name") or "")
        if not PC_SYMBOL.fullmatch(name):
            continue
        checked += 1
        actual = str(probe.get("symbol") or "").strip()
        if actual.casefold() != "centerpoint":
            evidence.append(
                {
                    "file": "VGA.xml",
                    "object": name,
                    "expected_symbol": "CenterPoint",
                    "actual_symbol": actual,
                    "reason": "probe_symbol_conflicts_with_confirmed_name_convention",
                }
            )
    if checked == 0:
        return result(rule, "NOT_APPLICABLE", [], "未发现 pXcY 命名 Probe")
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_feature_geometry_setup(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    blocks = [block for source in facts.get("code_sources", []) for block in source_blocks(source)]
    active_blocks = [(block, active_code(str(block.get("body") or ""))) for block in blocks]
    setup_blocks = [(block, body) for block, body in active_blocks if str(block.get("name") or "").casefold() == SETUP_NAME]
    call_blocks = [(block, body) for block, body in active_blocks if SETUP_CALL.search(body)]
    if not setup_blocks and not call_blocks:
        return result(rule, "NOT_APPLICABLE", [], "未发现 SetupFeatureProbeGeometry")

    evidence: list[dict[str, Any]] = []
    initialize_calls = [
        block
        for block, body in call_blocks
        if str(block.get("name") or "").casefold() in {"vga_initialize", "vgainitialize"}
        or re.search(r"\bHandles\s+VGA\.Initialize\b", str(block.get("header") or ""), re.IGNORECASE)
    ]
    if not initialize_calls:
        reference = (setup_blocks or call_blocks)[0][0]
        evidence.append(
            {
                "file": reference.get("file"),
                "object": "SetupFeatureProbeGeometry",
                "reason": "setup_not_called_from_vga_initialize",
            }
        )
    for block, body in setup_blocks:
        for offset, line in enumerate(body.splitlines()):
            match = GEOMETRY_MUTATION.search(line)
            if match:
                evidence.append(
                    {
                        "file": block.get("file"),
                        "object": block.get("name"),
                        "procedure": block.get("name"),
                        "line": int(block.get("body_start_line") or 1) + offset,
                        "snippet": match.group(0).strip(),
                        "reason": "feature_recalculation_mixed_into_geometry_setup",
                    }
                )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_angle_encoder_consistency(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    angle_probes = [
        probe for probe in facts.get("probes", []) if str(probe.get("type") or "").casefold() == "angle"
    ]
    if not angle_probes:
        return result(rule, "NOT_APPLICABLE", [], "项目中不存在 Angle Probe")
    valid_encoders = {
        value.casefold()
        for probe in angle_probes
        for value in (
            str(probe.get("name") or "").strip(),
            str(probe.get("encoder") or "").strip(),
        )
        if value
    }
    evidence: list[dict[str, Any]] = []
    for probe in facts.get("probes", []):
        if probe in angle_probes:
            continue
        encoder = str(probe.get("encoder") or "").strip()
        if encoder and encoder.casefold() not in valid_encoders:
            evidence.append(
                {
                    "file": "VGA.xml",
                    "object": probe.get("name"),
                    "encoder": encoder,
                    "angle_encoders": sorted(valid_encoders),
                    "reason": "probe_encoder_has_no_corresponding_angle_probe",
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_diameter_nominal_semantics(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    probes = {str(item.get("name") or "").casefold(): item for item in facts.get("probes", [])}
    evidence: list[dict[str, Any]] = []
    for measurement in facts.get("measurements", []):
        equation = active_code(str(measurement.get("equation") or ""))
        if not NOMINAL_SUBTRACTION.search(equation):
            continue
        sources = [probes.get(str(name).casefold()) for name in measurement.get("equation_sources", [])]
        diameter_context = str(measurement.get("symbol") or "").casefold() == "diameter" or any(
            source
            and str(source.get("symbol") or "").casefold() == "diameter"
            for source in sources
        )
        if diameter_context:
            evidence.append(
                actionable_evidence(
                    file="VGA.xml",
                    object_name=str(measurement.get("name") or "Measurement"),
                    reason="diameter_formula_subtracts_me_nominal",
                    missing_evidence="该测量应输出实际值还是相对名义值偏差的客户/测量语义",
                    manual_action="按测点图和测量定义确认输出语义；若应输出直径实际值，移除对 Me.Nominal 的减法",
                    equation=str(measurement.get("equation") or ""),
                )
            )
    if not evidence:
        return result(rule, "NOT_APPLICABLE", [], "未发现直径/对射公式减去 Me.Nominal")
    return result(rule, "MANUAL_VERIFY", evidence)


def check_probe_symbol_semantics(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    probes_by_name = {
        str(probe.get("name") or "").casefold(): probe
        for probe in facts.get("probes", [])
        if str(probe.get("name") or "").strip()
    }
    expected_by_probe: dict[str, set[str]] = {}
    usages_by_probe: dict[str, set[str]] = {}

    def propagate(source_name: str, expected: str, measurement_name: str, path: set[str]) -> None:
        key = str(source_name or "").casefold()
        probe = probes_by_name.get(key)
        if probe is None or key in path:
            return
        dependencies = [
            str(name)
            for name in probe.get("equation_sources", [])
            if str(name or "").casefold() in probes_by_name
        ]
        if not dependencies:
            return
        expected_by_probe.setdefault(key, set()).add(expected)
        usages_by_probe.setdefault(key, set()).add(measurement_name)
        next_path = path | {key}
        for dependency in dependencies:
            propagate(dependency, expected, measurement_name, next_path)

    for measurement in facts.get("measurements", []):
        expected = infer_measurement_symbol(measurement)
        if expected is None:
            continue
        measurement_name = str(measurement.get("name") or "Measurement")
        for source_name in measurement.get("equation_sources", []):
            propagate(str(source_name), expected, measurement_name, set())

    checked = 0
    evidence: list[dict[str, Any]] = []
    for probe in facts.get("probes", []):
        name = str(probe.get("name") or "")
        key = name.casefold()
        symbol = str(probe.get("symbol") or "").strip()
        expected_symbols = set(expected_by_probe.get(key, set()))
        if PC_SYMBOL.fullmatch(name):
            expected_symbols.add("CenterPoint")
        if not expected_symbols:
            continue
        checked += 1
        if len(expected_symbols) > 1:
            evidence.append(
                {
                    "file": "VGA.xml",
                    "object": name or "Probe",
                    "reason": "computed_probe_used_by_conflicting_measurement_semantics",
                    "actual_symbol": symbol,
                    "expected_symbols": sorted(expected_symbols),
                    "measurements": sorted(usages_by_probe.get(key, set())),
                }
            )
            continue
        expected = next(iter(expected_symbols))
        if symbol.casefold() != expected.casefold():
            evidence.append(
                {
                    "file": "VGA.xml",
                    "object": name or "Probe",
                    "reason": "computed_probe_symbol_conflicts_with_measurement_semantics",
                    "actual_symbol": symbol,
                    "expected_symbol": expected,
                    "measurements": sorted(usages_by_probe.get(key, set())),
                }
            )
    if checked == 0:
        return result(rule, "NOT_APPLICABLE", [], "未发现可由项目语义确定 Symbol 的公式 Probe")
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def temperature_probes(facts: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        probe
        for probe in facts.get("probes", [])
        if TEMPERATURE_TERM.search(
            " ".join(
                str(probe.get(field) or "") for field in ("name", "text", "type", "symbol")
            )
        )
    ]


def master_probe_rows(facts: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    return [
        (master_set, master, probe)
        for master_set in facts.get("master_sets", [])
        for master in master_set.get("masters", [])
        for probe in master.get("probes", [])
    ]


def check_temperature_masterset(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    candidates = temperature_probes(facts)
    if not candidates:
        return result(rule, "NOT_APPLICABLE", [], "项目中未发现温度类 Probe")
    mastered_ids = {probe.get("id") for _, _, probe in master_probe_rows(facts)}
    missing = [probe for probe in candidates if probe.get("id") not in mastered_ids]
    if not missing:
        return result(
            rule,
            "PASS",
            [{"file": "VGA.xml", "objects": [probe.get("name") for probe in candidates], "reason": "temperature_probes_in_masterset"}],
        )
    evidence = [
        actionable_evidence(
            file="VGA.xml",
            object_name=str(probe.get("name") or "Temperature Probe"),
            reason="temperature_probe_not_in_masterset",
            missing_evidence="校准流程是否要求记录该环境温度 Probe",
            manual_action="确认校准记录要求；需要记录时将该温度 Probe 加入对应 MasterSet",
            probe_id=probe.get("id"),
        )
        for probe in missing
    ]
    return result(rule, "MANUAL_VERIFY", evidence)


def normalized_item_numbers(text: str) -> set[str]:
    values: set[str] = set()
    for match in ITEM_NUMBER.finditer(text):
        number = match.group(1) or match.group(2)
        if number:
            values.add(f"f{int(number)}")
    return values


def check_master_certpoint(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    probes = {item.get("id"): item for item in facts.get("probes", [])}
    evidence: list[dict[str, Any]] = []
    for master_set, master, master_probe in master_probe_rows(facts):
        probe = probes.get(master_probe.get("id"), {})
        expected = normalized_item_numbers(
            f"{probe.get('name') or ''} {probe.get('text') or ''}"
        )
        if not expected:
            continue
        cert_point = str(master_probe.get("cert_point") or "").strip()
        actual = normalized_item_numbers(cert_point)
        if not cert_point or PLACEHOLDER.fullmatch(cert_point) or expected.isdisjoint(actual):
            evidence.append(
                actionable_evidence(
                    file="VGA.xml",
                    object_name=str(probe.get("name") or f"Probe#{master_probe.get('id')}"),
                    reason="master_certpoint_missing_or_conflicts_with_locatable_item_number",
                    missing_evidence="测点图中该 Probe 对应的最终检测项目编号",
                    manual_action="对照测点图核对 CertPoint，并填写与检测项目一致的编号",
                    master_set=master_set.get("name"),
                    master=master.get("name"),
                    cert_point=cert_point,
                    expected_item_numbers=sorted(expected),
                )
            )
    if not evidence:
        return result(rule, "NOT_APPLICABLE", [], "未发现可定位编号与 CertPoint 的疑似冲突")
    return result(rule, "MANUAL_VERIFY", evidence)


def check_master_nominal_actual(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    probes = {probe.get("id"): probe for probe in facts.get("probes", [])}
    probe_names = {
        str(probe.get("name") or "").casefold()
        for probe in facts.get("probes", [])
        if str(probe.get("name") or "").strip()
    }
    measurements_by_probe: dict[int, list[dict[str, Any]]] = {}
    for measurement in facts.get("measurements", []):
        for probe_id in measurement.get("bound_probe_ids", []):
            if isinstance(probe_id, int):
                measurements_by_probe.setdefault(probe_id, []).append(measurement)

    failures: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for master_set, master, master_probe in master_probe_rows(facts):
        probe_id = master_probe.get("id")
        project_probe = probes.get(probe_id, {})
        nominal_size = master_probe.get("nominal_size")
        actual_size = master_probe.get("actual_size")
        dependencies = [value for value in project_probe.get("dependency_ids", []) if isinstance(value, int)]
        equation_probe_sources = [
            str(value)
            for value in project_probe.get("equation_sources", [])
            if str(value or "").casefold() in probe_names
        ]
        single_point_zero = (
            not dependencies
            and not equation_probe_sources
            and isinstance(nominal_size, (int, float))
            and isinstance(actual_size, (int, float))
            and math.isfinite(float(nominal_size))
            and math.isfinite(float(actual_size))
            and math.isclose(float(nominal_size), 0.0, rel_tol=1e-12, abs_tol=1e-12)
            and math.isclose(float(actual_size), 0.0, rel_tol=1e-12, abs_tol=1e-12)
        )
        if single_point_zero:
            continue

        nominal_rows = [
            (str(measurement.get("name") or "Measurement"), float(measurement.get("nominal")))
            for measurement in measurements_by_probe.get(probe_id, [])
            if isinstance(measurement.get("nominal"), (int, float))
            and not isinstance(measurement.get("nominal"), bool)
            and math.isfinite(float(measurement.get("nominal")))
        ]
        unique_nominals: list[float] = []
        for _, nominal in nominal_rows:
            if not any(math.isclose(nominal, known, rel_tol=1e-12, abs_tol=1e-12) for known in unique_nominals):
                unique_nominals.append(nominal)
        unique_nominals.sort()
        object_name = f"{master_set.get('name')}/{master.get('name')}/Probe#{probe_id}"
        if not unique_nominals:
            continue
        if len(unique_nominals) > 1:
            conflicts.append(
                actionable_evidence(
                    file="VGA.xml",
                    object_name=object_name,
                    reason="master_probe_maps_to_conflicting_measurement_nominals",
                    missing_evidence="该 MasterSet Probe 应对应的唯一 Measurement Nominal",
                    manual_action="核对 Measurement 与 Probe 绑定，确认该校准 Probe 的正确名义值",
                    probe_name=project_probe.get("name"),
                    probe_text=project_probe.get("text"),
                    measurement_nominals=unique_nominals,
                    measurements=sorted({name for name, _ in nominal_rows}),
                )
            )
            continue

        expected = unique_nominals[0]
        matches = (
            isinstance(nominal_size, (int, float))
            and not isinstance(nominal_size, bool)
            and math.isfinite(float(nominal_size))
            and math.isclose(float(nominal_size), expected, rel_tol=1e-12, abs_tol=1e-12)
        )
        if not matches:
            failures.append({
                "file": "VGA.xml",
                "object": object_name,
                "probe_name": project_probe.get("name"),
                "probe_text": project_probe.get("text"),
                "reason": "master_nominal_size_differs_from_measurement_nominal",
                "expected_nominal": expected,
                "actual_nominal_size": nominal_size,
                "measurements": sorted({name for name, _ in nominal_rows}),
            })

    if failures:
        return result(rule, "FAIL", failures)
    if conflicts:
        return result(rule, "MANUAL_VERIFY", conflicts)
    return result(rule, "PASS", [])


def check_measurement_name_symbol(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    checked = 0
    evidence: list[dict[str, Any]] = []
    for measurement in facts.get("measurements", []):
        name = str(measurement.get("name") or "").strip()
        text = str(measurement.get("text") or "").strip()
        symbol = str(measurement.get("symbol") or "").strip()
        expected = infer_measurement_symbol(measurement)
        if expected is None:
            continue
        checked += 1
        if symbol.casefold() != expected.casefold():
            evidence.append(
                {
                    "file": "VGA.xml",
                    "object": name or "Measurement",
                    "reason": "measurement_symbol_conflicts_with_explicit_name_or_text",
                    "text": text,
                    "actual_symbol": symbol,
                    "expected_symbol": expected,
                }
            )
    if checked == 0:
        return result(rule, "NOT_APPLICABLE", [], "未发现可识别检测语义的 Measurement 名称或 Text")
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_temperature_traceability(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    candidates = temperature_probes(facts)
    semantic_code_parts: list[str] = []
    for source in facts.get("code_sources", []):
        blocks = source_blocks(source)
        if not blocks:
            semantic_code_parts.append(str(source.get("code") or ""))
            continue
        for block in blocks:
            name = str(block.get("name") or "")
            if re.search(r"(?:Placeholder|Stub|TODO|TBD)", name, re.IGNORECASE):
                continue
            semantic_code_parts.append(f"{name}\n{block.get('body') or ''}")
    code = "\n".join(semantic_code_parts)
    has_temp_code = TEMPERATURE_TERM.search(active_code(code)) is not None
    if not candidates and not has_temp_code:
        return result(rule, "NOT_APPLICABLE", [], "未发现温补功能、温度 Probe 或温补参数")
    raw_temperature_persisted = bool(candidates) and all(
        probe.get("save_dynamic_data") is True for probe in candidates
    )
    parameter_persisted = PARAMETER_PERSISTENCE.search(uncommented_code(code)) is not None
    if raw_temperature_persisted and parameter_persisted:
        return result(
            rule,
            "PASS",
            [
                {
                    "file": "VGA.xml / CodeModule.vgs",
                    "objects": [probe.get("name") for probe in candidates],
                    "reason": "temperature_raw_data_and_parameters_persisted",
                }
            ],
        )
    missing = []
    if not raw_temperature_persisted:
        missing.append("原始温度数据持久化配置")
    if not parameter_persisted:
        missing.append("温补算法参数持久化写入")
    return manual_result(
        rule,
        object_name=", ".join(str(probe.get("name") or "Temperature") for probe in candidates) or "温补代码",
        file="VGA.xml / CodeModule.vgs",
        reason="temperature_traceability_incomplete",
        missing_evidence="、".join(missing),
        manual_action="确认协议中的温补要求，并核对原始温度及系数/参数均可在结果或配置中追溯",
        raw_temperature_persisted=raw_temperature_persisted,
        parameter_persisted=parameter_persisted,
    )
