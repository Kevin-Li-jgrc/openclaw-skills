#!/usr/bin/env python3
from __future__ import annotations

from rules_measurement import check_string_datetime_not_empty


RULE_025 = {
    "rule_id": "VG-MEAS-025",
    "severity": "P1",
    "title": "启用的 String/DateTime/Date/Time Measurement 的 Equation 与 Text 必须非空",
    "sources": [{"reference": "Kevin 追加规则"}],
    "fail_condition": "Equation 或 Text 缺失/为空",
}


def measurement(
    name: str,
    *,
    measurement_type: str = "String",
    equation: str | None = "Function X() As String\nReturn A.Value\nEnd Function",
    text: str | None = "SerialNumber",
    active: bool = True,
) -> dict:
    raw: dict = {"Type": measurement_type}
    if not active:
        raw["Active"] = "False"
    return {
        "name": name,
        "type": measurement_type,
        "equation": equation,
        "text": text,
        "raw_attributes": raw,
    }


def test_meas_025() -> None:
    non_empty = check_string_datetime_not_empty(
        {"measurements": [measurement("M1000")]}, RULE_025, {}
    )
    assert non_empty["status"] == "PASS", non_empty

    for measurement_type in ("DateTime", "Date", "Time", "String"):
        ok = check_string_datetime_not_empty(
            {"measurements": [measurement(f"M_{measurement_type}", measurement_type=measurement_type)]},
            RULE_025,
            {},
        )
        assert ok["status"] == "PASS", ok

    empty_equation = check_string_datetime_not_empty(
        {"measurements": [measurement("M2000", equation="")]}, RULE_025, {}
    )
    assert empty_equation["status"] == "FAIL", empty_equation
    assert empty_equation["evidence"][0]["missing_fields"] == ["Equation"]

    missing_text = check_string_datetime_not_empty(
        {"measurements": [measurement("M2001", text=None)]}, RULE_025, {}
    )
    assert missing_text["status"] == "FAIL", missing_text
    assert missing_text["evidence"][0]["missing_fields"] == ["Text"]

    both_missing = check_string_datetime_not_empty(
        {"measurements": [measurement("M2002", equation="   ", text="")]}, RULE_025, {}
    )
    assert both_missing["status"] == "FAIL", both_missing
    assert both_missing["evidence"][0]["missing_fields"] == ["Equation", "Text"]

    double_unaffected = check_string_datetime_not_empty(
        {"measurements": [measurement("M3000", measurement_type="Double", equation="Function X() As Double\nReturn p1.Value\nEnd Function", text=None)]},
        RULE_025,
        {},
    )
    assert double_unaffected["status"] == "PASS", double_unaffected
    assert double_unaffected["evidence"] == []

    disabled_exempt = check_string_datetime_not_empty(
        {"measurements": [measurement("M2003", equation="", text="", active=False)]},
        RULE_025,
        {},
    )
    assert disabled_exempt["status"] == "PASS", disabled_exempt


def main() -> None:
    test_meas_025()
    print("VG-MEAS-025 regression tests passed")


if __name__ == "__main__":
    main()
