"""Task 1: the convention. What P9's MatchBeats rally counts (tm1Rally + tm2Rally) count, checked three ways, and how
they map onto the shot-level study's convention (a point's rally length counts the serve as shot 1 and the shot that
ended it: an ace 1, a double fault 0, a return error 2).

    A. Inside P9, point by point: the counts and the endings against the rally-analysis files' category (the shot the
       point ended on: "Serve", "Return", "3rd shot" ... "9+ odd shots", "10+ even shots") on the same points; the
       newer recount (tm1Shot + tm2Shot) against the same category; the parity of every count (the last ball in must be
       the point winner's); what the files' "rally length known" flag covers, match by match.
    B. Against the earlier sources, on the Stage 0 matches two sources hold: P9 against SirGenkii (the same ATP files,
       Jan-Apr 2025), TDI (mid-2026), the Hugging Face Infosys copy (early 2025) and the volunteer charts; and the AO /
       RG Infosys files against the charts. Points are aligned by their order in the match and a match is kept when the
       two sources agree on the server and the point winner of at least 98% of its points (as the shot-level study's
       Stage 1 did). Rally lengths are compared after mapping P9 to the convention (build_common.mb_convention); where
       one side is Infosys's capped groups, both sides are capped (9 = "9+ odd", 10 = "10+ even").

Reads no match result (point winners only, to align the two sequences).

Run:  ./python.sh src/eda/p9_point_details/build_convention.py     (after build_link.py; a few minutes)
Writes data/studies/p9_point_details/build/convention.json and convention_agreement.csv.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.p9_point_details import build_common as B  # noqa: E402
from src.eda.p9_point_details import build_points as BP  # noqa: E402

PAIRS = [("p9", "sirgenkii"), ("p9", "tdi"), ("p9", "infosys"), ("p9", "mcp"), ("infosys_slams", "mcp"),
         ("tdi", "mcp"), ("sirgenkii", "mcp")]


def inside_p9() -> dict:
    p = B.read_atp_points("p9")
    raw = pd.read_parquet(B.ATP_SOURCES["p9"][0] / "points.parquet",
                          columns=["year", "event_id", "match_id", "pointId", "tm1Shot", "tm2Shot"])
    raw["key"] = "p9|" + raw["year"].astype(str) + "|" + raw["event_id"].astype(str) + "|" + raw["match_id"].astype(str)
    raw["sgp"] = raw["pointId"].astype(str).str.rsplit("_", n=1).str[0]
    raw["new"] = B.num(raw["tm1Shot"]) + B.num(raw["tm2Shot"])
    p = p.merge(raw[["key", "sgp", "new"]].drop_duplicates(["key", "sgp"]), on=["key", "sgp"], how="left")
    c = B.mb_convention(p)
    out = {}
    known = c["tracked"] & c["old"].between(0, B.MAX_COUNT)
    k = c[known & (c["ra_shot"] > 0)].copy()
    # A1: predicted category from the count and the ending (standard rule), capped as the categories are
    pred = np.select([k["result"].eq("A"), k["result"].eq("DF"), k["result"].eq("W"), k["result"].isin(["FE", "UE"])],
                     [1, 1, k["old"], k["old"] + 1], -1).astype("int64")
    pred_c = B.capped(np.maximum(pred, 0))
    rows = {}
    for res, g in k.assign(pred_c=pred_c).groupby("result"):
        rows[res] = {"points": int(len(g)), "count_rule_equals_category": float((g["pred_c"] == g["ra_shot"]).mean())}
    out["A1_count_and_ending_vs_rally_file_category"] = rows
    out["A1_rule"] = ("ace: category 'Serve' (shot 1), count 0; double fault: category 'Serve', count 0 (convention 0); "
                      "winner: category = count; forced or unforced error: category = count + 1")
    # A2: the newer recount against the same categories, on rally-ended points
    if "new" in c:
        re_ = k[k["result"].isin(["W", "FE", "UE"])]
        newc = B.capped(np.clip(re_["new"].fillna(-1).to_numpy(), 0, None).astype("int64"))
        oldc = B.capped(np.select([re_["result"].eq("W")], [re_["old"]], re_["old"] + 1).astype("int64"))
        out["A2_recount_vs_category"] = {
            "points": int(len(re_)), "recount_equals_category": float((newc == re_["ra_shot"]).mean()),
            "old_rule_equals_category": float((oldc == re_["ra_shot"]).mean()),
            "by_result": {r: {"recount": float((newc[m] == re_["ra_shot"].to_numpy()[m]).mean()),
                              "old_rule": float((oldc[m] == re_["ra_shot"].to_numpy()[m]).mean())}
                          for r in ("W", "FE", "UE") for m in [re_["result"].eq(r).to_numpy()]}}
        miss = ~known & ~c["result"].isin(["A", "DF"])
        filled = miss & c["new"].fillna(0).gt(0)
        out["A2_recount_where_count_missing"] = {
            "points_missing_count": int(miss.sum()), "recount_positive": int(filled.sum()),
            "double_faults_given_1": int((~known & c["result"].eq("DF") & c["new"].fillna(0).eq(1)).sum())}
    # A3: unclassified endings resolved by the rally file's list
    nres = c[c["how"].eq("mb_list")]
    out["A3_unclassified_resolved_by_list"] = {"points": int(len(nres)),
                                               "equals_category": float((B.capped(nres["rally"].to_numpy())
                                                                         == nres["ra_shot"]).mean()) if len(nres) else None}
    # A4: what the flag covers, match by match
    rp = ~c["result"].isin(["A", "DF"])
    share_flag = (known & rp).groupby(c["key"]).sum() / rp.groupby(c["key"]).sum().replace(0, np.nan)
    share_valid = ((c["rally"] >= 1) & rp).groupby(c["key"]).sum() / rp.groupby(c["key"]).sum().replace(0, np.nan)
    m = B.read_atp_matches("p9").set_index("key")
    grp = np.where(m["series"].eq("ch"), "CH", m["level_src"].astype(str))
    t = pd.DataFrame({"grp": grp, "draw": m["draw"].to_numpy()}, index=m.index).join(
        share_flag.rename("flag")).join(share_valid.rename("valid"))
    bins = [-0.01, 0, 0.1, 0.5, 0.9, 1.0]
    out["A4_matches_by_flagged_share"] = {f"{g}|{d}": pd.cut(x["flag"], bins).value_counts().sort_index()
                                          .rename(str).to_dict() for (g, d), x in t.groupby(["grp", "draw"])}
    out["A4_matches_carrying_rally_length_gate_0.9"] = {f"{g}|{d}": {"matches": int(len(x)),
                                                                      "carrying": int(x["valid"].ge(B.GATE).sum())}
                                                        for (g, d), x in t.groupby(["grp", "draw"])}
    tr = c[known & rp]
    lo = tr.join(t["flag"], on="key")
    lo["band"] = pd.cut(lo["flag"], [-0.01, 0.5, 0.9, 1.0], labels=["<=0.5", "0.5-0.9", ">0.9"])
    oi = lo["old"].astype("int64")
    lo["parity"] = np.where(oi % 2 == 1, lo["server"], 3 - lo["server"]) == lo["scorer"]
    out["A4_flagged_rally_points_by_match_band"] = {
        str(b): {"points": int(len(g)), "count_0": float(g["old"].eq(0).mean()), "count_1": float(g["old"].eq(1).mean()),
                 "parity_ok_count_ge_1": float(g.loc[g["old"] >= 1, "parity"].mean())}
        for b, g in lo.groupby("band", observed=True)}
    out["how"] = c["how"].value_counts().to_dict()
    rules = B.event_rules(p)
    out["event_rules"] = rules["rule"].value_counts().to_dict()
    out["inclusive_events"] = rules.loc[rules["rule"].eq("inclusive"), "event"].tolist()
    return out


def source_points(source: str, links: pd.DataFrame, s0: pd.DataFrame, matches: set) -> pd.DataFrame:
    lk = links[links["source"].eq(source) & links["match_id_s0"].isin(matches)]
    keys = set(lk["key"])
    p = BP.atp_points(source) if source in B.ATP_SOURCES else BP.shot_level_points(source, keys)
    p = p[p["key"].isin(keys)]
    g = B.match_gate(p["key"], p["rally"], p["end"])
    p = p[p["key"].isin(set(g.loc[g["carries"], "key"]))]
    o = BP.orient(p, lk, s0)
    o["seq"] = o.groupby("match_id").cumcount()
    return o[["match_id", "seq", "server_id", "winner_id", "rally", "end"]]


def compare(a: pd.DataFrame, b: pd.DataFrame, na: str, nb: str) -> dict:
    both = np.intersect1d(a["match_id"].unique(), b["match_id"].unique())
    m = a[a["match_id"].isin(both)].merge(b[b["match_id"].isin(both)], on=["match_id", "seq"], suffixes=("_a", "_b"))
    agree = m["server_id_a"].eq(m["server_id_b"]) & m["winner_id_a"].eq(m["winner_id_b"])
    ok = agree.groupby(m["match_id"]).mean()
    good = ok[ok >= 0.98].index
    m = m[m["match_id"].isin(good)]
    out = {"pair": f"{na} | {nb}", "matches_both_carry": int(len(both)), "matches_aligned": int(len(good)),
           "points": int(len(m))}
    r = m[(m["rally_a"] >= 0) & (m["rally_b"] >= 0)]
    if len(r) == 0:
        return out
    capped = na in B.CAPPED_SOURCES or nb in B.CAPPED_SOURCES
    ra = B.capped(r["rally_a"].to_numpy()) if capped else r["rally_a"].to_numpy()
    rb = B.capped(r["rally_b"].to_numpy()) if capped else r["rally_b"].to_numpy()
    d = ra - rb
    out.update({"compared_capped": bool(capped), "rally_points": int(len(r)), "rally_equal": float((d == 0).mean()),
                "rally_within_1": float((np.abs(d) <= 1).mean()), "rally_mean_diff_a_minus_b": float(d.mean()),
                "band_equal": float((B.band_of(ra) == B.band_of(rb)).mean()),
                "same_side_of_5": float(((ra >= 5) == (rb >= 5)).mean()),
                "same_side_of_9": float(((ra >= 9) == (rb >= 9)).mean()),
                "rally_points_excl_ace_df": int(((r["end_a"].isin([1, 2])) | (r["end_b"].isin([1, 2]))).eq(False).sum())})
    nd = ~(r["end_a"].isin([1, 2]) | r["end_b"].isin([1, 2])).to_numpy()
    if nd.any():
        out["rally_equal_excl_ace_df"] = float((d[nd] == 0).mean())
        out["band_equal_excl_ace_df"] = float((B.band_of(ra[nd]) == B.band_of(rb[nd])).mean())
    return out


def main() -> int:
    res = {"inside_p9": inside_p9()}
    B.log("inside P9 done")
    links = pd.read_parquet(B.OUT / "links.parquet")
    links = links[links["match_id_s0"].notna()]
    s0 = B.stage0_men(["player_a_id", "player_b_id"], 2018)[["match_id", "player_a_id", "player_b_id"]]
    need = sorted({s for pr in PAIRS for s in pr})
    by_src = {s: set(links.loc[links["source"].eq(s), "match_id_s0"]) for s in need}
    shared = {s: set() for s in need}
    for a, b in PAIRS:
        common = by_src[a] & by_src[b]
        shared[a] |= common
        shared[b] |= common
    pts = {s: source_points(s, links, s0, shared[s]) for s in need if shared[s]}
    rows = []
    for a, b in PAIRS:
        if a in pts and b in pts:
            r = compare(pts[a], pts[b], a, b)
            rows.append(r)
            B.log(f"{a} | {b}: {r.get('matches_aligned', 0)} aligned, rally equal {r.get('rally_equal')}")
    t = pd.DataFrame(rows)
    t.to_csv(B.OUT / "convention_agreement.csv", index=False)
    res["agreement"] = rows
    B.write_json(B.OUT / "convention.json", res)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(t.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
