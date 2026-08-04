#!/usr/bin/env python3
from __future__ import annotations

import xml.etree.ElementTree as ET

from rules_dependencies import check_probe_equation_objects
from rules_measurement import check_probe_return_zero
from xml_facts import parse_imbus_modules, parse_vga


DEP_RULE = {
    "rule_id": "VG-DEP-001",
    "severity": "P1",
    "title": "Probe Equation 引用的项目对象必须存在",
    "sources": [{"reference": "regression"}],
    "fail_condition": "Probe Equation 存在无法解析的项目对象引用",
}
MEAS_RULE = {
    "rule_id": "VG-MEAS-013",
    "severity": "P1",
    "title": "Probe 不得确定性直接 Return 0",
    "sources": [{"reference": "regression"}],
    "fail_condition": "Probe 确定性直接 Return 0",
}

E1_EQUATION = """Function e1_Value() As Double
    If CInt(IMBModule11(0).Value) > 0 Then
        Return MapIntegerToDouble(CInt(IMBModule11(0).Value), 0, 20000, 0, 360)
    ElseIf CInt(IMBModule11(0).Value) < 0 Then
        Return MapIntegerToDouble(CInt(IMBModule11(0).Value), -20000, 0, 0, 360)
    Else
        Return 0
    End If
End Function"""


def probe(name: str, equation: str, sources: list[str]) -> dict:
    return {
        "id": 1,
        "name": name,
        "equation": equation,
        "object_sources": sources,
        "raw_attributes": {"Active": "True"},
    }


def test_e1_object_sources_and_helpers() -> None:
    root = ET.fromstring(
        f'''<VGA><Probes Code="Public Function MapIntegerToDouble() As Double&#10;Return 1&#10;End Function">
        <e1 Type="Angle" Id="149" Name="e1" Equation="{E1_EQUATION.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), '&#10;')}" />
        </Probes></VGA>'''
    )
    facts = parse_vga(root)
    assert facts["probe_code_functions"] == ["MapIntegerToDouble"], facts
    assert facts["probes"][0]["object_sources"] == ["IMBModule11"], facts
    facts["io_objects"] = [{"name": "IMBModule11"}]
    dep_result = check_probe_equation_objects(facts, DEP_RULE)
    assert dep_result["status"] == "PASS", dep_result


def test_dynamic_module_probe_is_allowed() -> None:
    facts = {
        "probes": [probe("dynamic_zero", "Function f() As Double\nReturn 0\nEnd Function", ["IMBModule11"])],
        "imbus_modules": [
            {"module_name": "IMBModule11", "bus_name": "IMBus2", "dynamic_being_used": True}
        ],
    }
    result = check_probe_return_zero(facts, MEAS_RULE, {})
    assert result["status"] == "PASS", result


def test_imbus_parent_dynamic_attribute_is_parsed() -> None:
    root = ET.fromstring(
        '''<IO>
        <IMBus1 Type="IMBus" Name="IMBus1" DynamicBeingUsed="True">
          <Module Type="IMB_im1" Name="IMBModule1"><Value /></Module>
        </IMBus1>
        <IMBus2 Type="IMBus" Name="IMBus2">
          <Module Type="IMB_im1" Name="IMBModule2"><Value /></Module>
        </IMBus2>
        </IO>'''
    )
    modules = {item["module_name"]: item for item in parse_imbus_modules(root)}
    assert modules["IMBModule1"]["dynamic_being_used"] is True, modules
    assert modules["IMBModule2"]["dynamic_being_used"] is False, modules


def test_nondynamic_direct_zero_fails() -> None:
    for dynamic_value in (False, None):
        facts = {
            "probes": [probe("placeholder", "Function f() As Double\nReturn 0.0\nEnd Function", ["IMBModule11"])],
            "imbus_modules": [
                {
                    "module_name": "IMBModule11",
                    "bus_name": "IMBus2",
                    "dynamic_being_used": dynamic_value,
                }
            ],
        }
        result = check_probe_return_zero(facts, MEAS_RULE, {})
        assert result["status"] == "FAIL", result


def test_e1_conditional_zero_branch_is_not_placeholder() -> None:
    facts = {
        "probes": [probe("e1", E1_EQUATION, ["IMBModule11"])],
        "imbus_modules": [
            {"module_name": "IMBModule11", "bus_name": "IMBus2", "dynamic_being_used": False}
        ],
    }
    result = check_probe_return_zero(facts, MEAS_RULE, {})
    assert result["status"] == "PASS", result


def test_ordinary_direct_zero_still_fails() -> None:
    facts = {
        "probes": [probe("ordinary_placeholder", "Function f() As Double\nReturn 0\nEnd Function", [])],
        "imbus_modules": [],
    }
    result = check_probe_return_zero(facts, MEAS_RULE, {})
    assert result["status"] == "FAIL", result


def main() -> None:
    test_e1_object_sources_and_helpers()
    test_dynamic_module_probe_is_allowed()
    test_imbus_parent_dynamic_attribute_is_parsed()
    test_nondynamic_direct_zero_fails()
    test_e1_conditional_zero_branch_is_not_placeholder()
    test_ordinary_direct_zero_still_fails()
    print("VG-DEP-001 / VG-MEAS-013 IMBus dynamic probe regression tests passed")


if __name__ == "__main__":
    main()
