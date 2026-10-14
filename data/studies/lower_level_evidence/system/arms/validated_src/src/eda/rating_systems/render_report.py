"""Render the HTML report of the study "rating systems against Elo".

The page opens with the summary (report_summary.py), then folds each stage's section (report_stageA.py, ...), with the
earlier studies' contract: SECTION and render(study_dir) -> {"html", "data", "script"}. The page shell and its CSS are
the predictability diagnostic's (src/eda/predictability_diagnostic/report_shell.html).

Reads data/studies/rating_systems/ (through the section modules); writes docs/studies/rating_systems/report.html.
Run after summary_results.py: ./python.sh src/eda/rating_systems/render_report.py
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

from src.eda.predictability_diagnostic import render_report as OLD_RENDER  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402

SHELL = HERE.parents[0] / "predictability_diagnostic" / "report_shell.html"
OUT = RC.DOCS / "report.html"
TITLE = "Can Glicko-2, TrueSkill or a smoothing rating beat Elo in tennis?"
LEDE = ("Glicko-2, TrueSkill, correlated-surface ratings and TrueSkill Through Time, built for tennis under the same time "
        "rule as the earlier studies' surface Elo, tuned on the same seasons and scored on the same matches: against Elo, "
        "against the bookmakers' closing prices, and beside the promising features. Men's (ATP) and women's (WTA) singles.")
BLURBS = {"A": "The systems, their frozen constants, the tuning years, the checks and probes.",
          "B": "Every system against surface Elo and the closing odds, by window, level and era; the shared test's rows.",
          "C": "The audit's feature ladder with each rating as the base, and the men's closing line."}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fold(stage: str, title: str, blurb: str, sid: str, body: str) -> str:
    return (f'  <details class="stage-fold"><summary><span class="t">Stage {html.escape(stage)}: {html.escape(title)}</span>'
            f'<span class="d">{html.escape(blurb)}</span></summary>\n'
            f'  <section class="stage" id="{sid}" aria-labelledby="{sid}-h">\n'
            f'    <div class="stage-head"><span class="stage-no">Stage {html.escape(stage)}</span><h2 id="{sid}-h">{html.escape(title)}</h2></div>\n'
            f'{body}\n  </section>\n  </details>')


def clean(x):
    """NaN and infinities are not JSON: they would break the page's one JSON.parse."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, float) and (x != x or x in (float("inf"), float("-inf"))):
        return None
    return x


def main() -> int:
    parts, data, scripts, nav = [], {}, [], []
    summ = load_module(HERE / "report_summary.py")
    out = summ.render(RC.OUT)
    sid, title = summ.SECTION["id"], summ.SECTION["title"]
    data[sid] = out.get("data", {})
    if out.get("script"):
        scripts.append(f"<script>\n{out['script']}\n</script>")
    parts.append(f'  <section class="stage" id="{sid}" aria-labelledby="{sid}-h">\n'
                 f'    <div class="stage-head"><span class="stage-no">Summary</span><h2 id="{sid}-h">{html.escape(title)}</h2></div>\n'
                 f'{out["html"]}\n  </section>')
    nav.append(f'<li><a href="#{sid}">Summary: {html.escape(title)}</a></li>')
    parts.append('  <div class="sub" style="margin-top:48px"><h2>The detail, stage by stage</h2>'
                 '<p class="muted" style="margin-top:6px">For reference. Open a stage to read it.</p></div>')
    stages = []
    for path in sorted(HERE.glob("report_stage*.py")):
        m = re.fullmatch(r"report_stage([A-Z])\.py", path.name)
        if not m:
            continue
        mod = load_module(path)
        sec = mod.SECTION
        out = mod.render(RC.OUT)
        sid, title, st = sec["id"], sec["title"], str(sec["stage"])
        data[sid] = out.get("data", {})
        if out.get("script"):
            scripts.append(f"<script>\n{out['script']}\n</script>")
        parts.append(fold(st, title, BLURBS.get(st, ""), sid, out["html"]))
        nav.append(f'<li><a href="#{sid}">Stage {html.escape(st)}: {html.escape(title)}</a></li>')
        stages.append(st)
    scripts.append(f"<script>\n{OLD_RENDER.OPEN_JS}\n</script>")
    built = json.loads((RC.OUT / "summary_results.json").read_text(encoding="utf-8"))["generated_at"][:10]
    tokens = {
        "DESCRIPTION": html.escape("Glicko-2, TrueSkill, correlated-surface ratings and TrueSkill Through Time against the "
                                   "tuned surface Elo and the closing odds, men's and women's singles 2013-2026."),
        "LEDE": html.escape(LEDE),
        "STATUS": html.escape("Leading candidate: TrueSkill Through Time (the owner, 3 Oct 2026) · summary and stages "
                              + ", ".join(stages)),
        "NAV": "".join(nav), "SECTIONS": "\n".join(parts), "SCRIPTS": "\n".join(scripts),
        "FOOT": (f"Study <code>docs/studies/rating_systems/</code> · code <code>src/eda/rating_systems/</code> · evidence "
                 f"<code>data/studies/rating_systems/</code> · the literature <code>docs/research/rating-systems/</code> · "
                 f"built {html.escape(built)}. Sources: Jeff Sackmann's tennis_atp and tennis_wta (CC BY-NC-SA 4.0), "
                 f"Tennis My Life and tennis-data.co.uk. A study; the owner's designation of TrueSkill Through Time as "
                 f"the leading candidate is recorded in <code>docs/decisions/2026-10-03-leading-rating-candidate.md</code>."),
    }
    page = OLD_RENDER.fill(SHELL.read_text(encoding="utf-8"), tokens)
    page = page.replace("<title>Tennis Predictability Diagnostic</title>", "<title>Rating Systems Against Elo</title>")
    page = page.replace('<p class="eyebrow">Tennis predictions · study · predictability diagnostic</p>',
                        '<p class="eyebrow">Tennis predictions · study · rating systems against Elo</p>')
    page = page.replace("<h1>How predictable is a tennis match, and what predicts it?</h1>", f"<h1>{html.escape(TITLE)}</h1>")
    blob = json.dumps(clean(data), separators=(",", ":"), default=float, allow_nan=False).replace("</", "<\\/")
    page = page.replace("__REPORT_DATA__", blob)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page):,} bytes; stages: {', '.join(stages) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
