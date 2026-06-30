---
name: "mistral-pdf-ocr"
description: "Mistral PDF OCR管线：总入口、manifest与质量报告"
---

# Mistral PDF OCR

## Purpose

Use this skill to process scanned or image-heavy PDFs with Mistral OCR 4 and produce reusable OCR artifacts:

- `*.md` for reading, summarization, formula extraction, and follow-up analysis
- `*.json` with pages, blocks, coordinates, confidence, and OCR structure
- `*_searchable_with_images.pdf` that keeps the original scanned page images and adds an invisible OCR text layer for search/copy
- `*_manifest.json` with input SHA256, upload/reuse status, generated outputs, and validation metrics
- `*_ocr_report.md` with page-level OCR/text statistics and low-text page warnings

Keep this skill generic. Do not put VGAGE-specific extraction, Notion routing, project requirement analysis, or customer-specific business logic here. For VGAGE technical agreement extraction after OCR, use `vgage-technical-agreement-extractor`.

## Safety Rules

- Do not upload any PDF to Mistral until the user explicitly confirms that the specific PDF may be uploaded to Mistral OCR.
- Treat each new PDF independently. Prior permission for one file does not authorize another file.
- Never put `MISTRAL_API_KEY` in chat, memory, Markdown outputs, logs, manifest files, reports, or generated PDFs.
- Read the API key from `MISTRAL_API_KEY` in the environment or `~/.openclaw/secrets.env`.
- Never overwrite the original PDF. Write outputs under `temp/ocr-outputs/` unless the user asks for another output directory.
- Default output should preserve images: generate `*_searchable_with_images.pdf`, not a pure text PDF, unless the user explicitly asks for a text-only rebuild.
- If Mistral OCR fails, report the HTTP/status error and do not claim completion.
- Use `--ocr-json` to reuse an existing OCR JSON without uploading the PDF again.

## Inputs

Accept either:

- a local PDF path
- a cached inbound attachment path, usually under `~/.openclaw/media/inbound/`
- a public PDF URL only when the user provides or approves it; URL mode currently uses the lower-level `mistral_ocr_pdf.py` script directly

For Feishu/direct attachment workflows, first locate the cached file under `~/.openclaw/media/inbound/` using the attachment filename or UUID.

## Standard Workflow

1. Confirm the target PDF and whether it is local or an inbound attachment.
2. If the user has not explicitly authorized uploading this exact PDF, ask: `这个 PDF 可以上传到 Mistral OCR 吗？`
3. Verify `MISTRAL_API_KEY` exists in the environment or `~/.openclaw/secrets.env`.
4. Prefer the orchestration script for normal local-PDF work:

```bash
python3 scripts/run_mistral_pdf_ocr.py \
  --pdf /path/to/input.pdf \
  --allow-upload \
  --name output_base_name \
  --output-dir temp/ocr-outputs
```

5. For断点续跑 or no-upload rebuilds, reuse existing OCR JSON:

```bash
python3 scripts/run_mistral_pdf_ocr.py \
  --pdf /path/to/input.pdf \
  --ocr-json temp/ocr-outputs/output_base_name.json \
  --name output_base_name \
  --output-dir temp/ocr-outputs
```

6. If the user needs public URL OCR or lower-level debugging, run the lower-level OCR script directly:

```bash
python3 scripts/mistral_ocr_pdf.py \
  --pdf /path/to/input.pdf \
  --allow-upload \
  --name output_base_name \
  --output-dir temp/ocr-outputs
```

Then rebuild the searchable PDF manually if needed:

```bash
python3 scripts/make_searchable_pdf_from_mistral_ocr.py \
  --input-pdf /path/to/input.pdf \
  --ocr-json temp/ocr-outputs/output_base_name.json \
  --output-pdf temp/ocr-outputs/output_base_name_searchable_with_images.pdf
```

7. Read the `*_manifest.json` and `*_ocr_report.md` before reporting completion. Report low-text pages or page-count mismatches clearly.

8. Send the searchable PDF back when the conversation channel supports file sending. For Feishu file/PDF sending, prefer `filePath`-style media sending when available.

## Expected Outputs

For input `FORMULAR.pdf`, expected outputs are:

- `temp/ocr-outputs/FORMULAR.md`
- `temp/ocr-outputs/FORMULAR.json`
- `temp/ocr-outputs/FORMULAR_searchable_with_images.pdf`
- `temp/ocr-outputs/FORMULAR_manifest.json`
- `temp/ocr-outputs/FORMULAR_ocr_report.md`

## Validation Criteria

The job is complete only when:

- OCR command returns `ok: true`, unless explicitly running no-upload reuse mode from an existing JSON.
- Markdown and JSON output files exist after fresh OCR.
- Searchable PDF exists.
- Manifest and OCR report exist.
- Searchable PDF page count matches the original PDF and OCR JSON page count.
- `pypdf.extract_text()` returns non-empty text for the searchable PDF unless the source has no recognizable text.
- Low-text pages are reported instead of silently ignored.
- User-visible response distinguishes between searchable PDF text layer and true CAD/vector redraw. Preserved page images remain raster images.

## Notes

- The searchable PDF keeps original scanned images as raster page visuals. It does not convert diagrams into CAD-grade vector drawings.
- The invisible text layer is positioned from Mistral OCR block coordinates and is intended for search/copy, not visual replacement of the scan.
- For formula-heavy documents, Markdown/JSON/manifest/report should be retained for later formula extraction or VGAGE mapping work.
- Low-text pages are warnings, not automatic failures. They often indicate image-only pages, diagrams, covers, or pages where text placement could not be inserted cleanly.
