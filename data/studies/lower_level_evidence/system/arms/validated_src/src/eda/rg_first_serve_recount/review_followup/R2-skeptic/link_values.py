"""R2-skeptic (round 2): link Stage 0's Roland Garros matches of 2019-2026 to RG's own records myself, and derive
the override values (the eighteen counts) from my own parse of the raw files.

Inputs (all mine, from parse.py and extract_raw.py): api.parquet, mb_points.parquet, mb_meta.parquet,
keystats.parquet, raw_rg.parquet; and Stage 0's two tables (data/studies/predictability_diagnostic/).

Linking: a Stage 0 match is placed on the RG code of the same year, tour, draw and round (the round read from the
code's number, RG's own numbering) whose two players carry its two raw names (folded word sets; score 3 same words,
2 a shared word of 3+ letters and a shared initial, 1 a shared word or a 5+ letter transliteration); the best pairing
must be unique; RG's winner is compared with the raw row's winner (reported, never forced).

Values per player (the raw row's winner w and loser l, by name):
    ace, df, svpt, 1stIn, 1stWon, 2ndWon   RG's match statistics ("first serve" in/served, "win on 1st/2nd serve")
    bpFaced, bpSaved                       the opponent's "break points won" (opportunities; opportunities - won)
    SvGms                                  my MatchBeats recount: non-tie-break games the player served, where
                                           MatchBeats holds as many serve points as RG's statistics for both players
MatchBeats is also recounted on every count, with the first server, tie-break games, and the special point codes
(P penalty point, F awarded point, N no point).

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    players.parquet   one row per Stage 0 player row of RG 2019-2026 with the raw row, my RG values, MatchBeats,
                      key statistics, RG's and the row's scores
    link_report.json  unlinked matches, ties, winner disagreements, link-score counts, codes used twice
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/link_values.py
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]


def fold(name) -> list[str]:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return []
    s = unicodedata.normalize("NFKD", str(name)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s).split()


def sim(a: list[str], b: list[str]) -> int:
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


def stage0_rows() -> pd.DataFrame:
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "qualifying", "round", "tournament_id", "tournament_name",
                                 "status", "status_detail", "score", "has_box", "box_status", "source", "source_file",
                                 "source_row", "sv_gms_incl_tb"])
    m = m[m["tournament_id"].str.fullmatch(r"20(19|2[0-6])-520") & m["year"].between(2019, 2026)].copy()
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name", "won",
                                                                       "side"])
    p = p[p["match_id"].isin(set(m["match_id"]))]
    return m, p


def mb_counts(pts: pd.DataFrame) -> pd.DataFrame:
    """Per (year, code, slot): MatchBeats recounted; first server; game structure."""
    rows = []
    for (y, c), g in pts.groupby(["year", "code"], sort=False):
        g = g.sort_values("idx")
        servers = g.groupby(["set_i", "game_i"])["server"].agg(lambda s: frozenset(s))
        tbflag = g.groupby(["set_i", "game_i"])["tb"].first()
        first_server = g["server"].iloc[0]
        for k in ("1", "2"):
            m = g[g["server"].eq(k)]
            first, second = m["serve"].eq("1"), m["serve"].eq("2")
            won = m["scorer"].eq(k)
            reg = sum(1 for key, v in servers.items() if v == {k} and not tbflag[key])
            reg_flag_only = sum(1 for key, v in servers.items() if k in v and not tbflag[key])
            rows.append({"year": y, "code": c, "slot": int(k), "mb_svpt": len(m), "mb_first_in": int(first.sum()),
                         "mb_first_won": int((first & won).sum()), "mb_second_won": int((second & won).sum()),
                         "mb_ace": int(m["result"].eq("A").sum()), "mb_df": int(m["result"].eq("DF").sum()),
                         "mb_sv_gms_regular": reg, "mb_sv_gms_flag": reg_flag_only,
                         "mb_sv_gms_any": int(sum(1 for v in servers.tolist() if k in v)),
                         "mb_tb_games": int(tbflag.sum()), "mb_mixed_nontb_games": int(
                             sum(1 for key, v in servers.items() if len(v) > 1 and not tbflag[key])),
                         "mb_penalty_pts": int(m["result"].eq("P").sum()),
                         "mb_awarded_pts": int(m["result"].eq("F").sum()),
                         "mb_nopoint_pts": int(m["result"].eq("N").sum()),
                         "mb_first_server": first_server, "mb_points_total": len(g)})
    return pd.DataFrame(rows)


def main() -> int:
    api = pd.read_parquet(OUT / "api.parquet")
    raw = pd.read_parquet(OUT / "raw_rg.parquet")
    pts = pd.read_parquet(OUT / "mb_points.parquet")
    meta = pd.read_parquet(OUT / "mb_meta.parquet")
    ks = pd.read_parquet(OUT / "keystats.parquet")
    m, p = stage0_rows()
    report = {}

    # the Stage 0 match's raw row
    raw["_row"] = raw["_row"].astype("Int64")
    m["source_row"] = pd.to_numeric(m["source_row"]).astype("Int64")
    r = raw.rename(columns={"_source_file": "source_file", "_row": "source_row", "source": "raw_source",
                            "tour": "raw_tour", "round": "raw_round", "score": "raw_score"})
    mm = m.merge(r, on=["source_file", "source_row"], how="left")
    report["stage0_matches"] = int(len(m))
    report["stage0_matches_without_raw_row"] = int(mm["raw_source"].isna().sum())
    report["stage0_source_vs_raw_source_disagree"] = int((mm["source"] != mm["raw_source"]).sum())
    mm["tour_l"] = mm["tour"].map({"atp": "M", "wta": "W"})
    mm["draw"] = np.where(mm["qualifying"], "qual", "main")
    mm["wn"], mm["ln"] = mm["winner_name"].map(fold), mm["loser_name"].map(fold)

    # RG codes
    tr = api["code"].map(rg_round)
    api["tour_l"], api["draw"], api["round"] = tr.str[0], tr.str[1], tr.str[2]
    api["name"] = (api["first"].fillna("") + " " + api["last"].fillna("")).map(fold)
    piv = api.pivot_table(index=["year", "code", "tour_l", "draw", "round"], columns="team", values="name",
                          aggfunc="first").reset_index().rename(columns={"A": "n1", "B": "n2"})
    wa = api[api["team"].eq("A")].set_index(["year", "code"])["winner"]
    wb = api[api["team"].eq("B")].set_index(["year", "code"])["winner"]
    piv["win1"] = [wa.get((y, c)) for y, c in zip(piv["year"], piv["code"])]
    piv["win2"] = [wb.get((y, c)) for y, c in zip(piv["year"], piv["code"])]
    groups = {k: g for k, g in piv.groupby(["year", "tour_l", "draw", "round"])}
    out = []
    for x in mm.itertuples(index=False):
        cand = groups.get((x.year, x.tour_l, x.draw, x.round))
        scored = []
        if cand is not None:
            for c in cand.itertuples(index=False):
                for orient, (a, b) in (("12", (c.n1, c.n2)), ("21", (c.n2, c.n1))):
                    s1, s2 = sim(x.wn, a), sim(x.ln, b)
                    scored.append(((min(s1, s2), s1 + s2), c.code, orient, c.win1, c.win2))
        scored.sort(key=lambda t: t[0], reverse=True)
        if not scored or scored[0][0][0] < 1:
            out.append({"match_id": x.match_id, "code": None, "orient": None, "lscore": None, "tie": False})
            continue
        best = scored[0]
        tie = any(s[0] == best[0] and (s[1] != best[1] or s[2] != best[2]) for s in scored[1:])
        rg_w_is = ("1" if best[3] is True else "2" if best[4] is True else None)
        out.append({"match_id": x.match_id, "code": best[1], "orient": best[2], "lscore": best[0][0],
                    "lsum": best[0][1], "tie": tie, "rg_winner_slot": rg_w_is,
                    "winner_agrees": (None if rg_w_is is None else (rg_w_is == best[2][0]))})
    lk = pd.DataFrame(out)
    mm = mm.merge(lk, on="match_id", how="left")
    report["unlinked"] = mm[mm["code"].isna()][["match_id", "winner_name", "loser_name", "raw_score"]].to_dict("records")
    report["ties"] = mm[mm["tie"].fillna(False)][["match_id", "code"]].to_dict("records")
    report["winner_disagrees"] = mm[mm["winner_agrees"].eq(False)][["match_id", "code", "winner_name", "loser_name",
                                                                      "raw_score"]].to_dict("records")
    report["winner_unknown_in_rg"] = mm[mm["code"].notna() & mm["winner_agrees"].isna()][
        ["match_id", "code", "raw_score"]].to_dict("records")
    report["link_score_counts"] = mm["lscore"].value_counts(dropna=False).to_dict()
    dup = mm[mm["code"].notna()].duplicated(["year", "code"], keep=False)
    report["codes_used_twice"] = mm[mm["code"].notna()][dup][["match_id", "code"]].to_dict("records")

    # one row per raw side
    a_idx = api.set_index(["year", "code", "team"])
    mbc = mb_counts(pts)
    mbi = mbc.set_index(["year", "code", "slot"])
    meta_ok = meta[meta["problem"].isna()].set_index(["year", "code"])
    ksi = ks[ks["problem"].isna()].set_index(["year", "code", "slot"]) if len(ks) else None
    sides = []
    for x in mm.itertuples(index=False):
        for side in ("w", "l"):
            rec = {"match_id": x.match_id, "year": x.year, "tour": x.tour_l, "draw": x.draw, "round": x.round,
                   "side": side, "player": x.winner_name if side == "w" else x.loser_name, "source": x.source,
                   "source_file": x.source_file, "source_row": x.source_row, "status": x.status,
                   "status_detail": x.status_detail, "s0_score": x.score, "raw_score": x.raw_score,
                   "has_box": x.has_box, "box_status": x.box_status, "code": x.code, "orient": x.orient,
                   "lscore": x.lscore, "winner_agrees": x.winner_agrees, "raw_tid": x.tid,
                   "raw_wkey": x.wkey, "raw_lkey": x.lkey, "raw_winner_name": x.winner_name,
                   "raw_loser_name": x.loser_name, "raw_round": x.raw_round, "raw_tour": x.raw_tour,
                   "raw_source": x.raw_source}
            for c in NINE:
                v = getattr(x, f"{side}_{c}")
                rec[f"raw_{c}"] = pd.to_numeric(v, errors="coerce") if v not in (None, "", "nan") else np.nan
            if isinstance(x.code, str):
                team = ("A" if x.orient == "12" else "B") if side == "w" else ("B" if x.orient == "12" else "A")
                oteam = "B" if team == "A" else "A"
                me, op = a_idx.loc[(x.year, x.code, team)], a_idx.loc[(x.year, x.code, oteam)]
                rec.update({"team": team, "rg_name": f"{me['first']} {me['last']}", "rg_winner": me["winner"],
                            "rg_end_cause": me["end_cause"], "rg_opp_end_cause": me["opp_end_cause"],
                            "rg_status": me["status"], "rg_status_label": me["status_label"],
                            "rg_court": me["court"], "rg_has_stats": me["has_stats"],
                            "rg_set_games": me["set_games"], "rg_set_tb": me["set_tb"],
                            "rg_opp_set_games": me["opp_set_games"], "rg_opp_set_tb": me["opp_set_tb"],
                            "rg_duration": me["duration"],
                            "my_ace": me["ace"], "my_df": me["df"], "my_svpt": me["svpt"], "my_1stIn": me["first_in"],
                            "my_1stWon": me["first_won"], "my_2ndWon": me["second_won"],
                            "my_bpFaced": op["bp_opps"],
                            "my_bpSaved": (op["bp_opps"] - op["bp_won"]) if pd.notna(op["bp_opps"]) else np.nan,
                            "rg_first_won_den": me["first_won_den"], "rg_second_won_den": me["second_won_den"],
                            "rg_ret_won": me["ret_won"], "rg_ret_den": me["ret_den"], "rg_total_won": me["total_won"],
                            "rg_opp_svpt": op["svpt"], "rg_set_svpt": me["set_svpt"], "rg_set_first_in": me["set_first_in"],
                            "rg_set_ace": me["set_ace"], "rg_set_df": me["set_df"], "rg_n_set_blocks": me["n_set_blocks"]})
                # MatchBeats slot by name
                if (x.year, x.code) in meta_ok.index:
                    mt = meta_ok.loc[(x.year, x.code)]
                    nm = fold(rec["rg_name"])
                    s1 = sim(nm, fold(f"{mt['p1_first']} {mt['p1_last']}"))
                    s2 = sim(nm, fold(f"{mt['p2_first']} {mt['p2_last']}"))
                    slot = 1 if (s1 > s2 and s1 >= 1) else 2 if (s2 > s1 and s2 >= 1) else None
                    rec.update({"mb_slot": slot, "mb_pair": max(s1, s2), "mb_complete": mt["complete"],
                                "mb_status": mt["status"], "mb_winner_slot": mt["winner_slot"], "mb_route": mt["route"]})
                    if slot is not None and (x.year, x.code, slot) in mbi.index:
                        rec.update(mbi.loc[(x.year, x.code, slot)].to_dict())
                        if ksi is not None and (x.year, x.code, slot) in ksi.index:
                            kk = ksi.loc[(x.year, x.code, slot)]
                            rec.update({c: kk[c] for c in kk.index if c.startswith("ks_")})
            sides.append(rec)
    sd = pd.DataFrame(sides)
    # MatchBeats complete for both players of the match (same serve points as RG's statistics)
    sd["mb_complete_side"] = sd["mb_svpt"].eq(sd["my_svpt"])
    sd["mb_complete_match"] = sd.groupby("match_id")["mb_complete_side"].transform("all")
    sd["mb_short_side"] = sd["mb_svpt"].gt(sd["my_svpt"])           # MatchBeats holds more serve points than RG
    sd["my_SvGms"] = np.where(sd["mb_complete_match"], sd["mb_sv_gms_regular"], np.nan)
    sd.to_parquet(OUT / "players.parquet", index=False)
    report["player_rows"] = int(len(sd))
    report["player_rows_by_year"] = sd.groupby("year").size().to_dict()
    report["mb_slot_unpaired"] = int((sd["code"].notna() & sd["mb_slot"].isna() & sd["mb_route"].notna()).sum()) \
        if "mb_route" in sd else None
    (OUT / "link_report.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, list) else (len(v), v[:5])) for k, v in report.items()}, indent=1,
                     default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
