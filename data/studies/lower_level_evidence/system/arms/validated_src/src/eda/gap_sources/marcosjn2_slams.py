"""Gap sources, lane A: Australian Open and Roland Garros point sequences in the Kaggle marcosjn2 dataset.

Kaggle "Tennis Point-by-Point Match Dataset (2015-2026)" (marcosjn2/tennis-point-by-point-match-dataset-20152025,
version 2, updated 2025-08-29, label MIT) is a SofaScore scrape: per game, the server and a 1/0 string of point
winners (1 = home player). It has no serve number, faults, point outcome or shots.

Reads:
* data/raw/gap_sources/marcosjn2/{atp,wta}-matches.jsonl (downloaded without login from Kaggle's public
  download endpoint on 29 Sep 2026; 145,024,923 and 118,527,233 bytes).
* data/dump/matches/sackmann_archive/{atp,wta}/*_matches_{2022..2025}.parquet: official scores.
* data/studies/data_map/matches.parquet: gap slam_points_ao_rg (GS 2022-2026, best below point).
* data/studies/gap_sources/hawkilol_matches.csv (from hawkilol_matches.py): which gap matches the Court Vision
  copy already fills.

For every AO / RG main-draw singles match of 2022-2025 in the scrape: the set scores from its game winners, a
check that every game's points reach the game winner (first to 4, tie-break first to 7 or 10, by 2), the link to
the official result and to the data map, and whether the match is in the gap and not already filled.

Writes data/studies/gap_sources/marcosjn2_ao_rg_summary.json.
Run: ./python.sh src/eda/gap_sources/marcosjn2_slams.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from hawkilol_matches import TNAME, norm, parse_score

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "gap_sources" / "marcosjn2"
SACK = ROOT / "data" / "dump" / "matches" / "sackmann_archive"
MAP = ROOT / "data" / "studies" / "data_map" / "matches.parquet"
OUT = ROOT / "data" / "studies" / "gap_sources"
YEARS = range(2022, 2026)


def tokens(name: str) -> set[str]:
    return {norm(t) for t in re.split(r"[\s\-]+", str(name)) if len(norm(t)) >= 3}


def same_player(a: str, b: str) -> bool:
    """Last name token of either name appears among the other's tokens (handles order and accents)."""
    ta, tb = tokens(a), tokens(b)
    la = norm(re.split(r"\s+", str(a).strip())[-1])
    lb = norm(re.split(r"\s+", str(b).strip())[-1])
    return (la in tb) or (lb in ta)


def game_ok(seq: str, winner: str, tb_target: int | None) -> bool:
    h = a = 0
    need = tb_target or 4
    for i, ch in enumerate(seq):
        h += ch == "1"
        a += ch == "0"
        if max(h, a) >= need and abs(h - a) >= 2:
            return i == len(seq) - 1 and ("1" if h > a else "0") == winner
    return False


def parse(fn: Path, tour: str) -> list[dict]:
    rows = []
    with open(fn, encoding="utf-8") as f:
        for line in f:
            j = json.loads(line)
            t = j["tournament"]
            if t.get("unique_name") not in TNAME.values() or "Qualifying" in t.get("name", "") \
                    or t.get("points") != 2000:
                continue
            year = int(j["meta"]["date"][:4])
            if year not in YEARS:
                continue
            slam = {v: k for k, v in TNAME.items()}[t["unique_name"]]
            best_of = 5 if tour == "M" else 3
            sets, bad, tb_extra = [], 0, 0
            for s in j["sequence"]["sets"]:
                final = s["set_number"] == best_of
                gh = ga = 0
                tb_pts = None
                for g in s["games"]:
                    target = (10 if final else 7) if g["is_tiebreak"] else None
                    seq = g["point_sequence"]
                    # SofaScore tie-break strings here usually end with one extra point for the tie-break winner
                    # (735 of 761 tie-breaks of 2022-2025); drop it when that makes the tie-break exact.
                    if g["is_tiebreak"] and not game_ok(seq, g["game_winner"], target) \
                            and game_ok(seq[:-1], g["game_winner"], target):
                        seq, tb_extra = seq[:-1], tb_extra + 1
                    bad += not game_ok(seq, g["game_winner"], target)
                    gh += g["game_winner"] == "1"
                    ga += g["game_winner"] == "0"
                    if g["is_tiebreak"]:
                        tb_pts = (seq.count("1"), seq.count("0"))
                sets.append((gh, ga, tb_pts))
            rows.append({"tour": tour, "year": year, "slam": slam, "date": j["meta"]["date"],
                         "round": j["round"]["name"], "home": j["players"]["home"]["name"],
                         "away": j["players"]["away"]["name"], "winner": j["sequence"]["match_winner"],
                         "sets": sets, "bad_games": bad, "tb_extra_point": tb_extra,
                         "n_points": sum(len(g["point_sequence"]) for s in j["sequence"]["sets"]
                                         for g in s["games"])})
    return rows


def main() -> None:
    rows = parse(RAW / "atp-matches.jsonl", "M") + parse(RAW / "wta-matches.jsonl", "W")
    off = []
    for tour, t in (("atp", "M"), ("wta", "W")):
        for y in YEARS:
            d = pd.read_parquet(SACK / tour / f"{tour}_matches_{y}.parquet")
            d = d[(d["tourney_level"] == "G") & d["tourney_name"].isin(TNAME.values())].copy()
            d["tour"], d["year"] = t, y
            d["slam"] = d["tourney_name"].map({v: k for k, v in TNAME.items()})
            off.append(d)
    off = pd.concat(off, ignore_index=True)
    mp = pd.read_parquet(MAP)
    mp = mp[(mp["level"] == "GS") & mp["tname"].isin(TNAME.values()) & mp["year"].isin(YEARS)].copy()
    mp["slam"] = mp["tname"].map({v: k for k, v in TNAME.items()})
    hk = pd.read_csv(OUT / "hawkilol_matches.csv")
    hk_filled = set(hk.loc[hk["fills_slam_points"], "map_uid"].dropna().astype(int))

    out = []
    for r in rows:
        c = off[(off["tour"] == r["tour"]) & (off["year"] == r["year"]) & (off["slam"] == r["slam"])]
        hit = c[c.apply(lambda o: (same_player(o["winner_name"], r["home"]) and same_player(o["loser_name"], r["away"]))
                        or (same_player(o["winner_name"], r["away"]) and same_player(o["loser_name"], r["home"])),
                        axis=1)] if len(c) else c
        status = "no_official"
        if len(hit) == 1:
            o = hit.iloc[0]
            home_won = same_player(o["winner_name"], r["home"])
            osets, flag = parse_score(o["score"])
            if flag in ("RET", "DEF"):
                while osets and osets[-1][:2] == (0, 0) and len(osets) > len(r["sets"]):
                    osets = osets[:-1]
            rs = [((h, a, tb) if home_won else (a, h, tb[::-1] if tb else None)) for h, a, tb in r["sets"]]
            games_eq = len(rs) == len(osets) and all((w, l) == (ow, ol) for (w, l, _), (ow, ol, _) in zip(rs, osets))
            tb_eq = all(ot is None or tb is None or min(tb) == ot for (_, _, tb), (_, _, ot) in zip(rs, osets))
            if games_eq and tb_eq and r["bad_games"] == 0:
                status = "complete"
            elif games_eq:
                status = "score_ok_with_gaps"
            else:
                status = "score_differs"
        elif len(hit) > 1:
            status = "ambiguous_official"
        m = mp[(mp["tour"] == r["tour"]) & (mp["year"] == r["year"]) & (mp["slam"] == r["slam"])]
        mh = m[m.apply(lambda x: (same_player(x["name1"], r["home"]) and same_player(x["name2"], r["away"]))
                       or (same_player(x["name1"], r["away"]) and same_player(x["name2"], r["home"])), axis=1)]
        uid = int(mh.iloc[0]["uid"]) if len(mh) == 1 else None
        best = mh.iloc[0]["best"] if len(mh) == 1 else None
        out.append({**{k: r[k] for k in ("tour", "year", "slam", "date", "round", "home", "away", "n_points",
                                          "bad_games", "tb_extra_point")},
                    "status": status, "map_uid": uid, "map_best": best,
                    "in_gap": best in ("result", "stats"),
                    "gap_not_filled_by_hawkilol": best in ("result", "stats") and uid not in hk_filled})
    t = pd.DataFrame(out)

    def cube(frame: pd.DataFrame, keys: list[str]) -> dict:
        return {"|".join(map(str, k if isinstance(k, tuple) else (k,))): int(v)
                for k, v in frame.groupby(keys).size().items()}

    gap = mp[mp["best"].isin(["result", "stats"])]
    table = []
    for (slam, year, tour), g in gap.groupby(["slam", "year", "tour"]):
        x = t[(t["slam"] == slam) & (t["year"] == year) & (t["tour"] == tour)]
        xg = x[x["in_gap"]]
        table.append({
            "slam": slam, "year": int(year), "tour": tour, "gap_matches": len(g),
            "marcosjn2_main_draw": len(x), "marcosjn2_complete": int((x["status"] == "complete").sum()),
            "in_gap": len(xg), "in_gap_complete": int((xg["status"] == "complete").sum()),
            "in_gap_complete_not_filled_by_hawkilol": int(((xg["status"] == "complete")
                                                           & xg["gap_not_filled_by_hawkilol"]).sum()),
        })
    summary = {
        "source": {"kaggle": "marcosjn2/tennis-point-by-point-match-dataset-20152025", "version": 2,
                   "last_updated": "2025-08-29", "files": {"atp-matches.jsonl": 145024923,
                                                           "wta-matches.jsonl": 118527233},
                   "license_label": "MIT", "provenance_field": "sofascore"},
        "ao_rg_main_draw_2022_2025": len(t),
        "status": cube(t, ["status"]),
        "tiebreaks_with_one_extra_trailing_point": int(t["tb_extra_point"].sum()),
        "by_slam_year_tour": cube(t, ["slam", "year", "tour"]),
        "map_link": {"linked": int(t["map_uid"].notna().sum()), "unlinked": int(t["map_uid"].isna().sum())},
        "gap_table": table,
        "totals": {k: int(sum(r[k] for r in table)) for k in ("gap_matches", "marcosjn2_main_draw",
                                                               "marcosjn2_complete", "in_gap",
                                                               "in_gap_complete",
                                                               "in_gap_complete_not_filled_by_hawkilol")},
    }
    (OUT / "marcosjn2_ao_rg_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("ao_rg_main_draw_2022_2025", "status", "map_link", "totals")},
                     indent=1))
    print(pd.DataFrame(table).to_string())


if __name__ == "__main__":
    main()
