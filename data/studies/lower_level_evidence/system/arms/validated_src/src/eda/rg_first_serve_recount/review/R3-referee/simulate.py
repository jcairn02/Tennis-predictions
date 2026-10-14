"""R3-referee, step 1: simulate the proposed corrections on the raw rows with the build's own code.

1. Reads the raw Sackmann rows (raw_subset.parquet, from extract_raw.py: stage0_build.normalise(load_raw())) and the
   proposed table as Stage 0 reads a correction table (dtype str, blanks kept).
2. Applies it alone with src.eda.input_data_audit.corrections.apply_row_corrections, then together with the decided
   row_corrections.csv (the rows of it in these events), as a candidate build would.
3. Lists every changed cell: only w_/l_ 1stIn, 1stWon, 2ndWon of the sides the table gives may change, to the table's
   values; nothing else.
4. Runs Stage 0's box checks on the rows before and after: the per-side checks (B0-B4, B6-B8) directly, and the whole
   stage0_build.box_scores (B0-B9, with the scores parsed as Stage 0 parses them) on the RG / Olympic rows. The
   'before' box status is checked against Stage 0's own box_status for the same source rows.
5. The rows Stage 0 now drops for a failed check, and what the fix does to them.

Writes into data/studies/rg_first_serve_recount/review/R3-referee/: sim_changed_cells.csv, sim_box_status.csv,
sim_dropped_rows.csv, sim_summary.json. Usage: ./python.sh src/eda/rg_first_serve_recount/review/R3-referee/simulate.py
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
from src.eda.feature_alpha_audit.repair_data import plain_match_tiebreak  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R3-referee"
STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
COUNTS = [f"{s}_{c}" for s in ("w", "l") for c in K.COUNTS]
SPLIT = [f"{s}_{c}" for s in ("w", "l") for c in K.SPLIT_COUNTS]


def numf(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("object").where(s.notna(), "").astype(str).str.strip().replace("", np.nan),
                         errors="coerce")


def side_checks(df: pd.DataFrame) -> pd.DataFrame:
    """Per side (w, l): Stage 0's per-side checks B0-B4, B6-B8, as box_scores states them."""
    out = {}
    for s in ("w", "l"):
        f = {c: numf(df[f"{s}_{c}"]) for c in K.COUNTS}
        checks = {"B0": pd.concat([f[c].lt(0) for c in K.COUNTS], axis=1).any(axis=1),
                  "B1": f["1stIn"] > f["svpt"], "B2": f["1stWon"] > f["1stIn"],
                  "B3": f["2ndWon"] > f["svpt"] - f["1stIn"], "B4": f["bpSaved"] > f["bpFaced"],
                  "B6": f["df"] > f["svpt"] - f["1stIn"], "B7": f["ace"] > f["1stWon"] + f["2ndWon"],
                  "B8": (f["bpFaced"] - f["bpSaved"]) > f["SvGms"]}
        for k, v in checks.items():
            out[f"{s}_{k}"] = v.fillna(False).to_numpy()
    return pd.DataFrame(out, index=df.index)


def stage0_box(df: pd.DataFrame, s0m: pd.DataFrame) -> pd.DataFrame:
    """stage0_build.box_scores on these rows, with status / status_detail as Stage 0 has them (its score parse and
    its relabelling of unmarked retirements) and the games and tiebreaks counted from the score the way score_columns
    counts them (no RG or Olympic row is a short-set event)."""
    d = df.copy()
    d["score"] = d["score"].fillna("").astype(str)
    key = d["_source_file"].astype(str) + "#" + d["_row"].astype(int).astype(str)
    st = s0m.set_index("key")
    d = B.parse_scores(d)                                    # Stage 0's own parse ...
    d["status"] = key.map(st["status"]).fillna(d["status"])  # ... with Stage 0's relabelling where it holds the row
    d["status_detail"] = key.map(st["status_detail"]).fillna(d["status_detail"])
    counted = [plain_match_tiebreak(s, "", stt, False) for s, stt in zip(d["score"], d["status"])]
    arr = np.array([B.score_counts(c, False) for c in counted], dtype="int64")
    for i, c in enumerate(["sets_w", "sets_l", "games_w", "games_l", "tb_w", "tb_l", "std_tb", "has_bracket",
                           "short_like", "last_done"]):
        d[c] = arr[:, i]
    d = B.box_scores(d)
    return d[["box_status", "has_box"]]


def main() -> int:
    raw = pd.read_parquet(OUT / "raw_subset.parquet")
    raw["_row"] = raw["_row"].astype("int64")
    raw = raw.reset_index(drop=True)
    prop = pd.read_csv(STUDY / "proposed_corrections.csv", dtype=str, keep_default_na=False)
    decided = pd.read_csv(K.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    summary: dict = {"proposed_rows": int(len(prop)), "by_fix": prop["fix"].value_counts().to_dict()}

    # --- 2. apply alone
    before = raw.copy()
    after, done = K.apply_row_corrections(raw.copy(), prop)
    summary["rows_changed_by_replace_split"] = int(len(done["replace_split"]))

    # --- 3. changed cells
    cols = [c for c in raw.columns]
    ch = []
    for c in cols:
        a = before[c].astype("object").where(before[c].notna(), None)
        b = after[c].astype("object").where(after[c].notna(), None)
        diff = [(x != y) and not (x is None and y is None) for x, y in zip(a.tolist(), b.tolist())]
        for i in np.flatnonzero(diff):
            ch.append({"row": int(i), "column": c, "before": a.iloc[i], "after": b.iloc[i]})
    ch = pd.DataFrame(ch)
    ch["source_file"] = before.loc[ch["row"], "_source_file"].to_numpy()
    ch["source_row"] = before.loc[ch["row"], "_row"].to_numpy()
    summary["changed_cells"] = int(len(ch))
    summary["changed_columns"] = ch["column"].value_counts().to_dict()
    summary["changed_outside_split"] = int((~ch["column"].isin(SPLIT)).sum())
    # each changed cell equals the table's value; each given side's three cells read the table's values after
    tk = prop.assign(source_row=prop["source_row"].astype(int)).set_index(["source_file", "source_row"])
    want = [float(tk.loc[(r.source_file, int(r.source_row)), r.column]) for r in ch.itertuples()]
    summary["changed_cells_equal_table"] = int(np.sum(np.array(want) == pd.to_numeric(ch["after"]).to_numpy()))
    ak = after.set_index(["_source_file", "_row"])
    given = reading = noop = 0
    side_rows = []
    for r in prop.itertuples():
        for s in ("w", "l"):
            v = [getattr(r, f"{s}_{c}") for c in K.SPLIT_COUNTS]
            if all(x == "" for x in v):
                continue
            given += 1
            got = [float(ak.loc[(r.source_file, int(r.source_row)), f"{s}_{c}"]) for c in K.SPLIT_COUNTS]
            reading += int(got == [float(x) for x in v])
            side_rows.append({"source_file": r.source_file, "source_row": int(r.source_row), "side": s, "fix": r.fix,
                              **{f"new_{c}": float(x) for c, x in zip(K.SPLIT_COUNTS, v)}})
    bk = before.set_index(["_source_file", "_row"])
    sides = pd.DataFrame(side_rows)
    for c in K.SPLIT_COUNTS:
        sides[f"old_{c}"] = [float(bk.loc[(a, b), f"{s}_{c}"]) for a, b, s in
                             zip(sides["source_file"], sides["source_row"], sides["side"])]
    noop = int(np.all([sides[f"old_{c}"].eq(sides[f"new_{c}"]) for c in K.SPLIT_COUNTS], axis=0).sum())
    summary.update({"sides_given": given, "sides_reading_table_after": reading, "sides_given_but_unchanged": noop})
    ch.to_csv(OUT / "sim_changed_cells.csv", index=False)

    # --- 2b. together with the decided table (the rows of it in these events), as a candidate build would apply both
    rk = set(zip(raw["_source_file"], raw["_row"]))
    dec_here = decided[[(f, int(r)) in rk for f, r in zip(decided["source_file"], decided["source_row"])]]
    overlap = set(zip(dec_here["source_file"], dec_here["source_row"].astype(int))) & \
        set(zip(prop["source_file"], prop["source_row"].astype(int)))
    summary["decided_rows_in_these_events"] = dec_here.groupby(["fix", "action"]).size().rename("rows") \
        .reset_index().to_dict("records")
    summary["decided_rows_also_proposed"] = sorted(f"{a}#{b}" for a, b in overlap)
    try:
        comb, done2 = K.apply_row_corrections(raw.copy(), pd.concat([dec_here, prop], ignore_index=True))
        summary["combined_with_decided"] = {"ok": True, **{k: int(len(v)) for k, v in done2.items() if len(v)}}
    except SystemExit as err:
        summary["combined_with_decided"] = {"ok": False, "error": str(err)}
        comb = None
    # a decided correction that changes a guarded count (svpt, ace, df) of a proposed side would stop the build
    if comb is not None:
        alone_dec, _ = K.apply_row_corrections(raw.copy(), dec_here) if len(dec_here) else (raw.copy(), None)
        moved = []
        for r in prop.itertuples():
            k = (alone_dec["_source_file"].eq(r.source_file) & alone_dec["_row"].eq(int(r.source_row)))
            for s in ("w", "l"):
                for c in ("svpt", "ace", "df"):
                    if str(alone_dec.loc[k, f"{s}_{c}"].iloc[0]) != str(raw.loc[k, f"{s}_{c}"].iloc[0]):
                        moved.append(f"{r.source_file}#{r.source_row} {s}_{c}")
        summary["decided_corrections_touching_guards"] = moved

    # --- 4. per-side checks, before and after, on the corrected rows and on every RG / Olympic row
    rgog = raw["tourney_name"].isin(["Roland Garros", "Paris Olympics"]) & pd.to_numeric(raw["season"]).between(2019, 2025)
    named = pd.Series([(f, r) in set(zip(prop["source_file"], prop["source_row"].astype(int)))
                       for f, r in zip(raw["_source_file"], raw["_row"])], index=raw.index)
    cb, ca = side_checks(before), side_checks(after)
    per = {}
    for k in ["B0", "B1", "B2", "B3", "B4", "B6", "B7", "B8"]:
        per[k] = {"named_rows_failing_before": int((cb[f"w_{k}"] | cb[f"l_{k}"])[named].sum()),
                  "named_rows_failing_after": int((ca[f"w_{k}"] | ca[f"l_{k}"])[named].sum()),
                  "rg_og_rows_failing_before": int((cb[f"w_{k}"] | cb[f"l_{k}"])[rgog].sum()),
                  "rg_og_rows_failing_after": int((ca[f"w_{k}"] | ca[f"l_{k}"])[rgog].sum())}
    summary["per_side_checks"] = per

    # --- 4b. the whole box_scores on the RG / Olympic rows, before and after; 'before' against Stage 0's own
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "source", "source_file", "source_row", "status", "status_detail",
                                 "box_status", "has_box", "tournament_name", "year", "qualifying", "tour", "round"])
    m = m[m["source"].eq("sackmann")].copy()
    m["key"] = m["source_file"].astype(str) + "#" + pd.to_numeric(m["source_row"]).astype("Int64").astype(str)
    sub_b, sub_a = before[rgog].copy(), after[rgog].copy()
    # Stage 0 applies the decided corrections first: do the same on both frames
    if len(dec_here):
        dsub = dec_here[[(f, int(r)) in set(zip(sub_b["_source_file"], sub_b["_row"]))
                         for f, r in zip(dec_here["source_file"], dec_here["source_row"])]]
        if len(dsub):
            sub_b, _ = K.apply_row_corrections(sub_b, dsub)
            sub_a, _ = K.apply_row_corrections(sub_a, dsub)
    bb, ba = stage0_box(sub_b, m), stage0_box(sub_a, m)
    key = sub_b["_source_file"].astype(str) + "#" + sub_b["_row"].astype(int).astype(str)
    st = m.set_index("key")
    tab = pd.DataFrame({"key": key, "tourney_name": sub_b["tourney_name"], "season": sub_b["season"],
                        "round": sub_b["round"], "winner_name": sub_b["winner_name"], "loser_name": sub_b["loser_name"],
                        "named": named[rgog].to_numpy(),
                        "stage0_box_status": key.map(st["box_status"]).to_numpy(),
                        "box_status_before": bb["box_status"].to_numpy(), "box_status_after": ba["box_status"].to_numpy()})
    for k in ["B1", "B2", "B3", "B6", "B7"]:
        tab[f"{k}_before"] = (cb.loc[rgog, f"w_{k}"] | cb.loc[rgog, f"l_{k}"]).to_numpy()
        tab[f"{k}_after"] = (ca.loc[rgog, f"w_{k}"] | ca.loc[rgog, f"l_{k}"]).to_numpy()
    tab.to_csv(OUT / "sim_box_status.csv", index=False)
    in_s0 = tab["stage0_box_status"].notna()
    summary["box_scores"] = {
        "rg_og_rows": int(len(tab)), "rows_in_stage0": int(in_s0.sum()),
        "before_equals_stage0": int((tab.loc[in_s0, "box_status_before"] == tab.loc[in_s0, "stage0_box_status"]).sum()),
        "before_vs_stage0_differences": tab.loc[in_s0 & (tab["box_status_before"] != tab["stage0_box_status"]),
                                                ["key", "stage0_box_status", "box_status_before"]].to_dict("records"),
        "status_change": tab.groupby(["box_status_before", "box_status_after"]).size().rename("rows").reset_index()
        .to_dict("records"),
        "named_status_change": tab[tab["named"]].groupby(["box_status_before", "box_status_after"]).size()
        .rename("rows").reset_index().to_dict("records"),
    }
    # --- 5. rows Stage 0 now drops for a failed check (in the four editions and the Olympics)
    dropped = tab[(tab["box_status_before"].eq("failed_check")) | (tab["stage0_box_status"].eq("failed_check"))].copy()
    dropped.to_csv(OUT / "sim_dropped_rows.csv", index=False)
    summary["dropped_rows"] = dropped.to_dict("records")
    (OUT / "sim_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str)[:12000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
