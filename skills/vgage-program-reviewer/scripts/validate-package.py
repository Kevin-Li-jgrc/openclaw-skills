from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


REQUIRED_FILES = (
    "SKILL.md",
    "references/result-schema.json",
    "references/rule-catalog.json",
    "references/source-manifest.json",
    "references/boundary-contract.md",
    "references/company-standard-v24.1.md",
    "references/company-standard-v26.06.md",
    "references/vgage-core-rules.md",
    "scripts/models.py",
    "scripts/xml_facts.py",
    "scripts/scan-project.py",
    "scripts/rules_structure.py",
    "scripts/rules_binding.py",
    "scripts/rules_dependencies.py",
    "scripts/rules_measurement.py",
    "scripts/rules_io.py",
    "scripts/rules_code.py",
    "scripts/rules_review_semantics.py",
    "scripts/rules_data.py",
    "scripts/run-deterministic-rules.py",
    "scripts/build-semantic-packet.py",
    "scripts/merge-and-validate-results.py",
    "scripts/render-html.py",
    "scripts/render-xlsx.py",
    "scripts/review-project.py",
    "templates/report-template.html",
)


def validate_package(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        path = root / relative_path
        if not path.is_file():
            errors.append(f"missing required file: {relative_path}")

    skill_path = root / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        if not re.match(
            r'\A---\nname: (?:[a-z0-9-]+|"[a-z0-9-]+")\n'
            r'description: (?:[^"\n]+|"[^"\n]+")\n---\n',
            text,
        ):
            errors.append("SKILL.md frontmatter must contain only valid name and description")

    json_files = (
        "references/result-schema.json",
        "references/rule-catalog.json",
        "references/source-manifest.json",
    )
    for relative_path in json_files:
        path = root / relative_path
        if not path.is_file():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {relative_path}: {exc}")

    catalog_path = root / "references" / "rule-catalog.json"
    runner_path = root / "scripts" / "run-deterministic-rules.py"
    if catalog_path.is_file() and runner_path.is_file():
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            scripts_path = str(root / "scripts")
            sys.path.insert(0, scripts_path)
            try:
                spec = importlib.util.spec_from_file_location("vgage_deterministic_runner", runner_path)
                runner = importlib.util.module_from_spec(spec)
                if spec.loader is None:
                    raise ImportError("runner loader is unavailable")
                spec.loader.exec_module(runner)
            finally:
                if sys.path and sys.path[0] == scripts_path:
                    sys.path.pop(0)
            registered = set(runner.RULES) | set(runner.CONTEXT_RULES)
            for rule in catalog.get("rules", []):
                rule_id = rule.get("rule_id")
                if rule.get("execution") in {"deterministic", "hybrid"} and rule_id not in registered:
                    errors.append(f"unregistered executable rule: {rule_id}")
        except Exception as exc:
            errors.append(f"cannot validate deterministic rule registry: {type(exc).__name__}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the staged VGAGE reviewer package")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    errors = validate_package(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("package: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
