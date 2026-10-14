"""R2-skeptic: link Sackmann's raw rows to RG's own records and the Olympic results myself, recount MatchBeats and the
Olympic play-by-play myself, and lay every source side by side, per raw row side (w / l).

Linking (my own, stricter than the lead's): same year, tour, draw and round (RG: the round from the match code
itself; Olympics: the unit's description); names compared as folded word sets; the best pairing must be unique AND
Sackmann's winner must be the record's winner (a disagreement is reported, never forced).

Writes sides.parquet in data/studies/rg_first_serve_recount/review/R2-skeptic/ (one row per raw row side) and
link_report.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/link_compare.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
COUNTS = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]


def fold(name) -> list[str]:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return []
    s = unicodedata.normalize("NFKD", str(name)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s).split()


def sim(a: list[str], b: list[str]) -> int:
    """3 same word set (or the same letters joined); 2 a shared word of 3+ letters and a shared initial;
    1 a shared word of 3+ letters, or a transliteration of 5+ letters (similarity 0.8+); 0 otherwise."""
    if not a or not b:
        return 0
    if sorted(a) == sorted(b) or "".join(sorted(a)) == "".join(sorted(b)) or "".join(a) == "".join(b):
        return 3
    sa, sb = {t for t in a if len(t) >= 3}, {t for t in b if len(t) >= 3}
    shared = sa & sb
    if shared:
        ia, ib = {t[0] for t in a if t not in shared}, {t[0] for t in b if t not in shared}
        return 2 if (ia & ib) else 1
    if any(len(x) >= 5 and len(y) >= 5 and SequenceMatcher(None, x, y).ratio() >= 0.8 for x in sa for y in sb):
        return 1
    return 0


def rg_round(code: str) -> tuple[str, str, str]:
    fam, n = code[:2], int(code[2:])
    tour = "W" if fam[1] == "D" else "M"
    if fam[0] == "Q":
        rnd = "Q3" if 16 <= n <= 31 else "Q2" if 32 <= n <= 63 else "Q1" if 64 <= n <= 127 else "?"
        return tour, "qual", rnd
    rnd = ("F" if n == 1 else "SF" if n <= 3 else "QF" if n <= 7 else "R16" if n <= 15 else "R32" if n <= 31
           else "R64" if n <= 63 else "R128" if n <= 127 else "?")
    return tour, "main", rnd


def link(sack: pd.DataFrame, rec: pd.DataFrame, keys: list[str], rid: str) -> pd.DataFrame:
    """sack: one row per Sackmann row with wn/ln (folded names); rec: one row per record match with n1/n2, win1
    (True when name 1 won). Returns per Sackmann row: rid, orient ('12': winner is name 1), score, tie flag,
    winner_agrees."""
    groups = {k: g for k, g in rec.groupby(keys)}
    out = []
    for r in sack.itertuples(index=False):
        d = r._asdict()
        cand = groups.get(tuple(d[k] for k in keys))
        scored = []
        if cand is not None:
            for c in cand.itertuples(index=False):
                for orient, (x, y) in (("12", (c.n1, c.n2)), ("21", (c.n2, c.n1))):
                    s1, s2 = sim(d["wn"], x), sim(d["ln"], y)
                    scored.append(((min(s1, s2), s1 + s2), getattr(c, rid), orient, c.win1))
        scored.sort(key=lambda t: t[0], reverse=True)
        if not scored or scored[0][0][0] < 1:
            out.append({"source_file": d["source_file"], "source_row": d["source_row"], rid: None, "orient": None,
                        "lscore": None, "tie": False, "winner_agrees": None})
            continue
        best = scored[0]
        tie = any(s[0] == best[0] and (s[1] != best[1] or s[2] != best[2]) for s in scored[1:])
        win_ok = (best[3] if best[2] == "12" else (not best[3])) if best[3] is not None else None
        out.append({"source_file": d["source_file"], "source_row": d["source_row"], rid: best[1], "orient": best[2],
                    "lscore": best[0][0], "lsum": best[0][1], "tie": tie, "winner_agrees": win_ok,
                    "second_best": scored[1][0][0] if len(scored) > 1 and scored[1][1] != best[1] else None})
    return pd.DataFrame(out)


def mb_counts(pts: pd.DataFrame) -> pd.DataFrame:
    """Per (year, code, slot) recount of MatchBeats: one route per match (match-beats/match-centre over the API)."""
    order = {"match-beats": 0, "match-centre": 0, "match-beats-api": 1}
    pts = pts.assign(_o=pts["route"].map(order))
    best = pts.groupby(["year", "code"])["_o"].transform("min")
    pts = pts[pts["_o"].eq(best)]
    rows = []
    for (y, c), g in pts.groupby(["year", "code"]):
        for k in ("1", "2"):
            m = g[g["server"].eq(k)]
            first = m["serve"].eq("1")
            second = m["serve"].eq("2")
            won = m["scorer"].eq(k)
            pid_serve = m["pointId"].astype(str).str.rsplit("_", n=1).str[-1]
            rows.append({"year": y, "code": c, "slot": int(k), "route": m["route"].iloc[0] if len(m) else None,
                         "mb_svpt": len(m), "mb_first_in": int(first.sum()), "mb_first_won": int((first & won).sum()),
                         "mb_second_won": int((second & won).sum()), "mb_other_serve": int((~first & ~second).sum()),
                         "mb_ace": int(m["result"].eq("A").sum()), "mb_df": int(m["result"].eq("DF").sum()),
                         "mb_df_on_first": int((m["result"].eq("DF") & first).sum()),
                         "mb_pid_serve_mismatch": int((pid_serve != m["serve"]).sum()),
                         "mb_points_total": len(g), "mb_speed_pts": int((pd.to_numeric(m["speed"]) > 0).sum()),
                         "mb_second_with_fault_speed": int((second & (pd.to_numeric(m["fault_speed"]) > 0)).sum()),
                         "mb_first_with_fault_speed": int((first & (pd.to_numeric(m["fault_speed"]) > 0)).sum())})
    return pd.DataFrame(rows)


def og_counts(st: pd.DataFrame, pbp: pd.DataFrame) -> pd.DataFrame:
    tot = st[st["pos"].eq("TOT")]
    rows = []
    for (unit, code), g in tot.groupby(["unit", "athlete_code"]):
        g = g.set_index("code")

        def v(c, f="value"):
            return g.loc[c, f] if c in g.index else None
        rows.append({"unit": unit, "athlete_code": code, "og_svpt": v("1ST_SERVE", "attempt"),
                     "og_first_in": v("1ST_SERVE"), "og_first_won": v("1ST_SERVE", "points_won"),
                     "og_second_won": v("2ND_SERVE", "points_won"), "og_second_in": v("2ND_SERVE"),
                     "og_second_att": v("2ND_SERVE", "attempt"), "og_ace": v("ACES"), "og_df": v("DBL_FAULT"),
                     "og_ace_first": v("1ST_SERVE", "ext_ace"), "og_ace_second": v("2ND_SERVE", "ext_ace"),
                     "og_spw": v("PTS_WON_SERVE"), "og_spw_att": v("PTS_WON_SERVE", "attempt"),
                     "og_bp_won": v("BREAK_PTS"), "og_bp_opps": v("BREAK_PTS", "attempt"),
                     "og_points": v("POINTS"), "og_recv_won": v("RECEIVE"), "og_recv_att": v("RECEIVE", "attempt")})
    out = pd.DataFrame(rows)
    # per-set sums
    per = st[~st["pos"].eq("TOT")]
    agg = []
    for (unit, code), g in per.groupby(["unit", "athlete_code"]):
        f = g[g["code"].eq("1ST_SERVE")]
        s2 = g[g["code"].eq("2ND_SERVE")]
        agg.append({"unit": unit, "athlete_code": code, "ogset_first_in": f["value"].sum(min_count=1),
                    "ogset_svpt": f["attempt"].sum(min_count=1), "ogset_first_won": f["points_won"].sum(min_count=1),
                    "ogset_second_won": s2["points_won"].sum(min_count=1)})
    out = out.merge(pd.DataFrame(agg), on=["unit", "athlete_code"], how="left")
    # the play-by-play
    p = pbp[pbp["result"].notna()].copy()
    r = p["result"].astype(str)
    p["f"] = r.isin(["PS1", "PR1", "A1"])
    p["fw"] = r.isin(["PS1", "A1"])
    p["sw"] = r.isin(["PS2", "A2"])
    p["known"] = r.isin(["PS1", "PR1", "A1", "PS2", "PR2", "A2", "DF"])
    g = p.groupby(["unit", "server"])
    pc = pd.DataFrame({"ogp_svpt": g.size(), "ogp_first_in": g["f"].sum(), "ogp_first_won": g["fw"].sum(),
                       "ogp_second_won": g["sw"].sum(), "ogp_ace": g["result"].apply(lambda s: s.isin(["A1", "A2"]).sum()),
                       "ogp_df": g["result"].apply(lambda s: s.eq("DF").sum()),
                       "ogp_unknown": g["known"].apply(lambda s: (~s).sum())}).reset_index()
    pc = pc.rename(columns={"server": "athlete_code"})
    return out.merge(pc, on=["unit", "athlete_code"], how="left")


def main() -> int:
    api = pd.read_parquet(OUT / "api_raw.parquet")
    sack = pd.read_parquet(OUT / "sack_rows.parquet")
    pts = pd.read_parquet(OUT / "mb_points.parquet")
    meta = pd.read_parquet(OUT / "mb_meta.parquet")
    ogst = pd.read_parquet(OUT / "og_stats.parquet")
    ogun = pd.read_parquet(OUT / "og_units.parquet")
    ogpb = pd.read_parquet(OUT / "og_pbp.parquet")
    for c in COUNTS:
        for s in ("w", "l"):
            sack[f"{s}_{c}"] = pd.to_numeric(sack[f"{s}_{c}"].replace("", np.nan), errors="coerce")
    sack["wn"], sack["ln"] = sack["winner_name"].map(fold), sack["loser_name"].map(fold)
    sack["draw"] = np.where(sack["round"].str.fullmatch(r"Q\d"), "qual", "main")
    sack["year"] = sack["tourney_id"].str[:4].astype(int)
    report = {}

    # ------------------------------------------------------------------ RG
    rg = sack[sack["tourney_name"].eq("Roland Garros")].copy()
    tr = api["code"].map(rg_round)
    api["tour"], api["draw"], api["round"] = tr.str[0], tr.str[1], tr.str[2]
    api["name"] = (api["first"].fillna("") + " " + api["last"].fillna("")).map(fold)
    m = api.pivot_table(index=["year", "code", "tour", "draw", "round"], columns="team", values="name",
                        aggfunc="first").reset_index().rename(columns={"A": "n1", "B": "n2"})
    wa = api[api["team"].eq("A")].set_index(["year", "code"])["winner"]
    m["win1"] = [wa.get((y, c)) for y, c in zip(m["year"], m["code"])]
    lk = link(rg, m, ["year", "tour", "draw", "round"], "code")
    rg = rg.merge(lk, on=["source_file", "source_row"])
    report["rg_rows"] = int(len(rg))
    report["rg_unlinked"] = rg[rg["code"].isna()][["source_file", "source_row", "winner_name", "loser_name"]] \
        .to_dict("records")
    report["rg_ties"] = rg[rg["tie"]][["source_file", "source_row", "winner_name", "loser_name", "code"]] \
        .to_dict("records")
    report["rg_winner_disagrees"] = rg[rg["winner_agrees"].eq(False)][
        ["source_file", "source_row", "winner_name", "loser_name", "code"]].to_dict("records")
    report["rg_link_score_counts"] = rg["lscore"].value_counts(dropna=False).to_dict()
    dup = rg[rg["code"].notna()].duplicated(["year", "code"], keep=False)
    report["rg_codes_used_twice"] = rg[rg["code"].notna()][dup][["source_file", "source_row", "code"]] \
        .to_dict("records")

    # the record's team for each raw side
    sides = []
    mbc = mb_counts(pts)
    meta_ok = meta[meta["problem"].isna()].copy()
    for r in rg.itertuples(index=False):
        if r.code is None or pd.isna(r.code):
            continue
        for side in ("w", "l"):
            team = ("A" if r.orient == "12" else "B") if side == "w" else ("B" if r.orient == "12" else "A")
            sides.append({"event": "RG", "year": r.year, "tour": r.tour, "draw": r.draw, "round": r.round,
                          "source_file": r.source_file, "source_row": r.source_row, "side": side,
                          "player": r.winner_name if side == "w" else r.loser_name, "score": r.score,
                          "code": r.code, "team": team, "lscore": r.lscore, "winner_agrees": r.winner_agrees,
                          "raw_winner_name": r.winner_name, "raw_loser_name": r.loser_name,
                          "raw_tourney_id": r.tourney_id, "raw_minutes": r.minutes,
                          **{f"raw_{c}": getattr(r, f"{side}_{c}") for c in COUNTS}})
    sd = pd.DataFrame(sides)
    a = api.rename(columns={c: f"api_{c}" for c in api.columns if c not in ("year", "code", "team")})
    sd = sd.merge(a, on=["year", "code", "team"], how="left")
    # opponent's api values (break points faced come from the opponent's "break points won")
    opp = api[["year", "code", "team", "bp_won", "bp_opps", "svpt"]].copy()
    opp["team"] = opp["team"].map({"A": "B", "B": "A"})
    opp = opp.rename(columns={"bp_won": "api_opp_bp_won", "bp_opps": "api_opp_bp_opps", "svpt": "api_opp_svpt"})
    sd = sd.merge(opp, on=["year", "code", "team"], how="left")
    # MatchBeats slots paired to API teams by name (and the Infosys id never used)
    mm = meta_ok.copy()
    order = {"match-beats": 0, "match-centre": 0, "match-beats-api": 1}
    mm["_o"] = mm["route"].map(order)
    mm = mm[mm["_o"].eq(mm.groupby(["year", "code"])["_o"].transform("min"))]
    slot_of = {}
    for r in mm.itertuples(index=False):
        n1 = fold(f"{r.p1_first} {r.p1_last}")
        n2 = fold(f"{r.p2_first} {r.p2_last}")
        slot_of[(r.year, r.code)] = (n1, n2, r.complete, r.status, r.court)
    mb_slot, mb_pair, mb_complete, mb_status = [], [], [], []
    for r in sd.itertuples(index=False):
        x = slot_of.get((r.year, r.code))
        if x is None:
            mb_slot.append(None); mb_pair.append(None); mb_complete.append(None); mb_status.append(None)
            continue
        me = r.api_name
        s1, s2 = sim(me, x[0]), sim(me, x[1])
        if s1 > s2 and s1 >= 1:
            mb_slot.append(1)
        elif s2 > s1 and s2 >= 1:
            mb_slot.append(2)
        else:
            mb_slot.append(None)
        mb_pair.append(max(s1, s2)); mb_complete.append(x[2]); mb_status.append(x[3])
    sd["mb_slot"], sd["mb_pair"], sd["mb_complete"], sd["mb_status"] = mb_slot, mb_pair, mb_complete, mb_status
    sd = sd.merge(mbc.rename(columns={"slot": "mb_slot"}), on=["year", "code", "mb_slot"], how="left")

    # ------------------------------------------------------------------ Olympics
    og = sack[sack["tourney_name"].eq("Paris Olympics")].copy()
    ogun = ogun.copy()
    ogun["tour"] = np.where(ogun["unit"].str.startswith("TENM"), "M", "W")
    rmap = {"First Round": "R64", "Second Round": "R32", "Third Round": "R16", "Quarter-final": "QF",
            "Semi-final": "SF", "Gold Medal Match": "F", "Bronze Medal Match": "BR"}
    ogun["round"] = ogun["description"].map(lambda d: next((v for k, v in rmap.items() if str(d).endswith(k)), None))
    ogun["draw"], ogun["year"] = "main", 2024
    ogun["n1"] = (ogun["home_given"].fillna("") + " " + ogun["home_family"].fillna("")).map(fold)
    ogun["n2"] = (ogun["away_given"].fillna("") + " " + ogun["away_family"].fillna("")).map(fold)
    ogun["win1"] = ogun["home_wlt"].map({"W": True, "L": False})
    lk = link(og, ogun, ["year", "tour", "draw", "round"], "unit")
    og = og.merge(lk, on=["source_file", "source_row"])
    report["og_rows"] = int(len(og))
    report["og_unlinked"] = og[og["unit"].isna()][["source_file", "source_row", "winner_name", "loser_name", "round"]] \
        .to_dict("records")
    report["og_ties"] = og[og["tie"]][["source_file", "source_row", "winner_name", "loser_name"]].to_dict("records")
    report["og_winner_disagrees"] = og[og["winner_agrees"].eq(False)][
        ["source_file", "source_row", "winner_name", "loser_name"]].to_dict("records")
    report["og_link_score_counts"] = og["lscore"].value_counts(dropna=False).to_dict()
    ogc = og_counts(ogst, ogpb)
    oside = []
    ui = ogun.set_index("unit")
    for r in og.itertuples(index=False):
        if r.unit is None or pd.isna(r.unit):
            continue
        u = ui.loc[r.unit]
        for side in ("w", "l"):
            home = (r.orient == "12") == (side == "w")
            oside.append({"event": "OG", "year": 2024, "tour": r.tour, "draw": "main", "round": r.round,
                          "source_file": r.source_file, "source_row": r.source_row, "side": side,
                          "player": r.winner_name if side == "w" else r.loser_name, "score": r.score,
                          "unit": r.unit, "athlete_code": u["home_code"] if home else u["away_code"],
                          "opp_code": u["away_code"] if home else u["home_code"], "lscore": r.lscore,
                          "winner_agrees": r.winner_agrees, "og_status": u["status"],
                          "raw_winner_name": r.winner_name, "raw_loser_name": r.loser_name,
                          "raw_tourney_id": r.tourney_id, "raw_minutes": r.minutes, "og_court": u["court"],
                          **{f"raw_{c}": getattr(r, f"{side}_{c}") for c in COUNTS}})
    od = pd.DataFrame(oside)
    od = od.merge(ogc, on=["unit", "athlete_code"], how="left")
    oo = ogc[["unit", "athlete_code", "og_bp_won", "og_bp_opps", "og_svpt"]].rename(
        columns={"athlete_code": "opp_code", "og_bp_won": "og_opp_bp_won", "og_bp_opps": "og_opp_bp_opps",
                 "og_svpt": "og_opp_svpt"})
    od = od.merge(oo, on=["unit", "opp_code"], how="left")
    allsides = pd.concat([sd, od], ignore_index=True)
    allsides.to_parquet(OUT / "sides.parquet", index=False)
    (OUT / "link_report.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()}, indent=1,
                     default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
