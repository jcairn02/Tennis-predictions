"""The proposed per-match corrections of the Roland-Garros first-serve recount (checklist item 6, step 2).

For every Sackmann player row of Roland Garros 2022-2025 and the Paris Olympics 2024 (rows.parquet, from recount.py)
the official record is RG's own statistics (rolandgarros.com) or the Olympic results file. A row is compared with it
on the counts the official record gives: svpt, ace, df, first_in, first_won, second_won, bp_faced, bp_saved.

    equal          every count equal: nothing to do
    split          only the first/second-serve split differs (first_in, first_won, second_won): serve points,
                   aces, double faults, serve points won and break points equal. Sub-classes by Sackmann's first
                   serves in against the record: "+" (more: second serves booked as first, the audit's fault),
                   "-" (fewer), "0" (the same first serves in, the points won moved between the serves)
    split+other    the split and another count differ: listed, not proposed
    other          another count differs, the split agrees: listed, not proposed
    no_record      no official record, or one that fails its own consistency checks

A split row is proposed only where the official record is consistent and the venue's other own record does not
contradict it: RG's MatchBeats recount (and RG's key statistics, 2025) or the Olympic play-by-play recount, where that
record holds every point (the same serve points), must give the same split. The correction is replace_split
(src/eda/input_data_audit/corrections.py): the three split counts of each such side from the official record, the
side's svpt, ace and df as guards.

Writes, in data/studies/rg_first_serve_recount/:
    proposed_rows.csv          one row per Stage 0 player row in scope, with its class and every source's counts
    proposed_corrections.csv   one row per raw match row to correct, in row_corrections.csv's columns
    control_2019_2021.csv      the same classes for RG 2019-2021 (the editions without the fault): a check of
                               the rule, never proposed
    proposal_summary.json      counts by edition and class, pooled first serves in before and after, the dry run
Reads no model result. Usage: ./python.sh src/eda/rg_first_serve_recount/propose.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402

OUT = S.STUDY
COMPARED = ["svpt", "ace", "df", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]
REST = ["svpt", "ace", "df", "bp_faced", "bp_saved"]
FIX = {"RG": "RGFS", "OG": "OGFS"}
ROW_COLUMNS = (["fix", "action", "match_id", "source_file", "source_row"] + K.ROW_GUARDS + ["side", "value"]
               + [f"{s}_{c}" for s in ("w", "l") for c in K.COUNTS])


def official(rows: pd.DataFrame) -> pd.DataFrame:
    """off_<count>: RG's statistics for RG rows, the Olympic results for OG rows; off_ok: the record and its
    opponent's pass the record's own consistency checks."""
    rg = rows["event"].eq("RG")
    for c in COMPARED:
        rows[f"off_{c}"] = np.where(rg, rows.get(f"api_{c}"), rows.get(f"ol_{c}"))
    opp = rows.groupby("match_id")["off_svpt"].transform("sum") - rows["off_svpt"]
    api_ok = (rows["api_first_won_den"].eq(rows["api_first_in"])
              & rows["api_second_won_den"].eq(rows["api_svpt"] - rows["api_first_in"])
              & rows["api_ret_den"].eq(opp)
              & rows["api_total_won"].eq(rows["api_first_won"] + rows["api_second_won"] + rows["api_ret_won"]))
    ol_ok = (rows["ol_status"].eq("OFFICIAL") & rows["ol_spw"].eq(rows["ol_first_won"] + rows["ol_second_won"])
             & rows["ol_second_served"].eq(rows["ol_svpt"] - rows["ol_first_in"]))
    ok = np.where(rg, api_ok, ol_ok)
    rows["off_ok"] = pd.Series(ok, index=rows.index).astype(bool) & rows["off_svpt"].notna()
    rows["off_ok"] = rows.groupby("match_id")["off_ok"].transform("all")      # both players' records consistent
    return rows


def second_channel(rows: pd.DataFrame) -> pd.Series:
    """'agrees', 'incomplete' (it misses points: other serve points), 'absent', or 'contradicts' (the same serve
    points, another split): RG's MatchBeats (and key statistics) or the Olympic play-by-play against the record."""
    out = pd.Series("absent", index=rows.index, dtype="object")
    for src in ("mb", "ks", "olp"):
        if f"{src}_svpt" not in rows:
            continue
        held = rows[f"{src}_svpt"].notna() & rows["off_svpt"].notna()
        complete = held & rows[f"{src}_svpt"].eq(rows["off_svpt"])
        same = complete & np.all([rows[f"{src}_{c}"].eq(rows[f"off_{c}"]) for c in S.SPLIT], axis=0)
        out[held & ~complete & out.eq("absent")] = "incomplete"
        out[same & out.isin(["absent", "incomplete"])] = "agrees"
        out[complete & ~same] = "contradicts"
    return out


def classify(rows: pd.DataFrame) -> pd.DataFrame:
    """equal; split (A: only the split differs); split_other (B: the split and an ace, double-fault or break-point
    count differ, serve points and serve points won agree); points (serve points or serve points won differ, the
    split differs too); other (the split agrees, something else differs); no_record."""
    rows["spw_raw"] = rows["raw_first_won"] + rows["raw_second_won"]
    rows["spw_off"] = rows["off_first_won"] + rows["off_second_won"]
    frame = rows["raw_svpt"].eq(rows["off_svpt"]) & rows["spw_raw"].eq(rows["spw_off"])
    rest_eq = np.all([rows[f"raw_{c}"].eq(rows[f"off_{c}"]) for c in REST], axis=0) & frame
    split_eq = np.all([rows[f"raw_{c}"].eq(rows[f"off_{c}"]) for c in S.SPLIT], axis=0)
    has = rows["off_ok"] & rows["raw_svpt"].notna()
    rows["cls"] = np.select([~has, rest_eq & split_eq, split_eq, rest_eq, frame],
                            ["no_record", "equal", "other", "split", "split_other"], "points")
    rows["d_first_in"] = rows["raw_first_in"] - rows["off_first_in"]
    rows["d_first_won"] = rows["raw_first_won"] - rows["off_first_won"]
    fixable = rows["cls"].isin(["split", "split_other"])
    rows["sign"] = np.where(fixable, np.sign(rows["d_first_in"]).map({1.0: "+", -1.0: "-", 0.0: "0"}), "")
    rows["second_channel"] = second_channel(rows)
    rows["proposed"] = fixable & ~rows["second_channel"].eq("contradicts")
    rows["proposal_class"] = np.where(rows["proposed"], np.where(rows["cls"].eq("split"), "A", "B"), "")
    return rows


def correction_rows(p: pd.DataFrame) -> pd.DataFrame:
    """One replace_split row per raw match row, from its proposed player rows."""
    raw = S.raw_rows()
    out = []
    for (sf, sr), g in p.groupby(["source_file", "source_row"]):
        r = raw[(raw["source_file"].eq(sf)) & (raw["source_row"].eq(sr))]
        if len(r) != 1:
            raise SystemExit(f"{sf} row {sr}: {len(r)} raw rows")
        r = r.iloc[0]
        cls = "A" if g["proposal_class"].eq("A").all() else "B"     # a match with a B side is a B correction
        rec = {"fix": FIX[g["event"].iloc[0]] + cls, "action": "replace_split", "match_id": g["match_id"].iloc[0],
               "source_file": sf, "source_row": int(sr), **{k: r[k] for k in K.ROW_GUARDS}}
        for x in g.itertuples():
            s = x.raw_side
            if s not in ("w", "l"):
                raise SystemExit(f"{sf} row {sr}: {x.player_name} is neither the raw row's winner nor its loser")
            rec.update({f"{s}_svpt": int(x.raw_svpt), f"{s}_ace": int(x.raw_ace) if pd.notna(x.raw_ace) else None,
                        f"{s}_df": int(x.raw_df) if pd.notna(x.raw_df) else None,
                        f"{s}_1stIn": int(x.off_first_in), f"{s}_1stWon": int(x.off_first_won),
                        f"{s}_2ndWon": int(x.off_second_won)})
        out.append(rec)
    return pd.DataFrame(out).reindex(columns=ROW_COLUMNS)


def dry_run(table: pd.DataFrame) -> dict:
    """Apply the table to the raw rows with the build's own code, then check that every corrected side now reads the
    official split, that nothing else changed, and that the box checks a split can fail (B1-B3, B6, B7) pass."""
    raw = S.raw_rows()
    keys = table[["source_file", "source_row"]].astype({"source_row": "Int64"})
    sub = raw.merge(keys, on=["source_file", "source_row"]).rename(columns={"source_file": "_source_file"})
    sub["_row"] = sub["source_row"]
    before = sub.copy()
    after, done = K.apply_row_corrections(sub.copy(), table.astype({"source_row": "int64"}).astype(str)
                                          .replace({"nan": "", "None": ""}))
    counts = [f"{s}_{c}" for s in ("w", "l") for c in K.COUNTS]
    changed = (before[counts].astype(str) != after[counts].astype(str))
    split_cols = [f"{s}_{c}" for s in ("w", "l") for c in K.SPLIT_COUNTS]
    other_changed = int(changed.drop(columns=split_cols).to_numpy().sum())
    fails = {}
    for s in ("w", "l"):
        f = {c: pd.to_numeric(after[f"{s}_{c}"].replace("", np.nan), errors="coerce") for c in K.COUNTS}
        checks = {"B1": f["1stIn"] > f["svpt"], "B2": f["1stWon"] > f["1stIn"],
                  "B3": f["2ndWon"] > f["svpt"] - f["1stIn"], "B6": f["df"] > f["svpt"] - f["1stIn"],
                  "B7": f["ace"] > f["1stWon"] + f["2ndWon"]}
        for k, v in checks.items():
            fails[k] = fails.get(k, 0) + int(v.fillna(False).sum())
    a = after.set_index(["_source_file", after["source_row"].astype(int)])
    t = table.set_index(["source_file", table["source_row"].astype(int)]).reindex(a.index)
    agree = 0
    for s in ("w", "l"):
        given = t[f"{s}_1stIn"].notna()
        same = np.all([pd.to_numeric(a[f"{s}_{c}"], errors="coerce").eq(pd.to_numeric(t[f"{s}_{c}"]))
                       for c in K.SPLIT_COUNTS], axis=0)
        agree += int((given & same).sum())
    return {"rows_in_table": int(len(table)), "rows_changed": int(len(done["replace_split"])),
            "sides_given": int(table[[f"{s}_1stIn" for s in ("w", "l")]].notna().to_numpy().sum()),
            "sides_reading_the_official_split_after": int(agree), "other_counts_changed": other_changed,
            "split_checks_failed_after": fails}


def edition_rates(rows: pd.DataFrame) -> pd.DataFrame:
    out = []
    for k, g in rows.groupby(["event", "year", "tour", "draw"]):
        h = g[g["raw_svpt"].notna() & g["raw_first_in"].notna()]
        after_fi = np.where(h["proposed"], h["off_first_in"], h["raw_first_in"])
        after_fw = np.where(h["proposed"], h["off_first_won"], h["raw_first_won"])
        o = g[g["off_ok"]]
        out.append({**dict(zip(["event", "year", "tour", "draw"], k)), "rows": len(h),
                    "first_in_pct_before": round(100 * h["raw_first_in"].sum() / h["raw_svpt"].sum(), 2),
                    "first_in_pct_after": round(100 * after_fi.sum() / h["raw_svpt"].sum(), 2),
                    "first_won_pct_before": round(100 * h["raw_first_won"].sum() / h["raw_first_in"].sum(), 2),
                    "first_won_pct_after": round(100 * after_fw.sum() / after_fi.sum(), 2),
                    "official_first_in_pct": round(100 * o["off_first_in"].sum() / o["off_svpt"].sum(), 2)
                    if len(o) else None,
                    **{f"n_{c}": int(g["cls"].eq(c).sum()) for c in ["equal", "split", "split_other", "points",
                                                                      "other", "no_record"]},
                    "n_proposed_A": int(g["proposal_class"].eq("A").sum()),
                    "n_proposed_B": int(g["proposal_class"].eq("B").sum())})
    return pd.DataFrame(out)


def main() -> int:
    rows = pd.read_parquet(OUT / "rows.parquet")
    rows = rows[rows["source"].eq("sackmann")].copy()
    rows = classify(official(rows))
    keep = ["event", "year", "tour", "draw", "round", "player_name", "won", "match_id", "player_id", "source_file",
            "source_row", "raw_side", "rg_code", "unit", "api_court", "cls", "sign", "proposed", "proposal_class",
            "second_channel", "d_first_in", "d_first_won"] + [f"{p}_{c}" for p in ("raw", "off") for c in COMPARED] \
        + [f"{p}_{c}" for p in ("mb", "ks", "olp", "cv", "mcp")
           for c in ("svpt", "first_in", "first_won", "second_won", "ace", "df")]
    keep = [c for c in keep if c in rows]
    scope = rows[(rows["event"].eq("RG") & rows["year"].between(2022, 2025)) | rows["event"].eq("OG")]
    control = rows[rows["event"].eq("RG") & rows["year"].between(2019, 2021)]
    scope[keep].to_csv(OUT / "proposed_rows.csv", index=False)
    control[keep].to_csv(OUT / "control_2019_2021.csv", index=False)
    table = correction_rows(scope[scope["proposed"]])
    table.to_csv(OUT / "proposed_corrections.csv", index=False)
    rates = pd.concat([edition_rates(control), edition_rates(scope)], ignore_index=True)
    rates.to_csv(OUT / "proposal_editions.csv", index=False)
    p = scope[scope["proposed"]]
    moved = p[p["d_first_in"] > 0]
    summary = {
        "player_rows_in_scope": int(len(scope)), "by_class": scope["cls"].value_counts().to_dict(),
        "fixable_by_class_and_sign": scope[scope["cls"].isin(["split", "split_other"])]
        .groupby(["cls", "sign"]).size().rename("rows").reset_index().to_dict("records"),
        "second_channel_of_fixable_rows": scope[scope["cls"].isin(["split", "split_other"])]["second_channel"]
        .value_counts().to_dict(),
        "proposed_player_rows": {"A": int(p["proposal_class"].eq("A").sum()), "B": int(p["proposal_class"].eq("B").sum())},
        "proposed_match_rows": table["fix"].value_counts().to_dict() if len(table) else {},
        "moved_first_serves_won_share": round(float(moved["d_first_won"].sum() / moved["d_first_in"].sum()), 4)
        if len(moved) else None,
        "control_2019_2021_by_class": control["cls"].value_counts().to_dict(),
        "control_fixable_by_sign": control[control["cls"].isin(["split", "split_other"])]["sign"].value_counts()
        .to_dict(),
        "dry_run": dry_run(table) if len(table) else None,
    }
    (OUT / "proposal_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(json.dumps(summary, indent=1, default=str))
    print(rates.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
