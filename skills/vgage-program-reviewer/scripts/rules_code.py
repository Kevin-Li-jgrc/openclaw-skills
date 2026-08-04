from __future__ import annotations

import re
from typing import Any

from rules_structure import result


WRAPPER = re.compile(r"^\s*(?:Public\s+|Private\s+|Friend\s+)?(?:Module|Namespace)\b", re.I | re.M)
OFFECT = re.compile(r"\bOffect\b", re.I)
PROCEDURE = re.compile(
    r"^\s*(?:(?:Public|Private|Friend|Protected|Shared|Overrides|Overloads)\s+)*"
    r"(Sub|Function)\s+([A-Za-z_][A-Za-z0-9_]*)\b([^\r\n]*)\r?\n"
    r"(.*?)^\s*End\s+\1\b",
    re.I | re.M | re.S,
)
CALL_LINE = re.compile(r"^\s*(?:Call\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(\s*\))?\s*$", re.I)
CALIBRATION_WRITE = re.compile(r"SetValueAsDateTime\s*\(\s*[\"'][^\"']*Calibration[^\"']*[\"']", re.I)
NOW_PLUS_PERIOD = re.compile(r"(?:DateTime\.)?(?:Now|Today)\s*\.\s*Add(?:Days|Months|Years)\s*\(", re.I)
DATE_ASSIGNMENT = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\b[^\r\n=]*=\s*"
    r"(?:DateTime\.)?(?:Now|Today)\s*\.\s*Add(?:Days|Months|Years)\s*\(",
    re.I,
)
PERIODIC_SURFACE = re.compile(r"AfterUpdate|AfterEvaluate|(?:Form|_)?Refresh", re.I)
SLOW_IO = re.compile(
    r"Thread(?:ing)?\.Thread\.Sleep|\bThread\.Sleep|\bHttpClient\b|\bWebClient\b|"
    r"\bHttpWebRequest\b|\bSqlConnection\b|\bOdbcConnection\b|\bOleDbConnection\b|"
    r"\bStream(?:Reader|Writer)\b|\bFile\.(?:Read|Write|Append|Open)|"
    r"\bDirectory\.|\.ExecuteNonQuery\b|\.Download(?:String|Data)\b|\.Upload(?:String|Data|File)\b",
    re.I,
)
EVENT_REGISTRATION = re.compile(r"\bAddHandler\b", re.I)
COLLECTION_GROWTH = re.compile(r"\.\s*(?:Add|Enqueue)\s*\(", re.I)
COLLECTION_BOUND = re.compile(r"\.\s*(?:Clear|Remove|RemoveAt|Dequeue)\s*\(|\b(?:Count|Capacity)\b", re.I)
REPEATED_CYCLE_ACTION = re.compile(r"\.\s*(?:Evaluate|AfterEvaluate|AfterUpdate|Refresh)\s*\(", re.I)
NUMERIC_LITERAL = r"(?<![A-Za-z_])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?![A-Za-z_])"


def source_blocks(source: dict[str, Any]) -> list[dict[str, Any]]:
    code = str(source.get("code") or "")
    blocks: list[dict[str, Any]] = []
    for match in PROCEDURE.finditer(code):
        blocks.append(
            {
                "file": source.get("file"),
                "surface": source.get("surface"),
                "object": source.get("object"),
                "name": match.group(2),
                "header": match.group(0).splitlines()[0],
                "body": match.group(4),
                "body_start_line": code[: match.start(4)].count("\n") + 1,
            }
        )
    if not blocks and code.strip():
        blocks.append(
            {
                "file": source.get("file"),
                "surface": source.get("surface"),
                "object": source.get("object"),
                "name": str(source.get("object") or source.get("surface") or "code"),
                "header": "",
                "body": code,
                "body_start_line": 1,
            }
        )
    return blocks


def check_bestfit_hardcoded_recalc(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    bestfit_names = [
        str(feature.get("name") or "").strip()
        for feature in facts.get("features", [])
        if str(feature.get("type") or "").casefold().startswith("bestfit")
        and str(feature.get("name") or "").strip()
    ]
    mutations: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for source in facts.get("code_sources", []):
        for block in source_blocks(source):
            pending: dict[str, dict[str, Any]] = {}
            for offset, raw_line in enumerate(str(block["body"]).splitlines()):
                line_number = block["body_start_line"] + offset
                line = raw_line.split("'", 1)[0]
                for name in bestfit_names:
                    escaped = re.escape(name)
                    literal_assignment = re.search(
                        rf"\b{escaped}\.(?:Offset|Correlation)\.(?:X|Y|Z)\s*=\s*{NUMERIC_LITERAL}\b",
                        line,
                        re.I,
                    )
                    literal_point = re.search(
                        rf"\b{escaped}\.AddPoint\s*\(\s*(?:New\s+Point\s*\()?[^\r\n)]*{NUMERIC_LITERAL}",
                        line,
                        re.I,
                    )
                    if literal_assignment or literal_point:
                        item = {
                            "file": block["file"],
                            "surface": block["surface"],
                            "object": name,
                            "procedure": block["name"],
                            "line": line_number,
                            "snippet": raw_line.strip(),
                        }
                        mutations.append(item)
                        pending[name.casefold()] = item
                    if re.search(rf"\b{escaped}\.Recalc\s*\(", line, re.I):
                        pending.pop(name.casefold(), None)
                    if pending.get(name.casefold()) and re.search(
                        rf"\b{escaped}\.(?:Center|Radius|Diameter)\b", line, re.I
                    ):
                        failures.append(
                            {
                                "file": block["file"],
                                "surface": block["surface"],
                                "object": name,
                                "procedure": block["name"],
                                "line": line_number,
                                "snippet": raw_line.strip(),
                                "reason": "bestfit_result_read_before_recalc",
                                "mutation_line": pending[name.casefold()]["line"],
                            }
                        )
                        pending.pop(name.casefold(), None)
            for name, mutation in pending.items():
                failures.append(
                    {
                        **mutation,
                        "object": mutation.get("object") or name,
                        "reason": "bestfit_hardcoded_mutation_without_recalc",
                    }
                )
    if not mutations:
        return result(rule, "NOT_APPLICABLE", [], "未发现使用数值字面量的 BestFit 硬编码拟合")
    return result(rule, "FAIL" if failures else "PASS", failures or mutations)


def check_periodic_code_risks(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    evidence: list[dict[str, Any]] = []
    for source in facts.get("code_sources", []):
        for block in source_blocks(source):
            if not PERIODIC_SURFACE.search(f"{block['name']} {block['header']}"):
                continue
            body = str(block["body"])
            has_bound = COLLECTION_BOUND.search(body) is not None
            recursion = re.compile(rf"\b{re.escape(str(block['name']))}\s*\(", re.I)
            for offset, raw_line in enumerate(body.splitlines()):
                line = raw_line.split("'", 1)[0]
                reason = None
                if SLOW_IO.search(line):
                    reason = "slow_io_in_periodic_handler"
                elif EVENT_REGISTRATION.search(line):
                    reason = "event_registration_in_periodic_handler"
                elif COLLECTION_GROWTH.search(line) and not has_bound:
                    reason = "unbounded_collection_growth"
                elif recursion.search(line):
                    reason = "direct_recursion_in_periodic_handler"
                elif REPEATED_CYCLE_ACTION.search(line):
                    reason = "recursive_cycle_action_in_periodic_handler"
                if reason:
                    evidence.append(
                        {
                            "file": block["file"],
                            "surface": block["surface"],
                            "object": block["object"],
                            "procedure": block["name"],
                            "line": block["body_start_line"] + offset,
                            "snippet": raw_line.strip(),
                            "reason": reason,
                        }
                    )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_code_module_format(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    module = facts.get("code_module", {})
    evidence: list[dict[str, Any]] = []
    if not module:
        evidence.append({"file": "CodeModule.vgs", "reason": "missing"})
    else:
        for field, reason in (
            ("has_utf8_bom", "missing_utf8_bom"),
            ("utf8_decodable", "not_utf8_decodable"),
        ):
            if module.get(field) is not True:
                evidence.append({"file": module.get("relative_path"), "reason": reason})
        if module.get("has_bare_lf") or module.get("has_bare_cr"):
            evidence.append({"file": module.get("relative_path"), "reason": "not_crlf_only"})
        wrapper = WRAPPER.search(str(module.get("code") or ""))
        if wrapper:
            evidence.append(
                {
                    "file": module.get("relative_path"),
                    "reason": "module_or_namespace_wrapper",
                    "snippet": wrapper.group(0).strip(),
                }
            )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def check_offect_api(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    evidence: list[dict[str, Any]] = []
    for source in facts.get("code_sources", []):
        for line_number, line in enumerate(str(source.get("code") or "").splitlines(), 1):
            if OFFECT.search(line):
                evidence.append(
                    {
                        "file": source.get("file"),
                        "surface": source.get("surface"),
                        "object": source.get("object"),
                        "line": line_number,
                        "snippet": line.strip(),
                    }
                )
    return result(rule, "FAIL" if evidence else "PASS", evidence)


def procedure_map(code: str) -> dict[str, dict[str, str]]:
    return {
        match.group(2).casefold(): {
            "kind": match.group(1),
            "name": match.group(2),
            "header": match.group(3),
            "body": match.group(4),
        }
        for match in PROCEDURE.finditer(code)
    }


def unconditional_calls(body: str) -> set[str]:
    calls: set[str] = set()
    if_depth = 0
    for raw_line in body.splitlines():
        line = raw_line.split("'", 1)[0].strip()
        if not line:
            continue
        if re.match(r"^End\s+If\b", line, re.I):
            if_depth = max(0, if_depth - 1)
            continue
        match = CALL_LINE.fullmatch(line)
        if match and if_depth == 0:
            calls.add(match.group(1).casefold())
        if re.match(r"^If\b.*\bThen\s*$", line, re.I):
            if_depth += 1
    return calls


def resets_calibration_due_date(body: str) -> bool:
    if not CALIBRATION_WRITE.search(body):
        return False
    if NOW_PLUS_PERIOD.search(body):
        return True
    assigned = {match.casefold() for match in DATE_ASSIGNMENT.findall(body)}
    return any(
        re.search(
            rf"SetValueAsDateTime\s*\([^\r\n]*\b{re.escape(name)}\b",
            body,
            re.I,
        )
        for name in assigned
    )


def check_calibration_due_reset(
    facts: dict[str, Any], rule: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    del context
    module = facts.get("code_module", {})
    code = str(module.get("code") or "")
    procedures = procedure_map(code)
    initializers = [
        item
        for item in procedures.values()
        if item["name"].casefold() == "vga_initialize"
        or re.search(r"\bHandles\s+VGA\.Initialize\b", item["header"], re.I)
    ]
    evidence: list[dict[str, Any]] = []
    for initializer in initializers:
        candidates = {initializer["name"].casefold()} | unconditional_calls(initializer["body"])
        for candidate in sorted(candidates):
            procedure = procedures.get(candidate)
            if procedure and resets_calibration_due_date(procedure["body"]):
                evidence.append(
                    {
                        "file": module.get("relative_path", "CodeModule.vgs"),
                        "called_from": initializer["name"],
                        "procedure": procedure["name"],
                        "reason": "unconditional_due_date_reset_on_initialize",
                    }
                )
    return result(rule, "FAIL" if evidence else "PASS", evidence)
