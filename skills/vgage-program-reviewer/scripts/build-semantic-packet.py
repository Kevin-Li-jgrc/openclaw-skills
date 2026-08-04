from __future__ import annotations

from typing import Any


MAX_SNIPPET = 2000


def build_semantic_packet(facts: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    rules = [
        {
            "rule_id": rule["rule_id"],
            "title": rule["title"],
            "severity": rule["severity"],
            "execution": rule["execution"],
            "sources": rule["sources"],
            "pass_condition": rule["pass_condition"],
            "fail_condition": rule["fail_condition"],
        }
        for rule in catalog["rules"]
        if rule["execution"] in {"semantic", "hybrid"}
    ]
    evidence = []
    for script in facts.get("scripts", []):
        evidence.append(
            {
                "relative_path": script.get("relative_path"),
                "snippet": str(script.get("snippet") or "")[:MAX_SNIPPET],
            }
        )
    return {
        "contract": {
            "required": [
                "rule_id",
                "status",
                "evidence",
                "violated_standard",
                "explanation",
            ],
            "fail_requires_concrete_evidence": True,
            "field_semantics_must_be_manual": True,
        },
        "rules": rules,
        "evidence": evidence,
        "parse_errors": facts.get("parse_errors", []),
    }
