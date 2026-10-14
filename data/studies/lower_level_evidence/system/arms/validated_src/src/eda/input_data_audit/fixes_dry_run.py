"""Dry run of the audit's corrections (docs/decisions/2026-10-08-corrupt-data-fixes.md), away from the live tables.

Builds Stage 0 twice into a scratch folder, each in its own process: without the corrections (the baseline:
--no-corrections; the decided Slam overrides apply as always) and with them. Then:
    baseline against live        the build reproduces today's live tables (no code or data drift)
    corrections against baseline only the corrected matches may change, and each changes as its table says: serve
                                 points + double faults (F1), the nine counts exchanged (F2), blanked (F3, F4) or
                                 replaced from the WTA's statistics (F3), ages set (F8b, F9), ids mapped (F7)
    detectors                    on the corrected rows the definition test and the exchanged-box fit no longer fire
The live tables' SHA-256 is checked before and after: they must not change. With --odds, Stage 1 is also built from
the live Stage 0 into the scratch folder, with and without the odds corrections, and compared row by row.

Writes data/studies/input_data_audit/fixes/dry_run.json.
Run: ./python.sh src/eda/input_data_audit/fixes_dry_run.py --scratch <folder outside the live Stage 0 folder> [--odds]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.input_data_audit import common as C  # noqa: E402
from src.eda.input_data_audit import corrections as K  # noqa: E402

LIVE = ROOT / "data" / "studies" / "predictability_diagnostic"
LIVE_FILES = [LIVE / "stage0_matches.parquet", LIVE / "stage0_match_players.parquet", LIVE / "stage1_odds.parquet"]
BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args: list[str]) -> float:
    t0 = time.time()
    print("-->", " ".join(args), flush=True)
    if subprocess.run([sys.executable, *args], cwd=ROOT).returncode != 0:
        raise SystemExit(f"failed: {' '.join(args)}")
    return round(time.time() - t0, 1)


def frames(folder: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_parquet(folder / "stage0_matches.parquet"), pd.read_parquet(folder / "stage0_match_players.parquet")


def changed(a: pd.DataFrame, b: pd.DataFrame, keys: list[str]) -> tuple[pd.DataFrame, dict]:
    """Rows present in both whose values differ (NaN equals NaN), and how many rows each column changes."""
    cols = [c for c in a.columns if c in b.columns and c not in keys]
    j = a.merge(b, on=keys, suffixes=("_a", "_b"))
    diff = pd.DataFrame({c: ~((j[f"{c}_a"] == j[f"{c}_b"]) | (j[f"{c}_a"].isna() & j[f"{c}_b"].isna()))
                         for c in cols})
    return j[diff.any(axis=1)], diff.sum().loc[lambda s: s > 0].astype(int).to_dict()


def expected(rows: pd.DataFrame, m0: pd.DataFrame) -> pd.DataFrame:
    """The Stage 0 match of each row correction, with its fix and action."""
    key = m0[["match_id", "source_file", "source_row"]].astype({"source_row": "int64"})
    r = rows.rename(columns={"match_id": "table_match_id"})
    r = r.assign(source_row=pd.to_numeric(r["source_row"]).astype("int64"))
    r = r.merge(key, on=["source_file", "source_row"], how="left")
    r["match_id_agrees"] = r["match_id"].eq(r["table_match_id"])
    return r


def check_rows(rows: pd.DataFrame, pb: pd.DataFrame, pc: pd.DataFrame, mb: pd.DataFrame, mc: pd.DataFrame) -> dict:
    """Each corrected match against its baseline: the change its action says, and nothing else."""
    out = {}
    b = pb.set_index(["match_id", "player_id"])
    c = pc.set_index(["match_id", "player_id"])
    for (fix, action), g in rows.groupby(["fix", "action"]):
        ids = g["match_id"].dropna().unique()
        ok, bad = 0, []
        for mid in ids:
            bm, cm = b.loc[mid], c.loc[mid]
            if action == "add_df_to_svpt" and bm["svpt"].isna().all():     # a box Stage 0 dropped before the fix
                good = cm[BOX].notna().all().all() and bool(mc.set_index("match_id").loc[mid, "has_box"])
            elif action == "add_df_to_svpt":
                good = (cm["svpt"] == bm["svpt"] + bm["df"]).all() and \
                    cm[[x for x in BOX if x != "svpt"]].equals(bm[[x for x in BOX if x != "svpt"]])
            elif action == "exchange_svgms":
                good = np.allclose(cm["sv_gms"].to_numpy(dtype=float), bm["sv_gms"].to_numpy(dtype=float)[::-1]) and \
                    cm[[x for x in BOX if x != "sv_gms"]].equals(bm[[x for x in BOX if x != "sv_gms"]])
            elif action == "exchange_box":
                good = np.allclose(cm[BOX].to_numpy(dtype=float), bm[BOX].to_numpy(dtype=float)[::-1], equal_nan=True)
            elif action == "blank_box":
                good = cm[BOX].isna().all().all() and not bool(mc.set_index("match_id").loc[mid, "has_box"])
            elif action == "replace_box":
                good = cm[BOX].notna().all().all() and bool(mc.set_index("match_id").loc[mid, "has_box"])
            else:                                  # set_age
                want = g[g["match_id"].eq(mid)]
                good = True
                for w in want.itertuples():
                    name = w.winner_name if w.side == "winner" else w.loser_name
                    who = cm[cm["player_name"].map(C.name_key) == C.name_key(name)]
                    good &= len(who) == 1 and abs(float(who["age"].iloc[0]) - float(w.value)) < 1e-6
            ok += bool(good)
            if not good:
                bad.append(mid)
        out[f"{fix}|{action}"] = {"matches": int(len(ids)), "as_expected": ok, "not_as_expected": bad[:20],
                                  "unresolved_rows": int(g["match_id"].isna().sum())}
    return out


def detectors(pc: pd.DataFrame, mc: pd.DataFrame, rows: pd.DataFrame) -> dict:
    """The audit's detectors on the corrected matches: definition test (F1) and exchanged-box fit (F2)."""
    pl = pc.merge(mc[["match_id", "status"]], on="match_id")
    opp = pl[["match_id", "player_id"] + BOX].rename(columns={"player_id": "opponent_id", **{b: f"o_{b}" for b in BOX}})
    pl = pl.merge(opp, on=["match_id", "opponent_id"])
    res = {}
    f1 = pl[pl["match_id"].isin(rows.loc[rows["action"].eq("add_df_to_svpt"), "match_id"])]
    res["F1_definition_test_failures_after"] = int(C.serve_points_exclude_dfs(f1).sum())
    f2 = pl[pl["match_id"].isin(rows.loc[rows["action"].isin(["exchange_box", "exchange_svgms"]), "match_id"])]
    if len(f2):
        flags = C.identity_flags(f2)
        res["F2_swapped_fit_after"] = int(flags["swapped_box_fits"].sum())
        res["F2_identity_fails_after"] = int(flags["games_identity_fails"].sum())
        res["F2_winner_fewer_points_after"] = int((flags["winner_fewer_points"] & f2["won"]).sum())
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--odds", action="store_true", help="also build Stage 1 with and without the odds corrections")
    ap.add_argument("--reuse", action="store_true", help="compare the builds already in the scratch folder")
    a = ap.parse_args()
    scratch = Path(a.scratch).resolve()
    if scratch == LIVE.resolve() or LIVE.resolve() in scratch.parents:
        raise SystemExit("the scratch folder must be outside the live Stage 0 folder")
    before = {p.name: sha(p) for p in LIVE_FILES}
    base, corr = scratch / "baseline", scratch / "corrected"
    seconds = {}
    if not a.reuse:
        seconds = {"baseline": run(["src/eda/predictability_diagnostic/stage0_build.py", "--out-dir", str(base),
                                    "--no-corrections"]),
                   "corrected": run(["src/eda/predictability_diagnostic/stage0_build.py", "--out-dir", str(corr)])}
    if a.odds and not a.reuse:
        seconds["odds_baseline"] = run(["src/eda/predictability_diagnostic/stage1_odds.py", "--out-dir",
                                        str(scratch / "odds_baseline"), "--no-corrections"])
        seconds["odds_corrected"] = run(["src/eda/predictability_diagnostic/stage1_odds.py", "--out-dir",
                                         str(scratch / "odds_corrected")])
    after = {p.name: sha(p) for p in LIVE_FILES}

    ml, pl = frames(LIVE)
    mb, pb = frames(base)
    mc, pc = frames(corr)
    _, drift_m = changed(ml, mb, ["match_id"])
    _, drift_p = changed(pl, pb, ["match_id", "player_id"])
    rows = expected(pd.read_csv(K.ROW_CORRECTIONS, dtype=str, keep_default_na=False), mb)
    aliases = pd.read_csv(K.ID_ALIASES, dtype=str, keep_default_na=False)
    alias_matches = set(pb.loc[pb["player_id"].isin(aliases["from_id"]), "match_id"])
    m_rows, m_cols = changed(mb, mc, ["match_id"])
    side_key = ["match_id", "side"]
    p_rows, p_cols = changed(pb, pc, side_key)
    touched = set(m_rows["match_id"]) | set(p_rows["match_id"])
    targets = set(rows["match_id"].dropna()) | alias_matches
    result = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "build_seconds": seconds,
        "live_tables_unchanged": before == after, "live_sha256": after,
        "baseline_equals_live": {"same_match_ids": set(ml["match_id"]) == set(mb["match_id"]),
                                 "match_columns_changed": drift_m, "player_columns_changed": drift_p},
        "same_match_ids_after_corrections": set(mb["match_id"]) == set(mc["match_id"]),
        "row_corrections": int(len(rows)), "row_corrections_unresolved": int(rows["match_id"].isna().sum()),
        "row_corrections_other_match_id": rows.loc[~rows["match_id_agrees"], ["table_match_id", "match_id"]]
        .head(20).to_dict("records"),
        "target_matches": len(targets), "matches_changed": len(touched),
        "match_columns_changed": m_cols, "player_columns_changed": p_cols,
        "changed_outside_targets": sorted(touched - targets)[:50],
        "changed_outside_targets_count": len(touched - targets),
        "targets_unchanged": sorted(targets - touched)[:50], "targets_unchanged_count": len(targets - touched),
        "per_fix": check_rows(rows, pb.merge(pc[side_key + ["player_id"]].rename(columns={"player_id": "pid_c"}),
                                             on=side_key).assign(player_id=lambda d: d["pid_c"]).drop(columns="pid_c"),
                              pc, mb, mc),
        "aliases": {"pairs": int(len(aliases)),
                    "second_ids_left_after": int(pc["player_id"].isin(aliases["from_id"]).sum()),
                    "matches": len(alias_matches)},
        "detectors_after": detectors(pc, mc, rows),
    }
    if a.odds:
        ob = pd.read_parquet(scratch / "odds_baseline" / "stage1_odds.parquet")
        oc = pd.read_parquet(scratch / "odds_corrected" / "stage1_odds.parquet")
        o_rows, o_cols = changed(ob, oc, ["match_id"])
        want = pd.read_csv(K.ODDS_CORRECTIONS, dtype=str, keep_default_na=False)
        result["odds"] = {"rows_changed": int(len(o_rows)), "columns_changed": o_cols,
                          "changed_outside_table": sorted(set(o_rows["match_id"]) - set(want["match_id"])),
                          "table_rows_unchanged": sorted(set(want["match_id"]) - set(o_rows["match_id"])),
                          "baseline_equals_live": changed(pd.read_parquet(LIVE / "stage1_odds.parquet"), ob,
                                                          ["match_id"])[1]}
    ok = (result["live_tables_unchanged"] and result["same_match_ids_after_corrections"]
          and not result["changed_outside_targets_count"] and not result["row_corrections_unresolved"]
          and all(not v["not_as_expected"] for v in result["per_fix"].values())
          and result["aliases"]["second_ids_left_after"] == 0)
    if a.odds:
        ok &= not result["odds"]["changed_outside_table"] and not result["odds"]["table_rows_unchanged"]
    result["pass"] = bool(ok)
    (K.FIXES / "dry_run.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("live_tables_unchanged", "same_match_ids_after_corrections",
                                             "matches_changed", "changed_outside_targets_count",
                                             "targets_unchanged_count", "pass")}, default=str))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
