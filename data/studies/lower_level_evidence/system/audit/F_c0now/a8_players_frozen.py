"""Role E audit of C0_now, part 8: every column of the frozen player rows (two per frozen match), equality only, in
column batches (no value is printed). Expected: differences only on the 1,644 box-layer matches, only in box columns.
Run: ./python.sh data/studies/lower_level_evidence/system/audit/F_c0now/a8_players_frozen.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as LC  # noqa: E402

AUD = ROOT / "data/studies/lower_level_evidence/system/audit/F_c0now"
CAND = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now"
RP, CP = LC.STAGE0_DIR / "stage0_match_players.parquet", CAND / "stage0_match_players.parquet"
cols = pq.read_schema(RP).names
OUT = {"columns_equal": cols == pq.read_schema(CP).names,
       "dtypes_equal": str(pq.read_schema(RP)) == str(pq.read_schema(CP)).replace(str(CP), str(RP))}
r = pd.read_parquet(RP, columns=["match_id", "side"])
c = pd.read_parquet(CP, columns=["match_id", "side"])
rk = r["match_id"] + "|" + r["side"]
ck = pd.Series(np.arange(len(c)), index=c["match_id"] + "|" + c["side"])
OUT["frozen_rows"], OUT["cand_rows"] = int(len(r)), int(len(c))
OUT["frozen_rows_missing"] = int((~rk.isin(ck.index)).sum())
pos = ck.reindex(rk).to_numpy()
L = pd.read_parquet(CAND / "box_layers.parquet", columns=["match_id", "applied", "reference_match"])
layered = set(L.loc[L["applied"].astype(bool) & L["reference_match"].astype(bool), "match_id"])
in_layer = r["match_id"].isin(layered).to_numpy()
diff = {}
changed = np.zeros(len(r), dtype=bool)
rest = [x for x in cols if x not in ("match_id", "side")]
for i in range(0, len(rest), 8):
    batch = rest[i:i + 8]
    a = pd.read_parquet(RP, columns=batch)
    b = pd.read_parquet(CP, columns=batch).iloc[pos].reset_index(drop=True)
    for col in batch:
        na, nb = a[col].isna().to_numpy(), b[col].isna().to_numpy()
        same = np.asarray(a[col].astype(object).to_numpy() == b[col].astype(object).to_numpy(), dtype=bool)
        e = (same & ~na & ~nb) | (na & nb)
        diff[col] = {"rows_differ": int((~e).sum()), "outside_layered_matches": int((~e & ~in_layer).sum())}
        changed |= ~e
    del a, b
OUT["columns_that_differ"] = {k: v for k, v in diff.items() if v["rows_differ"]}
OUT["rows_differ_any"] = int(changed.sum())
OUT["rows_differ_outside_layered_matches"] = int((changed & ~in_layer).sum())
OUT["matches_with_a_differing_row"] = int(r.loc[changed, "match_id"].nunique())
(AUD / "a8_results.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
print(json.dumps(OUT, indent=1, default=str))
