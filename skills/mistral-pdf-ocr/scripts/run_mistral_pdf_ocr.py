#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - reported at runtime
    PdfReader = None  # type: ignore[assignment]


DEFAULT_OUTPUT_DIR = Path("temp/ocr-outputs")


def slugify(value: str) -> str:
    import re

    value = re.sub(r"[\\/:*?\"<>|\s]+", "_", value).strip("_")
    return value[:160] or "document"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_json_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode != 0:
        raise SystemExit(
            "Command failed:\n"
            + " ".join(command)
            + "\n\nSTDOUT:\n"
            + completed.stdout[-4000:]
            + "\n\nSTDERR:\n"
            + completed.stderr[-4000:]
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Expected JSON output from command: {' '.join(command)}\n{exc}\n{completed.stdout[-2000:]}") from exc


def run_text_command(command: list[str]) -> str:
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode != 0:
        raise SystemExit(
            "Command failed:\n"
            + " ".join(command)
            + "\n\nSTDOUT:\n"
            + completed.stdout[-4000:]
            + "\n\nSTDERR:\n"
            + completed.stderr[-4000:]
        )
    return completed.stdout.strip()


def pdf_text_stats(path: Path) -> tuple[int, int, list[dict[str, int]]]:
    if PdfReader is None:
        raise SystemExit("pypdf is missing. Install pypdf before validating searchable PDFs.")
    reader = PdfReader(str(path))
    per_page = []
    total = 0
    for idx, page in enumerate(reader.pages, 1):
        chars = len(page.extract_text() or "")
        total += chars
        per_page.append({"page": idx, "text_chars": chars})
    return len(reader.pages), total, per_page


def ocr_page_stats(ocr_json: Path) -> tuple[int, list[dict[str, Any]]]:
    data = json.loads(ocr_json.read_text(encoding="utf-8"))
    pages = data.get("pages") or []
    stats = []
    for idx, page in enumerate(pages, 1):
        markdown = page.get("markdown") or ""
        blocks = page.get("blocks") or []
        confidence = page.get("confidence_scores")
        stats.append(
            {
                "page": idx,
                "markdown_chars": len(markdown.strip()),
                "block_count": len(blocks),
                "confidence_scores": confidence,
            }
        )
    return len(pages), stats


def markdown_report(manifest: dict[str, Any]) -> str:
    validation = manifest["validation"]
    low_pages = validation["low_text_pages"]
    lines = [
        f"# OCR Report: {manifest['name']}",
        "",
        f"- Created: {manifest['created_at']}",
        f"- Input: `{manifest['input']['path']}`",
        f"- Input SHA256: `{manifest['input']['sha256']}`",
        f"- OCR JSON: `{manifest['outputs']['ocr_json']}`",
        f"- Markdown: `{manifest['outputs'].get('markdown') or ''}`",
        f"- Searchable PDF: `{manifest['outputs']['searchable_pdf']}`",
        f"- Original pages: {validation['original_pdf_pages']}",
        f"- OCR pages: {validation['ocr_pages']}",
        f"- Searchable PDF pages: {validation['searchable_pdf_pages']}",
        f"- Searchable text chars: {validation['searchable_pdf_text_chars']}",
        f"- Low text pages: {', '.join(map(str, low_pages)) if low_pages else 'none'}",
        "",
        "## Page Text Stats",
        "",
        "| Page | OCR Markdown Chars | Searchable PDF Text Chars | OCR Blocks |",
        "|---:|---:|---:|---:|",
    ]
    ocr_by_page = {item["page"]: item for item in validation["ocr_page_stats"]}
    pdf_by_page = {item["page"]: item for item in validation["searchable_pdf_page_stats"]}
    for page in range(1, validation["original_pdf_pages"] + 1):
        ocr = ocr_by_page.get(page, {})
        pdf = pdf_by_page.get(page, {})
        lines.append(
            f"| {page} | {ocr.get('markdown_chars', 0)} | {pdf.get('text_chars', 0)} | {ocr.get('block_count', 0)} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Mistral PDF OCR, create a searchable PDF, and write manifest/report artifacts."
    )
    parser.add_argument("--pdf", required=True, help="Local PDF path.")
    parser.add_argument("--allow-upload", action="store_true", help="Required when OCR must upload the PDF to Mistral.")
    parser.add_argument("--ocr-json", help="Existing OCR JSON path. When provided, skip upload/OCR and reuse it.")
    parser.add_argument("--name", help="Output base name.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--model", default="mistral-ocr-4-0")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--low-text-threshold", type=int, default=20)
    parser.add_argument(
        "--script-dir",
        default=str(Path(__file__).resolve().parent),
        help="Directory containing mistral_ocr_pdf.py and make_searchable_pdf_from_mistral_ocr.py.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.exists() or pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Input PDF not found or not a PDF: {pdf}")

    if not args.ocr_json and not args.allow_upload:
        raise SystemExit("Refusing to upload PDF without --allow-upload. Pass --ocr-json to reuse existing OCR output.")

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = slugify(args.name or pdf.stem)
    script_dir = Path(args.script_dir).expanduser().resolve()

    if args.ocr_json:
        ocr_json = Path(args.ocr_json).expanduser().resolve()
        if not ocr_json.exists():
            raise SystemExit(f"OCR JSON not found: {ocr_json}")
        markdown_path = output_dir / f"{base}.md"
        if not markdown_path.exists():
            markdown_path = None
        ocr_result: dict[str, Any] = {"ok": True, "json_path": str(ocr_json), "markdown_path": str(markdown_path or "")}
    else:
        ocr_script = script_dir / "mistral_ocr_pdf.py"
        ocr_result = run_json_command(
            [
                sys.executable,
                str(ocr_script),
                "--pdf",
                str(pdf),
                "--allow-upload",
                "--name",
                base,
                "--output-dir",
                str(output_dir),
                "--model",
                args.model,
                "--timeout",
                str(args.timeout),
            ]
        )
        ocr_json = Path(ocr_result["json_path"]).expanduser().resolve()
        markdown_path = Path(ocr_result["markdown_path"]).expanduser().resolve()

    searchable_pdf = output_dir / f"{base}_searchable_with_images.pdf"
    searchable_script = script_dir / "make_searchable_pdf_from_mistral_ocr.py"
    run_text_command(
        [
            sys.executable,
            str(searchable_script),
            "--input-pdf",
            str(pdf),
            "--ocr-json",
            str(ocr_json),
            "--output-pdf",
            str(searchable_pdf),
        ]
    )

    original_pages, _, _ = pdf_text_stats(pdf)
    ocr_pages, ocr_stats = ocr_page_stats(ocr_json)
    searchable_pages, searchable_text_chars, searchable_page_stats = pdf_text_stats(searchable_pdf)
    low_text_pages = [
        item["page"] for item in searchable_page_stats if item["text_chars"] < args.low_text_threshold
    ]

    validation = {
        "original_pdf_pages": original_pages,
        "ocr_pages": ocr_pages,
        "searchable_pdf_pages": searchable_pages,
        "searchable_pdf_text_chars": searchable_text_chars,
        "low_text_threshold": args.low_text_threshold,
        "low_text_pages": low_text_pages,
        "ocr_page_stats": ocr_stats,
        "searchable_pdf_page_stats": searchable_page_stats,
        "page_counts_match": original_pages == ocr_pages == searchable_pages,
    }
    if not validation["page_counts_match"]:
        raise SystemExit(f"Page count mismatch: {validation}")

    manifest = {
        "ok": True,
        "name": base,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input": {
            "path": str(pdf),
            "sha256": sha256_file(pdf),
            "upload_authorized": bool(args.allow_upload and not args.ocr_json),
            "reused_ocr_json": bool(args.ocr_json),
        },
        "model": args.model,
        "outputs": {
            "markdown": str(markdown_path) if markdown_path else None,
            "ocr_json": str(ocr_json),
            "searchable_pdf": str(searchable_pdf),
            "manifest": str(output_dir / f"{base}_manifest.json"),
            "report": str(output_dir / f"{base}_ocr_report.md"),
        },
        "ocr_result": ocr_result,
        "validation": validation,
    }
    manifest_path = output_dir / f"{base}_manifest.json"
    report_path = output_dir / f"{base}_ocr_report.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(markdown_report(manifest), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
