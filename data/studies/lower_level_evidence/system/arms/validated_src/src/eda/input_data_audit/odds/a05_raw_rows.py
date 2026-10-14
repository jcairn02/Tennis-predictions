"""Task 3/5: the raw tennis-data rows behind the 30 Sep Stage 1, rebuilt, and checked against Stage 1's links.

The 30 Sep build read the staging of the 22 Sep download. Every workbook is byte-identical today except ATP 2013,
ATP 2025, ATP 2026 and WTA 2026 (re-downloaded 5 Oct; the replaced bytes are kept under superseded/) and ATP 2018
(absent on 30 Sep). Those four are re-partitioned here from the superseded workbooks exactly as the ingest does.

Outputs (out/):
    a05_td30.parquet               the 30 Sep tennis-data rows (td_file, td_row, all columns as text)
    a05_link_content_check.json    Stage 1's td_winner/td_loser/odds vs the raw row at (td_file, td_row)
    a05_dup_links.csv              a td row used by two matches, a match with two rows (none expected)
    a05_td_duplicate_rows.csv      the same match listed twice by tennis-data (same pair, same event)
    a05_workbook_diffs.json        superseded vs current workbook, per changed file: rows and cells changed
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from _common import NEW, OLD, OUTD, ROOT, SUP, TD, num, read_book
from src.ingest.public_dump import common as IC

SUPERSEDED = {("atp", 2013): SUP / "atp" / "2013.wayback-20230514150458.520267fb0d44.xlsx",
              ("atp", 2025): SUP / "atp" / "2025.wayback-20260307200645.8acfcf78d18e.xlsx",
              ("atp", 2026): SUP / "atp" / "2026.wayback-20260803192930.003dd0e38f35.xlsx",
              ("wta", 2026): SUP / "wta" / "2026.wayback-20260803192940.d134630c6d12.xlsx"}


def partitions(book: pd.DataFrame, tour: str, year: int) -> pd.DataFrame:
    col = "Series" if "Series" in book.columns else "Tier"
    out = []
    for value, g in book.groupby(book[col].fillna("__none__"), sort=False):
        v = None if value == "__none__" else value
        g = g.copy()
        g["td_file"] = f"data/dump/odds/tennis_data_couk/{tour}/{IC.slugify(v)}/{year}.parquet"
        g["td_row"] = np.arange(len(g))
        out.append(g)
    return pd.concat(out)


frames = []
for f in sorted(TD.glob("*/*/*.parquet")):
    y, t = int(f.stem), f.parts[-3]
    if y < 2010 or (t, y) in SUPERSEDED or (t, y) == ("atp", 2018):
        continue
    df = pd.read_parquet(f)
    df["td_file"] = f.relative_to(ROOT).as_posix()
    df["td_row"] = np.arange(len(df))
    df["tour"], df["season"] = t, y
    frames.append(df)
for (t, y), p in SUPERSEDED.items():
    b = partitions(read_book(p), t, y)
    b["tour"], b["season"] = t, y
    frames.append(b)
td30 = pd.concat(frames, ignore_index=True)
keep = [c for c in td30.columns if not c.startswith("_")]
td30[keep].astype({c: "string" for c in keep if c not in ("td_row", "season")}).to_parquet(OUTD / "a05_td30.parquet", index=False)
print("30 Sep tennis-data rows rebuilt:", len(td30), "(Stage 1 30 Sep summary says 79,728)")

# ---- Stage 1's links against the raw rows
o30 = pd.read_parquet(OLD / "stage1_odds.parquet")
s30 = pd.read_parquet(OLD / "stage0_matches.parquet", columns=["match_id", "a_won"])
lk = o30[o30["link"] != "none"].merge(s30, on="match_id", how="left")
raw = td30.set_index(["td_file", "td_row"])
idx = pd.MultiIndex.from_arrays([lk["td_file"].astype(str), lk["td_row"].astype("int64")])
r = raw.reindex(idx)
chk = {"linked_rows": int(len(lk)), "raw_row_found": int(r["Winner"].notna().sum())}
chk["winner_name_equal"] = int((r["Winner"].to_numpy() == lk["td_winner"].astype(str).to_numpy()).sum())
chk["loser_name_equal"] = int((r["Loser"].to_numpy() == lk["td_loser"].astype(str).to_numpy()).sum())
a_is_w = np.where(lk["link"].eq("winner_swapped"), ~lk["a_won"].astype(bool), lk["a_won"].astype(bool))
aw, al = num(pd.Series(r["AvgW"].to_numpy())), num(pd.Series(r["AvgL"].to_numpy()))
exp_a = np.where(a_is_w, aw, al)
exp_b = np.where(a_is_w, al, aw)
eq = lambda x, y: (np.isclose(x, y) | (np.isnan(x) & np.isnan(y)))  # noqa: E731
chk["avg_a_equal"] = int(eq(exp_a, lk["avg_a"].to_numpy(dtype=float)).sum())
chk["avg_b_equal"] = int(eq(exp_b, lk["avg_b"].to_numpy(dtype=float)).sum())
(OUTD / "a05_link_content_check.json").write_text(json.dumps(chk, indent=1))
print(chk)

# ---- duplicate links
d1 = lk[lk.duplicated(["td_file", "td_row"], keep=False)]
d2 = o30[o30["match_id"].duplicated(keep=False)]
pd.concat([d1.assign(kind="td row used twice"), d2.assign(kind="match twice")]).to_csv(OUTD / "a05_dup_links.csv", index=False)
print("td rows used by two matches:", len(d1), "| match ids twice:", len(d2))
for name, o in (("7 Oct", pd.read_parquet(NEW / "stage1_odds.parquet")),):
    l7 = o[o["link"] != "none"]
    print(name, "td rows used twice:", int(l7.duplicated(["td_file", "td_row"]).sum()), "| match ids twice:", int(o["match_id"].duplicated().sum()))

# ---- the same match listed twice by tennis-data
td30["date"] = pd.to_datetime(td30["Date"], errors="coerce")
td30["pairkey"] = td30[["Winner", "Loser"]].astype(str).apply(lambda s: "|".join(sorted(s)), axis=1)
g = td30.groupby(["tour", "season", "Tournament", "pairkey"])
dup = td30[g["td_row"].transform("size") > 1].sort_values(["tour", "season", "Tournament", "pairkey"])
dup[["tour", "season", "td_file", "td_row", "Date", "Tournament", "Round", "Winner", "Loser", "W1", "L1", "W2", "L2",
     "AvgW", "AvgL", "PSW", "PSL", "Comment"]].to_csv(OUTD / "a05_td_duplicate_rows.csv", index=False)
print("tennis-data rows whose pair appears twice at one event:", len(dup))
print(dup[["tour", "season", "Date", "Tournament", "Round", "Winner", "Loser", "AvgW", "AvgL", "Comment"]].head(40).to_string())
# are any of these duplicate rows linked, and to which matches?
dl = dup.merge(lk[["td_file", "td_row", "match_id", "link"]], on=["td_file", "td_row"], how="left")
print("of those, linked:", int(dl["match_id"].notna().sum()))

# ---- superseded vs current workbook
diffs = {}
cur_paths = {("atp", 2013): "atp/2013.xlsx", ("atp", 2025): "atp/2025.xlsx", ("atp", 2026): "atp/2026.xlsx",
             ("wta", 2026): "wta/2026.xlsx"}
for k, p in SUPERSEDED.items():
    old = read_book(p)
    new = read_book(ROOT / "data/raw/public_dump/tennis_data_couk" / cur_paths[k])
    key = ["Tournament", "Round", "Winner", "Loser"]
    o = old.assign(_k=old[key].astype(str).agg("|".join, axis=1))
    n = new.assign(_k=new[key].astype(str).agg("|".join, axis=1))
    o["_n"] = o.groupby("_k").cumcount()
    n["_n"] = n.groupby("_k").cumcount()
    m = o.merge(n, on=["_k", "_n"], how="outer", suffixes=("_o", "_n"), indicator=True)
    both = m[m["_merge"] == "both"]
    changed = {}
    for c in old.columns:
        if c in new.columns and c not in key:
            a_, b_ = both[f"{c}_o"].fillna("").astype(str), both[f"{c}_n"].fillna("").astype(str)
            nd = int((a_ != b_).sum())
            if nd:
                changed[c] = nd
    rec = {"old_rows": int(len(old)), "new_rows": int(len(new)), "only_old": int((m["_merge"] == "left_only").sum()),
           "only_new": int((m["_merge"] == "right_only").sum()), "matched": int(len(both)),
           "cells_changed_by_column": changed, "columns_old_only": [c for c in old.columns if c not in new.columns],
           "columns_new_only": [c for c in new.columns if c not in old.columns]}
    oc = [c for c in ("AvgW", "AvgL", "MaxW", "MaxL", "PSW", "PSL", "B365W", "B365L") if c in changed]
    if oc:
        ex = both[np.logical_or.reduce([both[f"{c}_o"].fillna("").astype(str) != both[f"{c}_n"].fillna("").astype(str) for c in oc])]
        rec["odds_changed_examples"] = ex[["_k", "Date_o", "Date_n"] + [f"{c}_{s}" for c in oc for s in "on"]].head(12).to_dict("records")
    if "Date" in changed:
        ex = both[both["Date_o"].fillna("").astype(str) != both["Date_n"].fillna("").astype(str)]
        rec["date_changed_examples"] = ex[["_k", "Date_o", "Date_n"]].head(8).to_dict("records")
    rec["only_old_examples"] = m[m["_merge"] == "left_only"]["_k"].head(8).tolist()
    rec["only_new_examples"] = m[m["_merge"] == "right_only"]["_k"].head(8).tolist()
    diffs[f"{k[0]} {k[1]}"] = rec
(OUTD / "a05_workbook_diffs.json").write_text(json.dumps(diffs, indent=1, default=str))
print(json.dumps(diffs, indent=1, default=str)[:12000])
