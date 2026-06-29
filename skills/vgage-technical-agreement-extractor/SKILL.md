---
name: "vgage-technical-agreement-extractor"
description: "Extract VGAGE agreements into a fixed Notion analysis database."
---

# VGAGE Technical Agreement Extractor

Use this skill when the user uploads or references a technical agreement, customer specification, measurement station protocol, DWG-derived requirement package, or PDF that should feed VGAGE Pro programming or project analysis.

This skill converts OCR output into a traceable VGAGE requirement record. It focuses on detection parameters, takt/cycle-time requirements, precision and acceptance standards, data interaction, marking, temperature compensation, and other customer-specific functions.

## Public Setup

Before using this public copy, replace the placeholders below with your own Notion workspace values.

- Top-level parent page: `<VGAGE_PRO_PARENT_PAGE_NAME>`
- Top-level parent page id: `<VGAGE_PRO_PARENT_PAGE_ID>`
- Hub page under parent: `<PROJECT_REQUIREMENT_ANALYSIS_HUB_PAGE_NAME>`
- Hub page id: `<PROJECT_REQUIREMENT_ANALYSIS_HUB_PAGE_ID>`
- Database inside hub page: `<ANALYSIS_DATABASE_NAME>`
- Database id: `<ANALYSIS_DATABASE_ID>`
- Data source id: `<ANALYSIS_DATA_SOURCE_ID>`
- Legacy or unrelated progress database id, if any: `<PROJECT_PROGRESS_DATABASE_ID>`

Do not publish your private Notion IDs, customer documents, OCR output, API keys, tokens, or local paths.

## Core Rule

All VGAGE technical-agreement extraction records must be written into the fixed Notion analysis database configured above. Do not create loose Notion pages for this workflow unless the user explicitly overrides the destination.

Do not use a legacy technical-agreement database or a project-progress database as the destination for new records. Legacy databases should be retained only as historical evidence unless the user explicitly approves migration.

Default status for new records is `Pending user confirmation`. Treat OCR and extracted requirements as draft evidence until the user confirms high-risk fields.

## Notion Routing Boundary

Keep technical-agreement analysis separate from project-progress tracking.

Use the configured analysis database for:

- technical agreements and customer specifications
- OCR extraction records
- detection-parameter tables
- detection detail tables
- requirement analysis
- user confirmation checklists
- VGAGE programming task books
- programming handoff content based on technical agreements

Do not write these outputs into a project-progress database or a project-number page inside that database.

A project-progress database should be used only for:

- project status tracking
- meeting or PPT progress
- design / manufacturing / assembly stages
- due dates and reminders
- short project-progress summaries

If a request mentions a project number and also mentions technical agreements, detection-related content, measurement items, requirement extraction, confirmation items, programming task books, OCR, or customer specification content, the destination is still the analysis database. The project number is metadata for the analysis record, not a routing instruction.

Only mirror content to a project-progress page when the user explicitly asks for it. In that case, write only a short summary and backlink to the analysis record; keep the full extraction, tables, confirmation checklist, and programming handoff in the analysis database.

## Inputs

Accept any of these inputs:

- Original PDF technical agreement.
- OCR Markdown and JSON produced by a PDF OCR workflow.
- A searchable PDF generated from OCR.
- A text export from a customer agreement, drawing note, or project specification.

If only a PDF is available, run OCR first. Upload a PDF to an OCR provider only when the user explicitly says that exact PDF can be uploaded. Preserve the original PDF and never overwrite it.

## Required Artifacts

For each processed agreement, keep these paths or values when available:

- original PDF path
- OCR Markdown path
- OCR JSON path
- searchable PDF path
- OCR date
- page count
- OCR model/provider if known
- Notion database page URL

Never expose API keys, Notion tokens, or local secrets in reports or public artifacts.

## Extraction Workflow

1. Confirm the source file and upload authorization.
2. Run OCR if OCR Markdown does not already exist.
3. Read the OCR Markdown and spot-check the OCR JSON or source PDF when a key field is ambiguous.
4. Extract requirements into the sections below.
5. Create or update one record in the configured Notion analysis data source.
6. Do not use a project-progress database as a fallback destination, even when a project number is present.
7. Write the full Markdown summary into the Notion page body.
8. Read back the Notion page title, core properties, parent/database, and body content before reporting completion.

## Extraction Sections

### Basic Project Info

Capture these fields when present:

- project name
- customer
- production line
- equipment name
- product model or part family
- source file name
- agreement/version/date if visible

If a field is not found, write `not identified` instead of guessing.

### Detection Parameters

Build a table of measurement items. Include columns when present:

- item name
- feature or station context
- nominal value
- USL / LSL
- UAL / LAL
- unit
- measurement method or sensor/gage
- related product/model
- page/source evidence
- confidence or note

Do not infer sign, direction, channel, probe mapping, formula, or tolerance from habit. Mark these as user-confirmation items unless explicitly stated.

### Equipment Takt / Cycle Time

Extract:

- whole-station takt or cycle-time limit
- manual operation cycle-time limit
- single-piece or multi-piece condition
- OEE / availability requirements
- loading/unloading assumptions
- source page and short evidence

Keep multiple cycle-time values separate. Do not collapse equipment takt, manual takt, and measurement time into one value.

### Precision And Acceptance Standards

Extract:

- repeatability / reproducibility / GR&R
- accuracy / resolution / uncertainty
- calibration requirements
- acceptance rules
- sample-count or trial-count requirements
- environmental conditions that affect acceptance

Mark acceptance standards as high risk if the OCR is blurry, table-heavy, or formula-like.

### Data Interaction Requirements

Extract data and communication requirements, including:

- PLC / IO / fieldbus
- RFID / barcode scanner
- MES / database / web API
- data upload/download fields
- trigger timing
- cache/retry/logging requirements
- traceability and anti-duplicate rules

For PLC addresses, MES field names, trigger timing, and upload/download semantics, record exact source evidence and require user confirmation before programming delivery.

### Auxiliary And Customer-Specific Functions

Extract special requirements such as:

- temperature compensation
- marking / engraving / label printing
- Q-DAS / SPC
- reports
- permissions and user roles
- rework / NG handling
- automatic flow, alarms, interlocks
- data retention and export
- UI or HMI flow requirements

Marking is primarily a customer-specific function and secondarily a hardware interaction item.

### VGAGE Implementation Mapping

Map confirmed and draft requirements to possible VGAGE surfaces:

- `VGA.xml`
- `CodeModule.vgs`
- `IO.xml`
- Form XML
- `Screens.xml`
- `Settings.config`
- `Q-DAS.xml`
- `SPC.xml`

This mapping is planning evidence, not authorization to edit project files. Do not edit original VGAGE projects through this skill.

### User Confirmation Checklist

Always produce a checklist of items the user must confirm before programming, especially:

- PLC address and IO mapping
- MES fields and upload/download triggers
- marking content and timing
- RTG timing
- sensor/probe direction and sign
- tolerances and acceptance thresholds
- temperature compensation formula and reference temperature
- data retry/cache behavior

## Notion Write Rules

Create records in the configured analysis data source.

Populate these properties when possible:

- `项目名称`
- `协议名称`
- `设备名称`
- `客户`
- `产线`
- `产品型号`
- `来源文件名`
- `原始PDF路径`
- `OCR Markdown路径`
- `OCR JSON路径`
- `可搜索PDF路径`
- `OCR日期`
- `状态`
- `风险等级`
- `可搜索PDF`
- `编程任务书`
- `关联VGAGE项目`

Set `状态 = 待确认` unless the user has explicitly confirmed the extracted requirements. Set `风险等级 = 高` when the agreement includes PLC, MES, IO, marking, RTG, Q-DAS, SPC, formulas, sign, direction, or tolerance-sensitive content.

Set `编程任务书 = false` unless the output includes a dedicated programming-handoff section ready for a VGAGE worker.

Before completion, verify the record parent/database is the configured analysis database. If the record was written to a project-progress database, the task is not complete; move or recreate the full content in the analysis database before reporting.

## Output Format

Return a concise result with:

- Notion record URL
- artifact paths
- extracted top-level requirements summary
- top risks
- user confirmation checklist
- validation performed

## Validation

Before saying the task is complete, verify at minimum:

- OCR Markdown exists and has non-trivial text.
- Page count or source coverage is known when using OCR.
- Detection/takt/precision/data/custom sections are either populated or explicitly marked `not identified`.
- Notion record exists in the configured analysis database.
- Notion body contains the generated Markdown summary.
- The record was not written into a project-progress database.
- The original PDF was not overwritten or deleted.

If a searchable PDF was generated, verify text can be extracted from it or clearly report that searchable-PDF validation was not completed.

## Failure Handling

- Missing upload authorization: ask the user before sending the PDF to OCR.
- OCR failure: keep the original file, report the failure, and do not fabricate extraction results.
- Notion database inaccessible: stop and report the exact blocked step; do not create a page elsewhere without user approval.
- Accidental write to a project-progress database: do not treat it as complete. Recreate or move the full extraction into the configured analysis database, then optionally leave only a short backlink in the progress page if the user approves.
- Ambiguous OCR: include OCR caveats and source page references.
- Token or API errors: never print secrets; report only the failing command/tool class and next safe action.

## Safety Boundaries

- Never delete original files.
- Never publish private agreements or extracted customer data publicly.
- Never treat OCR text as field-confirmed truth.
- Never infer high-risk implementation fields that are not explicit in the source.
- Never directly overwrite original VGAGE project files.
