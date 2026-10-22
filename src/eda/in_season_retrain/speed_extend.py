"""Stage 2's speed table extended to every men's match of a retrain's season (the owner's condition 1, 20 Oct 2026:
"speed table extended and checked"; docs/decisions/2026-10-09-adoption-by-change-class.md, its amendment). Reads no
match result.

The decided history column (data/studies/infosys_atp_backfill/speed_columns_augmented.parquet) was built for the
serve-speed study's frame keys (63,737 matches, its 2026 ending in early October), so a newer instance's later season-Y
matches have no spd_L_B / spd_L_D. Here the same builder (serve_speed_tabpfn/adaptive/columns.py: build_scenario on the
augmented history, its release table and the 28-day filter; infosys_atp_backfill/columns.py's build_on) runs on side
targets made from the instance's own tables for its season-Y men's matches: the frame's match ids and side A (Stage 0's,
checked: the frame's a_won equals Stage 0's), the players, tournament and round from Stage 0, es / lf / obs from the
match clock, tdate from the tournament date.

    check   on the season-Y matches the column holds, the builder's values on the instance's own targets against the
            column's: how many are equal, and for the rest whether their targets differ from the study's keys (players
            re-keyed or swapped, a timing change) or not (unexplained)
    write   <instance>/stage2_speed_columns.parquet: match_id, spd_L_B, spd_L_D, source ("column": the decided
            column's value, kept; "extended": the builder's, for a match the column lacks), for every frame match of
            2019 .. season; and stage2_speed_columns.json (the check, and the history and column read, with SHA-256)

The decided history and column (decided()) are live_panel's: since 22 Oct 2026 the repaired history (576 published
averages more than 5 km/h off the match's point record replaced by the point mean) and its column
(source_reconciliation/applied/speed_columns_repaired.parquet), the owner's approval of that day
(docs/decisions/2026-10-22-source-reconciliation-repairs.md); before, the backfilled history and
speed_columns_augmented.parquet. So the first retrain after it carries the repair into stage 2, and no earlier instance
changes: each keeps the table its own retrain wrote.

    ./python.sh src/eda/in_season_retrain/speed_extend.py --instance <folder> --season 2026 [--stage0 <parquet>]
                                                          [--timing <parquet>]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import training_rows as TR  # noqa: E402

COLUMN = ROOT / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"   # until 22 Oct 2026
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"


def decided() -> tuple[Path, Path]:
    """(the decided speed history, stage 2's decided column on it): live_panel's, the repaired pair once the repair of
    22 Oct 2026 is present (checked against their records), else the backfilled history and COLUMN."""
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    col = LP.decided_column()
    return (LP.REPAIRED if col == LP.COLUMN_REPAIRED else LP.BACKFILLED), col
OUT_NAME = "stage2_speed_columns"
SCEN = ("B", "D")
TOL = 1e-9


def instance_keys(instance: Path, season: int, stage0: Path, timing: Path) -> pd.DataFrame:
    """Frame keys (panel.build_frame_keys' columns) for the instance's men's matches of `season`, from its own tables."""
    from src.eda.serve_speed_tabpfn import panel as P
    f = pd.read_parquet(instance / "model_frame.parquet", columns=["match_id", "tour", "season", "tournament_date",
                                                                   "a_won"])
    f = f[(f["season"] == season) & (f["tour"] == "atp")].copy()
    f["match_id"] = f["match_id"].astype(str)
    s0 = pd.read_parquet(stage0, columns=["match_id", "player_a_id", "player_b_id", "tournament_id", "round_order",
                                          "level", "a_won"])
    s0["match_id"] = s0["match_id"].astype(str)
    k = f.merge(s0, on="match_id", how="left", suffixes=("", "_s0"), validate="one_to_one")
    if k["player_a_id"].isna().any():
        raise SystemExit(f"{int(k['player_a_id'].isna().sum())} frame matches are not in Stage 0")
    if not (k["a_won"].astype(int) == k["a_won_s0"].astype(int)).all():
        raise SystemExit("the frame's side A is not Stage 0's on some matches")
    tm = pd.read_parquet(timing, columns=["match_id", "es", "lf", "obs"])
    tm["match_id"] = tm["match_id"].astype(str)
    k = k.merge(tm, on="match_id", how="left", validate="one_to_one")
    if k[["es", "lf", "obs"]].isna().any().any():
        raise SystemExit("frame matches without a timing row")
    k["rebuilt_id"] = k["match_id"]
    k["obs_raw"] = k["obs"].astype(float)
    k["obs"] = np.floor(k["obs_raw"]).astype("int64")
    k["es"], k["lf"] = k["es"].astype("int64"), k["lf"].astype("int64")
    k["tdate"] = P.days(k["tournament_date"])
    k["round_order"] = k["round_order"].astype("int64")
    k["id_conflict"], k["flipped"] = False, False
    k["a_rebuilt"], k["b_rebuilt"] = k["player_a_id"], k["player_b_id"]
    return k[["match_id", "rebuilt_id", "tour", "season", "player_a_id", "player_b_id", "es", "lf", "obs", "obs_raw",
              "tdate", "tournament_id", "round_order", "level", "id_conflict", "flipped", "a_rebuilt",
              "b_rebuilt"]].reset_index(drop=True)


def _key(d: pd.DataFrame) -> pd.Series:
    return d["match_id"].astype(str) + "|" + d["side"].astype(str)


def history(live: bool = True, repaired: bool = True) -> tuple[pd.DataFrame, pd.Series]:
    """The speed history the builder reads, and each live-only row's own release day. The decided history (frozen:
    its latest observation 3 Oct 2026; live_panel.frozen_panel, the repaired one since 22 Oct 2026) and, with live, the
    live panel's rows it lacks (the daily collector's from 8 Oct 2026, and any backfill: 21 Oct 2026), so a match
    after the history's end reads what the live feed had. repaired=False: the history without the 22 Oct repair."""
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    h = LP.frozen_panel(repaired=repaired)
    if not live:
        return h, pd.Series(dtype="int64")
    lp = LP.load()
    new = lp[~_key(lp).isin(set(_key(h)))]
    lacking = [c for c in h.columns if c not in new.columns]
    if lacking:
        raise SystemExit(f"the live panel lacks the history's columns {lacking}")
    rel = pd.Series(new["release"].to_numpy(dtype="int64"), index=_key(new).to_numpy())
    return pd.concat([h, new[list(h.columns)]], ignore_index=True), rel


def release_table(p: pd.DataFrame, live_release: pd.Series) -> pd.DataFrame:
    """adaptive/columns.release_table, extended to rows the availability table does not hold (the live-only rows): their
    release under each scenario by its own rule (latency/availability.py: the weekly Monday for B and E, lf + 2 for D,
    lf + 1 + k for L<k>), but never before the day the live feed collected them (its release), so a row collected late
    cannot reach a match played before it was collected. A live-only Slam row is refused (its rule needs the event)."""
    from src.eda.serve_speed_tabpfn.adaptive import columns as CO
    from src.eda.serve_speed_tabpfn.latency import availability as AV
    from src.eda.serve_speed_tabpfn.latency import features_latency as FL
    have = CO._avail_columns()
    want = [f"release_{s}" for s in CO.SCENARIOS if f"release_{s}" in have]
    a = pd.read_parquet(FL.AVAIL, columns=["match_id", "side", "lf"] + want).astype({"match_id": str, "side": str})
    m = p[["match_id", "side"]].astype(str).merge(a, on=["match_id", "side"], how="left", validate="one_to_one")
    live = live_release.reindex(_key(p)).to_numpy(dtype="float64")
    live_only = ~np.isnan(live)                # the availability table may list their matches, on an older clock
    found = m[want[0]].notna().to_numpy() & ~live_only
    lf = p["lf"].to_numpy(np.int64)
    if (live_only & p["level"].eq("GS").to_numpy()).any():
        raise SystemExit("a live-only speed row at a Slam: its release rule needs the event's last day")
    if (~found & ~live_only).any():
        raise SystemExit("a history speed row the availability table does not hold")
    floor = np.nan_to_num(live, nan=-1).astype(np.int64)
    rules = {"A": lf + 1, "B": AV.weekly_release(lf), "D": lf + AV.DAILY_LAG, "E": AV.weekly_release(lf),
             **{f"L{k}": lf + 1 + k for k in AV.LAGS}}
    r = pd.DataFrame(index=p.index)
    for c in want:
        s = c.replace("release_", "")
        new = rules[s] if s == "A" else np.maximum(rules[s], floor)
        r[s] = np.where(found, m[c].to_numpy(dtype="float64"), new).astype(np.int64)
    assert (m.loc[found, "lf"].to_numpy(np.int64) == lf[found]).all()
    assert (r["A"].to_numpy() == lf + 1).all()
    return r


def build(keys: pd.DataFrame, live: bool = True, repaired: bool = True) -> tuple[pd.DataFrame, dict]:
    """spd_L_B and spd_L_D on the given keys: the decided builder on the speed history (build_on's patch), with the
    live feed's later rows when live."""
    from src.eda.serve_speed_tabpfn import features as F
    from src.eda.serve_speed_tabpfn import panel as P
    from src.eda.serve_speed_tabpfn.adaptive import columns as CO
    from src.eda.serve_speed_tabpfn.latency import features_latency as FL
    hist, live_rel = history(live, repaired)
    frozen_load = P.load_panel
    P.load_panel = lambda use_only=True: (hist[hist["use"].astype(bool)].reset_index(drop=True)
                                          if use_only else hist)
    try:
        p = FL.load_panel()
        rt = release_table(p, live_rel) if live else CO.release_table(p)
        t = F.side_targets(keys)
        tm = t[t["tour"].eq("atp")].reset_index(drop=True)
        out = keys[["match_id"]].copy()
        for s in SCEN:
            cols = CO.build_scenario(p, keys, tm, rt, s)["cols"]
            out[f"spd_L_{s}"] = cols[f"spd_L_{s}"].to_numpy()
    finally:
        P.load_panel = frozen_load
    info = {"history_rows": int(len(hist)), "live_only_rows": int(len(live_rel)),
            "live_only_obs_last": TR.day_text(int(hist["obs"].max())) if len(hist) else None}
    return out, info


def run(instance: Path, season: int, stage0: Path = STAGE0, timing: Path = TR.TIMING,
        out_dir: Path | None = None) -> dict:
    t0 = time.time()
    from src.eda.serve_speed_tabpfn import panel as P
    keys = instance_keys(instance, season, stage0, timing)
    hist_path, column = decided()
    col = pd.read_parquet(column, columns=["match_id", "spd_L_B", "spd_L_D"])
    col["match_id"] = col["match_id"].astype(str)
    col = col.set_index("match_id")
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    got, hist_info = build(keys, repaired=hist_path == LP.REPAIRED)     # the column's own history
    got = got.set_index("match_id")
    have = keys["match_id"][keys["match_id"].isin(col.index)].to_numpy()
    lack = keys["match_id"][~keys["match_id"].isin(col.index)].to_numpy()
    # the check: the builder on the instance's own targets against the decided column, where the column holds a match
    old = P.load_frame_keys().astype({"match_id": str}).set_index("match_id")
    same_keys = pd.Series(False, index=pd.Index(have))
    kk = keys.set_index("match_id").loc[have]
    in_old = old.index.intersection(have)
    o = old.loc[in_old]
    same_keys.loc[in_old] = ((o["player_a_id"] == kk.loc[in_old, "player_a_id"])
                             & (o["player_b_id"] == kk.loc[in_old, "player_b_id"])
                             & (o["es"] == kk.loc[in_old, "es"]) & (o["lf"] == kk.loc[in_old, "lf"])
                             & (o["obs"] == kk.loc[in_old, "obs"]) & (o["tdate"] == kk.loc[in_old, "tdate"])
                             & (o["round_order"] == kk.loc[in_old, "round_order"])).to_numpy()
    check = {}
    for s in SCEN:
        d = np.abs(got.loc[have, f"spd_L_{s}"].to_numpy(float) - col.loc[have, f"spd_L_{s}"].to_numpy(float))
        eq = d <= TOL
        check[s] = {"overlap": int(len(have)), "equal": int(eq.sum()), "max_abs_diff": float(d.max()) if len(d) else 0.0,
                    "differ_with_same_targets": int((~eq & same_keys.to_numpy()).sum()),
                    "differ_with_changed_targets": int((~eq & ~same_keys.to_numpy()).sum()),
                    "examples_unexplained": [str(x) for x in np.asarray(have)[~eq & same_keys.to_numpy()][:5]]}
    ok = all(c["differ_with_same_targets"] == 0 for c in check.values())
    # every frame match of 2019 .. season: the column's values kept, the builder's where the column lacks a match
    f = pd.read_parquet(instance / "model_frame.parquet", columns=["match_id", "tour", "season"])
    f["match_id"] = f["match_id"].astype(str)
    f = f[f["season"].between(2019, season)]
    out = pd.DataFrame({"match_id": f["match_id"].to_numpy()})
    for s in SCEN:
        out[f"spd_L_{s}"] = col[f"spd_L_{s}"].reindex(out["match_id"]).to_numpy(float)
    out["source"] = np.where(out["spd_L_B"].notna(), "column", "")
    ext = out["match_id"].isin(lack).to_numpy()
    for s in SCEN:
        out.loc[ext, f"spd_L_{s}"] = got.loc[out.loc[ext, "match_id"], f"spd_L_{s}"].to_numpy(float)
    out.loc[ext, "source"] = "extended"
    women = f["tour"].eq("wta").to_numpy()
    for s in SCEN:                                     # women's column is 0, as in the decided one
        out.loc[women & out[f"spd_L_{s}"].isna().to_numpy(), f"spd_L_{s}"] = 0.0
    out.loc[women & (out["source"] == ""), "source"] = "women (0)"
    missing = int(out[[f"spd_L_{s}" for s in SCEN]].isna().any(axis=1).sum())
    # the frozen history ends (the augmented panel: latest observation 3 Oct 2026, latest finish 7 Oct); a match that
    # starts after its last finish reads the live panel's later rows (the daily collector's, a backfill), released no
    # earlier than the live feed collected them (release_table)
    h = pd.read_parquet(hist_path, columns=["lf", "use", "tour"])
    last_lf = int(h.loc[h["use"].astype(bool) & h["tour"].eq("atp"), "lf"].max())
    beyond = keys.loc[keys["match_id"].isin(lack) & (keys["es"] > last_lf + 1), "match_id"]
    rec = {"instance": instance.name, "season": season, "column": str(column), "column_sha256": TR.sha256_file(column),
           "history": str(hist_path), "history_sha256": TR.sha256_file(hist_path),
           "frame_sha256": TR.sha256_file(instance / "model_frame.parquet"), "stage0": str(stage0),
           "timing": str(timing), "season_men": int(len(keys)), "in_column": int(len(have)), "extended": int(len(lack)),
           "check": check, "check_passed": ok, "rows": int(len(out)), "missing_after": missing,
           "history_last_finish": TR.day_text(last_lf), "extended_beyond_history": int(len(beyond)),
           "live_history": hist_info,
           "beyond_note": "matches starting after the frozen history's last finish read the live panel's later rows "
                          "(the daily collector's from 8 Oct 2026, and any backfill), each released by its scenario's "
                          "rule but never before the day the live feed collected it",
           "rule": "the column's value where it holds the match; the builder's for the others (same history, release "
                   "days, constants); the check: on the overlap, every difference must come from changed targets",
           "seconds": round(time.time() - t0, 1)}
    out_dir = Path(out_dir) if out_dir else instance
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_dir / f"{OUT_NAME}.parquet", index=False)
    (out_dir / f"{OUT_NAME}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--stage0", default=str(STAGE0), help="the Stage 0 the instance was built from (its tree's)")
    ap.add_argument("--timing", default=str(TR.TIMING), help="the match clock the instance was built from")
    ap.add_argument("--out", help="another folder for the two files (a test; default the instance)")
    a = ap.parse_args()
    inst = Path(a.instance) if Path(a.instance).is_absolute() else ROOT / a.instance
    rec = run(inst, a.season, Path(a.stage0), Path(a.timing), Path(a.out) if a.out else None)
    print(json.dumps(rec, indent=1))
    return 0 if rec["check_passed"] and rec["missing_after"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
