"""Source reconciliation, Part G (serve speed), step 1: every first-serve-speed record on disk, linked to the frozen
snapshot's (match_id, side). Reads no match result: Stage 0 is read with explicit context columns only.

Runs every reader of spd_readers.py (a reader's output is cached in speed/cache/<reader>.parquet; --fresh re-reads),
links each record (spd_readers.link_records), adds the snapshot's context and marks records that cannot belong to their
linked match:
    mislink_round   the source's own round differs from the linked match's (ManTennisData and the ATP host's files,
                    whose link table keeps the source round; the panel's own rule)
    mislink_level   a Slam-only source on a non-Slam match, or a tour-only source on a Slam match (the panel's rule)
    dup_conflict    two records of one source on one player-match, more than 0.5 km/h apart (both dropped); within
                    0.5 the first is kept and the other marked dup_copy
valid = no mark. Per-match rows go to speed/records.parquet (git-ignored); counts to speed/build_summary.json.

Run: ./python.sh src/eda/source_reconciliation/spd_build.py [--fresh]   (about 4 minutes with --fresh: the handoff)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import spd_readers as R  # noqa: E402

OUT = C.OUT / "speed"
CACHE = OUT / "cache"
RECORDS = OUT / "records.parquet"
S0_M = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id", "tournament_name",
        "tournament_date"]
S0_P = ["match_id", "side", "player_id", "player_name"]
SLAM_ONLY = {"mb_slams", "ks_rg", "ibm_pts", "ibm_stat", "sackmann_pts", "hawkeye_pts", "ao_mc"}
TOUR_ONLY = {"mb_atp", "ra_atp", "ks_atp", "ra_handoff", "ks_handoff", "ra_sirgenkii", "ks_sirgenkii", "ks_mantd"}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def read_all(fresh: bool) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    parts = []
    for name, fn in R.READERS.items():
        path = CACHE / f"{name}.parquet"
        if path.exists() and not fresh:
            a = pd.read_parquet(path)
        else:
            a = fn()
            a.to_parquet(path, index=False)
        log(f"  {name}: {len(a):,} records")
        parts.append(a)
    return pd.concat(parts, ignore_index=True)


def marks(r: pd.DataFrame) -> pd.Series:
    why = pd.Series("", index=r.index, dtype=object)
    rmis = r["round_src"].notna() & (r["round_src"].astype(str) != r["round"].astype(str))
    why[rmis] = "mislink_round"
    lvl = (r["src"].isin(SLAM_ONLY) & r["level"].ne("GS")) | (r["src"].isin(TOUR_ONLY) & r["level"].eq("GS"))
    why[(why == "") & lvl] = "mislink_level"
    # two records of one source on one player-match (after the checks above)
    val = np.where(r["kind"].eq("points"), r["s1"], r["v1"])
    r = r.assign(_v=val)
    ok = why.eq("")
    g = r[ok].groupby(["src", "match_id", "side"])["_v"]
    spread = (g.transform("max") - g.transform("min")).reindex(r.index)
    size = g.transform("size").reindex(r.index)
    why[ok & (size > 1) & (spread > 0.5)] = "dup_conflict"
    ok = why.eq("")
    dup = r[ok].duplicated(["src", "match_id", "side"], keep="first")
    why[dup[dup].index] = "dup_copy"
    return why


def summary(rec: pd.DataFrame, linked: pd.DataFrame) -> dict:
    by = []
    for src, g in rec.groupby("src", sort=False):
        l = linked[linked["src"].eq(src)]
        v = l[l["valid"]]
        timed = (v["n1"] >= 1) if g["kind"].iloc[0] == "points" else v["v1"].notna()
        by.append({"src": src, "kind": g["kind"].iloc[0], "sys": g["sys"].iloc[0], "records": int(len(g)),
                   "linked": int(len(l)), "linked_share": round(len(l) / max(len(g), 1), 4),
                   "orientation_by_names": int(l["side_names"].notna().sum()),
                   "names_agree_with_link": int((l["name_ok"] == 1).sum()),
                   "names_reversed_link": int((l["name_ok"] == 0).sum()),
                   "invalid": l.loc[~l["valid"], "invalid_reason"].value_counts().to_dict(),
                   "valid": int(len(v)), "valid_timed": int(timed.sum()),
                   "valid_timed_by_tour_year": {f"{t}|{y}": int(n) for (t, y), n in
                                                v[timed].groupby(["tour", "year_s0"]).size().items()}})
    return {"built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "reads_results": False,
            "stage0": "data/studies/source_reconciliation/_snapshot (manifest.json)", "by_source": by}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="re-run every reader (else the cached outputs)")
    a = ap.parse_args()
    log("readers")
    rec = read_all(a.fresh)
    log(f"{len(rec):,} records; links")
    s0m, s0p = C.stage0(S0_M, S0_P)
    tables = R.link_tables()
    linked = R.link_records(rec, tables, s0p)
    linked = linked.merge(s0m.rename(columns={"year": "year_s0"}), on="match_id", how="left", validate="many_to_one")
    linked = linked.merge(s0p[["match_id", "side", "player_id"]], on=["match_id", "side"], how="left",
                          validate="many_to_one")
    linked["invalid_reason"] = marks(linked)
    linked["valid"] = linked["invalid_reason"].eq("")
    OUT.mkdir(parents=True, exist_ok=True)
    linked.to_parquet(RECORDS, index=False)
    s = summary(rec, linked)
    C.write_json(OUT / "build_summary.json", s)
    for b in s["by_source"]:
        log(f"  {b['src']:13s} records {b['records']:6d} linked {b['linked']:6d} valid timed {b['valid_timed']:6d} "
            f"names agree {b['names_agree_with_link']} reversed {b['names_reversed_link']} invalid {b['invalid']}")
    log(f"wrote {RECORDS.relative_to(ROOT)} ({len(linked):,} rows) and build_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
