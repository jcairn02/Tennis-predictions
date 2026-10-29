"""Task 2's links: every rally source's matches to today's Stage 0 match, with which source player is Stage 0's side A.

ATP-format files (P9 = infosys_atp_recent, infosys_atp, infosys_challengers, infosys_slams). Their matches carry the
ATP's player codes, the ATP event id, the draw and, for main draws, the round of the match code, but no match date.
Each is linked inside its own event (Stage 0's tournament id, without the date suffix Stage 0 adds when an id names two
events) and draw:
    1. names: both surnames (the data map's surname key), with compatible first names, unique in the event and draw
       (the round decides between two); a looser pass (one surname key and the other the data map's same_player);
    2. a crosswalk ATP code -> Stage 0 player id, learned from the strict name links' votes (a code takes the id that
       holds at least 80% of its votes), with two existing crosswalks as fallback for codes no name link reached
       (the live speed linker's cache and the source reconciliation's, both read only);
    3. ids: the match of the event and draw with the same two crosswalked ids (unique; the round decides between two);
       for events Stage 0 lacks, the same two ids within 7 days of the event's first day (P9 only: it has the date).
A link needs the name pass and the id pass to agree, or one of them alone; where they point to different matches the
row is left unlinked ('conflict'). Nothing is guessed: no candidate, two equal candidates or a conflict leave it out.

The shot-level study's sources (infosys = the Hugging Face copy, sirgenkii, slamtracker, slam_pbp, slam_tracking, mcp)
keep that study's links (stage0_source_matches.parquet, 2 Oct 2026), carried to today's ids by the rebuilds' id maps;
the rows it left unlinked (men, 2018 on) are linked again to today's Stage 0 by the same linker (shot_level common
Stage0Linker). TDI's dump was refreshed on 26 Oct 2026, so TDI is read again with the shot-level reader and linked anew.

Checks (no result read): the round of main-draw links; each player's aces in the points against Stage 0's box score,
in the link's orientation and swapped.

Run:  ./python.sh src/eda/p9_point_details/build_link.py      (a few minutes)
Writes data/studies/p9_point_details/build/: links.parquet (one row per source match), crosswalk.parquet,
link_report.json, link_failures.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.data_map import measure as M  # noqa: E402
from src.eda.p9_point_details import build_common as B  # noqa: E402

XW_MIN_SHARE = 0.8
WINDOW_DAYS = 7
EXTERNAL_XW = {
    "live_speed": ROOT / "data" / "studies" / "serve_speed_tabpfn" / "live" / "crosswalk.parquet",
    "source_reconciliation": ROOT / "data" / "studies" / "source_reconciliation" / "box" / "atp_crosswalk.parquet",
}


def stage0_frame(from_year: int = 2017) -> pd.DataFrame:
    m = B.stage0_men(["level", "qualifying", "round", "round_order", "tournament_id", "tournament_name",
                      "tournament_date", "player_a_id", "player_b_id", "status"], from_year)
    m["tidp"] = B.tid_prefix(m["tournament_id"])
    m["draw"] = np.where(m["qualifying"], "qual", "main")
    nm = B.stage0_names(m["match_id"]).drop_duplicates(["match_id", "player_id"])
    names = nm.set_index(["match_id", "player_id"])["player_name"]
    m["name_a"] = names.reindex(pd.MultiIndex.from_arrays([m["match_id"], m["player_a_id"]])).to_numpy()
    m["name_b"] = names.reindex(pd.MultiIndex.from_arrays([m["match_id"], m["player_b_id"]])).to_numpy()
    m["ka"], m["kb"] = m["name_a"].map(M.surname_key), m["name_b"].map(M.surname_key)
    m["plo"] = np.minimum(m["player_a_id"], m["player_b_id"])
    m["phi"] = np.maximum(m["player_a_id"], m["player_b_id"])
    return m


def _pick(c: pd.DataFrame, score: str, out_cols: list[str]) -> tuple[pd.DataFrame, pd.Index]:
    """The best candidate per source key by (score, round_ok); keys whose best two tie are ambiguous."""
    c = c.sort_values(["key", score, "round_ok", "match_id"], ascending=[True, False, False, True])
    top = c.drop_duplicates("key")
    second = c[c.duplicated("key")].drop_duplicates("key").set_index("key")
    t = top.set_index("key")
    tie = second.index.intersection(t.index)
    tie = tie[(second.loc[tie, score].to_numpy() == t.loc[tie, score].to_numpy())
              & (second.loc[tie, "round_ok"].to_numpy() == t.loc[tie, "round_ok"].to_numpy())]
    return top[~top["key"].isin(tie)][["key"] + out_cols], pd.Index(tie)


def name_links(src: pd.DataFrame, s0: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index]:
    """Per source match: the Stage 0 match its names point to inside its event and draw (score 3: both surnames and
    both first names; 2: both surnames; 1: one surname and the other the map's same_player), a1_n (player 1 is A)."""
    c = src[["key", "tid", "draw", "rnd", "n1", "n2"]].merge(
        s0[["match_id", "tidp", "draw", "round", "name_a", "name_b", "ka", "kb"]],
        left_on=["tid", "draw"], right_on=["tidp", "draw"], how="inner")
    c["k1"], c["k2"] = c["n1"].map(M.surname_key), c["n2"].map(M.surname_key)
    c = c[(c["k1"].isin([""]) == False) & ((c["k1"] == c["ka"]) | (c["k1"] == c["kb"])  # noqa: E712
                                          | (c["k2"] == c["ka"]) | (c["k2"] == c["kb"]))].copy()
    if c.empty:
        return pd.DataFrame(columns=["key", "match_id", "a1_n", "score_n"]), pd.Index([])
    n1, n2, na, nb = (c[x].fillna("").astype(str).to_numpy() for x in ("n1", "n2", "name_a", "name_b"))
    k1, k2, ka, kb = (c[x].to_numpy() for x in ("k1", "k2", "ka", "kb"))
    fn = np.vectorize(M.same_first_name, otypes=[bool])
    sp = np.vectorize(M.same_player, otypes=[bool])
    keys_s, keys_w = (k1 == ka) & (k2 == kb), (k1 == kb) & (k2 == ka)
    fn_s = fn(n1, na) & fn(n2, nb)
    fn_w = fn(n1, nb) & fn(n2, na)
    loose_s = ((k1 == ka) | sp(n1, na)) & ((k2 == kb) | sp(n2, nb)) & ((k1 == ka) | (k2 == kb))
    loose_w = ((k1 == kb) | sp(n1, nb)) & ((k2 == ka) | sp(n2, na)) & ((k1 == kb) | (k2 == ka))
    s_s = np.select([keys_s & fn_s, keys_s, loose_s & fn_s], [3, 2, 1], 0)
    s_w = np.select([keys_w & fn_w, keys_w, loose_w & fn_w], [3, 2, 1], 0)
    c["score_n"] = np.maximum(s_s, s_w)
    # orientation: the better side; a tie (the same surname both ways) is left undecided
    c["a1_n"] = np.where(s_s > s_w, True, np.where(s_w > s_s, False, None))
    c["round_ok"] = c["rnd"].isna() | c["rnd"].eq(c["round"])
    c = c[c["score_n"] > 0]
    return _pick(c, "score_n", ["match_id", "a1_n", "score_n", "round_ok"])


def learn_crosswalk(src: pd.DataFrame, nl: pd.DataFrame, s0: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame, dict]:
    """ATP code -> Stage 0 id from the strict name links (score 3, oriented), majority >= XW_MIN_SHARE; then the
    external crosswalks for codes with no vote. Returns the map, the table and a summary with agreement rates."""
    lk = nl[nl["score_n"].eq(3) & nl["a1_n"].notna()].merge(src[["key", "c1", "c2"]], on="key").merge(
        s0[["match_id", "player_a_id", "player_b_id"]], on="match_id")
    a1 = lk["a1_n"].astype(bool).to_numpy()
    votes = pd.DataFrame({"code": np.concatenate([lk["c1"].to_numpy(), lk["c2"].to_numpy()]),
                          "pid": np.concatenate([np.where(a1, lk["player_a_id"], lk["player_b_id"]),
                                                 np.where(a1, lk["player_b_id"], lk["player_a_id"])])})
    votes = votes.dropna()
    top = votes.groupby(["code", "pid"]).size().reset_index(name="votes")
    top["total"] = top.groupby("code")["votes"].transform("sum")
    top["share"] = top["votes"] / top["total"]
    best = top.sort_values(["code", "votes", "pid"], ascending=[True, False, True]).drop_duplicates("code")
    kept = best[best["share"] >= XW_MIN_SHARE].assign(origin="name_votes")
    summary = {"codes_with_votes": int(len(best)), "codes_kept": int(len(kept)),
               "codes_below_share": int((best["share"] < XW_MIN_SHARE).sum()),
               "below_share_examples": best[best["share"] < XW_MIN_SHARE].head(15).to_dict(orient="records")}
    ext = {}
    for name, path in EXTERNAL_XW.items():
        if path.exists():
            e = pd.read_parquet(path, columns=["code", "pid"])
            e["code"] = e["code"].map(B.atp_code)
            ext[name] = e.dropna().drop_duplicates("code").set_index("code")["pid"]
            both = kept["code"][kept["code"].isin(ext[name].index)]
            agree = (kept.set_index("code").loc[both, "pid"] == ext[name].loc[both]).mean() if len(both) else np.nan
            summary[f"agreement_with_{name}"] = {"codes_in_both": int(len(both)), "same_id_share": float(agree)}
    needed = set(src["c1"].dropna()) | set(src["c2"].dropna())
    have = set(kept["code"])
    extra = []
    for name, e in ext.items():
        add = sorted((needed - have) & set(e.index))
        extra.append(pd.DataFrame({"code": add, "pid": e.loc[add].to_numpy(), "origin": name}))
        have |= set(add)
    xw = pd.concat([kept[["code", "pid", "votes", "total", "share", "origin"]]] + extra, ignore_index=True)
    # a Stage 0 id claimed by two codes (one player under two ATP codes, or a slip): kept, reported
    multi = xw.groupby("pid")["code"].nunique()
    summary["pids_with_two_codes"] = int((multi > 1).sum())
    summary["pids_with_two_codes_examples"] = xw[xw["pid"].isin(multi[multi > 1].index)].head(20).to_dict(
        orient="records")
    summary["codes_needed"] = int(len(needed))
    summary["codes_mapped"] = int(len(have & needed))
    summary["codes_from_external"] = {k: int((xw["origin"] == k).sum()) for k in ext}
    return xw.set_index("code")["pid"], xw, summary


def id_links(src: pd.DataFrame, s0: pd.DataFrame, xw: pd.Series) -> tuple[pd.DataFrame, pd.Index]:
    x1, x2 = src["c1"].map(xw), src["c2"].map(xw)
    s = src.assign(x1=x1, x2=x2, lo=np.minimum(x1.fillna(""), x2.fillna("")),
                   hi=np.maximum(x1.fillna(""), x2.fillna("")))
    s = s[x1.notna() & x2.notna()]
    c = s[["key", "tid", "draw", "rnd", "lo", "hi", "x1", "start"]].merge(
        s0[["match_id", "tidp", "draw", "round", "plo", "phi", "player_a_id", "tournament_date"]],
        left_on=["tid", "draw", "lo", "hi"], right_on=["tidp", "draw", "plo", "phi"], how="inner")
    c["round_ok"] = c["rnd"].isna() | c["rnd"].eq(c["round"])
    c["score_i"] = 1
    c["a1_i"] = c["x1"].eq(c["player_a_id"])
    in_event, amb = _pick(c, "score_i", ["match_id", "a1_i", "round_ok"])
    in_event["window"] = False
    # events Stage 0 lacks (or a match not found in its event): the same two ids within WINDOW_DAYS of the event start
    rest = s[~s["key"].isin(in_event["key"]) & ~s["key"].isin(amb) & s["start"].notna()]
    w = rest[["key", "draw", "rnd", "lo", "hi", "x1", "start"]].merge(
        s0[["match_id", "draw", "round", "plo", "phi", "player_a_id", "tournament_date"]],
        left_on=["draw", "lo", "hi"], right_on=["draw", "plo", "phi"], how="inner")
    w = w[(w["tournament_date"] - w["start"]).abs().dt.days <= WINDOW_DAYS].copy()
    w["round_ok"] = w["rnd"].isna() | w["rnd"].eq(w["round"])
    w["score_i"] = 1
    w["a1_i"] = w["x1"].eq(w["player_a_id"])
    in_window, amb2 = _pick(w, "score_i", ["match_id", "a1_i", "round_ok"])
    in_window["window"] = True
    return pd.concat([in_event, in_window], ignore_index=True), amb.union(amb2)


def link_atp(s0: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    src = pd.concat([B.read_atp_matches(s) for s in B.ATP_SOURCES], ignore_index=True)
    B.log(f"ATP-format matches: {len(src):,} ({src['source'].value_counts().to_dict()})")
    nl, amb_n = name_links(src, s0)
    B.log(f"  name links {len(nl):,}; ambiguous {len(amb_n):,}")
    xw, xw_table, xw_summary = learn_crosswalk(src, nl, s0)
    B.log(f"  crosswalk: {xw_summary['codes_mapped']:,} of {xw_summary['codes_needed']:,} codes mapped")
    il, amb_i = id_links(src, s0, xw)
    B.log(f"  id links {len(il):,} ({int(il['window'].sum())} by the date window); ambiguous {len(amb_i):,}")
    out = src.merge(nl.rename(columns={"match_id": "mid_n", "round_ok": "round_ok_n"}), on="key", how="left")
    out = out.merge(il.rename(columns={"match_id": "mid_i", "round_ok": "round_ok_i"}), on="key", how="left")
    hn, hi = out["mid_n"].notna(), out["mid_i"].notna()
    same = hn & hi & out["mid_n"].eq(out["mid_i"])
    tid_known = out["tid"].isin(set(s0["tidp"]))
    method = np.select(
        [same, hn & hi, hi & out["window"].eq(True), hi, hn & out["score_n"].ge(2), hn],
        ["ids+names", "conflict", "ids_window", "ids", "names", "names_loose"], "")
    reason = np.select([out["key"].isin(amb_n) | out["key"].isin(amb_i), ~tid_known],
                       ["ambiguous", "event_not_in_stage0"], "no_candidate")
    out["method"] = np.where(method == "", "unlinked:" + reason, method)
    linked = ~out["method"].str.startswith("unlinked") & out["method"].ne("conflict")
    out["match_id_s0"] = np.where(linked, out["mid_i"].where(hi, out["mid_n"]), None)
    a1 = out["a1_i"].where(hi, out["a1_n"])
    out["a1"] = np.where(linked, a1, None)
    # a link without an orientation (two surnames alike, no ids) is not usable
    noor = linked & pd.isna(out["a1"])
    out.loc[noor, "method"] = "unlinked:no_orientation"
    out.loc[noor, "match_id_s0"] = None
    out["round_ok"] = out["round_ok_i"].where(hi, out["round_ok_n"])
    # two source matches on one Stage 0 match (within a source): keep the one with more points, list the other
    lk = out[out["match_id_s0"].notna()].sort_values(["source", "match_id_s0", "points_src"],
                                                     ascending=[True, True, False])
    dup = lk.duplicated(["source", "match_id_s0"])
    out.loc[lk.index[dup], "method"] = "unlinked:duplicate_of_another_copy"
    out.loc[lk.index[dup], ["match_id_s0", "a1"]] = None
    return out, xw_table, xw_summary


def ace_check(links: pd.DataFrame) -> dict:
    """Orientation check without results: each player's aces in the points against Stage 0's box score."""
    out = {}
    mp = pd.read_parquet(B.STAGE0_PLAYERS, columns=["match_id", "player_id", "ace", "has_box"])
    s0 = B.stage0_men(["player_a_id", "player_b_id"], 2017).set_index("match_id")
    for source in B.ATP_SOURCES:
        lk = links[links["source"].eq(source) & links["match_id_s0"].notna()]
        if lk.empty:
            continue
        p = B.read_atp_points(source)
        a = p[p["result"].eq("A")]
        cnt = a.groupby(["key", "server"]).size().unstack(fill_value=0).reindex(columns=[1, 2], fill_value=0)
        lk = lk.join(cnt, on="key")
        pa = lk["match_id_s0"].map(s0["player_a_id"])
        pb = lk["match_id_s0"].map(s0["player_b_id"])
        box = mp[mp["has_box"].fillna(False).astype(bool)].drop_duplicates(["match_id", "player_id"]).set_index(
            ["match_id", "player_id"])["ace"]
        ace_a = box.reindex(pd.MultiIndex.from_arrays([lk["match_id_s0"], pa])).to_numpy()
        ace_b = box.reindex(pd.MultiIndex.from_arrays([lk["match_id_s0"], pb])).to_numpy()
        a1 = lk["a1"].astype(bool).to_numpy()
        p1, p2 = lk[1].fillna(0).to_numpy(), lk[2].fillna(0).to_numpy()
        mine_a = np.where(a1, p1, p2)
        mine_b = np.where(a1, p2, p1)
        ok = ~np.isnan(ace_a.astype(float)) & ~np.isnan(ace_b.astype(float)) & ((p1 + p2) > 0)
        diff_here = (np.abs(mine_a - ace_a) + np.abs(mine_b - ace_b))[ok]
        diff_swap = (np.abs(mine_b - ace_a) + np.abs(mine_a - ace_b))[ok]
        informative = diff_here != diff_swap
        out[source] = {"matches_compared": int(ok.sum()),
                       "aces_equal_in_link_orientation": int((diff_here == 0).sum()),
                       "informative": int(informative.sum()),
                       "closer_in_link_orientation": int((diff_here < diff_swap).sum()),
                       "closer_swapped": int((diff_swap < diff_here).sum())}
    return out


def link_shot_level(s0_ids: set) -> tuple[pd.DataFrame, dict]:
    """The shot-level sources' links carried to today's ids; unlinked men's rows (2018 on) and TDI linked anew."""
    from src.eda.shot_level import common as S
    from src.eda.shot_level import stage0_sources as SS
    sm = pd.read_parquet(B.SHOT_LEVEL / "stage0_source_matches.parquet",
                         columns=["source", "key", "tour", "year", "d", "name1", "name2", "round", "draw", "level",
                                  "n_points", "match_id", "a1"])
    sm = sm[sm["tour"].eq("M") & sm["source"].isin([s for s in B.SHOT_LEVEL_SOURCES if s != "tdi"])].copy()
    sm = sm[sm["year"].fillna(0).astype(int) >= 2017]
    remap = B.id_remap()
    sm["match_id_s0"] = sm["match_id"].map(lambda x: remap.get(x, x) if isinstance(x, str) else None)
    ok = sm["match_id_s0"].isin(s0_ids) & sm["a1"].notna()
    sm["method"] = np.where(ok, "shot_level_link", "")
    sm.loc[~ok, "match_id_s0"] = None
    B.log(f"shot-level sources: {len(sm):,} men's matches 2017+; {int(ok.sum()):,} carried; relinking the rest and TDI")
    linker = S.Stage0Linker()
    rest = sm[~ok & (sm["year"].fillna(0).astype(int) >= 2018)]
    summary = {"carried_by_id_maps": int(ok.sum()), "relink_attempted": int(len(rest))}
    if len(rest):
        lk = linker.link(rest[["tour", "d", "year", "name1", "name2", "round", "draw", "level"]])
        got = lk["match_id"].notna() & lk["a1"].notna()
        sm.loc[lk.index[got], "match_id_s0"] = lk.loc[got, "match_id"]
        sm.loc[lk.index[got], "a1"] = lk.loc[got, "a1"]
        sm.loc[lk.index[got], "method"] = "relinked_today"
        summary["relinked_today"] = int(got.sum())
    sm.loc[sm["method"].eq(""), "method"] = "unlinked"
    tdi = SS.tdi()
    tdi = tdi[tdi["tour"].eq("M")].copy()
    lk = linker.link(tdi[["tour", "d", "year", "name1", "name2", "round", "draw", "level"]])
    got = lk["match_id"].notna() & lk["a1"].notna()
    tdi["match_id_s0"] = np.where(got, lk["match_id"], None)
    tdi["a1"] = np.where(got, lk["a1"], None)
    tdi["method"] = np.where(got, "linked_today", "unlinked")
    summary["tdi_matches_read_today"] = int(len(tdi))
    summary["tdi_linked_today"] = int(got.sum())
    old_tdi = pd.read_parquet(B.SHOT_LEVEL / "stage0_source_matches.parquet", columns=["source", "match_id"])
    old_tdi = old_tdi[old_tdi["source"].eq("tdi")]
    summary["tdi_in_shot_level_table"] = int(len(old_tdi))
    summary["tdi_linked_in_shot_level_table"] = int(old_tdi["match_id"].notna().sum())
    cols = ["source", "key", "year", "d", "name1", "name2", "round", "draw", "level", "n_points", "match_id_s0", "a1",
            "method"]
    out = pd.concat([sm[cols], tdi[cols]], ignore_index=True)
    # two source matches on one Stage 0 match within a source: keep the one with more points
    lk2 = out[out["match_id_s0"].notna()].sort_values(["source", "match_id_s0", "n_points"],
                                                      ascending=[True, True, False])
    dup = lk2.duplicated(["source", "match_id_s0"])
    out.loc[lk2.index[dup], "method"] = "unlinked:duplicate_of_another_copy"
    out.loc[lk2.index[dup], ["match_id_s0", "a1"]] = None
    return out, summary


def rates(links: pd.DataFrame, s0: pd.DataFrame) -> list[dict]:
    lv = links.copy()
    lv["linked"] = lv["match_id_s0"].notna()
    lv["season"] = lv["year"].astype(str)
    if "level_src" in lv:
        lv["level_grp"] = np.select([lv["source"].eq("infosys_slams"),
                                     lv["series"].eq("ch") | lv["source"].eq("infosys_challengers"),
                                     lv["level_src"].isin(["1000"]), lv["level_src"].isin(["atp500"]),
                                     lv["level_src"].isin(["atp250"]), lv["level_src"].isin(["atpFinal"]),
                                     lv["level_src"].isin(["nextGen"])],
                                    ["GS", "CH", "T1000", "T500", "T250", "FIN", "NextGen"],
                                    np.where(lv["source"].eq("infosys_atp"), "tour", "other"))
    g = lv.groupby(["source", "level_grp", "draw", "season"], dropna=False).agg(
        matches=("key", "size"), linked=("linked", "sum")).reset_index()
    g["rate"] = g["linked"] / g["matches"]
    return g.to_dict(orient="records")


def main() -> int:
    B.OUT.mkdir(parents=True, exist_ok=True)
    s0 = stage0_frame()
    B.log(f"Stage 0 men's matches 2017+: {len(s0):,}")
    atp, xw_table, xw_summary = link_atp(s0)
    s0_ids = set(B.stage0_men(["year"], 2010)["match_id"])
    shot, shot_summary = link_shot_level(s0_ids)
    B.log(f"shot-level sources: {int(shot['match_id_s0'].notna().sum()):,} of {len(shot):,} linked")
    # the gate's tracking flag per ATP-format match, for the report (rally-carrying matches' link rate)
    carry = []
    for source in B.ATP_SOURCES:
        p = B.mb_convention(B.read_atp_points(source))
        g = B.match_gate(p["key"], p["rally"], p["end"])
        carry.append(g[["key", "carries", "share"]])
    carry = pd.concat(carry, ignore_index=True)
    atp = atp.merge(carry, on="key", how="left")
    atp["carries"] = atp["carries"].fillna(False).astype(bool)
    atp["round_disagrees"] = atp["match_id_s0"].notna() & atp["round_ok"].eq(False)
    keep = ["source", "key", "year", "event_id", "match_id", "tid", "draw", "rnd", "c1", "c2", "n1", "n2", "level_src",
            "series", "start", "points_src", "score_n", "method", "match_id_s0", "a1", "round_ok", "round_disagrees",
            "carries", "share"]
    atp_out = atp[keep].copy()
    atp_out["a1"] = atp_out["a1"].astype("boolean")
    shot_out = shot.copy()
    shot_out["a1"] = shot_out["a1"].astype("boolean")
    links = pd.concat([atp_out.assign(family="atp_format"),
                       shot_out.rename(columns={"n_points": "points_src"}).assign(family="shot_level")],
                      ignore_index=True)
    links["year"] = links["year"].astype(str)
    for c in ("rnd", "round", "level", "level_src", "series", "c1", "c2", "n1", "n2", "name1", "name2", "tid",
              "event_id", "match_id", "draw", "score_n"):
        if c in links:
            links[c] = links[c].astype("string") if c != "score_n" else links[c].astype("Float64")
    links.to_parquet(B.OUT / "links.parquet", index=False)
    xw_table.to_parquet(B.OUT / "crosswalk.parquet", index=False)
    fail = atp[atp["match_id_s0"].isna()][["source", "key", "tid", "draw", "rnd", "c1", "c2", "n1", "n2", "level_src",
                                           "series", "start", "points_src", "carries", "method"]]
    fail.to_csv(B.OUT / "link_failures.csv", index=False)
    report = {
        "atp_format": {
            "methods": atp.groupby(["source", "method"]).size().rename("n").reset_index().to_dict(orient="records"),
            "rates": rates(atp, s0),
            "rally_carrying_rates": rates(atp[atp["carries"]], s0),
            "round_disagreements_main_draw": int(atp.loc[atp["draw"].eq("main"), "round_disagrees"].sum()),
            "round_disagreement_examples": atp[atp["round_disagrees"] & atp["draw"].eq("main")][
                ["source", "key", "rnd", "match_id_s0"]].head(20).to_dict(orient="records"),
            "crosswalk": xw_summary,
            "ace_check": ace_check(atp),
            "failures_by_reason": fail.groupby(["source", "method", "carries"]).size().rename("n").reset_index()
            .to_dict(orient="records"),
        },
        "shot_level": {**shot_summary,
                       "by_source": shot.groupby(["source", "method"]).size().rename("n").reset_index()
                       .to_dict(orient="records")},
    }
    B.write_json(B.OUT / "link_report.json", report)
    m = atp.groupby("source").agg(n=("key", "size"), linked=("match_id_s0", lambda x: x.notna().sum()))
    B.log("ATP-format link rates:\n" + m.assign(rate=m["linked"] / m["n"]).to_string())
    c = atp[atp["carries"]].groupby("source").agg(n=("key", "size"), linked=("match_id_s0", lambda x: x.notna().sum()))
    B.log("rally-carrying matches:\n" + c.assign(rate=c["linked"] / c["n"]).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
