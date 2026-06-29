#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


DEFAULT_ENDPOINT = "https://api.mistral.ai/v1/ocr"
DEFAULT_MODEL = "mistral-ocr-4-0"
DEFAULT_OUTPUT_DIR = Path("temp/ocr-outputs")
SECRETS_ENV = Path.home() / ".openclaw" / "secrets.env"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def slugify(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\s]+", "_", value).strip("_")
    return value[:160] or "document"


def page_index(page: dict[str, Any], fallback: int) -> int:
    raw = page.get("index")
    if isinstance(raw, int):
        return raw + 1 if raw == fallback - 1 else raw
    return fallback


def build_markdown(result: dict[str, Any], source_name: str) -> str:
    pages = result.get("pages") or []
    usage = result.get("usage_info") or {}
    model = result.get("model") or ""
    lines = [
        "---",
        f'source_name: "{source_name.replace(chr(34), chr(92) + chr(34))}"',
        f'model: "{str(model).replace(chr(34), chr(92) + chr(34))}"',
        f'created_at: "{datetime.now().isoformat(timespec="seconds")}"',
        f"page_count: {len(pages)}",
        f"usage_info: {json.dumps(usage, ensure_ascii=False)}",
        "---",
        "",
        f"# {source_name}",
        "",
    ]
    for idx, page in enumerate(pages, 1):
        number = page_index(page, idx)
        markdown = (page.get("markdown") or "").strip()
        confidence = page.get("confidence_scores")
        lines.append(f"## Page {number}")
        if confidence:
            lines.append("")
            lines.append(f"<!-- confidence_scores: {json.dumps(confidence, ensure_ascii=False)} -->")
        lines.append("")
        lines.append(markdown or "_No OCR text returned for this page._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.pdf_url:
        document = {"type": "document_url", "document_url": args.pdf_url}
    else:
        pdf_path = Path(args.pdf).expanduser().resolve()
        if not pdf_path.exists():
            raise SystemExit(f"PDF not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise SystemExit(f"Input must be a PDF: {pdf_path}")
        encoded = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
        document = {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{encoded}",
        }

    payload: dict[str, Any] = {
        "model": args.model,
        "document": document,
        "include_blocks": args.include_blocks,
        "include_image_base64": args.include_image_base64,
    }
    if args.table_format != "none":
        payload["table_format"] = args.table_format
    if args.confidence_scores_granularity != "none":
        payload["confidence_scores_granularity"] = args.confidence_scores_granularity
    if args.extract_header:
        payload["extract_header"] = True
    if args.extract_footer:
        payload["extract_footer"] = True
    return payload


def output_base_name(args: argparse.Namespace) -> str:
    if args.name:
        return slugify(args.name)
    if args.pdf_url:
        tail = args.pdf_url.rstrip("/").split("/")[-1] or "url_pdf"
        return slugify(tail.removesuffix(".pdf"))
    return slugify(Path(args.pdf).stem)


def run_ocr(args: argparse.Namespace) -> tuple[Path, Path, dict[str, Any]]:
    if not args.allow_upload:
        raise SystemExit("Refusing to upload PDF without --allow-upload.")

    load_env_file(SECRETS_ENV)
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise SystemExit("MISTRAL_API_KEY is missing. Put it in env or ~/.openclaw/secrets.env.")

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_base_name(args)
    json_path = output_dir / f"{base}.json"
    md_path = output_dir / f"{base}.md"

    payload = build_payload(args)
    response = requests.post(
        args.endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=args.timeout,
    )
    if response.status_code >= 400:
        detail = response.text[:2000]
        raise SystemExit(f"Mistral OCR failed: HTTP {response.status_code}\n{detail}")

    result = response.json()
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_name = args.name or (Path(args.pdf).name if args.pdf else args.pdf_url)
    md_path.write_text(build_markdown(result, source_name), encoding="utf-8")
    return md_path, json_path, result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OCR a PDF with Mistral OCR 4 and write Markdown/JSON outputs.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf", help="Local PDF path.")
    input_group.add_argument("--pdf-url", help="Public PDF URL.")
    parser.add_argument("--allow-upload", action="store_true", help="Required: confirms the PDF may be uploaded to Mistral.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--name", help="Output base name and Markdown title.")
    parser.add_argument("--table-format", choices=["none", "markdown", "html"], default="markdown")
    parser.add_argument("--confidence-scores-granularity", choices=["none", "page", "word"], default="page")
    parser.add_argument("--include-blocks", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-image-base64", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--extract-header", action="store_true")
    parser.add_argument("--extract-footer", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    md_path, json_path, result = run_ocr(args)
    pages = result.get("pages") or []
    usage = result.get("usage_info") or {}
    print(json.dumps({
        "ok": True,
        "markdown_path": str(md_path),
        "json_path": str(json_path),
        "page_count": len(pages),
        "model": result.get("model"),
        "usage_info": usage,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
