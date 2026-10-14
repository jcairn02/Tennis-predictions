"""R3-referee, step 5: this reviewer's scope, and the simulation of exactly that scope.

Starts from every proposed side (official_sides.csv: the values read here from the official records' raw files, equal
to the proposal's) and leaves out:
  X1  both sides of a match in which both proposed sides read fewer first serves in than the official record ("both
      minus"): there the independent records split (MCP and Court Vision: 4 for the official record, 3 for Sackmann's,
      1 tie; on Van de Zandschulp they disagree with each other), against 29-0 for the official record on every other
      "-" side; the official record may be the one off in such matches.
  X2  every Olympic side where Sackmann reads fewer first serves in than the Olympic record ("-"): no clean Olympic
      edition validates that record, MCP is noisier there, and the only charts of such sides (Fernandez, Muchova) side
      with Sackmann or neither.
  X3  Laura Pigossi's side of Pigossi-Kawa, RG 2024 Q2 (wta_matches_qual_itf_2024.csv row 37474): Stage 0 drops the
      match for a failed check (B3, from this very fault); the fix would bring it back with Kawa's side still corrupt
      and unproposed (class "points": 36 first serves in where RG has 23, serve points 51 against 48).

Writes scope.csv (source_file, source_row, side, first_in, first_won, second_won, fix, notes), scope_excluded.csv, and
scope_simulation.json: the scope as a replace_split table applied to the raw rows with apply_row_corrections, alone and
with the decided table, the changed cells, the per-side checks and Stage 0's box_scores before and after.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R3-referee/make_scope.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3common as C  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("r3sim", HERE / "simulate.py")
SIM = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SIM)
K = SIM.K
OUT = C.OUT
PIGOSSI = ("data/raw/public_dump/sackmann_archive/wta/wta_matches_qual_itf_2024.csv", 37474, "w")


def main() -> int:
    s = pd.read_csv(OUT / "official_sides.csv")
    s["d"] = s["raw_first_in"] - s["off_first_in"]
    # both players read fewer first serves in from Sackmann than from the official record, whether or not the
    # opponent's side is proposed (every player row of the scope, from the lead's table; its official values were
    # re-read from the raw files in independent.py)
    allr = pd.read_csv(C.STUDY / "proposed_rows.csv", low_memory=False)
    allr["d"] = allr["raw_first_in"] - allr["off_first_in"]
    per = allr.groupby(["source_file", "source_row"])["d"].agg(["size", "max"])
    both_minus = set(per[(per["size"] == 2) & (per["max"] < 0)].index)
    s["X1"] = np.array([(a, b) in both_minus for a, b in zip(s["source_file"], s["source_row"])]) & s["d"].lt(0).to_numpy()
    s["X2"] = s["fix"].str.startswith("OG") & s["d"].lt(0)
    s["X3"] = [(a, b, c) == PIGOSSI for a, b, c in zip(s["source_file"], s["source_row"], s["side"])]
    s["excluded"] = s[["X1", "X2", "X3"]].any(axis=1)
    assert s["values_equal_official"].all() and s["svpt_equal"].all() and s["spw_equal"].all()
    keep = s[~s["excluded"]].copy()
    keep["notes"] = np.select([keep["d"].gt(0), keep["d"].lt(0)], ["sign +", "sign -"], "sign 0") + \
        "; second record " + keep["second_channel"].astype(str)
    scope = keep[["source_file", "source_row", "side", "off_first_in", "off_first_won", "off_second_won", "fix", "notes"]] \
        .rename(columns={"off_first_in": "first_in", "off_first_won": "first_won", "off_second_won": "second_won"})
    for c in ("first_in", "first_won", "second_won"):
        scope[c] = scope[c].astype(int)
    scope.to_csv(OUT / "scope.csv", index=False)
    ex = s[s["excluded"]].copy()
    ex["reason"] = np.select([ex["X3"], ex["X1"] & ex["X2"], ex["X1"], ex["X2"]],
                             ["X3 Pigossi-Kawa: fix would bring back a match whose other side is corrupt",
                              "X1+X2 both-minus match at the Olympics", "X1 both-minus match", "X2 Olympic '-' side"], "")
    ex[["fix", "source_file", "source_row", "side", "player", "round", "raw_first_in", "off_first_in", "raw_first_won",
        "off_first_won", "raw_second_won", "off_second_won", "reason"]].to_csv(OUT / "scope_excluded.csv", index=False)

    # ---- the scope as a replace_split table: the proposed rows, the excluded sides blanked
    prop = pd.read_csv(C.STUDY / "proposed_corrections.csv", dtype=str, keep_default_na=False)
    inscope = set(zip(scope["source_file"], scope["source_row"].astype(int), scope["side"]))
    t = prop.copy()
    for i, r in t.iterrows():
        for side in ("w", "l"):
            if (r["source_file"], int(r["source_row"]), side) not in inscope:
                for c in ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon"):
                    t.at[i, f"{side}_{c}"] = ""
    t = t[(t["w_1stIn"] != "") | (t["l_1stIn"] != "")].reset_index(drop=True)
    # each given value equals the scope's
    sv = {(a, int(b), c): (x, y, z) for a, b, c, x, y, z in scope[["source_file", "source_row", "side", "first_in",
                                                                     "first_won", "second_won"]].itertuples(index=False)}
    for r in t.itertuples():
        for side in ("w", "l"):
            v = getattr(r, f"{side}_1stIn")
            if v != "":
                assert (int(float(v)), int(float(getattr(r, f"{side}_1stWon"))), int(float(getattr(r, f"{side}_2ndWon")))) \
                    == sv[(r.source_file, int(r.source_row), side)]
    t.to_csv(OUT / "scope_as_corrections.csv", index=False)

    raw = C.raw_subset().reset_index(drop=True)
    before = raw.copy()
    after, done = K.apply_row_corrections(raw.copy(), t)
    cells = []
    for c in raw.columns:
        a = before[c].astype("object").where(before[c].notna(), None).tolist()
        b = after[c].astype("object").where(after[c].notna(), None).tolist()
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y and not (x is None and y is None):
                cells.append((i, c, x, y))
    ch = pd.DataFrame(cells, columns=["row", "column", "before", "after"])
    ch["side"] = ch["column"].str[0]
    ch["key"] = [(before.at[i, "_source_file"], int(before.at[i, "_row"]), sd) for i, sd in zip(ch["row"], ch["side"])]
    decided = pd.read_csv(K.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    rk = set(zip(raw["_source_file"], raw["_row"]))
    dec_here = decided[[(f, int(r)) in rk for f, r in zip(decided["source_file"], decided["source_row"])]]
    try:
        _, done2 = K.apply_row_corrections(raw.copy(), pd.concat([dec_here, t], ignore_index=True))
        combined = {"ok": True, **{k: int(len(v)) for k, v in done2.items() if len(v)}}
    except SystemExit as err:
        combined = {"ok": False, "error": str(err)}
    rgog = raw["tourney_name"].isin(["Roland Garros", "Paris Olympics"]) & pd.to_numeric(raw["season"]).between(2019, 2025)
    named = pd.Series([(f, int(r)) in set(zip(t["source_file"], t["source_row"].astype(int)))
                       for f, r in zip(raw["_source_file"], raw["_row"])], index=raw.index)
    cb, ca = SIM.side_checks(before), SIM.side_checks(after)
    checks = {k: {"scope_rows_failing_before": int((cb[f"w_{k}"] | cb[f"l_{k}"])[named].sum()),
                  "scope_rows_failing_after": int((ca[f"w_{k}"] | ca[f"l_{k}"])[named].sum())}
              for k in ["B0", "B1", "B2", "B3", "B4", "B6", "B7", "B8"]}
    m = pd.read_parquet(C.ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet",
                        columns=["source", "source_file", "source_row", "status", "status_detail", "box_status"])
    m = m[m["source"].eq("sackmann")].copy()
    m["key"] = m["source_file"].astype(str) + "#" + pd.to_numeric(m["source_row"]).astype("Int64").astype(str)
    sb, sa = before[rgog].copy(), after[rgog].copy()
    if len(dec_here):
        d2 = dec_here[[(f, int(r)) in set(zip(sb["_source_file"], sb["_row"])) for f, r in
                       zip(dec_here["source_file"], dec_here["source_row"])]]
        if len(d2):
            sb, _ = K.apply_row_corrections(sb, d2)
            sa, _ = K.apply_row_corrections(sa, d2)
    bb, ba = SIM.stage0_box(sb, m), SIM.stage0_box(sa, m)
    key = sb["_source_file"].astype(str) + "#" + sb["_row"].astype(int).astype(str)
    s0 = key.map(m.set_index("key")["box_status"])
    res = {
        "scope_sides": int(len(scope)), "scope_by_fix": scope["fix"].value_counts().to_dict(),
        "scope_match_rows": int(len(t)), "scope_match_rows_by_fix": t["fix"].value_counts().to_dict(),
        "excluded_sides": int(len(ex)), "excluded_by_reason": ex["reason"].value_counts().to_dict(),
        "excluded_by_fix": ex["fix"].value_counts().to_dict(),
        "rows_changed": int(len(done["replace_split"])), "changed_cells": int(len(ch)),
        "changed_columns": ch["column"].value_counts().to_dict(),
        "changed_outside_split": int((~ch["column"].str[2:].isin(["1stIn", "1stWon", "2ndWon"])).sum()),
        "changed_sides_outside_scope": int(sum(k not in inscope for k in ch["key"])),
        "scope_sides_reading_their_values_after": int(sum(
            [float(after.loc[(after["_source_file"].eq(a)) & (after["_row"].eq(b)), f"{c}_{x}"].iloc[0]) for x in
             ("1stIn", "1stWon", "2ndWon")] == [float(v) for v in sv[(a, b, c)]] for a, b, c in inscope)),
        "combined_with_decided": combined, "per_side_checks": checks,
        "box_scores_before_equals_stage0": int((bb["box_status"].to_numpy() == s0.to_numpy()).sum()),
        "rg_og_rows": int(rgog.sum()),
        "box_status_changes": pd.DataFrame({"before": bb["box_status"].to_numpy(), "after": ba["box_status"].to_numpy()})
        .value_counts().rename("rows").reset_index().to_dict("records"),
    }
    (OUT / "scope_simulation.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
