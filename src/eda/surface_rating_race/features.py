"""The surface-offset TTT over the whole history at the tuned constants, and the ratings scored on their own.

1. Per tour, the full history (2010 to the latest match) at the frozen overall constants and the offset constants of
   tuning_choice.json: data/studies/surface_rating_race/ttt_offset.parquet (match_id, tour, the pass's outputs). Check:
   on the tuning matches (2013-2018) the full pass gives the tuning pass's log loss (the leak-proof timeline makes a
   pass's early rows independent of later ones; the last days of 2018 may differ where a 2019 event's window starts in
   December).
2. The ratings alone, P(A wins) with no model, against each other (milli-log-loss, positive = second named better,
   95% intervals over four-week blocks):
       elo        Stage 1's surface Elo (the 70/30 blend; 75/25 women)
       elo_off    the surface-offset Elo of the Elo-pieces study (overall Elo plus the offset)
       ttt_blend  the decided TTT (leak-proof; the 35/65 or 30/70 blend)
       ttt_off    this study's surface-offset TTT
   on (a) the rating-systems study's evaluation matches (every level, qualifying included) and (b) the race's own
   population (main tour with closing odds, debut seasons out), 2019-2026 and 2022-2026. Each forecast raw, and
   rescaled: its log-odds times one slope per tour fitted on the population's 2013-2018 matches, the Elo-pieces study's
   method for its evidence (the rescaled form was added after the raw table showed the offset Elo behind Stage 1 Elo
   on every level, a raw-forecast miscalibration that study's numbers had removed).

Writes ttt_offset.parquet, ttt_offset_run.json, ratings_alone.csv, features_summary.json.
Run: ./python.sh src/eda/surface_rating_race/features.py [--score-only]   (--score-only: score the saved passes)
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.rating_systems import common as RC  # noqa: E402
from src.eda.surface_rating_race import common as C  # noqa: E402
from src.eda.surface_rating_race import runs as RU  # noqa: E402
from src.eda.surface_rating_race import ttt_offset as TO  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

PAIRS = [("elo", "elo_off"), ("elo", "ttt_blend"), ("elo", "ttt_off"), ("elo_off", "ttt_off"), ("ttt_blend", "ttt_off"),
         ("elo_off", "ttt_blend")]
WINDOWS = {"2013-2018 (tuning)": (2013, 2018), "2019-2026": (2019, 2026), "2022-2026": (2022, 2026)}


def chosen() -> dict:
    ch = json.loads((C.OUT / "tuning_choice.json").read_text())
    return {t: dict(RU.frozen_constants()[t], sigma_o=ch[t]["sigma_o"], gamma_o=ch[t]["gamma_o"]) for t in C.TOURS}


def job(tour: str) -> pd.DataFrame:
    t0 = time.time()
    t, h = RU.load_history(tour)
    o = RU.run_pass(h, chosen()[tour])
    o.insert(0, "match_id", t["match_id"].to_numpy())
    o.insert(1, "tour", tour)
    o["seconds"] = round(time.time() - t0, 1)
    return o


def main() -> int:
    t0 = time.time()
    run_file = C.OUT / "ttt_offset_run.json"
    if "--score-only" in sys.argv:          # the passes are saved; score them again without rerunning them
        o = pd.read_parquet(C.TTT_OFFSET)
        seconds = json.loads(run_file.read_text())["seconds"] if run_file.exists() else None
    else:
        with ProcessPoolExecutor(max_workers=2) as ex:
            parts = list(ex.map(job, C.TOURS))
        seconds = {p["tour"].iloc[0]: float(p["seconds"].iloc[0]) for p in parts}
        o = pd.concat(parts, ignore_index=True).drop(columns=["seconds"])
        o.to_parquet(C.TTT_OFFSET, index=False, compression="zstd")
        C.write_json(run_file, {"seconds": seconds, "constants": chosen(), "rows": int(len(o))})
        C.log(f"ttt_offset.parquet: {len(o):,} matches; seconds {seconds}")
    # forecasts of the four ratings
    f = pd.read_parquet(RC.OUT / "stageB_features.parquet", columns=["match_id", "tour", "year", "evaluation", "a_won",
                                                                       "p_elo"])
    m = RC.C.load_matches(["match_id", "tournament_date"]).set_index("match_id")
    f["tournament_date"] = m.reindex(f["match_id"])["tournament_date"].to_numpy()
    tt = pd.read_parquet(C.TTT_TIMED, columns=["match_id", "p_ttt_timed"]).rename(columns={"p_ttt_timed": "p_ttt_blend"})
    pc = pd.read_parquet(C.PIECES_OUT / "pieces.parquet", columns=["match_id", "R_a", "R_b", "D_a", "D_b"])
    pc["p_elo_off"] = expit(np.log(10) / 400 * ((pc["R_a"] + pc["D_a"].fillna(0)) - (pc["R_b"] + pc["D_b"].fillna(0))))
    oo = o[["match_id"]].copy()
    oo["p_ttt_off"] = TO.p_offset(o)
    for d in (tt, pc[["match_id", "p_elo_off"]], oo):
        f = f.merge(d, on="match_id", how="left", validate="one_to_one")
    f = f[f["evaluation"].astype(bool)].reset_index(drop=True)
    # the race's population: the frame's matches (main tour with closing odds), debut seasons out; Stage 1 Elo and the
    # offset Elo from the frame's own inputs (elo_logit; elo_overall + elo_surf_offset)
    fr = pd.read_parquet(C.PIECES_FRAME, columns=["match_id", "tour", "year", "a_won", "tournament_date", "debut_season",
                                                   "x_elo_logit", "x_elo_overall", "x_elo_surf_offset"])
    fr = fr[~fr["debut_season"].astype(bool)].reset_index(drop=True)
    fr["p_elo"] = expit(fr["x_elo_logit"])
    fr["p_elo_off"] = expit(fr["x_elo_overall"] + fr["x_elo_surf_offset"].fillna(0.0))
    for d in (tt, oo):
        fr = fr.merge(d, on="match_id", how="left", validate="one_to_one")
    rows, scales = [], {}
    names = ("elo", "elo_off", "ttt_blend", "ttt_off")
    for pop, df in (("evaluation (every level)", f), ("race population", fr)):
        y = df["a_won"].to_numpy(bool)
        # rescaled (added after the raw table was seen, to match the Elo-pieces study's method): per tour, the rating's
        # log-odds times one slope fitted on the population's 2013-2018 matches (no intercept)
        tune = df["year"].between(*C.TUNE_YEARS).to_numpy()
        for r in names:
            x = logit(np.clip(df[f"p_{r}"].to_numpy(dtype=float), 1e-9, 1 - 1e-9))
            s = np.full(len(df), np.nan)
            for tour in C.TOURS:
                tk = (df["tour"] == tour).to_numpy()
                k = tune & tk & np.isfinite(x)
                beta, _ = T.fit_logistic(x[k][:, None], y[k].astype(float))
                s[tk] = beta[0]
                scales[f"{pop}|{r}|{tour}"] = float(beta[0])
            df[f"p_{r}_scaled"] = expit(s * x)
        for tour in C.TOURS + ("both",):
            tm = (df["tour"] == tour) if tour != "both" else pd.Series(True, index=df.index)
            for label, (a, b) in WINDOWS.items():
                k = (tm & df["year"].between(a, b)).to_numpy() \
                    & np.isfinite(df[[f"p_{r}" for r in names]].to_numpy()).all(axis=1)
                g = df[k]
                for form, suffix in (("raw", ""), ("rescaled", "_scaled")):
                    ll = {r: C.ll(g[f"p_{r}{suffix}"].to_numpy(), y[k]) for r in names}
                    for base, model in PAIRS:
                        c = C.compare(ll[base], ll[model], g["tournament_date"].to_numpy())
                        rows.append({"population": pop, "forecast": form, "tour": tour, "window": label, "base": base,
                                     "model": model, "matches": c["n"], "gain": c["gain"], "lo": c["lo"], "hi": c["hi"],
                                     "log_loss_model": float(ll[model].mean())})
    R = pd.DataFrame(rows)
    R.to_csv(C.OUT / "ratings_alone.csv", index=False)
    ch = json.loads((C.OUT / "tuning_choice.json").read_text())
    check = {}
    m0 = RC.load_table()[["match_id", "tour", "year", "evaluation", "a_won"]].merge(oo, on="match_id", how="left")
    for tour in C.TOURS:
        k = (m0["evaluation"].astype(bool) & (m0["tour"] == tour) & m0["year"].between(*C.TUNE_YEARS)).to_numpy()
        check[tour] = {"full_pass": C.mean_ll(m0.loc[k, "p_ttt_off"].to_numpy(), m0.loc[k, "a_won"].to_numpy(bool)),
                       "tuning_pass": ch[tour]["log_loss"], "matches": int(k.sum()),
                       "tuning_matches": ch[tour]["matches"]}
    C.write_json(C.OUT / "features_summary.json", {
        "constants": chosen(), "seconds": seconds, "rows": int(len(o)), "tuning_log_loss_check": check,
        "rescaling_slopes_2013_2018": scales,
        "key": "milli-log-loss; positive = the second-named rating is better; 95% intervals over four-week blocks",
        "elapsed": round(time.time() - t0, 1)})
    with pd.option_context("display.width", 220, "display.max_rows", 300):
        print(json.dumps(check, indent=1))
        print(R[(R["tour"] != "both") & (R["window"] != "2013-2018 (tuning)")].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
