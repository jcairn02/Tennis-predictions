"""Aggregate tables of the ATP-official readers (box/atp_*.csv), for REPORT_atp.md. Aggregates only (counts, shares,
means) and ids; per-match rows stay in the readers' parquet files.

    atp_coverage.csv            Q1: Stage 0 men's matches each reader covers, by season and level group (Stage 0's), with
                                the complete ones; 'any_atp_official' is their union
    atp_recount_vs_box.csv      Q2 (and Q3's TDI half): each recount against its own system's box score, per count, on
                                the same match (complete recounts of matches the box marks complete), all seasons and by
                                season
    atp_recount_vs_box_diffs.csv  the differences' distribution per pair and count (recount minus box)
    atp_svgms_tiebreaks.csv     service games: is a recount-box difference the tiebreaks (a definitional difference)?
    atp_mantd_vs_keystats.csv   Q3: ManTennisData against each copy of the Infosys key statistics, joined on the ATP's
                                own match key (year_event_CODE) and player code (no Stage 0 link needed), per count and
                                season
    atp_events_disagree.csv     Q4: events (season, ATP event) where two official records of the same matches disagree
                                more than usual: rows, the share of player rows with any count different, the worst count
    atp_vs_stage0.csv           the readers' sanity check against Stage 0 (complete rows), per count, season and level
                                group (not the study's comparison: Stage 0 is not a referee)

Run: ./python.sh src/eda/source_reconciliation/atp_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import atp_common as A  # noqa: E402

READERS = ["atp_ks_handoff", "atp_mb_handoff_recount", "atp_ks_backfill", "atp_backfill_recount", "atp_ch_recount",
           "atp_ks_sirgenkii", "atp_sirgenkii_recount", "atp_ks_daily", "atp_tdi_stats", "atp_tdi_recount",
           "atp_mantennisdata"]
COUNTS = A.COUNTS + ["sv_won"]
PAIRS = [("atp_mb_handoff_recount", "atp_ks_handoff", "source_key"),
         ("atp_backfill_recount", "atp_ks_backfill", "source_key"),
         ("atp_ch_recount", "atp_ks_handoff", "source_key"),
         ("atp_ch_recount", "atp_mantennisdata", "match"),
         ("atp_sirgenkii_recount", "atp_ks_sirgenkii", "source_key"),
         ("atp_tdi_recount", "atp_tdi_stats", "source_key")]
KS_COPIES = ["atp_ks_handoff", "atp_ks_backfill", "atp_ks_sirgenkii", "atp_ks_daily"]


def load(name: str) -> pd.DataFrame:
    r = pd.read_parquet(A.READERS / f"{name}.parquet")
    s = A.s0_men().set_index("match_id")
    r["year"] = r["match_id"].map(s["year"])
    r["level_group"] = r["match_id"].map(s["level_group"])
    r["qual_level"] = r["match_id"].map(s["qual_level"])
    r["level"] = r["match_id"].map(s["level"])
    r["season_ev"] = r["match_id"].map(s["season"]).astype("Int64").astype(str) + "-" + \
        r["match_id"].map(s["ev"]).astype("Int64").astype(str)
    r["tournament_name"] = r["match_id"].map(s["tournament_name"])
    return r


def coverage(data: dict) -> pd.DataFrame:
    s = A.s0_men()
    s = s[s["year"].between(2015, 2026)]
    base = s.groupby(["year", "level_group", "qual_level"]).agg(stage0_matches=("match_id", "size"),
                                                                stage0_with_box=("has_box", "sum")).reset_index()
    rows = []
    union, union_rc = {}, {}
    for name, r in data.items():
        m = r.dropna(subset=["match_id"]).groupby("match_id")["complete"].all()
        is_rc = (r["kind"] == "recount").all()
        for mid, c in m.items():
            union[mid] = union.get(mid, False) or bool(c)
            if is_rc:
                union_rc[mid] = union_rc.get(mid, False) or bool(c)
        f = s[s["match_id"].isin(m.index)].assign(complete=lambda d: d["match_id"].map(m))
        g = f.groupby(["year", "level_group", "qual_level"]).agg(covered=("match_id", "size"),
                                                                 covered_complete=("complete", "sum")).reset_index()
        rows.append(base.merge(g, on=["year", "level_group", "qual_level"], how="left").assign(reader=name))
    for label, un in (("any_atp_official", union), ("any_atp_recount", union_rc)):
        u = pd.Series(un, dtype=bool)
        f = s[s["match_id"].isin(u.index)].assign(complete=lambda d: d["match_id"].map(u))
        g = f.groupby(["year", "level_group", "qual_level"]).agg(covered=("match_id", "size"),
                                                                 covered_complete=("complete", "sum")).reset_index()
        rows.append(base.merge(g, on=["year", "level_group", "qual_level"], how="left").assign(reader=label))
    out = pd.concat(rows, ignore_index=True)
    out[["covered", "covered_complete"]] = out[["covered", "covered_complete"]].fillna(0).astype(int)
    out["share_of_stage0"] = (out["covered"] / out["stage0_matches"]).round(4)
    out["share_complete_of_stage0"] = (out["covered_complete"] / out["stage0_matches"]).round(4)
    return out[["reader", "year", "level_group", "qual_level", "stage0_matches", "stage0_with_box", "covered",
                "covered_complete", "share_of_stage0", "share_complete_of_stage0"]]


def compare(a: pd.DataFrame, b: pd.DataFrame, on: list[str], by: list[str] | None, label: dict) -> pd.DataFrame:
    """Per count: rows where both hold a value, equal share, mean difference (a minus b), share within 1."""
    j = a.merge(b, on=on, suffixes=("_a", "_b"))
    groups = [((), j)] if not by else list(j.groupby(by))
    rows = []
    for key, g in groups:
        key = key if isinstance(key, tuple) else (key,)
        for c in COUNTS:
            if f"{c}_a" not in g or f"{c}_b" not in g:
                continue
            both = g[f"{c}_a"].notna() & g[f"{c}_b"].notna()
            n = int(both.sum())
            if not n:
                continue
            d = g.loc[both, f"{c}_a"] - g.loc[both, f"{c}_b"]
            row = dict(label, count=c, n=n, equal=round(float((d == 0).mean()), 5),
                       mean_diff=round(float(d.mean()), 4), within_1=round(float((d.abs() <= 1).mean()), 5))
            for k, v in zip(by or [], key):
                row[k] = v
            rows.append(row)
    return pd.DataFrame(rows)


def recount_vs_box(data: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    out, diffs, svg = [], [], []
    for rc, bx, how in PAIRS:
        a = data[rc][data[rc]["complete"].astype(bool)].copy()
        b = data[bx][data[bx]["complete"].astype(bool)].copy()
        on = ["source_key", "x_player_no"] if how == "source_key" else ["match_id", "player_id"]
        keep_a = on + COUNTS + ["year", "x_tb_first", "x_tb_played", "season_ev", "tournament_name", "level_group"]
        a = a[[c for c in keep_a if c in a]]
        b = b[on + COUNTS]
        if how == "match":
            a = a.dropna(subset=["match_id", "player_id"])
            b = b.dropna(subset=["match_id", "player_id"]).drop_duplicates(on)
        lab = {"recount": rc, "box": bx, "joined_on": "+".join(on)}
        out.append(compare(a, b, on, None, dict(lab, scope="all seasons")))
        out.append(compare(a, b, on, ["year"], dict(lab, scope="by season")))
        j = a.merge(b, on=on, suffixes=("_a", "_b"))
        for c in COUNTS:
            d = (j[f"{c}_a"] - j[f"{c}_b"]).dropna()
            vc = d.value_counts().sort_index()
            for v, n in vc.items():
                diffs.append(dict(lab, count=c, diff=float(v), rows=int(n)))
        # service games and tiebreaks
        d = j["sv_gms_a"] - j["sv_gms_b"]
        ok = d.notna()
        if ok.any() and "x_tb_first" in j:
            svg.append(dict(lab, rows=int(ok.sum()), equal=int((d[ok] == 0).sum()),
                            box_minus_recount_equals_tiebreaks_served_first=int(
                                ((-d[ok]) == j.loc[ok, "x_tb_first"]).sum() - ((d[ok] == 0) & (j.loc[ok, "x_tb_first"]
                                                                                              == 0)).sum()),
                            box_minus_recount_equals_tiebreaks_played=int(
                                ((-d[ok]) == j.loc[ok, "x_tb_played"]).sum() - ((d[ok] == 0) & (j.loc[ok, "x_tb_played"]
                                                                                               == 0)).sum()),
                            differ_without_tiebreaks=int(((d[ok] != 0) & (j.loc[ok, "x_tb_played"] == 0)).sum()),
                            rows_with_tiebreaks=int((j.loc[ok, "x_tb_played"] > 0).sum()),
                            equal_among_rows_with_tiebreaks=int(((d[ok] == 0) & (j.loc[ok, "x_tb_played"] > 0)).sum())))
    return pd.concat(out, ignore_index=True), pd.DataFrame(diffs), pd.DataFrame(svg)


def mantd_vs_keystats(data: dict) -> tuple[pd.DataFrame, list]:
    mt = data["atp_mantennisdata"].dropna(subset=["x_atp_key"]).copy()
    mt["k"] = mt["x_atp_key"] + "|" + mt["x_code"].astype(str)
    mt = mt.drop_duplicates("k")
    out, joined = [], []
    for ks in KS_COPIES:
        b = data[ks].copy()
        b["k"] = b["source_key"] + "|" + b["x_code"].astype(str)
        lab = {"mantennisdata": "atp_mantennisdata", "keystats": ks, "joined_on": "ATP key + player code"}
        a = mt[["k"] + COUNTS + ["year", "x_season"]]
        bb = b[["k"] + COUNTS + ["season_ev", "tournament_name", "level_group"]]
        out.append(compare(a, bb, ["k"], None, dict(lab, scope="all seasons")))
        out.append(compare(a, bb, ["k"], ["x_season"], dict(lab, scope="by season")))
        j = a.merge(bb, on="k", suffixes=("_a", "_b"))
        j["copy"] = ks
        joined.append(j)
    return pd.concat(out, ignore_index=True), joined


def events_disagree(frames: list[tuple[str, pd.DataFrame]], min_rows: int = 20) -> pd.DataFrame:
    rows = []
    for label, j in frames:
        cols = [c for c in COUNTS if f"{c}_a" in j and f"{c}_b" in j]
        diff = pd.DataFrame({c: (j[f"{c}_a"] != j[f"{c}_b"]) & j[f"{c}_a"].notna() & j[f"{c}_b"].notna()
                             for c in cols})
        j = j.assign(any_diff=diff.any(axis=1))
        overall = float(j["any_diff"].mean()) if len(j) else np.nan
        for (ev, tname, lg), g in j.groupby(["season_ev", "tournament_name", "level_group"], dropna=False):
            if len(g) < min_rows:
                continue
            per = diff.loc[g.index].mean()
            rows.append({"comparison": label, "season_event": ev, "tournament_name": tname, "level_group": lg,
                         "player_rows": int(len(g)), "share_any_count_differs": round(float(g["any_diff"].mean()), 4),
                         "comparison_overall_share": round(overall, 4), "worst_count": per.idxmax(),
                         "worst_count_share_differs": round(float(per.max()), 4)})
    out = pd.DataFrame(rows)
    return out.sort_values(["comparison", "share_any_count_differs"], ascending=[True, False])


def vs_stage0(data: dict) -> pd.DataFrame:
    p = A.s0_players()[["match_id", "player_id"] + A.COUNTS]
    out = []
    for name, r in data.items():
        a = r[r["complete"].astype(bool)].dropna(subset=["match_id", "player_id"])
        a = a[["match_id", "player_id", "year", "level_group"] + A.COUNTS].drop_duplicates(["match_id", "player_id"])
        out.append(compare(a.rename(columns={}), p, ["match_id", "player_id"], ["year", "level_group"],
                           {"reader": name}))
    return pd.concat(out, ignore_index=True)


def main() -> int:
    data = {n: load(n) for n in READERS}
    cov = coverage(data)
    cov.to_csv(A.BOX / "atp_coverage.csv", index=False)
    rvb, diffs, svg = recount_vs_box(data)
    rvb.to_csv(A.BOX / "atp_recount_vs_box.csv", index=False)
    diffs.to_csv(A.BOX / "atp_recount_vs_box_diffs.csv", index=False)
    svg.to_csv(A.BOX / "atp_svgms_tiebreaks.csv", index=False)
    mvk, joined = mantd_vs_keystats(data)
    mvk.to_csv(A.BOX / "atp_mantd_vs_keystats.csv", index=False)
    # Q4: events where two official records disagree
    frames = [(f"atp_mantennisdata vs {j['copy'].iloc[0]}", j) for j in joined if len(j)]
    for rc, bx, how in PAIRS:
        if how != "source_key":
            continue
        a = data[rc][data[rc]["complete"].astype(bool)]
        b = data[bx][data[bx]["complete"].astype(bool)]
        j = a.merge(b[["source_key", "x_player_no"] + COUNTS], on=["source_key", "x_player_no"],
                    suffixes=("_a", "_b"))
        frames.append((f"{rc} vs {bx}", j))
    ev = events_disagree(frames)
    ev.to_csv(A.BOX / "atp_events_disagree.csv", index=False)
    vs0 = vs_stage0(data)
    vs0.to_csv(A.BOX / "atp_vs_stage0.csv", index=False)
    print("wrote", ", ".join(f"atp_{x}.csv" for x in ("coverage", "recount_vs_box", "recount_vs_box_diffs",
                                                         "svgms_tiebreaks", "mantd_vs_keystats", "events_disagree",
                                                         "vs_stage0")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
