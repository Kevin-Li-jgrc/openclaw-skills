#!/usr/bin/env python3
from __future__ import annotations

from rules_data import check_part_text


RULE = {
    "rule_id": "VG-STR-016",
    "severity": "P2",
    "title": "Part Text 必须填写实际工件名称，并与项目证据一致",
    "sources": [{"reference": "Kevin 追加规则"}],
    "fail_condition": "Part Text 缺失",
}


def main() -> None:
    text_present = check_part_text(
        {"parts": [{"name": "Part1", "text": "4K Front Support 29512739", "description": None}]},
        RULE,
        {},
    )
    assert text_present["status"] == "PASS", text_present

    text_missing = check_part_text(
        {"parts": [{"name": "Part1", "text": "   ", "description": "旧 Description 仍有值"}]},
        RULE,
        {},
    )
    assert text_missing["status"] == "FAIL", text_missing
    assert text_missing["evidence"] == [
        {"file": "VGA.xml", "object": "Part1", "missing_fields": ["Text"]}
    ], text_missing

    print("VG-STR-016 Part Text regression tests passed")


if __name__ == "__main__":
    main()
