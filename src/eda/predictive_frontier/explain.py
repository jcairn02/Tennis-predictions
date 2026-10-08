"""Build a self-contained plain-language explanation from the measured study.

Run with ./python.sh src/eda/predictive_frontier/explain.py.
No model is fitted and no study result is overwritten.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/studies/predictive_frontier/results.csv"
TEMPLATE = Path(__file__).with_name("explain_template.html")
OUTPUT = ROOT / "docs/studies/predictive_frontier/explained.html"


def main():
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        results = list(csv.DictReader(handle))
    cited = []

    def get(tour, route, model, comparator="baseline", window="2019_onward"):
        selected = [r for r in results if all(r[key] == value for key, value in
                    {"tour": tour, "route": route, "model": model,
                     "comparator": comparator, "window": window}.items())]
        if len(selected) != 1:
            raise ValueError((tour, route, model, comparator, window, len(selected)))
        cited.append(selected[0])
        return selected[0]

    def number(row, column="gain_mll", digits=2, signed=True):
        return format(float(row[column]), f"{'+' if signed else ''}.{digits}f").replace("-", "−")

    def interval(row):
        return f"{number(row, 'lo_mll')} to {number(row, 'hi_mll')}"

    men = get("atp", "elo", "combined")
    women = get("wta", "elo", "combined")
    market_old = get("atp", "elo", "baseline", "raw_pinnacle")
    market_new = get("atp", "elo", "combined", "raw_pinnacle")
    gap_closed = 100 * (float(market_new["gain_mll"]) - float(market_old["gain_mll"])) / -float(market_old["gain_mll"])
    reliability = get("atp", "elo", "reliability")
    form = get("atp", "elo", "innovations")
    surface = get("atp", "elo", "surface_specialization")
    line_hint = get("atp", "pinnacle", "reliability", "raw_market")
    line_extra = get("atp", "pinnacle", "reliability")
    selector = get("atp", "elo", "past_selected")
    recent = get("atp", "elo", "combined", window="2022_onward")
    years = [get("atp", "elo", "combined", window=f"year_{year}") for year in range(2019, 2027)]
    positive_years = sum(float(r["gain_mll"]) > 0 for r in years)
    labels = [("reliability", "How much to trust the evidence"),
              ("innovations", "Performance above personal expectations"),
              ("surface_specialization", "Personal surface adjustment"),
              ("recovery", "Recovery and recent interruptions"),
              ("event_speed", "Event conditions and playing style"),
              ("combined", "All five groups of signals together")]
    table_rows = []
    for model, label in labels:
        m, w = get("atp", "elo", model), get("wta", "elo", model)
        table_rows.append('<tr' + (' class="combined-row"' if model == "combined" else '') + '>'
                          f'<th scope="row">{html.escape(label)}</th>'
                          f'<td><strong>{number(m)}</strong><small>{interval(m)}</small></td>'
                          f'<td><strong>{number(w)}</strong><small>{interval(w)}</small></td></tr>')
    values = {
        "gap_closed": f"{gap_closed:.1f}", "gap_remaining": f"{100-gap_closed:.1f}",
        "gap_gain": f"{float(market_new['gain_mll'])-float(market_old['gain_mll']):.3f}",
        "gap_original": number(market_old, signed=False, digits=3).lstrip("−"),
        "men_gain": number(men), "men_interval": interval(men), "men_n": f"{int(men['n']):,}",
        "women_gain": number(women), "women_interval": interval(women), "women_n": f"{int(women['n']):,}",
        "men_before": number(men, "comparator_ll", 6, False), "men_after": number(men, "model_ll", 6, False),
        "men_gain_decimal": f"{float(men['gain_mll']) / 1000:.6f}",
        "market_n": f"{int(market_new['n']):,}",
        "reliability_gain": number(reliability), "form_gain": number(form), "surface_gain": number(surface),
        "recovery_gain": number(get("atp", "elo", "recovery")),
        "event_gain": number(get("atp", "elo", "event_speed")),
        "line_hint": number(line_hint), "line_hint_interval": interval(line_hint),
        "line_extra": number(line_extra), "line_extra_interval": interval(line_extra),
        "selector_gain": number(selector), "recent_gain": number(recent),
        "positive_years": str(positive_years), "year_count": str(len(years)),
        "results_rows": "\n".join(table_rows),
    }
    document = TEMPLATE.read_text(encoding="utf-8")
    for key, value in values.items():
        document = document.replace("{{" + key + "}}", value)
    unresolved = re.findall(r"\{\{[^}]+\}\}", document)
    if unresolved:
        raise ValueError(unresolved)
    OUTPUT.write_text(document, encoding="utf-8")
    evidence = {
        "output": str(OUTPUT.relative_to(ROOT)), "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "template_sha256": hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "gap_closed_percent": gap_closed, "cited_measured_rows": cited,
        "illustrations": "65/100 vs 70/100 service points, sparse vs deep evidence, and the 70-wins/30-losses scoring toy are invented teaching examples, not empirical forecasts.",
    }
    (SOURCE.parent / "explanation_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}; {len(document.encode('utf-8')):,} bytes; all study scores sourced from results.csv")


if __name__ == "__main__":
    main()
