"""Offline delivery checks: active links, registries, research syntax and archive preservation."""
import ast
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "docs/research/legacy-one-shot"


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)
    return result.stdout


def main():
    files = subprocess.run(["rg", "--files", "-g", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    broken = []
    checked = 0
    for rel in files:
        path = ROOT / rel
        if ARCHIVE in path.parents and path.name != "INDEX.md":
            continue
        checked += 1
        text = path.read_text(encoding="utf-8-sig")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            target = target.strip("<>").split("#")[0]
            if not target or re.match(r"^[a-z]+://", target):
                continue
            if not (path.parent / target).exists():
                broken.append({"file": rel, "target": target})
    if broken:
        raise AssertionError(broken)
    parsed = []
    for file in (ROOT / "src/eda/tennis_data_audit").glob("*.py"):
        ast.parse(file.read_text(encoding="utf-8-sig"), filename=str(file))
        parsed.append(file.name)
    ast.parse((ROOT / "src/eda/digest_research_output.py").read_text(encoding="utf-8"))
    # Every moved/copied original is checked against the pre-existing tracked content.
    mapping = {"README.md": "README.md", "CLAUDE.md": "CLAUDE.md",
               "src/features/README.md": "src/features/README.md", "src/models/README.md": "src/models/README.md",
               "scripts/README.md": "scripts/README.md", "data/README.md": "data/README.md"}
    tracked = git("ls-files", "docs", "config", "*.txt").decode().splitlines()
    for rel in tracked:
        target = "paper-extracts/" + rel if rel.endswith(".txt") else rel
        if (ARCHIVE / target).exists():
            mapping[rel] = target
    mismatches = []
    for original, relative in mapping.items():
        prior = git("show", "HEAD:" + original).decode("utf-8-sig").replace("\r\n", "\n")
        current = (ARCHIVE / relative).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        if relative.endswith(".md") and current.startswith("> HISTORICAL LLM RESEARCH"):
            current = current.split("\n\n", 1)[1]
        if prior != current:
            mismatches.append(original)
    if mismatches:
        raise AssertionError({"archive_content_mismatches": mismatches})
    source = json.loads((ROOT / "docs/research/tennis-data-audit/source-register.json").read_text(encoding="utf-8"))
    assert len(source) == len({r["id"] for r in source})
    for row in source:
        assert {"name", "url", "coverage", "granularity", "access", "rights", "evidence_status", "limitations"} <= row.keys()
    summary = json.loads((ROOT / "data/studies/tennis_data_audit/polymarket/audited-summary.json").read_text(encoding="utf-8"))
    assert sum(r["events"] for r in summary["classes"]) == summary["sport_window_tennis_events"]
    assert sum(r["contracts"] for r in summary["market_types"]) == summary["sport_window_contracts"]
    assert summary["positive_lifetime_volume_contracts"] + summary["zero_lifetime_volume_contracts"] + summary["missing_lifetime_volume_contracts"] == summary["sport_window_contracts"]
    result = {"active_markdown_files_checked": checked, "broken_local_links": broken,
              "archived_original_files_verified": len(mapping), "archive_content_mismatches": mismatches,
              "research_python_files_syntax_checked": parsed, "source_records": len(source),
              "unique_main_source_urls": len({r["url"] for r in source}),
              "census_classification_and_missingness_reconciliation": "pass"}
    (ROOT / "data/studies/tennis_data_audit/delivery-validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
