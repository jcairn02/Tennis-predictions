"""Predictability diagnostic: render the study's HTML report from the stages' JSON.

Each stage adds its section as its own module, report_stageN.py, which holds

    SECTION = {"stage": N, "id": "...", "title": "..."}
    def render(study_dir: Path) -> dict      # {"html": str, "data": dict, "script": str}

and builds its prose and numbers from that stage's JSON only. This builder assembles whatever
section modules exist into report_shell.html; the sections' data travel as one JSON block the
page's scripts read.

The page reads summary first: report_summary.py (the same contract, SECTION["stage"] = "summary")
opens the page, and the stages follow in stage order as a reference, each folded under a one-line
description of what it answers.

Reads data/studies/predictability_diagnostic/ (through the section modules);
writes docs/studies/predictability_diagnostic/report.html.
Run: ./python.sh src/eda/predictability_diagnostic/render_report.py
"""
from __future__ import annotations

import html
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

SHELL = HERE / "report_shell.html"
OUT = C.DOCS / "report.html"
LEDE = ("What predicts the winner of a professional tennis match beyond Elo ratings and the bookmakers' prices? "
        "Men's (ATP) and women's (WTA) singles, side by side.")
REPAIR_NOTICE = ('<aside style="border:2px solid #b46b26;padding:20px;margin:24px 0;background:#fff8ed;color:#382718">'
                '<strong>Historical results — superseded for the shortlisted features.</strong> '
                'The 2 October audit found event-start chronology, forecast-format and evaluation defects. '
                'Shared code is repaired; the selected features have a separate rebuild using verified match days. '
                'The numbers below remain the original historical results, including their original evidence labels. '
                '<a href="../feature_alpha_audit/repairs.html">Read the repairs and rebuilt results</a>. '
                'The simulation-based luck estimate is conditional on its point model; it is not a forecasting ceiling.</aside>')
# what each stage answers, in a line, for its folded heading
BLURBS = {0: "How the match table was built from two public sources, cleaned and checked.",
          1: "How well rankings, Elo ratings and the bookmakers predict winners.",
          2: "What decides a match: points, break points and tiebreaks, and how much is luck.",
          3: "Which player statistics are stable from season to season, and which are chance.",
          4: "Every candidate feature, tested against Elo and against the bookmakers."}
# a link to a folded stage opens it
OPEN_JS = """(function () {
  const open = id => { const t = id && document.getElementById(id); const d = t && t.closest("details"); if (d) d.open = true; };
  document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener("click", () => open(a.getAttribute("href").slice(1))));
  if (location.hash) open(location.hash.slice(1));
})();"""


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def section_modules() -> list:
    """The summary's section module if it exists, then the stages' in stage order."""
    found = []
    for path in HERE.glob("report_stage*.py"):
        m = re.fullmatch(r"report_stage(\d+)\.py", path.name)
        if not m:
            continue
        found.append((int(m.group(1)), load_module(path)))
    mods = [mod for _, mod in sorted(found, key=lambda x: x[0])]
    if (HERE / "report_summary.py").exists():
        mods.insert(0, load_module(HERE / "report_summary.py"))
    return mods


def fill(template: str, tokens: dict) -> str:
    def sub(m):
        key = m.group(1)
        if key not in tokens:
            raise KeyError(f"template token {{{{{key}}}}} has no value")
        return tokens[key]
    return re.sub(r"\{\{([A-Z_]+)\}\}", sub, template)


def main() -> int:
    parts, data, scripts, nav, stages = [REPAIR_NOTICE], {}, [], [], []
    reference_heading = False
    for mod in section_modules():
        sec = mod.SECTION
        out = mod.render(C.OUT)
        sid, title = sec["id"], html.escape(sec["title"])
        data[sid] = out.get("data", {})
        if out.get("script"):
            scripts.append(f"<script>\n{out['script']}\n</script>")
        if sec["stage"] == "summary":
            parts.append(f'  <section class="stage" id="{sid}" aria-labelledby="{sid}-h">\n'
                         f'    <div class="stage-head"><span class="stage-no">Summary</span><h2 id="{sid}-h">{title}</h2></div>\n'
                         f'{out["html"]}\n  </section>')
            nav.append(f'<li><a href="#{sid}">Summary: {title}</a></li>')
        else:
            if not reference_heading:
                parts.append('  <div class="sub" style="margin-top:48px"><h2>The detail, stage by stage</h2>'
                             '<p class="muted" style="margin-top:6px">For reference. Open a stage to read it.</p></div>')
                reference_heading = True
            parts.append(f'  <details class="stage-fold"><summary><span class="t">Stage {sec["stage"]}: {title}</span>'
                         f'<span class="d">{html.escape(BLURBS.get(sec["stage"], ""))}</span></summary>\n'
                         f'  <section class="stage" id="{sid}" aria-labelledby="{sid}-h">\n'
                         f'    <div class="stage-head"><span class="stage-no">Stage {sec["stage"]}</span><h2 id="{sid}-h">{title}</h2></div>\n'
                         f'{out["html"]}\n  </section>\n  </details>')
            nav.append(f'<li><a href="#{sid}">Stage {sec["stage"]}: {title}</a></li>')
        stages.append(str(sec["stage"]))
    scripts.append(f"<script>\n{OPEN_JS}\n</script>")
    built = json.loads((C.OUT / "stage0_summary.json").read_text(encoding="utf-8"))["generated_at"][:10]
    numbered = [s for s in stages if s != "summary"]
    tokens = {
        "DESCRIPTION": html.escape("What predicts the winner of a tennis match beyond Elo ratings and the bookmakers' "
                                   "prices: an exploratory study of the repository's ATP and WTA data."),
        "LEDE": html.escape(LEDE),
        "STATUS": html.escape("A study, not a decision · " + ("summary and " if "summary" in stages else "")
                              + "stages " + ", ".join(numbered)),
        "NAV": "".join(nav), "SECTIONS": "\n".join(parts), "SCRIPTS": "\n".join(scripts),
        "FOOT": (f"Study <code>docs/studies/predictability_diagnostic/</code> · code "
                 f"<code>src/eda/predictability_diagnostic/</code> · evidence "
                 f"<code>data/studies/predictability_diagnostic/</code> · tables built {html.escape(built)}. "
                 "Sources: Jeff Sackmann's tennis_atp and tennis_wta (CC BY-NC-SA 4.0) and Tennis My Life. "
                 "A study, not a decision."),
    }
    page = fill(SHELL.read_text(encoding="utf-8"), tokens)
    blob = json.dumps(data, separators=(",", ":"), default=float).replace("</", "<\\/")
    page = page.replace("__REPORT_DATA__", blob)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page):,} bytes; sections: {', '.join(stages)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
