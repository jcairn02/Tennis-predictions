"""The serve-speed history's repair the owner approved on 22 Oct 2026 (rule ks_within5;
docs/decisions/2026-10-22-source-reconciliation-repairs.md; the evidence: data/studies/source_reconciliation/speed/
REPORT.md and the README's § 6). --build reads no match result; --check reads results of 2019-2024 only, as the decided
comparison does.

    --build   the repaired history and stage 2's column on it, each with its record:
              history  live_panel.frozen_panel(repaired=False) (the corrected history plus the ATP backfill, the history
                       the live feed and stage 2 read until now) with the study's ks_within5 values
                       (speed/histories/ks_within5.parquet, spd_consensus.py): a published average more than 5 km/h off
                       the player-match's complete point record takes the point mean, on the row's own scale. Checked
                       first: the study's base (speed/histories/current.parquet) equals today's history exactly, and the
                       rule's copy differs from it in y alone.
                       -> data/studies/serve_speed_tabpfn/live/speed_panel_repaired.parquet and .json, which
                          live_panel.frozen_panel() reads from then on
              column   infosys_atp_backfill/columns.py's build_on on the repaired history (the 63,737 frame matches of the
                       decided column). Checked first: on today's history it reproduces the decided column
                       (speed_columns_augmented.parquet) exactly; after: the repaired column equals the study's
                       (speed/spdl/ks_within5.parquet) on every column both hold.
                       -> data/studies/source_reconciliation/applied/speed_columns_repaired.parquet and .json
                          (live_panel.COLUMN_REPAIRED: a retrain's own speed table keeps it, in_season_retrain/
                          speed_extend.py; the daily engine reads it for an instance without its own table)
              live     the 28-day form of every man in today's live panel, built on both histories with the same daily
                       rows (as infosys_atp_backfill/live_check.py): it must not move, every changed row being older than
                       the form's 364-day history
    --check   the harm check of the repair alone: stage 2 on the same forecasts (the live instance's seeds 0-3,
              walk-forward), the decided column against the repaired one, seasons 2020-2024, both tours (women read no
              speed), men, by season (current_best_model/compare.score; positive = the repaired column better; harm =
              worse by more than 0.10 mLL with the whole 95% interval below 0). The retrain's own harm check holds every
              arm on the frozen reference's speed column, so it cannot see this repair.
              -> data/studies/source_reconciliation/applied/speed_harm.csv and .json

    ./python.sh src/eda/source_reconciliation/apply_speed.py --build      (about 15 minutes)
    ./python.sh src/eda/source_reconciliation/apply_speed.py --check [--instance <folder>]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402

SPEED = C.OUT / "speed"
APPLIED = C.OUT / "applied"
DECISION = "docs/decisions/2026-10-22-source-reconciliation-repairs.md"
RULE = "ks_within5"
HARM_MLL = 0.10
THROUGH = 2024
STUDY_TOL = 1e-9          # the study's copy recomputed every y on the MatchBeats scale and back (spd_consensus.py)
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def history_pair() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Today's history (without the repair) and the repaired one, after the checks against the study's copies."""
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    base = LP.frozen_panel(repaired=False).reset_index(drop=True)
    cur = pd.read_parquet(SPEED / "histories" / "current.parquet").drop(columns=["consensus_rule"])
    # the study's base is today's history: every column exact, y to the study's round trip
    pd.testing.assert_frame_equal(cur.drop(columns=["y"]), base.drop(columns=["y"]), check_exact=True)
    if not np.allclose(cur["y"].to_numpy(float), base["y"].to_numpy(float), rtol=0, atol=STUDY_TOL, equal_nan=True):
        raise SystemExit("the study's base history is not today's (y)")
    ks = pd.read_parquet(SPEED / "histories" / f"{RULE}.parquet").drop(columns=["consensus_rule"])
    if list(ks.columns) != list(base.columns) or len(ks) != len(base):
        raise SystemExit(f"{RULE}: not the history's columns and rows")
    pd.testing.assert_frame_equal(ks.drop(columns=["y"]), base.drop(columns=["y"]), check_exact=True)
    changed = ((ks["y"] - base["y"]).abs() > STUDY_TOL).to_numpy()
    rep = base.copy()
    rep["y"] = np.where(changed, ks["y"].to_numpy(float), base["y"].to_numpy(float))    # unchanged rows keep theirs
    info = {"rows": int(len(rep)), "changed": int(changed.sum()),
            "changed_by_source": base.loc[changed, "source"].value_counts().to_dict(),
            "changed_by_year": {str(k): int(v) for k, v in base.loc[changed, "year"].value_counts().sort_index().items()},
            "change_kmh": {"median_abs": float((rep["y"] - base["y"])[changed].abs().median()),
                           "max_abs": float((rep["y"] - base["y"])[changed].abs().max())},
            "latest_changed_obs": None}
    if changed.any():
        from src.eda.serve_speed_tabpfn.live import common as LC
        info["latest_changed_obs"] = LC.date_of(int(base.loc[changed, "obs"].max()))
    rows = base.loc[changed, ["match_id", "side", "player_id", "year", "source", "basis"]].copy()
    rows["y_before"], rows["y_after"] = base.loc[changed, "y"].to_numpy(), rep.loc[changed, "y"].to_numpy()
    return base, rep, info | {"rows_changed": rows}


def live_form(history: pd.DataFrame, linked: pd.DataFrame, day: int) -> pd.DataFrame:
    """Today's form on a history (infosys_atp_backfill/live_check.py's live_form; the live folder is not written)."""
    from src.eda.serve_speed_tabpfn.live import form as FM
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    keep = LP.frozen_panel
    LP.frozen_panel = lambda repaired=True: history
    try:
        with tempfile.TemporaryDirectory() as tmp:
            live, _ = LP.build(linked, out=Path(tmp))
    finally:
        LP.frozen_panel = keep
    return FM.form_as_of(day, live)


def build() -> int:
    import hashlib
    from src.eda.infosys_atp_backfill import columns as IC
    from src.eda.serve_speed_tabpfn.live import common as LC
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    base, rep, info = history_pair()
    rows_changed = info.pop("rows_changed")
    log(f"history: {info['changed']} rows repaired of {info['rows']:,}")
    # the column first, on both histories: today's must reproduce the decided column exactly
    stored = pd.read_parquet(LP.COLUMN_BACKFILLED)
    old = IC.build_on(base)
    pd.testing.assert_frame_equal(old.reset_index(drop=True), stored[old.columns].reset_index(drop=True),
                                  check_dtype=False, check_exact=True)
    log("today's history reproduces the decided column exactly")
    new = IC.build_on(rep)
    study = pd.read_parquet(SPEED / "spdl" / f"{RULE}.parquet")
    both = [c for c in new.columns if c in study.columns and c != "match_id"]
    s = study.set_index("match_id").loc[new["match_id"]]
    for c in both:
        a, b = new[c].to_numpy(), s[c].to_numpy()
        if a.dtype.kind == "f" or b.dtype.kind == "f":
            ok = np.allclose(a.astype(float), b.astype(float), rtol=0, atol=STUDY_TOL, equal_nan=True)
        else:
            ok = np.array_equal(a, b)
        if not ok:
            raise SystemExit(f"the repaired column's {c} differs from the study's")
    log(f"the repaired column equals the study's on {len(both)} columns")
    # today's live form: unmoved
    linked = pd.read_parquet(LC.LINKED)
    day = LC.day_of(pd.Timestamp.now().date().isoformat())
    fa, fb = live_form(base, linked, day), live_form(rep, linked, day)
    j = fa.merge(fb, on="player_id", how="outer", suffixes=("_before", "_after"), indicator=True)
    moved = int((~np.isclose(j["f_hat_before"].fillna(0), j["f_hat_after"].fillna(0), rtol=0, atol=1e-12)).sum())
    live = {"day": LC.date_of(day), "players": int(len(j)), "players_whose_form_moved": moved,
            "max_abs_change_kmh": float((j["f_hat_before"] - j["f_hat_after"]).abs().max())}
    log(f"live form on {live['day']}: {moved} of {len(j)} players move")
    if moved:
        raise SystemExit("today's live form moves under the repair: not written (the study found none would)")
    # write the history, then the column built on it
    rep.to_parquet(LP.REPAIRED, index=False)
    bm = json.loads(LP.BACKFILLED_META.read_text(encoding="utf-8"))
    rsha = hashlib.sha256(LP.REPAIRED.read_bytes()).hexdigest()
    C.write_json(LP.REPAIRED_META, {
        "what": "the live feed's speed history (corrected, with the ATP backfill) with the published averages more "
                "than 5 km/h off the match's complete point record replaced by the point mean (rule ks_within5)",
        "decision": DECISION, "built_by": "src/eda/source_reconciliation/apply_speed.py --build",
        "evidence": "data/studies/source_reconciliation/speed/REPORT.md; the rule's copy speed/histories/ks_within5.parquet",
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "backfilled_sha256": bm["backfilled_sha256"], "repaired_sha256": rsha, **info,
        "rows_changed_file": "data/studies/source_reconciliation/applied/speed_rows_changed.csv", "live_check": live})
    APPLIED.mkdir(parents=True, exist_ok=True)
    rows_changed.to_csv(APPLIED / "speed_rows_changed.csv", index=False, float_format="%.4f")
    new.to_parquet(LP.COLUMN_REPAIRED, index=False)
    moved_cols = {}
    for c in [c for c in new.columns if c.startswith("spd_L_")]:
        d = (new[c].to_numpy(float) - old[c].to_numpy(float))
        d = np.abs(np.nan_to_num(d))
        moved_cols[c] = {"moved_0_25": int((d >= 0.25).sum()), "moved_0_5": int((d >= 0.5).sum()),
                         "moved_1": int((d >= 1).sum()), "max_abs": float(d.max())}
    C.write_json(LP.COLUMN_REPAIRED_META, {
        "what": "stage 2's history column (infosys_atp_backfill/columns.py's build_on) on the repaired speed history",
        "decision": DECISION, "built_by": "src/eda/source_reconciliation/apply_speed.py --build",
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "history": "data/studies/serve_speed_tabpfn/live/speed_panel_repaired.parquet", "history_sha256": rsha,
        "replaces": "data/studies/infosys_atp_backfill/speed_columns_augmented.parquet",
        "replaces_sha256": C.sha256(LP.COLUMN_BACKFILLED),
        "column_sha256": hashlib.sha256(LP.COLUMN_REPAIRED.read_bytes()).hexdigest(), "rows": int(len(new)),
        "moved_against_the_decided_column": moved_cols, "equals_the_study_copy_on": both})
    LP.decided_column()                                   # the records read back
    if LP.frozen_panel()["y"].to_numpy(float).tolist() != rep["y"].to_numpy(float).tolist():
        raise SystemExit("live_panel.frozen_panel() does not read the repaired history back")
    log(f"written: {LP.REPAIRED.name} and {LP.COLUMN_REPAIRED.name}")
    return 0


def check(instance: str | None) -> int:
    from src.eda.current_best_model import compare as CMP
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    if instance is None:
        from src.pipeline.train import active_instance
        instance = str(active_instance())
    name, P, _ = CMP.candidate(instance)
    frame = CMP.inputs_frame(P)
    y = CMP.outcomes(P, THROUGH)
    info = CMP.scoring_info(frame, frame, y, y, THROUGH)

    def column(path):
        z = pd.read_parquet(path, columns=["match_id", "spd_L_B"]).astype({"match_id": str})
        return z.set_index("match_id")["spd_L_B"]
    z_old, z_new = column(LP.COLUMN_BACKFILLED), column(LP.decided_column())
    if LP.decided_column() != LP.COLUMN_REPAIRED:
        raise SystemExit("the repaired column is not in place: run --build first")
    keep = info.index.isin(z_old.index) & info.index.isin(z_new.index)
    lost = int((~keep).sum())
    info = info[keep]
    test = tuple(range(2020, THROUGH + 1))
    p = CMP.seed_table(P, frame, tuple(range(CMP.FIT_FROM, THROUGH + 1))).reindex(info.index)
    if p.isna().any().any():
        raise SystemExit("forecasts missing")
    tab, coef = CMP.score(info, p, p, z_old, z_new, test)
    tab = tab[tab["comparison"].str.startswith("both stages") | tab["comparison"].str.startswith("for scale")].copy()
    tab["comparison"] = tab["comparison"].str.replace("candidate vs reference", "repaired column vs decided column")
    prim = tab[(tab["population"] == "both tours") & tab["comparison"].str.startswith("both stages")].iloc[0]
    harm = bool(prim["estimate"] < -HARM_MLL and prim["hi"] < 0)
    APPLIED.mkdir(parents=True, exist_ok=True)
    tab.to_csv(APPLIED / "speed_harm.csv", index=False)
    out = {"check": "the speed repair alone: stage 2 on the decided column against the repaired one, same forecasts",
           "instance": name, "test_seasons": list(test), "results_read_through": THROUGH,
           "matches_not_in_both_columns": lost, "positive": "the repaired column better (mLL per match)",
           "primary_both_tours": {k: prim[k] for k in ("matches", "estimate", "lo", "hi", "p_better", "reading")},
           "harm_rule": f"worse by more than {HARM_MLL} mLL with the whole 95% interval below 0", "harm": harm,
           "men": {k: tab[(tab["population"] == "men") & tab["comparison"].str.startswith("both stages")].iloc[0][k]
                   for k in ("matches", "estimate", "lo", "hi", "p_better", "reading")},
           "coefficients": {"decided": coef["reference"], "repaired": coef["candidate"]},
           "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    C.write_json(APPLIED / "speed_harm.json", out)
    print(tab[["population", "comparison", "matches", "estimate", "lo", "hi", "p_better", "reading"]].to_string(index=False))
    print({"harm": harm, "primary": out["primary_both_tours"]})
    return 3 if harm else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--build", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--instance", help="--check: the instance whose forecasts are scored (default: the one in use)")
    a = ap.parse_args()
    return build() if a.build else check(a.instance)


if __name__ == "__main__":
    sys.exit(main())
