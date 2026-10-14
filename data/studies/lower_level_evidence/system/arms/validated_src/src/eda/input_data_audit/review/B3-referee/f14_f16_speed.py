"""B3-referee, F14/F15/F16: flagged serve-speed records against other sources, the player's norm and the box score,
and the panel's choice simulated without them.

Read-only. Writes data/studies/input_data_audit/fixes/B3-referee/f14_rows.csv, f15_rows.csv, f16_rows.csv and
f14_f16_summary.json.

Definitions (checked against src/eda/serve_speed_tabpfn/panel.py):
  * spd_max on a key-statistic record is the SAME record's maximum for the SAME player (handoff "Max Speed" per player;
    ManTennisData ks_max per player row), not the match's maximum over both players.
  * the panel's use rows (speed_panel.parquet, use = True) are what reaches spd_L; a record that is not chosen does not.
  * the fallback: panel.choose() re-run on the player-match's records with the flagged record marked invalid, then the
    panel's value-level drops (men y < 120, women y < 100, n < 10; no_clock is kept from the panel row).
Norm: median y of the player's OTHER use rows within 365 days either side (same tour), with their count.
Box check: n of a key-statistic record is its first serves in; Stage 0's first_in for the same side should equal it
(n2 = first serves total - first in = second-serve points) when the record belongs to that match.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
SP = ROOT / "data/studies/serve_speed_tabpfn"
S0 = ROOT / "data/studies/predictability_diagnostic"


def norms(u: pd.DataFrame) -> pd.DataFrame:
    """Median y (and spd_max) of each use row's player's other use rows within 365 days either side."""
    out = []
    for (tour, pid), g in u.groupby(["tour", "player_id"]):
        t = g["obs"].to_numpy()
        y = g["y"].to_numpy()
        mx = g["spd_max"].to_numpy()
        for i, idx in enumerate(g.index):
            w = (np.abs(t - t[i]) <= 365)
            w[i] = False
            out.append((idx, np.median(y[w]) if w.any() else np.nan, int(w.sum()),
                        np.nanmedian(mx[w]) if w.any() and np.isfinite(mx[w]).any() else np.nan))
    n = pd.DataFrame(out, columns=["idx", "norm_y", "norm_n", "norm_max"]).set_index("idx")
    return n


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    from src.eda.serve_speed_tabpfn import panel as PN
    rec = pd.read_parquet(SP / "speed_records.parquet")
    pan = pd.read_parquet(SP / "speed_panel.parquet")
    s0m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "level"])
    s0p = pd.read_parquet(S0 / "stage0_match_players.parquet",
                          columns=["match_id", "side", "player_id", "first_in", "svpt", "df"])
    u = pan[pan["use"]].copy()
    u = u.join(norms(u))
    u = u.merge(s0p.rename(columns={"player_id": "s0_pid"}), on=["match_id", "side"], how="left")
    u["box_first_in"] = u["first_in"]
    u["box_second_pts"] = u["svpt"] - u["first_in"]
    u = u.drop(columns=["first_in", "svpt", "df"])
    key = ["match_id", "side", "source", "source_key"]
    rec_idx = rec.set_index(key)

    def others(row) -> list:
        o = rec[(rec.match_id == row.match_id) & (rec.side == row.side)
                & ~((rec.source == row.source) & (rec.source_key == row.source_key))]
        return [(s, k, round(float(y), 1), int(n) if pd.notna(n) else None, bool(v), why)
                for s, k, y, n, v, why in zip(o.source, o.kind, o.y, o.n, o.valid, o.invalid_reason)]

    def fallback(rows: pd.DataFrame) -> pd.DataFrame:
        """Re-run panel.choose on the affected player-matches with the given records marked invalid."""
        ms = rows[["match_id", "side"]].drop_duplicates()
        r = rec.merge(ms, on=["match_id", "side"], how="inner").copy()
        bad = r.set_index(key).index.isin(pd.MultiIndex.from_frame(rows[key]))
        r.loc[bad, "valid"] = False
        r.loc[bad, "invalid_reason"] = "b3_flag"
        best = PN.choose(r, s0m)
        pr = pan.set_index(["match_id", "side"])
        best = best.merge(pr[["tour", "player_id", "drop_reason"]].rename(columns={"drop_reason": "panel_drop"}),
                          left_on=["match_id", "side"], right_index=True, how="left")
        low = np.where(best["tour"].eq("atp"), best["y"] < PN.MEN_MIN, best["y"] < PN.WOMEN_MIN)
        reason = best["drop_reason"].astype(object).copy()
        reason[(reason == "") & best["panel_drop"].eq("no_clock").to_numpy()] = "no_clock"
        reason[(reason == "") & low] = "implausible"
        reason[(reason == "") & (best["n"].fillna(0).round() < PN.MIN_N)] = "low_n"
        best["new_use"] = reason.eq("")
        best["new_drop"] = reason
        return best[["match_id", "side", "source", "source_key", "kind", "y", "n", "new_use", "new_drop"]].rename(
            columns={"source": "new_source", "source_key": "new_source_key", "kind": "new_kind", "y": "new_y",
                     "n": "new_n"})

    summary = {}

    # ---------------- F14 ----------------
    has = u["spd_max"].notna()
    f14 = u[has & (u["y_raw"] >= u["spd_max"] - 1.0)].copy()
    f14["rule_strict_gt"] = f14["y_raw"] > f14["spd_max"]
    f14["rule_ge"] = f14["y_raw"] >= f14["spd_max"]
    f14["max_equals_y"] = f14["y_raw"] == f14["spd_max"]
    f14["y_minus_norm"] = f14["y"] - f14["norm_y"]
    f14["max_minus_normmax"] = f14["spd_max"] - f14["norm_max"]
    f14["n_matches_box"] = f14["n"] == f14["box_first_in"]
    f14["other_records"] = [others(r) for r in f14.itertuples()]
    fb = fallback(f14)
    f14 = f14.merge(fb, on=["match_id", "side"], how="left")
    f14["new_minus_norm"] = f14["new_y"] - f14["norm_y"]
    # classification: which field is wrong?
    f14["verdict"] = np.select(
        [(f14["y_minus_norm"] > 15) | (f14["y"] >= 240),
         (f14["y_minus_norm"].abs() <= 8) & (f14["max_minus_normmax"] < -8),
         f14["y_minus_norm"].abs() <= 8],
        ["average_wrong", "max_wrong_average_normal", "average_normal"], "unclear")
    cols = ["match_id", "side", "player_id", "tour", "year", "tournament_name", "round", "source", "source_key",
            "y_raw", "y", "n", "box_first_in", "n_matches_box", "spd2_raw", "spd_max", "norm_y", "norm_n", "norm_max",
            "y_minus_norm", "max_minus_normmax", "rule_strict_gt", "rule_ge", "max_equals_y", "verdict",
            "other_records", "new_source", "new_kind", "new_y", "new_n", "new_use", "new_drop", "new_minus_norm"]
    f14[cols].to_csv(OUT / "f14_rows.csv", index=False)
    summary["F14"] = {
        "rows": int(len(f14)), "by_source": f14["source"].value_counts().to_dict(),
        "strict_gt": int(f14["rule_strict_gt"].sum()), "ge": int(f14["rule_ge"].sum()),
        "max_equals_y": int(f14["max_equals_y"].sum()),
        "verdicts": f14["verdict"].value_counts().to_dict(),
        "verdict_by_source": f14.groupby(["source", "verdict"]).size().to_dict(),
        "n_matches_box": f14["n_matches_box"].value_counts(dropna=False).to_dict(),
        "fallback_use": f14["new_use"].value_counts(dropna=False).to_dict(),
        "fallback_source": f14["new_source"].value_counts(dropna=False).to_dict(),
        "fallback_minus_norm_abs_le_8": int((f14["new_use"] & (f14["new_minus_norm"].abs() <= 8)).sum()),
        "fallback_minus_norm_abs_gt_15": int((f14["new_use"] & (f14["new_minus_norm"].abs() > 15)).sum()),
    }
    summary["F14"]["verdict_by_rule"] = {
        r: f14[f14[r]]["verdict"].value_counts().to_dict() for r in ("rule_strict_gt", "rule_ge")}
    summary["F14"]["verdict_within_1_only"] = f14[~f14["rule_ge"]]["verdict"].value_counts().to_dict()

    # ---------------- F15 ----------------
    f15 = u[u["tour"].eq("atp") & (u["y"] >= 240)].copy()
    f15["in_f14"] = f15.set_index(key).index.isin(f14.set_index(key).index)
    f15["y_minus_norm"] = f15["y"] - f15["norm_y"]
    f15["other_records"] = [others(r) for r in f15.itertuples()]
    fb15 = fallback(f15)
    f15 = f15.merge(fb15, on=["match_id", "side"], how="left")
    f15["new_minus_norm"] = f15["new_y"] - f15["norm_y"]
    f15[["match_id", "side", "player_id", "year", "tournament_name", "round", "source", "source_key", "y_raw", "y", "n",
         "box_first_in", "spd_max", "norm_y", "norm_n", "y_minus_norm", "in_f14", "other_records", "new_source",
         "new_y", "new_n", "new_use", "new_drop", "new_minus_norm"]].to_csv(OUT / "f15_rows.csv", index=False)
    # records (chosen or not) of >= 240 for men anywhere, and women >= 210
    hi_all = rec[(rec.tour_s0.eq("atp") & (rec.y >= 240)) | (rec.tour_s0.eq("wta") & (rec.y >= 210))]
    summary["F15"] = {"use_rows_men_ge_240": int(len(f15)), "of_which_in_f14": int(f15["in_f14"].sum()),
                      "by_source": f15["source"].value_counts().to_dict(),
                      "y_range": [float(f15["y"].min()), float(f15["y"].max())] if len(f15) else None,
                      "y_minus_norm_min": float(f15["y_minus_norm"].min()) if len(f15) else None,
                      "fallback_use": f15["new_use"].value_counts(dropna=False).to_dict(),
                      "fallback_minus_norm": f15["new_minus_norm"].round(1).tolist(),
                      "all_records_men_ge240_or_women_ge210": int(len(hi_all)),
                      "all_records_by_source_valid": hi_all.groupby(["source", "valid"]).size().to_dict()}
    # use rows just under 240 for context
    summary["F15"]["use_rows_men_230_240"] = int((u["tour"].eq("atp") & u["y"].between(230, 240, inclusive="left")).sum())
    summary["F15"]["max_use_y_men_excl_ge240"] = float(u[u["tour"].eq("atp") & (u["y"] < 240)]["y"].max())

    # ---------------- F16 ----------------
    k = ["player_id", "y_raw", "n", "spd2_raw", "spd_max"]
    dup = u[u.duplicated(k, keep=False) & u["n"].gt(0)].sort_values(k + ["obs"]).copy()
    dup["pair"] = dup.groupby(k, dropna=False).ngroup()
    dup["n_matches_box"] = dup["n"] == dup["box_first_in"]
    dup["n2_matches_box"] = (dup["n2"] == dup["box_second_pts"])
    dup["y_minus_norm"] = dup["y"] - dup["norm_y"]
    dup["kind_f16"] = "same_player_two_matches"
    ab = u.pivot_table(index="match_id", columns="side", values="y_raw", aggfunc="first").dropna()
    abn = u.pivot_table(index="match_id", columns="side", values="n", aggfunc="first").reindex(ab.index)
    same = ab[(ab["A"] == ab["B"]) & (abn["A"] == abn["B"])].index
    sides = u[u["match_id"].isin(same)].copy()
    sides["pair"] = sides["match_id"]
    sides["n_matches_box"] = sides["n"] == sides["box_first_in"]
    sides["n2_matches_box"] = sides["n2"] == sides["box_second_pts"]
    sides["y_minus_norm"] = sides["y"] - sides["norm_y"]
    sides["kind_f16"] = "both_sides_identical"
    f16 = pd.concat([dup, sides], ignore_index=True)
    f16["other_records"] = [others(r) for r in f16.itertuples()]
    fb16 = fallback(f16)
    f16 = f16.merge(fb16, on=["match_id", "side"], how="left")
    f16["new_minus_norm"] = f16["new_y"] - f16["norm_y"]
    f16[["kind_f16", "pair", "match_id", "side", "player_id", "year", "tournament_name", "round", "obs", "source",
         "source_key", "y_raw", "n", "n2", "spd2_raw", "spd_max", "box_first_in", "box_second_pts", "n_matches_box",
         "n2_matches_box", "norm_y", "norm_n", "y_minus_norm", "other_records", "new_source", "new_y", "new_n", "new_use",
         "new_drop", "new_minus_norm"]].to_csv(OUT / "f16_rows.csv", index=False)
    summary["F16"] = {"same_player_two_matches_rows": int(len(dup)), "pairs": int(dup["pair"].nunique()),
                      "both_sides_identical_matches": int(len(same)),
                      "n_matches_box": f16.groupby(["kind_f16", "n_matches_box"]).size().to_dict()}
    def strkeys(o):
        if isinstance(o, dict):
            return {("|".join(map(str, k)) if isinstance(k, tuple) else str(k)): strkeys(v) for k, v in o.items()}
        if isinstance(o, list):
            return [strkeys(v) for v in o]
        return o

    summary = strkeys(summary)
    (OUT / "f14_f16_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
