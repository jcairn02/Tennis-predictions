"""R2-skeptic: the sides I confirm, by stated tests, and a dry run of them through the build's own replace_split.

A proposed side (proposed_corrections.csv) is confirmed only if every test holds:
  T1 my own parse of the raw official file (RG's match JSON / the Olympic results JSON) gives the proposed values;
  T2 my own link (same year, tour, draw and round; full names; Sackmann's winner = the record's winner; non-exact names
     reviewed by hand) puts the side on the same official match and player;
  T3 the guards (svpt, ace, df) are Sackmann's raw values and serve points won do not change;
  T4 the official record passes its own consistency checks for both players;
  T5 the venue's second record, read point by point (RG's MatchBeats, decrypted; the Olympic play-by-play), holds every
     serve point of the side and gives exactly the proposed split (key statistics alone do not count: not a point record);
  T6 the side is "+" (Sackmann's first serves in above the official's: the audit's fault, which every independent
     referee confirms is Sackmann's error), or it is "-" / "0" and Court Vision 2022 (my recount; it holds every serve
     point of the side) reads exactly the official split, with the Match Charting Project not reading Sackmann's;
  T7 no independent record contradicts the official first serves in on the side: the Match Charting Project or Court
     Vision 2022 (holding every serve point) reading Sackmann's first serves in rather than the official's is a
     contradiction, unless a physical record settles the side for the official one (Court Vision 2022 reading the
     official split, or the radar's measured first-serve faults exceeding Sackmann's second-serve points). Court Vision
     2023-24 is not used: it misses faulted first serves (it reads more first serves in than RG on 40-79% of rows).

Writes scope.csv (source_file, source_row, side, first_in, first_won, second_won, fix, notes), excluded.csv (every
proposed side not confirmed, with the failed test), scope_summary.json (counts and the dry run).
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/build_scope.py
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
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"
K3 = ["source_file", "source_row", "side"]


def main() -> int:
    from src.eda.input_data_audit import corrections as K
    v = pd.read_csv(OUT / "value_check.csv", low_memory=False)
    v["sign"] = np.sign(v["d_first_in"]).map({1.0: "+", -1.0: "-", 0.0: "0"})
    # T1-T4 (computed in classify_check.py / link_compare.py)
    v["T1"] = v["val_eq_official"].astype(bool)
    v["T2"] = v["code"].notna() | v["unit"].notna()
    v["T3"] = v["guard_eq_raw"].astype(bool) & v["spw_kept"].astype(bool)
    v["T4"] = v["off_ok"].astype(bool)
    v["T5"] = v["my_second"].eq("agrees") & v["val_eq_second"].astype(bool)
    # T6: sign, or Court Vision 2022 for "-" / "0"
    cv = pd.read_csv(OUT / "cv2022_sides.csv", low_memory=False)[K3 + ["cv_complete", "cv_eq_off_split",
                                                                       "cv_eq_raw_split", "cv_svpt"]]
    v = v.merge(cv, on=K3, how="left")
    pr = pd.read_csv(STUDY / "proposed_rows.csv", low_memory=False).rename(columns={"raw_side": "side"})
    pr = pr[pr["side"].isin(["w", "l"])][K3 + ["mcp_svpt", "mcp_first_in", "mcp_first_won", "mcp_second_won"]]
    v = v.merge(pr, on=K3, how="left")
    mcp_complete = v["mcp_svpt"].eq(v["raw_svpt"])
    v["mcp_eq_sack"] = mcp_complete & v["mcp_first_in"].eq(v["raw_first_in"]) & v["mcp_first_won"].eq(v["raw_first_won"])
    v["mcp_eq_off"] = mcp_complete & v["mcp_first_in"].eq(v["off_first_in"]) & v["mcp_first_won"].eq(v["off_first_won"])
    cv_ok = v["cv_complete"].fillna(False).astype(bool) & v["cv_eq_off_split"].fillna(False).astype(bool)
    v["T6"] = v["sign"].eq("+") | (v["sign"].isin(["-", "0"]) & cv_ok & ~v["mcp_eq_sack"])
    rad0 = pd.read_csv(OUT / "radar_sides.csv", low_memory=False)[K3 + ["refutes_sackmann"]].rename(
        columns={"refutes_sackmann": "radar_refutes"})
    v = v.merge(rad0, on=K3, how="left")
    mcp_contra = mcp_complete & v["mcp_first_in"].eq(v["raw_first_in"]) & ~v["mcp_first_in"].eq(v["off_first_in"])
    cv_contra = v["cv_complete"].fillna(False).astype(bool) & v["cv_eq_raw_split"].fillna(False).astype(bool)
    settled = cv_ok | v["radar_refutes"].eq(True)
    v["T7"] = ~((mcp_contra | cv_contra) & ~settled)
    tests = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
    v["confirmed"] = np.all([v[t] for t in tests], axis=0)
    v["failed"] = [",".join(t for t in tests if not r[t]) for _, r in v[tests].iterrows()]

    # evidence notes per confirmed side
    rad = pd.read_csv(OUT / "radar_sides.csv", low_memory=False)[K3 + ["n_fs", "n2_sack", "n2_off", "refutes_sackmann"]]
    v = v.merge(rad, on=K3, how="left")

    def note(r):
        parts = [f"Sackmann first serves in minus official: {int(r['d_first_in']):+d}"]
        if r["fix"].endswith("B") and r["my_cls"] == "split_other":
            diff = [c for c in ("ace", "df", "bp_faced", "bp_saved") if r[f"raw_{c}"] != r[f"off_{c}"]]
            parts.append("split only; Sackmann's " + "/".join(diff) + " left as is (differs from both official records)")
        def yes(x):
            return bool(x == True) if not (isinstance(x, float) and np.isnan(x)) else False   # noqa: E712
        if yes(r.get("refutes_sackmann")):
            parts.append(f"radar: {int(r['n_fs'])} measured first-serve faults > Sackmann's {int(r['n2_sack'])} "
                         "second-serve points")
        if yes(r["cv_complete"]) and yes(r["cv_eq_off_split"]):
            parts.append("Court Vision 2022 = official split")
        if r["mcp_eq_off"]:
            parts.append("MCP = official")
        return "; ".join(parts)
    conf = v[v["confirmed"]].copy()
    conf["notes"] = conf.apply(note, axis=1)
    scope = conf[["source_file", "source_row", "side", "p_first_in", "p_first_won", "p_second_won", "fix", "notes"]] \
        .rename(columns={"p_first_in": "first_in", "p_first_won": "first_won", "p_second_won": "second_won"})
    for c in ("first_in", "first_won", "second_won", "source_row"):
        scope[c] = scope[c].astype(int)
    scope = scope.sort_values(["source_file", "source_row", "side"]).reset_index(drop=True)
    scope.to_csv(OUT / "scope.csv", index=False)
    exc = v[~v["confirmed"]][K3 + ["fix", "sign", "d_first_in", "my_cls", "my_second", "failed", "player", "year",
                                   "round"]]
    exc.to_csv(OUT / "excluded.csv", index=False)

    # ------------------------------------------------------------------ dry run with the build's own code
    sack = pd.read_parquet(OUT / "sack_rows.parquet")
    keys = scope[["source_file", "source_row"]].drop_duplicates()
    sub = sack.merge(keys, on=["source_file", "source_row"]).copy()
    sub["_source_file"], sub["_row"] = sub["source_file"], sub["source_row"]
    before = sub.copy()
    pc = pd.read_csv(STUDY / "proposed_corrections.csv")
    tab = pc.merge(keys, on=["source_file", "source_row"]).copy()
    for s in ("w", "l"):                     # keep only the sides I confirm
        mine = scope[scope["side"].eq(s)].set_index(["source_file", "source_row"])
        idx = pd.MultiIndex.from_frame(tab[["source_file", "source_row"]])
        keep = idx.isin(mine.index)
        for c in ("svpt", "ace", "df", "1stIn", "1stWon", "2ndWon"):
            tab.loc[~keep, f"{s}_{c}"] = np.nan
        m = mine.reindex(idx)
        assert (tab.loc[keep, f"{s}_1stIn"].to_numpy() == m.loc[keep, "first_in"].to_numpy()).all()
    tab_s = tab.astype({"source_row": "int64"}).astype(str).replace({"nan": "", "None": ""})
    after, done = K.apply_row_corrections(sub.copy(), tab_s)
    counts = [f"{s}_{c}" for s in ("w", "l") for c in K.COUNTS]
    changed = before[counts].astype(str).ne(after[counts].astype(str))
    other = int(changed.drop(columns=[f"{s}_{c}" for s in ("w", "l") for c in K.SPLIT_COUNTS]).to_numpy().sum())
    a = after.set_index(["source_file", "source_row"])
    reads = 0
    fails = {}
    for r in scope.itertuples(index=False):
        row = a.loc[(r.source_file, r.source_row)]
        got = [float(row[f"{r.side}_{c}"]) for c in ("1stIn", "1stWon", "2ndWon")]
        reads += got == [r.first_in, r.first_won, r.second_won]
        f = {c: float(pd.to_numeric(row[f"{r.side}_{c}"] or np.nan, errors="coerce"))
             for c in ("svpt", "1stIn", "1stWon", "2ndWon", "df", "ace")}
        for k, bad in {"B1": f["1stIn"] > f["svpt"], "B2": f["1stWon"] > f["1stIn"],
                       "B3": f["2ndWon"] > f["svpt"] - f["1stIn"], "B6": f["df"] > f["svpt"] - f["1stIn"],
                       "B7": f["ace"] > f["1stWon"] + f["2ndWon"]}.items():
            fails[k] = fails.get(k, 0) + int(bad)
    summary = {
        "proposed_sides": int(len(v)), "confirmed_sides": int(len(scope)),
        "confirmed_match_rows": int(len(keys)),
        "confirmed_by_fix": scope["fix"].value_counts().to_dict(),
        "confirmed_by_fix_and_sign": conf.groupby(["fix", "sign"]).size().rename("n").reset_index().to_dict("records"),
        "excluded_by_reason": exc["failed"].value_counts().to_dict(),
        "excluded_by_fix_and_sign": exc.groupby(["fix", "sign"]).size().rename("n").reset_index().to_dict("records"),
        "minus_zero_confirmed_by_court_vision": int(conf["sign"].isin(["-", "0"]).sum()),
        "dry_run": {"rows_changed": int(len(done["replace_split"])), "sides_reading_my_values_after": int(reads),
                    "other_counts_changed": other, "per_side_checks_failed_after": fails},
        "moved_first_serves": {"before_pct": None},
    }
    # pooled first serves in, before and after, over the confirmed sides
    summary["moved_first_serves"] = {"sackmann_first_in": int(conf["raw_first_in"].sum()),
                                     "official_first_in": int(conf["off_first_in"].sum()),
                                     "serve_points": int(conf["raw_svpt"].sum())}
    (OUT / "scope_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
