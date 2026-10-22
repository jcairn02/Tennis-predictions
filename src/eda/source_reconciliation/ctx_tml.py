"""Tennis My Life's own row for every Stage 0 match that has one, for parts C-E (results, context fields, ATP codes).

Two routes:
    pairs        Stage 0's Sackmann rows (source_file, source_row) -> the TML row the data-continuity study paired them
                 with (data/studies/data_continuity/tml_vs_sackmann_pairs.parquet: s_file, s_row -> t_file, t_row, and
                 whether TML's winner is Sackmann's), read from the staged TML files by (_source_file, _row)
    stage0_tml   Stage 0's own TML rows (source 'tml'): the row itself
Every pair is checked by names (srcc_common.name_grade of TML's winner and loser against Stage 0's players); a pair
whose names do not fit (the TML file rewritten since the pairing) is kept with names_ok False and left out of every
comparison. The brief counts TML's rows before its 2026 splice as dependent on Sackmann's (family sackmann_tml).

Writes data/studies/source_reconciliation/context/work/tml_rows.parquet and context/tml_rows_summary.json.
Run: ./python.sh src/eda/source_reconciliation/ctx_tml.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import ctx_common as X  # noqa: E402

PAIRS = C.STUDIES / "data_continuity" / "tml_vs_sackmann_pairs.parquet"
TML = C.DUMP / "matches" / "tennis_my_life"
COLS = ["tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "indoor", "tourney_date", "match_num",
        "winner_id", "winner_seed", "winner_entry", "winner_name", "winner_age", "loser_id", "loser_seed",
        "loser_entry", "loser_name", "loser_age", "score", "best_of", "round", "_source_file", "_row"]


def staged() -> pd.DataFrame:
    import pyarrow.parquet as pq
    frames = []
    for f in sorted(TML.glob("*/*.parquet")):
        names = set(pq.read_schema(f).names)
        t = pq.read_table(f, columns=[c for c in COLS if c in names]).to_pandas()
        frames.append(t.assign(group=f.parent.name, file=f.name))
    t = pd.concat(frames, ignore_index=True)
    for c in COLS:
        if c not in t:
            t[c] = None
    t["_row"] = pd.to_numeric(t["_row"], errors="coerce").astype("Int64")
    t["tml_key"] = t["_source_file"].astype(str) + ":" + t["_row"].astype(str)
    return t.drop_duplicates("tml_key")


def main() -> int:
    m = X.stage0_matches()
    t = staged().set_index("tml_key")
    X.log(f"staged TML rows: {len(t):,}")
    p = pd.read_parquet(PAIRS, columns=["s_file", "s_row", "t_file", "t_row", "role", "orientation", "link_status"])
    p = p[p["role"].eq("w")].drop_duplicates(["s_file", "s_row"])
    s = m[m["source"].eq("sackmann")][["match_id", "source_file", "source_row"]]
    a = s.merge(p, left_on=["source_file", "source_row"], right_on=["s_file", "s_row"])
    a["tml_key"] = a["t_file"].astype(str) + ":" + a["t_row"].astype(str)
    a = a[["match_id", "tml_key", "orientation", "link_status"]].assign(via="pairs")
    own = m[m["source"].eq("tml")][["match_id", "source_file", "source_row"]].copy()
    own["tml_key"] = own["source_file"].astype(str) + ":" + own["source_row"].astype(str)
    own = own[["match_id", "tml_key"]].assign(orientation="same", link_status="stage0_row", via="stage0_tml")
    x = pd.concat([a, own], ignore_index=True)
    x = x.join(t[[c for c in COLS if c not in ("_source_file", "_row")]], on="tml_key")
    found = x["winner_name"].notna()
    mm = m.set_index("match_id")
    wn = np.where(mm.loc[x["match_id"], "a_won"].to_numpy(dtype=bool), mm.loc[x["match_id"], "name_a"].to_numpy(),
                  mm.loc[x["match_id"], "name_b"].to_numpy())
    ln = np.where(mm.loc[x["match_id"], "a_won"].to_numpy(dtype=bool), mm.loc[x["match_id"], "name_b"].to_numpy(),
                  mm.loc[x["match_id"], "name_a"].to_numpy())
    sw = x["orientation"].eq("swapped").to_numpy()
    g_same = [X._grade(a_, b_) + X._grade(c_, d_) for a_, b_, c_, d_ in zip(x["winner_name"], wn, x["loser_name"], ln)]
    g_swap = [X._grade(a_, d_) + X._grade(c_, b_) for a_, b_, c_, d_ in zip(x["winner_name"], wn, x["loser_name"], ln)]
    g_same, g_swap = np.array(g_same), np.array(g_swap)
    x["names_ok"] = found.to_numpy() & np.where(sw, g_swap >= 2, g_same >= 2)
    x["tml_winner_is_s0_winner"] = ~sw
    # re-pairing: Stage 0's Sackmann rows without a valid pair (TML rewrote its Challenger files since the pairing, so
    # the paired row numbers point elsewhere) take the staged TML row with the same two full names (sorted name keys),
    # the same tour and a tournament date within 7 days, where exactly one such row exists both ways
    from src.eda.match_timing import srcc_common as K
    need = m[m["source"].eq("sackmann") & ~m["match_id"].isin(set(x.loc[x["names_ok"], "match_id"]))]
    used = set(x.loc[x["names_ok"], "tml_key"])
    tt = t[~t.index.isin(used)].reset_index()
    tt["tour"] = np.where(tt["group"].str.startswith("wta"), "wta", "atp")
    tt["k"] = [("|".join(sorted([K.name_info(a)[0], K.name_info(b)[0]]))) for a, b in zip(tt["winner_name"], tt["loser_name"])]
    tt["td"] = pd.to_datetime(tt["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    nk = need[["match_id", "tour", "tdate", "name_a", "name_b", "a_won"]].copy()
    nk["k"] = [("|".join(sorted([K.name_info(a)[0], K.name_info(b)[0]]))) for a, b in zip(nk["name_a"], nk["name_b"])]
    j = nk.merge(tt[["tml_key", "tour", "k", "td", "winner_name"]], on=["tour", "k"])
    j = j[(j["td"] - j["tdate"]).dt.days.abs() <= 7]
    j = j[j.groupby("match_id")["tml_key"].transform("nunique").eq(1) & j.groupby("tml_key")["match_id"].transform("nunique").eq(1)]
    winner_s0 = np.where(j["a_won"].to_numpy(dtype=bool), j["match_id"].map(mm["name_a"]), j["match_id"].map(mm["name_b"]))
    j["tml_winner_is_s0_winner"] = [K.name_info(a)[0] == K.name_info(b)[0] for a, b in zip(j["winner_name"], winner_s0)]
    add = j[["match_id", "tml_key", "tml_winner_is_s0_winner"]].assign(
        orientation=np.where(j["tml_winner_is_s0_winner"], "same", "swapped"), link_status="exact_name_pair_7d",
        via="name_pair", names_ok=True)
    add = add.join(t[[c for c in COLS if c not in ("_source_file", "_row")]], on="tml_key")
    x = pd.concat([x[x["names_ok"] | ~x["match_id"].isin(set(add["match_id"]))], add], ignore_index=True)
    X.WORK.mkdir(parents=True, exist_ok=True)
    for c in ("winner_id", "loser_id", "winner_seed", "loser_seed", "winner_entry", "loser_entry", "winner_age",
              "loser_age", "draw_size", "best_of", "indoor", "tourney_level", "tourney_date", "match_num", "surface",
              "tourney_id", "tourney_name", "round", "score", "winner_name", "loser_name"):
        x[c] = x[c].map(lambda v: None if X.blank(v) else str(v))
    x.to_parquet(X.WORK / "tml_rows.parquet", index=False)
    x["names_ok"] = x["names_ok"].astype(bool)
    summ = {"pairs_rows_read": int(len(p)), "stage0_sackmann_rows_paired": int(len(a)),
            "stage0_tml_rows": int(len(own)), "staged_row_found_for_pairs_and_own_rows": int(found.sum()),
            "re_paired_by_exact_names": int(len(add)),
            "rows_kept": int(len(x)), "names_ok": int(x["names_ok"].sum()),
            "names_not_ok_left_out": int((~x["names_ok"]).sum()),
            "by_via": x.groupby("via")["names_ok"].agg(["size", "sum"]).rename(columns={"sum": "names_ok"})
                       .reset_index().to_dict("records"),
            "stage0_sackmann_matches_with_valid_tml_row": int(x.loc[x["names_ok"] & x["via"].ne("stage0_tml"),
                                                                    "match_id"].nunique())}
    X.write_json(X.OUT / "tml_rows_summary.json", summ)
    X.log(str(summ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
