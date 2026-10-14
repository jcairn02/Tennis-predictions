"""Three versions of the 54-input model's sporting inputs, scored on identical matches.

    original     the inputs the TabPFN-Thinking study used (data/studies/tabpfn_thinking/frame.parquet): full history,
                 tournament-week clock (the overlap leak), Stage 0's data
    leak-proof   this study's rebuild (leakproof_features.parquet): full history, the leak-proof timeline for IOS,
                 the repair's data corrections, scheduled formats
    repaired     the feature-alpha repair (repairs/repair_features.parquet): main-tour matches with a provider match day
                 only (78,714 of 872,704); it never rebuilt the 52-week points matchup or the IOS profile

Each model is a logistic regression without intercept (antisymmetric: side A is random), fitted per tour on the
2013-2021 main-tour matches and scored on 2022-2026, exactly the TabPFN-Thinking study's design, on the matches every
compared version can score (identical training and test rows). Gains are milli-log-loss: positive = the model's log loss
is lower = better. Intervals: paired, four-week calendar blocks (the corrected harness's method).

Writes data/studies/match_timing/score_results.csv and score_summary.json.
Run: ./python.sh src/eda/match_timing/score.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.tabpfn_thinking import common as TT  # noqa: E402

PROFILE = TT.PROFILE_STATS
ADJDEF = TT.ADJDEF_STATS
IOS7 = TT.IOS_STATS
EVERYTHING = TT.EVERYTHING                                   # elo + 8 (the 9-input combination)
PROFILE16 = [f"form_{s}" for s in PROFILE] + [f"formdef_{s}" for s in ADJDEF]
IOS21 = [f"ios{k}_{s}" for s in IOS7 for k in ("O", "D")] + [f"prod_{s}" for s in IOS7]
ALL47 = EVERYTHING + ["points_52w"] + PROFILE16 + IOS21

# the rebuilt tables' column for each model input
SRC = {"ratings_iid": "rating_matchup|single", "elo_games": "elo_games|single", "adjperf_tpw_2w": "adjperf_tpw|decayed",
       "ios_points_short": "ios_short", "points_52w": "mu_points|52 weeks", "sets_14d": "sets_14d|single",
       "surface_first": "surface_first|single", "age": "age|single", "age_sq": "age|single|2"}
SRC.update({f"form_{s}": f"adjperf_{s}|decayed" for s in PROFILE})
SRC.update({f"formdef_{s}": f"adjdef_{s}|decayed" for s in ADJDEF})
SRC.update({f"ios{k}_{s}": f"ios_{k}_{s}|single" for s in IOS7 for k in ("O", "D")})
SRC.update({f"prod_{s}": f"prod_{s}|single" for s in IOS7})

MODELS = {   # name: (inputs, uses the odds, versions that hold every input)
    "elo": (["elo_logit"], False, ("original", "leakproof", "repaired")),
    "everything9": (EVERYTHING, False, ("original", "leakproof", "repaired")),
    "market": ([], True, ("original", "leakproof", "repaired")),
    "mkt_profile16": (PROFILE16, True, ("original", "leakproof", "repaired")),
    "mkt_everything_profile25": (EVERYTHING + PROFILE16, True, ("original", "leakproof", "repaired")),
    "mkt_ios21": (IOS21, True, ("original", "leakproof")),
    "mkt_all47": (ALL47, True, ("original", "leakproof")),
}


def rebuilt(path: Path, frame: pd.DataFrame) -> pd.DataFrame:
    """A rebuilt feature table in the model's input names, on the TabPFN frame's matches."""
    f = pd.read_parquet(path)
    out = pd.DataFrame({"match_id": f["match_id"]})
    out["elo_logit"] = logit(np.clip(f["p_elo"].to_numpy(dtype=float), TT.EPS, 1 - TT.EPS))
    for name, col in SRC.items():
        out[name] = f[col].to_numpy(dtype=float) if col in f.columns else np.nan
    return frame[["match_id"]].merge(out, on="match_id", how="left")


def versions() -> tuple[pd.DataFrame, dict]:
    fr = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/frame.parquet")
    base = fr[["match_id", "tour", "year", "tournament_date", "a_won", "split", "tabpfn_split", "group"]].copy()
    base["odds_logit"] = fr["odds_logit"].to_numpy()
    orig = fr[["match_id"]].copy()
    for name in ["elo_logit"] + [n for n in SRC]:
        col = f"in_{name}"
        orig[name] = fr[col].to_numpy(dtype=float) if col in fr.columns else np.nan
    v = {"original": orig, "leakproof": rebuilt(MT.FEATURES, fr),
         "repaired": rebuilt(MT.REPAIRED / "repair_features.parquet", fr)}
    return base, v


def fit_predict(X_tr, y_tr, X_te) -> np.ndarray:
    beta, _ = TT.fit_logistic(X_tr, y_tr)
    return expit(X_te @ beta)


def score() -> pd.DataFrame:
    base, V = versions()
    recs = []
    for tour in TT.TOURS:
        for model, (inputs, use_odds, vers) in MODELS.items():
            cols = (["odds_logit"] if use_odds else []) + inputs
            split_col = "tabpfn_split" if use_odds else "split"
            ok = (base["tour"].eq(tour) & base[split_col].isin(["train", "test"])).to_numpy().copy()
            if use_odds:
                ok &= np.isfinite(base["odds_logit"].to_numpy())
            for ver in vers:                         # identical rows: every compared version has every input
                X = V[ver][inputs].to_numpy(dtype=float) if inputs else np.zeros((len(base), 0))
                ok &= np.isfinite(X).all(axis=1)
            tr = ok & base[split_col].eq("train").to_numpy()
            te = ok & base[split_col].eq("test").to_numpy()
            y = base["a_won"].astype(int).to_numpy()
            for ver in vers:
                X = np.column_stack([base["odds_logit"].to_numpy()] * use_odds
                                    + [V[ver][c].to_numpy(dtype=float) for c in inputs])
                p = fit_predict(X[tr], y[tr], X[te])
                recs.append(pd.DataFrame({"tour": tour, "model": model, "version": ver,
                                          "match_id": base["match_id"].to_numpy()[te], "year": base["year"].to_numpy()[te],
                                          "date": base["tournament_date"].to_numpy()[te], "y": y[te], "p": p,
                                          "train_rows": int(tr.sum())}))
    return pd.concat(recs, ignore_index=True)


def main() -> int:
    P = score()
    P["ll"] = TT.ll(P["p"].to_numpy(), P["y"].to_numpy())
    P.to_parquet(MT.OUT / "score_predictions.parquet", index=False)
    rows = []
    for (tour, model), g in P.groupby(["tour", "model"]):
        wide = g.pivot_table(index=["match_id", "date", "year"], columns="version", values="ll").reset_index()
        for window, sel in (("2022-2026", wide["year"].between(2022, 2026)), ("2026", wide["year"].eq(2026))):
            w = wide[sel]
            rec = {"tour": tour, "model": model, "window": window, "matches": len(w),
                   "train_rows": int(g["train_rows"].iloc[0])}
            for ver in ("original", "leakproof", "repaired"):
                if ver in w:
                    rec[f"ll_{ver}"] = float(w[ver].mean())
            for a, b in (("original", "leakproof"), ("repaired", "leakproof"), ("original", "repaired")):
                if a in w and b in w:
                    c = TT.compare(w[a].to_numpy(), w[b].to_numpy(), w["date"].to_numpy())
                    rec[f"gain_{b}_over_{a}"], rec[f"lo_{b}_over_{a}"], rec[f"hi_{b}_over_{a}"] = c["gain"], c["lo"], c["hi"]
            rows.append(rec)
    R = pd.DataFrame(rows)
    # each model against the recalibrated close (odds models) or recalibrated Elo (no-odds), per version
    gains = []
    for (tour, ver), g in P.groupby(["tour", "version"]):
        for model in g["model"].unique():
            ref = "market" if MODELS[model][1] else "elo"
            if model == ref:
                continue
            a = g[g["model"].eq(ref)].set_index("match_id")
            b = g[g["model"].eq(model)].set_index("match_id")
            ids = a.index.intersection(b.index)
            for window, yrs in (("2022-2026", (2022, 2026)), ("2026", (2026, 2026))):
                s = ids[b.loc[ids, "year"].between(*yrs).to_numpy()]
                if len(s) == 0:
                    continue
                c = TT.compare(a.loc[s, "ll"].to_numpy(), b.loc[s, "ll"].to_numpy(), b.loc[s, "date"].to_numpy())
                gains.append({"tour": tour, "version": ver, "model": model, "against": ref, "window": window,
                              "matches": c["n"], "gain": c["gain"], "lo": c["lo"], "hi": c["hi"]})
    G = pd.DataFrame(gains)
    R.to_csv(MT.OUT / "score_results.csv", index=False)
    G.to_csv(MT.OUT / "score_gains.csv", index=False)
    MT.jdump({"versions": R.to_dict("records"), "gains": G.to_dict("records"),
              "key": "milli-log-loss; positive = the second-named forecast has the lower log loss (better); "
                     "a 95% interval spanning 0 is a tie"}, MT.OUT / "score_summary.json")
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(R.round(4).to_string(index=False))
        print(G.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
