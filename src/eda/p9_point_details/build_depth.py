"""Task 4: depth, the stopping rule's number. How much P9 raises each player's 52-week history of points with a known
rally length, on men's matches of 2025-01-01 to 2026-10-18 at tour level (Slams included) and at Challengers, main
draws and qualifying.

The count. A match's points with a known rally length, double faults excluded (a double fault is known from the
ending in every source, measured or not), from one source: the first in build_common.PREFERENCE among the sources that
carry the match's rally length (at least GATE of its points other than aces and double faults with one). With P9:
every source; without P9: every other source. Per player and target match, the counts of the player's own matches in
the 52 weeks before (build_common.window_sums): Stage 0's clock, events with an earlier tournament date within 364
days, plus earlier rounds of the same event. Every level of history counts (a Challenger or ITF match with rally data
counts for a tour-level target).

Reported by level group (Slams; 250s to Finals; Challengers), draw and half-year of the target: the median and quartiles
with and without P9, the ratio (the median of each player-match's ratio, and the ratio of the medians), and the share
of matches where both players have at least 300 and at least 1,000 such points.

The headline (the brief and the lead): the median, over the player-matches of tour-level main draws (Slams included)
and Challenger main draws, of each player's count with P9 over the count without. A player-match with no such point
either way counts as a ratio of 1 (P9 adds nothing); with points only with P9, as infinite. Variants: those rows left
out; the ratio of the medians; the gate at 0.5; the sources' raw "known" flags with no gate (P9's flag counts aces,
double faults and untracked 0/1 counts, build_convention.py).

Run:  ./python.sh src/eda/p9_point_details/build_depth.py      (after build_points.py; about a minute)
Writes data/studies/p9_point_details/build/depth.csv (every cell), depth.json (headline and variants),
depth_rows.parquet (one row per target player-match: the two counts).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.p9_point_details import build_common as B  # noqa: E402

START, END_ = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-10-18")
HISTORY_FROM = pd.Timestamp("2023-12-01")
LEVEL_GROUP = {"GS": "Slams", "FIN": "250s to Finals", "T1000": "250s to Finals", "T500": "250s to Finals",
               "T250": "250s to Finals", "CH": "Challengers"}
STOP_RATIO = 1.5


def match_counts(ms: pd.DataFrame, gate: float, value: str = "known_nondf", raw: bool = False) -> pd.DataFrame:
    """Per Stage 0 match: the count with every source (n_with) and without P9 (n_without)."""
    m = ms.copy()
    m["pref"] = m["source"].map({s: i for i, s in enumerate(B.PREFERENCE)})
    if raw:
        ok = m[value] > 0
    else:
        ok = m["share"].fillna(0).ge(gate) & m["rp"].gt(0)
    c = m[ok].sort_values(["match_id", "pref"])
    w = c.drop_duplicates("match_id").set_index("match_id")[value]
    wo = c[c["source"].ne("p9")].drop_duplicates("match_id").set_index("match_id")[value]
    out = pd.DataFrame({"n_with": w}).join(wo.rename("n_without"), how="outer").fillna(0)
    src = c.drop_duplicates("match_id").set_index("match_id")["source"]
    out["source_with"] = src.reindex(out.index)
    return out


def player_rows() -> pd.DataFrame:
    m = B.stage0_men(["level", "qualifying", "status", "round", "round_order", "tournament_id", "tournament_date"],
                     2023)
    m = m[pd.to_datetime(m["tournament_date"]) >= HISTORY_FROM]
    mp = pd.read_parquet(B.STAGE0_PLAYERS, columns=["match_id", "player_id", "side"])
    r = mp.merge(m, on="match_id", how="inner")
    r["tournament_date"] = pd.to_datetime(r["tournament_date"])
    return r


def summarise(t: pd.DataFrame, a: str = "with_", b: str = "without_") -> dict:
    w, wo = t[a].to_numpy(dtype=float), t[b].to_numpy(dtype=float)
    ratio = np.where(wo > 0, w / np.where(wo > 0, wo, 1), np.where(w > 0, np.inf, 1.0))
    both = t.groupby("match_id").agg(wmin=(a, "min"), womin=(b, "min"))
    q = lambda x, p: float(np.quantile(x, p)) if len(x) else np.nan  # noqa: E731
    nz = ~((w == 0) & (wo == 0))
    med_w, med_wo = q(w, .5), q(wo, .5)
    return {
        "player_matches": int(len(t)), "matches": int(t["match_id"].nunique()),
        "with_q25": q(w, .25), "with_median": med_w, "with_q75": q(w, .75),
        "without_q25": q(wo, .25), "without_median": med_wo, "without_q75": q(wo, .75),
        "median_ratio": q(ratio, .5),
        "median_ratio_excluding_zero_both": q(ratio[nz], .5) if nz.any() else np.nan,
        "ratio_of_medians": (med_w / med_wo) if med_wo > 0 else (np.inf if med_w > 0 else np.nan),
        "ratio_of_means": float(w.mean() / wo.mean()) if wo.mean() > 0 else np.inf,
        "share_zero_without": float((wo == 0).mean()), "share_zero_with": float((w == 0).mean()),
        "share_zero_both": float((~nz).mean()),
        "both_ge_300_with": float(both["wmin"].ge(300).mean()), "both_ge_300_without": float(both["womin"].ge(300).mean()),
        "both_ge_1000_with": float(both["wmin"].ge(1000).mean()),
        "both_ge_1000_without": float(both["womin"].ge(1000).mean()),
    }


def compute(rows: pd.DataFrame, counts: pd.DataFrame) -> pd.DataFrame:
    r = rows.copy()
    r["n_with"] = r["match_id"].map(counts["n_with"]).fillna(0)
    r["n_without"] = r["match_id"].map(counts["n_without"]).fillna(0)
    s = B.window_sums(r, ["n_with", "n_without"])
    r["with_"], r["without_"] = s["n_with"].to_numpy(), s["n_without"].to_numpy()
    return r


def targets(r: pd.DataFrame) -> pd.DataFrame:
    t = r[(r["tournament_date"] >= START) & (r["tournament_date"] <= END_) & r["level"].isin(list(LEVEL_GROUP))
          & r["status"].isin(["completed", "retired"])].copy()
    t["level_group"] = t["level"].map(LEVEL_GROUP)
    t["draw"] = np.where(t["qualifying"].astype(bool), "qual", "main")
    t["half"] = t["tournament_date"].dt.year.astype(str) + np.where(t["tournament_date"].dt.month <= 6, "H1", "H2")
    t["headline_pop"] = t["draw"].eq("main")
    return t


def table(t: pd.DataFrame, variant: str) -> list[dict]:
    rows = []
    for keys, g in [(("all", "all", "all"), t)] + \
            [((lg, "all", "all"), g) for lg, g in t.groupby("level_group")] + \
            [((lg, d, "all"), g) for (lg, d), g in t.groupby(["level_group", "draw"])] + \
            [((lg, d, h), g) for (lg, d, h), g in t.groupby(["level_group", "draw", "half"])] + \
            [(("tour+CH main (headline)", "main", "all"), t[t["headline_pop"]])] + \
            [(("tour+CH main (headline)", "main", h), g) for h, g in t[t["headline_pop"]].groupby("half")] + \
            [(("tour main (Slams + 250s to Finals)", "main", "all"), t[t["headline_pop"] & t["level"].ne("CH")])]:
        rows.append({"variant": variant, "level_group": keys[0], "draw": keys[1], "half": keys[2], **summarise(g)})
    return rows


def main() -> int:
    ms = pd.read_parquet(B.OUT / "match_sources.parquet")
    rows = player_rows()
    B.log(f"player-match rows from {HISTORY_FROM.date()}: {len(rows):,}")
    out, keep = [], None
    variants = {"gate_0.9": dict(gate=B.GATE), "gate_0.5": dict(gate=0.5),
                "raw_flags_no_gate": dict(gate=0.0, value="raw_known", raw=True)}
    for name, kw in variants.items():
        counts = match_counts(ms, **kw)
        r = compute(rows, counts)
        t = targets(r)
        out += table(t, name)
        if name == "gate_0.9":
            keep = t
        B.log(f"{name}: done")
    d = pd.DataFrame(out)
    d.to_csv(B.OUT / "depth.csv", index=False)
    keep[["match_id", "player_id", "side", "tournament_date", "tournament_id", "round", "round_order", "level",
          "level_group", "draw", "half", "with_", "without_"]].rename(
        columns={"with_": "count_with_p9", "without_": "count_without_p9"}).to_parquet(B.OUT / "depth_rows.parquet",
                                                                                         index=False)
    head = d[(d["variant"] == "gate_0.9") & (d["level_group"] == "tour+CH main (headline)") & (d["half"] == "all")]
    h = head.iloc[0].to_dict()
    res = {"clock": "Stage 0's tournament_date and round_order: events with an earlier tournament date within 364 "
                    "days, plus earlier rounds of the same event (build_common.window_sums)",
           "population": "men's Stage 0 matches, tournament date 2025-01-01 to 2026-10-18, completed or retired; the "
                         "headline: tour-level main draws (Slams, Finals, 1000s, 500s, 250s) and Challenger main draws",
           "count": "points with a known rally length, double faults excluded, in matches that carry rally length "
                    "(gate 0.9), one source per match (P9 first)",
           "headline_median_ratio": h["median_ratio"],
           "stopping_rule": f"stop if below {STOP_RATIO}",
           "stops": bool(h["median_ratio"] < STOP_RATIO),
           "headline": h,
           "variants": d[(d["level_group"] == "tour+CH main (headline)") & (d["half"] == "all")].to_dict(
               orient="records")}
    B.write_json(B.OUT / "depth.json", res)
    show = d[(d["variant"] == "gate_0.9") & (d["half"] == "all")][
        ["level_group", "draw", "player_matches", "with_median", "without_median", "median_ratio",
         "median_ratio_excluding_zero_both", "ratio_of_medians", "share_zero_both", "both_ge_300_with",
         "both_ge_300_without"]]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(show.round(3).to_string(index=False))
        print(d[(d["level_group"] == "tour+CH main (headline)") & (d["half"] == "all")][
            ["variant", "median_ratio", "median_ratio_excluding_zero_both", "ratio_of_medians", "with_median",
             "without_median"]].round(3).to_string(index=False))
    B.log(f"HEADLINE median ratio (tour + Challenger main draws): {h['median_ratio']:.3f}; stops: {res['stops']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
