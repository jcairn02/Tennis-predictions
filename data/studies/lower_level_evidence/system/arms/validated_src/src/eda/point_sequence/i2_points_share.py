"""I2: is the women's points-share anomaly (predictability Stage 2: log loss 0.118 real against 0.103 iid replay) real?

Pre-registration: data/studies/point_sequence/trait_prereg.md, section 7 (and deviation D1). Run after trait_build.py:
    ./python.sh src/eda/point_sequence/i2_points_share.py

For each population (women: WTA umpire log, non-Slam, best of three, obs from 1 Jun 2019, seasons to 2024; men's
control: every source, non-Slam, best of three, 2013-2024; secondaries) and each world (real; 3 replays in each of the
variants V05, V1, V15, VPS, built by trait_build.py), a five-fold cross-validated logistic regression without intercept
(stage2_anatomy.oof_logit) of the winner on 100 x (A's points share - 0.5), and on logit of the iid plug-in chance at
the match's measured serve rates (stage2_iid.match_win_by). Gap = real - replay log loss, per match paired, in
milli-log-loss; positive = the real points share decides matches less well than iid luck.

Writes data/studies/point_sequence/i2_gaps.csv, i2_diagnostics.csv, i2_results.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import trait_common as TC  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402
from src.eda.predictability_diagnostic.stage2_anatomy import logit, logloss, oof_logit  # noqa: E402

FAMILIES = {"V05": [f"V05_{r}" for r in range(TC.REPLAYS)], "V1": [f"V1_{r}" for r in range(TC.REPLAYS)],
            "V15": [f"V15_{r}" for r in range(TC.REPLAYS)], "VPS": [f"VPS_{r}" for r in range(TC.REPLAYS)]}
JUNE_2019 = int(np.datetime64("2019-06-01", "D").astype("int64"))


def populations(pop: pd.DataFrame) -> dict:
    gs = pop["level"].eq("GS")
    w = pop["tour"].eq("wta")
    a = pop["tour"].eq("atp")
    bo3 = pop["bo"].eq(3)
    from19 = (pop["obs"] >= JUNE_2019) & pop["year"].le(2024)
    return {
        "women_wta_log_nonslam (primary)": w & pop["source"].eq("wta") & ~gs & bo3 & from19,
        "men_nonslam_2013_2024 (primary control)": a & ~gs & bo3,
        "men_nonslam_jun2019_2024 (secondary)": a & ~gs & bo3 & from19,
        "women_all_sources_nonslam_jun2019_2024 (secondary)": w & ~gs & bo3 & from19,
        "women_slams_jun2019_2024 (secondary)": w & gs & bo3 & from19,
        "men_slams_bo5_2013_2024 (secondary)": a & gs & pop["bo"].eq(5),
    }


def world_frame(pop, mf, pm, world):
    """Per match: points share edge, winner, plug-in chance, tie-breaks, for one world."""
    g = mf[mf["world"] == world].set_index("mcode").sort_index()
    p = pm[pm["world"] == world]
    sa = p[p["side"] == 1].set_index("mcode").sort_index()
    sb = p[p["side"] == 2].set_index("mcode").sort_index()
    pa = (sa["svpt_won"] / sa["svpt"]).to_numpy("float64")
    pb = (sb["svpt_won"] / sb["svpt"]).to_numpy("float64")
    rule = pop["final"].map(TC.STAGE2_RULE).to_numpy()
    plug = M.match_win_by(np.clip(pa, 1e-4, 1 - 1e-4), np.clip(pb, 1e-4, 1 - 1e-4), pop["bo"].to_numpy(), rule)
    share = (g["a_pts"] / g["pts"]).to_numpy("float64")
    return pd.DataFrame({"share": share, "a_won": g["a_won"].to_numpy() > 0.5, "plug": plug,
                         "tiebreaks": g["tiebreaks"].to_numpy("float64"), "sets": g["sets"].to_numpy("float64"),
                         "pts": g["pts"].to_numpy("float64")})


def fit(frame: pd.DataFrame) -> dict:
    y = frame["a_won"].to_numpy()
    x = 100 * (frame["share"].to_numpy() - 0.5)
    p1, c1 = oof_logit(x, y)
    p2, c2 = oof_logit(logit(frame["plug"].to_numpy()), y)
    won_share = np.where(y, frame["share"], 1 - frame["share"])
    fewer = won_share < 0.5
    return {"ll_share": logloss(p1, y), "ll_plug": logloss(p2, y), "slope_share": float(c1[0]), "slope_plug": float(c2[0]),
            "diag": {"matches": int(len(y)), "tiebreaks_per_match": float(frame["tiebreaks"].mean()),
                     "deciding_set_pct": float(100 * (frame["sets"] == frame["sets"].max()).mean()),
                     "won_with_fewer_points_pct": float(100 * fewer.mean()),
                     "equal_points_pct": float(100 * (np.abs(frame["share"] - 0.5) < 1e-12).mean()),
                     "points_share_sd_pp": float(100 * frame["share"].std()),
                     "winner_mean_share_pct": float(100 * won_share.mean()),
                     "points_per_match": float(frame["pts"].mean()),
                     "odds_per_point": float(np.exp(c1[0])), "cv_ll_share": float(logloss(p1, y).mean()),
                     "cv_ll_plug": float(logloss(p2, y).mean())}}


def gap(a: np.ndarray, b: np.ndarray) -> dict:
    d = np.asarray(a) - np.asarray(b)
    n = len(d)
    mean, se = 1000 * d.mean(), 1000 * d.std(ddof=1) / np.sqrt(n)
    return {"n": int(n), "mLL": float(mean), "lo": float(mean - 1.96 * se), "hi": float(mean + 1.96 * se)}


def box_score_check(pop, sub_idx, real_frame) -> dict:
    """Real matches only: the Stage 0 box score's points share against the sequence's, on the same matches."""
    mp = pd.read_parquet(TC.S0 / "stage0_match_players.parquet", columns=["match_id", "side", "tpw_n", "tpw_d", "has_box"])
    a = mp[mp["side"].eq("A")].set_index("match_id")
    ids = pop["match_id"].to_numpy()[sub_idx]
    tn = a["tpw_n"].reindex(ids).to_numpy("float64")
    td = a["tpw_d"].reindex(ids).to_numpy("float64")
    hb = a["has_box"].reindex(ids).fillna(False).to_numpy().astype(bool)
    ok = hb & np.isfinite(tn) & np.isfinite(td) & (td > 0)
    rf = real_frame.iloc[sub_idx].reset_index(drop=True)
    seq_share = rf["share"].to_numpy()[ok]
    box_share = (tn / np.where(td > 0, td, 1))[ok]
    y = rf["a_won"].to_numpy()[ok]
    pb, cb = oof_logit(100 * (box_share - 0.5), y)
    ps, cs = oof_logit(100 * (seq_share - 0.5), y)
    llb, lls = logloss(pb, y), logloss(ps, y)
    diff = np.abs(box_share - seq_share)
    wrong_side = (np.where(y, box_share, 1 - box_share) < 0.45) & (np.where(y, seq_share, 1 - seq_share) >= 0.5)
    return {"matches_with_box": int(ok.sum()), "of": int(len(sub_idx)),
            "cv_ll_box_share": float(llb.mean()), "cv_ll_seq_share": float(lls.mean()),
            "box_minus_seq": gap(llb, lls), "share_differs_by_over_1pp_pct": float(100 * (diff > 0.01).mean()),
            "share_differs_by_over_5pp": int((diff > 0.05).sum()),
            "box_says_winner_under_45pct_while_seq_over_50pct": int(wrong_side.sum()),
            "slope_box": float(cb[0]), "slope_seq": float(cs[0])}


def main() -> int:
    t0 = time.time()
    pop = pd.read_parquet(TC.OUT / "trait_population.parquet")
    mf = pd.read_parquet(TC.OUT / "trait_matches.parquet")
    pm = pd.concat([pd.read_parquet(TC.OUT / "trait_player_matches.parquet", columns=["world", "mcode", "side", "svpt", "svpt_won"]),
                    pd.read_parquet(TC.OUT / "trait_player_matches_variants.parquet", columns=["world", "mcode", "side", "svpt", "svpt_won"])],
                   ignore_index=True)
    worlds = ["real"] + [w for f in FAMILIES.values() for w in f]
    frames = {w: world_frame(pop, mf, pm, w) for w in worlds}
    TC.log("world frames built")
    pops = populations(pop)
    gap_rows, diag_rows, out = [], [], {"populations": {}}
    for pname, mask in pops.items():
        idx = np.flatnonzero(mask.to_numpy())
        if len(idx) < 300:
            continue
        fits = {w: fit(frames[w].iloc[idx].reset_index(drop=True)) for w in worlds}
        for w in worlds:
            diag_rows.append({"population": pname, "world": w, **fits[w]["diag"]})
        res = {"matches": int(len(idx)), "real": fits["real"]["diag"]}
        for fam, ws in FAMILIES.items():
            rep_share = np.mean([fits[w]["ll_share"] for w in ws], axis=0)
            rep_plug = np.mean([fits[w]["ll_plug"] for w in ws], axis=0)
            gs = gap(fits["real"]["ll_share"], rep_share)
            gp = gap(fits["real"]["ll_plug"], rep_plug)
            row = {"population": pname, "family": fam, "matches": int(len(idx)),
                   "real_ll_share": float(fits["real"]["ll_share"].mean()), "replay_ll_share": float(rep_share.mean()),
                   "gap_share_mLL": gs["mLL"], "gap_share_lo": gs["lo"], "gap_share_hi": gs["hi"],
                   "real_ll_plug": float(fits["real"]["ll_plug"].mean()), "replay_ll_plug": float(rep_plug.mean()),
                   "gap_plug_mLL": gp["mLL"], "gap_plug_lo": gp["lo"], "gap_plug_hi": gp["hi"],
                   "replay_ll_share_by_replay": [float(fits[w]["ll_share"].mean()) for w in ws]}
            gap_rows.append(row)
            res[fam] = row
        if pname.startswith("women_wta_log") or pname.startswith("women_all") or pname.startswith("men_nonslam_2013"):
            res["box_score_check"] = box_score_check(pop, idx, frames["real"])
        out["populations"][pname] = res
        TC.log(f"{pname}: {len(idx):,} matches")
    gaps = pd.DataFrame(gap_rows)
    gaps.to_csv(TC.OUT / "i2_gaps.csv", index=False)
    pd.DataFrame(diag_rows).to_csv(TC.OUT / "i2_diagnostics.csv", index=False)
    # decision (pre-registered): women's primary gap positive and excluding 0 under every variant; men's covers 0 at V1
    wname, mname = "women_wta_log_nonslam (primary)", "men_nonslam_2013_2024 (primary control)"
    wg = gaps[gaps["population"] == wname].set_index("family")
    mg = gaps[gaps["population"] == mname].set_index("family")
    women_ok = {f: bool(wg.loc[f, "gap_share_lo"] > 0) for f in FAMILIES}
    men_covers = {f: bool(mg.loc[f, "gap_share_lo"] <= 0 <= mg.loc[f, "gap_share_hi"]) for f in FAMILIES}
    diff = {}
    for f in FAMILIES:
        se_w = (wg.loc[f, "gap_share_hi"] - wg.loc[f, "gap_share_lo"]) / (2 * 1.96)
        se_m = (mg.loc[f, "gap_share_hi"] - mg.loc[f, "gap_share_lo"]) / (2 * 1.96)
        d = wg.loc[f, "gap_share_mLL"] - mg.loc[f, "gap_share_mLL"]
        se = float(np.hypot(se_w, se_m))
        diff[f] = {"women_minus_men_mLL": float(d), "lo": float(d - 1.96 * se), "hi": float(d + 1.96 * se)}
    out["decision"] = {"women_gap_positive_excluding_0": women_ok, "men_gap_covers_0": men_covers,
                       "women_minus_men": diff,
                       "pass": bool(all(women_ok.values()) and men_covers["V1"]),
                       "rule": "women's points-share gap positive with its 95% interval excluding 0 under V05, V1, V15 "
                               "and VPS, and the men's covering 0 under V1"}
    out["stage2_reference"] = "predictability Stage 2: women 0.118 real vs 0.103 replay; men bo3 0.117 vs 0.118 (box scores)"
    out["seconds"] = round(time.time() - t0, 1)
    (TC.OUT / "i2_results.json").write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    TC.log("wrote i2_gaps.csv, i2_diagnostics.csv, i2_results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
