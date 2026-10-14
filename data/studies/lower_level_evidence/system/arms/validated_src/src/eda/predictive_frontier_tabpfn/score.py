"""Score the single saved ATP/2026 Thinking fit and write a layperson report.

This module makes no API requests. It refuses absent, mismatched or incomplete
paid-run receipts. Every reported gain is calculated on identical match rows.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.predictive_frontier_tabpfn import common as C, guard as G

REPORT = ROOT / "docs/studies/predictive_frontier_tabpfn/report.html"
EPS = 1e-10
LABELS = {
    "tabpfn": "TabPFN 3.5 Thinking · 36 inputs",
    "logistic_combined_fixed": "Logistic regression · same 36 inputs",
    "logistic_strong_fixed": "Logistic regression · original 9 inputs",
    "logistic_combined_annual": "Earlier annual logistic · 36 inputs",
    "p_avg_a": "Average closing line · raw",
    "average_calibrated": "Average closing line · calibrated",
    "p_ps_a": "Pinnacle closing line · raw",
    "pinnacle_calibrated": "Pinnacle closing line · calibrated",
}
SPORTS_MODELS = ["tabpfn", "logistic_combined_fixed", "logistic_strong_fixed", "logistic_combined_annual"]


def loss(y, probability):
    """Natural-log binary loss, with one common numerical boundary rule."""
    y, p = np.asarray(y, dtype=float), np.asarray(probability, dtype=float)
    if y.shape != p.shape or not np.isin(y, [0., 1.]).all():
        raise ValueError("Targets must be binary and aligned with probabilities")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Scored probabilities must be finite and in [0, 1]")
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))


def symmetrize(original, swapped):
    a, b = np.asarray(original, dtype=float), np.asarray(swapped, dtype=float)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError("A/B orientation predictions must have identical 1D shapes")
    return .5 * (a + 1 - b)


def paired_interval(delta, dates):
    """Match-weighted gain with a cluster-t interval over fixed 28-day blocks."""
    delta = np.asarray(delta, dtype=float)
    dates = np.asarray(dates, dtype="datetime64[D]")
    if delta.ndim != 1 or dates.shape != delta.shape or not np.isfinite(delta).all() or np.isnat(dates).any():
        raise ValueError("Paired losses and valid dates must align")
    if not len(delta):
        return {"clusters": 0, "gain_mll": None, "lo_mll": None, "hi_mll": None}
    blocks = (dates - np.datetime64("2010-01-04")).astype(int) // 28
    ids, inverse = np.unique(blocks, return_inverse=True)
    mean, n, g = float(delta.mean()), len(delta), len(ids)
    if g < 2:
        return {"clusters": g, "gain_mll": 1000 * mean, "lo_mll": None, "hi_mll": None}
    influence = np.bincount(inverse, weights=delta - mean, minlength=g)
    se = np.sqrt(g / (g - 1) * np.dot(influence, influence)) / n
    radius = float(student_t.ppf(.975, g - 1) * se)
    return {"clusters": g, "gain_mll": 1000 * mean,
            "lo_mll": 1000 * (mean - radius), "hi_mll": 1000 * (mean + radius)}


def compare(frame, base, model, subset, mask):
    mask = np.asarray(mask, dtype=bool)
    mask &= np.isfinite(frame[base].to_numpy(dtype=float)) & np.isfinite(frame[model].to_numpy(dtype=float))
    part = frame.loc[mask]
    if not len(part):
        return {"subset": subset, "base": base, "model": model, "n": 0,
                "base_ll": None, "model_ll": None, "first_date": None, "last_date": None,
                **paired_interval([], [])}
    b, m = loss(part.a_won, part[base]), loss(part.a_won, part[model])
    return {"subset": subset, "base": base, "model": model, "n": len(part),
            "base_ll": float(b.mean()), "model_ll": float(m.mean()),
            "first_date": str(part.tournament_date.min().date()),
            "last_date": str(part.tournament_date.max().date()),
            **paired_interval(b - m, part.tournament_date)}


def summarize(frame):
    if len(frame) == 0 or not frame.tour.eq("atp").all() or not frame.year.eq(2026).all():
        raise ValueError("Scoring is restricted to ATP men in 2026")
    if frame.match_id.duplicated().any():
        raise ValueError("Each test match must occur exactly once")
    for name in SPORTS_MODELS:
        loss(frame.a_won, frame[name])
    subsets = {"all_2026": np.ones(len(frame), dtype=bool),
               "average_closing": np.isfinite(frame.p_avg_a.to_numpy(dtype=float)),
               "pinnacle_closing": np.isfinite(frame.p_ps_a.to_numpy(dtype=float))}
    tables, comparisons = [], []
    for subset, mask in subsets.items():
        models = SPORTS_MODELS.copy()
        if subset == "average_closing":
            models += ["p_avg_a", "average_calibrated"]
        elif subset == "pinnacle_closing":
            models += ["p_ps_a", "pinnacle_calibrated"]
        part = frame.loc[mask]
        for model in models:
            if len(part) and not np.isfinite(part[model].to_numpy(dtype=float)).all():
                raise ValueError(f"Missing {model} predictions on the common {subset} subset")
            tables.append({"subset": subset, "model": model, "n": len(part),
                           "log_loss": float(loss(part.a_won, part[model]).mean()) if len(part) else None})
        bases = ["logistic_combined_fixed", "logistic_strong_fixed", "logistic_combined_annual"]
        if subset == "average_closing":
            bases += ["p_avg_a", "average_calibrated"]
        elif subset == "pinnacle_closing":
            bases += ["p_ps_a", "pinnacle_calibrated"]
        for base in bases:
            comparisons.append(compare(frame, base, "tabpfn", subset, mask.copy()))
        for base in models[len(SPORTS_MODELS):]:
            comparisons.append(compare(frame, base, "logistic_combined_fixed", subset, mask.copy()))
    return {"scores": tables, "comparisons": comparisons}


def load():
    train_x, _, query_x, ids, manifest = C.load_upload()
    if len(C.NAMES) != 36 or "tour_code" in C.NAMES:
        raise ValueError("This report requires exactly 36 sporting inputs and no tour flag")
    full = pd.read_parquet(C.OUT / "frame.parquet")
    test = full[full.split.eq("test")].reset_index(drop=True)
    train = full[full.split.eq("train")]
    if not full.tour.eq("atp").all() or not train.year.le(2025).all() or not test.year.eq(2026).all():
        raise ValueError("Prepared rows violate men-only pre-2026 training / 2026 test")
    if len(train) != len(train_x) or train.tournament_date.max() >= test.tournament_date.min():
        raise ValueError("Training and test chronology/counts do not match the upload")
    base = pd.read_parquet(C.OUT / "baselines.parquet")
    if not np.array_equal(base.match_id.to_numpy(), test.match_id.to_numpy()):
        raise ValueError("Baseline match IDs/order differ from the frozen test rows")
    for name in base.columns.drop("match_id"):
        test[name] = base[name].to_numpy()
    n = len(test)
    if len(query_x) != 2 * n or not np.array_equal(ids.match_id.iloc[:n].to_numpy(), test.match_id.to_numpy()):
        raise ValueError("Prediction IDs do not describe the frozen test matches")
    binding = G.binding_for(manifest["input_sha256"], manifest["config"])
    path = C.THINKING / "predictions.npz"
    complete = json.loads((C.THINKING / "COMPLETE.json").read_text(encoding="utf-8"))
    if any(complete.get(k) != v for k, v in binding.items()):
        raise ValueError("Completion receipt belongs to another paid request")
    if (complete.get("status") != "COMPLETE" or complete.get("fit_requests_dispatched") != 1
            or complete.get("prediction_requests_dispatched") != 1
            or complete.get("prediction_sha256") != C.sha256_file(path)
            or complete.get("query_rows") != 2 * n):
        raise ValueError("A complete one-fit/one-prediction receipt is required")
    for name in ("fit_slot.json", "predict_slot.json", "fit_complete.json"):
        if not (C.THINKING / name).exists():
            raise ValueError(f"Missing paid-run receipt: {name}")
        record = json.loads((C.THINKING / name).read_text(encoding="utf-8"))
        receipt_binding = record.get("binding", record)
        if any(receipt_binding.get(k) != v for k, v in binding.items()):
            raise ValueError(f"Paid-run receipt belongs to another request: {name}")
    _, p_a, metadata, _ = G.load_predictions(path, binding, 2 * n)
    if metadata != complete.get("metadata"):
        raise ValueError("Prediction metadata differs from the completion receipt")
    test["tabpfn_original"] = p_a[:n]
    test["tabpfn_swapped"] = p_a[n:]
    test["tabpfn"] = symmetrize(p_a[:n], p_a[n:])
    gap = np.abs(p_a[:n] - (1 - p_a[n:]))
    info = {"manifest": manifest, "metadata": metadata, "receipt": complete,
            "training_rows": len(train), "test_rows": n, "query_rows": 2 * n,
            "train_first_date": str(train.tournament_date.min().date()),
            "train_last_date": str(train.tournament_date.max().date()),
            "test_first_date": str(test.tournament_date.min().date()),
            "test_last_date": str(test.tournament_date.max().date()),
            "training_year_counts": {str(k): int(v) for k, v in train.groupby("year").size().items()},
            "asymmetry_mean_abs": float(gap.mean()), "asymmetry_p95": float(np.quantile(gap, .95)),
            "asymmetry_max": float(gap.max())}
    for key, file in (("run", "thinking_run.json"), ("preflight", "preflight.json"), ("baselines", "baselines_meta.json")):
        path = C.OUT / file
        info[key] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    return test, info


def _esc(value):
    return html.escape(str(value), quote=True)


def _fmt(value, places=5):
    return "Unavailable" if value is None else f"{value:.{places}f}"


def _interval(record):
    if record["lo_mll"] is None:
        return "Unavailable: fewer than two time blocks"
    return f"{record['lo_mll']:+.2f} to {record['hi_mll']:+.2f}"


def training_choice_html(selection):
    """Explain the frozen history choice without making the reader inspect JSON."""
    candidates = selection.get("candidates", [])
    if not candidates:
        return ""
    best = {}
    for record in candidates:
        strategy = record["strategy"]
        if strategy not in best or record["log_loss"] < best[strategy]["log_loss"]:
            best[strategy] = record
    names = {"all": "All eligible history", "latest6": "Latest six calendar years", "latest4": "Latest four calendar years"}
    ranges = {"all": "2013–2025", "latest6": "2020–2025", "latest4": "2022–2025"}
    chosen = selection["strategy"]
    rows = "".join(
        f'<tr class="{"best" if strategy == chosen else ""}"><td>{_esc(names.get(strategy, strategy))}'
        f'{" · selected" if strategy == chosen else ""}</td><td>{ranges.get(strategy, "See manifest")}</td>'
        f'<td>{record["log_loss"]:.6f}</td><td>{record["penalty"]:g}</td></tr>'
        for strategy, record in best.items())
    years = ", ".join(map(str, selection.get("validation_years", [])))
    n = best[chosen]["validation_rows"]
    gain = (best.get("all", best[chosen])["log_loss"] - best[chosen]["log_loss"]) * 1000
    detail = f"Its validation advantage over using all available history was {gain:.2f} milli-log-loss (a log-loss reduction of {gain / 1000:.6f}). This is a small advantage, not proof of a universally best training window." if chosen != "all" else "Keeping all eligible history had the lowest validation loss among the windows checked."
    return f'''<section><h2>Why train on {ranges.get(chosen, 'this history')}?</h2><p>We compared three ways to choose training history before looking at this experiment's 2026 scores. Each strategy predicted the same {n:,} validation matches in {years}. To predict a validation season, its model saw only earlier seasons. For example, the six-year strategy predicted 2025 using 2019–2024, then used 2020–2025 for the final 2026 fit.</p><div class="scroll"><table><thead><tr><th>History strategy</th><th>Final training years</th><th>Validation log loss ↓</th><th>Chosen ridge</th></tr></thead><tbody>{rows}</tbody></table></div><p><b>{_esc(names.get(chosen, chosen))} had the lowest validation log loss.</b> {detail}</p><p class="caption">Each row shows that history's best ridge setting from the fixed search. Ridge gently limits the 27 new feature weights to reduce fitting noise. This selection used logistic regression as a proxy; the single paid TabPFN fit uses the selected history, so this experiment cannot determine which history TabPFN itself would prefer.</p></section>'''


def render_report(result, info):
    """Return standalone HTML, using only the actual saved-run statistics."""
    comparisons = result["comparisons"]
    main = next(r for r in comparisons if r["subset"] == "all_2026" and r["base"] == "logistic_combined_fixed")
    gain = main["gain_mll"]
    headline = "TabPFN had lower log loss than logistic regression." if gain > 0 else "Logistic regression had lower log loss than TabPFN." if gain < 0 else "The two models tied on log loss."
    certainty = ("The paired uncertainty interval stays above zero, supporting a TabPFN improvement in this sample."
                 if main["lo_mll"] is not None and main["lo_mll"] > 0 else
                 "The paired uncertainty interval stays below zero, supporting the logistic model in this sample."
                 if main["hi_mll"] is not None and main["hi_mll"] < 0 else
                 "The paired uncertainty interval includes zero, so this sample does not clearly separate the models.")
    average = next(r for r in comparisons if r["subset"] == "average_closing" and r["base"] == "p_avg_a" and r["model"] == "tabpfn")
    market_takeaway = (f"The average closing line still had lower log loss than TabPFN: {average['base_ll']:.5f} versus {average['model_ll']:.5f}, on the same {average['n']:,} matches."
                       if average["n"] and average["gain_mll"] < 0 else
                       f"TabPFN had lower log loss than the average closing line on the {average['n']:,} paired matches; the detailed uncertainty interval is below."
                       if average["n"] and average["gain_mll"] > 0 else
                       "The average closing-line comparison is shown below.")
    manifest, config = info["manifest"], info["manifest"]["config"]
    summary_cards = f'''<div class="stats"><div><span>Training matches</span><strong>{info['training_rows']:,}</strong><small>{_esc(info['train_first_date'])} → {_esc(info['train_last_date'])}</small></div><div><span>2026 test matches</span><strong>{info['test_rows']:,}</strong><small>{_esc(info['test_first_date'])} → {_esc(info['test_last_date'])}</small></div><div><span>Model inputs</span><strong>36</strong><small>9 established inputs + 27 new features</small></div><div><span>Paid Thinking fits</span><strong>1</strong><small>Men only · no market odds as inputs</small></div></div>'''
    sections = []
    titles = {"all_2026": "The direct model comparison", "average_closing": "Against the average closing line", "pinnacle_closing": "Against Pinnacle's closing line"}
    for subset in titles:
        records = [r for r in result["scores"] if r["subset"] == subset]
        n = records[0]["n"]
        best = min((r["log_loss"] for r in records if r["log_loss"] is not None), default=None)
        rows = "".join(f'<tr class="{"best" if r["log_loss"] == best and best is not None else ""}"><td>{_esc(LABELS[r["model"]])}</td><td>{r["n"]:,}</td><td>{_fmt(r["log_loss"])}</td></tr>' for r in records)
        paired = [r for r in comparisons if r["subset"] == subset and r["model"] == "tabpfn"
                  and (r["base"] == "logistic_combined_fixed" if subset == "all_2026" else r["base"] in ("p_avg_a", "average_calibrated", "p_ps_a", "pinnacle_calibrated"))]
        gains = "".join(f'<tr><td>{_esc(LABELS[r["base"]])}</td><td>{r["gain_mll"]:+.2f}</td><td>{_interval(r)}</td></tr>' for r in paired if r["gain_mll"] is not None)
        note = "Each model is scored on exactly the same 2026 matches. The earlier annual model is a reference from the existing study; its tuning history may differ."
        if subset == "average_closing":
            note = f"{n:,} of {info['test_rows']:,} test matches have an average closing quote. All rows in this table use that same subset. This benchmark averages the bookmakers represented in the source."
        elif subset == "pinnacle_closing":
            available = next((r for r in paired if r["n"]), None)
            period = f" ({available['first_date']} to {available['last_date']})" if available else ""
            note = f"Only {n:,} of {info['test_rows']:,} test matches have a Pinnacle quote{period}. This small, early-season subset cannot establish performance against Pinnacle across 2026."
            if available:
                note += f" Its dates occupy only {available['clusters']} of the fixed 28-day time blocks; uncertainty estimates based on so few blocks are unreliable."
        sections.append(f'''<section><h2>{titles[subset]}</h2><p>{note}</p><div class="scroll"><table><thead><tr><th>Forecast</th><th>Matches</th><th>Log loss ↓</th></tr></thead><tbody>{rows}</tbody></table></div><h3>TabPFN's gain over the comparator</h3><p class="caption">Positive = TabPFN better. A gain of +1.00 here means log loss fell by 0.001.</p><div class="scroll"><table><thead><tr><th>Comparator</th><th>Gain (milli-log-loss)</th><th>Paired 95% interval</th></tr></thead><tbody>{gains or '<tr><td colspan="3">No paired closing quotes available.</td></tr>'}</tbody></table></div></section>''')
    run = info.get("run") or {}
    quote = (info.get("preflight") or {}).get("total_quoted")
    cost = f"The provider token counter increased by {run['tokens_monthly_delta']:,} tokens." if "tokens_monthly_delta" in run else "A final provider token-counter change was not recorded."
    if quote is not None:
        cost += f" The preflight estimate was {quote:,} tokens."
    if "wall_seconds" in run:
        cost += f" The recorded dispatch-to-completion time was {run['wall_seconds'] / 60:.1f} minutes."
    metadata = info["metadata"]
    runtime = metadata.get("tabpfn_config", {}).get("model_path", config["model_path"])
    n_estimators = metadata.get("n_estimators")
    estimator_note = f"The server reported {n_estimators} prediction estimators." if n_estimators is not None else "The server did not report the final estimator count."
    training = manifest.get("training_selection", manifest.get("train_selection", {}))
    protocol = manifest.get("protocol", {})
    details = {"training_selection": training, "protocol": protocol, "requested_config": config,
               "returned_model_metadata": metadata, "training_year_counts": info["training_year_counts"],
               "input_sha256": manifest["input_sha256"],
               "symmetry": {k: info[k] for k in ("asymmetry_mean_abs", "asymmetry_p95", "asymmetry_max")}}
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Men's tennis: TabPFN vs logistic regression in 2026</title><style>
:root{{--ink:#142b36;--muted:#536774;--paper:#f5f7f6;--line:#d9e2df;--accent:#096954;--tint:#eaf6ee}}*{{box-sizing:border-box}}body{{margin:0;color:var(--ink);background:var(--paper);font:17px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}}main{{max-width:1100px;margin:auto;padding:44px 24px 70px}}header{{padding:24px 0 30px}}.eyebrow{{letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-size:12px;font-weight:750}}h1{{font-size:clamp(30px,4.7vw,51px);line-height:1.12;max-width:880px;margin:14px 0 22px;letter-spacing:-.025em}}h2{{font-size:26px;line-height:1.25;margin:0 0 15px}}h3{{font-size:18px;margin:26px 0 5px}}p{{max-width:850px;margin:10px 0 17px}}.lead{{font-size:21px}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:25px 0}}.stats>div{{padding:20px;background:white;border:1px solid var(--line);border-radius:12px}}.stats span,.stats small{{display:block;color:var(--muted);font-size:13px}}.stats strong{{display:block;font-size:33px;line-height:1.3;margin:6px 0}}section{{margin:24px 0;padding:29px;background:white;border:1px solid var(--line);border-radius:14px}}.takeaway{{background:var(--tint);border-left:5px solid var(--accent)}}.callout{{font-size:23px;font-weight:700;margin:0 0 12px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;margin:16px 0;font-size:15px}}th,td{{padding:13px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{font-size:12px;text-transform:uppercase;letter-spacing:.025em;color:var(--muted);background:#f4f7f6}}td:nth-child(n+2){{font-variant-numeric:tabular-nums;white-space:nowrap}}.best{{background:var(--tint)}}.caption,small,footer{{font-size:13px;color:var(--muted)}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:25px}}li{{margin:11px 0}}a{{color:var(--accent)}}details{{margin:25px 0}}summary{{cursor:pointer;font-weight:650}}pre{{overflow:auto;font-size:12px;background:#f2f5f4;padding:18px;border-radius:8px;max-height:500px}}code{{font-size:.9em;overflow-wrap:anywhere}}footer{{margin:32px 0 0}}@media(max-width:760px){{main{{padding:22px 14px 40px}}section{{padding:20px 17px}}.stats{{grid-template-columns:1fr 1fr}}.two{{grid-template-columns:1fr;gap:5px}}table{{font-size:13px}}th,td{{padding:11px 8px}}}}@media print{{body{{background:white;font-size:12px}}main{{padding:0}}section{{break-inside:avoid}}details{{display:none}}}}
</style></head><body><main>
<header><div class="eyebrow">One fit · ATP men only · 2026 test</div><h1>Can TabPFN improve the tennis forecast?</h1><p class="lead">We gave TabPFN 3.5 Thinking and logistic regression the same 36 sporting inputs and the same training matches, then compared their forecasts on men's matches played in 2026.</p>{summary_cards}</header>
<section class="takeaway"><p class="callout">{headline}</p><p>TabPFN log loss: <b>{main['model_ll']:.5f}</b>. Logistic log loss: <b>{main['base_ll']:.5f}</b>. TabPFN's gain was <b>{gain:+.2f} milli-log-loss</b> (95% interval: {_interval(main)}).</p><p>{certainty}</p><p><b>{market_takeaway}</b></p></section>
<section><h2>How to read the results</h2><div class="two"><div><h3>Log loss: lower is better</h3><p>This scores the probability attached to what actually happened. Correct, confident forecasts earn a better score; confident mistakes receive a larger penalty. A model that always says “50–50” scores about <b>0.69315</b>.</p><p>A 70% forecast for the eventual winner scores about 0.357. A 90% forecast for the loser scores about 2.303. We average that penalty across the matches.</p></div><div><h3>The closing line: a strong benchmark</h3><p>The source describes these odds as late pre-match prices. We turn each player's price into an implied probability, then scale the pair to sum to 100%, removing the quoted margin proportionally. Exact historical quote timestamps have not been verified.</p><p>“Raw” uses that normalized probability directly. “Calibrated” adjusts its confidence using training matches only. Beating logistic regression shows an improvement over our model; beating the closing line is a separate question.</p></div></div></section>
{''.join(sections)}
{training_choice_html(training)}
<section><h2>What was trained, and what was held back?</h2><ol><li><b>Men only.</b> Neither model was trained on women's matches. Each training row is one men's singles match.</li><li><b>Choose history before 2026.</b> Candidate training histories were compared using earlier validation seasons ending in 2025. The selected history was then frozen for both models. This uses logistic validation as a practical proxy; one TabPFN fit cannot establish TabPFN's best history length.</li><li><b>Use the same 36 inputs.</b> These are the established 9 inputs, including Elo and serve/return strength, plus the 27 new performance, reliability, recovery and event-condition features. Closing prices, player names and match outcomes are excluded from the input columns.</li><li><b>Fit once, then test in 2026.</b> Model weights stay fixed through the test. Sporting features can update from earlier matches as the season proceeds, following the repaired study's historical availability rules.</li><li><b>Handle player order consistently.</b> One prediction request contains each test match in both player orders. We average the two equivalent win probabilities. That means {info['query_rows']:,} query rows, but only {info['test_rows']:,} distinct test matches.</li></ol><p>The logistic model is a probability regression with one coefficient per feature; the 27 new coefficients have a selected ridge penalty. TabPFN uses its pretrained tabular model and the provider's high-effort Thinking procedure. Both are judged on probabilities, using log loss.</p></section>
<section><h2>How strong is this evidence?</h2><ul><li><b>2026 was excluded from this fit and its history selection, but it is not untouched research data.</b> This project's earlier feature study had already examined these years and outcomes.</li><li><b>The test covers the available part of 2026.</b> It runs through {_esc(info['test_last_date'])}; it is not a complete season. The underlying archive also has very little ATP data in 2018.</li><li><b>The uncertainty interval groups nearby matches.</b> We compare losses match by match, then group dates into 28-day blocks. The interval describes sampling uncertainty in this test; it does not cover different random seeds, alternative training choices or all previous feature searches. Secondary comparisons are exploratory.</li><li><b>The historical timing has limits.</b> Features use reconstructed match days, not exact match timestamps. The new rolling features use earlier days; some established features allow an earlier round in the same event on the same day. Exact historical quote/publication times remain unverified.</li><li><b>One fitted configuration is one experiment.</b> Internal Thinking validation is controlled by the provider and is not guaranteed to follow time order. The outer boundary still keeps all 2026 targets out of training.</li><li><b>Prediction quality is not a betting profit result.</b> These scores do not measure executable prices, commission, limits or actual returns. Matches ending in retirement follow the study's winner/advancement label; bookmakers can settle them differently.</li></ul></section>
<section><h2>The actual run</h2><p>One completed hosted Thinking fit and one prediction request are recorded. Requested model: <code>{_esc(config['model_path'])}</code>; returned model: <code>{_esc(runtime)}</code>. Settings: high Thinking effort, log-loss objective, seed {_esc(config['random_state'])}, {config['n_estimators']} estimators requested. {estimator_note}</p><p>{cost} Token-counter movement is not a dollar-cost receipt and may include other account activity.</p><p class="caption">Provider documentation for the settings and token accounting: <a href="https://docs.priorlabs.ai/capabilities/thinking-mode">Thinking mode</a> · <a href="https://docs.priorlabs.ai/api-reference/metering">API metering</a>. Checked 2 October 2026 (Pacific). The scores above come from our saved run, not provider benchmarks.</p><details><summary>Technical details and the training-selection record</summary><pre>{_esc(json.dumps(details, indent=2, allow_nan=False))}</pre></details><p class="caption">Reproduce scoring from saved predictions: <code>./python.sh src/eda/predictive_frontier_tabpfn/score.py</code>. This does not call the paid API.</p><p class="caption"><a href="../../../data/studies/predictive_frontier_tabpfn/results.json">Exact results (JSON)</a> · <a href="../../../data/studies/predictive_frontier_tabpfn/comparisons.csv">Paired comparisons (CSV)</a> · <a href="../../../data/studies/predictive_frontier_tabpfn/manifest.json">Frozen experiment manifest</a> · <a href="../../../src/eda/predictive_frontier_tabpfn/score.py">Scoring code</a></p></section>
<footer>Generated {_esc(result['generated_at'])} from the saved experiment. Positive gains favor TabPFN in the displayed comparison tables. This is a bounded research comparison.</footer>
</main></body></html>'''


def main():
    frame, info = load()
    result = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
              "tour": "atp", "test_year": 2026, "info": info, **summarize(frame)}
    C.write_json(C.OUT / "results.json", result)
    pd.DataFrame(result["scores"]).to_csv(C.OUT / "scores.csv", index=False)
    pd.DataFrame(result["comparisons"]).to_csv(C.OUT / "comparisons.csv", index=False)
    keep = ["match_id", "tour", "year", "tournament_date", "a_won", *LABELS,
            "tabpfn_original", "tabpfn_swapped"]
    frame[keep].to_parquet(C.OUT / "test_predictions.parquet", index=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(result, info), encoding="utf-8")
    prepared = REPORT.with_name("prepared.html")
    if prepared.exists():
        archived = REPORT.with_name("prepared_before_fit_snapshot.html")
        if not archived.exists():
            archived.write_text(prepared.read_text(encoding="utf-8"), encoding="utf-8")
        prepared.write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TabPFN experiment completed</title><style>body{font:19px/1.65 system-ui,sans-serif;max-width:760px;margin:65px auto;padding:0 24px;color:#142b36}a{color:#096954}</style></head><body><h1>The TabPFN experiment has now completed.</h1><p>This preparation page has been superseded by the actual results from the single paid fit.</p><p><a href="report.html">Open the completed men's 2026 comparison report →</a></p><p><small>The <a href="prepared_before_fit_snapshot.html">pre-fit preparation snapshot</a> is retained as a historical record. Its pending status is no longer current.</small></p></body></html>''', encoding="utf-8")
    print(f"Scored {len(frame):,} ATP matches in 2026. Report: {REPORT}", flush=True)
    for r in result["comparisons"]:
        if r["n"]:
            print(f"{r['subset']}: {r['model']} vs {r['base']}; n={r['n']:,}; "
                  f"LL {r['model_ll']:.6f} vs {r['base_ll']:.6f}; gain {r['gain_mll']:+.3f} mLL "
                  f"[{_interval(r)}]", flush=True)


def report_prepared():
    """Publish the real local controls while explicitly marking TabPFN unrun."""
    train_x, _, query_x, _, manifest = C.load_upload()
    if (C.THINKING / "fit_slot.json").exists() or (C.THINKING / "predictions.npz").exists():
        raise ValueError("A paid attempt exists; use its actual receipts instead of an unrun report")
    frame = pd.read_parquet(C.OUT / "frame.parquet")
    train, test = frame[frame.split.eq("train")], frame[frame.split.eq("test")].copy()
    if len(C.NAMES) != 36 or not frame.tour.eq("atp").all() or not test.year.eq(2026).all() or not train.year.le(2025).all():
        raise ValueError("Prepared report is restricted to the ATP/2026 design")
    if len(train) != len(train_x) or len(query_x) != 2 * len(test) or train.tournament_date.max() >= test.tournament_date.min():
        raise ValueError("Prepared report rows do not match the chronological upload")
    base = pd.read_parquet(C.OUT / "baselines.parquet")
    if not np.array_equal(base.match_id.to_numpy(), test.match_id.to_numpy()):
        raise ValueError("Prepared baseline IDs differ from the frozen test rows")
    for name in base.columns.drop("match_id"):
        test[name] = base[name].to_numpy()
    rows, scores = [], []
    for subset, columns, mask in (
        ("All 2026 test matches", SPORTS_MODELS[1:], np.ones(len(test), dtype=bool)),
        ("With average closing prices", ["logistic_combined_fixed", "p_avg_a", "average_calibrated"], np.isfinite(test.p_avg_a.to_numpy())),
        ("With Pinnacle closing prices", ["logistic_combined_fixed", "p_ps_a", "pinnacle_calibrated"], np.isfinite(test.p_ps_a.to_numpy())),
    ):
        for model in columns:
            value = float(loss(test.loc[mask, "a_won"], test.loc[mask, model]).mean()) if mask.any() else None
            rec = {"subset": subset, "model": model, "n": int(mask.sum()), "log_loss": value}
            scores.append(rec)
            rows.append(f'<tr><td>{_esc(subset)}</td><td>{_esc(LABELS[model])}</td><td>{rec["n"]:,}</td><td>{_fmt(value)}</td></tr>')
    selection = manifest.get("train_selection", {})
    selected = selection.get("strategy", "See frozen manifest")
    selected = {"all": "all eligible history from 2013 through 2025", "latest6": "the latest six calendar years (2020–2025)",
                "latest4": "the latest four calendar years (2022–2025)"}.get(selected, selected)
    report = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Men's 2026 TabPFN experiment — prepared, not fitted</title><style>body{{font:17px/1.6 system-ui,sans-serif;color:#142b36;background:#f5f7f6;margin:0}}main{{max-width:1050px;margin:auto;padding:35px 22px}}h1{{font-size:40px;line-height:1.15}}h2{{font-size:25px}}section{{background:white;border:1px solid #d9e2df;border-radius:12px;padding:25px;margin:22px 0}}.pending{{background:#fff4d9;border-left:5px solid #a76100}}.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:12px;border-bottom:1px solid #d9e2df;text-align:left}}td:last-child{{font-variant-numeric:tabular-nums}}th{{background:#edf3f0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}small{{color:#536774}}a{{color:#096954}}@media(max-width:650px){{main{{padding:20px 12px}}h1{{font-size:31px}}section{{padding:18px 14px}}th,td{{padding:9px 6px}}}}</style></head><body><main>
<small>ATP men only · train before 2026 · test in 2026</small><h1>The revised experiment is ready. TabPFN has not been fitted.</h1><section class="pending"><h2>Current status: waiting for TabPFN access</h2><p>No TabPFN fit or prediction request has been dispatched for this experiment. The tables below contain only the local logistic models and closing-price benchmarks. There is no TabPFN score yet.</p></section>
<section><h2>The experiment you requested</h2><p><b>{len(train_x):,} men's matches for training</b>, dated {train.tournament_date.min().date()} to {train.tournament_date.max().date()}. <b>{len(test):,} men's matches for testing</b>, dated {test.tournament_date.min().date()} to {test.tournament_date.max().date()}.</p><p>TabPFN and the direct logistic comparator will receive the same 36 sporting inputs: the established 9, including Elo and serve/return strength, plus the 27 new features. Neither receives closing prices as model inputs. No women's matches are included.</p><p>Training-history choice: <b>{_esc(selected)}</b>. This was selected using logistic-regression validation predictions for 2023, 2024 and 2025, with each validation season predicted using earlier seasons only. All 2026 results were excluded from that selection. This is a practical proxy for selecting history before spending the single TabPFN fit; it cannot prove which history TabPFN would prefer.</p></section>
{training_choice_html(selection)}
<section><h2>The comparison scores already available</h2><p><b>Lower log loss is better.</b> It rewards assigning a high probability to the outcome that actually happens and penalizes confident mistakes. Always saying “50–50” scores about 0.69315. Each group below uses identical matches for its listed models.</p><div class="scroll"><table><thead><tr><th>Match group</th><th>Forecast</th><th>Matches</th><th>Log loss ↓</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p>The closing line is the bookmakers' late pre-match price, converted to a probability after removing the quoted margin. “Calibrated” adjusts its confidence using training data only. The Pinnacle quotes cover a small early-season subset, so they are not a full-2026 benchmark.</p></section>
<section><h2>What happens in the one-fit comparison?</h2><p>Once access is available, the prepared request uses TabPFN 3.5 Thinking, high effort, log-loss objective, seed 0 and 8 estimators requested. One prediction request includes both player orders for each match; averaging the equivalent probabilities removes arbitrary player-order effects. The final report will compare TabPFN with logistic regression and both closing-line benchmarks, including paired uncertainty intervals.</p><p>The fitted model stays fixed through 2026. Pre-match sporting features can incorporate earlier 2026 matches as the season progresses. This is a test of forecasts made before each match, not a forecast of the entire season made on 1 January.</p></section>
<section><h2>Limits to keep in mind</h2><p>These are the available 2026 matches, not a complete season. The archive has very little ATP data for 2018. Exact historical price timestamps remain unverified. This project previously examined 2026 outcomes during feature research, so this is a chronological test for this fit, not untouched research data. Prediction scores alone do not establish betting profit.</p><details><summary>Frozen training-history selection</summary><pre>{_esc(json.dumps(selection, indent=2))}</pre></details><p><a href="../../../data/studies/predictive_frontier_tabpfn/manifest.json">Frozen experiment manifest</a> · <a href="../../../data/studies/predictive_frontier_tabpfn/prepared_scores.json">Exact local comparison scores</a></p></section><small>Prepared {_esc(pd.Timestamp.now(tz='UTC').isoformat(timespec='seconds'))}. No paid TabPFN results are claimed.</small></main></body></html>'''
    path = REPORT.with_name("prepared.html")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    C.write_json(C.OUT / "prepared_scores.json", {"tabpfn_fitted": False, "scores": scores})
    print(f"Prepared-only report (no TabPFN result): {path}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-only", action="store_true")
    args = parser.parse_args()
    report_prepared() if args.prepared_only else main()
