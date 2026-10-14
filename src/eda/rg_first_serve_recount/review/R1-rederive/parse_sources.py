"""R1-rederive (independent reviewer): parse the raw venue records myself.

Reads only raw files (no code or table of src/eda/rg_first_serve_recount/ is used):
  * rolandgarros.com match documents     data/raw/point_sources/rolandgarros/matches/<year>/<code>.json.gz
  * Infosys MatchBeats envelopes (RG)    data/raw/point_sources/infosys_slams/RG/<year>/<route>/<code>.json.gz
    (2019-2024 route match-beats; 2025 route match-centre, which also carries the key statistics block)
  * Infosys MatchBeats envelopes (AO25)  data/raw/point_sources/infosys_slams/AO/2025/match-beats/<code>.json.gz
  * Paris 2024 Olympic results files     data/raw/point_sources/olympics/OG2024/RES_ByRSC_H2H/<unit>.json.gz
The Infosys envelopes are opened with the adapter's decrypt() and blocks_of() (the site's own decryption step);
everything after the decryption (the point recount) is my own code.

Writes (data/studies/rg_first_serve_recount/review/R1-rederive/work/):
  rg_api.parquet      one row per RG document and team (A/B): names, ids, winner flag, end cause, the match statistics
                      as Sackmann's counts, the document's own consistency checks, per-set sums
  mb_points.parquet   one row per RG/AO MatchBeats file and team (1/2): my recount of every point served by that team
  rg_ks25.parquet     RG 2025 key statistics (match-centre 'stats' block, set0), one row per file and player
  ol_stats.parquet    one row per Olympic unit and athlete: the TOT statistics as Sackmann's counts + consistency checks
  ol_pbp.parquet      one row per Olympic unit and athlete: my recount of the play-by-play

Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/parse_sources.py
"""
from __future__ import annotations

import glob
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.ingest.point_sources.infosys_slams import blocks_of, decrypt  # noqa: E402  (the site's own decryption)

RAW = ROOT / "data" / "raw" / "point_sources"
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive" / "work"
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


def frac(text) -> tuple[float, float]:
    m = FRAC.match(str(text or ""))
    return (float(m.group(1)), float(m.group(2))) if m else (float("nan"), float("nan"))


def whole(text) -> float:
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return float("nan")


def load_json_gz(path: str):
    with gzip.open(path, "rb") as fh:
        return json.loads(fh.read())


def code_round(code: str) -> str:
    """RG's match numbering (SM/SD 001 the final ... 064-127 the first round; QM/QD 016-031 the last qualifying round)."""
    fam, n = code[:2], int(code[2:])
    if fam in ("SM", "SD"):
        for first, k, rnd in ((1, 1, "F"), (2, 2, "SF"), (4, 4, "QF"), (8, 8, "R16"), (16, 16, "R32"), (32, 32, "R64"),
                              (64, 64, "R128")):
            if first <= n < first + k:
                return rnd
    else:
        for first, k, rnd in ((16, 16, "Q3"), (32, 32, "Q2"), (64, 64, "Q1")):
            if first <= n < first + k:
                return rnd
    return "?"


# ---------------------------------------------------------------------------------------------------------------
# rolandgarros.com match documents
# ---------------------------------------------------------------------------------------------------------------
def team_counts(stats: dict, mine: str, theirs: str) -> dict:
    """Sackmann's counts for one team of an RG statistics block ('teamAValue' / 'teamBValue')."""
    def val(key, side):
        return (stats.get(key) or {}).get(side)
    fi, sv = frac(val("firstServeRateIn", mine))
    w1, w1d = frac(val("winRateOnFirstServe", mine))
    w2, w2d = frac(val("winRateOnSecondServe", mine))
    bpw_opp, bpo_opp = frac(val("breakPoint", theirs))      # the opponent's break points won on my serve
    bpw_me, bpo_me = frac(val("breakPoint", mine))
    rw, rd = frac(val("returnPoints", mine))
    orw, ord_ = frac(val("returnPoints", theirs))
    return {"ace": whole(val("aces", mine)), "df": whole(val("doubleFaults", mine)), "svpt": sv, "first_in": fi,
            "first_won": w1, "second_won": w2, "bp_faced": bpo_opp, "bp_saved": bpo_opp - bpw_opp,
            "w1_den": w1d, "w2_den": w2d, "ret_won": rw, "ret_den": rd, "opp_ret_won": orw, "opp_ret_den": ord_,
            "bp_won": bpw_me, "bp_chances": bpo_me, "tpw": whole(val("totalPointsWon", mine))}


def parse_rg_api() -> pd.DataFrame:
    rows = []
    for path in sorted(glob.glob(str(RAW / "rolandgarros" / "matches" / "*" / "*.json.gz"))):
        year, code = int(Path(path).parent.name), Path(path).name.split(".")[0]
        d = load_json_gz(path)
        m = d.get("match") or {}
        md = m.get("matchData") or {}
        mss = d.get("matchStatisticsSection") or {}
        ms = mss.get("matchStatistics") or {}
        has_stats = bool(ms) and "firstServeRateIn" in ms
        sets = {}
        for k in range(1, 6):
            s = mss.get(f"setStatistics{k}")
            if isinstance(s, dict) and "firstServeRateIn" in s:
                sets[k] = s
        for t, mine, theirs in (("A", "teamAValue", "teamBValue"), ("B", "teamBValue", "teamAValue")):
            team = m.get(f"team{t}") or {}
            pl = (team.get("players") or [{}])[0]
            r = {"year": year, "code": code, "family": code[:2], "round_code": code_round(code),
                 "round_api": md.get("round"), "round_label": md.get("roundLabel"), "status": md.get("status"),
                 "type_label": md.get("typeLabel"), "minutes": md.get("durationInMinutes"),
                 "team": t, "player_id": str(pl.get("id")), "first_name": pl.get("firstName"),
                 "last_name": pl.get("lastName"), "country": pl.get("country"), "winner": bool(team.get("winner")),
                 "end_cause": team.get("endCause") or "", "games": ",".join(str(s.get("score")) for s in team.get("sets") or []),
                 "n_players": len(team.get("players") or []), "has_stats": has_stats, "n_sets_stats": len(sets)}
            if has_stats:
                r.update(team_counts(ms, mine, theirs))
                # per-set sums of the same counts (the document's set blocks)
                tot = Counter()
                for s in sets.values():
                    c = team_counts(s, mine, theirs)
                    for k in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"):
                        tot[k] += c[k]
                for k in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"):
                    r[f"sets_{k}"] = tot[k] if sets else float("nan")
            rows.append(r)
    df = pd.DataFrame(rows)
    # the document's own consistency checks, per team (the opponent's serve points come from the other team's row)
    opp = df.set_index(["year", "code", "team"])[["svpt"]].rename(columns={"svpt": "opp_svpt"})
    df["opp_team"] = df["team"].map({"A": "B", "B": "A"})
    df = df.join(opp, on=["year", "code", "opp_team"])
    df["chk_w1_den"] = df["w1_den"].eq(df["first_in"])
    df["chk_w2_den"] = df["w2_den"].eq(df["svpt"] - df["first_in"])
    df["chk_ret_den"] = df["ret_den"].eq(df["opp_svpt"])
    df["chk_tpw"] = df["tpw"].eq(df["first_won"] + df["second_won"] + df["ret_won"])
    df["chk_order"] = (df["first_won"] <= df["first_in"]) & (df["first_in"] <= df["svpt"]) & \
        (df["second_won"] <= df["svpt"] - df["first_in"]) & (df["df"] <= df["svpt"] - df["first_in"])
    df["chk_sets"] = True
    for k in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"):
        df["chk_sets"] &= df[f"sets_{k}"].eq(df[k])
    df["chk_all"] = df[["chk_w1_den", "chk_w2_den", "chk_ret_den", "chk_tpw", "chk_order"]].all(axis=1) & df["has_stats"]
    return df


# ---------------------------------------------------------------------------------------------------------------
# Infosys MatchBeats (decrypted with the adapter's decrypt, recounted here)
# ---------------------------------------------------------------------------------------------------------------
def recount_mb(mb: dict) -> tuple[dict, dict]:
    """Per team (1/2): every point the team served. Returns (per-team counts, file facts)."""
    cnt = {t: Counter() for t in ("1", "2")}
    facts = Counter()
    seen = set()
    for st in mb.get("setData") or []:
        for g in st.get("gameData") or []:
            for p in g.get("pointData") or []:
                facts["points"] += 1
                pid = p.get("pointId")
                if pid in seen:
                    facts["dup_ids"] += 1
                seen.add(pid)
                srv, serve, scorer, res = str(p.get("server")), p.get("serve"), str(p.get("scorer")), p.get("result")
                if srv not in cnt or serve not in (1, 2, "1", "2") or scorer not in ("1", "2"):
                    facts["odd_points"] += 1
                    continue
                serve = int(serve)
                c = cnt[srv]
                c["svpt"] += 1
                won = scorer == srv
                if serve == 1:
                    c["first_in"] += 1
                    c["first_won"] += won
                else:
                    c["second_pts"] += 1
                    c["second_won"] += won
                c["ace"] += res == "A"
                c["df"] += res == "DF"
                if res == "DF" and (serve != 2 or won):
                    facts["odd_df"] += 1
                if res == "A" and not won:
                    facts["odd_ace"] += 1
    return cnt, facts


def parse_mb() -> pd.DataFrame:
    rows = []
    specs = [("RG", y, "match-beats") for y in range(2019, 2025)] + [("RG", 2025, "match-centre"),
                                                                      ("AO", 2025, "match-beats")]
    for slam, year, route in specs:
        for path in sorted(glob.glob(str(RAW / "infosys_slams" / slam / str(year) / route / "*.json.gz"))):
            code = Path(path).name.split(".")[0]
            base = {"slam": slam, "year": year, "route": route, "code": code}
            try:
                blocks = blocks_of(route, load_json_gz(path))
                env = blocks.get("mbData")
                mb = decrypt(env) if isinstance(env, dict) else None
            except Exception as e:  # noqa: BLE001  (recorded, not hidden)
                rows.append({**base, "team": None, "mb_status": f"decrypt_failed: {e}"})
                continue
            if not isinstance(mb, dict) or not mb.get("setData"):
                rows.append({**base, "team": None, "mb_status": "empty"})
                continue
            cnt, facts = recount_mb(mb)
            pdx = mb.get("playerData") or {}
            for t in ("1", "2"):
                rows.append({**base, "team": t, "mb_status": "ok", "is_complete": mb.get("isMatchComplete"),
                             "match_status": mb.get("matchStatus"), "match_winner": str(mb.get("matchWinner")),
                             "sets_complete": mb.get("setsComplete"), "event_type": mb.get("eventType"),
                             "mb_match_id": mb.get("matchId"), "mb_year": mb.get("year"),
                             "player_id": str(pdx.get(f"tm{t}Ply1Id")), "mb_name": pdx.get(f"tm{t}Ply1Name"),
                             "mb_first": pdx.get(f"tm{t}Ply1FirstName"), "mb_last": pdx.get(f"tm{t}Ply1LastName"),
                             **{f"mb_{k}": cnt[t][k] for k in ("svpt", "first_in", "first_won", "second_pts",
                                                               "second_won", "ace", "df")},
                             **{f"file_{k}": facts[k] for k in ("points", "dup_ids", "odd_points", "odd_df", "odd_ace")}})
    return pd.DataFrame(rows)


def parse_ks25() -> pd.DataFrame:
    """RG 2025's key statistics block (match-centre file), set0 = the match."""
    names = {"Aces": "ace", "Double Faults": "df", "First Serve": "first", "Win On 1st Serve": "w1",
             "Win On 2nd Serve": "w2", "Break Points Won": "bpw", "Receiving Points Won": "ret",
             "Total Points Won": "tpw"}
    rows = []
    for path in sorted(glob.glob(str(RAW / "infosys_slams" / "RG" / "2025" / "match-centre" / "*.json.gz"))):
        code = Path(path).name.split(".")[0]
        try:
            st = decrypt(blocks_of("match-centre", load_json_gz(path)).get("stats") or {})
        except Exception as e:  # noqa: BLE001
            rows.append({"year": 2025, "code": code, "ks_status": f"decrypt_failed: {e}"})
            continue
        if not isinstance(st, dict) or not (st.get("setStats") or {}).get("set0"):
            rows.append({"year": 2025, "code": code, "ks_status": "empty"})
            continue
        ent = {e.get("name"): e for e in st["setStats"]["set0"]}
        players = st.get("players") or [{}, {}]
        for i, side in ((0, "player1"), (1, "player2")):
            other = "player2" if side == "player1" else "player1"
            g = lambda n, s=side: (ent.get(n) or {}).get(s)  # noqa: E731
            fi, sv = frac(g("First Serve"))
            w1, w1d = frac(g("Win On 1st Serve"))
            w2, w2d = frac(g("Win On 2nd Serve"))
            obw, obo = frac((ent.get("Break Points Won") or {}).get(other))
            rows.append({"year": 2025, "code": code, "ks_status": "ok", "ks_team": str(i + 1),
                         "player_id": str((players[i] if i < len(players) else {}).get("player1Id")),
                         "ks_ace": whole(g("Aces")), "ks_df": whole(g("Double Faults")), "ks_svpt": sv,
                         "ks_first_in": fi, "ks_first_won": w1, "ks_second_won": w2, "ks_w1_den": w1d,
                         "ks_w2_den": w2d, "ks_bp_faced": obo, "ks_bp_saved": obo - obw,
                         "ks_complete": st.get("matchCompleted")})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------
# Paris 2024 Olympic results files
# ---------------------------------------------------------------------------------------------------------------
def parse_olympics() -> tuple[pd.DataFrame, pd.DataFrame]:
    srows, prows = [], []
    for path in sorted(glob.glob(str(RAW / "olympics" / "OG2024" / "RES_ByRSC_H2H" / "*.json.gz"))):
        r = load_json_gz(path)["results"]
        unit = r.get("eventUnitCode")
        ext = {e.get("ei_code"): e.get("ei_value") for e in r.get("extendedInfos") or []}
        base = {"unit": unit, "file": Path(path).name, "gender": "M" if unit.startswith("TENM") else "W",
                "round_desc": (r.get("eventUnit") or {}).get("shortDescription"),
                "status": (r.get("status") or {}).get("code"), "match_status": ext.get("MATCH_STATUS"),
                "final_result": ext.get("FINAL_RESULT")}
        items = r.get("items") or []
        codes = [it.get("participant", {}).get("code") or it.get("athleteCode") for it in items]
        for it in items:
            p = it.get("participant") or {}
            tot = {s.get("code"): s for s in it.get("statsItems") or [] if s.get("pos") == "TOT"}
            def v(code, field="value"):
                return whole((tot.get(code) or {}).get(field))
            def ex(code, sub):
                for e in (tot.get(code) or {}).get("extendedStatsItems") or []:
                    if e.get("code") == sub:
                        return whole(e.get("value"))
                return float("nan")
            row = {**base, "athlete": p.get("code") or it.get("athleteCode"), "name": p.get("name"),
                   "given": p.get("givenName"), "family": p.get("familyName"),
                   "org": (p.get("organisation") or {}).get("code"), "wlt": it.get("resultWLT"),
                   "ace": v("ACES"), "df": v("DBL_FAULT"), "svpt": v("1ST_SERVE", "attempt"),
                   "first_in": v("1ST_SERVE"), "first_won": ex("1ST_SERVE", "POINTS_WON"),
                   "second_att": v("2ND_SERVE", "attempt"), "second_in": v("2ND_SERVE"),
                   "second_won": ex("2ND_SERVE", "POINTS_WON"), "ace1": ex("1ST_SERVE", "ACE"),
                   "ace2": ex("2ND_SERVE", "ACE"), "bp_won": v("BREAK_PTS"), "bp_chances": v("BREAK_PTS", "attempt"),
                   "ret_won": v("RECEIVE"), "ret_den": v("RECEIVE", "attempt"), "psw": v("PTS_WON_SERVE"),
                   "psw_den": v("PTS_WON_SERVE", "attempt"), "points": v("POINTS")}
            srows.append(row)
        # play-by-play recount, per server
        cnt = {c: Counter() for c in codes}
        odd = 0
        for per in r.get("playByPlay") or []:
            for a in per.get("actions") or []:
                srv = [e.get("pbpea_value") for e in a.get("extendedActions") or [] if e.get("pbpea_code") == "SERVER"]
                res = a.get("pbpa_Result")
                if len(srv) != 1 or srv[0] not in cnt or res not in ("PS1", "PR1", "PS2", "PR2", "A1", "A2", "DF"):
                    odd += 1
                    continue
                c = cnt[srv[0]]
                c["svpt"] += 1
                c["first_in"] += res in ("PS1", "PR1", "A1")
                c["first_won"] += res in ("PS1", "A1")
                c["second_won"] += res in ("PS2", "A2")
                c["ace"] += res in ("A1", "A2")
                c["df"] += res == "DF"
        for c in codes:
            prows.append({"unit": unit, "athlete": c, "pbp_odd": odd,
                          **{f"pbp_{k}": cnt[c][k] for k in ("svpt", "first_in", "first_won", "second_won", "ace", "df")}})
    st = pd.DataFrame(srows)
    opp = st.set_index(["unit", "athlete"])
    pairs = st.groupby("unit")["athlete"].apply(list).to_dict()
    st["opp_athlete"] = [next((a for a in pairs[u] if a != me), None) for u, me in zip(st["unit"], st["athlete"])]
    st["opp_svpt"] = [opp["svpt"].get((u, a), float("nan")) for u, a in zip(st["unit"], st["opp_athlete"])]
    st["opp_bp_won"] = [opp["bp_won"].get((u, a), float("nan")) for u, a in zip(st["unit"], st["opp_athlete"])]
    st["opp_bp_chances"] = [opp["bp_chances"].get((u, a), float("nan")) for u, a in zip(st["unit"], st["opp_athlete"])]
    st["bp_faced"] = st["opp_bp_chances"]
    st["bp_saved"] = st["opp_bp_chances"] - st["opp_bp_won"]
    st["chk_official"] = st["status"].eq("OFFICIAL")
    st["chk_psw"] = st["psw"].eq(st["first_won"] + st["second_won"]) & st["psw_den"].eq(st["svpt"])
    st["chk_2nd_att"] = st["second_att"].eq(st["svpt"] - st["first_in"])
    st["chk_df"] = st["df"].eq(st["second_att"] - st["second_in"])
    st["chk_ret_den"] = st["ret_den"].eq(st["opp_svpt"])
    st["chk_points"] = st["points"].eq(st["psw"] + st["ret_won"])
    st["chk_aces"] = st["ace"].eq(st["ace1"] + st["ace2"])
    st["chk_all"] = st[["chk_official", "chk_psw", "chk_2nd_att"]].all(axis=1)
    return st, pd.DataFrame(prows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    api = parse_rg_api()
    api.to_parquet(OUT / "rg_api.parquet", index=False)
    print("rg_api", api.shape, api.groupby("year").size().to_dict())
    mb = parse_mb()
    mb.to_parquet(OUT / "mb_points.parquet", index=False)
    print("mb", mb.shape, mb.groupby(["slam", "year", "mb_status"]).size().to_dict())
    ks = parse_ks25()
    ks.to_parquet(OUT / "rg_ks25.parquet", index=False)
    print("ks25", ks.shape, ks["ks_status"].value_counts().to_dict())
    ol, pbp = parse_olympics()
    ol.to_parquet(OUT / "ol_stats.parquet", index=False)
    pbp.to_parquet(OUT / "ol_pbp.parquet", index=False)
    print("olympics", ol.shape, pbp.shape)


if __name__ == "__main__":
    main()
