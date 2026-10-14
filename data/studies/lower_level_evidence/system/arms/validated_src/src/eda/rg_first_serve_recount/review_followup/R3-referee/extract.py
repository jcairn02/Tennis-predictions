"""R3-referee (follow-up), step 0: Stage 0's raw rows read once, and the lead's candidate applied with the build's code.

1. raw = stage0_build.normalise(stage0_build.load_raw()): Stage 0's raw rows, before any table.
2. The candidate's two tables, built twice: by whole_box.candidate_tables (imported; the lead's script is not run) from
   followup/proposed_overrides.csv, followup/proposed_exchanges.csv and confirmed/confirmed_corrections.csv, and my own
   way (the decided tables with the same rows appended). The two must name the same rows with the same values.
3. The subset kept for the review: every row of a Roland-Garros tournament id 2018-2026 (any source), the other Slams,
   the clay Masters and the Olympics of 2018-2026, and every row any of the four tables names, as read.
4. The candidate applied to the WHOLE raw frame (stage0_build.apply_box_overrides, then
   input_data_audit.corrections.apply_row_corrections), so the overrides' exactly-one-row test runs on every row: the
   rows that change, whether a table names them, whether each override row reads its table afterwards, whether the
   exchanges read exchanged. The subset after.
5. The decided tables (what Stage 0 applies today) applied to the subset, the same way.

Writes into data/studies/rg_first_serve_recount/followup/review/R3-referee/: sub_raw.parquet, sub_today.parquet,
sub_cand.parquet, candidate_overrides.csv, candidate_corrections.csv, extract_summary.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/extract.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.rg_first_serve_recount import whole_box as W  # noqa: E402  (functions only; its main is not run)

NAMES = {"Roland Garros", "Paris Olympics", "Tokyo Olympics", "Australian Open", "Wimbledon", "US Open", "Us Open",
         "Madrid Masters", "Rome Masters", "Monte Carlo Masters", "Madrid", "Rome"}


def ov_key(frame: pd.DataFrame, src: pd.Series | None = None) -> pd.Series:
    """The key apply_box_overrides looks a row up by: source|tour|tid|round|winner key|loser key."""
    if src is None:     # a raw frame
        return (frame["source"] + "|" + frame["tour"] + "|" + frame["tid"] + "|" + frame["round"] + "|"
                + frame["wkey"] + "|" + frame["lkey"])
    return (src + "|" + frame["tour"] + "|" + frame["tid"] + "|" + frame["round"] + "|" + frame["winner_key"] + "|"
            + frame["loser_key"])


def table_source(ov: pd.DataFrame) -> pd.Series:
    return ov["source"].fillna("").replace("", "tml") if "source" in ov else pd.Series("tml", index=ov.index)


def save(frame: pd.DataFrame, name: str) -> None:
    f = frame.copy()
    for c in f.columns:
        if f[c].dtype == object:
            f[c] = f[c].map(lambda x: None if x is None or (isinstance(x, float) and x != x) else str(x))
    f.to_parquet(F.OUT / name, index=False)


def main() -> int:
    F.OUT.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    # ---------------------------------------------------------------- 2. the candidate's tables
    dec_ov = pd.read_csv(B.DECIDED_OVERRIDES, dtype=str, keep_default_na=False)
    dec_rc = pd.read_csv(K.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    lead_ov = pd.read_csv(F.FOLLOW / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    lead_ex = pd.read_csv(F.FOLLOW / "proposed_exchanges.csv")                    # as whole_box.main holds them
    confirmed = pd.read_csv(F.STUDY / "confirmed" / "confirmed_corrections.csv")
    ov_c, rc_c = W.candidate_tables(lead_ov, lead_ex, confirmed)
    # my own way
    mine_ov = pd.concat([dec_ov.assign(source="tml"), lead_ov], ignore_index=True)
    split_keep = confirmed[~confirmed["match_id"].isin(set(lead_ov["stage0_match_id"]))]
    add = pd.concat([split_keep, lead_ex], ignore_index=True)
    add = add.astype(object).where(add.notna(), "")
    for c in add.columns:
        add[c] = add[c].map(lambda x: str(int(x)) if isinstance(x, float) and float(x).is_integer() else str(x))
    mine_rc = pd.concat([dec_rc, add.reindex(columns=dec_rc.columns, fill_value="")], ignore_index=True)
    cmp_ov = ov_c[mine_ov.columns.tolist()].astype(str).reset_index(drop=True)
    cmp_rc = rc_c[dec_rc.columns.tolist()].astype(str).reset_index(drop=True)
    summary["tables"] = {
        "decided_overrides": int(len(dec_ov)), "decided_corrections": int(len(dec_rc)),
        "lead_overrides": int(len(lead_ov)), "lead_exchanges": int(len(lead_ex)),
        "confirmed_split_rows": int(len(confirmed)), "split_rows_kept": int(len(split_keep)),
        "split_rows_kept_by_fix": split_keep["fix"].value_counts().to_dict(),
        "candidate_overrides": int(len(ov_c)), "candidate_corrections": int(len(rc_c)),
        "candidate_tables_equal_my_own_overrides": bool(cmp_ov.equals(mine_ov.astype(str).reset_index(drop=True))),
        "candidate_tables_equal_my_own_corrections": bool(cmp_rc.equals(mine_rc.astype(str).reset_index(drop=True))),
        "candidate_corrections_by_fix_action": rc_c.groupby(["fix", "action"]).size().rename("rows").reset_index()
        .to_dict("records")}
    if not summary["tables"]["candidate_tables_equal_my_own_corrections"]:
        d = (cmp_rc != mine_rc.astype(str).reset_index(drop=True))
        summary["tables"]["correction_cells_differing"] = int(d.to_numpy().sum())
        summary["tables"]["correction_columns_differing"] = d.sum()[d.sum() > 0].to_dict()
    ov_c.to_csv(F.OUT / "candidate_overrides.csv", index=False)
    rc_c.to_csv(F.OUT / "candidate_corrections.csv", index=False)

    # ---------------------------------------------------------------- 1 and 3. the raw rows and the subset
    raw = B.normalise(B.load_raw())
    summary["raw_rows"] = int(len(raw))
    key = ov_key(raw)
    rk = F.rowkey(raw["_source_file"], raw["_row"])
    yr = pd.to_numeric(raw["season"], errors="coerce")
    rg_tid = raw["tid"].str.fullmatch(r"20(1[89]|2[0-6])-520")
    big = raw["tourney_name"].isin(NAMES) | raw["tourney_name"].str.contains("Olympic", case=False)
    named_ov = key.isin(set(ov_key(ov_c, table_source(ov_c))))
    named_rc = rk.isin(set(F.rowkey(rc_c["source_file"], rc_c["source_row"])))
    sub = rg_tid | (big & yr.between(2018, 2026)) | named_ov | named_rc
    summary["subset_rows"] = int(sub.sum())
    summary["subset_rg_rows_by_source_season"] = raw[rg_tid].groupby(["source", "season"]).size().rename("rows") \
        .reset_index().astype(str).to_dict("records")
    sub_raw = raw.loc[sub].copy()
    save(sub_raw, "sub_raw.parquet")

    # ---------------------------------------------------------------- 4. the candidate on the whole frame
    before = F.numbers(raw, F.OV_COLS).astype("float32")
    smry: dict = {}
    raw = B.apply_box_overrides(raw, ov_c, "candidate overrides (R3 simulation)", smry)
    raw, done = K.apply_row_corrections(raw, rc_c)
    after = F.numbers(raw, F.OV_COLS).astype("float32")
    same = ((before == after) | (before.isna() & after.isna())).all(axis=1)
    changed = ~same
    named = named_ov | named_rc
    src = table_source(ov_c)
    pos = pd.Series(raw.index, index=key.to_numpy())
    ov_rows = pos.loc[ov_key(ov_c, src).to_numpy()].to_numpy()
    tv = F.numbers(ov_c, F.OV_COLS).to_numpy(dtype="float32")
    got = after.loc[ov_rows].to_numpy()
    reads = ((got == tv) | (np.isnan(got) & np.isnan(tv))).all(axis=1)
    rg = ov_c["box_source"].eq("rolandgarros").to_numpy()
    rc_rows = raw.index[named_rc.to_numpy()]
    ex = done.get("exchange_box", pd.Index([]))
    ex_rk = set(F.rowkey(lead_ex["source_file"], lead_ex["source_row"]))
    ex_rows = [i for i in ex if rk.loc[i] in ex_rk]
    w9, l9 = [f"w_{c}" for c in F.NINE.values()], [f"l_{c}" for c in F.NINE.values()]
    ex_ok = [bool(np.allclose(after.loc[i, w9].to_numpy(float), before.loc[i, l9].to_numpy(float), equal_nan=True)
                  and np.allclose(after.loc[i, l9].to_numpy(float), before.loc[i, w9].to_numpy(float), equal_nan=True))
             for i in ex_rows]
    summary["candidate_on_whole_frame"] = {
        "override_log": smry.get("box_overrides"),
        "corrections_by_action": {a: int(len(i)) for a, i in done.items() if len(i)},
        "rows_changed": int(changed.sum()),
        "rows_changed_not_named_by_a_table": int((changed & ~named).sum()),
        "rows_named_unchanged": int((named & ~changed).sum()),
        "override_rows_also_named_by_a_correction": int(len(set(ov_rows) & set(rc_rows))),
        "rg_override_rows_reading_their_table_after": int(reads[rg].sum()), "rg_override_rows": int(rg.sum()),
        "decided_override_rows_reading_their_table_after": int(reads[~rg].sum()), "decided_override_rows": int((~rg).sum()),
        "rg_override_rows_blank_before": int(before.loc[ov_rows[rg]].isna().all(axis=1).sum()),
        "rgx_exchanges_applied": len(ex_rows), "rgx_exchanges_reading_exchanged": int(sum(ex_ok)),
    }
    sub_cand = raw.loc[sub].copy()
    save(sub_cand, "sub_cand.parquet")
    del raw, before, after, key, rk, pos
    # ---------------------------------------------------------------- 5. the decided tables on the subset
    today = sub_raw.copy()
    smry2: dict = {}
    today = B.apply_box_overrides(today, dec_ov, "decided overrides (R3 simulation)", smry2)
    today, done2 = K.apply_row_corrections(today, dec_rc)
    summary["decided_on_subset"] = {"override_log": smry2.get("box_overrides"),
                                    "corrections_by_action": {a: int(len(i)) for a, i in done2.items() if len(i)}}
    save(today, "sub_today.parquet")
    (F.OUT / "extract_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
