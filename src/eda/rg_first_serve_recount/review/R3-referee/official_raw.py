"""R3-referee, step 2: the proposed values against the official records' raw files, read here without the lead's code.

For every raw match row of proposed_corrections.csv:
  * Roland Garros: data/raw/point_sources/rolandgarros/matches/<year>/<code>.json.gz (rolandgarros.com's match API),
    the code taken from proposed_rows.csv (the lead's link) and checked here: the code's round (the adapter's
    round_lookup), both names, which team won, and the score in sets and games must equal the Sackmann row's.
    Counts from matchStatisticsSection.matchStatistics: "first serve" in/served, "win on 1st serve" won/in, "win on
    2nd serve" won/(served - in), aces, double faults, the opponent's "break points won", "receiving points won",
    "total points won", with the record's own consistency checks.
    RG's MatchBeats (data/raw/point_sources/infosys_slams/RG/<year>/<route>/<code>.json.gz, decrypted with the
    adapter's decrypt and blocks_of) is recounted point by point: serve points, points played on serve 1, won on each.
  * Olympics: data/raw/point_sources/olympics/OG2024/RES_ByRSC_H2H/<unit>.json.gz: status, names, W/L, round, score
    (periods), 1ST_SERVE value/attempt and POINTS_WON, 2ND_SERVE POINTS_WON, ACES, DBL_FAULT, PTS_WON_SERVE, and the
    play-by-play recounted (results PS1/PS2/PR1/PR2/A1/A2/DF, server from the SERVER field).

Writes data/studies/rg_first_serve_recount/review/R3-referee/official_sides.csv (one row per proposed side with every
value) and official_summary.json. Usage: ./python.sh src/eda/rg_first_serve_recount/review/R3-referee/official_raw.py
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.point_sources import infosys_slams as I  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R3-referee"
STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"
RAW = ROOT / "data" / "raw" / "point_sources"
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
OG_ROUND = {"First Round": "R64", "Second Round": "R32", "Third Round": "R16", "Quarterfinal": "QF",
            "Quarter-final": "QF", "Semifinal": "SF", "Semi-final": "SF", "Gold Medal Match": "F",
            "Bronze Medal Match": "BR"}


def fold(name) -> list[str]:
    s = unicodedata.normalize("NFKD", str(name or "")).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s).split()


def name_ok(a, b) -> int:
    """2: same words (any order) or same letters; 1: a shared word of 3+ letters; 0: none."""
    ta, tb = fold(a), fold(b)
    if sorted(ta) == sorted(tb) or "".join(sorted(ta)) == "".join(sorted(tb)) or "".join(ta) == "".join(tb):
        return 2
    return 1 if {t for t in ta if len(t) >= 3} & {t for t in tb if len(t) >= 3} else 0


def iv(v):
    """A raw count as a whole number, None when blank."""
    t = str(v).strip() if v is not None else ""
    return int(float(t)) if t not in ("", "nan", "None") else None


def frac(v):
    m = FRAC.match(str(v)) if v is not None else None
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def sack_sets(score: str) -> list[tuple[int, int]]:
    out = []
    for tok in str(score).split():
        m = re.match(r"^(\d+)-(\d+)", tok)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return out


# ------------------------------------------------------------------------------------------------ Roland Garros
def rg_doc(year: int, code: str) -> dict:
    return json.load(gzip.open(RAW / "rolandgarros" / "matches" / str(year) / f"{code}.json.gz"))


def rg_teams(doc: dict) -> dict:
    m = doc["match"]
    st = (doc.get("matchStatisticsSection") or {}).get("matchStatistics") or {}
    out = {}
    for t, o in (("A", "B"), ("B", "A")):
        team = m[f"team{t}"]
        p = team["players"][0] if team.get("players") else {}
        v = lambda k, side=t: (st.get(k) or {}).get(f"team{side}Value")
        fi, sv = frac(v("firstServeRateIn"))
        fw, fwd = frac(v("winRateOnFirstServe"))
        sw, swd = frac(v("winRateOnSecondServe"))
        obw, obo = frac(v("breakPoint", o))
        rw, rd = frac(v("returnPoints"))
        out[t] = {"name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(), "winner": bool(team.get("winner")),
                  "sets": [(s.get("score"), s.get("tieBreak")) for s in team.get("sets") or []],
                  "end_cause": team.get("endCause"),
                  "ace": int(v("aces")) if v("aces") not in (None, "") else None,
                  "df": int(v("doubleFaults")) if v("doubleFaults") not in (None, "") else None,
                  "svpt": sv, "first_in": fi, "first_won": fw, "first_won_den": fwd, "second_won": sw,
                  "second_won_den": swd, "bp_faced": obo, "bp_saved": None if obo is None else obo - obw,
                  "ret_won": rw, "ret_den": rd,
                  "total_won": int(v("totalPointsWon")) if v("totalPointsWon") not in (None, "") else None}
    for t, o in (("A", "B"), ("B", "A")):
        x, y = out[t], out[o]
        x["consistent"] = bool(x["svpt"] is not None and x["first_won_den"] == x["first_in"]
                               and x["second_won_den"] == x["svpt"] - x["first_in"] and x["ret_den"] == y["svpt"]
                               and x["total_won"] == x["first_won"] + x["second_won"] + x["ret_won"])
    out["round_label"] = m["matchData"].get("roundLabel")
    out["status"] = m["matchData"].get("status")
    return out


def mb_counts(year: int, code: str) -> dict | None:
    """RG's MatchBeats recounted per player slot: the static file where held, else the match-centre file, else the
    API file. Returns {'route', 'complete', 'p1': {...}, 'p2': {...}} or None."""
    base = RAW / "infosys_slams" / "RG" / str(year)
    for route in ("match-beats", "match-centre", "match-beats-api"):
        f = base / route / f"{code}.json.gz"
        if not f.exists():
            continue
        blocks = I.blocks_of(route, json.load(gzip.open(f)))
        if "mbData" not in blocks:
            continue
        doc = I.decrypt(blocks["mbData"])
        if not isinstance(doc, dict) or not doc.get("setData"):
            continue
        pts = [p for s in doc["setData"] for g in (s.get("gameData") or []) for p in (g.get("pointData") or [])]
        pdat = doc.get("playerData") or {}
        res = {"route": route, "complete": doc.get("isMatchComplete"), "points": len(pts)}
        for k in ("1", "2"):
            mine = [p for p in pts if str(p.get("server")) == k]
            res[f"p{k}"] = {"name": f"{pdat.get(f'tm{k}Ply1FirstName') or ''} {pdat.get(f'tm{k}Ply1LastName') or ''}",
                            "svpt": len(mine), "first_in": sum(str(p.get("serve")) == "1" for p in mine),
                            "first_won": sum(str(p.get("serve")) == "1" and str(p.get("scorer")) == k for p in mine),
                            "second_won": sum(str(p.get("serve")) == "2" and str(p.get("scorer")) == k for p in mine),
                            "serve_other": sum(str(p.get("serve")) not in ("1", "2") for p in mine),
                            "ace": sum(p.get("result") == "A" for p in mine),
                            "df": sum(p.get("result") == "DF" for p in mine)}
        return res
    return None


# ------------------------------------------------------------------------------------------------ Olympics
def og_doc(unit: str) -> dict:
    return json.loads(gzip.open(RAW / "olympics" / "OG2024" / "RES_ByRSC_H2H" / f"{unit}.json.gz").read())["results"]


def og_players(r: dict) -> dict:
    out = {}
    for it in r.get("items") or []:
        code = it.get("athleteCode")
        tot = {s["code"]: s for s in it.get("statsItems") or [] if s.get("pos") == "TOT"}
        def val(c, f="value"):
            x = (tot.get(c) or {}).get(f)
            return int(x) if x not in (None, "") else None
        def ext(c, k):
            for e in (tot.get(c) or {}).get("extendedStatsItems") or []:
                if e.get("code") == k:
                    return int(e["value"]) if e.get("value") not in (None, "") else None
            return None
        out[code] = {"name": (it.get("participant") or {}).get("name"), "wlt": it.get("resultWLT"),
                     "sort": it.get("sortOrder"), "svpt": val("1ST_SERVE", "attempt"), "first_in": val("1ST_SERVE"),
                     "first_won": ext("1ST_SERVE", "POINTS_WON"), "second_won": ext("2ND_SERVE", "POINTS_WON"),
                     "second_served": val("2ND_SERVE", "attempt"), "second_in": val("2ND_SERVE"),
                     "ace": val("ACES"), "df": val("DBL_FAULT"), "spw": val("PTS_WON_SERVE"),
                     "spw_den": val("PTS_WON_SERVE", "attempt"), "bp_won": val("BREAK_PTS"),
                     "bp_opps": val("BREAK_PTS", "attempt"), "first_aces": ext("1ST_SERVE", "ACE"),
                     "second_aces": ext("2ND_SERVE", "ACE")}
    codes = list(out)
    for c in codes:
        o = [x for x in codes if x != c]
        if o:
            out[c]["bp_faced"] = out[o[0]]["bp_opps"]
            out[c]["bp_saved"] = None if out[o[0]]["bp_opps"] is None else out[o[0]]["bp_opps"] - out[o[0]]["bp_won"]
    # the play-by-play recounted per server
    pbp = {c: {"svpt": 0, "first_in": 0, "first_won": 0, "second_won": 0, "ace": 0, "df": 0, "unknown": 0}
           for c in codes}
    for per in r.get("playByPlay") or []:
        for a in per.get("actions") or []:
            res = a.get("pbpa_Result")
            server = next((e.get("pbpea_value") for e in a.get("extendedActions") or [] if e.get("pbpea_code") == "SERVER"),
                          None)
            if res is None or server not in pbp:
                continue
            c = pbp[server]
            c["svpt"] += 1
            c["first_in"] += res in ("PS1", "PR1", "A1")
            c["first_won"] += res in ("PS1", "A1")
            c["second_won"] += res in ("PS2", "A2")
            c["ace"] += res in ("A1", "A2")
            c["df"] += res == "DF"
            c["unknown"] += res not in ("PS1", "PR1", "A1", "PS2", "PR2", "A2", "DF")
    for c in codes:
        out[c]["pbp"] = pbp[c]
    return out


def main() -> int:
    prop = pd.read_csv(STUDY / "proposed_corrections.csv", dtype=str, keep_default_na=False)
    rows = pd.read_csv(STUDY / "proposed_rows.csv", low_memory=False)
    raw = pd.read_parquet(OUT / "raw_subset.parquet")
    raw = raw.set_index(["_source_file", "_row"])
    rounds = I.round_lookup()
    out, issues = [], []
    for r in prop.itertuples():
        sf, sr = r.source_file, int(r.source_row)
        g = rows[(rows["source_file"].eq(sf)) & (rows["source_row"].eq(sr))]
        x = raw.loc[(sf, sr)]
        rec0 = {"fix": r.fix, "source_file": sf, "source_row": sr, "winner_name": x["winner_name"],
                "loser_name": x["loser_name"], "round": x["round"], "score": x["score"]}
        sets_s = sack_sets(x["score"])
        if r.fix.startswith("RG"):
            year = int(g["year"].iloc[0])
            code = g["rg_code"].dropna().unique()
            if len(code) != 1:
                issues.append(f"{sf}#{sr}: rg codes {code}")
                continue
            code = code[0]
            t = rg_teams(rg_doc(year, code))
            # which team is the Sackmann winner: by names, then the winner flag as a check
            sc = {tm: (name_ok(t[tm]["name"], x["winner_name"]), name_ok(t[tm]["name"], x["loser_name"])) for tm in "AB"}
            w_team = "A" if sc["A"][0] + sc["B"][1] > sc["B"][0] + sc["A"][1] else "B"
            l_team = "B" if w_team == "A" else "A"
            link = {"code": code, "code_round": rounds.get(("RG", code)), "round_ok": rounds.get(("RG", code)) == x["round"],
                    "w_name_score": sc[w_team][0], "l_name_score": sc[l_team][1],
                    "rg_winner_is_sackmann_winner": t[w_team]["winner"] and not t[l_team]["winner"],
                    "rg_status": t["status"], "rg_end_cause": t[w_team]["end_cause"] or t[l_team]["end_cause"]}
            rg_sets = [(a[0], b[0]) for a, b in zip(t[w_team]["sets"], t[l_team]["sets"])]
            link["score_ok"] = [tuple(int(v) if v is not None else -1 for v in s) for s in rg_sets] == sets_s
            mb = mb_counts(year, code)
            mbmap = {}
            if mb:
                for k in ("1", "2"):
                    s = (name_ok(mb[f"p{k}"]["name"], t["A"]["name"]), name_ok(mb[f"p{k}"]["name"], t["B"]["name"]))
                    mbmap["A" if s[0] > s[1] else "B" if s[1] > s[0] else "?"] = mb[f"p{k}"]
            for side, team in (("w", w_team), ("l", l_team)):
                given = getattr(r, f"{side}_1stIn") != ""
                if not given:
                    continue
                o = t[team]
                m = mbmap.get(team)
                out.append({**rec0, **link, "side": side, "player": x[f"{'winner' if side == 'w' else 'loser'}_name"],
                            "official_name": o["name"],
                            "raw_svpt": iv(x[f"{side}_svpt"]), "raw_ace": iv(x[f"{side}_ace"]), "raw_df": iv(x[f"{side}_df"]),
                            "raw_first_in": iv(x[f"{side}_1stIn"]), "raw_first_won": iv(x[f"{side}_1stWon"]),
                            "raw_second_won": iv(x[f"{side}_2ndWon"]),
                            "prop_first_in": int(float(getattr(r, f"{side}_1stIn"))),
                            "prop_first_won": int(float(getattr(r, f"{side}_1stWon"))),
                            "prop_second_won": int(float(getattr(r, f"{side}_2ndWon"))),
                            "prop_svpt": int(float(getattr(r, f"{side}_svpt"))),
                            "off_svpt": o["svpt"], "off_first_in": o["first_in"], "off_first_won": o["first_won"],
                            "off_second_won": o["second_won"], "off_ace": o["ace"], "off_df": o["df"],
                            "off_bp_faced": o["bp_faced"], "off_bp_saved": o["bp_saved"],
                            "off_consistent": o["consistent"] and t[l_team if team == w_team else w_team]["consistent"],
                            "raw_bp_faced": iv(x[f"{side}_bpFaced"]), "raw_bp_saved": iv(x[f"{side}_bpSaved"]),
                            "second_route": mb["route"] if mb else None, "second_points": mb["points"] if mb else None,
                            **({f"second_{k}": m[k] for k in ("svpt", "first_in", "first_won", "second_won", "ace", "df",
                                                                "serve_other")} if m else {})})
        else:
            unit = g["unit"].dropna().unique()
            if len(unit) != 1:
                issues.append(f"{sf}#{sr}: units {unit}")
                continue
            unit = unit[0]
            doc = og_doc(unit)
            pl = og_players(doc)
            codes = list(pl)
            sc = {c: (name_ok(pl[c]["name"], x["winner_name"]), name_ok(pl[c]["name"], x["loser_name"])) for c in codes}
            w_c = codes[0] if sc[codes[0]][0] + sc[codes[1]][1] > sc[codes[1]][0] + sc[codes[0]][1] else codes[1]
            l_c = codes[1] if w_c == codes[0] else codes[0]
            desc = (doc.get("eventUnit") or {}).get("description", "")
            rnd = next((v for k, v in OG_ROUND.items() if desc.endswith(k)), None)
            # periods: home/away scores; home is the item with sortOrder 1? use the WIN markers and names instead
            per = [(p["home"].get("score"), p["away"].get("score")) for p in doc.get("periods") or []]
            home_is_w = pl[w_c]["sort"] == 1
            lead = lambda v: int(re.match(r"\d+", str(v)).group(0))     # "6(6)": games, then tie-break points
            og_sets = [(lead(h), lead(a)) if home_is_w else (lead(a), lead(h)) for h, a in per if h not in (None, "")]
            link = {"code": unit, "code_round": rnd, "round_ok": rnd == x["round"],
                    "w_name_score": sc[w_c][0], "l_name_score": sc[l_c][1],
                    "rg_winner_is_sackmann_winner": pl[w_c]["wlt"] == "W" and pl[l_c]["wlt"] == "L",
                    "rg_status": (doc.get("status") or {}).get("code"), "score_ok": og_sets == sets_s,
                    "capture_date": doc.get("date")}
            for side, c in (("w", w_c), ("l", l_c)):
                if getattr(r, f"{side}_1stIn") == "":
                    continue
                o = pl[c]
                cons = (link["rg_status"] == "OFFICIAL" and o["spw"] == o["first_won"] + o["second_won"]
                        and o["second_served"] == o["svpt"] - o["first_in"])
                out.append({**rec0, **link, "side": side, "player": x[f"{'winner' if side == 'w' else 'loser'}_name"],
                            "official_name": o["name"],
                            "raw_svpt": iv(x[f"{side}_svpt"]), "raw_ace": iv(x[f"{side}_ace"]), "raw_df": iv(x[f"{side}_df"]),
                            "raw_first_in": iv(x[f"{side}_1stIn"]), "raw_first_won": iv(x[f"{side}_1stWon"]),
                            "raw_second_won": iv(x[f"{side}_2ndWon"]),
                            "prop_first_in": int(float(getattr(r, f"{side}_1stIn"))),
                            "prop_first_won": int(float(getattr(r, f"{side}_1stWon"))),
                            "prop_second_won": int(float(getattr(r, f"{side}_2ndWon"))),
                            "prop_svpt": int(float(getattr(r, f"{side}_svpt"))),
                            "off_svpt": o["svpt"], "off_first_in": o["first_in"], "off_first_won": o["first_won"],
                            "off_second_won": o["second_won"], "off_ace": o["ace"], "off_df": o["df"],
                            "off_bp_faced": o.get("bp_faced"), "off_bp_saved": o.get("bp_saved"),
                            "off_consistent": cons, "off_first_aces": o["first_aces"], "off_second_aces": o["second_aces"],
                            "raw_bp_faced": iv(x[f"{side}_bpFaced"]), "raw_bp_saved": iv(x[f"{side}_bpSaved"]),
                            "second_route": "olympic_pbp", "second_points": None,
                            **{f"second_{k}": o["pbp"][k] for k in ("svpt", "first_in", "first_won", "second_won", "ace",
                                                                     "df")},
                            "second_serve_other": o["pbp"]["unknown"]})
    d = pd.DataFrame(out)
    d["values_equal_official"] = (d["prop_first_in"].eq(d["off_first_in"]) & d["prop_first_won"].eq(d["off_first_won"])
                                  & d["prop_second_won"].eq(d["off_second_won"]))
    d["svpt_equal"] = d["prop_svpt"].eq(d["off_svpt"]) & d["raw_svpt"].eq(d["off_svpt"])
    d["spw_equal"] = (d["raw_first_won"] + d["raw_second_won"]).eq(d["off_first_won"] + d["off_second_won"])
    held = d["second_svpt"].notna()
    complete = held & d["second_svpt"].eq(d["off_svpt"])
    same = complete & d["second_first_in"].eq(d["off_first_in"]) & d["second_first_won"].eq(d["off_first_won"]) \
        & d["second_second_won"].eq(d["off_second_won"])
    d["second_channel"] = np.select([same, complete & ~same, held & ~complete], ["agrees", "contradicts", "incomplete"],
                                    "absent")
    d["sign"] = np.sign(d["raw_first_in"] - d["off_first_in"]).map({1: "+", -1: "-", 0: "0"})
    d["other_diff"] = np.where(d["raw_ace"].ne(d["off_ace"]), "ace ", "") + \
        np.where(d["raw_df"].ne(d["off_df"]), "df ", "") + \
        np.where(d["raw_bp_faced"].ne(d["off_bp_faced"]) | d["raw_bp_saved"].ne(d["off_bp_saved"]), "bp", "")
    d.to_csv(OUT / "official_sides.csv", index=False)
    summ = {"sides": int(len(d)), "issues": issues,
            "by_fix": d.groupby("fix").size().to_dict(),
            "values_equal_official": int(d["values_equal_official"].sum()),
            "svpt_equal": int(d["svpt_equal"].sum()), "spw_equal": int(d["spw_equal"].sum()),
            "official_consistent": int(d["off_consistent"].sum()),
            "round_ok": int(d["round_ok"].sum()), "score_ok": int(d["score_ok"].sum()),
            "winner_ok": int(d["rg_winner_is_sackmann_winner"].sum()),
            "name_scores": d.groupby(["w_name_score", "l_name_score"]).size().rename("sides").reset_index()
            .to_dict("records"),
            "second_channel": d.groupby(["fix", "second_channel"]).size().rename("sides").reset_index().to_dict("records"),
            "sign_by_fix": d.groupby(["fix", "sign"]).size().rename("sides").reset_index().to_dict("records"),
            "other_diff_by_fix": d.groupby(["fix", "other_diff"]).size().rename("sides").reset_index().to_dict("records"),
            "status": d["rg_status"].value_counts().to_dict()}
    (OUT / "official_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1, default=str))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    bad = d[~d["values_equal_official"] | ~d["svpt_equal"] | ~d["spw_equal"] | ~d["off_consistent"] | ~d["round_ok"]
            | ~d["score_ok"] | ~d["rg_winner_is_sackmann_winner"] | (d["w_name_score"] < 1) | (d["l_name_score"] < 1)]
    print(bad[["fix", "source_file", "source_row", "side", "player", "official_name", "code", "round", "code_round",
               "score", "score_ok", "round_ok", "rg_winner_is_sackmann_winner", "w_name_score", "l_name_score",
               "values_equal_official", "svpt_equal", "spw_equal", "off_consistent"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
