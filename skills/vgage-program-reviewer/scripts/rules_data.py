from __future__ import annotations

import re
from pathlib import PureWindowsPath
from typing import Any

from rules_structure import result


MES_WRITE = re.compile(
    r"\bMES\b|\b(?:Upload|Send|Write|Post|Submit|Save)\w*MES\w*\b|"
    r"\bMES(?:Upload|Send|Write|Result|Data|Client|Service|Api)\w*\b|"
    r"\bHttpClient\b|\bWebClient\b|\bHttpWebRequest\b|"
    r"\bSqlConnection\b|\bOdbcConnection\b|\bOleDbConnection\b|"
    r"\.PostAsync\b|\.PutAsync\b|\.ExecuteNonQuery\b|\bWeb\s*API\b",
    re.I,
)
FAILURE_HANDLING = re.compile(r"\bTry\b[\s\S]*?\bCatch\b", re.I)
RETRY_OR_CACHE = re.compile(r"\bRetry\w*\b|\bCache\w*\b|缓存|重试|\bQueue\w*\b|\bSpool\w*\b", re.I)
COMPLETION_STATE = re.compile(
    r"\b[A-Za-z_]\w*(?:Complete|Completed|Done|Success)[A-Za-z_0-9]*\s*=\s*True\b",
    re.I,
)
MARKING_CODE = re.compile(
    r"\b[A-Za-z_]*(?:Marking|MarkCode|MarkerPattern|HansLaser)[A-Za-z_0-9]*\b|"
    r"\bLaserMark\w*\b|\bDotPeen\w*\b|\bEngrav\w*\b|打标|镭雕|刻印|激光打码|点针",
    re.I,
)
ANTI_DUPLICATE = re.compile(r"\b(?:Is)?Duplicate\w*\b|\bRepeat(?:Code)?\w*\b|\bAlreadyExists\w*\b|防重|重码|重复码", re.I)
ANTI_DUPLICATE_BYPASS = re.compile(
    r"\b(?:Duplicate|Repeat|AntiDuplicate)\w*(?:Pass|Passed|OK|Valid)\w*\s*=\s*True\b|"
    r"\b(?:IsDuplicate|DuplicateFound|RepeatFound)\w*\s*=\s*False\b|"
    r"\bAllow\w*Mark\w*(?:\.Value)?\s*=\s*True\b",
    re.I,
)


def without_vb_comments(code: str) -> str:
    return "\n".join(line.split("'", 1)[0] for line in code.splitlines())


def code_source_matches(facts: dict[str, Any], pattern: re.Pattern[str]) -> list[dict[str, Any]]:
    return [
        source
        for source in facts.get("code_sources", [])
        if pattern.search(without_vb_comments(str(source.get("code") or "")))
    ]


def check_external_write_resilience(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    sources = code_source_matches(facts, MES_WRITE)
    if not sources:
        return result(rule, "NOT_APPLICABLE", [], "未发现 MES、数据库或 Web API 写入代码")
    project_code = "\n".join(
        without_vb_comments(str(source.get("code") or ""))
        for source in facts.get("code_sources", [])
    )
    missing = []
    if not FAILURE_HANDLING.search(project_code):
        missing.append("failure_handling")
    if not RETRY_OR_CACHE.search(project_code):
        missing.append("retry_or_cache")
    if not COMPLETION_STATE.search(project_code):
        missing.append("completion_state")
    evidence = [
        {
            "file": source.get("file"),
            "surface": source.get("surface"),
            "object": source.get("object"),
            "missing_guards": missing,
        }
        for source in sources
    ]
    return result(rule, "FAIL" if missing else "PASS", evidence)


def check_marking_anti_duplicate(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    sources = code_source_matches(facts, MARKING_CODE)
    if not sources:
        return result(rule, "NOT_APPLICABLE", [], "未发现打标相关代码")
    project_code = "\n".join(
        without_vb_comments(str(source.get("code") or ""))
        for source in facts.get("code_sources", [])
    )
    bypass = ANTI_DUPLICATE_BYPASS.search(project_code)
    if bypass:
        source = next(source for source in sources if bypass.group(0) in str(source.get("code") or "")) if any(
            bypass.group(0) in str(source.get("code") or "") for source in sources
        ) else sources[0]
        return result(
            rule,
            "FAIL",
            [{
                "file": source.get("file"),
                "surface": source.get("surface"),
                "object": source.get("object"),
                "snippet": bypass.group(0),
                "reason": "anti_duplicate_hardcoded_pass",
            }],
        )
    if not ANTI_DUPLICATE.search(project_code):
        return result(
            rule,
            "FAIL",
            [{
                "file": sources[0].get("file"),
                "surface": sources[0].get("surface"),
                "object": sources[0].get("object"),
                "reason": "anti_duplicate_check_missing",
            }],
        )
    return result(
        rule,
        "PASS",
        [{
            "file": sources[0].get("file"),
            "surface": sources[0].get("surface"),
            "object": sources[0].get("object"),
            "reason": "anti_duplicate_check_found",
        }],
    )


def check_required_vga_fields(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    required = ("SerialNumber", "SalesOrder", "Customer", "EndUser", "CreatedBy")
    missing = [name for name in required if not str(facts.get("vga", {}).get(name) or "").strip()]
    evidence = [{"object": "VGA", "missing_fields": missing}] if missing else []
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_domestic_encoding(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    region = context.get("project_region", "unknown")
    if region == "unknown":
        return result(rule, "MANUAL_VERIFY", [{"object": "project_region", "reason": "人工确认国内或海外项目"}])
    if region == "overseas":
        return result(rule, "PASS", [])
    encoding = str(facts.get("vga", {}).get("Encoding") or "").strip()
    evidence = [] if encoding.upper() == "GB2312" else [{"object": "VGA.Encoding", "actual": encoding}]
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_part_text(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    evidence = [
        {"file": "VGA.xml", "object": part.get("name"), "missing_fields": ["Text"]}
        for part in facts.get("parts", [])
        if not str(part.get("text") or "").strip()
    ]
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_auto_archive_path(facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    del context
    raw = str(facts.get("auto_archive", {}).get("network_folder") or "").strip()
    invalid = not raw
    if raw:
        path = PureWindowsPath(raw)
        invalid = path.drive.upper() == "C:"
    evidence = [{"object": "Auto-Archive.Network folder", "actual": raw}] if invalid else []
    if invalid:
        return result(rule, "FAIL", evidence)
    return result(rule, "PASS", [{"object": "Auto-Archive.Network folder", "actual": raw, "manual": "confirm folder exists"}])
