from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


RULE_STATUSES = {
    "PASS",
    "FAIL",
    "MANUAL_VERIFY",
    "NOT_ASSESSABLE",
    "NOT_APPLICABLE",
}
SEVERITIES = {"P0", "P1", "P2", "P3", "INFO"}
EXECUTION_STATES = {"COMPLETE", "INCOMPLETE"}
OVERALL_STATUSES = {
    "BLOCKED",
    "RECTIFICATION_REQUIRED",
    "STATIC_PASSED_MANUAL_PENDING",
    "STATIC_REVIEW_PASSED",
}
MANUAL_EVIDENCE_FIELDS = {"reason", "missing_evidence", "manual_action"}


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    status: str
    severity: str
    title: str
    sources: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    impact: str
    recommendation: str
    exception_reason: str | None = None


@dataclass
class ReviewResult:
    execution_state: str
    overall_status: str | None
    project: dict[str, Any]
    rule_package: dict[str, Any]
    rules: list[RuleResult] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def validate_review(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"execution_state", "overall_status", "project", "rule_package", "rules", "errors"}
    for key in sorted(required - set(data)):
        errors.append(f"missing required field: {key}")

    execution_state = data.get("execution_state")
    if execution_state not in EXECUTION_STATES:
        errors.append(f"invalid execution_state: {execution_state}")

    overall_status = data.get("overall_status")
    if overall_status is not None and overall_status not in OVERALL_STATUSES:
        errors.append(f"invalid overall_status: {overall_status}")
    if execution_state == "INCOMPLETE" and overall_status in {
        "STATIC_PASSED_MANUAL_PENDING",
        "STATIC_REVIEW_PASSED",
    }:
        errors.append("INCOMPLETE review cannot have a static-pass status")

    rules = data.get("rules", [])
    if not isinstance(rules, list):
        return errors + ["rules must be an array"]

    seen: set[str] = set()
    required_rule_fields = {
        "rule_id",
        "status",
        "severity",
        "title",
        "sources",
        "evidence",
        "impact",
        "recommendation",
    }
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"rules[{index}] must be an object")
            continue
        for key in sorted(required_rule_fields - set(rule)):
            errors.append(f"rules[{index}] missing field: {key}")
        rule_id = rule.get("rule_id")
        if rule_id in seen:
            errors.append(f"duplicate rule_id: {rule_id}")
        elif isinstance(rule_id, str):
            seen.add(rule_id)
        if rule.get("status") not in RULE_STATUSES:
            errors.append(f"rules[{index}] invalid status: {rule.get('status')}")
        if rule.get("severity") not in SEVERITIES:
            errors.append(f"rules[{index}] invalid severity: {rule.get('severity')}")
        if rule.get("status") == "NOT_APPLICABLE" and not rule.get("exception_reason"):
            errors.append(f"rules[{index}] NOT_APPLICABLE requires exception_reason")
        if execution_state == "COMPLETE" and rule.get("status") == "NOT_ASSESSABLE":
            errors.append(
                f"rules[{index}] COMPLETE review cannot contain NOT_ASSESSABLE: {rule_id}"
            )
        if rule.get("status") == "MANUAL_VERIFY":
            evidence = rule.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"rules[{index}] MANUAL_VERIFY evidence must not be empty")
                continue
            for evidence_index, item in enumerate(evidence):
                if not isinstance(item, dict):
                    errors.append(
                        f"rules[{index}] MANUAL_VERIFY evidence[{evidence_index}] must be an object"
                    )
                    continue
                if not str(item.get("file") or "").strip() and not str(item.get("object") or "").strip():
                    errors.append(
                        f"rules[{index}] MANUAL_VERIFY evidence[{evidence_index}] requires file or object"
                    )
                for field in sorted(MANUAL_EVIDENCE_FIELDS):
                    if not str(item.get(field) or "").strip():
                        errors.append(
                            f"rules[{index}] MANUAL_VERIFY evidence[{evidence_index}] requires {field}"
                        )
    return errors
