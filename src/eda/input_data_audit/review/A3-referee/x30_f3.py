"""F3: WTA Adelaide 2 2022 carries Adelaide 2021's box scores. Per match: copy or not; the WTA API's own box.
Also F3b's precondition: the WTA API's per-count exact agreement with Sackmann on clean WTA events of 2021-2022.

Writes:
    f3_adelaide2_matches.csv   every Sackmann Adelaide 2 2022 match: box present, equal to an Adelaide 2021 box (which),
                               the WTA API's box for the same match, agreement, checks of the API box
    f3_wta_api_agreement.csv   per count: exact agreement of the WTA API with Sackmann, clean 2021-2022 WTA events
    f3a_scope.csv / f3b_scope.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 60)


def player_rows(r: pd.DataFrame, tour: str = "wta") -> pd.DataFrame:
    out = []
    for side, me, op in (("w", "winner", "loser"), ("l", "loser", "winner")):
        c = rc.raw_counts(r, side)
        d = pd.DataFrame({"_source_file": r["_source_file"], "_row": r["_row"], "tourney_id": r["tourney_id"],
                          "tourney_name": r["tourney_name"], "tourney_date": r["tourney_date"], "round": r["round"],
                          "score": r["score"], "side": side, "pid": f"{tour}:" + r[f"{me}_id"].astype(str),
                          "name": r[f"{me}_name"], "oname": r[f"{op}_name"]})
        out.append(pd.concat([d, c], axis=1))
    o = pd.concat(out, ignore_index=True)
    o["pk"], o["ok"] = rc.keys(o["name"]), rc.keys(o["oname"])
    o["sn"] = o["name"].map(lambda n: max(rc.name_key(n).split(), key=len) if rc.name_key(n) else "")
    o["osn"] = o["oname"].map(lambda n: max(rc.name_key(n).split(), key=len) if rc.name_key(n) else "")
    return o


ALIASES = {  # WTA API name key -> Sackmann name key, for players renamed between the two records (Adelaide 2 2022)
    "alison riske": "alison amritraj riske", "sanders storm": "hunter storm", "smith tina": "nadine smith tina"}


def api_rows() -> pd.DataFrame:
    a = rc.wta_api_totals()
    a["pk"] = a["pk"].replace(ALIASES)
    a["ok"] = a["ok"].replace(ALIASES)
    a["sn"] = a["name"].map(lambda n: max(rc.name_key(n).split(), key=len) if rc.name_key(n) else "")
    a["osn"] = a["oname"].map(lambda n: max(rc.name_key(n).split(), key=len) if rc.name_key(n) else "")
    return a


def join_api(s: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """Sackmann player rows to WTA API player rows: same WTA tournament number and year, same player and opponent
    (full name keys, else surnames)."""
    s = s.copy()
    s["wta_tid"] = s["tourney_id"].astype(str).str.extract(r"^\d{4}-(\d+)$")[0]
    s["year"] = s["tourney_id"].astype(str).str[:4]
    j1 = s.merge(a, left_on=["wta_tid", "year", "pk", "ok"], right_on=["tournament_id", "year", "pk", "ok"],
                 suffixes=("", "_api"))
    rest = s[~s.set_index(["_source_file", "_row", "side"]).index.isin(j1.set_index(["_source_file", "_row", "side"]).index)]
    j2 = rest.merge(a, left_on=["wta_tid", "year", "sn", "osn"], right_on=["tournament_id", "year", "sn", "osn"],
                    suffixes=("", "_api"))
    j = pd.concat([j1, j2], ignore_index=True)
    # one API row per Sackmann row (a pair meeting twice in one event, e.g. qualifying and main, is ambiguous: drop)
    j = j[~j.duplicated(["_source_file", "_row", "side"], keep=False)]
    return j


def main() -> int:
    a = api_rows()
    r22 = pd.read_parquet(rc.SACK / "wta" / "wta_matches_2022.parquet")
    q22 = pd.read_parquet(rc.SACK / "wta" / "wta_matches_qual_itf_2022.parquet")
    r21 = pd.read_parquet(rc.SACK / "wta" / "wta_matches_2021.parquet")
    q21 = pd.read_parquet(rc.SACK / "wta" / "wta_matches_qual_itf_2021.parquet")
    all22 = pd.concat([r22, q22], ignore_index=True)
    all21 = pd.concat([r21, q21], ignore_index=True)
    ad2 = all22[all22["tourney_name"].astype(str).str.contains("Adelaide")]
    print(ad2.groupby(["tourney_id", "tourney_name", "tourney_date"]).size())
    ad1_21 = all21[all21["tourney_name"].astype(str).str.contains("Adelaide")]
    print(ad1_21.groupby(["tourney_id", "tourney_name", "tourney_date"]).size())
    A2 = ad2[ad2["tourney_name"].eq("Adelaide 2")].copy()
    raw16 = [f"{s}_{c}" for s in ("w", "l") for c in ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms",
                                                      "bpSaved", "bpFaced"]]

    def key(df):
        return df[raw16].apply(lambda c: rc.num(c)).fillna(-1).astype(int).astype(str).agg("|".join, axis=1)

    A2["has_raw_box"] = rc.num(A2["w_svpt"]).fillna(0) > 0
    A2["key"] = key(A2)
    src = ad1_21.copy()
    src["key"] = key(src)
    src = src[rc.num(src["w_svpt"]).fillna(0) > 0]
    src_map = src.set_index("key")[["tourney_name", "round", "winner_name", "loser_name", "score"]]
    src_map = src_map[~src_map.index.duplicated()]
    A2["copy_of_2021"] = A2["key"].map(lambda k: " ".join(map(str, src_map.loc[k].tolist())) if k in src_map.index else "")
    # also: equal to ANY earlier Sackmann WTA row (2019-2021)?
    older = pd.concat([pd.read_parquet(rc.SACK / "wta" / f"wta_matches_{y}.parquet") for y in (2019, 2020, 2021)]
                      + [pd.read_parquet(rc.SACK / "wta" / f"wta_matches_qual_itf_{y}.parquet") for y in (2019, 2020, 2021)],
                      ignore_index=True)
    older = older[rc.num(older["w_svpt"]).fillna(0) > 0]
    older_keys = set(key(older))
    A2["equals_an_earlier_row"] = A2["key"].isin(older_keys)
    # WTA API for these matches
    pr = player_rows(A2)
    j = join_api(pr, a)
    for b in rc.BOX:
        j[f"eq_{b}"] = j[b].eq(j[f"api_{b}"])
    j["eq_n"] = j[[f"eq_{b}" for b in rc.BOX]].sum(axis=1)
    per_match = j.groupby(["_source_file", "_row"]).agg(api_rows=("eq_n", "size"), api_eq_counts=("eq_n", "sum"))
    A2 = A2.merge(per_match, left_on=["_source_file", "_row"], right_index=True, how="left")
    # Stage 0 rows
    m, p = rc.stage0()
    s0 = m[m["source_file"].isin(A2["_source_file"].unique())][["match_id", "source_file", "source_row", "has_box",
                                                                 "box_status", "score", "status", "status_detail"]]
    A2 = A2.merge(s0.rename(columns={"source_file": "_source_file", "source_row": "_row", "score": "s0_score"}),
                  on=["_source_file", "_row"], how="left")
    # API box checks (as Stage 0 would run them), per match with both players held
    jj = j.copy()
    api_box = {}
    for (f, rr), g in jj.groupby(["_source_file", "_row"]):
        if len(g) != 2:
            continue
        gw, gl = g[g["side"] == "w"].iloc[0], g[g["side"] == "l"].iloc[0]
        api_box[(f, rr)] = ({b: gw[f"api_{b}"] for b in rc.BOX}, {b: gl[f"api_{b}"] for b in rc.BOX})
    chk = []
    for _, r in A2.iterrows():
        k = (r["_source_file"], r["_row"])
        if k not in api_box:
            chk.append({"api_box_held": False})
            continue
        w, l_ = api_box[k]
        allzero = all((v == 0) for v in list(w.values()) + list(l_.values()))
        c = rc.box_checks(pd.DataFrame([w]), pd.DataFrame([l_]), pd.Series([r["s0_score"]]), pd.Series([r["status"]]),
                          pd.Series([r["status_detail"]]))
        chk.append({"api_box_held": not allzero, "api_box_passes_B0_B9": bool(c["has_box"][0]) and not allzero,
                    **{f"api_w_{b}": w[b] for b in rc.BOX}, **{f"api_l_{b}": l_[b] for b in rc.BOX}})
    A2 = pd.concat([A2.reset_index(drop=True), pd.DataFrame(chk)], axis=1)
    cols = ["match_id", "_source_file", "_row", "round", "winner_name", "loser_name", "score", "has_raw_box",
            "copy_of_2021", "equals_an_earlier_row", "has_box", "box_status", "api_rows", "api_eq_counts",
            "api_box_held", "api_box_passes_B0_B9"] + [f"api_{s}_{b}" for s in ("w", "l") for b in rc.BOX] \
        + [f"{s}_{c}" for s in ("w", "l") for c in ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms",
                                                     "bpSaved", "bpFaced"]]
    A2[cols].to_csv(rc.OUT / "f3_adelaide2_matches.csv", index=False)
    print(A2[["round", "winner_name", "loser_name", "score", "has_raw_box", "copy_of_2021", "has_box", "api_rows",
              "api_eq_counts", "api_box_held", "api_box_passes_B0_B9"]].to_string())
    print("Adelaide 2 2022 matches:", len(A2), "with a raw box:", int(A2["has_raw_box"].sum()),
          "equal to an Adelaide 2021 box:", int(A2["copy_of_2021"].ne("").sum()),
          "equal to any 2019-21 row:", int(A2["equals_an_earlier_row"].sum()))

    # ---------------- F3b precondition: WTA API vs Sackmann on clean 2021-2022 WTA events
    raw = []
    for y in (2021, 2022):
        for f in (f"wta_matches_{y}.parquet", f"wta_matches_qual_itf_{y}.parquet"):
            t = pd.read_parquet(rc.SACK / "wta" / f)
            raw.append(t)
    raw = pd.concat(raw, ignore_index=True)
    raw = raw[rc.num(raw["w_svpt"]).fillna(0) > 0]
    bad_tid = {"2021-2028", "2021-2027"}            # Abu Dhabi 2021, Phillip Island 2021 (F2 clusters)
    raw = raw[~raw["tourney_id"].astype(str).isin(bad_tid) & ~raw["tourney_name"].eq("Adelaide 2")]
    swapped = pd.read_csv(rc.OUT / "f2_matches.csv")
    pr = player_rows(raw)
    pr = pr[~pr["_row"].astype(str).add("|").add(pr["_source_file"]).isin(
        swapped["_row"].astype(str).add("|").add(swapped["_source_file"]))]
    j = join_api(pr, a)
    print(f"\nclean 2021-22 Sackmann WTA player rows with a box: {len(pr):,}; joined to the WTA API: {len(j):,}")
    zero = j[[f"api_{b}" for b in rc.BOX]].fillna(0).eq(0).all(axis=1)
    print("API rows all zero (no statistics):", int(zero.sum()))
    j = j[~zero]
    rows = []
    for b in rc.BOX:
        eq = j[b].eq(j[f"api_{b}"])
        rows.append({"count": b, "rows": int(j[b].notna().sum()), "exact_equal": round(float(eq.mean()), 4),
                     "within_1": round(float((j[b] - j[f"api_{b}"]).abs().le(1).mean()), 4),
                     "mean_diff_sackmann_minus_api": round(float((j[b] - j[f"api_{b}"]).mean()), 3)})
    ag = pd.DataFrame(rows)
    allnine = j[[b for b in rc.BOX]].values == j[[f"api_{b}" for b in rc.BOX]].values
    ag = pd.concat([ag, pd.DataFrame([{"count": "all nine", "rows": len(j),
                                       "exact_equal": round(float(allnine.all(axis=1).mean()), 4)}])])
    eight = [b for b in rc.BOX if b != "sv_gms"]
    e8 = (j[eight].values == j[[f"api_{b}" for b in eight]].values).all(axis=1)
    ag = pd.concat([ag, pd.DataFrame([{"count": "eight (no sv_gms)", "rows": len(j), "exact_equal": round(float(e8.mean()), 4)}])])
    # by event: share of player rows equal on all nine
    j["all9"] = allnine.all(axis=1)
    by_ev = j.groupby(["tourney_id", "tourney_name"]).agg(rows=("all9", "size"), all9=("all9", "mean")).sort_values("all9")
    ag.to_csv(rc.OUT / "f3_wta_api_agreement.csv", index=False)
    by_ev.to_csv(rc.OUT / "f3_wta_api_agreement_by_event.csv")
    print(ag.to_string(index=False))
    print("\nevents with the lowest all-nine agreement:")
    print(by_ev.head(25).to_string())
    print("\ndistribution of event all-nine agreement:", by_ev["all9"].describe().round(3).to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
