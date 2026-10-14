"""R1-rederive (round 2): my override rows and the four exchanges applied to Stage 0's raw RG rows with the build's code.

Reads work/stage0_rg_rows.parquet (Stage 0's raw rows of RG 2019-2026, as normalise() leaves them) and my tables
(my_overrides.csv, rgx.csv). Applies:
  1. my override table with stage0_build.apply_box_overrides (source column "sackmann" / "tml");
  2. the four exchanges with src.eda.input_data_audit.corrections.apply_row_corrections (action exchange_box);
then runs Stage 0's own box checks (stage0_build.box_scores) on every RG row, before and after, and compares them with
my re-implementation in classify.py.

Writes dry_run.json. Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/dry_run.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.input_data_audit import corrections as X  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"
SRC = list(C.BOX_SOURCE_NAMES.values())
CNT = [f"{s}_{c}" for s in "wl" for c in SRC]


def checked(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 0's box_scores on the rows (scores parsed with Stage 0's own functions)."""
    x = df.copy()
    x = B.parse_scores(x)
    sc = np.array([B.score_counts(s, False) for s in x["score"]], dtype="int64")
    for i, c in enumerate(["sets_w", "sets_l", "games_w", "games_l", "tb_w", "tb_l", "std_tb"]):
        x[c] = sc[:, i]
    return B.box_scores(x)


def main() -> None:
    s0 = pd.read_parquet(WORK / "stage0_rg_rows.parquet")
    s0 = s0[(s0["source"].eq("sackmann") & s0["tid"].str.fullmatch(r"20(19|2[0-6])-520")) |
            (s0["source"].eq("tml") & s0["group"].eq("atp_qualifying") & s0["tid"].eq("2026-520"))].copy()
    for c in CNT:     # the staged files carry text; write the numbers back as the source files do
        s0[c] = [("" if pd.isna(v) else format(v, ".10g")) for v in s0[c]]
    s0 = s0.reset_index(drop=True)
    before = s0.copy()
    ov = pd.read_csv(HERE / "my_overrides.csv", dtype=str, keep_default_na=False)
    ov = ov[ov["group"].isin(["W22", "W26"])].reset_index(drop=True)
    addendum = "--with-addendum" in sys.argv
    if addendum:   # the added matches appended to overrides_scope.csv by addendum.py, with their lookup keys
        sc = pd.read_csv(HERE / "overrides_scope.csv", dtype=str, keep_default_na=False)
        mm = pd.read_csv(HERE / "matches.csv", dtype=str, keep_default_na=False)
        ad = sc[~sc["stage0_match_id"].isin(set(ov["stage0_match_id"]))].merge(
            mm[["s0_match_id", "source", "tour", "tid", "round", "wkey", "lkey", "source_file", "source_row"]],
            left_on="stage0_match_id", right_on="s0_match_id")
        ad = ad.rename(columns={"wkey": "winner_key", "lkey": "loser_key"})
        ov = pd.concat([ov, ad[[c for c in ov.columns if c in ad.columns]]], ignore_index=True).fillna("")
    # apply_box_overrides reads ov["score"] and ov["minutes"] even when the table has no such column (KeyError):
    # the decided table carries both, so mine carries them empty (no score or minutes is replaced)
    ov["score"], ov["minutes"] = "", ""
    summary: dict = {}
    after = B.apply_box_overrides(s0.copy(), ov, "my_overrides.csv", summary)
    # every override row reads my values afterwards; nothing else changed
    key = after["source"] + "|" + after["tour"] + "|" + after["tid"] + "|" + after["round"] + "|" + after["wkey"] + \
        "|" + after["lkey"]
    want = ov["source"] + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|" + \
        ov["loser_key"]
    pos = pd.Series(after.index, index=key.to_numpy()).loc[want.to_numpy()].to_numpy()
    reads = (after.loc[pos, CNT].astype(str).to_numpy() == ov[CNT].astype(str).to_numpy()).all(axis=1)
    changed = (after[CNT].astype(str).to_numpy() != before[CNT].astype(str).to_numpy()).any(axis=1)
    out_of_table = changed & ~after.index.isin(pos)
    # the four exchanges
    rgx = pd.read_csv(HERE / "rgx.csv")
    raw = before.set_index(["_source_file", "_row"])
    table = pd.DataFrame({"fix": "RGX", "action": "exchange_box", "match_id": "",
                          "source_file": rgx["source_file"], "source_row": rgx["source_row"].astype(str),
                          "tourney_id": [raw.loc[(f, r), "tourney_id"] for f, r in zip(rgx["source_file"], rgx["source_row"])],
                          "round": rgx["round"], "winner_name": rgx["winner_name"], "loser_name": rgx["loser_name"],
                          "side": "", "value": ""})
    for c in CNT:
        table[c] = ""
    after2, done = X.apply_row_corrections(after.copy(), table)
    at = done["exchange_box"]
    ex_ok = []
    for i, r in zip(at, rgx.itertuples()):
        ok = all(float(after2.loc[i, f"w_{s}"]) == getattr(r, f"rg_w_{k}") and
                 float(after2.loc[i, f"l_{s}"]) == getattr(r, f"rg_l_{k}")
                 for k, s in (("ace", "ace"), ("df", "df"), ("svpt", "svpt"), ("first_in", "1stIn"),
                              ("first_won", "1stWon"), ("second_won", "2ndWon"), ("bp_faced", "bpFaced"),
                              ("bp_saved", "bpSaved")))
        ok &= float(after2.loc[i, "w_SvGms"]) == r.der_w_sv_gms and float(after2.loc[i, "l_SvGms"]) == r.der_l_sv_gms
        ex_ok.append(bool(ok))
    overlap = set(pos) & set(at)
    # Stage 0's own box checks, before and after
    cb, ca = checked(before), checked(after2)
    m = pd.read_csv(HERE / "matches.csv", low_memory=False).set_index("rid")
    ca["rid_"] = after2["rid"].to_numpy()
    in_ov = ca.index.isin(pos)
    gained = in_ov & ~cb["has_box"].to_numpy() & ca["has_box"].to_numpy()
    lost = in_ov & cb["has_box"].to_numpy() & ~ca["has_box"].to_numpy()
    yr = after2["season"].astype(int).to_numpy()
    res = {
        "override_rows": int(len(ov)), "rows_found": int(len(pos)), "rows_reading_my_values": int(reads.sum()),
        "rows_changed_outside_table": int(out_of_table.sum()),
        "rows_changed_by_overrides": int(changed.sum()),
        "exchanges_applied": int(len(at)), "exchanges_reading_rg": int(sum(ex_ok)),
        "rows_both_overridden_and_exchanged": len(overlap),
        "overridden_rows_box_status_after": ca.loc[in_ov, "box_status"].value_counts().to_dict(),
        "overridden_rows_failing_after": int((in_ov & ca["box_status"].eq("failed_check").to_numpy()).sum()),
        "overridden_rows_without_sv_gms_after": int((in_ov & ca["box_status"].eq("no_svgms").to_numpy()).sum()),
        "matches_gaining_a_box": int(gained.sum()),
        "matches_gaining_a_box_by_year": pd.Series(yr[gained]).value_counts().to_dict(),
        "matches_losing_a_box": int(lost.sum()),
        "rgx_box_status_after": ca.loc[ca.index.isin(at), "box_status"].tolist(),
        "my_checks_agree_with_stage0": None,
    }
    g23 = [(int(after2.loc[i, "season"]), after2.loc[i, "winner_name"], after2.loc[i, "loser_name"])
           for i in np.flatnonzero(gained) if yr[i] != 2026]
    res["gained_outside_2026"] = g23
    # my classify.py checks (off_fails, off_B5) against Stage 0's on the overridden rows
    mine = m.loc[after2.loc[pos, "rid"].to_numpy()]
    st0_fail = ca.loc[pos, "box_status"].eq("failed_check").to_numpy()
    res["my_checks_agree_with_stage0"] = bool((mine["off_fails"].astype(str).eq("True").to_numpy() == st0_fail).all())
    # Stage 0's checks today on the same rows (before), for the record
    res["overridden_rows_box_status_before"] = cb.loc[in_ov, "box_status"].value_counts().to_dict()
    name = "dry_run_with_addendum.json" if addendum else "dry_run.json"
    (HERE / name).write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
