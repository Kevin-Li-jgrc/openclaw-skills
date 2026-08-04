#!/usr/bin/env python3
from __future__ import annotations

from rules_measurement import check_masterset_text


RULE = {
    "rule_id": "VG-MEAS-016",
    "severity": "P2",
    "title": "MasterSet Text 必须填写实际校准件类型，如 Max/Min Mastering",
    "sources": [{"reference": "Kevin 追加规则"}],
    "fail_condition": "MasterSet Text 缺失",
}


def main() -> None:
    text_present = check_masterset_text(
        {
            "master_sets": [
                {
                    "name": "MasterSet1",
                    "text": "VG12047 Mean Master",
                    "description": None,
                }
            ]
        },
        RULE,
        {},
    )
    assert text_present["status"] == "PASS", text_present

    text_missing = check_masterset_text(
        {
            "master_sets": [
                {
                    "name": "MasterSet1",
                    "text": "   ",
                    "description": "旧 Description 仍有值",
                }
            ]
        },
        RULE,
        {},
    )
    assert text_missing["status"] == "FAIL", text_missing
    assert text_missing["evidence"] == [
        {"file": "VGA.xml", "object": "MasterSet1", "missing_fields": ["Text"]}
    ], text_missing

    print("VG-MEAS-016 MasterSet Text regression tests passed")


if __name__ == "__main__":
    main()
