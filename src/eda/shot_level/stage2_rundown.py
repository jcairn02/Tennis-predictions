"""Stage 2, part 2: every shot-level feature scored with the earlier studies' harness (src/eda/ufc_ideas/common.py), so
that its numbers sit in the same list as every feature tried so far.

    single rows   every feature of stage2_features.parquet, per tour: alone, given surface Elo, given the closing odds
    the interaction   rally9 (A - B, last 52 weeks) with its product with the expected share of long rallies
    profiles      fixed here before any score was read (PROFILES): the core statistics together in each memory and kind,
                  the speed, sequence and style families, and everything of the last 52 weeks; inputs that are constant
                  on a tour are left out of that tour's profile
    two more bases for the profiles: "mktbox", the closing odds together with the men's 16-input box-score profile of
                  the UFC study's Stage D (adjperf on twelve statistics, two-week memory, plus adjdef on four), and
                  "elobox", surface Elo with the same profile. Each base is a walk-forward forecast (each season fitted on
                  earlier seasons only), so a gain over it is what the shot-level profile adds to the box scores on the
                  same matches

The reading follows the harness, with the closing odds as the reading base (results are ranked by the gain on the
odds); the gains given Elo are reported beside it.

Run:  ./python.sh src/eda/shot_level/stage2_rundown.py [--workers 5]
Writes data/studies/shot_level/stage2_frame.parquet (the scored frame) and stage2_ranking.csv, stage2_results.csv,
stage2_null_copies.csv, stage2_results.json (the harness's files), stage2_catalog.json (every row's inputs).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stats as T  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

BOX_PROFILE = [f"adjperf_{s}|decayed" for s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved",
                                                 "bp_faced_pg", "brk", "bp_conv", "rpw_first", "rpw_second")] + \
              [f"adjdef_{s}|decayed" for s in ("ace", "df", "first_in", "bp_faced_pg")]
CORE_OFF = ["srv_quick", "ret_quick", "rally5", "rally9", "ret_inplay", "winner_rate", "error_rate", "ue_share",
            "net_rate", "net_won"]
CORE_ADJ = ["srv_quick", "ret_quick", "rally5", "rally9", "ret_inplay", "winner_rate", "error_rate", "ue_share",
            "w_ratio", "net_won"]
CORE_DEF = ["srv_quick", "ret_quick", "ret_inplay", "winner_rate", "error_rate", "w_ratio", "net_rate", "net_won"]
SEQ = ["consolidate", "break_back", "serve_set", "pressure_srv", "first_in_pressure", "after_loss"]
STYLE = ["long_share", "t_share", "wide_share", "deep_ret", "bh_ue_share", "fh_win_share"]
PROFILES = {
    "core_off|dec2": ([f"{s}|off|dec2" for s in CORE_OFF], ("mktbox", "elobox")),
    "core_off|w52": ([f"{s}|off|w52" for s in CORE_OFF], ("mktbox", "elobox")),
    "core_adj|dec2": ([f"{s}|adj|dec2" for s in CORE_ADJ], ("mktbox", "elobox")),
    "core_adj|w52": ([f"{s}|adj|w52" for s in CORE_ADJ], ("mktbox", "elobox")),
    "core_def|w52": ([f"{s}|def|w52" for s in CORE_DEF], ()),
    "speed|w52": (["spd1|off|w52", "spd2|off|w52", "spd1_change|off|dec2-w52"], ()),
    "sequence|w52": ([f"{s}|off|w52" for s in SEQ], ()),
    "style|w52": ([f"{s}|off|w52" for s in STYLE], ()),
    "all_off|w52": ([f"{s}|off|w52" for s in T.ALL_STATS], ("mktbox",)),
}


def walk_base(frame: pd.DataFrame, base_col: str, cols: list[str]) -> np.ndarray:
    """Walk-forward forecast of logistic([logit base, cols]) without intercept: season Y fitted on the pool matches of
    earlier seasons where the base and every column exist (at least 300), scaled on the training rows. Missing where an
    input is missing or the season has too little training."""
    out = np.full(len(frame), np.nan)
    for t in C.TOURS:
        m = frame["tour"].eq(t).to_numpy()
        p = frame[base_col].to_numpy(dtype="float64")
        X = frame[cols].to_numpy(dtype="float64")
        ok = m & np.isfinite(p) & np.isfinite(X).all(axis=1)
        yr = frame["year"].to_numpy()
        y = frame["a_won"].to_numpy().astype(int)
        lb = logit(np.clip(np.nan_to_num(p, nan=0.5), 1e-9, 1 - 1e-9))
        for Y in range(C.EVAL_YEARS[0], C.EVAL_YEARS[-1] + 1):
            tr, te = ok & (yr < Y), ok & (yr == Y)
            if tr.sum() < U.MIN_TRAIN or te.sum() == 0:
                continue
            sd = X[tr].std(axis=0)
            sd[sd == 0] = 1.0
            Ztr = np.column_stack([lb[tr], X[tr] / sd])
            Zte = np.column_stack([lb[te], X[te] / sd])
            lr = LogisticRegression(C=np.inf, fit_intercept=False, max_iter=200).fit(Ztr, y[tr])
            out[te] = lr.predict_proba(Zte)[:, 1]
    return out


def tasks_for(frame: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    feats = [c for c in frame.columns if c.count("|") == 2 and not c.startswith(("adjperf_", "adjdef_"))]
    tasks, cat = [], []
    for t in C.TOURS:
        tt = frame["tour"].eq(t)
        for c in feats:
            if c.startswith("rally_edge"):
                continue
            s, kind, mem = c.split("|")
            fam = T.FAMILY_OF.get(s, "speed")
            tasks.append(U.task(t, f"{s}|{kind}", mem, f"{s} ({kind}, {mem})", fam, [c]))
            cat.append({"tour": t, "id": f"{s}|{kind}", "form": mem, "inputs": [c], "family": fam})
        cols = ["rally9|off|w52", "rally_edge|x_long|w52"]
        tasks.append(U.task(t, "rally_edge", "w52", "long-rally edge where long rallies are likely", "rally", cols))
        cat.append({"tour": t, "id": "rally_edge", "form": "w52", "inputs": cols, "family": "rally"})
        for name, (cols, extra) in PROFILES.items():
            use = [c for c in cols if c in frame and np.nanstd(frame.loc[tt, c].to_numpy(dtype="float64")) > 0]
            bases = {"mktbox": "p_mktbox", "elobox": "p_elobox"}
            scores = ("alone", "elo", "market") + tuple(extra)
            pid, form = name.split("|")
            tasks.append(U.task(t, f"profile_{pid}", form, f"profile: {pid} ({form}, {len(use)} inputs)", "profile", use,
                                scores=scores, bases={k: v for k, v in bases.items() if k in extra}))
            cat.append({"tour": t, "id": f"profile_{pid}", "form": form, "inputs": use, "family": "profile",
                        "extra_bases": list(extra), "dropped_constant": [c for c in cols if c not in use]})
    return tasks, cat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=5)
    args = ap.parse_args()
    S.log("frame: features, box-score profile, the two extra bases")
    frame = pd.read_parquet(S.OUT / "stage2_features.parquet")
    box = pd.read_parquet(ROOT / "data/studies/ufc_ideas/stageD_profile_features.parquet", columns=["match_id"] + BOX_PROFILE)
    frame = frame.merge(box, on="match_id", how="left")
    assert len(frame) == 255123
    frame["p_mktbox"] = walk_base(frame, "p_mkt", BOX_PROFILE)
    frame["p_elobox"] = walk_base(frame, "p_elo", BOX_PROFILE)
    S.log(f"  p_mktbox on {int(np.isfinite(frame['p_mktbox']).sum())} matches, p_elobox on {int(np.isfinite(frame['p_elobox']).sum())}")
    path = S.OUT / "stage2_frame.parquet"
    frame.to_parquet(path, index=False)
    tasks, cat = tasks_for(frame)
    (S.OUT / "stage2_catalog.json").write_text(json.dumps(cat, indent=1), encoding="utf-8")
    S.log(f"{len(tasks)} rows to score")
    res = U.rundown(path, tasks, S.OUT / "stage2", workers=args.workers, reading_base="market")
    r = res["ranking"]
    show = ["tour", "id", "form", "inputs", "alone_imp", "elo_imp", "market_imp", "market_lo", "market_hi",
            "market_scored", "market_clears_line", "reading"]
    with pd.option_context("display.width", 250, "display.max_rows", 80):
        for t in C.TOURS:
            print(r[r["tour"].eq(t)][show].head(25).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
