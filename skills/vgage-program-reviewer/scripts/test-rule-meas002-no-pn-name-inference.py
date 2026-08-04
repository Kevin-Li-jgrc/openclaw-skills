#!/usr/bin/env python3
from __future__ import annotations

from rules_review_semantics import check_diameter_nominal_semantics


RULE = {
    "rule_id": "VG-MEAS-002",
    "severity": "P1",
    "title": "直径公式不得错误减去 Me.Nominal",
    "sources": [{"reference": "measurement rules"}],
    "fail_condition": "直径实际值公式错误减去 Me.Nominal",
}


def main() -> None:
    facts = {
        "probes": [{"name": "p1n2", "symbol": ""}],
        "measurements": [
            {
                "name": "M1",
                "symbol": "",
                "equation": "Return p1n2.Value - Me.Nominal",
                "equation_sources": ["p1n2"],
            }
        ],
    }
    checked = check_diameter_nominal_semantics(facts, RULE, {})
    assert checked["status"] == "NOT_APPLICABLE", checked
    print("VG-MEAS-002 pXnY name-only inference regression test passed")


if __name__ == "__main__":
    main()
