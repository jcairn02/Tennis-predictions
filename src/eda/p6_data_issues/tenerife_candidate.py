"""The harm check's candidate for the Tenerife date correction (owner, 14 Oct 2026; docs/decisions/2026-10-14-p6-data-issues.md,
point 1): the frozen reference's tables with the 31 dates changed, and nothing else.

Why from the frozen reference's own tables. compare.py reads a candidate against the frozen reference of 8 Oct 2026.
The live tables have moved on since (Tennis My Life's own revisions, the Roland Garros repair, new matches); a candidate
rebuilt from today's sources would differ in all of those. Here the sandbox (run_chain.py --setup --candidate, in its
own MODEL_REBUILD_SANDBOX) takes the reference's frozen tables, and only the 31 matches change, as the Stage 0 build
would change them with the date correction (D1 in data/studies/input_data_audit/fixes/date_corrections.csv):
    Stage 0      tournament_date 2024-01-21 -> 2024-02-26 for the 31 rows of 2024-2847; then the build's own chronological
                 sort (predictability_diagnostic.common.chrono_sort) and its order numbers, and the players' rows in that
                 order, as stage0_build does
    timeline     the frozen timeline (tables_later: the only copy, which differs from the build's in no model input; the
                 reference's README) with the 31 windows moved by the anchor's shift. Their windows are rule windows
                 (no exact day), offsets from the anchor day that do not depend on the date (match_timing.timing's
                 anchor_day, rule_label, rule_windows): checked here, as the reviewers did, by recomputing them. Not
                 re-linked from today's source folders, which would bring the timeline's own later changes
    Stage 1's odds and every other frozen table: the reference's, unchanged
Then, from run_chain: lane 0's last step (the leak-proof features, match_timing/rebuild.py), lanes 1 and 2, the
reference's build of the base frame without the women's indoor fill (build_frame.py --indoor-men-only, then the
leak-proof frame and the Elo frames: the 9 Oct fill came after the freeze), lane 3, --collect; the fits (seeds 0-3,
seasons 2019-2024, the reference's 58 inputs); compare.py --candidate.

Writes <out>/candidate_prep.json: what was copied and changed, with SHA-256, and the checks (the patched tables equal the
reference's everywhere but the 31 matches; every new window holds the match's play day).

Run (after run_chain.py --setup --candidate with the same MODEL_REBUILD_SANDBOX):
    MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_sb_tenerife ./python.sh src/eda/p6_data_issues/tenerife_candidate.py \
        --out data/studies/current_best_model/2026-10-14_tenerife_dates
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.match_timing import timing as TM  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

SANDBOX = Path(os.environ.get("MODEL_REBUILD_SANDBOX", ""))
FROZEN = ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen"
CONSENSUS = ROOT / "data" / "studies" / "p6_data_issues" / "stage0_review" / "consensus.json"
PLAY_DAYS = ROOT / "data" / "studies" / "p6_data_issues" / "tml_misdates" / "stage0_date_corrections.csv"
OLD, NEW = pd.Timestamp("2024-01-21"), pd.Timestamp("2024-02-26")
S0 = Path("data") / "studies" / "predictability_diagnostic"
MT = Path("data") / "studies" / "match_timing"
EPOCH = pd.Timestamp("1970-01-01")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore_frozen(sb: Path) -> list[dict]:
    """The reference's frozen tables (tables/, then tables_later/) over the sandbox's copies of the live ones."""
    done = []
    for part in ("tables", "tables_later"):
        base = FROZEN / part
        for src in sorted(p for p in base.rglob("*") if p.is_file()):
            rel = src.relative_to(base)
            dst = sb / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                os.chmod(dst, stat.S_IREAD | stat.S_IWRITE)
            shutil.copy2(src, dst)
            os.chmod(dst, stat.S_IREAD | stat.S_IWRITE)       # the frozen copies are read-only; the sandbox's need not be
            done.append({"file": rel.as_posix(), "from": part, "sha256": sha(dst)})
    return done


def patch_stage0(sb: Path, ids: list[str]) -> dict:
    mpath, ppath = sb / S0 / "stage0_matches.parquet", sb / S0 / "stage0_match_players.parquet"
    m, mp = pd.read_parquet(mpath), pd.read_parquet(ppath)
    ref = m.copy()
    hit = m["match_id"].isin(ids)
    if int(hit.sum()) != len(ids) or not (m.loc[hit, "tournament_date"] == OLD).all():
        raise SystemExit(f"Stage 0: {int(hit.sum())} of {len(ids)} rows found, or not all dated {OLD.date()}")
    m.loc[hit, "tournament_date"] = NEW
    m = C.chrono_sort(m.drop(columns="order")).reset_index(drop=True)
    m["order"] = np.arange(len(m), dtype="int64")
    mp = mp.merge(m[["match_id", "order"]], on="match_id").sort_values(["order", "side"]).drop(columns="order")
    # the check: every column but the date (31 rows) and the order numbers equal the reference's, match by match
    a = m.set_index("match_id").sort_index()
    b = ref.set_index("match_id").sort_index()
    other = [c for c in a.columns if c not in ("order", "tournament_date")]
    same_other = bool(a[other].equals(b[other]))
    changed_dates = int((a["tournament_date"] != b["tournament_date"]).sum())
    moved = int((a["order"] != b["order"]).sum())
    mp_same = bool(mp.sort_values(["match_id", "side"]).reset_index(drop=True).equals(
        pd.read_parquet(ppath).sort_values(["match_id", "side"]).reset_index(drop=True)))
    if not same_other or changed_dates != len(ids) or not mp_same:
        raise SystemExit(f"Stage 0 patch check failed: other columns equal {same_other}, dates changed "
                         f"{changed_dates}, player rows equal {mp_same}")
    m.to_parquet(mpath, index=False)
    mp.reset_index(drop=True).to_parquet(ppath, index=False)
    return {"dates_changed": changed_dates, "rows_reordered": moved, "other_columns_equal": same_other,
            "player_rows_equal_but_order": mp_same, "matches": int(len(m)),
            "sha256": {"stage0_matches.parquet": sha(mpath), "stage0_match_players.parquet": sha(ppath)}}


def patch_timeline(sb: Path, ids: list[str]) -> dict:
    tpath = sb / MT / "timing.parquet"
    t = pd.read_parquet(tpath)
    hit = t["match_id"].isin(ids)
    rows = t[hit].copy()
    if len(rows) != len(ids) or rows["exact"].astype(bool).any():
        raise SystemExit(f"timeline: {len(rows)} of {len(ids)} rows, or some with an exact day")
    old_m, new_m = rows.copy(), rows.copy()
    new_m["tournament_date"] = NEW
    a_old, a_new = TM.anchor_day(old_m), TM.anchor_day(new_m)
    shift = np.unique(np.asarray(a_new) - np.asarray(a_old))
    lab_same = bool((TM.rule_label(old_m).to_numpy() == TM.rule_label(new_m).to_numpy()).all())
    if len(shift) != 1 or not lab_same:
        raise SystemExit(f"timeline: the anchor moves by {shift} days, rule labels unchanged {lab_same}")
    d = float(shift[0])
    if not np.allclose(np.asarray(a_old, dtype=float), rows["anchor"].to_numpy(dtype=float)):
        raise SystemExit("timeline: the stored anchor is not the clock's anchor_day of the stored date")
    t.loc[hit, "tournament_date"] = NEW
    t.loc[hit, "start"] = float((NEW - EPOCH).days)
    for c in ("anchor", "es", "lf", "obs"):
        t.loc[hit, c] = t.loc[hit, c] + d
    pd_days = pd.read_csv(PLAY_DAYS)
    pd_days = pd_days[pd_days["stage0_match_id"].isin(ids)]
    play = dict(zip(pd_days["stage0_match_id"], (pd.to_datetime(pd_days["played_from"]) - EPOCH).dt.days))
    new = t[hit]
    holds = [(r.es <= play[r.match_id] <= r.lf) for r in new.itertuples() if r.match_id in play]
    t.to_parquet(tpath, index=False)
    return {"anchor_shift_days": d, "rule_labels_unchanged": lab_same, "rows": int(hit.sum()),
            "windows_holding_the_play_day": int(sum(holds)), "with_a_play_day": len(holds),
            "new_windows": [str((EPOCH + pd.Timedelta(days=new["es"].min())).date()),
                            str((EPOCH + pd.Timedelta(days=new["lf"].max())).date())],
            "sha256": sha(tpath)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sb = SANDBOX
    if not str(sb) or not (sb / "src").exists():
        raise SystemExit("set MODEL_REBUILD_SANDBOX to the candidate's sandbox (made by run_chain.py --setup --candidate)")
    ids = json.loads(CONSENSUS.read_text(encoding="utf-8"))["G1"]["rows"]
    rec = {"sandbox": str(sb), "rows": ids, "restored": restore_frozen(sb)}
    rec["stage0"] = patch_stage0(sb, ids)
    rec["timeline"] = patch_timeline(sb, ids)
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidate_prep.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("stage0", "timeline")}, indent=1, default=str))
    ok = rec["timeline"]["windows_holding_the_play_day"] == rec["timeline"]["with_a_play_day"] == len(ids)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
