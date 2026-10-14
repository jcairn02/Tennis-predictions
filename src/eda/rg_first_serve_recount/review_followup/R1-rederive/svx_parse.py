"""R1-rederive (group SVX): who served each game, from the Slams' own MatchBeats files, recounted myself.

Files (only the editions of this round): RG 2019-2024 (match-beats), RG 2025 (match-centre, mbData block), RG 2026
(match-beats-api), AO 2025 (match-beats). Each is opened with the adapter's blocks_of/decrypt (the site's own step);
everything after is my own code.

Per game, in the file's order: set and game numbers, tiebreak flag (isTieBreak), completion (isGameComplete), points,
the server (a service game: the server of its points, every point checked; a tiebreak: the server of its first
point), the set score after the game (tm1SetScore/tm2SetScore) and the game's winner. Per file: the players (ids,
names), the first point (its set, game, point number and the game score after it), and the order checks.

Writes work/svx_games.parquet (one row per game) and work/svx_files.parquet (one row per file).
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/svx_parse.py
"""
from __future__ import annotations

import glob
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.ingest.point_sources.infosys_slams import blocks_of, decrypt  # noqa: E402  (the site's own decryption)

RAW = ROOT / "data" / "raw" / "point_sources" / "infosys_slams"
WORK = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive" / "work"
SPECS = [("RG", y, "match-beats") for y in range(2019, 2025)] + [("RG", 2025, "match-centre"),
                                                                ("RG", 2026, "match-beats-api"),
                                                                ("AO", 2025, "match-beats")]
# the SVX addendum's editions (--addendum): AO on the static match-beats route, the API route only for codes the static
# route lacks (it holds the two finals); RG 2013-2015 on the API route. RG 2016-2018 are left out (still downloading).
ADD_SPECS = [("AO", y, "match-beats") for y in (2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026)] + \
    [("AO", y, "match-beats-api") for y in (2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026)] + \
    [("RG", y, "match-beats-api") for y in (2013, 2014, 2015)]


ADD2_SPECS = [("RG", y, "match-beats-api") for y in (2016, 2017, 2018)] + \
    [("RG", y, "match-beats") for y in (2016, 2017, 2018)]     # the static route holds only the two finals


def main() -> None:
    addendum2 = "--addendum2" in sys.argv
    addendum = "--addendum" in sys.argv and not addendum2
    games, files = [], []
    seen: set = set()
    for slam, year, route in (ADD2_SPECS if addendum2 else ADD_SPECS if addendum else SPECS):
        for path in sorted(glob.glob(str(RAW / slam / str(year) / route / "*.json.gz"))):
            code = Path(path).name.split(".")[0]
            if (slam, year, code) in seen:
                continue                 # the static route's file is kept; the API copy of the same match is not read
            seen.add((slam, year, code))
            base = {"slam": slam, "year": year, "code": code, "route": route}
            try:
                with gzip.open(path, "rb") as fh:
                    env = blocks_of(route, json.loads(fh.read())).get("mbData")
                mb = decrypt(env) if isinstance(env, dict) else None
            except Exception as e:  # noqa: BLE001  (recorded)
                files.append({**base, "status": f"decrypt_failed: {e}"})
                continue
            if not isinstance(mb, dict) or not mb.get("setData"):
                files.append({**base, "status": "empty"})
                continue
            pdx = mb.get("playerData") or {}
            first = None
            order_ok = True
            last = (0, 0)
            n = 0
            for st in mb.get("setData") or []:
                for g in st.get("gameData") or []:
                    pts = g.get("pointData") or []
                    s_no, g_no = int(st.get("set") or 0), int(g.get("game") or 0)
                    if (s_no, g_no) <= last:
                        order_ok = False
                    last = (s_no, g_no)
                    srv = Counter(str(p.get("server")) for p in pts if str(p.get("server")) in ("1", "2"))
                    tb = bool(g.get("isTieBreak"))
                    fp = next((p for p in pts if str(p.get("server")) in ("1", "2")), None)
                    if tb:
                        server = str(fp.get("server")) if fp else None
                    else:
                        server = srv.most_common(1)[0][0] if srv else None
                    if first is None and pts:
                        p0 = pts[0]
                        first = {"first_set": s_no, "first_game": g_no, "first_point": p0.get("point"),
                                 "first_point_id": p0.get("pointId"), "first_server": str(p0.get("server")),
                                 "first_gs1": str(p0.get("tm1GameScore")), "first_gs2": str(p0.get("tm2GameScore"))}
                    games.append({**base, "order": n, "set": s_no, "game": g_no, "tb": tb,
                                  "complete": bool(g.get("isGameComplete")), "points": len(pts), "server": server,
                                  "mixed": (len(srv) > 1) and not tb, "winner": str(g.get("gameWinner")),
                                  "set1": g.get("tm1SetScore"), "set2": g.get("tm2SetScore")})
                    n += 1
            files.append({**base, "status": "ok", "games": n, "order_ok": order_ok,
                          "match_complete": mb.get("isMatchComplete"), "match_status": mb.get("matchStatus"),
                          "match_winner": str(mb.get("matchWinner")), "sets_complete": mb.get("setsComplete"),
                          "id1": str(pdx.get("tm1Ply1Id")), "id2": str(pdx.get("tm2Ply1Id")),
                          "first1": pdx.get("tm1Ply1FirstName"), "last1": pdx.get("tm1Ply1LastName"),
                          "first2": pdx.get("tm2Ply1FirstName"), "last2": pdx.get("tm2Ply1LastName"),
                          **(first or {})})
    g = pd.DataFrame(games)
    f = pd.DataFrame(files)
    tag = "_add2" if addendum2 else "_add" if addendum else ""
    g.to_parquet(WORK / f"svx_games{tag}.parquet", index=False)
    f.to_parquet(WORK / f"svx_files{tag}.parquet", index=False)
    print(f.groupby(["slam", "year", "status"]).size().to_string())
    print("games:", len(g), "| files out of order:", int((f["order_ok"] == False).sum()),  # noqa: E712
          "| service games with points of both servers:", int(g["mixed"].sum()))


if __name__ == "__main__":
    main()
