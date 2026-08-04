#!/usr/bin/env python3
from __future__ import annotations

from rules_binding import check_measurement_probe_exists
from rules_io import check_imbus_text_and_channels
from rules_measurement import check_measurement_return_zero


IO_RULE = {
    "rule_id": "VG-IO-011",
    "severity": "P1",
    "title": "IMBus 标识与通道 Text",
    "sources": [{"reference": "regression"}],
    "fail_condition": "IMBus 标识或通道 Text 无效",
}
BIND_RULE = {
    "rule_id": "VG-BIND-002",
    "severity": "P1",
    "title": "Measurement 引用必须可解析",
    "sources": [{"reference": "regression"}],
    "fail_condition": "Measurement 引用无法解析",
}
MEAS_RULE = {
    "rule_id": "VG-MEAS-021",
    "severity": "P1",
    "title": "Measurement Return 0 类型判定",
    "sources": [{"reference": "regression"}],
    "fail_condition": "Measurement 返回 0 不符合类型规则",
}


def io_point(bus_text: str, text: str = "0 [p1]") -> dict:
    return {
        "bus_name": "IMBus1",
        "bus_text": bus_text,
        "module_type": "IMB_im1",
        "text": text,
    }


def test_io_connection_markers() -> None:
    for marker in ("COM3", "Serial COM 12", "192.168.1.25", "IBR USB adapter", "USB3 adapter"):
        checked = check_imbus_text_and_channels({"io_points": [io_point(marker)]}, IO_RULE, {})
        assert checked["status"] == "PASS", (marker, checked)

    missing = check_imbus_text_and_channels({"io_points": [io_point("IBR interface")]}, IO_RULE, {})
    assert missing["status"] == "FAIL", missing

    bad_ip = check_imbus_text_and_channels({"io_points": [io_point("999.1.1.1")]}, IO_RULE, {})
    assert bad_ip["status"] == "FAIL", bad_ip

    bad_channel = check_imbus_text_and_channels(
        {"io_points": [io_point("USB", "sensor p1")]}, IO_RULE, {}
    )
    assert bad_channel["status"] == "FAIL", bad_channel


def measurement(name: str, equation: str, sources: list[str], measurement_type: str = "Double") -> dict:
    return {
        "name": name,
        "type": measurement_type,
        "equation": equation,
        "equation_sources": sources,
        "raw_attributes": {"Active": "True"},
    }


def test_custom_variable_binding() -> None:
    local = measurement(
        "M1",
        "Function M1_Value() As Double\n"
        "Dim CustomResult As DoubleMeasurement = DirectCast(Part1(\"M2\"), DoubleMeasurement)\n"
        "Return CustomResult.Value\nEnd Function",
        ["CustomResult"],
    )
    checked = check_measurement_probe_exists({"measurements": [local]}, BIND_RULE)
    assert checked["status"] == "PASS", checked

    io_object = measurement(
        "M2C", "Function M2C_Value() As String\nReturn SerialTag.Value\nEnd Function", ["SerialTag"], "String"
    )
    checked = check_measurement_probe_exists(
        {
            "measurements": [io_object],
            "io_objects": [{"name": "SerialTag", "type": "String"}],
        },
        BIND_RULE,
    )
    assert checked["status"] == "PASS", checked

    public_global = measurement(
        "M2", "Function M2_Value() As Double\nReturn SharedResult.Value\nEnd Function", ["SharedResult"]
    )
    checked = check_measurement_probe_exists(
        {
            "measurements": [public_global],
            "code_module": {"code": "Public SharedResult As DoubleMeasurement"},
        },
        BIND_RULE,
    )
    assert checked["status"] == "PASS", checked

    public_dim = measurement(
        "M2B", "Function M2B_Value() As Double\nReturn TempCycle.Value\nEnd Function", ["TempCycle"]
    )
    checked = check_measurement_probe_exists(
        {
            "measurements": [public_dim],
            "probe_code": "Public Dim TempCycle As DoubleMeasurement",
        },
        BIND_RULE,
    )
    assert checked["status"] == "PASS", checked

    missing_probe = measurement(
        "M3", "Function M3_Value() As Double\nReturn p999.Value\nEnd Function", ["p999"]
    )
    checked = check_measurement_probe_exists({"measurements": [missing_probe]}, BIND_RULE)
    assert checked["status"] == "FAIL", checked


def test_measurement_return_zero_by_type() -> None:
    double_branch = measurement(
        "MD",
        "Function MD_Value() As Double\nIf Ready Then\nReturn 1\nElse\nReturn 0\nEnd If\nEnd Function",
        [],
        "Double",
    )
    checked = check_measurement_return_zero({"measurements": [double_branch]}, MEAS_RULE, {})
    assert checked["status"] == "FAIL", checked

    double_commented = measurement(
        "MDC", "Function MDC_Value() As Double\nReturn 0 ' invalid placeholder\nEnd Function", [], "Double"
    )
    checked = check_measurement_return_zero({"measurements": [double_commented]}, MEAS_RULE, {})
    assert checked["status"] == "FAIL", checked

    integer_branch = measurement(
        "MI",
        "Function MI_Value() As Integer\nIf Ready Then\nReturn 1\nElse\nReturn 0\nEnd If\nEnd Function",
        [],
        "Integer",
    )
    checked = check_measurement_return_zero({"measurements": [integer_branch]}, MEAS_RULE, {})
    assert checked["status"] == "PASS", checked

    integer_direct = measurement(
        "MI0", "Function MI0_Value() As Integer\nReturn 0\nEnd Function", [], "Integer"
    )
    checked = check_measurement_return_zero({"measurements": [integer_direct]}, MEAS_RULE, {})
    assert checked["status"] == "FAIL", checked

    string_zero = measurement(
        "MS", "Function MS_Value() As String\nReturn 0\nEnd Function", [], "String"
    )
    checked = check_measurement_return_zero({"measurements": [string_zero]}, MEAS_RULE, {})
    assert checked["status"] == "PASS", checked


def main() -> None:
    test_io_connection_markers()
    test_custom_variable_binding()
    test_measurement_return_zero_by_type()
    print("VG-IO-011 / VG-BIND-002 / VG-MEAS-021 regression tests passed")


if __name__ == "__main__":
    main()
