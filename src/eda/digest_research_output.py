"""Scratch: parse the multi-agent research workflow output (JSON) into per-angle
markdown archives under docs/research/imported/ (unapproved research).

Run:  ./python.sh src/eda/digest_research_output.py <path_to_workflow_output_json>
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "docs" / "research" / "imported"


def load_json_loosely(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            raise
        return json.loads(text[start:end + 1])


def main(src: str) -> None:
    data = load_json_loosely(Path(src))
    if isinstance(data, dict):
        if "logs" in data:
            print("workflow logs:")
            for line in data["logs"]:
                print(f"  {line}")
        data = data["result"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for angle in data:
        key = angle["key"]
        lines = [f"# Research archive: {key}", "",
                 "*Unapproved imported research. Facts and verification verdicts below "
                 "are assertions in the input, not independently revalidated by this "
                 "importer and not project decisions.*", ""]

        lines.append("## Facts")
        for f in angle.get("facts", []):
            crit = " **[decision-critical]**" if f.get("decision_critical") else ""
            lines.append(f"\n### {f['topic']} ({f['confidence']}){crit}")
            lines.append(f"{f['fact']}")
            lines.append(f"\nSource: {f['source_url']}")

        gaps = angle.get("gaps_noticed", [])
        if gaps:
            lines.append("\n## Gaps noticed by the research agent")
            for g in gaps:
                lines.append(f"- {g}")

        ver = angle.get("verifications", [])
        if ver:
            lines.append("\n## Verifications (adversarial)")
            for v in ver:
                vd = v.get("verdict") or {}
                lines.append(f"\n### {v['topic']} — vote {v.get('vote')} — **{vd.get('verdict', '?')}**")
                lines.append(f"Corrected/current fact: {vd.get('corrected_fact', '')}")
                lines.append(f"\nEvidence: {vd.get('evidence', '')}")

        out = OUT_DIR / f"{key}.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {out} ({out.stat().st_size:,} bytes; "
              f"{len(angle.get('facts', []))} facts, {len(ver)} verifications)")


if __name__ == "__main__":
    main(sys.argv[1])
