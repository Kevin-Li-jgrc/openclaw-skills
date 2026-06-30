# VGAGE 编程任务书风险清单

Use this checklist when preparing taskbooks and handoffs.

## Always high-risk unless confirmed

- Sensor channel, physical location, direction, and sign.
- RTG timing and station action sequence.
- PLC DB/address, read/write direction, trigger/reset semantics, and handshake timing.
- MES fields, endpoint, upload/download timing, cache/retry behavior, and failure policy.
- Marking content, encoding, anti-duplicate source, trigger timing, completion signal.
- Temperature compensation formula, reference temperature, temperature source, coefficient direction.
- Nominal/USL/LSL/UAL/LAL conflicts, OCR ambiguity, or contradictory agreement tables.
- Q-DAS / SPC required fields, part identifiers, output path, and customer acceptance method.

## Do not treat as confirmed

- OCR text without page/table spot-check for formula-like or tolerance-sensitive data.
- Historical project habit without evidence that the new project matches.
- Project number match alone.
- Sensor naming similarity alone.
- Customer phrase similarity without field-level mapping.

## Minimum implementation validation

- Work on a copy or patch draft, never overwrite original project files.
- XML parse check after edits.
- `VGA.xml` object reference check.
- Probe Dependencies check.
- Measurement Probe binding check.
- Formula/Nominal/tolerance relation check.
- Compile/open smoke test in VGAGE Pro when possible.
- Representative data or mock run for MES/PLC/marking logic.
- Record rollback path and changed files.

## Handoff wording

Use explicit status wording:

- `可分配 worker`: safe to start on a copy with listed constraints.
- `待现场确认`: taskbook is structured but blocked on field confirmation.
- `DONE_WITH_CONCERNS`: artifacts exist but Notion/writeback/validation could not be fully verified.
