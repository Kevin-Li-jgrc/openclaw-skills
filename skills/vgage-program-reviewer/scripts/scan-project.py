from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from xml_facts import (
    parse_form,
    parse_imbus_modules,
    parse_io,
    parse_io_objects,
    parse_screens,
    parse_vga,
    parse_xml,
)


UTF8_BOM = b"\xef\xbb\xbf"


def is_review_path(relative_path: Path) -> bool:
    return any(part.startswith("VGAGE_REVIEW_") for part in relative_path.parts)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_files(project_root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(project_root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file():
            continue
        relative = path.relative_to(project_root)
        if is_review_path(relative):
            continue
        stat = path.stat()
        files.append(
            {
                "relative_path": relative.as_posix(),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256(path),
            }
        )
    return files


def fingerprint(files: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in files:
        digest.update(item["relative_path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(item["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def read_code_module(path: Path, relative_path: str) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        code = raw.decode("utf-8-sig")
        utf8_decodable = True
        decode_error = None
    except UnicodeDecodeError as exc:
        code = ""
        utf8_decodable = False
        decode_error = str(exc)
    return {
        "relative_path": relative_path,
        "has_utf8_bom": raw.startswith(UTF8_BOM),
        "utf8_decodable": utf8_decodable,
        "decode_error": decode_error,
        "has_bare_lf": re.search(rb"(?<!\r)\n", raw) is not None,
        "has_bare_cr": re.search(rb"\r(?!\n)", raw) is not None,
        "code": code,
    }


def scan_project(project_root: Path, evidence_paths: list[Path]) -> dict[str, Any]:
    root = project_root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"project path is not a readable directory: {project_root}")

    files = project_files(root)
    facts: dict[str, Any] = {
        "project": {"root": str(root), "name": root.name, "fingerprint": fingerprint(files)},
        "files": files,
        "vga": {},
        "operations": [],
        "parts": [],
        "measurements": [],
        "probes": [],
        "probe_code": "",
        "probe_code_functions": [],
        "master_sets": [],
        "features": [],
        "tags": [],
        "io_points": [],
        "io_objects": [],
        "imbus_modules": [],
        "screens": [],
        "forms": [],
        "scripts": [],
        "code_module": {},
        "code_sources": [],
        "auto_archive": {},
        "evidence": [],
        "parse_errors": [],
    }

    by_name = {Path(item["relative_path"]).name.casefold(): root / item["relative_path"] for item in files}
    for filename, parser in (("vga.xml", parse_vga), ("io.xml", parse_io)):
        path = by_name.get(filename)
        if path is None:
            continue
        try:
            root_element = parse_xml(path)
            parsed = parser(root_element)
            if filename == "vga.xml":
                facts.update(parsed)
            else:
                facts["io_points"] = parsed
                facts["io_objects"] = parse_io_objects(root_element)
                facts["imbus_modules"] = parse_imbus_modules(root_element)
        except Exception as exc:  # parse errors are evidence, not scanner crashes
            facts["parse_errors"].append(
                {
                    "relative_path": path.relative_to(root).as_posix(),
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    screens_path = by_name.get("screens.xml")
    if screens_path is not None:
        try:
            facts["screens"] = parse_screens(parse_xml(screens_path))
        except Exception as exc:
            facts["parse_errors"].append(
                {
                    "relative_path": screens_path.relative_to(root).as_posix(),
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    for item in files:
        relative_path = item["relative_path"]
        if not Path(relative_path).name.casefold().endswith("form.xml"):
            continue
        path = root / relative_path
        try:
            facts["forms"].append(parse_form(parse_xml(path), relative_path))
            form = facts["forms"][-1]
            if str(form.get("code") or "").strip():
                facts["code_sources"].append(
                    {
                        "file": relative_path,
                        "surface": "Form",
                        "object": Path(relative_path).stem,
                        "code": form["code"],
                    }
                )
        except Exception as exc:
            facts["parse_errors"].append(
                {
                    "relative_path": relative_path,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    for item in files:
        if item["relative_path"].casefold().endswith(".vgs"):
            facts["scripts"].append(item)

    code_module_path = by_name.get("codemodule.vgs")
    if code_module_path is not None:
        relative_path = code_module_path.relative_to(root).as_posix()
        facts["code_module"] = read_code_module(code_module_path, relative_path)
        if facts["code_module"]["utf8_decodable"]:
            facts["code_sources"].append(
                {
                    "file": relative_path,
                    "surface": "CodeModule",
                    "object": None,
                    "code": facts["code_module"]["code"],
                }
            )

    for section, surface in (("probes", "Probe"), ("measurements", "Measurement")):
        for item in facts.get(section, []):
            equation = str(item.get("equation") or "")
            if equation.strip():
                facts["code_sources"].append(
                    {
                        "file": "VGA.xml",
                        "surface": surface,
                        "object": item.get("name"),
                        "code": equation,
                    }
                )

    for evidence_path in evidence_paths:
        path = evidence_path.expanduser().resolve()
        facts["evidence"].append(
            {
                "path": str(path),
                "exists": path.exists(),
                "sha256": sha256(path) if path.is_file() else None,
            }
        )
    return facts
