#!/usr/bin/env python3
from __future__ import annotations

from rules_measurement import check_evaluate_when_selected
from rules_review_semantics import check_master_nominal_actual


RULE_019 = {
    "rule_id": "VG-MEAS-019",
    "severity": "P1",
    "title": "MasterSet Probe NominalSize 与 Measurement Nominal 一致",
    "sources": [{"reference": "Kevin 追加规则"}],
    "fail_condition": "MasterSet Probe NominalSize 与 Measurement Nominal 不一致",
}
RULE_022 = {
    "rule_id": "VG-MEAS-022",
    "severity": "P1",
    "title": "EvaluateWhenSelected 必须为 False",
    "sources": [{"reference": "Kevin 追加规则"}],
    "fail_condition": "EvaluateWhenSelected 有效值为 True",
}


def measurement(
    name: str,
    value: bool | None,
    *,
    measurement_type: str = "Double",
    nominal: float | None = None,
    probe_ids: list[int] | None = None,
) -> dict:
    raw = {"Type": measurement_type}
    if value is not None:
        raw["EvaluateWhenSelected"] = str(value)
    return {
        "name": name,
        "type": measurement_type,
        "evaluate_when_selected": value,
        "effective_evaluate_when_selected": True if value is None else value,
        "nominal": nominal,
        "bound_probe_ids": probe_ids or [],
        "raw_attributes": raw,
    }


def master_probe(probe_id: int, nominal: float, actual: float) -> dict:
    return {
        "id": probe_id,
        "nominal_size": nominal,
        "actual_size": actual,
    }


def master_facts(probe: dict, measurements: list[dict], mastered: list[dict]) -> dict:
    return {
        "probes": [probe],
        "measurements": measurements,
        "master_sets": [{
            "name": "MasterSet1",
            "masters": [{"name": "Master1", "probes": mastered}],
        }],
    }


def test_meas_022() -> None:
    for measurement_type, value in (("DateTime", None), ("Date", True), ("Time", True), ("String", None), ("String", True)):
        exempt = check_evaluate_when_selected(
            {
                "measurements": [
                    measurement(
                        f"M_{measurement_type}",
                        value,
                        measurement_type=measurement_type,
                    )
                ]
            },
            RULE_022,
            {},
        )
        assert exempt["status"] == "PASS", exempt
        assert exempt["evidence"] == [], exempt

    explicit_false = check_evaluate_when_selected(
        {"measurements": [measurement("M1", False)]}, RULE_022, {}
    )
    assert explicit_false["status"] == "PASS", explicit_false

    explicit_true = check_evaluate_when_selected(
        {"measurements": [measurement("M1", True)]}, RULE_022, {}
    )
    assert explicit_true["status"] == "FAIL", explicit_true

    omitted_defaults_true = check_evaluate_when_selected(
        {"measurements": [measurement("M1", None)]}, RULE_022, {}
    )
    assert omitted_defaults_true["status"] == "FAIL", omitted_defaults_true
    assert omitted_defaults_true["evidence"][0]["effective_evaluate_when_selected"] is True
    assert omitted_defaults_true["evidence"][0]["raw_value"] is None

    approved_exception = check_evaluate_when_selected(
        {"measurements": [measurement("M1", None)]},
        RULE_022,
        {"rule_exceptions": {"VG-MEAS-022": "approved function evidence"}},
    )
    assert approved_exception["status"] == "PASS", approved_exception


def test_meas_019() -> None:
    single_point_zero = master_facts(
        {"id": 1, "name": "p1", "dependency_ids": []},
        [measurement("M1", False, nominal=25.0, probe_ids=[1])],
        [master_probe(1, 0.0, 0.0)],
    )
    exempt = check_master_nominal_actual(single_point_zero, RULE_019, {})
    assert exempt["status"] == "PASS", exempt

    composite = {
        "id": 69,
        "name": "p21n22",
        "text": "内径组合探头",
        "dependency_ids": [21, 22],
    }
    matching = master_facts(
        composite,
        [measurement("M1", False, nominal=386.905, probe_ids=[69])],
        [master_probe(69, 386.905, 386.91)],
    )
    matched = check_master_nominal_actual(matching, RULE_019, {})
    assert matched["status"] == "PASS", matched

    mismatching = master_facts(
        composite,
        [measurement("M1", False, nominal=386.905, probe_ids=[69])],
        [master_probe(69, 0.0, 0.0)],
    )
    mismatch = check_master_nominal_actual(mismatching, RULE_019, {})
    assert mismatch["status"] == "FAIL", mismatch
    assert mismatch["evidence"][0]["expected_nominal"] == 386.905
    assert mismatch["evidence"][0]["actual_nominal_size"] == 0.0
    assert mismatch["evidence"][0]["probe_name"] == "p21n22"
    assert mismatch["evidence"][0]["probe_text"] == "内径组合探头"

    no_measurement_nominal = master_facts(
        composite,
        [measurement("M1", False, nominal=None, probe_ids=[69])],
        [master_probe(69, 0.0, 0.0)],
    )
    not_judged = check_master_nominal_actual(no_measurement_nominal, RULE_019, {})
    assert not_judged["status"] == "PASS", not_judged

    conflicting = master_facts(
        composite,
        [
            measurement("M1", False, nominal=10.0, probe_ids=[69]),
            measurement("M2", False, nominal=20.0, probe_ids=[69]),
        ],
        [master_probe(69, 10.0, 10.1)],
    )
    conflict = check_master_nominal_actual(conflicting, RULE_019, {})
    assert conflict["status"] == "MANUAL_VERIFY", conflict
    assert conflict["evidence"][0]["measurement_nominals"] == [10.0, 20.0]
    assert conflict["evidence"][0]["probe_name"] == "p21n22"
    assert conflict["evidence"][0]["probe_text"] == "内径组合探头"


def main() -> None:
    test_meas_022()
    test_meas_019()
    print("VG-MEAS-019 / VG-MEAS-022 regression tests passed")


if __name__ == "__main__":
    main()
