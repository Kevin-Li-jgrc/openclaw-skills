from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "report-template.html"

FIELD_LABELS = {
    "file": "文件",
    "object": "对象",
    "line": "行号",
    "reason": "判定原因",
    "missing_fields": "缺失字段",
    "equation": "公式 / 代码",
    "actual_symbol": "当前符号",
    "expected_symbol": "期望符号",
    "measurements": "关联检测项",
    "violated_standard": "违反标准",
    "explanation": "说明",
    "impact": "影响",
    "recommendation": "建议",
    "missing_evidence": "缺失证据",
    "manual_action": "人工操作",
    "property": "属性",
    "actual": "当前值",
    "expected": "期望值",
    "value": "值",
    "name": "名称",
    "text": "文本",
    "description": "说明",
    "fields": "字段",
    "objects": "对象列表",
    "required_files": "必需文件",
    "missing_required_files": "缺失必需文件",
    "missing_objects": "缺失对象",
    "missing_probe_ids": "缺失 Probe ID",
    "missing_probe_names": "缺失 Probe 名称",
    "missing_dependency_ids": "缺失依赖 ID",
    "extra_dependency_ids": "多余依赖 ID",
    "actual_dependency_ids": "当前依赖 ID",
    "expected_dependency_ids": "期望依赖 ID",
    "actual_probe_ids": "当前 Probe ID",
    "expected_probe_ids": "期望 Probe ID",
    "expected_symbols": "期望符号",
    "duplicate_ids": "重复 ID",
    "collisions": "名称冲突",
    "operation": "工序",
    "operation_id": "工序 ID",
    "feature_type": "Feature 类型",
    "encoder": "编码器",
    "angle_encoders": "角度编码器",
    "digits": "小数位数",
    "nominal": "名义值",
    "number_of_cycles_to_save": "保存周期数",
    "evaluate_when_selected": "选中时计算",
    "channel": "通道",
    "channel_index": "通道索引",
    "parsed_channel": "解析通道",
    "capacity": "容量",
    "module": "模块",
    "mapping": "映射",
    "probe": "Probe",
    "probe_name": "Probe 名称",
    "probe_text": "Probe 文本",
    "vga_tag": "VGA Tag",
    "bus_text": "总线文本",
    "serialized_name": "序列化名称",
    "target": "目标",
    "section": "区段",
    "procedure": "过程",
    "surface": "脚本面",
    "message": "消息",
}

SOURCE_LABELS = {
    "standard": "标准",
    "item": "条款",
    "reference": "依据",
    "skill": "规则源",
}

REASON_LABELS = {
    "computed_probe_symbol_conflicts_with_measurement_semantics": "公式 Probe 符号与 Measurement 检测语义冲突",
    "computed_probe_used_by_conflicting_measurement_semantics": "同一公式 Probe 被互相冲突的检测语义使用",
    "measurement_symbol_conflicts_with_explicit_name_or_text": "Measurement 符号与名称或文本中的明确检测语义冲突",
    "probe_symbol_conflicts_with_confirmed_name_convention": "Probe 符号与已确认的命名语义冲突",
    "missing": "缺失",
    "not_configured_as_pair": "未成对配置",
    "not_finite_numbers": "不是有效有限数值",
    "USL_less_than_LSL": "USL 小于 LSL",
    "invalid_script_identifier": "不是合法脚本标识符",
    "global_name_collision": "与全局对象重名",
    "declared_form_file_missing": "Screens 声明的 Form 文件缺失",
    "dangling_event_target": "事件目标悬空",
    "dangling_control_reference": "控件引用悬空",
    "bestfit_result_read_before_recalc": "BestFit 在 Recalc 前读取结果",
    "bestfit_hardcoded_mutation_without_recalc": "BestFit 硬编码修改后未执行 Recalc",
    "unconditional_due_date_reset_on_initialize": "初始化时无条件重置校准到期日",
    "anti_duplicate_hardcoded_pass": "防重码结果被硬编码放行",
    "anti_duplicate_check_missing": "缺少防重码检查",
}


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def overall_verdict(review: dict[str, Any]) -> tuple[str, str, str]:
    overall_status = review.get("overall_status")
    if review.get("execution_state") == "COMPLETE" and overall_status == "STATIC_REVIEW_PASSED":
        return "检查通过", "pass", "全部程序检查项通过"
    details = {
        "BLOCKED": "存在阻断项",
        "RECTIFICATION_REQUIRED": "存在需要整改的检查项",
        "STATIC_PASSED_MANUAL_PENDING": "仍有检查项待人工确认",
        "STATIC_REVIEW_PASSED": "执行状态异常，不能判定为通过",
    }
    return "检查不通过", "fail", details.get(overall_status, "检查未完整执行")


def render_meta(review: dict[str, Any]) -> str:
    project = review["project"]
    package = review["rule_package"]
    items = (
        ("项目", project.get("name")),
        ("路径", project.get("root")),
        ("项目指纹", project.get("fingerprint")),
        ("执行状态", review.get("execution_state")),
        ("规则版本", package.get("catalog_version")),
        ("规则生效日", package.get("effective_date")),
    )
    return "".join(f"<div><strong>{esc(label)}：</strong>{esc(value)}</div>" for label, value in items)


def field_label(key: str) -> str:
    return FIELD_LABELS.get(key, key.replace("_", " ").strip().title())


def render_scalar(key: str, value: Any) -> str:
    if value is None or value == "":
        return '<span class="empty-value">未填写</span>'
    if isinstance(value, bool):
        return esc("是" if value else "否")
    text = str(value)
    if key == "reason":
        translated = REASON_LABELS.get(text)
        if translated:
            return f'<span class="field-value">{esc(translated)}</span><code class="reason-code">{esc(text)}</code>'
        if "_" in text and " " not in text:
            return f'<code class="reason-code">{esc(text)}</code>'
    if key in {"equation", "code", "snippet"} or "\n" in text or "\r" in text:
        return f'<pre class="code-block"><code>{esc(text)}</code></pre>'
    return f'<span class="field-value">{esc(text)}</span>'


def render_value(key: str, value: Any) -> str:
    if isinstance(value, dict):
        rows = "".join(
            f'<div class="nested-field"><span>{esc(field_label(str(child_key)))}</span>{render_value(str(child_key), child_value)}</div>'
            for child_key, child_value in value.items()
        )
        return f'<div class="nested-fields">{rows}</div>'
    if isinstance(value, list):
        if not value:
            return '<span class="empty-value">无</span>'
        if all(not isinstance(item, (dict, list)) for item in value):
            return '<div class="chip-list">' + "".join(f'<span class="chip">{esc(item)}</span>' for item in value) + "</div>"
        return '<div class="nested-list">' + "".join(
            f'<div class="nested-item">{render_value(key, item)}</div>' for item in value
        ) + "</div>"
    return render_scalar(key, value)


def render_evidence(evidence: list[Any]) -> str:
    if not evidence:
        return '<div class="empty-evidence">本检查项未记录额外证据。</div>'
    cards = []
    for index, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            body = f'<div class="evidence-field evidence-field--wide">{render_value("value", item)}</div>'
        else:
            body = "".join(
                f'<div class="evidence-field{(" evidence-field--wide" if key in {"equation", "code", "snippet", "explanation", "reason", "manual_action", "missing_evidence"} else "")}">'
                f'<dt>{esc(field_label(str(key)))}</dt><dd>{render_value(str(key), value)}</dd></div>'
                for key, value in item.items()
            )
        cards.append(
            f'<article class="evidence-card"><div class="evidence-card-title">证据 {index}</div>'
            f'<dl class="evidence-grid">{body}</dl></article>'
        )
    return "".join(cards)


def render_sources(sources: list[Any]) -> str:
    if not sources:
        return '<span class="empty-value">未记录</span>'
    chips = []
    for source in sources:
        if isinstance(source, dict):
            parts = [f"{SOURCE_LABELS.get(str(key), str(key))}：{value}" for key, value in source.items()]
            chips.append(" · ".join(parts))
        else:
            chips.append(str(source))
    return '<div class="source-list">' + "".join(f'<span class="source-chip">{esc(item)}</span>' for item in chips) + "</div>"


def render_rule_detail(rule: dict[str, Any]) -> str:
    evidence = rule.get("evidence") or []
    sections = [
        '<section class="detail-section"><h3>证据</h3>' + render_evidence(evidence) + "</section>",
        '<section class="detail-section"><h3>规则来源</h3>' + render_sources(rule.get("sources") or []) + "</section>",
    ]
    if rule.get("impact"):
        sections.append(f'<section class="detail-section detail-section--impact"><h3>影响</h3><p>{esc(rule["impact"])}</p></section>')
    if rule.get("recommendation"):
        sections.append(f'<section class="detail-section detail-section--recommendation"><h3>建议</h3><p>{esc(rule["recommendation"])}</p></section>')
    open_attr = " open" if rule.get("status") == "FAIL" else ""
    count_label = f"证据 {len(evidence)} 项" if evidence else "无附加证据"
    return (
        f'<details class="rule-detail"{open_attr}><summary><span>查看详情</span>'
        f'<span class="detail-count">{esc(count_label)}</span></summary>'
        f'<div class="detail-body">{"".join(sections)}</div></details>'
    )


def render_rows(review: dict[str, Any]) -> str:
    rows = []
    for rule in review["rules"]:
        detail = render_rule_detail(rule)
        rows.append(
            f"<tr data-status=\"{esc(rule['status'])}\" data-severity=\"{esc(rule['severity'])}\">"
            f"<td>{esc(rule['rule_id'])}</td><td class=\"{esc(rule['severity'])}\">{esc(rule['severity'])}</td>"
            f"<td class=\"{esc(rule['status'])}\">{esc(rule['status'])}</td><td>{esc(rule['title'])}</td><td>{detail}</td></tr>"
        )
    return "".join(rows)


def render_html(review: dict[str, Any], output_path: Path) -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    statuses = sorted({rule["status"] for rule in review["rules"]})
    severities = [value for value in ("P0", "P1", "P2", "P3", "INFO") if any(rule["severity"] == value for rule in review["rules"])]
    verdict_label, verdict_tone, verdict_detail = overall_verdict(review)
    replacements = {
        "{{TITLE}}": esc(f"VGAGE 程序审查报告｜{review['project'].get('name', '')}"),
        "{{VERDICT_LABEL}}": esc(verdict_label),
        "{{VERDICT_TONE}}": esc(verdict_tone),
        "{{VERDICT_DETAIL}}": esc(verdict_detail),
        "{{OVERALL_STATUS}}": esc(review.get("overall_status") or "未完成"),
        "{{META}}": render_meta(review),
        "{{SCOPE_NOTICE}}": (
            "本报告仅检查项目文件、程序逻辑和程序侧接口配置；"
            "不判断真实 PLC 地址、物理通道与接线、传感器方向、COM 口、"
            "气压与限位、执行机构、现场安全效果、实际节拍或整机联锁。"
        ),
        "{{STATUS_OPTIONS}}": "".join(f'<option value="{esc(value)}">{esc(value)}</option>' for value in statuses),
        "{{SEVERITY_OPTIONS}}": "".join(f'<option value="{esc(value)}">{esc(value)}</option>' for value in severities),
        "{{ROWS}}": render_rows(review),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(template)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output_path)
