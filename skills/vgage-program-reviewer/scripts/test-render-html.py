from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("render-html.py")
spec = importlib.util.spec_from_file_location("vgage_render_html_test", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

review = {
    "execution_state": "COMPLETE",
    "overall_status": "BLOCKED",
    "project": {"name": "Demo", "root": "/demo", "fingerprint": "abc"},
    "rule_package": {"catalog_version": "2.11.0", "effective_date": "2026-07-17"},
    "rules": [
        {
            "rule_id": "VG-TST-001",
            "status": "FAIL",
            "severity": "P1",
            "title": "结构化证据测试",
            "sources": [{"reference": "shared/core"}],
            "evidence": [
                {
                    "object": "M1",
                    "probe_name": "p21n22",
                    "probe_text": None,
                    "equation": "Function M1_Value() As Integer\r\n Return 0\r\nEnd Function",
                    "measurements": ["M1", "M2"],
                    "reason": "measurement_symbol_conflicts_with_explicit_name_or_text",
                    "custom_field": "<script>alert(1)</script>",
                }
            ],
            "impact": "存在错误",
            "recommendation": "修正后复查",
        },
        {
            "rule_id": "VG-TST-002",
            "status": "PASS",
            "severity": "P3",
            "title": "空区块测试",
            "sources": [],
            "evidence": [],
            "impact": "",
            "recommendation": "",
        },
    ],
}

with tempfile.TemporaryDirectory(prefix="vgage-render-html-") as temporary:
    output = Path(temporary) / "report.html"
    module.render_html(review, output)
    rendered = output.read_text(encoding="utf-8")

assert "VGAGE 程序审查报告｜Demo" in rendered
assert "检查不通过" in rendered
assert rendered.count('<details class="rule-detail" open>') == 1
assert '<div class="evidence-card-title">证据 1</div>' in rendered
assert "公式 / 代码" in rendered and '<pre class="code-block"><code>' in rendered
assert rendered.count('class="chip"') == 2
assert "Measurement 符号与名称或文本中的明确检测语义冲突" in rendered
assert "Probe 名称" in rendered and "p21n22" in rendered
assert "Probe 文本" in rendered and "未填写" in rendered
assert "Custom Field" in rendered
assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
assert "<script>alert(1)</script>" not in rendered
assert "本检查项未记录额外证据" in rendered
assert "&quot;object&quot;" not in rendered
assert "{{" not in rendered

print("html evidence UI: PASS")
