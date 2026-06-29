---
name: "mistral-pdf-ocr"
description: "Mistral OCR识别扫描PDF并生成可搜索PDF"
---

# Mistral PDF OCR

## Purpose

Use this skill to process scanned PDFs with Mistral OCR 4 and produce reusable OCR artifacts:

- `*.md` for reading, summarization, formula extraction, and follow-up analysis
- `*.json` with pages, blocks, coordinates, confidence, and OCR structure
- `*_searchable_with_images.pdf` that keeps the original scanned page images and adds an invisible OCR text layer for search/copy

## Safety Rules

- Do not upload any PDF to Mistral until the user explicitly confirms that the specific PDF may be uploaded to Mistral OCR.
- Treat each new PDF independently. Prior permission for one file does not authorize another file.
- Never put `MISTRAL_API_KEY` in chat, memory, Markdown outputs, logs, or generated PDFs.
- Read the API key from `MISTRAL_API_KEY` in the environment or `~/.openclaw/secrets.env`.
- Never overwrite the original PDF. Write outputs under `temp/ocr-outputs/` unless the user asks for another output directory.
- Default output should preserve images: generate `*_searchable_with_images.pdf`, not a pure text PDF, unless the user explicitly asks for a text-only rebuild.
- If Mistral OCR fails, report the HTTP/status error and do not claim completion.

## Inputs

Accept either:

- a local PDF path
- a cached inbound attachment path, usually under `~/.openclaw/media/inbound/`
- a public PDF URL, only when the user provides or approves it

For Feishu/direct attachment workflows, first locate the cached file under `~/.openclaw/media/inbound/` using the attachment filename or UUID.

## Standard Workflow

1. Confirm the target PDF and whether it is local or an inbound attachment.
2. If the user has not explicitly authorized uploading this exact PDF, ask: `这个 PDF 可以上传到 Mistral OCR 吗？`
3. Verify `MISTRAL_API_KEY` exists in the environment or `~/.openclaw/secrets.env`.
4. Run OCR:

```bash
python3 scripts/mistral_ocr_pdf.py \
  --pdf /path/to/input.pdf \
  --allow-upload \
  --name output_base_name \
  --output-dir temp/ocr-outputs
```

5. Generate the searchable PDF that preserves original images:

```bash
python3 scripts/make_searchable_pdf_from_mistral_ocr.py \
  --input-pdf /path/to/input.pdf \
  --ocr-json temp/ocr-outputs/output_base_name.json \
  --output-pdf temp/ocr-outputs/output_base_name_searchable_with_images.pdf
```

6. Validate before reporting completion:

```bash
python3 - <<'PY'
from pathlib import Path
from pypdf import PdfReader
p = Path('temp/ocr-outputs/output_base_name_searchable_with_images.pdf')
r = PdfReader(str(p))
text = '\n'.join((page.extract_text() or '') for page in r.pages)
print('exists', p.exists())
print('bytes', p.stat().st_size)
print('pages', len(r.pages))
print('text_chars', len(text))
PY
```

7. Report the generated paths and send the searchable PDF back when the conversation channel supports file sending.

## Expected Outputs

For input `FORMULAR.pdf`, expected outputs are:

- `temp/ocr-outputs/FORMULAR.md`
- `temp/ocr-outputs/FORMULAR.json`
- `temp/ocr-outputs/FORMULAR_searchable_with_images.pdf`

## Validation Criteria

The job is complete only when:

- OCR command returns `ok: true`.
- Markdown and JSON output files exist.
- Searchable PDF exists.
- Searchable PDF page count matches the original PDF and OCR JSON page count.
- `pypdf.extract_text()` returns non-empty text for the searchable PDF unless the source has no recognizable text.
- User-visible response distinguishes between searchable PDF text layer and true CAD/vector redraw. Preserved page images remain raster images.

## Notes

- The searchable PDF keeps original scanned images as raster page visuals. It does not convert diagrams into CAD-grade vector drawings.
- The invisible text layer is positioned from Mistral OCR block coordinates and is intended for search/copy, not visual replacement of the scan.
- For formula-heavy documents, Markdown/JSON should be retained for later formula extraction or VGAGE mapping work.
