#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz


def clean_text(value: str) -> str:
    value = re.sub(r"^#+\s*", "", value.strip())
    value = value.replace("$$", "")
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def font_size_for(rect: fitz.Rect, text: str) -> float:
    if not text:
        return 6
    base = max(4.5, min(11.0, rect.height * 0.52))
    if len(text) > 120:
        base = min(base, 6.5)
    elif len(text) > 60:
        base = min(base, 8.0)
    return base


def add_text_layer(input_pdf: Path, ocr_json: Path, output_pdf: Path) -> None:
    data = json.loads(ocr_json.read_text(encoding="utf-8"))
    doc = fitz.open(str(input_pdf))
    pages = data.get("pages") or []
    if len(doc) != len(pages):
        raise SystemExit(f"page count mismatch: pdf={len(doc)} ocr={len(pages)}")

    for page_idx, page_data in enumerate(pages):
        page = doc[page_idx]
        page_rect = page.rect
        dims = page_data.get("dimensions") or {}
        source_w = float(dims.get("width") or page_rect.width)
        source_h = float(dims.get("height") or page_rect.height)
        sx = page_rect.width / source_w
        sy = page_rect.height / source_h
        for block in page_data.get("blocks") or []:
            text = clean_text(str(block.get("content") or ""))
            if not text:
                continue
            rect = fitz.Rect(
                float(block.get("top_left_x") or 0) * sx,
                float(block.get("top_left_y") or 0) * sy,
                float(block.get("bottom_right_x") or 0) * sx,
                float(block.get("bottom_right_y") or 0) * sy,
            )
            if rect.is_empty or rect.width < 8 or rect.height < 4:
                continue
            page.insert_textbox(
                rect,
                text,
                fontsize=font_size_for(rect, text),
                fontname="helv",
                color=(0, 0, 0),
                render_mode=3,
                overlay=True,
            )

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_pdf), garbage=4, deflate=True)
    doc.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Keep original PDF images and add an invisible Mistral OCR text layer.")
    parser.add_argument("--input-pdf", required=True)
    parser.add_argument("--ocr-json", required=True)
    parser.add_argument("--output-pdf", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    add_text_layer(
        Path(args.input_pdf).expanduser().resolve(),
        Path(args.ocr_json).expanduser().resolve(),
        Path(args.output_pdf).expanduser().resolve(),
    )
    print(args.output_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
