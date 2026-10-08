"""Gap sources, lane A: which Slam matches the hawkilol Court Vision copy can fill, and how well.

Reads:
* data/raw/gap_sources/hawkilol/ (fetched by fetch_hawkilol.py from GitHub hawkilol/tennisSlamBallTracking at
  commit f97a9b3): the match catalogue and the 2,027 processed per-point CSVs (one row per serve, so a first-
  serve fault and the second serve are separate rows).
* data/dump/matches/sackmann_archive/{atp,wta}/*_matches_{2019..2024}.parquet (string-typed): the official
  round, winner and final score of every Slam main-draw singles match.
* data/studies/data_map/matches.parquet: the data map's per-match table (gaps slam_points_ao_rg and
  women_shots, as selected in data/data_map.yaml).

Replay: for each (set, game, point) the row with the highest serve number is the point's final row and its
point_winner_id is the point winner (fault rows are skipped this way). Points are replayed into games
(tie-break at 6-6, first to 7; final set first to 10 at 6-6 from 2022 at both Slams and at the AO from 2019;
Roland Garros final sets of 2019-2021 are advantage sets), games into sets, and the sets are compared with the
official score, tie-break points included.

pbp_status:
* complete: every point of every game is present (point numbers run 1..n, game numbers 1..n), each game ends
  exactly on its last point (the last game of a retired match may be unfinished), and every set, tie-break
  points included, equals the official score.
* tb_points_differ: as complete, but a tie-break's points differ from the Sackmann results file (two 2019
  cases checked against Sackmann's Slam point-by-point archive agree with the replay, not with the file).
* score_ok_with_gaps: every set's games equal the official score, but some points are missing or a game does
  not replay cleanly.
* partial: the sets that are present equal the official score, but games or sets at the end are missing
  (catalogue status "I" in almost every case).
* gaps_score_differs: a set differs from the official score, and every differing set holds a detected gap.
* mismatch: a set differs from the official score with no gap detected in it.

Writes:
* data/studies/gap_sources/hawkilol_matches.csv: one row per catalogue match.
* data/studies/gap_sources/hawkilol_summary.json: counts by slam, year, tour and status, and the gap fills.
Run: ./python.sh src/eda/gap_sources/hawkilol_matches.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "gap_sources" / "hawkilol"
SACK = ROOT / "data" / "dump" / "matches" / "sackmann_archive"
MAP = ROOT / "data" / "studies" / "data_map" / "matches.parquet"
OUT = ROOT / "data" / "studies" / "gap_sources"
COMMIT = "f97a9b31e64eab8485474398414dd26523871f64"

SLAM = {"australian_open": "AO", "roland_garros": "RG"}
TNAME = {"AO": "Australian Open", "RG": "Roland Garros"}
AO_ROUNDS = {1: "R128", 2: "R64", 3: "R32", 4: "R16", 5: "QF", 6: "SF", 7: "F"}
GRAIN = {"result": 0, "stats": 1, "point": 2, "shot": 3}
TRACKED = 0.9  # a match counts as tracked when at least this share of its points (final rows) has a trajectory


@lru_cache(maxsize=None)
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z]", "", s.upper())


def cat_surname(name: str) -> tuple[str, str]:
    """'R.NADAL' / 'J. Sinner' / 'C.O'CONNELL' -> ('NADAL', 'R')."""
    name = str(name).strip()
    if "." in name:
        ini, sur = name.split(".", 1)
    else:
        parts = name.split()
        ini, sur = (parts[0], " ".join(parts[1:])) if len(parts) > 1 else ("", name)
    return norm(sur), norm(ini)[:1]


# Catalogue surname -> the surname Sackmann and the data map use (name changes, shortened names).
ALIAS = {"RAMOSVINOLAS": "RAMOS", "RISKE": "RISKEAMRITRAJ", "KUZMOVA": "HRUNCAKOVA", "KOZLOVA": "BAINDL",
         "GAVRILOVA": "SAVILLE", "SANDERS": "HUNTER", "GOERGES": "GORGES"}


def name_hit(full: str, sur: str, ini: str) -> int:
    """2 = surname and initial agree, 1 = surname only, 0 = no match."""
    n = norm(full)
    if not sur or not (n.endswith(sur) or (sur in ALIAS and n.endswith(ALIAS[sur]))):
        return 0
    return 2 if ini and n.startswith(ini) else 1


def round_of(slam: str, mid: str) -> str:
    num = int(re.sub(r"\D", "", mid.split("_")[-1]))
    if slam == "AO":
        return AO_ROUNDS.get(num // 100, "?")
    for lo, rnd in [(64, "R128"), (32, "R64"), (16, "R32"), (8, "R16"), (4, "QF"), (2, "SF"), (1, "F")]:
        if num >= lo:
            return rnd
    return "?"


def parse_score(score: str) -> tuple[list[tuple[int, int, int | None]], str]:
    """'7-6(5) 3-6 6-4' -> ([(7, 6, 5), (3, 6, None), (6, 4, None)], ''); suffix RET / W/O / DEF."""
    sets, flag = [], ""
    for tok in str(score).split():
        m = re.fullmatch(r"(\d+)-(\d+)(?:\((\d+)\))?", tok)
        if m:
            sets.append((int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None))
        elif tok.upper().startswith("RET"):
            flag = "RET"
        elif tok.upper() in ("W/O", "WO"):
            flag = "W/O"
        elif tok.upper().startswith("DEF"):
            flag = "DEF"
        else:
            flag = flag or tok
    return sets, flag


def set_rules(slam: str, year: int, set_no: int, best_of: int) -> tuple[bool, int]:
    """(tie-break at 6-6?, tie-break target) for this set."""
    final = set_no == best_of
    if not final:
        return True, 7
    if year >= 2022 or slam == "AO":
        return True, 10
    return False, 0  # Roland Garros final set 2019-2021: advantage set


def replay(df: pd.DataFrame, ids: tuple[str, str], slam: str, year: int, best_of: int) -> dict:
    for c in ("set_num", "game_num", "point_num", "serve_num"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["set_num", "game_num", "point_num"]).sort_values(
        ["set_num", "game_num", "point_num", "serve_num"], kind="stable")
    keys = ["set_num", "game_num", "point_num"]
    dup_final = int(df.duplicated(keys + ["serve_num"]).sum())
    final = df.groupby(keys, sort=True).tail(1)
    a, b = ids
    foreign = int((~final["point_winner_id"].isin([a, b])).sum())
    fault_only = int(((final["serve_num"] == 1) & (final["point_end_type"] == "Faulty Serve")).sum())
    out = {"n_points": len(final), "dup_serve_rows": dup_final, "points_unknown_winner": foreign,
           "points_fault_only": fault_only, "missing_points": 0, "missing_games": 0, "bad_games": 0,
           "unfinished_last_game": False, "sets": [],
           "track_share_points": round(float((final["is_track_avail"].astype(str) == "True").mean()), 4)
           if len(final) else 0.0}
    set_nums = sorted(final["set_num"].unique())
    out["missing_sets"] = int(max(set_nums) - len(set_nums)) if set_nums else 0
    for s in set_nums:
        tb_on, target = set_rules(slam, year, int(s), best_of)
        fs = final[final["set_num"] == s]
        games = sorted(fs["game_num"].unique())
        gaps = int(max(games) - len(games))  # detected problems inside this set
        out["missing_games"] += gaps
        gaps += int((~fs["point_winner_id"].isin([a, b])).sum())
        ga = gb = 0
        tb_pts = None
        for g in games:
            fg = fs[fs["game_num"] == g]
            pnums = fg["point_num"].astype(int).tolist()
            out["missing_points"] += max(pnums) - len(pnums)
            gaps += max(pnums) - len(pnums)
            is_tb = tb_on and int(g) == 13  # game 13 of a tie-break set (numbering restarts every set)
            need = target if is_tb else 4
            pa = pb = 0
            decided_at = None
            for i, w in enumerate(fg["point_winner_id"].tolist()):
                if w == a:
                    pa += 1
                elif w == b:
                    pb += 1
                if decided_at is None and max(pa, pb) >= need and abs(pa - pb) >= 2:
                    decided_at = i
            last = len(pnums) - 1
            if decided_at is None:
                winner = fg["point_winner_id"].iloc[-1]
                is_last_game = (s == set_nums[-1]) and (g == games[-1])
                if is_last_game:
                    out["unfinished_last_game"] = True
                    winner = None
                else:
                    out["bad_games"] += 1
                    gaps += 1
            else:
                winner = a if pa > pb else b
                if decided_at != last:
                    out["bad_games"] += 1
                    gaps += 1
            if winner == a:
                ga += 1
            elif winner == b:
                gb += 1
            if is_tb:
                tb_pts = (pa, pb)
        out["sets"].append((ga, gb, tb_pts, gaps))
    return out


def compare(rsets: list, osets: list, flag: str, rp: dict) -> str:
    """pbp_status of a replay against the official sets (see the module docstring)."""
    if flag in ("RET", "DEF"):
        while osets and osets[-1][:2] == (0, 0) and len(osets) > len(rsets):
            osets = osets[:-1]  # "6-2 7-6(3) 0-0 RET": the unplayed set has no points
    if not rsets:
        return "partial"
    games_eq = [(ga, gb) == (ow, ol) for (ga, gb, _, _), (ow, ol, _) in zip(rsets, osets)]
    tb_eq = [ot is None or tb is None or min(tb) == ot for (_, _, tb, _), (_, _, ot) in zip(rsets, osets)]
    clean = (rp["missing_points"] == 0 and rp["missing_games"] == 0 and rp["missing_sets"] == 0
             and rp["bad_games"] == 0 and rp["points_unknown_winner"] == 0
             and (not rp["unfinished_last_game"] or flag in ("RET", "DEF")))
    if len(rsets) == len(osets) and all(games_eq):
        if not all(tb_eq):
            return "tb_points_differ" if clean else "score_ok_with_gaps"
        return "complete" if clean else "score_ok_with_gaps"
    if len(rsets) <= len(osets) and all(games_eq[:-1]) and all(tb_eq[:-1]) and (
            rsets[-1][0] <= osets[len(rsets) - 1][0] and rsets[-1][1] <= osets[len(rsets) - 1][1]):
        return "partial"
    differing = [r for r, eq in zip(rsets, games_eq) if not eq]
    if len(rsets) == len(osets) and differing and all(r[3] > 0 for r in differing):
        return "gaps_score_differs"
    return "mismatch"


def load_official() -> pd.DataFrame:
    frames = []
    for tour, league in (("atp", "atp"), ("wta", "wta")):
        for y in range(2019, 2025):
            d = pd.read_parquet(SACK / tour / f"{tour}_matches_{y}.parquet")
            d = d[(d["tourney_level"] == "G") & d["tourney_name"].isin(TNAME.values())].copy()
            d["league"], d["year"] = league, y
            frames.append(d)
    off = pd.concat(frames, ignore_index=True)
    off["slam"] = off["tourney_name"].map({v: k for k, v in TNAME.items()})
    return off[["league", "year", "slam", "round", "winner_name", "loser_name", "score", "best_of",
                "tourney_id", "match_num"]]


def link(cands: pd.DataFrame, n1: tuple[str, str], n2: tuple[str, str], a: str, b: str, rnd: str | None):
    """Rows of cands whose two name columns (a, b) match the two surnames, in either order."""
    hits = []
    for i, r in cands.iterrows():
        s1 = min(name_hit(r[a], *n1), name_hit(r[b], *n2))
        s2 = min(name_hit(r[a], *n2), name_hit(r[b], *n1))
        s, order = (s1, 0) if s1 >= s2 else (s2, 1)
        if s:
            hits.append((s, i, order))
    if len(hits) > 1 and rnd is not None and "round" in cands:
        same = [h for h in hits if cands.loc[h[1], "round"] == rnd]
        hits = same or hits
    if len(hits) > 1:
        best = max(h[0] for h in hits)
        hits = [h for h in hits if h[0] == best]
    if not hits and rnd is not None and "round" in cands:
        # fallback: one surname matches and the round agrees (score 0 marks it in the output)
        for i, r in cands[cands["round"] == rnd].iterrows():
            if name_hit(r[a], *n1) or name_hit(r[b], *n2):
                hits.append((0, i, 0))
            elif name_hit(r[a], *n2) or name_hit(r[b], *n1):
                hits.append((0, i, 1))
    return hits


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cat = pd.read_csv(RAW / "players_matches_catalogue" / "catalogue_all_matches_available.csv", dtype=str)
    off = load_official()
    mp = pd.read_parquet(MAP)
    mp = mp[(mp["level"] == "GS") & mp["tname"].isin(TNAME.values())].copy()
    mp["slam"] = mp["tname"].map({v: k for k, v in TNAME.items()})

    rows = []
    for _, c in cat.iterrows():
        slam, league, year = SLAM[c["tournament"]], c["league"], int(c["year"])
        mid = c["match_id"].split("_")[-1]
        folder = RAW / "pbp_data_csvs" / c["tournament"] / league
        fname = f"{league}_{c['tournament']}_{year}_{mid}_pbp.csv"
        df = pd.read_csv(folder / fname, dtype=str)
        rnd = round_of(slam, mid)
        n1, n2 = cat_surname(c["player1"]), cat_surname(c["player2"])
        ids = (c["player1_id"], c["player2_id"])
        ids_in_rows = set(df["server_id"].dropna()) | set(df["returner_id"].dropna())
        row = {
            "year": year, "slam": slam, "event": c["match_type"], "tour": "M" if league == "atp" else "W",
            "match_id": mid, "round_from_id": rnd, "player1": c["player1"], "player1_id": ids[0],
            "player2": c["player2"], "player2_id": ids[1], "status": c["match_status"],
            "sets_completed": c["num_sets_completed"], "court": c["court_name"], "n_rows": len(df),
            "ids_match_rows": ids_in_rows <= set(ids),
            "track_share": round((df["is_track_avail"].astype(str) == "True").mean(), 4) if len(df) else 0.0,
            "file": f"pbp_data_csvs/{c['tournament']}/{league}/{fname}",
        }
        # official result
        cands = off[(off["league"] == league) & (off["year"] == year) & (off["slam"] == slam)]
        hits = link(cands, n1, n2, "winner_name", "loser_name", rnd)
        best_of = 5 if league == "atp" else 3
        if len(hits) == 1:
            s, i, order = hits[0]
            o = off.loc[i]
            row.update({"official_round": o["round"], "official_winner": o["winner_name"],
                        "official_loser": o["loser_name"], "official_score": o["score"],
                        "official_link": {2: "surname+initial", 1: "surname", 0: "one surname+round"}[s]})
            win_id, lose_id = (ids[0], ids[1]) if order == 0 else (ids[1], ids[0])
            best_of = int(o["best_of"]) if str(o["best_of"]).isdigit() else best_of
        else:
            row.update({"official_round": None, "official_winner": None, "official_loser": None,
                        "official_score": None, "official_link": f"{len(hits)} candidates"})
            win_id, lose_id = ids
        # replay
        if len(df):
            rp = replay(df.copy(), (win_id, lose_id), slam, year, best_of)
        else:
            rp = {"n_points": 0, "sets": [], "missing_points": 0, "missing_games": 0, "bad_games": 0,
                  "missing_sets": 0, "unfinished_last_game": False, "points_unknown_winner": 0,
                  "points_fault_only": 0, "dup_serve_rows": 0, "track_share_points": 0.0}
        rep = " ".join(f"{ga}-{gb}" + (f"({min(tb)})" if tb and {ga, gb} == {6, 7} else "")
                       for ga, gb, tb, _ in rp["sets"])
        row.update({k: rp[k] for k in ("n_points", "track_share_points", "missing_points", "missing_games",
                                       "missing_sets", "bad_games", "unfinished_last_game",
                                       "points_unknown_winner", "points_fault_only", "dup_serve_rows")})
        row["games_replayed"] = sum(ga + gb for ga, gb, _, _ in rp["sets"])
        row["replay_score"] = rep
        # compare
        if row["official_score"] is None:
            status, row["official_flag"] = "no_official", None
        else:
            osets, flag = parse_score(row["official_score"])
            status = compare(rp["sets"], osets, flag, rp)
            row["official_flag"] = flag
            row["games_official"] = sum(w + l for w, l, _ in osets)
        row["pbp_status"] = status
        row["tracked"] = row["track_share_points"] >= TRACKED
        # data map link
        mc = mp[(mp["slam"] == slam) & (mp["year"] == year) & (mp["tour"] == row["tour"])]
        mh = link(mc, n1, n2, "name1", "name2", None)
        if len(mh) == 1:
            m = mc.loc[mh[0][1]]
            row.update({"map_uid": int(m["uid"]), "map_best": m["best"], "map_link": "one"})
        else:
            row.update({"map_uid": None, "map_best": None, "map_link": f"{len(mh)} candidates"})
        gaps = []
        if row["map_best"] is not None:
            below = GRAIN[row["map_best"]]
            if year >= 2022 and below < GRAIN["point"]:
                gaps.append("slam_points_ao_rg")
            if row["tour"] == "W" and below < GRAIN["shot"]:
                gaps.append("women_shots")
        row["gap"] = ";".join(gaps)
        # slam_points_ao_rg is filled by a complete point sequence; women_shots by a complete sequence whose
        # rows are (almost) all tracked (the per-shot trajectories themselves sit in the raw JSON).
        row["fills_slam_points"] = "slam_points_ao_rg" in gaps and status == "complete"
        row["fills_women_shots"] = "women_shots" in gaps and status == "complete" and row["tracked"]
        rows.append(row)

    t = pd.DataFrame(rows)
    order = ["year", "slam", "tour", "event", "match_id", "round_from_id", "official_round", "player1",
             "player1_id", "player2", "player2_id", "status", "sets_completed", "court", "n_rows", "n_points",
             "games_replayed", "games_official", "track_share", "track_share_points", "tracked",
             "ids_match_rows", "missing_points", "missing_games", "missing_sets", "bad_games", "unfinished_last_game", "points_unknown_winner", "points_fault_only",
             "dup_serve_rows", "replay_score", "official_score", "official_flag", "official_winner",
             "official_loser", "official_link", "pbp_status", "map_uid", "map_best", "map_link", "gap",
             "fills_slam_points", "fills_women_shots", "file"]
    t = t[order].sort_values(["year", "slam", "tour", "match_id"])
    t.to_csv(OUT / "hawkilol_matches.csv", index=False)

    # gap populations from the data map (selection as in data_map.yaml)
    full = pd.read_parquet(MAP)
    gs = full[full["level"] == "GS"]
    below_point = gs[gs["year"].between(2022, 2026) & gs["best"].isin(["result", "stats"])]
    women_gap = full[(full["tour"] == "W") & full["level"].isin(["GS", "FIN", "T1000", "T500", "T250"])
                     & full["year"].between(2018, 2026) & (full["best"] != "shot")]

    def cube(frame: pd.DataFrame, keys: list[str]) -> dict:
        return {"|".join(map(str, k if isinstance(k, tuple) else (k,))): int(v)
                for k, v in frame.groupby(keys).size().items()}

    usable = ["complete", "tb_points_differ"]
    gap_rows = []
    for (slam, year, tour), pop in below_point[below_point["tname"].isin(TNAME.values())].groupby(
            [below_point["tname"].map({v: k for k, v in TNAME.items()}), "year", "tour"]):
        h = t[(t["slam"] == slam) & (t["year"] == year) & (t["tour"] == tour)
              & t["gap"].str.contains("slam_points_ao_rg")]
        ok = h[h["pbp_status"] == "complete"]
        gap_rows.append({
            "slam": slam, "year": int(year), "tour": tour, "gap_matches": len(pop),
            "hawkilol_in_gap": len(h), "complete": len(ok), "complete_tracked": int(ok["tracked"].sum()),
            "score_ok_with_gaps": int((h["pbp_status"] == "score_ok_with_gaps").sum()),
            "partial": int((h["pbp_status"] == "partial").sum()),
            "differs": int(h["pbp_status"].isin(["gaps_score_differs", "mismatch"]).sum()),
            "gap_left_after_complete": len(pop) - len(ok),
        })
    women_rows = []
    for year in range(2018, 2027):
        wg = women_gap[(women_gap["level"] == "GS") & (women_gap["year"] == year)]
        h = t[(t["tour"] == "W") & (t["year"] == year) & t["gap"].str.contains("women_shots")]
        women_rows.append({
            "year": year, "gap_GS_all_slams": len(wg),
            "gap_GS_AO_RG": int(wg["tname"].isin(TNAME.values()).sum()),
            "hawkilol_in_gap": len(h), "tracked": int(h["tracked"].sum()),
            "tracked_and_complete": int((h["tracked"] & (h["pbp_status"] == "complete")).sum()),
        })
    not_gap = t[(t["year"] >= 2022) & ~t["gap"].str.contains("slam_points_ao_rg")]
    summary = {
        "source": {"repo": "hawkilol/tennisSlamBallTracking", "commit": COMMIT},
        "catalogue_matches": len(t),
        "by_slam_year_tour": cube(t, ["slam", "year", "tour"]),
        "catalogue_status": cube(t, ["status"]),
        "catalogue_status_vs_pbp_status": cube(t, ["status", "pbp_status"]),
        "pbp_status": cube(t, ["pbp_status"]),
        "pbp_status_by_slam_year": cube(t, ["slam", "year", "pbp_status"]),
        "tracked_threshold": TRACKED,
        "tracked": int(t["tracked"].sum()),
        "tracked_by_slam_year_tour": cube(t[t["tracked"]], ["slam", "year", "tour"]),
        "track_share_points_quartiles_by_slam_year": {
            f"{s}|{y}": [round(float(q), 3) for q in g["track_share_points"].quantile([0, .25, .5, .75, 1])]
            for (s, y), g in t.groupby(["slam", "year"])},
        "official_link": cube(t, ["official_link"]),
        "round_from_id_agrees_with_official": int((t["round_from_id"] == t["official_round"]).sum()),
        "map_link": cube(t, ["map_link"]),
        "map_best_of_hawkilol_2022_2024": cube(t[t["year"] >= 2022], ["slam", "year", "map_best"]),
        "gap_slam_points_ao_rg": {
            "population_all_slams_2022_2026": len(below_point),
            "population_by_tname_year_tour": cube(below_point.fillna({"tname": "(none)"}),
                                                  ["tname", "year", "tour"]),
            "fill_table_ao_rg": gap_rows,
            "hawkilol_2022_2024_outside_gap_(already_point_or_shot)": len(not_gap),
        },
        "gap_women_shots": {
            "population_all_levels": len(women_gap),
            "by_year": women_rows,
        },
    }
    (OUT / "hawkilol_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("catalogue_matches", "pbp_status", "tracked",
                                              "official_link", "map_link")}, indent=1))


if __name__ == "__main__":
    main()
