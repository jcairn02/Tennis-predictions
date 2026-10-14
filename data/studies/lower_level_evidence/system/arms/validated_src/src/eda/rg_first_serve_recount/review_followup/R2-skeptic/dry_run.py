"""R2-skeptic (round 2): my two scope tables through the build's own code, on the Roland Garros raw rows.

My overrides (overrides_scope.csv: my values) take the lead's key columns (source, tour, tid, round, winner_key,
loser_key), and are applied with stage0_build.apply_box_overrides to the raw rows of RG 2019-2026 (extract_raw.py, the
build's own loader and normaliser; the keys carry the tournament id, so the subset holds every row a key can name).
My exchanges take the lead's exchange rows (proposed_exchanges.csv) and are applied with
corrections.apply_row_corrections. Checks: every override names exactly one row, every overridden row reads my values,
every exchanged row reads its two boxes exchanged, nothing else changes. Writes nothing but dry_run.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/dry_run.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"


def numbers(f: pd.DataFrame) -> pd.DataFrame:
    return f[B.OVERRIDE_COUNTS].apply(lambda s: pd.to_numeric(s.astype(str).str.strip().replace(
        {"": np.nan, "nan": np.nan, "None": np.nan}), errors="coerce"))


def main() -> int:
    raw = pd.read_parquet(OUT / "raw_rg.parquet")
    raw["_row"] = raw["_row"].astype("Int64").astype(str)
    mine = pd.read_csv(OUT / "overrides_scope.csv", dtype=str, keep_default_na=False)
    lead = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    keys = ["feed_key", "stage0_match_id", "box_source", "source", "tour", "tid", "round", "winner_key", "loser_key",
            "winner_name", "loser_name", "score", "minutes"]
    ov = mine.merge(lead[keys], on=["feed_key", "stage0_match_id"], how="left")
    before = numbers(raw)
    df = B.apply_box_overrides(raw.copy(), ov, "R2-skeptic overrides_scope.csv", {})
    ex = pd.read_csv(LEAD / "proposed_exchanges.csv", dtype=str, keep_default_na=False)
    mine_ex = pd.read_csv(OUT / "exchanges_scope.csv", dtype=str, keep_default_na=False)
    ex = ex.merge(mine_ex[["source_file", "source_row"]], on=["source_file", "source_row"])
    df, done = K.apply_row_corrections(df, ex)
    after = numbers(df)
    key = df["source"] + "|" + df["tour"] + "|" + df["tid"] + "|" + df["round"] + "|" + df["wkey"] + "|" + df["lkey"]
    want = ov["source"] + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|" + \
        ov["loser_key"]
    pos = pd.Series(df.index, index=key.to_numpy())
    rows = pd.Index(pos.loc[want.to_numpy()].to_numpy())
    table = ov[B.OVERRIDE_COUNTS].apply(lambda s: pd.to_numeric(s.replace("", np.nan), errors="coerce")).to_numpy()
    got = after.loc[rows].to_numpy()
    reads = ((got == table) | (np.isnan(got) & np.isnan(table))).all(axis=1)
    exch_rows = done.get("exchange_box", pd.Index([]))
    w = [f"w_{c}" for c in B.C.BOX_SOURCE_NAMES.values()]
    l = [f"l_{c}" for c in B.C.BOX_SOURCE_NAMES.values()]
    ex_ok = [bool(np.allclose(after.loc[r, w].to_numpy(float), before.loc[r, l].to_numpy(float), equal_nan=True)
                  and np.allclose(after.loc[r, l].to_numpy(float), before.loc[r, w].to_numpy(float), equal_nan=True))
             for r in exch_rows]
    changed = ~((before == after) | (before.isna() & after.isna())).all(axis=1)
    named = rows.union(pd.Index(exch_rows))
    res = {"override_rows": int(len(ov)), "override_rows_reading_my_values_after": int(reads.sum()),
           "exchanges_applied": int(len(exch_rows)), "exchanges_reading_exchanged": int(sum(ex_ok)),
           "raw_rows_changed": int(changed.sum()), "changed_outside_my_tables": int(changed[~changed.index.isin(named)].sum()),
           "overridden_rows_without_a_box_before": int(before.loc[rows].isna().all(axis=1).sum())}
    (OUT / "dry_run.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
