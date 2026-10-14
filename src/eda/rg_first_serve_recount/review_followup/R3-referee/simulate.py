"""R3-referee (follow-up), step 6: Stage 0's box checks (B0-B9) on the rows as Stage 0 reads them today and with the
candidate applied; the rows the overrides bring back.

Reads sub_today.parquet (the raw rows with the decided tables, as Stage 0 applies them today) and sub_cand.parquet (the
whole candidate: the decided override table plus the RG rows, then the decided corrections plus the step-2 split rows
of matches without an override and the four exchanges), from extract.py; and, when given --scope, a table of my own
(overrides_scope.csv) applied to sub_raw.parquet with the decided tables, the confirmed split rows of matches outside
my scope and the exchanges I confirm.

On every Stage 0 row of Roland Garros 2019-2026 and the Paris Olympics: stage0_build.box_scores (B0-B9, with B5
dropping only the service games), the score parsed as Stage 0 parses it and its status as Stage 0 holds it (its
relabelling of unmarked retirements); the 'today' status is checked against Stage 0's own box_status. Then, per
version: the box status, each check's failures, the rows whose status changes, and the rows Stage 0 drops today
(no usable box, or no service games) that a version brings back.

Writes sim_rows.csv, sim_summary.json (and sim_scope_rows.csv / sim_scope_summary.json with --scope) into
data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/simulate.py [--scope]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402

from src.eda.feature_alpha_audit.repair_data import plain_match_tiebreak  # noqa: E402
from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

CHECKS = ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]


def checks(df: pd.DataFrame, st: pd.DataFrame) -> pd.DataFrame:
    """box_scores on these rows, and each check's failure (as box_scores computes it, on usable boxes)."""
    d = df.copy()
    d["score"] = d["score"].fillna("").astype(str)
    key = F.rowkey(d["_source_file"], d["_row"])
    d = B.parse_scores(d)
    d["status"] = key.map(st["status"]).fillna(d["status"]).to_numpy()
    d["status_detail"] = key.map(st["status_detail"]).fillna(d["status_detail"]).to_numpy()
    counted = [plain_match_tiebreak(s, "", stt, False) for s, stt in zip(d["score"], d["status"])]
    arr = np.array([B.score_counts(c, False) for c in counted], dtype="int64")
    for i, c in enumerate(["sets_w", "sets_l", "games_w", "games_l", "tb_w", "tb_l", "std_tb", "has_bracket",
                           "short_like", "last_done"]):
        d[c] = arr[:, i]
    # each check, recomputed the way box_scores states it (for the record of which check fails)
    w, l = B.box_frame(d, "w"), B.box_frame(d, "l")
    kinds = pd.DataFrame({"w": B.box_kind(d, "w"), "l": B.box_kind(d, "l")})
    usable = ~kinds.isin(["blank", "all_zero", "partial"]).any(axis=1)
    games, std_tb = d["games_w"] + d["games_l"], d["std_tb"]
    scored = d["status"].isin(["completed", "retired", "other"]) & d["score"].ne("") & ~d["status_detail"].eq("unknown")
    zero_sv = (w["sv_gms"].fillna(-1).eq(0) & w["svpt"].gt(0)) | (l["sv_gms"].fillna(-1).eq(0) & l["svpt"].gt(0))
    sv_total = (w["sv_gms"] + l["sv_gms"]).where(~zero_sv)
    b5 = usable & scored & sv_total.notna() & ~((sv_total - (games - std_tb)).abs().le(1) | (sv_total - games).abs().le(1))
    fails = {"B5": b5.fillna(False)}
    for f in (w, l):
        sv = f["sv_gms"].where(~b5 & ~zero_sv)
        side = {"B0": f.lt(0).any(axis=1), "B1": f["first_in"] > f["svpt"], "B2": f["first_won"] > f["first_in"],
                "B3": f["second_won"] > f["svpt"] - f["first_in"], "B4": f["bp_saved"] > f["bp_faced"],
                "B6": f["df"] > f["svpt"] - f["first_in"], "B7": f["ace"] > f["first_won"] + f["second_won"],
                "B8": (f["bp_faced"] - f["bp_saved"]) > sv}
        for k, v in side.items():
            fails[k] = fails.get(k, pd.Series(False, index=d.index)) | v.fillna(False)
    played = (games - std_tb) - np.where(d["status"].eq("completed"), 0, 1)
    fails["B9"] = (scored & ((w["svpt"] + l["svpt"]) < B.MIN_POINTS_PER_GAME * played)).fillna(False)
    out = B.box_scores(d)
    res = pd.DataFrame({"box_status": out["box_status"], "has_box": out["has_box"]}, index=d.index)
    for k in CHECKS:
        res[f"fail_{k}"] = (usable & fails[k]).to_numpy()
    return res


def stage0_rows(frame: pd.DataFrame, s0: pd.DataFrame) -> pd.Series:
    """Rows of the frame that are Stage 0 rows of RG 2019-2026 or the Paris Olympics (by source file and row)."""
    key = F.rowkey(frame["_source_file"], frame["_row"])
    return key.isin(set(s0["key"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", action="store_true", help="also simulate my own scope (overrides_scope.csv)")
    args = ap.parse_args()
    s0 = pd.read_parquet(F.S0 / "stage0_matches.parquet",
                         columns=["match_id", "source", "source_file", "source_row", "status", "status_detail",
                                  "box_status", "has_box", "tournament_name", "year", "qualifying", "tour", "round"])
    s0 = s0[(s0["tournament_name"].eq("Roland Garros") & s0["year"].between(2019, 2026))
            | s0["tournament_name"].eq("Paris Olympics")].copy()
    s0["key"] = F.rowkey(s0["source_file"], s0["source_row"])
    st = s0.drop_duplicates("key").set_index("key")
    versions = {"today": pd.read_parquet(F.OUT / "sub_today.parquet"), "cand": pd.read_parquet(F.OUT / "sub_cand.parquet")}
    if args.scope:
        versions["scope"] = scope_version()
    res = {}
    base = None
    for name, fr in versions.items():
        fr["_row"] = pd.to_numeric(fr["_row"]).astype("int64")
        sel = stage0_rows(fr, s0)
        f = fr[sel].copy()
        f["key"] = F.rowkey(f["_source_file"], f["_row"])
        f = f.drop_duplicates("key").set_index("key")
        r = checks(f.reset_index(drop=False), st)
        r.index = f.index
        res[name] = r
        if base is None:
            base = f[["tourney_name", "season", "tour", "round", "winner_name", "loser_name", "score", "source"]]
    tab = base.copy()
    tab["stage0_box_status"] = tab.index.map(st["box_status"])
    tab["stage0_match_id"] = tab.index.map(st["match_id"])
    for name, r in res.items():
        tab[f"{name}_box_status"] = r["box_status"].reindex(tab.index)
        tab[f"{name}_fails"] = r[[f"fail_{k}" for k in CHECKS]].reindex(tab.index).apply(
            lambda x: " ".join(k for k, v in zip(CHECKS, x) if v), axis=1)
    usable = ["full", "no_svgms"]
    smry = {"stage0_rows": int(len(tab)),
            "today_reproduces_stage0": int((tab["today_box_status"] == tab["stage0_box_status"]).sum()),
            "today_vs_stage0_differences": tab.loc[tab["today_box_status"] != tab["stage0_box_status"],
                                                   ["stage0_match_id", "stage0_box_status", "today_box_status"]]
            .to_dict("records")}
    for name in [n for n in res if n != "today"]:
        t = tab
        smry[name] = {
            "status_by_version": {v: t[f"{v}_box_status"].value_counts().to_dict() for v in ("today", name)},
            "transitions": t.groupby(["today_box_status", f"{name}_box_status"]).size().rename("rows").reset_index()
            .to_dict("records"),
            "check_failures_on_usable_boxes": {v: {k: int(t[f"{v}_fails"].str.contains(rf"\b{k}\b").sum()) for k in CHECKS}
                                               for v in ("today", name)},
            "rows_losing_a_usable_box": t.loc[t["today_box_status"].isin(usable) & ~t[f"{name}_box_status"].isin(usable),
                                              ["stage0_match_id", "today_box_status", f"{name}_box_status"]].to_dict("records"),
            "rows_brought_back": t.loc[~t["today_box_status"].eq("full") & t[f"{name}_box_status"].eq("full")]
            .groupby(["tourney_name", "season", "today_box_status"]).size().rename("rows").reset_index()
            .astype(str).to_dict("records"),
            "rows_still_dropped": t.loc[~t[f"{name}_box_status"].isin(usable),
                                        ["stage0_match_id", "winner_name", "loser_name", "score", "today_box_status",
                                         f"{name}_box_status", f"{name}_fails"]].to_dict("records"),
        }
    tab.to_csv(F.OUT / ("sim_rows.csv" if not args.scope else "sim_scope_rows.csv"))
    (F.OUT / ("sim_summary.json" if not args.scope else "sim_scope_summary.json")).write_text(
        json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in smry.items()}, indent=1, default=str)[:20000])
    return 0


def scope_version() -> pd.DataFrame:
    """My scope as a candidate: the decided override table plus my override rows (source from the lead's table, keyed
    identically), then the decided corrections plus the confirmed split rows of matches outside my overrides and my
    exchanges, applied to the raw subset with the build's own code."""
    raw = pd.read_parquet(F.OUT / "sub_raw.parquet")
    raw["_row"] = pd.to_numeric(raw["_row"]).astype("int64")
    mine = pd.read_csv(F.OUT / "overrides_scope.csv", dtype=str, keep_default_na=False)
    lead = pd.read_csv(F.FOLLOW / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    keys = lead.drop(columns=[c for c in F.OV_COLS]).merge(mine[["feed_key", "stage0_match_id"] + F.OV_COLS],
                                                           on=["feed_key", "stage0_match_id"], how="inner")
    keys = keys[lead.columns]
    dec_ov = pd.read_csv(B.DECIDED_OVERRIDES, dtype=str, keep_default_na=False)
    ov = pd.concat([dec_ov.assign(source="tml"), keys], ignore_index=True)
    ov = ov.reindex(columns=list(dec_ov.columns) + [c for c in lead.columns if c not in dec_ov.columns]).fillna("")
    dec_rc = pd.read_csv(K.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    confirmed = pd.read_csv(F.STUDY / "confirmed" / "confirmed_corrections.csv", dtype=str, keep_default_na=False)
    ex = pd.read_csv(F.OUT / "exchanges_scope.csv", dtype=str, keep_default_na=False)
    lead_ex = pd.read_csv(F.FOLLOW / "proposed_exchanges.csv", dtype=str, keep_default_na=False)
    ex = lead_ex.merge(ex[["source_file", "source_row"]], on=["source_file", "source_row"], how="inner")
    split = confirmed[~confirmed["match_id"].isin(set(keys["stage0_match_id"]))]
    rc = pd.concat([dec_rc, split.reindex(columns=dec_rc.columns, fill_value=""),
                    ex.reindex(columns=dec_rc.columns, fill_value="")], ignore_index=True)
    raw = B.apply_box_overrides(raw, ov, "R3 scope", {})
    raw, _ = K.apply_row_corrections(raw, rc)
    return raw


if __name__ == "__main__":
    sys.exit(main())
