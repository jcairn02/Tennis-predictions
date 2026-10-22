"""Are the source reconciliation's repairs of 22 Oct 2026 in a Stage 0, and in an instance's stage-2 speed table?
(docs/decisions/2026-10-22-source-reconciliation-repairs.md; the register of revisions pending at the next retrain,
data/studies/current_best_model/pending_at_retrain.json, names this check.)

    --stage0 <folder>     the folder holding stage0_matches.parquet and stage0_match_players.parquet:
        SRS1   each match's two service-game counts are the point record's (box/slam_svgms_candidates.csv)
        SRO1   each match's counts are the tour's box (the decided row_corrections.csv); service games compared where
               Stage 0 keeps them
        SRRET  each match is retired
        SRLVL  every match of each named event at the corrected level (event_corrections.csv)
        SRSRF  every match of each named event on the corrected surface
    --instance <folder>   also: its own stage-2 speed table (stage2_speed_columns.json, written by a retrain's
                          in_season_retrain/speed_extend.py) was built from the repaired speed history and column
                          (live_panel.REPAIRED and COLUMN_REPAIRED, by SHA-256). An instance without that table fails:
                          only a retrain's instance carries the repair into stage 2
    --write <json>        the result, as JSON
Exit 0 when every check passes, 1 otherwise. Reads no match result.
    ./python.sh src/eda/source_reconciliation/verify_applied.py --stage0 data/studies/predictability_diagnostic
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.input_data_audit import corrections as COR  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

FIXES = {"SRS1", "SRO1", "SRRET", "SRLVL", "SRSRF"}
SACK = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon", "second_won": "2ndWon",
        "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}


def check_stage0(folder: Path, fixes: Path = COR.FIXES) -> dict:
    folder = Path(folder)
    m = pd.read_parquet(folder / "stage0_matches.parquet",
                        columns=["match_id", "tour", "tournament_id", "level", "surface", "status"])
    p = pd.read_parquet(folder / "stage0_match_players.parquet", columns=["match_id", "won"] + list(SACK))
    rc = pd.read_csv(Path(fixes) / COR.ROW_CORRECTIONS.name, dtype=str, keep_default_na=False)
    rc = rc[rc["fix"].isin(FIXES)]
    ev = pd.read_csv(Path(fixes) / COR.EVENT_CORRECTIONS.name, dtype=str, keep_default_na=False) \
        if (Path(fixes) / COR.EVENT_CORRECTIONS.name).exists() else pd.DataFrame(columns=["fix"])
    out: dict = {"stage0": str(folder), "fixes": str(fixes)}
    w = p[p["won"].astype(bool)].set_index("match_id")
    l = p[~p["won"].astype(bool)].set_index("match_id")
    mm = m.set_index("match_id")

    def tally(name: str, ids, ok) -> None:
        ids = list(ids)
        ok = np.asarray(ok, dtype=bool)
        out[name] = {"named": len(ids), "in_stage0": int(len(ids)), "ok": int(ok.sum()),
                     "failing": [i for i, g in zip(ids, ok) if not g][:5]}

    s1 = pd.read_csv(C.OUT / "box" / "slam_svgms_candidates.csv", dtype=str)
    want = set(rc.loc[rc["fix"].eq("SRS1"), "match_id"])
    s1 = s1[s1["match_id"].isin(want)]
    have = s1["match_id"].isin(w.index) & s1["match_id"].isin(l.index)
    ok = have.to_numpy().copy()
    ids = s1.loc[have, "match_id"]
    ok[have.to_numpy()] = ((w.loc[ids, "sv_gms"].to_numpy() == s1.loc[have, "x_recount_w_svgms"].astype(float).to_numpy())
                           & (l.loc[ids, "sv_gms"].to_numpy() == s1.loc[have, "x_recount_l_svgms"].astype(float).to_numpy()))
    tally("SRS1", s1["match_id"], ok)
    if len(want) != len(s1):
        out["SRS1"]["ok"] = -1                      # a decided row without its study row: rebuild the check
    o1 = rc[rc["fix"].eq("SRO1")]
    ok = []
    for r in o1.itertuples():
        d = r._asdict()
        if r.match_id not in w.index or r.match_id not in l.index:
            ok.append(False)
            continue
        good = True
        for c, s in SACK.items():
            for side, frame in (("w", w), ("l", l)):
                v = frame.loc[r.match_id, c]
                if c == "sv_gms" and pd.isna(v):
                    continue
                good &= bool(v == float(d[f"{side}_{s}"]))
        ok.append(good)
    tally("SRO1", o1["match_id"], ok)
    st = rc[rc["fix"].eq("SRRET")]
    tally("SRRET", st["match_id"], [i in mm.index and mm.loc[i, "status"] == "retired" for i in st["match_id"]])
    for fix, field in (("SRLVL", "level"), ("SRSRF", "surface")):
        e = ev[ev["fix"].eq(fix)]
        good = []
        for r in e.itertuples():
            x = m[m["tour"].eq(r.tour) & m["tournament_id"].eq(r.tournament_id)]
            good.append(len(x) > 0 and set(x[field].astype(str)) == {r.value})
        tally(fix, e["tour"] + "|" + e["tournament_id"], good)
    named = [k for k in ("SRS1", "SRO1", "SRRET", "SRLVL", "SRSRF")]
    out["ok"] = all(out[k]["named"] > 0 and out[k]["ok"] == out[k]["named"] for k in named)
    return out


def check_instance(instance: Path) -> dict:
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    rec_path = Path(instance) / "stage2_speed_columns.json"
    out: dict = {"instance": str(instance), "record": str(rec_path)}
    if not rec_path.exists():
        out.update(ok=False, why="no stage2_speed_columns.json: not a retrain's instance (stage 2 would read the "
                                 "daily engine's decided column)")
        return out
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    hist = json.loads(LP.REPAIRED_META.read_text(encoding="utf-8"))
    col = json.loads(LP.COLUMN_REPAIRED_META.read_text(encoding="utf-8"))
    out["column_is_repaired"] = rec.get("column_sha256") == col["column_sha256"]
    out["history_is_repaired"] = rec.get("history_sha256") == hist["repaired_sha256"]
    out["check_passed"] = bool(rec.get("check_passed"))
    out["ok"] = out["column_is_repaired"] and out["history_is_repaired"] and out["check_passed"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0", required=True, help="the folder holding the Stage 0 tables")
    ap.add_argument("--fixes", default=None, help="the decided correction tables the Stage 0 was built with (default: "
                                                  "its own tree's, data/studies/input_data_audit/fixes beside it, "
                                                  "else the repository's)")
    ap.add_argument("--instance", help="an instance folder: its stage-2 speed table too")
    ap.add_argument("--write", help="write the result here (JSON)")
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    stage0 = Path(a.stage0) if Path(a.stage0).is_absolute() else root / a.stage0
    own = stage0.parent / "input_data_audit" / "fixes"           # a build tree's own copy (a retrain's sandbox)
    fixes = Path(a.fixes) if a.fixes else (own if (own / COR.ROW_CORRECTIONS.name).exists() else COR.FIXES)
    res = {"stage0": check_stage0(stage0, fixes)}
    if a.instance:
        res["instance"] = check_instance(Path(a.instance) if Path(a.instance).is_absolute() else root / a.instance)
    res["ok"] = res["stage0"]["ok"] and res.get("instance", {"ok": True})["ok"]
    res["checked_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    if a.write:
        C.write_json(Path(a.write), res)
    print(json.dumps(res, indent=1, default=str))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
