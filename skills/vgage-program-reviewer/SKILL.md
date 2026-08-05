---
name: "vgage-program-reviewer"
description: "审查 VGAGE 项目，支持离线检具豁免、多连接标识、自定义变量和零返回判定。"
---

# VGAGE Program Reviewer

当前规则目录版本：`2.15.0`。

检查完整 VGAGE Pro 项目目录中的项目文件、程序逻辑和程序侧接口配置。运行前读取 `references/boundary-contract.md`、`references/rule-catalog.json` 和 `references/source-manifest.json`。

1. 要求完整项目目录；技术协议、IO 点表、时序表、测点图和客户要求为可选证据。
2. 原程序文件只读。只允许在项目根目录新增 `VGAGE_REVIEW_YYYYMMDD_HHMMSS/`。
3. 运行 `scripts/review-project.py` 获取确定性判定结果；`execution=hybrid` 的规则由脚本内置的确定性规则函数直接判定完成，不产出独立的语义审查证据包，不需要额外人工/AI 语义复核步骤。
4. 只审查可由项目文件证明的错误。真实 PLC 地址、物理通道/接线、传感器正负方向、COM 口、气压/限位/执行机构以及现场安全效果不进入规则目录或报告。
5. FAIL 必须有 Rule ID、文件或对象证据及可复现理由。`MANUAL_VERIFY` 必须同时给出具体文件/对象、触发原因、缺失证据和可执行的人工动作；禁止空证据人工确认。
6. 有条件适用的规则在未发现触发功能时返回 `NOT_APPLICABLE`，且不进入 JSON、HTML 或 Excel 报告。
7. 从同一 `review-results.json` 生成离线 HTML 和 `VGAGE程序审查清单.xlsx`。HTML 标题使用“VGAGE 程序审查报告｜项目名”，页面顶部显示总体检查结论；仅 `COMPLETE + STATIC_REVIEW_PASSED` 显示“检查通过”，其余状态显示“检查不通过”并保留详细状态。“证据与建议”使用结构化证据卡片、中文字段名、来源标签和代码块；FAIL 默认展开，空影响/建议不显示。
8. `COMPLETE` 报告不得包含 `NOT_ASSESSABLE`；存在未执行规则或结果不满足 Schema 时必须标记为 `INCOMPLETE`。
9. 静态通过不等于设备验收通过；不得自动修改、联网、上传或建立远程连接。
