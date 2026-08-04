from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from models import load_json, validate_review


SCRIPT_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_ROOT.parent


def load_script(filename: str, module_name: str):
    path = SCRIPT_ROOT / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    spec.loader.exec_module(module)
    return module


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_review_directory(project_root: Path) -> Path:
    stem = f"VGAGE_REVIEW_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    candidate = project_root / stem
    counter = 1
    while candidate.exists():
        candidate = project_root / f"{stem}_{counter:02d}"
        counter += 1
    candidate.mkdir()
    return candidate


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def run_review(project_root: Path, evidence: list[Path], project_region: str) -> tuple[int, Path | None]:
    root = project_root.expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: project path is not a readable directory: {project_root}", file=sys.stderr)
        return 3, None

    scan_module = load_script("scan-project.py", "vgage_scan_project")
    rules_module = load_script("run-deterministic-rules.py", "vgage_deterministic_rules")
    merge_module = load_script("merge-and-validate-results.py", "vgage_merge_results")
    html_module = load_script("render-html.py", "vgage_render_html")
    xlsx_module = load_script("render-xlsx.py", "vgage_render_xlsx")

    catalog_path = PACKAGE_ROOT / "references" / "rule-catalog.json"
    manifest_path = PACKAGE_ROOT / "references" / "source-manifest.json"
    catalog = load_json(catalog_path)
    manifest = load_json(manifest_path)
    before = scan_module.scan_project(root, evidence)
    relative_names = {Path(item["relative_path"]).name.casefold() for item in before["files"]}
    missing_required = [name for name in ("vga.xml", "io.xml", "codemodule.vgs") if name not in relative_names]
    execution_state = "INCOMPLETE" if before["parse_errors"] or missing_required else "COMPLETE"
    errors = list(before["parse_errors"])
    errors.extend(
        {"error_type": "MissingRequiredFile", "relative_path": name, "message": "required project file is missing"}
        for name in missing_required
    )

    context = {"project_region": project_region, "rule_exceptions": {}}
    deterministic = rules_module.run_deterministic_rules(before, catalog, context)
    merged = merge_module.merge_results(deterministic, [], catalog)
    merged = [item for item in merged if item.get("status") != "NOT_APPLICABLE"]
    overall_status = merge_module.calculate_overall_status(merged, execution_state)
    review = {
        "execution_state": execution_state,
        "overall_status": overall_status,
        "project": before["project"],
        "rule_package": {
            "catalog_version": catalog["catalog_version"],
            "effective_date": catalog["effective_date"],
            "catalog_sha256": file_sha256(catalog_path),
            "source_manifest": manifest,
        },
        "rules": merged,
        "errors": errors,
    }
    schema_errors = validate_review(review)
    if schema_errors:
        review["execution_state"] = "INCOMPLETE"
        review["overall_status"] = None
        review["errors"].extend(
            {"error_type": "ResultValidationError", "message": message} for message in schema_errors
        )

    review_dir = create_review_directory(root)
    json_path = review_dir / "review-results.json"
    html_path = review_dir / "VGAGE静态审查报告.html"
    xlsx_path = review_dir / "VGAGE程序审查清单.xlsx"
    try:
        write_json_atomic(json_path, review)
        html_module.render_html(review, html_path)
        xlsx_module.render_xlsx(review, xlsx_path)
    except Exception as exc:
        review["execution_state"] = "INCOMPLETE"
        review["overall_status"] = None
        review["errors"].append({"error_type": type(exc).__name__, "message": str(exc)})
        write_json_atomic(json_path, review)
        print(f"ERROR: output rendering failed: {exc}", file=sys.stderr)
        return 4, review_dir

    after = scan_module.scan_project(root, evidence)
    if after["project"]["fingerprint"] != before["project"]["fingerprint"]:
        review["execution_state"] = "INCOMPLETE"
        review["overall_status"] = None
        review["errors"].append(
            {"error_type": "SourceMutationDetected", "message": "source project fingerprint changed during review"}
        )
        write_json_atomic(json_path, review)
        html_module.render_html(review, html_path)
        xlsx_module.render_xlsx(review, xlsx_path)
        print("ERROR: source project changed during review", file=sys.stderr)
        return 2, review_dir

    print(str(review_dir))
    return (0 if review["execution_state"] == "COMPLETE" else 2), review_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Review a complete VGAGE Pro project")
    parser.add_argument("project_path", type=Path)
    parser.add_argument("--evidence", action="append", default=[], type=Path)
    parser.add_argument("--project-region", choices=("domestic", "overseas", "unknown"), default="unknown")
    args = parser.parse_args()
    code, _ = run_review(args.project_path, args.evidence, args.project_region)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
