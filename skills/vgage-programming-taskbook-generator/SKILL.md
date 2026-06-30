---
name: "vgage-programming-taskbook-generator"
description: "Generate VGAGE programming taskbooks from requirements."
---

# VGAGE Programming Taskbook Generator

Use this skill to convert VGAGE requirement evidence into a programming taskbook that a `vgage-bot` / `vgage-worker-*` agent can execute safely.

This skill sits between requirement extraction and implementation:

```text
technical agreement / OCR / detection table / operator/field confirmations
-> vgage-technical-agreement-extractor or equivalent analysis
-> vgage-programming-taskbook-generator
-> worker implementation on a copy / static audit / operator/field confirmation
```

## Core Boundary

Generate taskbooks only. Do not directly modify original VGAGE project files through this skill.

A taskbook may recommend file targets, object names, formulas, scripts, validation steps, and worker assignment. It is not authorization to edit live project files.

Always preserve these boundaries:

- Do not overwrite, delete, or directly patch original VGAGE project files.
- Do not confirm sensor direction, sign, channel, RTG timing, PLC addresses, MES fields, marking content, or formula direction unless the field operator has explicitly confirmed them.
- Do not route taskbooks to `project-progress database` or project-number pages there.
- Store or update taskbook records only in `<VGAGE_REQUIREMENT_ANALYSIS_DATABASE_PATH>` unless field operator explicitly overrides.
- Set the analysis-library `编程任务书` property to true when the output is a dedicated programming taskbook.
- If evidence is insufficient, generate a `待确认任务书` instead of pretending it is executable.

## Fixed Notion Destination

Use the same analysis library as `vgage-technical-agreement-extractor`:

- Top-level parent page: `VGAGE Pro`
- Hub page: `<REQUIREMENT_ANALYSIS_HUB>`
- Database: `分析库`
- Data source id: `<ANALYSIS_DATA_SOURCE_ID>`

Use `project-progress database` only for short progress summaries when field operator explicitly asks for mirroring. Keep full taskbooks, task tables, confirmation checklists, and implementation mapping in the analysis library.

## Inputs

Accept any of these:

- A Notion analysis record created by `vgage-technical-agreement-extractor`.
- OCR Markdown / JSON from a technical agreement.
- A detection-related Markdown table or extracted `检测相关信息详表`.
- operator-confirmed notes from a VGAGE discussion.
- DWG-derived requirement notes or measurement drafts.
- Existing project scan output when used as supporting evidence.

If the source is only a PDF and OCR is required, use `mistral-pdf-ocr` first and upload only after field operator explicitly authorizes that exact file.

## Required Output

Always produce a structured Markdown taskbook with these sections:

1. Project identity and source evidence.
2. Three-layer analysis summary.
3. Hardware interaction table.
4. Detection parameter table.
5. Customer-specific function table.
6. VGAGE object / file mapping table.
7. Programming task split.
8. operator/field confirmation checklist.
9. Validation and handoff checklist.
10. Residual risks and assumptions.

Use `references/taskbook-template.md` for the expected structure.

## Workflow

1. Identify the source evidence and whether it already came from a verified Notion analysis record.
2. Read only the relevant upstream artifacts: Notion body, OCR Markdown, detection table, operator notes, and supporting project scan outputs.
3. Separate facts, judgments, and assumptions.
4. Build the taskbook using the three-layer framework:
   - Hardware interaction layer.
   - Detection parameter layer.
   - Customer-specific function layer.
5. Map every actionable item to VGAGE files and objects using `references/mapping-rules.md`.
6. Split work into task groups:
   - `可直接执行`: evidence is sufficient and risk is low or medium.
   - `需现场确认后执行`: field-level ambiguity or high-risk implementation decision exists.
   - `禁止自动判断`: direction/sign/channel/PLC/MES/RTG/marking semantics are missing or contradictory.
   - `建议另开试验副本`: change is risky, event-driven, hardware-facing, or likely to affect VGAGE startup/compile behavior.
7. Add a validation checklist using `references/risk-checklist.md`.
8. Create or update the Notion taskbook record in the fixed analysis library.
9. Read back the Notion record parent/data source, title, status, `编程任务书`, and body key sections before reporting completion.

## Taskbook Status

Use one of these statuses in the taskbook body and Notion properties when available:

- `草稿`: requirements are organized but not ready to assign.
- `待现场确认`: high-risk fields require operator/field confirmation.
- `可分配 worker`: enough information exists for a worker to start on a copy.
- `已交付 worker`: the taskbook has been assigned to a specific worker.
- `已完成`: implementation and validation evidence have been linked.

Default to `待现场确认` when uncertain.

## Programming Task Split Rules

Prefer small task groups that can be independently verified:

- Project preparation / copy / backup.
- Probe and Measurement creation.
- Formula and Nominal/tolerance handling.
- RTG / Part / operation flow.
- IO / PLC / Tag mapping.
- MES / database / API / file export.
- Marking / anti-duplicate / scan binding.
- Temperature compensation.
- Q-DAS / SPC output.
- Form / Screens UI changes.
- Static audit and smoke validation.

For each task group include:

- `目标`.
- `输入证据`.
- `建议落点`.
- `可执行步骤`.
- `待确认项`.
- `最小验证`.
- `推荐 worker` when assignment is relevant.

## Confirmation Rules

Always list operator/field-confirmation items for:

- Sensor channel, direction, sign, and physical position.
- RTG timing and station action sequence.
- PLC addresses, read/write direction, trigger bits, reset semantics, and handshake timing.
- MES fields, upload/download timing, retry/cache behavior, and failure policy.
- Marking content, encoding, trigger timing, anti-duplicate source, and completion signal.
- Nominal/USL/LSL/UAL/LAL conflicts or OCR ambiguity.
- Temperature compensation formula, reference temperature, coefficient direction, and temperature source.
- Q-DAS / SPC required fields and output path.

Do not move these into `可直接执行` unless the evidence includes explicit operator/field confirmation.

## Validation

Before reporting the taskbook complete, verify at minimum:

- The taskbook contains all required sections.
- Every high-risk item is either confirmed or listed in the confirmation checklist.
- `project-progress database` was not used as the full taskbook destination.
- The Notion record exists in `<VGAGE_REQUIREMENT_ANALYSIS_DATABASE_PATH>` when Notion writing is part of the request.
- The Notion record has `编程任务书 = true` when the taskbook is ready for handoff.
- The body includes the programming task split and validation checklist.

If Notion writing cannot be verified, report `DONE_WITH_CONCERNS` rather than complete.

## Output Summary

Reply with:

- Taskbook title and Notion URL or local path.
- Status: `草稿` / `待现场确认` / `可分配 worker` / `DONE_WITH_CONCERNS`.
- Main task groups.
- Top operator/field-confirmation items.
- Validation performed.
- Recommended next worker action.

Keep the chat summary concise; the taskbook itself carries the detail.
