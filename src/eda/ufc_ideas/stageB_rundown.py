"""Stage B, the rundown: every Stage B feature scored through the shared harness (common.rundown: walk-forward by season,
alone / given surface Elo / given the closing odds, 20 shuffled copies, the family-wide line, the reading), with the
earlier study's leading rows re-scored in the same run for side-by-side reading, then the direct questions:

    (a) per statistic, which channel adds most given Elo: Stage 4's opponent-adjusted form (stage4_ranking.csv), adjperf,
        adjdef, IOS (the rating of the player's own production of the statistic, and of what the player allows)
    (b) whether any adjperf / adjdef / IOS row adds to the serve and return ratings through the iid model: the best three
        such rows per tour (by the given-Elo gain), the IOS points matchup (the ratings' batch twin) and the best of its
        diagnostics, scored again two ways: through the harness with the ratings through the iid model as the base
        (p_ratings = expit of rating_matchup|single), and, for Elo and the ratings together, by the harness's own walk with
        both refitted: [logit p_elo, logit p_ratings, feature] against [logit p_elo, logit p_ratings], with the harness's
        20 shuffled copies of the feature (its keys) as the band. (A first version used one fixed season-by-season blend
        of Elo and the ratings as a single base; a fixed blend can be mis-weighted, which a feature then corrects, so it
        was replaced before anything was reported.)
    (c) the opponent-strength rows, given Elo and given the market
    (d) the mirror: adjdef on a statistic against adjperf on its mirror (Part 1 measures the per-match z; here the
        feature columns)

Rows that are the same feature twice are scored once: adjdef on a statistic whose mirror is in the list is adjperf on the
mirror (an identity, measured in Part 1 and again here), and is listed in the catalog as an alias.

Writes, in data/studies/ufc_ideas/:
    stageB_features.parquet                  the pool, the earlier study's re-scored columns, every Stage B feature and
                                             p_ratings
    stageB_ranking.csv, stageB_results.csv, stageB_null_copies.csv, stageB_results.json   the harness's rundown
    stageB_vs_ratings_ranking.csv, _results.csv, _null_copies.csv, _results.json         question (b)'s rundown
    stageB_catalog.json                      one entry per scored row id
    stageB_summary.json                      the parts' summaries, the direct questions, the headline tables, timings

Run after stageB_adjperf.py, stageB_ios.py and stageB_split.py:
    ./python.sh src/eda/ufc_ideas/stageB_rundown.py   (about 9 minutes with 5 worker processes)
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")       # Stage B's share of the machine: at most 5 processes or threads at once

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.ufc_ideas import common as H  # noqa: E402
from src.eda.ufc_ideas import stageB_adjperf as AP  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402
from src.eda.ufc_ideas import stageB_ios as IO  # noqa: E402
from src.eda.ufc_ideas import stageB_split as SP  # noqa: E402

FEATURES = B.OUT / "stageB_features.parquet"
PREFIX = B.OUT / "stageB"
PREFIX_RATINGS = B.OUT / "stageB_vs_ratings"
CATALOG = B.OUT / "stageB_catalog.json"
SUMMARY = B.OUT / "stageB_summary.json"
CANDIDATES = C.OUT / "stage4_candidates.csv"

EARLIER = ["rating_matchup|single", "rating_serve|single", "rating_return|single", "spw|adjusted", "rpw|adjusted",
           "tpw|52 weeks", "spw|52 weeks", "rpw|52 weeks", "mu_points|52 weeks", "mu_points|adjusted"]
WORKERS = 5
FORM_WORDS = {"52 weeks": "the last year", "decayed": "decayed", "career": "career", "single": "one form"}
SPLIT_WORDS = {"strong_minus_weak_naive": "strong minus weak (difference of the two shrunk means)",
               "strong_minus_weak": "strong minus weak (the player's own contrast)",
               "vs_strong": "against strong opponents", "vs_weak": "against weak opponents",
               "vs_top_third": "against the top third", "vs_mid_third": "against the middle third",
               "vs_bottom_third": "against the bottom third", "top_minus_bottom_third": "top third minus bottom third",
               "slope": "slope on the opponent's Elo"}      # longer keys first: the first prefix that matches is used


# ------------------------------------------------------------------------------------------------
# Row metadata: names, families, descriptions

def describe_col(col: str, adj_used: dict, ios_chosen: dict, ios_diag: dict | None = None) -> dict:
    """id, name, family, description and the tuned constants of one feature column."""
    base, form = col.split("|")
    fw = FORM_WORDS.get(form, form)
    if base == "ios_matchup_points" and form.startswith("diagnostic: "):
        label = form[len("diagnostic: "):]
        return {"name": "IOS points matchup through the iid model", "family": "IOS",
                "description": ("The IOS points matchup with one constant changed from the tuned ones (a shorter memory or "
                                "a heavier ridge): a diagnostic of what the winner's signal wants."),
                "tuned": {t: {**(ios_diag or {}).get((label, t), {}), "note": f"diagnostic: {label}"} for t in C.TOURS}}
    if base.startswith("adjperf_") or base.startswith("adjdef_"):
        ch, s = base.split("_", 1)
        words = B.WORDS[s]
        if ch == "adjperf":
            desc = (f"The player's {words} in each earlier match scored against what that opponent usually allows, "
                    f"as a z on the log-odds scale, averaged ({fw}) and shrunk toward zero; A minus B.")
            name = f"adjperf: {words}"
        else:
            desc = (f"How far the player held each earlier opponent's {words} below that opponent's own norm, as a z, "
                    f"averaged ({fw}) and shrunk toward zero; A minus B.")
            name = f"adjdef: {words}"
        tuned = {t: {**{k: adj_used[base][t][k] for k in ("h1", "K1", "tau", "h3", "K3")}, "tuned_on": adj_used[base][t]["from"]}
                 for t in C.TOURS}
        return {"name": name, "family": ch, "description": desc, "tuned": tuned}
    if base.startswith("ios_"):
        if base.startswith("ios_matchup"):
            kind = base.split("_")[-1]
            name = f"IOS {kind} matchup through the iid model"
            what = "serve points won" if kind == "points" else "service games held"
            desc = (f"Each player's chance on serve against this opponent from the IOS ratings of {what}, through the "
                    f"iid model with the match's format: the log-odds that A wins.")
            stat = "spw" if kind == "points" else "hold"
            tuned = {t: ios_chosen[(t, stat)] for t in C.TOURS}
            return {"name": name, "family": "IOS", "description": desc, "tuned": tuned}
        _, side, s = base.split("_", 2)
        words = B.WORDS[s]
        if side == "O":
            name = f"IOS offence: {words}"
            desc = f"The player's IOS offence rating of {words} (a batch ridge solve over earlier weeks), A minus B."
        else:
            ret = IO.RETURN_OF.get(s)
            name = f"IOS defence: {words}" + (f" (= {B.WORDS[ret]})" if ret else "")
            desc = (f"The player's IOS defence rating against servers' {words}: how far the player holds a server below "
                    f"their rate, A minus B.")
        return {"name": name, "family": "IOS", "description": desc, "tuned": {t: ios_chosen[(t, s)] for t in C.TOURS}}
    if base in ("wins_over_strong", "wins_over_weak"):
        grp = "strong" if base.endswith("strong") else "weak"
        return {"name": f"Wins above Elo against {grp} opponents", "family": "opponent split",
                "description": (f"Matches won minus surface Elo's pre-match chance, over earlier matches against {grp} "
                                f"opponents ({fw}), shrunk toward zero; A minus B."),
                "tuned": {t: {"K3": adj_used["adjperf_tpw"][t]["K3"], "from": "adjperf_tpw"} for t in C.TOURS}}
    if base == "strong_gap_x_strong_opp":
        return {"name": "Strong-minus-weak gap when the opponent is strong", "family": "opponent split",
                "description": ("A's strong-minus-weak contrast of total points won when B is strong, minus B's when A is "
                                f"strong ({fw})."),
                "tuned": {t: {"K3": adj_used["adjperf_tpw"][t]["K3"], "tau": adj_used["adjperf_tpw"][t]["tau"]}
                          for t in C.TOURS}}
    templates = {
        "strong_minus_weak_naive": "The mean adjperf z of {w} against strong opponents minus against weak ones, each mean shrunk toward zero separately",
        "strong_minus_weak": "The player's own contrast of the adjperf z of {w}, against strong opponents minus against weak ones, shrunk toward zero as one quantity",
        "vs_strong": "The player's mean adjperf z of {w} over earlier matches against strong opponents, shrunk toward zero",
        "vs_weak": "The player's mean adjperf z of {w} over earlier matches against weak opponents, shrunk toward zero",
        "vs_top_third": "The player's mean adjperf z of {w} against opponents in the top third of strength, shrunk toward zero",
        "vs_mid_third": "The player's mean adjperf z of {w} against opponents in the middle third of strength, shrunk toward zero",
        "vs_bottom_third": "The player's mean adjperf z of {w} against opponents in the bottom third of strength, shrunk toward zero",
        "top_minus_bottom_third": "The player's own contrast of the adjperf z of {w}, top third of opponents minus bottom third, shrunk toward zero as one quantity",
        "slope": "The within-player slope of the adjperf z of {w} on the opponent's pre-match Elo, shrunk toward the population's slope"}
    for key, words in SPLIT_WORDS.items():
        if base.startswith(key + "_"):
            s = base[len(key) + 1:]
            return {"name": f"adjperf {B.WORDS[s]}, {words}", "family": "opponent split",
                    "description": (templates[key].format(w=B.WORDS[s]) + f" ({fw}); A minus B. Opponent strength is the "
                                    "opponent's pre-match surface Elo against a fixed line."),
                    "tuned": {t: {k: adj_used[f"adjperf_{s}"][t][k] for k in ("K3", "tau")} for t in C.TOURS}}
    raise ValueError(col)


def earlier_meta(col: str, cand: pd.DataFrame) -> dict:
    base, form = col.split("|")
    c = cand[cand["id"].eq(base)].iloc[0]
    return {"name": c["name"], "family": "earlier study", "group": c["group"], "wta_box_from_2019": c["wta_box_from_2019"] == "yes",
            "description": f"The earlier study's {c['name'].lower()} ({FORM_WORDS.get(form, form)}), re-scored in this run.",
            "tuned": None}


# ------------------------------------------------------------------------------------------------
# The frame

def given_elo_and_ratings(f: pd.DataFrame, col: str, tour: str, first: int) -> dict:
    """What a feature adds to Elo and the ratings through the iid model together, both refitted: the harness's walk
    (stage4_rundown.walk) of a logistic regression without an intercept on [logit p_elo, logit p_ratings, feature]
    against one on [logit p_elo, logit p_ratings], each season fitted on the pool matches of 2010 to the season before and
    scored on its evaluation matches; the feature standardised, and its 20 copies shuffled within seasons with the
    harness's own keys (common.init_worker) through the same fits, as the band."""
    keys_all = np.random.default_rng(H.SEED).random((len(f), H.COPIES))
    pe = f["p_elo"].to_numpy(dtype="float64")
    pr = f["p_ratings"].to_numpy(dtype="float64")
    x = f[col].to_numpy(dtype="float64")
    ok = (f["tour"].to_numpy() == tour) & np.isfinite(pe) & np.isfinite(pr) & np.isfinite(x)
    idx = np.flatnonzero(ok)
    year = f["year"].to_numpy()[idx]
    assert (np.diff(year) >= 0).all()
    y = f["a_won"].to_numpy(dtype=bool)[idx]
    ev = f["evaluation"].to_numpy(dtype=bool)[idx]
    xs = x[idx]  # walk() fits feature scales on prior-season training rows only
    dates = R.cluster_dates(f)[idx]
    copies = R.shuffled(xs[:, None], year, keys_all[idx])
    allx = np.concatenate([xs[None, :, None], copies], axis=0)
    le = logit(np.clip(pe[idx], 1e-9, 1 - 1e-9))
    lr = logit(np.clip(pr[idx], 1e-9, 1 - 1e-9))
    base2 = np.stack([le, lr], axis=1)
    Zf = np.ascontiguousarray(np.concatenate([np.broadcast_to(base2[None], (H.COPIES + 1, len(idx), 2)), allx], axis=2))
    seasons = list(range(first, C.EVAL_YEARS[-1] + 1))
    wf = R.walk(Zf, y, year, seasons, None)
    wb = R.walk(np.ascontiguousarray(base2[None]), y, year, seasons, None)
    d = wb["llm"][0][None, :] - wf["llm"]
    scored = np.isfinite(d[0]) & ev
    out = {k: v for k, v in R.summarize(d, scored, dates).items() if k != "copies"}
    for w, (a, b) in H.WINDOWS.items():
        g = R.summarize(d, scored & (year >= a) & (year <= b), dates)
        out[w] = g.get("imp")
    out["seasons_scored"] = wf["scored"]
    return out


def assemble() -> tuple[pd.DataFrame, dict]:
    pool = H.load_pool(extra=EARLIER)
    parts = {"adj": pd.read_parquet(AP.ADJ_FEATURES), "ios": pd.read_parquet(IO.IOS_FEATURES),
             "split": pd.read_parquet(SP.SPLIT_FEATURES)}
    for k, p in parts.items():
        assert (p["match_id"].to_numpy() == pool["match_id"].to_numpy()).all(), k
    frame = pool.copy()
    for p in parts.values():
        for c in p.columns:
            if c != "match_id":
                frame[c] = p[c].to_numpy()
    frame["p_ratings"] = expit(frame["rating_matchup|single"].to_numpy(dtype="float64"))
    # identical columns are scored once: adjdef on a mirrored statistic is adjperf on the mirror
    aliases, checks = {}, []
    for s, m in B.MIRROR.items():
        for form in AP.FORMS:
            a, b = f"adjdef_{s}|{form}", f"adjperf_{m}|{form}"
            x, y = frame[a].to_numpy(dtype="float64"), frame[b].to_numpy(dtype="float64")
            e = np.isfinite(x) & np.isfinite(y)
            same_missing = bool((np.isfinite(x) == np.isfinite(y)).all())
            diff = float(np.abs(x[e] - y[e]).max())
            checks.append({"adjdef": a, "adjperf": b, "matches": int(e.sum()), "same_missing": same_missing,
                           "max_abs_diff": diff, "corr": float(np.corrcoef(x[e], y[e])[0, 1])})
            if same_missing and diff < 1e-5:
                aliases[a] = b
    # a decayed form identical to the career form (an infinite half-life chosen) is an alias too
    for c in [c for c in frame.columns if c.endswith("|decayed") and c.startswith(("adjperf_", "adjdef_"))]:
        car = c.replace("|decayed", "|career")
        x, y = frame[c].to_numpy(dtype="float64"), frame[car].to_numpy(dtype="float64")
        e = np.isfinite(x) & np.isfinite(y)
        if (np.isfinite(x) == np.isfinite(y)).all() and np.abs(x[e] - y[e]).max() < 1e-7:
            aliases[c] = car
    frame.to_parquet(FEATURES, index=False, compression="zstd")
    return frame, {"aliases": aliases, "mirror_feature_checks": checks}


# ------------------------------------------------------------------------------------------------

def build_tasks(frame: pd.DataFrame, aliases: dict, adj_used: dict, ios_chosen: dict, ios_diag: dict) -> tuple[list, dict]:
    cand = pd.read_csv(CANDIDATES)
    tasks, meta = [], {}
    feat_cols = [c for c in frame.columns if "|" in c and c not in EARLIER]
    for col in feat_cols + EARLIER:
        if col in aliases:
            continue
        if col in EARLIER:
            m = earlier_meta(col, cand)
            box = m["wta_box_from_2019"]
        else:
            m = describe_col(col, adj_used, ios_chosen, ios_diag)
            box = not col.startswith("wins_over_")
        base, form = col.split("|")
        meta[col] = {"id": base, "form": form, **{k: m[k] for k in ("name", "family", "description", "tuned")},
                     "wta_box_from_2019": bool(box)}
        for t in C.TOURS:
            tasks.append(H.task(t, base, form, m["name"], m["family"], [col], wta_box_from_2019=box))
    return tasks, meta


def channel_table(rank: pd.DataFrame, s4: pd.DataFrame, aliases: dict) -> list[dict]:
    """(a) Per statistic and tour, the given-Elo gain of each channel's best form."""
    def best(t, prefix_cols):
        r = rank[(rank["tour"] == t) & rank["col"].isin(prefix_cols)]
        if r.empty:
            return None
        b = r.loc[r["elo_imp"].idxmax()]
        return {"col": b["col"], "form": b["form"], "elo_imp": float(b["elo_imp"]), "elo_lo": float(b["elo_lo"]),
                "elo_hi": float(b["elo_hi"]), "reading": b["reading"], "elo_2022_2026": float(b["elo_2022-2026"])}
    out = []
    mirror_ios = {v: k for k, v in IO.RETURN_OF.items()}
    for s in B.STATS:
        for t in C.TOURS:
            rec = {"stat": s, "tour": t, "words": B.WORDS[s]}
            a = s4[(s4["tour"] == t) & (s4["id"] == s) & (s4["form"] == "adjusted")]
            rec["stage4_adjusted"] = ({"elo_imp": float(a["elo_imp"].iloc[0]), "reading": a["reading"].iloc[0],
                                       "elo_2022_2026": float(a["elo_2022-2026"].iloc[0])} if len(a) else None)
            a4 = s4[(s4["tour"] == t) & (s4["id"] == s)]
            if len(a4):
                b4 = a4.loc[a4["elo_imp"].idxmax()]
                rec["stage4_best_form"] = {"form": b4["form"], "elo_imp": float(b4["elo_imp"])}
            rec["adjperf"] = best(t, [f"adjperf_{s}|{f}" for f in AP.FORMS])
            dcols = [aliases.get(f"adjdef_{s}|{f}", f"adjdef_{s}|{f}") for f in AP.FORMS]
            rec["adjdef"] = best(t, dcols)
            rec["adjdef_is_alias_of"] = (f"adjperf_{B.MIRROR[s]}" if s in B.MIRROR else None)
            if s in IO.IOS_STATS:
                rec["ios_own"] = best(t, [f"ios_O_{s}|single"])
                rec["ios_allowed"] = best(t, [f"ios_D_{s}|single"])
                rec["ios_map"] = {"own": f"ios_O_{s}", "allowed": f"ios_D_{s}"}
            elif s in mirror_ios:
                m = mirror_ios[s]
                rec["ios_own"] = best(t, [f"ios_D_{m}|single"])          # returning well = holding servers down
                rec["ios_allowed"] = best(t, [f"ios_O_{m}|single"])      # serving well = holding returners down
                rec["ios_map"] = {"own": f"ios_D_{m}", "allowed": f"ios_O_{m}"}
            else:
                rec["ios_own"] = rec["ios_allowed"] = None
            cands = {k: rec[k]["elo_imp"] for k in ("stage4_adjusted", "adjperf", "adjdef", "ios_own", "ios_allowed")
                     if rec.get(k)}
            rec["winner"] = max(cands, key=cands.get) if cands else None
            out.append(rec)
    return out


CORR_COLS = ["adjperf_tpw|decayed", "adjperf_tpw|decayed, earlier weeks", "adjperf_tpw|52 weeks", "adjperf_tpw|career",
             "ios_matchup_points|single", "rating_matchup|single", "tpw|52 weeks"]
STAGE4_EXTRA = ["elo_games|single", "sets_14d|single"]          # read from stage4_features.parquet for the comparison only


def correlations(frame: pd.DataFrame) -> dict:
    """Pearson correlations, per tour on the evaluation matches of the box-score seasons (the women's from 2019), of the
    leading adjperf forms and the IOS points matchup with Elo's log-odds, the earlier study's ratings matchup, total points
    won over 52 weeks, and two earlier features that also carry recent results: the games-weighted Elo and the sets played
    over the last 14 days (stage4_features.parquet, aligned by match id)."""
    s4 = pd.read_parquet(H.STAGE4_FEATURES, columns=["match_id"] + STAGE4_EXTRA).set_index("match_id")
    s4 = s4.reindex(frame["match_id"].to_numpy())
    d = frame[CORR_COLS].astype("float64").copy()
    for c in STAGE4_EXTRA:
        d[c] = s4[c].to_numpy(dtype="float64")
    d["elo_logit"] = logit(np.clip(frame["p_elo"].to_numpy(dtype="float64"), 1e-9, 1 - 1e-9))
    out = {}
    for t in C.TOURS:
        m = ((frame["tour"] == t) & frame["evaluation"] & (frame["year"] >= (C.WTA_BOX_FROM if t == "wta" else C.EVAL_YEARS[0]))).to_numpy()
        cm = d[m].corr()
        out[t] = {"matches": int(m.sum()),
                  "rows": {r: {c: float(cm.loc[r, c]) for c in cm.columns} for r in
                           ("adjperf_tpw|decayed", "adjperf_tpw|decayed, earlier weeks", "ios_matchup_points|single")}}
    return out


def data_checks() -> dict:
    """Checks on the earlier study's table that the write-up reports (not fixes): tournament dates that are not Mondays
    (the time rule treats a date as a week), players with a later event starting one to six days after an earlier one (a
    two-week event's late rounds are then 'earlier' for the second event), and box-score counts outside 0..d."""
    m = C.load_matches(["match_id", "tour", "tournament_date", "tournament_id", "level"])
    d = pd.to_datetime(m["tournament_date"])
    out = {"matches": int(len(m)), "non_monday_matches": int((d.dt.dayofweek != 0).sum()),
           "non_monday_by_tour": {t: int(((d.dt.dayofweek != 0) & (m["tour"] == t)).sum()) for t in C.TOURS},
           "distinct_dates": {t: int(d[m["tour"] == t].nunique()) for t in C.TOURS},
           "distinct_iso_weeks": {t: int(d[m["tour"] == t].dt.strftime("%G-%V").nunique()) for t in C.TOURS}}
    mp = C.load_match_players(["match_id", "player_id"], match_columns=["tour", "level"])
    ev = (mp.groupby(["player_id", "tournament_date", "tournament_id"]).agg(n=("match_id", "size")).reset_index()
          .sort_values(["player_id", "tournament_date"]))
    gap = (ev["tournament_date"] - ev.groupby("player_id")["tournament_date"].shift()).dt.days
    close = (gap > 0) & (gap < 7)
    out["player_events_starting_1_to_6_days_after_an_earlier_event"] = int(close.sum())
    out["matches_in_those_later_events"] = int(ev.loc[close, "n"].sum())
    raw = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id"] + [f"{s}_{x}" for s in C.RATES for x in ("n", "d")])
    bad = []
    for s in C.RATES:
        n_, d_ = raw[f"{s}_n"].to_numpy(dtype="float64"), raw[f"{s}_d"].to_numpy(dtype="float64")
        if s == "bp_faced_pg":
            off = np.isfinite(n_) & np.isfinite(d_) & (n_ < 0)
        else:
            off = np.isfinite(n_) & np.isfinite(d_) & ((n_ < 0) | (n_ > d_))
        for i in np.flatnonzero(off):
            bad.append({"stat": s, "match_id": raw["match_id"].iloc[i], "n": float(n_[i]), "d": float(d_[i])})
    out["counts_outside_0_to_d"] = bad
    return out


def row_view(r: pd.Series) -> dict:
    keys = ["tour", "id", "form", "name", "group", "col", "reading", "elo_imp", "elo_lo", "elo_hi", "elo_band_max",
            "elo_z", "elo_clears_line", "eras_positive", "eras_scored", "elo_2019-2026", "elo_2022-2026", "elo_coverage",
            "elo_scored", "elo_coef", "alone_imp", "market_imp", "market_lo", "market_hi", "market_above_band",
            "market_clears_line", "market_band_max", "market_2022-2026", "market_scored"]
    out = {}
    for k in keys:
        if k in r.index:
            v = r[k]
            out[k] = (None if (isinstance(v, float) and not np.isfinite(v)) else
                      (v.item() if hasattr(v, "item") else v))
    return out


def main() -> int:
    t_start = time.time()
    adj_summ = json.loads(AP.ADJ_SUMMARY.read_text(encoding="utf-8"))
    ios_summ = json.loads(IO.IOS_SUMMARY.read_text(encoding="utf-8"))
    split_summ = json.loads(SP.SPLIT_SUMMARY.read_text(encoding="utf-8"))
    adj_used = adj_summ["used"]
    ios_chosen = {(c["tour"], c["stat"]): {k: c[k] for k in ("h", "kappa", "tau")} for c in ios_summ["chosen"]}
    ios_diag = {(d["diagnostic"], d["tour"]): {k: d[k] for k in ("h", "kappa", "tau")} for d in ios_summ.get("diagnostics", [])}
    frame, al = assemble()
    aliases = al["aliases"]
    B.log(f"wrote {FEATURES.name}: {frame.shape[0]:,} matches x {frame.shape[1]} columns; {len(aliases)} aliases")
    corr = correlations(frame)
    tasks, meta = build_tasks(frame, aliases, adj_used, ios_chosen, ios_diag)
    B.log(f"{len(tasks)} rows to score")
    t0 = time.time()
    res = H.rundown(FEATURES, tasks, PREFIX, workers=WORKERS)
    t_main = round(time.time() - t0, 1)
    rank = res["ranking"].copy()
    rank["col"] = rank["id"] + "|" + rank["form"]
    rank["family"] = rank["group"]

    # (b) the best three adjperf / adjdef / IOS rows per tour, and the IOS points matchup, given the ratings
    picks, together = [], {}
    for t in C.TOURS:
        fam = rank[(rank["tour"] == t) & rank["family"].isin(["adjperf", "adjdef", "IOS"])]
        r = fam[~fam["form"].str.startswith("diagnostic")].sort_values("elo_imp", ascending=False)
        chosen_cols = list(r["col"].head(3))
        if "ios_matchup_points|single" not in chosen_cols:
            chosen_cols.append("ios_matchup_points|single")
        dg = fam[fam["form"].str.startswith("diagnostic")].sort_values("elo_imp", ascending=False)
        if len(dg):
            chosen_cols.append(dg["col"].iloc[0])
        for col in chosen_cols:
            m = meta[col]
            picks.append(H.task(t, m["id"], m["form"], m["name"], m["family"], [col], scores=("ratings",),
                                wta_box_from_2019=m["wta_box_from_2019"], bases={"ratings": "p_ratings"}))
            first = C.WTA_BOX_FROM if (t == "wta" and m["wta_box_from_2019"]) else C.EVAL_YEARS[0]
            together[(t, col)] = given_elo_and_ratings(frame, col, t, first)
    t0 = time.time()
    res_r = H.rundown(FEATURES, picks, PREFIX_RATINGS, workers=WORKERS, reading_base="ratings")
    t_ratings = round(time.time() - t0, 1)
    rr = res_r["ranking"].copy()

    # the catalog
    catalog = []
    for col, m in meta.items():
        catalog.append({"id": col, "name": m["name"], "family": m["family"], "description": m["description"],
                        "tuned": m["tuned"]})
    for a, b in aliases.items():
        catalog.append({"id": a, "name": f"(alias) {a.split('|')[0]}", "family": "adjdef" if a.startswith("adjdef") else "adjperf",
                        "description": f"Identical to {b} (the same feature computed through the other channel); scored once.",
                        "tuned": None, "alias_of": b})
    B.jdump(catalog, CATALOG)

    # direct questions and headline tables
    s4 = H.stage4_reference()
    chan = channel_table(rank, s4, aliases)
    top = {t: [row_view(r) for _, r in rank[rank["tour"] == t].sort_values("elo_imp", ascending=False).head(10).iterrows()]
           for t in C.TOURS}
    earlier = {t: [row_view(r) for _, r in rank[(rank["tour"] == t) & (rank["family"] == "earlier study")]
                   .sort_values("elo_imp", ascending=False).iterrows()] for t in C.TOURS}
    market = {t: [row_view(r) for _, r in rank[rank["tour"] == t].sort_values("market_imp", ascending=False).head(10).iterrows()]
              for t in C.TOURS}
    split_rows = {t: [row_view(r) for _, r in rank[(rank["tour"] == t) & (rank["family"] == "opponent split")]
                      .sort_values("elo_imp", ascending=False).iterrows()] for t in C.TOURS}
    fam_best = {}
    for t in C.TOURS:
        for fam in ("adjperf", "adjdef", "IOS", "opponent split", "earlier study"):
            r = rank[(rank["tour"] == t) & (rank["family"] == fam)]
            if len(r):
                fam_best[f"{t}|{fam}"] = {"elo": row_view(r.loc[r["elo_imp"].idxmax()]),
                                          "market": row_view(r.loc[r["market_imp"].idxmax()])}
    counts = {t: {k: int(v) for k, v in rank[rank["tour"] == t]["reading"].value_counts().items()} for t in C.TOURS}
    counts_by_family = {f"{t}|{fam}": {k: int(v) for k, v in g["reading"].value_counts().items()}
                        for (t, fam), g in rank.groupby(["tour", "family"])}
    # the re-scored earlier rows against the earlier study's own numbers
    repro = []
    for col in EARLIER:
        base, form = col.split("|")
        for t in C.TOURS:
            a = rank[(rank["tour"] == t) & (rank["col"] == col)]
            b = s4[(s4["tour"] == t) & (s4["id"] == base) & (s4["form"] == form)]
            if len(a) and len(b):
                repro.append({"col": col, "tour": t, "here": float(a["elo_imp"].iloc[0]), "stage4": float(b["elo_imp"].iloc[0]),
                              "market_here": float(a["market_imp"].iloc[0]), "market_stage4": float(b["market_imp"].iloc[0])})
    vs_ratings = [{k: (None if (isinstance(v, float) and not np.isfinite(v)) else (v.item() if hasattr(v, "item") else v))
                   for k, v in r.items() if k in ("tour", "id", "form", "name", "group", "ratings_imp", "ratings_lo",
                                                   "ratings_hi", "ratings_band_max", "ratings_z", "ratings_clears_line",
                                                   "ratings_above_band", "ratings_2019-2026", "ratings_2022-2026",
                                                   "ratings_scored", "eras_positive", "reading")} for _, r in rr.iterrows()]
    for v in vs_ratings:
        g = rank[(rank["tour"] == v["tour"]) & (rank["id"] == v["id"]) & (rank["form"] == v["form"])]
        v["elo_imp"] = float(g["elo_imp"].iloc[0])
        v["elo_clears_line"] = bool(g["elo_clears_line"].iloc[0])
        tg = together[(v["tour"], f"{v['id']}|{v['form']}")]
        v.update({"elo_ratings_imp": tg.get("imp"), "elo_ratings_lo": tg.get("lo"), "elo_ratings_hi": tg.get("hi"),
                  "elo_ratings_band_max": tg.get("band_max"), "elo_ratings_band_min": tg.get("band_min"),
                  "elo_ratings_z": tg.get("z"), "elo_ratings_above_band": tg.get("above_band"),
                  "elo_ratings_scored": tg.get("n"), "elo_ratings_2019-2026": tg.get("2019-2026"),
                  "elo_ratings_2022-2026": tg.get("2022-2026")})
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "rows_scored": {t: int((rank["tour"] == t).sum()) for t in C.TOURS},
        "aliases": aliases, "mirror_feature_checks": al["mirror_feature_checks"],
        "lines": {k: v for k, v in res["lines"].items()}, "lines_vs_ratings": res_r["lines"],
        "readings": counts, "readings_by_family": counts_by_family,
        "top10_given_elo": top, "earlier_rows": earlier, "top10_given_market": market, "split_rows": split_rows,
        "family_best": fam_best, "channel_per_statistic": chan, "vs_ratings": vs_ratings, "earlier_reproduced": repro,
        "correlations": corr, "data_checks": data_checks(),
        "ios_diagnostic_rows": [row_view(r) for _, r in rank[rank["form"].str.startswith("diagnostic")
                                                              | (rank["col"] == "ios_matchup_points|single")].iterrows()],
        "adjperf": {k: adj_summ[k] for k in ("settings", "counts", "chosen", "brief_grid_choice", "brief_grid", "used",
                                             "flatness", "mirror", "probe", "seconds", "z_info")},
        "ios": {k: ios_summ[k] for k in ("settings", "chosen", "brief_grid_choice", "brief_grid", "typical_units", "flatness",
                                         "scores", "stage3_comparison", "diagnostics", "solver", "probe", "seconds",
                                         "tuning_seconds")},
        "split": {k: split_summ[k] for k in ("settings", "lines", "population_slope", "describe", "share_vs_strong",
                                             "contrast_vs_naive_corr", "probe", "seconds")},
        "seconds": {"adjperf": adj_summ["seconds"]["total"], "ios": ios_summ["seconds"]["total"],
                    "split": split_summ["seconds"]["total"], "rundown_main": t_main, "rundown_vs_ratings": t_ratings,
                    "rundown_total": round(time.time() - t_start, 1)},
    }
    B.jdump(summary, SUMMARY)
    B.log(f"wrote {CATALOG.name} and {SUMMARY.name}; total {summary['seconds']['rundown_total']:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
