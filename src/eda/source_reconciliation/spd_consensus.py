"""Source reconciliation, Part G (serve speed), step 3a: alternative speed histories under consensus rules. Reads no
match result. The live feed's history (live_panel.frozen_panel()) is never modified: each alternative is a copy written
under speed/histories/ (git-ignored parquet).

Every rule acts on the history's own rows (same player-matches, same basis, edition and n); it changes a row's value y
or its use flag. Values are compared on the MatchBeats scale (spd_agree.py: y_mb, the families fam_*); a new value v is
put back on the row's own basis by the row's offset (y - y_mb: -0.5 on a key-statistic or rally-analysis row, 0
otherwise), so each edition keeps one scale.
    current         the history as it is (the base)
    points_first    a row with a complete point copy (spd_agree's precedence) takes that copy's mean; else unchanged
                    (the panel's Slam rule, everywhere, with the referee's completeness gate)
    median          the median of the independent families the player-match has (the best point copy, the ATP key
                    statistic, the IBM statistic, RG's key statistic, the AO match centre); with two, their mean
    ks_within5      a key-statistic row is kept only when within 5 km/h of the player-match's other family (the point
                    copy if any, else the other aggregates' median); beyond it, the other family's value; a key statistic
                    with no other family is kept
    ks_within3      the same at 3 km/h
    ks_within5_audit  ks_within5, and an uncorroborated key-statistic row is dropped (use False) when it fails one of
                    the input-data audit's rules: average >= maximum, second-serve average >= first, men outside
                    150-235 km/h (women 125-205)
    ks_within5_literal  ks_within5, and every key-statistic row with no other family is dropped (the brief's wording
                    read literally: "a key statistic only when within X km/h of another source")
Writes speed/histories/<rule>.parquet and speed/t3_rules.csv (rows changed or dropped per rule, tour, season, source).
Run: ./python.sh src/eda/source_reconciliation/spd_consensus.py   (after spd_agree.py)
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

OUT = C.OUT / "speed"
HIST = OUT / "histories"
FAMS = ["fam_points", "fam_ks", "fam_ibm_stat", "fam_rg_ks", "fam_ao_mc"]
RULES = ["current", "points_first", "median", "ks_within5", "ks_within3", "ks_within5_audit", "ks_within5_literal"]


def base() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The history and its spd_agree values, aligned. Only a COMPLETE point copy (timed share >= 0.9, covering the box
    score's first serves in to 10%) counts as the point family here: a partial copy can lack a set, and a full-match
    statistic is not overruled by it."""
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    hist = LP.frozen_panel().reset_index(drop=True)
    pr = pd.read_parquet(OUT / "panel_rows.parquet")
    pr = pr.set_index(["match_id", "side"]).reindex(pd.MultiIndex.from_frame(hist[["match_id", "side"]])).reset_index()
    assert len(pr) == len(hist) and (pr["y"].to_numpy() == hist["y"].to_numpy()).all()
    pr["fam_points"] = pr["fam_points"].where(pr["pt_complete"].fillna(False).astype(bool))
    return hist, pr


def other_family(pr: pd.DataFrame) -> pd.Series:
    """For a key-statistic row: the point copy if any, else the median of the other aggregates."""
    agg = pr[["fam_ibm_stat", "fam_rg_ks", "fam_ao_mc"]].median(axis=1, skipna=True)
    return pr["fam_points"].where(pr["fam_points"].notna(), agg)


def apply_rule(rule: str, hist: pd.DataFrame, pr: pd.DataFrame) -> pd.DataFrame:
    h = hist.copy()
    y_mb = pr["y_mb"].to_numpy(float)
    offset = h["y"].to_numpy(float) - y_mb
    v = y_mb.copy()
    use = h["use"].astype(bool).to_numpy().copy()
    ks_row = h["basis"].astype(str).eq("ks").to_numpy()
    if rule == "points_first":
        fp = pr["fam_points"].to_numpy(float)
        v = np.where(np.isfinite(fp), fp, v)
    elif rule == "median":
        cm = pr[FAMS].median(axis=1, skipna=True).to_numpy(float)
        v = np.where(np.isfinite(cm), cm, v)
    elif rule.startswith("ks_within"):
        x = 3.0 if rule == "ks_within3" else 5.0
        oth = other_family(pr).to_numpy(float)
        swap = ks_row & np.isfinite(oth) & (np.abs(y_mb - oth) > x)
        v = np.where(swap, oth, v)
        alone = ks_row & ~np.isfinite(oth)
        if rule == "ks_within5_audit":
            men = h["tour"].eq("atp").to_numpy()
            raw = h["y_raw"].to_numpy(float)
            bad = ((raw >= h["spd_max"].to_numpy(float)) | (h["spd2_raw"].to_numpy(float) >= raw)
                   | np.where(men, (raw < 150) | (raw > 235), (raw < 125) | (raw > 205)))
            use &= ~(alone & bad)
        if rule == "ks_within5_literal":
            use &= ~alone
    elif rule != "current":
        raise ValueError(rule)
    h["y"] = v + offset
    h["use"] = use
    h["consensus_rule"] = rule
    return h


def changes(rule: str, hist: pd.DataFrame, h: pd.DataFrame) -> pd.DataFrame:
    d = (h["y"] - hist["y"]).abs()
    ch = d > 1e-9
    dropped = hist["use"].astype(bool) & ~h["use"].astype(bool)
    rows = []
    for (tour, year, src), g in hist.assign(ch=ch, d=d, dropped=dropped).groupby(["tour", "year", "source"]):
        rows.append({"rule": rule, "tour": tour, "year": int(year), "panel_source": src, "rows": int(len(g)),
                     "use_rows": int(g["use"].sum()), "changed": int(g["ch"].sum()),
                     "changed_beyond_1": int((g["d"] > 1).sum()), "changed_beyond_5": int((g["d"] > 5).sum()),
                     "dropped": int(g["dropped"].sum()), "mean_abs_change_changed": g.loc[g["ch"], "d"].mean(),
                     "max_abs_change": g["d"].max()})
    return pd.DataFrame(rows)


def main() -> int:
    hist, pr = base()
    HIST.mkdir(parents=True, exist_ok=True)
    out = []
    for rule in RULES:
        h = apply_rule(rule, hist, pr)
        h.to_parquet(HIST / f"{rule}.parquet", index=False)
        c = changes(rule, hist, h)
        out.append(c)
        print(f"{rule:20s} changed {int(c['changed'].sum()):6d} (beyond 5 km/h {int(c['changed_beyond_5'].sum()):5d}) "
              f"dropped {int(c['dropped'].sum()):6d}")
    pd.concat(out, ignore_index=True).to_csv(OUT / "t3_rules.csv", index=False, float_format="%.4f")
    return 0


if __name__ == "__main__":
    sys.exit(main())
