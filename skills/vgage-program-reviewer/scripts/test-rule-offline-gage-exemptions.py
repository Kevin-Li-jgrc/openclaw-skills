#!/usr/bin/env python3
from __future__ import annotations

from rules_dependencies import check_summary_measurement_rtg0
from rules_measurement import check_evaluate_when_selected


RULE_DEP_007 = {
    "rule_id": "VG-DEP-007",
    "severity": "P1",
    "title": "纯汇总 Measurement 使用 RTG0",
    "sources": [{"reference": "Kevin 追加规则"}],
    "fail_condition": "纯汇总 Measurement 未使用 RTG0",
}
RULE_MEAS_022 = {
    "rule_id": "VG-MEAS-022",
    "severity": "P1",
    "title": "EvaluateWhenSelected 必须为 False",
    "sources": [{"reference": "Kevin 追加规则"}],
    "fail_condition": "EvaluateWhenSelected 有效值为 True",
}


def evaluate_facts(gage_type: str | None, evaluate: bool = True) -> dict:
    facts = {
        "vga": {},
        "measurements": [{
            "name": "M_Result",
            "type": "Double",
            "evaluate_when_selected": evaluate,
            "effective_evaluate_when_selected": evaluate,
            "raw_attributes": {"EvaluateWhenSelected": str(evaluate)},
        }],
    }
    if gage_type is not None:
        facts["vga"]["GageType"] = gage_type
    return facts


def summary_facts(gage_type: str | None, ready_to_gage: int = 3) -> dict:
    facts = {
        "vga": {},
        "measurements": [
            {"id": 1, "name": "M_Source", "equation_sources": [], "ready_to_gage": 1},
            {
                "id": 2,
                "name": "M_Summary",
                "equation_sources": ["M_Source"],
                "ready_to_gage": ready_to_gage,
            },
        ],
    }
    if gage_type is not None:
        facts["vga"]["GageType"] = gage_type
    return facts


def test_offline_gage_exempts_both_rules() -> None:
    for gage_type in ("Offline", " offline ", "OFFLINE"):
        evaluate = check_evaluate_when_selected(
            evaluate_facts(gage_type), RULE_MEAS_022, {}
        )
        assert evaluate["status"] == "PASS", evaluate
        assert evaluate["evidence"][0]["reason"] == "offline_gage_exemption", evaluate

        summary = check_summary_measurement_rtg0(summary_facts(gage_type), RULE_DEP_007)
        assert summary["status"] == "PASS", summary
        assert summary["evidence"][0]["reason"] == "offline_gage_exemption", summary


def test_non_offline_gage_keeps_existing_checks() -> None:
    for gage_type in ("Inline", None, "Hybrid"):
        evaluate = check_evaluate_when_selected(
            evaluate_facts(gage_type), RULE_MEAS_022, {}
        )
        assert evaluate["status"] == "FAIL", (gage_type, evaluate)

        summary = check_summary_measurement_rtg0(summary_facts(gage_type), RULE_DEP_007)
        assert summary["status"] == "FAIL", (gage_type, summary)


def test_non_offline_valid_values_still_pass() -> None:
    evaluate = check_evaluate_when_selected(
        evaluate_facts("Inline", evaluate=False), RULE_MEAS_022, {}
    )
    assert evaluate["status"] == "PASS", evaluate

    summary = check_summary_measurement_rtg0(
        summary_facts("Inline", ready_to_gage=0), RULE_DEP_007
    )
    assert summary["status"] == "PASS", summary


def main() -> None:
    test_offline_gage_exempts_both_rules()
    test_non_offline_gage_keeps_existing_checks()
    test_non_offline_valid_values_still_pass()
    print("offline gage exemption regression tests passed")


if __name__ == "__main__":
    main()
