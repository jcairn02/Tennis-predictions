"""Render the measured frontier study; every displayed score comes from CSV."""
from __future__ import annotations
import html
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[3] / "data/studies/predictive_frontier/matplotlib_cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/studies/predictive_frontier"
DOC = ROOT / "docs/studies/predictive_frontier"
LABELS = {"innovations": "Own-expected form", "surface_specialization": "Surface correction",
          "reliability": "Reliability / variability", "recovery": "Recovery context",
          "event_speed": "Event speed × style", "combined": "All five families",
          "past_selected": "Prior-season selector", "baseline": "Existing strong model"}


def gain(row):
    return f"{row.gain_mll:+.3f} [{row.lo_mll:+.3f}, {row.hi_mll:+.3f}]"


def table(headers, rows):
    md = "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n"
    md += "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)
    ht = '<div class="table-wrap"><table><thead><tr>'
    ht += "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr></thead><tbody>"
    ht += "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>" for row in rows)
    return md + "\n", ht + "</tbody></table></div>"


def main():
    DOC.mkdir(parents=True, exist_ok=True)
    f = pd.read_csv(OUT / "results.csv")
    summary = json.loads((OUT / "summary.json").read_text())
    meta = json.loads((OUT / "frontier_features_summary.json").read_text())
    tests = ET.parse(OUT / "tests.xml").getroot()
    suites = list(tests.iter("testsuite"))
    ntests = sum(int(s.attrib["tests"]) for s in suites)
    failed = sum(int(s.attrib.get("failures", 0)) + int(s.attrib.get("errors", 0)) for s in suites)
    skipped = sum(int(s.attrib.get("skipped", 0)) for s in suites)
    if failed or skipped:
        raise ValueError("Report requires passing, unskipped verification")

    def row(tour, route, model, comparator="baseline", window="2019_onward"):
        q = f[(f.tour == tour) & (f.route == route) & (f.model == model)
              & (f.comparator == comparator) & (f.window == window)]
        if len(q) != 1:
            raise ValueError((tour, route, model, comparator, window, len(q)))
        return q.iloc[0]

    md, ht = [], []
    def heading(text, level=2):
        md.append("#" * level + " " + text)
        ht.append(f"<h{level}>{html.escape(text)}</h{level}>")
    def para(text):
        md.append(text)
        ht.append(f"<p>{html.escape(text)}</p>")
    def addtable(headers, rows):
        m, h = table(headers, rows)
        md.append(m)
        ht.append(h)
    def link(text, url):
        md.append(f"[{text}]({url})")
        ht.append(f'<p><a href="{html.escape(url, quote=True)}">{html.escape(text)}</a></p>')

    heading("New predictive features: brainstorm and measured tests", 1)
    para("2 October 2026 · Research evidence, not a production or betting decision.")
    atp = row("atp", "elo", "combined")
    wta = row("wta", "elo", "combined")
    para(f"Observed: new features improve the strongest corrected existing Elo-based model. The combined model gains {gain(atp)} milli-log-loss for men and {gain(wta)} for women. The men's gain survives the 28-comparison adjustment used here; the women's does not. No new family demonstrates a clear increment over the existing model that already uses Pinnacle and the recent-statistics profile.")
    link("The deep brainstorm: 38 directions and 15 primary sources", "research.md")
    link("Machine-readable results, including every year and the average-market sensitivity", "../../../data/studies/predictive_frontier/results.csv")
    para("Positive means better: +1 milli-log-loss reduces average natural-log loss by 0.001. It is neither one percentage point of accuracy nor a betting return. Brackets are paired 95% intervals clustered in four-week calendar blocks. These historical seasons were examined in previous studies; even corrected and multiplicity-adjusted results remain exploratory.")

    heading("What was tested")
    addtable(["Family", "New representation", "Distinction / limitation"], [
        ["Own-expected form", "Serve/return point residuals against BOTH players' pre-match strengths; 28/182-day memory", "Old adjperf adjusts for the opponent, rather than the player's own joint expectation."],
        ["Surface correction", "Shrunk surface-specific innovation minus global innovation", "A compact correction; not a refitted full Bayesian player-by-surface model."],
        ["Reliability / variability", "Decayed point exposure and excess residual dispersion; interactions with strength", "Approximate evidence quality and volatility, not calibrated posterior uncertainty."],
        ["Recovery context", "Observed gaps, retirement losses and coverage, jointly with strength", "Rest and retirement were already studied; this is a joint representation. Missing matches are not verified rest."],
        ["Event speed × style", "Earlier-day service residuals from this edition × serve/return style", "An inferred condition proxy, not measured court speed or the published ace-speed index."],
    ])
    para(f"Built {len(sum(meta['feature_groups'].values(), []))} signed inputs on {meta['pool_matches']:,} repaired matches. Point residuals shrink with 200 prior points; surface deviations with 400; event conditions with 800. Constants were fixed before the new score run. Every new rolling feature uses strictly earlier days. Supplied Elo and serve/return ratings retain the repair's earlier-day / strictly-earlier-same-event-round rule. Current outcomes, scores, box availability and retirement status enter later updates only.")
    para("The short, long and short-minus-long form columns are linearly dependent. They expose the chosen representation and affect ridge geometry; they are not independent information. The first unpenalized extension fit failed before candidate results were produced. Extensions then used positive ridge values 0.0001, 0.001, 0.01 and 0.1; old baselines kept their original fitting and penalties. No feature was changed in response to its measured gain.")

    heading("Increment over the strong Elo model")
    para("Comparator: the repaired nine-input Elo, serve/return, recent adjusted points, short IOS, games-weighted Elo, load, surface familiarity and age combination. It is the strongest corrected existing Elo ladder, not the invalidated earlier cached model or the unrepaired paid TabPFN result. Each model uses the same complete training/target rows within tour, expanding from 2013 and evaluating from 2019.")
    addtable(["Feature addition", "Men: 18,174 matches", "Women: 16,675 matches", "Holm p: men / women"], [
        [LABELS[name], gain(row("atp", "elo", name)), gain(row("wta", "elo", name)),
         f"{row('atp', 'elo', name).holm_p_28_primary:.3g} / {row('wta', 'elo', name).holm_p_28_primary:.3g}"]
        for name in LABELS if name != "baseline"])
    para(f"The combined men's log loss changes from {atp.comparator_ll:.6f} to {atp.model_ll:.6f}; women's from {wta.comparator_ll:.6f} to {wta.model_ll:.6f}. The three useful individual men's additions are reliability, own-expected form, and surface correction. Recovery and event speed supply no clear individual gain. Their inclusion in the combined model does not establish that they are necessary.")
    para("The selector chooses among the baseline, the five families and their combination using only the prior two seasons' out-of-season losses; it defaults to the baseline with fewer than 300 eligible validation matches. Ridge choices follow the same past-only rule. The reported selector is not an oracle that picks the eventual historical winner.")
    addtable(["Window", "Men: combined", "Men: past-only selector", "Women: combined", "Women: selector"], [
        [window, gain(row("atp", "elo", "combined", window=window)), gain(row("atp", "elo", "past_selected", window=window)),
         gain(row("wta", "elo", "combined", window=window)), gain(row("wta", "elo", "past_selected", window=window))]
        for window in ("2022_onward", "2024_2025")])
    para("The men's improvement persists in 2022 onward and in the completed 2024–2025 seasons, so it is not confined to the first year following the ATP history gap. These windows were specified before scoring; they overlap and are not independent replications.")

    heading("Increment over the market-plus-statistics model")
    para("Comparator: annual Pinnacle calibration plus the 16-input recent adjperf/adjdef profile and serve/return, load, surface and age context. Men's baseline reproduces the repaired result; the women's version uses the analogous specification and is not a previously established WTA winner. Training begins in 2010. Average and Pinnacle fits use identical rows with both prices. A whole model family's features share its training-only ridge penalty, with the market coefficient unpenalized.")
    addtable(["Feature addition", "Men: 16,333 matches", "Women: 14,984 matches"], [
        [LABELS[name], gain(row("atp", "pinnacle", name)), gain(row("wta", "pinnacle", name))]
        for name in LABELS if name != "baseline"])
    para("None of these incremental intervals excludes zero. Reliability has the best men's point estimate, but its additional information beyond the existing strong market model is uncertain. Individual family results and the whole candidate ledger are retained, including negative results.")
    addtable(["Pinnacle-assisted forecast", "Men vs raw Pinnacle", "Men vs recalibrated Pinnacle", "Women vs raw Pinnacle"], [
        [LABELS[name], gain(row("atp", "pinnacle", name, "raw_market")),
         gain(row("atp", "pinnacle", name, "calibrated_market")), gain(row("wta", "pinnacle", name, "raw_market"))]
        for name in ("baseline", "reliability", "combined", "past_selected")])
    para("The men's reliability-assisted forecast has a nominal positive interval against the plain line. That is a secondary, selected comparison combining the old profile with the new family; it does not demonstrate new conditional alpha. Its gain beyond the old market-plus-profile model spans zero, and the past-only market selector also spans zero against the plain line. Do not promote the best post-hoc plain-line comparison as a discovered betting edge.")
    addtable(["Market-free forecast vs raw Pinnacle", "Men: 16,362 paired matches", "Women: 15,003 paired matches"], [
        [LABELS[name], gain(row("atp", "elo", name, "raw_pinnacle")), gain(row("wta", "elo", name, "raw_pinnacle"))]
        for name in ("baseline", "combined", "past_selected")])
    old = row("atp", "elo", "baseline", "raw_pinnacle").gain_mll
    new = row("atp", "elo", "combined", "raw_pinnacle").gain_mll
    para(f"On identical price-covered matches, the combined men's model closes {100*(new-old)/(-old):.1f}% of the remaining Elo-combination-to-Pinnacle log-loss gap. Pinnacle remains substantially better. This fraction uses the paired market subset, not the larger all-match gain.")

    heading("Annual stability and the full experiment view")
    addtable(["Year", "Men combined vs strong Elo", "Women combined vs strong Elo"], [
        [str(year) + (" (partial)" if year == 2026 else ""),
         gain(row("atp", "elo", "combined", window=f"year_{year}")),
         gain(row("wta", "elo", "combined", window=f"year_{year}"))] for year in range(2019, 2027)])
    md.append("![Paired gains by feature family and benchmark](frontier_gains.svg)")
    ht.append('<figure><img src="frontier_gains.svg" alt="Four panels of paired feature gains, with uncertainty, for men and women against Elo and the market-plus-profile baseline"><figcaption>Each panel uses its own stated strong comparator. Positive gains improve log loss; bars show pointwise 95% intervals.</figcaption></figure>')

    heading("Interpretation and next ideas")
    para("Inferred: uncertainty and a better distinction between stable ability and temporary form are productive directions for the sporting model. The market appears to contain much of this information already. These results do not imply a ceiling on pre-match predictability, nor do they rule out richer surface, condition or style models.")
    para("Suggested next experiments: a full joint surface-aware serve/return model; uncertainty integrated through the point-to-match conversion; and, among data already held, unreturned-serve quality, rally-length matchups, and serve-direction versus return-vulnerability interactions. The 38-idea register distinguishes these from raw statistics already tested. Shot-chart and tracking ideas were researched but not tested in this batch: their player/event joins, definitions and historical publication times need separate validation. This report does not claim to complete the existing shot-level study.")
    link("Primary-source rationale: Ingram's point-based hierarchical tennis model", "https://martiningram.github.io/papers/bayes_point_based.pdf")
    link("Primary-source rationale: Gollub's serve forecasting and shrinkage study", "https://journals.sagepub.com/doi/10.3233/JSA-200345")

    heading("Coverage, inference and verification")
    para("Accepted histories are main-tour matches with provider-supported match days; undated lower-level history is excluded. The repaired table spans 2010-01-03 to 2026-08-02, with no rows after the study's 2026-10-02 date. ATP 2018 is almost entirely absent: its 17 rows are 31 December matches from 2019-season editions. Pinnacle coverage in 2026 ends on 13 January for men and 14 January for women, while the model-only evaluation reaches August. Missing history changes exposure, apparent rest and rating quality.")
    para("Common complete cases preserve comparability within each route but differ between routes. Exact match-end, statistic-publication and quote timestamps remain unavailable; the feature chronology assumes prior-day results are available. Retrospective source matching establishes identity, not an executable forecasting feed. Published bookmaker rows are not verified tradable closing quotes; no returns, fees, spreads or settlement-specific betting test was run.")
    para("Holm adjustment covers 28 primary tests: five families, combined and selector, across two tours and the two primary routes, against their strong baselines in 2019 onward. Pointwise intervals and secondary raw-line/recent-window comparisons are not selection-adjusted. The correction does not undo previous study selection, guarantee independent calendar blocks, or prove robustness to serial player dependence across blocks.")
    maxerr = max(v["max_abs_error"] for v in summary["baseline_reproduction"])
    para(f"Verification: {ntests} tests passed; zero skipped, failed or errored. Checks cover actual-date overlap mutations through rebuilt upstream ratings, current/future-result isolation with responsive later controls, day/event separation, paired invalid-box exclusion, surface pooling, gap decay, side exchange, training-only scaling, and past-only model selection. Cached baseline target coverage and labels match; maximum forecast difference is {maxerr:.2g}. Input hashes and coefficients are saved; original study outputs were read, not overwritten.")
    link("Frozen scoring protocol and input hashes", "../../../data/studies/predictive_frontier/protocol.json")
    link("Feature definitions, constants, hashes and coverage", "../../../data/studies/predictive_frontier/frontier_features_summary.json")
    link("Test evidence", "../../../data/studies/predictive_frontier/tests.xml")
    link("Previous corrected study", "../feature_alpha_audit/repairs.md")
    heading("Reproduce")
    command = "\n".join(["./python.sh -m src.eda.predictive_frontier.features",
        "./python.sh src/eda/predictive_frontier/score.py",
        "./python.sh -m pytest test/predictive_frontier test/feature_alpha_audit/test_repair_score.py test/feature_alpha_audit/test_profile_retest.py test/feature_alpha_audit/test_elo_retest.py -p no:cacheprovider --basetemp=data/studies/predictive_frontier/pytest_reproduction --junitxml=data/studies/predictive_frontier/tests.xml",
        "./python.sh src/eda/predictive_frontier/report.py",
        "./python.sh src/eda/feature_alpha_audit/check_report.py --document docs/studies/predictive_frontier/report.html --output-dir data/studies/predictive_frontier"])
    md.append("```bash\n" + command + "\n```")
    ht.append("<pre><code>" + html.escape(command) + "</code></pre>")
    para("On this Windows machine run through Git Bash with C:/Users/zerom/miniforge3/envs/tennis/Library/bin prepended to PATH. Use a fresh pytest temporary directory. No new package, paid model call or dataset acquisition was required.")

    # Scientific forest plot: standalone SVG and PNG artifacts, generated from measured CSV.
    names = [name for name in LABELS if name != "baseline"]
    plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans"})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5), constrained_layout=True, sharex="row")
    for ax, (tour, route) in zip(axes.flat, [("atp", "elo"), ("wta", "elo"), ("atp", "pinnacle"), ("wta", "pinnacle")]):
        rows = [row(tour, route, name) for name in names]
        values = np.array([r.gain_mll for r in rows])
        low, high = np.array([r.lo_mll for r in rows]), np.array([r.hi_mll for r in rows])
        ax.errorbar(values, np.arange(len(names)), xerr=np.vstack([values-low, high-values]),
                    fmt="o", color="#176c70", ecolor="#78989b", capsize=3)
        ax.axvline(0, color="#9ca6b0", linewidth=1)
        ax.set_yticks(np.arange(len(names)), [LABELS[n] for n in names])
        ax.invert_yaxis()
        ax.set_title(f"{'Men' if tour == 'atp' else 'Women'} · {'strong Elo model' if route == 'elo' else 'Pinnacle + existing profile'}")
        ax.set_xlabel("Incremental improvement (milli-log-loss)")
        ax.grid(axis="x", alpha=.15)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("New information helps the Elo model; closing-line increments remain uncertain", fontsize=14)
    fig.savefig(DOC / "frontier_gains.svg")
    fig.savefig(DOC / "frontier_gains.png", dpi=150)
    plt.close(fig)
    (DOC / "README.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")
    css = """body{margin:0;background:#f5f7f9;color:#152c3a;font:16px/1.65 system-ui,sans-serif}main{max-width:1130px;margin:0 auto;padding:42px 30px 72px}h1{font-size:38px;line-height:1.15;letter-spacing:-1px;max-width:950px}h2{margin-top:42px;font-size:24px;line-height:1.3}p{max-width:1040px}a{color:#07696e}table{border-collapse:collapse;font-size:14px;min-width:640px;width:100%;background:white}th,td{text-align:left;vertical-align:top;padding:11px 13px;border-bottom:1px solid #e1e8ec}th{background:#e7eff2}td:first-child{font-weight:550}.table-wrap{overflow-x:auto;border:1px solid #d8e2e7;border-radius:8px;margin:20px 0}pre{overflow:auto;background:#e7eff2;padding:20px;font-size:13px}figure{margin:24px 0}img{width:100%;height:auto}figcaption{font-size:13px;color:#526a78}@media(max-width:600px){main{padding:24px 16px}h1{font-size:29px}h2{font-size:22px}body{font-size:15px}}"""
    document = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tennis predictive frontier — measured study</title><style>' + css + '</style></head><body><main>' + "\n".join(ht) + "</main></body></html>"
    (DOC / "report.html").write_text(document, encoding="utf-8")
    print(f"Wrote reports and forest plot; {ntests} verified tests; {len(f)} measured comparison rows")


if __name__ == "__main__":
    main()
