"""Render the HTML report of the study "ideas borrowed from UFC-predictions".

The page opens with this study's summary (report_summary.py: what was tried, whether it was promising and how it
did, both studies on one scale), then folds each stage's section (report_stageA.py, report_stageB.py, ... with the
same contract as the earlier study's sections: SECTION and render(study_dir) -> {"html", "data", "script"}), and
finally folds the earlier study's own summary (src/eda/predictability_diagnostic/report_summary.py, rendered from its
own tables) for reference, with a link to its full report.

Reads data/studies/ufc_ideas/ (through the section modules) and the earlier study's tables;
writes docs/studies/ufc_ideas/report.html.
Run after summary_results.py: ./python.sh src/eda/ufc_ideas/render_report.py
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
from src.eda.predictability_diagnostic import render_report as OLD_RENDER  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

SHELL = HERE.parents[0] / "predictability_diagnostic" / "report_shell.html"
OUT = U.DOCS / "report.html"
OLD_SUMMARY = HERE.parents[0] / "predictability_diagnostic" / "report_summary.py"
TITLE = "What the UFC pipeline's tools add to tennis prediction"
LEDE = ("A Bradley–Terry rating, market-embedded ratings, opponent-adjusted statistics, strength of schedule and fatigue, "
        "borrowed from the owner's UFC project and tried on the same matches and with the same test as the predictability "
        "diagnostic. Men's (ATP) and women's (WTA) singles, side by side.")
BLURBS = {"A": "A Bradley–Terry rating tuned for tennis against Elo, and a rating solved from closing odds (MESR).",
          "B": "Opponent-adjusted statistics (adjperf, adjdef), IOS ridge ratings per statistic, and performance split by the opponent's strength.",
          "C": "Strength of schedule, credit for old opponents at what they turned out to be worth, and fatigue.",
          "D": "The best of everything together, against Elo and against the bookmakers."}
STAGE_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stage_modules() -> list:
    found = []
    for path in HERE.glob("report_stage*.py"):
        m = re.fullmatch(r"report_stage([A-Z])\.py", path.name)
        if m:
            found.append((STAGE_ORDER.get(m.group(1), 99), load_module(path)))
    return [mod for _, mod in sorted(found, key=lambda x: x[0])]


def fold(stage: str, title: str, blurb: str, sid: str, body: str, label: str = "Stage") -> str:
    return (f'  <details class="stage-fold"><summary><span class="t">{label} {html.escape(stage)}: {html.escape(title)}</span>'
            f'<span class="d">{html.escape(blurb)}</span></summary>\n'
            f'  <section class="stage" id="{sid}" aria-labelledby="{sid}-h">\n'
            f'    <div class="stage-head"><span class="stage-no">{label} {html.escape(stage)}</span><h2 id="{sid}-h">{html.escape(title)}</h2></div>\n'
            f'{body}\n  </section>\n  </details>')


def main() -> int:
    parts, data, scripts, nav, stages = [OLD_RENDER.REPAIR_NOTICE], {}, [], [], []
    # the new summary
    summ = load_module(HERE / "report_summary.py")
    out = summ.render(U.OUT)
    sid, title = summ.SECTION["id"], summ.SECTION["title"]
    data[sid] = out.get("data", {})
    if out.get("script"):
        scripts.append(f"<script>\n{out['script']}\n</script>")
    parts.append(f'  <section class="stage" id="{sid}" aria-labelledby="{sid}-h">\n'
                 f'    <div class="stage-head"><span class="stage-no">Summary</span><h2 id="{sid}-h">{html.escape(title)}</h2></div>\n'
                 f'{out["html"]}\n  </section>')
    nav.append(f'<li><a href="#{sid}">Summary: {html.escape(title)}</a></li>')
    # the stages
    mods = stage_modules()
    if mods:
        parts.append('  <div class="sub" style="margin-top:48px"><h2>The detail, stage by stage</h2>'
                     '<p class="muted" style="margin-top:6px">For reference. Open a stage to read it.</p></div>')
    for mod in mods:
        sec = mod.SECTION
        try:
            out = mod.render(U.OUT)
        except FileNotFoundError as e:                 # a stage whose outputs are not on disk yet
            print(f"skipping stage {sec.get('stage')}: {e}")
            continue
        sid, title, st = sec["id"], sec["title"], str(sec["stage"])
        data[sid] = out.get("data", {})
        if out.get("script"):
            scripts.append(f"<script>\n{out['script']}\n</script>")
        parts.append(fold(st, title, BLURBS.get(st, ""), sid, out["html"]))
        nav.append(f'<li><a href="#{sid}">Stage {html.escape(st)}: {html.escape(title)}</a></li>')
        stages.append(st)
    # the earlier study's summary, for reference
    old = load_module(OLD_SUMMARY)
    out = old.render(C.OUT)
    sid, title = old.SECTION["id"], old.SECTION["title"]
    data[sid] = out.get("data", {})
    if out.get("script"):
        scripts.append(f"<script>\n{out['script']}\n</script>")
    parts.append('  <div class="sub" style="margin-top:48px"><h2>The earlier study</h2>'
                 '<p class="muted" style="margin-top:6px">The predictability diagnostic\'s own summary (2 Oct 2026), as it was written, '
                 'for reference; its full report with its five stages is '
                 '<a href="../predictability_diagnostic/report.html">report.html</a> in its own folder. Its "stages below" are there, not here.</p></div>')
    parts.append(fold("", title, "What predicts the winner beyond Elo and the bookmakers: 59 candidates in 325 versions.", sid, out["html"],
                      label="Earlier study"))
    nav.append(f'<li><a href="#{sid}">Earlier study: {html.escape(title)}</a></li>')
    scripts.append(f"<script>\n{OLD_RENDER.OPEN_JS}\n</script>")
    built = json.loads((U.OUT / "summary_results.json").read_text(encoding="utf-8"))["generated_at"][:10]
    tokens = {
        "DESCRIPTION": html.escape("Ideas borrowed from the UFC-predictions pipeline, tried on the tennis data: Bradley–Terry and "
                                   "market ratings, opponent-adjusted statistics, strength of schedule and fatigue; every feature "
                                   "tried in both studies and how it did."),
        "LEDE": html.escape(LEDE),
        "STATUS": html.escape("A study, not a decision · summary and stages " + ", ".join(stages) + " · with the earlier study's summary"),
        "NAV": "".join(nav), "SECTIONS": "\n".join(parts), "SCRIPTS": "\n".join(scripts),
        "FOOT": (f"Study <code>docs/studies/ufc_ideas/</code> · code <code>src/eda/ufc_ideas/</code> · evidence "
                 f"<code>data/studies/ufc_ideas/</code> · built {html.escape(built)}. The earlier study: "
                 f"<code>docs/studies/predictability_diagnostic/</code>. Sources: Jeff Sackmann's tennis_atp and tennis_wta "
                 f"(CC BY-NC-SA 4.0), Tennis My Life and tennis-data.co.uk. A study, not a decision."),
    }
    page = OLD_RENDER.fill(SHELL.read_text(encoding="utf-8"), tokens)
    page = page.replace("<title>Tennis Predictability Diagnostic</title>", f"<title>{html.escape(TITLE)}</title>")
    page = page.replace("<p class=\"eyebrow\">Tennis predictions · study · predictability diagnostic</p>",
                        "<p class=\"eyebrow\">Tennis predictions · study · ideas borrowed from UFC-predictions</p>")
    page = page.replace("<h1>How predictable is a tennis match, and what predicts it?</h1>", f"<h1>{html.escape(TITLE)}</h1>")
    def clean(x):
        """NaN and infinities are not JSON: they would break the page's one JSON.parse, so they become null."""
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [clean(v) for v in x]
        if isinstance(x, float) and (x != x or x in (float("inf"), float("-inf"))):
            return None
        return x
    blob = json.dumps(clean(data), separators=(",", ":"), default=float, allow_nan=False).replace("</", "<\\/")
    page = page.replace("__REPORT_DATA__", blob)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page):,} bytes; stages: {', '.join(stages) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
