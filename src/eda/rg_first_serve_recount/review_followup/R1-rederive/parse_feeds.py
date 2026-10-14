"""R1-rederive (round 2): parse Roland Garros's own records of 2019-2026 myself, from the raw files.

Reads only raw files (no code or table of src/eda/rg_first_serve_recount/ is used):
  * rolandgarros.com match documents   data/raw/point_sources/rolandgarros/matches/<year>/<code>.json.gz   (2019-2026)
  * Infosys MatchBeats envelopes (RG)  data/raw/point_sources/infosys_slams/RG/<year>/<route>/<code>.json.gz
        2019-2024 route match-beats, 2025 match-centre (mbData block), 2026 match-beats-api
  * Infosys key statistics (RG)        2025 match-centre (stats block), 2026 keystats-api
The Infosys envelopes are opened with the adapter's decrypt() and blocks_of() (the site's own decryption step); the
recount after it is my own code.

Writes (data/studies/rg_first_serve_recount/followup/review/R1-rederive/work/):
  rg_api.parquet    one row per document and team (A/B): names, ids, winner flag, end cause, set scores, the match
                    statistics as Sackmann's eight counts, the document's own consistency checks, per-set sums
  mb.parquet        one row per MatchBeats file and team (1/2): my recount of every point the team served, and the
                    games it served: tiebreak games apart, unfinished games apart, games without points apart
  mb_games.parquet  one row per MatchBeats game: set, game, tiebreak flag, server(s) seen, points, winner
  ks.parquet        one row per key-statistics file and player (2025, 2026): the set0 counts as Sackmann's
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/parse_feeds.py
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
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive" / "work"
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]


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
    """RG's numbering: SM/SD 001 the final, 002-003 SF, ... 064-127 R128; QM/QD 016-031 Q3, 032-063 Q2, 064-127 Q1."""
    fam, n = code[:2], int(code[2:])
    table = ((1, 1, "F"), (2, 2, "SF"), (4, 4, "QF"), (8, 8, "R16"), (16, 16, "R32"), (32, 32, "R64"),
             (64, 64, "R128")) if fam in ("SM", "SD") else ((16, 16, "Q3"), (32, 32, "Q2"), (64, 64, "Q1"))
    for first, k, rnd in table:
        if first <= n < first + k:
            return rnd
    return "?"


# ---------------------------------------------------------------------------------------------------------------
# rolandgarros.com match documents
# ---------------------------------------------------------------------------------------------------------------
def team_counts(stats: dict, mine: str, theirs: str) -> dict:
    def val(key, side):
        return (stats.get(key) or {}).get(side)
    fi, sv = frac(val("firstServeRateIn", mine))
    w1, w1d = frac(val("winRateOnFirstServe", mine))
    w2, w2d = frac(val("winRateOnSecondServe", mine))
    bpw_opp, bpo_opp = frac(val("breakPoint", theirs))      # the opponent's break points won on my serve
    bpw_me, bpo_me = frac(val("breakPoint", mine))
    rw, rd = frac(val("returnPoints", mine))
    return {"ace": whole(val("aces", mine)), "df": whole(val("doubleFaults", mine)), "svpt": sv, "first_in": fi,
            "first_won": w1, "second_won": w2, "bp_faced": bpo_opp, "bp_saved": bpo_opp - bpw_opp,
            "w1_den": w1d, "w2_den": w2d, "ret_won": rw, "ret_den": rd, "bp_won": bpw_me, "bp_chances": bpo_me,
            "tpw": whole(val("totalPointsWon", mine))}


def parse_rg_api() -> pd.DataFrame:
    rows = []
    for path in sorted(glob.glob(str(RAW / "rolandgarros" / "matches" / "*" / "*.json.gz"))):
        year, code = int(Path(path).parent.name), Path(path).name.split(".")[0]
        d = load_json_gz(path)
        m = d.get("match") or {}
        md = m.get("matchData") or {}
        mss = d.get("matchStatisticsSection") or {}
        ms = mss.get("matchStatistics") or {}
        has_stats = isinstance(ms, dict) and "firstServeRateIn" in ms
        sets = {k: mss[f"setStatistics{k}"] for k in range(1, 6)
                if isinstance(mss.get(f"setStatistics{k}"), dict) and "firstServeRateIn" in mss[f"setStatistics{k}"]}
        for t, mine, theirs in (("A", "teamAValue", "teamBValue"), ("B", "teamBValue", "teamAValue")):
            team = m.get(f"team{t}") or {}
            pl = (team.get("players") or [{}])[0]
            st = team.get("sets") or []
            r = {"year": year, "code": code, "family": code[:2], "round": code_round(code),
                 "round_api": md.get("round"), "round_label": md.get("roundLabel"), "status": md.get("status"),
                 "status_label": md.get("statusLabel"), "minutes": md.get("durationInMinutes"),
                 "date": md.get("dateSchedule"), "team": t, "player_id": str(pl.get("id")),
                 "first_name": pl.get("firstName"), "last_name": pl.get("lastName"), "country": pl.get("country"),
                 "winner": bool(team.get("winner")), "end_cause": team.get("endCause") or "",
                 "entry": team.get("entryStatus") or "", "seed": team.get("seed"),
                 "games": ",".join("" if s.get("score") is None else str(s.get("score")) for s in st),
                 "tbs": ",".join("" if s.get("tieBreak") is None else str(s.get("tieBreak")) for s in st),
                 "set_winner": ",".join("1" if s.get("winner") else "0" for s in st),
                 "n_players": len(team.get("players") or []), "has_stats": has_stats, "n_sets_stats": len(sets)}
            if has_stats:
                r.update(team_counts(ms, mine, theirs))
                tot = Counter()
                for s in sets.values():
                    c = team_counts(s, mine, theirs)
                    for k in EIGHT:
                        tot[k] += c[k]
                for k in EIGHT:
                    r[f"sets_{k}"] = tot[k] if sets else float("nan")
            rows.append(r)
    df = pd.DataFrame(rows)
    opp = df.set_index(["year", "code", "team"])[["svpt"]].rename(columns={"svpt": "opp_svpt"})
    df["opp_team"] = df["team"].map({"A": "B", "B": "A"})
    df = df.join(opp, on=["year", "code", "opp_team"])
    df["chk_w1_den"] = df["w1_den"].eq(df["first_in"])
    df["chk_w2_den"] = df["w2_den"].eq(df["svpt"] - df["first_in"])
    df["chk_ret_den"] = df["ret_den"].eq(df["opp_svpt"])
    df["chk_tpw"] = df["tpw"].eq(df["first_won"] + df["second_won"] + df["ret_won"])
    df["chk_order"] = (df["first_won"] <= df["first_in"]) & (df["first_in"] <= df["svpt"]) & \
        (df["second_won"] <= df["svpt"] - df["first_in"]) & (df["df"] <= df["svpt"] - df["first_in"]) & \
        (df["bp_saved"] >= 0) & (df["ace"] >= 0)
    df["chk_present"] = df[EIGHT].notna().all(axis=1)
    df["chk_sets"] = True
    for k in EIGHT:
        df["chk_sets"] &= df[f"sets_{k}"].eq(df[k])
    df["chk_all"] = df[["chk_w1_den", "chk_w2_den", "chk_ret_den", "chk_tpw", "chk_order", "chk_present"]].all(axis=1) \
        & df["has_stats"]
    return df


# ---------------------------------------------------------------------------------------------------------------
# Infosys MatchBeats
# ---------------------------------------------------------------------------------------------------------------
MB_SPECS = [(y, "match-beats") for y in range(2019, 2025)] + [(2025, "match-centre"), (2026, "match-beats-api")]


def recount(mb: dict, year: int, code: str) -> tuple[dict, dict, list]:
    """Per team (1/2): points served and their outcome; games served (tiebreaks apart). Returns counts, facts, games."""
    cnt = {t: Counter() for t in ("1", "2")}
    facts = Counter()
    games = []
    seen = set()
    first_server = None
    for st in mb.get("setData") or []:
        for g in st.get("gameData") or []:
            pts = g.get("pointData") or []
            servers = Counter()
            for p in pts:
                facts["points"] += 1
                pid = p.get("pointId")
                if pid in seen:
                    facts["dup_ids"] += 1
                seen.add(pid)
                srv, serve, scorer, res = str(p.get("server")), p.get("serve"), str(p.get("scorer")), p.get("result")
                if srv in cnt:
                    servers[srv] += 1
                    if first_server is None:
                        first_server = srv
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
                c["fault_spd_on_1"] += serve == 1 and (p.get("faultSrvSpd") or 0) > 0
                c["fault_spd_on_2"] += serve == 2 and (p.get("faultSrvSpd") or 0) > 0
            tb = bool(g.get("isTieBreak"))
            done = bool(g.get("isGameComplete"))
            srv_of_game = servers.most_common(1)[0][0] if servers else None
            first_pt = next((str(p.get("server")) for p in pts if str(p.get("server")) in cnt), None)
            if tb:      # a tiebreak's servers alternate; its turn in the game order is its first point's server
                srv_of_game = first_pt
            mixed = len(servers) > 1
            games.append({"year": year, "code": code, "set": st.get("set"), "game": g.get("game"), "tb": tb,
                          "complete": done, "points": len(pts), "server": srv_of_game, "mixed": mixed,
                          "first_point_server": first_pt,
                          "winner": str(g.get("gameWinner")), "tm1_set": g.get("tm1SetScore"),
                          "tm2_set": g.get("tm2SetScore")})
            if srv_of_game is None:
                facts["games_no_points"] += 1
                facts["games_no_points_tb" if tb else "games_no_points_reg"] += 1
                continue
            if tb:
                facts["tb_games"] += 1
                cnt[srv_of_game]["tb_first_served"] += 1
                continue
            if mixed:
                facts["games_mixed_server"] += 1
            c = cnt[srv_of_game]
            c["sv_gms_reg_all"] += 1
            c["sv_gms_reg_done" if done else "sv_gms_reg_open"] += 1
    facts["first_server"] = first_server or ""
    return cnt, facts, games


def parse_mb() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, games = [], []
    for year, route in MB_SPECS:
        for path in sorted(glob.glob(str(RAW / "infosys_slams" / "RG" / str(year) / route / "*.json.gz"))):
            code = Path(path).name.split(".")[0]
            base = {"year": year, "route": route, "code": code}
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
            cnt, facts, gl = recount(mb, year, code)
            games += gl
            pdx = mb.get("playerData") or {}
            for t in ("1", "2"):
                rows.append({**base, "team": t, "mb_status": "ok", "is_complete": mb.get("isMatchComplete"),
                             "match_status": mb.get("matchStatus"), "match_winner": str(mb.get("matchWinner")),
                             "sets_complete": mb.get("setsComplete"), "mb_match_id": mb.get("matchId"),
                             "player_id": str(pdx.get(f"tm{t}Ply1Id")), "mb_first": pdx.get(f"tm{t}Ply1FirstName"),
                             "mb_last": pdx.get(f"tm{t}Ply1LastName"),
                             **{f"mb_{k}": cnt[t][k] for k in ("svpt", "first_in", "first_won", "second_pts",
                                                               "second_won", "ace", "df", "sv_gms_reg_all",
                                                               "sv_gms_reg_done", "sv_gms_reg_open",
                                                               "tb_first_served", "fault_spd_on_1", "fault_spd_on_2")},
                             **{f"file_{k}": facts[k] for k in ("points", "dup_ids", "odd_points", "games_no_points",
                                                                "games_no_points_tb", "games_no_points_reg",
                                                                "games_mixed_server", "tb_games", "first_server")}})
    return pd.DataFrame(rows), pd.DataFrame(games)


# ---------------------------------------------------------------------------------------------------------------
# key statistics (2025 match-centre 'stats' block; 2026 keystats-api)
# ---------------------------------------------------------------------------------------------------------------
KS_SPECS = [(2025, "match-centre"), (2026, "keystats-api")]


def parse_ks() -> pd.DataFrame:
    rows = []
    for year, route in KS_SPECS:
        for path in sorted(glob.glob(str(RAW / "infosys_slams" / "RG" / str(year) / route / "*.json.gz"))):
            code = Path(path).name.split(".")[0]
            try:
                env = blocks_of(route, load_json_gz(path)).get("stats")
                st = decrypt(env) if isinstance(env, dict) else None
            except Exception as e:  # noqa: BLE001
                rows.append({"year": year, "code": code, "ks_status": f"decrypt_failed: {e}"})
                continue
            if not isinstance(st, dict) or not (st.get("setStats") or {}).get("set0"):
                rows.append({"year": year, "code": code, "ks_status": "empty"})
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
                rows.append({"year": year, "code": code, "ks_status": "ok", "ks_team": str(i + 1),
                             "player_id": str((players[i] if i < len(players) else {}).get("player1Id")),
                             "ks_ace": whole(g("Aces")), "ks_df": whole(g("Double Faults")), "ks_svpt": sv,
                             "ks_first_in": fi, "ks_first_won": w1, "ks_second_won": w2, "ks_w1_den": w1d,
                             "ks_w2_den": w2d, "ks_bp_faced": obo, "ks_bp_saved": obo - obw,
                             "ks_bpcg": whole(g("Break Points Converted Games")),
                             "ks_complete": st.get("matchCompleted")})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    api = parse_rg_api()
    api.to_parquet(OUT / "rg_api.parquet", index=False)
    print("rg_api teams", api.shape, api.groupby("year").size().to_dict())
    print("documents with statistics", api[api["team"].eq("A")].groupby("year")["has_stats"].sum().to_dict())
    print("team rows failing the document's checks (with statistics):",
          api[api["has_stats"] & ~api["chk_all"]].groupby("year").size().to_dict())
    print("set sums unequal to the match (with statistics):",
          api[api["has_stats"] & ~api["chk_sets"]].groupby("year").size().to_dict())
    print("end causes:", api["end_cause"].value_counts().to_dict(), "| statuses:", api["status"].value_counts().to_dict())
    mb, games = parse_mb()
    mb.to_parquet(OUT / "mb.parquet", index=False)
    games.to_parquet(OUT / "mb_games.parquet", index=False)
    print("mb", mb.shape, mb.groupby(["year", "mb_status"]).size().to_dict())
    ks = parse_ks()
    ks.to_parquet(OUT / "ks.parquet", index=False)
    print("ks", ks.shape, ks.groupby(["year", "ks_status"]).size().to_dict())


if __name__ == "__main__":
    main()
