from __future__ import annotations

from typing import Any


def calculate_overall_status(results: list[dict[str, Any]], execution_state: str) -> str | None:
    if execution_state != "COMPLETE":
        return None
    if any(item.get("status") == "FAIL" and item.get("severity") in {"P0", "P1"} for item in results):
        return "BLOCKED"
    if any(item.get("status") == "FAIL" and item.get("severity") == "P2" for item in results):
        return "RECTIFICATION_REQUIRED"
    if any(item.get("status") in {"MANUAL_VERIFY", "NOT_ASSESSABLE"} for item in results):
        return "STATIC_PASSED_MANUAL_PENDING"
    return "STATIC_REVIEW_PASSED"


def valid_semantic_finding(finding: dict[str, Any], known_ids: set[str]) -> bool:
    if finding.get("rule_id") not in known_ids:
        return False
    if finding.get("status") not in {"PASS", "FAIL", "MANUAL_VERIFY", "NOT_ASSESSABLE", "NOT_APPLICABLE"}:
        return False
    if finding.get("status") == "FAIL":
        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            return False
        if not all(isinstance(item, dict) and (item.get("file") or item.get("object")) for item in evidence):
            return False
        if not str(finding.get("violated_standard") or "").strip():
            return False
        if not str(finding.get("explanation") or "").strip():
            return False
    if finding.get("status") == "NOT_APPLICABLE" and not finding.get("exception_reason"):
        return False
    return True


def normalize(rule: dict[str, Any], status: str, evidence: list[dict[str, Any]], recommendation: str = "") -> dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "status": status,
        "severity": rule["severity"],
        "title": rule["title"],
        "sources": rule["sources"],
        "evidence": evidence,
        "impact": rule["fail_condition"] if status == "FAIL" else "",
        "recommendation": recommendation,
    }


def merge_results(
    deterministic_results: list[dict[str, Any]],
    semantic_findings: list[dict[str, Any]],
    catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    rules = catalog["rules"]
    by_rule = {rule["rule_id"]: rule for rule in rules}
    known_ids = set(by_rule)
    deterministic = {item["rule_id"]: item for item in deterministic_results if item.get("rule_id") in known_ids}
    semantic: dict[str, dict[str, Any]] = {}
    invalid_semantic_ids: set[str] = set()
    for finding in semantic_findings:
        rule_id = finding.get("rule_id")
        if valid_semantic_finding(finding, known_ids):
            semantic[rule_id] = finding
        elif rule_id in known_ids:
            invalid_semantic_ids.add(rule_id)

    merged: list[dict[str, Any]] = []
    for rule in rules:
        rule_id = rule["rule_id"]
        if rule_id in deterministic:
            merged.append(deterministic[rule_id])
            continue
        if rule_id in semantic:
            finding = semantic[rule_id]
            item = normalize(rule, finding["status"], finding.get("evidence", []), finding.get("recommendation", ""))
            if finding.get("exception_reason"):
                item["exception_reason"] = finding["exception_reason"]
            merged.append(item)
            continue
        if rule_id in invalid_semantic_ids:
            merged.append(normalize(rule, "NOT_ASSESSABLE", []))
            continue
        merged.append(normalize(rule, "NOT_ASSESSABLE", []))
    return merged
