"""Gap sources, lane B1: what the Kaggle marcosjn2 SofaScore point sequences add to three data-map gaps.

Input: data/raw/gap_sources/marcosjn2/{atp,wta}-matches.jsonl (fetch_marcosjn2.py; Kaggle version 2 of
29 Aug 2025), data/studies/data_map/matches.parquet (the map's per-match table) and, for the score check,
the Sackmann archive result files staged under data/dump/matches/sackmann_archive/.

What it does:
1. Flattens every record and replays its point sequence: each game must end exactly on its last point
   (4 points and a 2-point lead; tie-breaks to 7, or 10 for final-set tie-breaks), each set must end on its
   last game, and the match must end when a player has won 2 sets (3 in men's Grand Slam main draws, and
   in other best-of-five matches found by a fallback). A tie-break with exactly one extra point after its
   end, won by the tie-break's winner, is accepted: 99.5% of the dataset's tie-breaks carry that trailing
   point, which Sackmann's Slam point logs show is appended (see slam_point_check). Qualifying is read
   from the round name or the tournament name.
2. Counts records by gender, year, tier (`tournament.points`), qualifying or main draw, and month.
3. Links records to Sackmann result rows (same tour, both surnames, date -10..+21 days of the tournament
   start) and compares the replayed set scores with the official score.
4. Links records to the data map's matches the same way the map links sources (both surname keys and
   -10..+21 days of `d`, -40 for Slam qualifying; then one surname plus a loose test of the other name),
   using the map's own name functions, and reports which gap matches (best grain below point) it fills
   for wta_2018_points, atp_points_2025 and slam_points_ao_rg.

Writes:
* data/studies/gap_sources/marcosjn2_gap_links.csv: one row per gap match that a record links to.
* data/studies/gap_sources/marcosjn2_summary.json: counts, replay and score-check results, gap fills.

Run: ./python.sh src/eda/gap_sources/marcosjn2_links.py
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "gap_sources" / "marcosjn2"
OUT = ROOT / "data" / "studies" / "gap_sources"
MAP = ROOT / "data" / "studies" / "data_map" / "matches.parquet"
SACK = ROOT / "data" / "dump" / "matches" / "sackmann_archive"

_spec = importlib.util.spec_from_file_location("measure", ROOT / "src" / "eda" / "data_map" / "measure.py")
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)
surname_key, pair_key, same_player = measure.surname_key, measure.pair_key, measure.same_player

GAPS = {
    "wta_2018_points": {"tours": ["W"], "levels": ["FIN", "T1000", "T500", "T250", "TQ", "CH", "CHQ"], "years": [2018]},
    "atp_points_2025": {"tours": ["M"], "levels": ["FIN", "T1000", "T500", "T250", "TQ"], "years": [2025, 2026]},
    "slam_points_ao_rg": {"tours": ["M", "W"], "levels": ["GS"], "years": [2022, 2023, 2024, 2025, 2026]},
}
BELOW_POINT = {"result", "stats"}


# ---------------------------------------------------------------------------------------------
# Replay

def _game(seq: str, tiebreak: bool):
    """(state, winner '1'/'0' or None, home points, away points, target).

    state: ok (ends exactly on its last point); trailing (a tie-break that ends one point before its last
    point, the extra point going to the tie-break's winner: the dataset's systematic artefact, see the
    notes); short (never finished); overlong (finished earlier than that); bad (a character other than 0/1).
    Points h and a exclude a trailing extra point. Tie-breaks are tried to 7, then to 10.
    """
    targets = (7, 10) if tiebreak else (4,)
    best = None
    for target in targets:
        h = a = 0
        state, win = "short", None
        for i, c in enumerate(seq):
            if c == "1":
                h += 1
            elif c == "0":
                a += 1
            else:
                return "bad", None, h, a, target
            if max(h, a) >= target and abs(h - a) >= 2:
                win = "1" if h > a else "0"
                extra = len(seq) - 1 - i
                if extra == 0:
                    state = "ok"
                elif tiebreak and extra == 1 and seq[-1] == win:
                    state = "trailing"
                else:
                    state = "overlong"
                break
        res = (state, win, h, a, target)
        if state in ("ok", "trailing"):
            return res
        best = best or res
    return best


def replay(rec: dict, best_of: int) -> dict:
    sets = (rec.get("sequence") or {}).get("sets") or []
    issues: list[str] = []
    set_scores = []            # (home games, away games, tb home, tb away)
    sets_won = {"1": 0, "0": 0}
    match_over_at = None
    tb10 = trailing = n_tb = 0
    for si, s in enumerate(sets):
        gh = ga = 0
        tb = None
        games = s.get("games") or []
        set_over = False
        for gi, g in enumerate(games):
            if set_over:
                issues.append(f"s{si + 1}:game_after_set_end")
                break
            ps = g.get("point_sequence") or ""
            is_tb = bool(g.get("is_tiebreak"))
            state, win, h, a, target = _game(ps, is_tb)
            last_game_of_match = si == len(sets) - 1 and gi == len(games) - 1
            if state == "short" and not last_game_of_match:
                issues.append(f"s{si + 1}g{gi + 1}:short")
            elif state in ("overlong", "bad"):
                issues.append(f"s{si + 1}g{gi + 1}:{state}")
            if win is not None and str(g.get("game_winner")) != win:
                issues.append(f"s{si + 1}g{gi + 1}:winner_field")
            n_tb += is_tb
            trailing += state == "trailing"
            if is_tb and target == 10 and state in ("ok", "trailing"):
                tb10 += 1
            if win is None:
                continue
            if win == "1":
                gh += 1
            else:
                ga += 1
            if is_tb:
                tb = (h, a)
                set_over = True
            elif max(gh, ga) >= 6 and abs(gh - ga) >= 2:
                set_over = True
        set_scores.append((gh, ga) + (tb if tb else (None, None)))
        if set_over:
            w = "1" if gh > ga else "0"
            sets_won[w] += 1
            if str(s.get("set_winner")) != w:
                issues.append(f"s{si + 1}:set_winner_field")
            if sets_won[w] == (best_of + 1) // 2 and match_over_at is None:
                match_over_at = si
        elif si != len(sets) - 1:
            issues.append(f"s{si + 1}:set_unfinished")
    need = (best_of + 1) // 2
    decided = max(sets_won.values()) >= need
    if match_over_at is not None and match_over_at != len(sets) - 1:
        issues.append("sets_after_match_end")
    mw = str((rec.get("sequence") or {}).get("match_winner"))
    if decided:
        w = "1" if sets_won["1"] > sets_won["0"] else "0"
        if mw != w:
            issues.append("match_winner_field")
    if issues:
        status = "inconsistent"
    elif decided:
        status = "complete"
    else:
        status = "unfinished"          # retirement or a truncated sequence
    return {"status": status, "issues": ";".join(issues[:6]), "sets": set_scores,
            "sets_home": sets_won["1"], "sets_away": sets_won["0"], "tb10": tb10,
            "n_tb": n_tb, "tb_trailing": trailing}


def score_text(set_scores, winner_is_home: bool) -> str:
    out = []
    for gh, ga, th, ta in set_scores:
        w, l = (gh, ga) if winner_is_home else (ga, gh)
        s = f"{w}-{l}"
        if th is not None:
            s += f"({min(th, ta)})"
        out.append(s)
    return " ".join(out)


# ---------------------------------------------------------------------------------------------
# Load

def tier_of(points) -> str:
    if points is None or (isinstance(points, float) and np.isnan(points)):
        return "none"
    return str(int(points))


def load_records() -> pd.DataFrame:
    rows = []
    for fn in ("atp", "wta"):
        with (RAW / f"{fn}-matches.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                tour = "M" if r["meta"]["gender"] == "M" else "W"
                rnd = (r.get("round") or {}).get("name") or ""
                # qualifying: the round says so, or the tournament does ('Australian Open, Melbourne,
                # Australia, Qualifying' has blank or 'Round of 16' rounds on about 1,270 records)
                qual = bool(re.search(r"qualif", rnd, re.I) or re.search(r"qualif", r["tournament"].get("name") or "", re.I))
                tier = tier_of(r["tournament"].get("points"))
                best_of = 5 if tour == "M" and tier == "2000" and not qual else 3
                rp = replay(r, best_of)
                if best_of == 3 and rp["issues"] == "sets_after_match_end":
                    # best-of-five outside men's Slam main draws: Wimbledon's last qualifying round (to
                    # 2019), the Australian Open wildcard play-offs, Olympic and Davis Cup finals
                    rp5 = replay(r, 5)
                    if rp5["status"] == "complete":
                        rp, best_of = rp5, 5
                sets = r["sequence"].get("sets") or []
                npts = sum(len(g.get("point_sequence") or "") for s in sets for g in (s.get("games") or []))
                home_wins = str(r["sequence"].get("match_winner")) == "1"
                rows.append({
                    "key": r["key"], "event_id": r["meta"]["event_id"], "tour": tour,
                    "m_date": r["meta"]["date"], "tournament": r["tournament"].get("unique_name"),
                    "tournament_name": r["tournament"].get("name"), "tier": tier,
                    "ground": r["tournament"].get("ground_type"), "round": rnd,
                    "draw": "qual" if qual else "main", "home": r["players"]["home"]["name"],
                    "away": r["players"]["away"]["name"], "home_wins": home_wins,
                    "n_points": npts, "n_games": sum(len(s.get("games") or []) for s in sets),
                    "replay": rp["status"], "replay_issues": rp["issues"], "tb10": rp["tb10"],
                    "n_tiebreaks": rp["n_tb"], "tb_trailing_point": rp["tb_trailing"],
                    "m_score": score_text(rp["sets"], home_wins), "_sets": rp["sets"],
                    "_games": ([(s.get("set_number"), g.get("game_number"), bool(g.get("is_tiebreak")),
                                 g.get("point_sequence") or "") for s in sets for g in (s.get("games") or [])]
                               if tier == "2000" else None),
                })
    df = pd.DataFrame(rows)
    df["m_date"] = pd.to_datetime(df["m_date"])
    df["year"] = df["m_date"].dt.year
    df["month"] = df["m_date"].dt.month
    df["name1"], df["name2"] = df["home"], df["away"]
    return df


def slam_of(name: str) -> str | None:
    n = name.lower() if isinstance(name, str) else ""
    for code, pat in measure.SLAM_PATTERNS.items():
        if re.search(pat, n):
            return code
    return None


# ---------------------------------------------------------------------------------------------
# Linking (the data map's rules, simplified to the first two passes)

def _first_word(name) -> str:
    words = re.split(r"[^a-z]+", measure._ascii(str(name or "")).lower())
    words = [w for w in words if w]
    return words[0] if len(words) > 1 else ""


def _first_clash(a, b) -> bool:
    """True when two spellings' first words are both known and neither is a prefix of the other."""
    x, y = _first_word(a), _first_word(b)
    return bool(x and y) and not (x.startswith(y) or y.startswith(x))


def link(left: pd.DataFrame, right: pd.DataFrame, lo=-10, hi=21, gsq_lo=-40) -> pd.DataFrame:
    """For each left row (tour, m_date, name1, name2, draw, tier) the best right row (rid; tour, d, name1,
    name2, draw). Returns left index -> rid, pass, delta."""
    L = left.copy()
    L["k1"], L["k2"] = L["name1"].map(surname_key), L["name2"].map(surname_key)
    L["pair"] = pair_key(L["k1"], L["k2"])
    L["lo"] = np.where(L["tier"].eq("2000") & L["draw"].eq("qual"), gsq_lo, lo)
    L["lid"] = L.index
    R = right.copy()
    R["k1"], R["k2"] = R["name1"].map(surname_key), R["name2"].map(surname_key)
    R["pair"] = pair_key(R["k1"], R["k2"])

    def best(c: pd.DataFrame, tag: str) -> pd.DataFrame:
        if c.empty:
            return pd.DataFrame(columns=["lid", "rid", "pass", "delta"])
        c = c.copy()
        c["delta"] = (c["m_date"] - c["d"]).dt.days
        c = c[(c["delta"] >= c["lo"]) & (c["delta"] <= hi)]
        mism = c["draw"].notna() & c["draw_r"].notna() & (c["draw"] != c["draw_r"])
        c["score"] = (c["delta"] - 3).abs() + np.where(mism, 40, 0)
        if "fn_clash" in c:
            c["score"] += np.where(c["fn_clash"], 20, 0)
        c = c.sort_values(["lid", "score"]).drop_duplicates("lid")
        c["pass"] = tag
        return c[["lid", "rid", "pass", "delta"]]

    Rr = R[["rid", "tour", "pair", "d", "draw", "k1", "name1", "name2"]].rename(
        columns={"draw": "draw_r", "k1": "k1_r", "name1": "name1_r", "name2": "name2_r"})
    c1 = L[["lid", "tour", "pair", "m_date", "draw", "lo", "k1", "name1", "name2"]].dropna(subset=["pair"]).merge(
        Rr, on=["tour", "pair"])
    # tie-break between candidates with the same surname pair (the Pliskova twins, two Wangs):
    # penalise a candidate whose first names clash
    c1["fn_clash"] = [
        _first_clash(a1, b1 if k == kr else b2) or _first_clash(a2, b2 if k == kr else b1)
        for a1, a2, b1, b2, k, kr in zip(c1["name1"], c1["name2"], c1["name1_r"], c1["name2_r"], c1["k1"], c1["k1_r"])]
    f1 = best(c1, "pair")
    todo = L[~L["lid"].isin(f1["lid"])]
    keys = ["lid", "tour", "m_date", "draw", "lo"]
    left2 = pd.concat([todo[keys].assign(key=todo["k1"], other=todo["name2"]),
                       todo[keys].assign(key=todo["k2"], other=todo["name1"])])
    right2 = pd.concat([R[["rid", "tour", "d", "draw"]].assign(key=R["k1"], rother=R["name2"]),
                        R[["rid", "tour", "d", "draw"]].assign(key=R["k2"], rother=R["name1"])])
    right2 = right2.rename(columns={"draw": "draw_r"})
    c2 = left2[left2["key"] != ""].merge(right2, on=["tour", "key"])
    c2 = c2[((c2["m_date"] - c2["d"]).dt.days >= c2["lo"]) & ((c2["m_date"] - c2["d"]).dt.days <= hi)]
    if not c2.empty:
        ok = [same_player(a, b) for a, b in zip(c2["other"], c2["rother"])]
        c2 = c2[ok]
    f2 = best(c2, "one_surname")
    out = pd.concat([f1, f2]).set_index("lid")
    return out


# ---------------------------------------------------------------------------------------------
# Official scores

_SET = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")


def parse_score(score: str):
    """Sackmann score -> (list of (w, l, tb loser points or None), ended_early flag)."""
    toks = str(score or "").replace("[", "").replace("]", "").split()
    sets, early = [], False
    for t in toks:
        m = _SET.match(t)
        if m:
            sets.append((int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None))
        elif t.upper() in ("RET", "DEF", "W/O", "ABD", "UNK", "DEF.", "RET."):
            early = True
    return sets, early


def official_pool() -> pd.DataFrame:
    frames = []
    for tour, sub, pats in (("M", "atp", ["atp_matches_{y}", "atp_matches_qual_chall_{y}"]),
                            ("W", "wta", ["wta_matches_{y}", "wta_matches_qual_itf_{y}"])):
        for y in range(2018, 2027):
            for pat in pats:
                p = SACK / sub / (pat.format(y=y) + ".parquet")
                if not p.exists():
                    continue
                d = pd.read_parquet(p, columns=["tourney_name", "tourney_level", "tourney_date", "round",
                                                "winner_name", "loser_name", "score"])
                d["tour"] = tour
                d["file"] = p.stem
                frames.append(d)
    pool = pd.concat(frames, ignore_index=True)
    pool["d"] = pd.to_datetime(pool["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    pool["name1"], pool["name2"] = pool["winner_name"], pool["loser_name"]
    q = pool["round"].astype(str).str.match(r"^Q\d")
    pool["draw"] = np.where(q, "qual", "main")
    pool["rid"] = np.arange(len(pool))
    return pool


def compare(rec: pd.Series, off: pd.Series) -> str:
    """exact | games_only | winner_differs | sets_differ | official_unparsed."""
    osets, early = parse_score(off["score"])
    if not osets:
        return "official_unparsed"
    # which side of the record is the official winner?
    kw = surname_key(off["winner_name"])
    home_is_w = surname_key(rec["home"]) == kw or (surname_key(rec["away"]) != kw and same_player(rec["home"], off["winner_name"]))
    if rec["replay"] == "complete" and home_is_w != rec["home_wins"] and not early:
        return "winner_differs"
    mine = []
    for gh, ga, th, ta in rec["_sets"]:
        w, l = (gh, ga) if home_is_w else (ga, gh)
        mine.append((w, l, min(th, ta) if th is not None else None))
    if [(a, b) for a, b, _ in mine] != [(a, b) for a, b, _ in osets]:
        return "sets_differ"
    if [c for _, _, c in mine] != [c for _, _, c in osets]:
        return "games_only"
    return "exact"


# ---------------------------------------------------------------------------------------------
# Point order against an independent point log: Sackmann's Grand Slam point-by-point (IBM/Slam feeds)

SLAM_PBP = ROOT / "data" / "raw" / "public_dump" / "sackmann_archive" / "slam_pointbypoint"
SLAM_FILES = {"AO": "ausopen", "RG": "frenchopen", "W": "wimbledon", "USO": "usopen"}


def slam_point_check(df: pd.DataFrame) -> dict:
    """Compare every game's point order with Sackmann's Slam point logs, for editions both hold."""
    res = {"editions": [], "matches_compared": 0, "no_pair_in_sackmann": 0, "games_equal": 0,
           "games_differ": 0, "matches_with_a_differing_game": 0, "games_missing_in_sackmann": 0,
           "tiebreaks": {"equal": 0, "equal_plus_one_trailing_point": 0, "other": 0}, "examples": []}
    for (y, code), grp in df[df["slam"].notna()].groupby(["year", "slam"]):
        fp, fm = SLAM_PBP / f"{y}-{SLAM_FILES[code]}-points.csv", SLAM_PBP / f"{y}-{SLAM_FILES[code]}-matches.csv"
        if not (fp.exists() and fm.exists()):
            continue
        pts = pd.read_csv(fp, usecols=["match_id", "SetNo", "GameNo", "PointNumber", "PointWinner"], low_memory=False)
        pts = pts[pts["PointWinner"].isin([1, 2])].copy()
        pts["_pn"] = pd.to_numeric(pts["PointNumber"], errors="coerce")
        pts = pts.sort_values(["match_id", "_pn"], kind="stable")
        mt = pd.read_csv(fm, usecols=["match_id", "player1", "player2"], low_memory=False)
        pairs = {}
        for mid, p1, p2 in zip(mt["match_id"], mt["player1"], mt["player2"]):
            pairs.setdefault(frozenset((surname_key(p1), surname_key(p2))), []).append((mid, p1))
        by_mid = {mid: g for mid, g in pts.groupby("match_id")}
        res["editions"].append(f"{y}-{SLAM_FILES[code]}")
        for _, r in grp.iterrows():
            hit = pairs.get(frozenset((surname_key(r["home"]), surname_key(r["away"]))))
            if not hit or len(hit) != 1 or hit[0][0] not in by_mid:
                res["no_pair_in_sackmann"] += 1
                continue
            mid, p1 = hit[0]
            home_is_p1 = surname_key(r["home"]) == surname_key(p1)
            off = {}
            for setno, sg in by_mid[mid].groupby("SetNo", sort=True):
                for gi, gno in enumerate(dict.fromkeys(sg["GameNo"]), start=1):
                    w = sg.loc[sg["GameNo"] == gno, "PointWinner"]
                    off[(int(setno), gi)] = "".join("1" if ((x == 1) == home_is_p1) else "0" for x in w)
            res["matches_compared"] += 1
            differ = False
            for setno, gno, is_tb, seq in r["_games"]:
                o = off.get((int(setno), int(gno)))
                if o is None:
                    res["games_missing_in_sackmann"] += 1
                elif is_tb:
                    key = "equal" if seq == o else ("equal_plus_one_trailing_point" if seq[:-1] == o else "other")
                    res["tiebreaks"][key] += 1
                elif seq == o:
                    res["games_equal"] += 1
                else:
                    res["games_differ"] += 1
                    differ = True
                    if len(res["examples"]) < 6:
                        res["examples"].append({"key": r["key"], "set": setno, "game": gno, "marcosjn2": seq, "sackmann": o})
            res["matches_with_a_differing_game"] += differ
    return res


# ---------------------------------------------------------------------------------------------

def gap_rows(m: pd.DataFrame, sel: dict) -> pd.DataFrame:
    return m[m["tour"].isin(sel["tours"]) & m["level"].isin(sel["levels"]) & m["year"].isin(sel["years"])
             & m["best"].isin(BELOW_POINT)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_records()
    summary: dict = {"source": {
        "dataset": "https://www.kaggle.com/datasets/marcosjn2/tennis-point-by-point-match-dataset-20152025",
        "version": 2, "files": json.loads((RAW / "_files.json").read_text(encoding="utf-8"))["datasetFiles"],
        "receipts": [json.loads(x) for x in (RAW / "_receipts.jsonl").read_text(encoding="utf-8").splitlines() if x]}}
    summary["source"]["files"] = [{"name": f["name"], "bytes": f["totalBytes"], "created": f["creationDate"]}
                                  for f in summary["source"]["files"]]
    summary["records"] = {"total": int(len(df)), "by_tour": df.groupby("tour").size().to_dict(),
                          "date_min": str(df["m_date"].min().date()), "date_max": str(df["m_date"].max().date()),
                          "distinct_event_ids": int(df["event_id"].nunique())}

    # 2. counts
    ct = df.groupby(["tour", "year", "tier", "draw"]).size().rename("n").reset_index()
    summary["counts_tour_year_tier_draw"] = ct.to_dict(orient="records")
    w18 = df[(df.tour == "W") & (df.year == 2018)]
    summary["wta_2018_by_tier_draw"] = {f"{t}|{d}": int(n) for (t, d), n in w18.groupby(["tier", "draw"]).size().items()}
    summary["wta_2018_tier_none_tournaments"] = w18[w18.tier == "none"].groupby("tournament").size().sort_values(ascending=False).to_dict()
    summary["wta_125_records"] = df[(df.tour == "W") & (df.tier == "125")].groupby(["year", "tournament"]).size().rename("n").reset_index().to_dict(orient="records")
    a25 = df[(df.tour == "M") & (df.year == 2025)]
    summary["atp_2025_by_month_tier_draw"] = [{"month": int(mo), "tier": t, "draw": d, "n": int(n)} for (mo, t, d), n in
                                              a25.groupby(["month", "tier", "draw"]).size().items()]
    summary["atp_2026_records"] = int(((df.tour == "M") & (df.year == 2026)).sum())
    df["slam"] = np.where(df["tier"].eq("2000"), df["tournament"].map(slam_of), None)
    s = df[df["slam"].isin(["AO", "RG"]) & df["year"].between(2022, 2026)]
    summary["ao_rg_2022_2026_by_tour_year_draw"] = [{"slam": a, "tour": t, "year": int(y), "draw": d, "n": int(n)} for (a, t, y, d), n in
                                                     s.groupby(["slam", "tour", "year", "draw"]).size().items()]

    # 1. replay
    summary["replay"] = {"by_status": df["replay"].value_counts().to_dict(),
                         "by_tour_status": {f"{t}|{st}": int(n) for (t, st), n in df.groupby(["tour", "replay"]).size().items()},
                         "tiebreaks": int(df["n_tiebreaks"].sum()),
                         "tiebreaks_with_one_trailing_point": int(df["tb_trailing_point"].sum()),
                         "records_with_a_tiebreak": int(df["n_tiebreaks"].gt(0).sum()),
                         "final_set_10pt_tiebreaks": int(df["tb10"].sum()),
                         "issue_types": pd.Series([i.split(":")[-1] for x in df["replay_issues"] if x for i in x.split(";")]).value_counts().to_dict(),
                         "inconsistent_share_by_year": (df.assign(bad=df.replay.eq("inconsistent")).groupby("year")["bad"].mean().round(4).to_dict())}

    # 3. official score check (Sackmann result rows, 2018 on)
    pool = official_pool()
    recent = df[df["year"] >= 2018]
    lk = link(recent, pool)
    chk = recent.join(lk, how="inner").merge(pool[["rid", "winner_name", "loser_name", "score", "file", "tourney_name"]], on="rid")
    chk["cmp"] = [compare(r, r) for _, r in chk.iterrows()]
    summary["score_check"] = {
        "records_2018_on": int(len(recent)), "linked_to_sackmann_row": int(len(chk)),
        "result": chk["cmp"].value_counts().to_dict(),
        "result_complete_replays": chk[chk.replay == "complete"]["cmp"].value_counts().to_dict(),
        "result_by_tour": {f"{t}|{c}": int(n) for (t, c), n in chk.groupby(["tour", "cmp"]).size().items()},
        "sackmann_ended_early": int(chk["score"].astype(str).str.contains("RET|DEF|W/O|ABD", regex=True).sum()),
        "examples_sets_differ": chk[chk.cmp == "sets_differ"].head(8)[["key", "m_score", "score", "replay", "replay_issues"]].to_dict(orient="records"),
    }
    df = df.merge(chk[["key", "cmp", "score"]].rename(columns={"cmp": "score_check", "score": "official_score"}), on="key", how="left")
    summary["slam_point_order_check"] = slam_point_check(df)

    # 4. gap links
    m = pd.read_parquet(MAP)
    m = m[m["year"] >= 2018].copy()
    m["rid"] = m["uid"]
    lk2 = link(df[df["year"] >= 2018], m[["rid", "tour", "d", "name1", "name2", "draw"]])
    linked = df.join(lk2, how="inner").rename(columns={"rid": "uid"})
    # one record per universe match: keep the closest
    linked["absd"] = (linked["delta"] - 3).abs()
    dup_uids = int(linked["uid"].duplicated(keep=False).sum())
    linked = linked.sort_values(["uid", "absd"]).drop_duplicates("uid")
    summary["universe_link"] = {"records_2018_on": int((df["year"] >= 2018).sum()), "linked": int(len(lk2)),
                                "by_pass": lk2["pass"].value_counts().to_dict(),
                                "records_sharing_a_uid": dup_uids,
                                "linked_by_level": linked.merge(m[["uid", "level"]], on="uid")["level"].value_counts().to_dict()}
    out_rows = []
    gap_summary = {}
    for gid, sel in GAPS.items():
        g = gap_rows(m, sel)
        j = g.merge(linked[["uid", "key", "event_id", "m_date", "tournament", "tier", "round", "home", "away", "pass",
                            "delta", "replay", "replay_issues", "n_points", "n_tiebreaks", "tb_trailing_point", "m_score",
                            "official_score", "score_check"]],
                    on="uid", how="inner")
        j.insert(0, "gap", gid)
        res = {"gap_matches": int(len(g)), "filled": int(len(j)),
               "filled_complete_replay": int(j["replay"].eq("complete").sum()),
               "filled_complete_and_score_exact": int((j["replay"].eq("complete") & j["score_check"].eq("exact")).sum()),
               "by_level": {f"{lv}|{d}": [int(len(gg)), int(len(j[(j.level == lv) & (j.draw == d)]))]
                            for (lv, d), gg in g.groupby(["level", "draw"])},
               "by_year": {int(y): [int(len(gg)), int((j.year == y).sum())] for y, gg in g.groupby("year")}}
        if gid == "atp_points_2025":
            jm = j["d"].dt.strftime("%Y-%m")
            res["by_month_of_d"] = {ym: [int(len(gg)), int((jm == ym).sum())]
                                    for ym, gg in g.groupby(g["d"].dt.strftime("%Y-%m"))}
            res["by_month_of_d_note"] = "[gap matches, filled]; d is the tournament week start, so Dec 2024 = 2025 season openers"
        if gid == "slam_points_ao_rg":
            g = g.assign(slam=g["tname"].map(slam_of))
            j = j.assign(slam=j["tname"].map(slam_of))
            res["by_slam_year_tour"] = {f"{a}|{y}|{t}": [int(len(gg)), int(((j.slam == a) & (j.year == y) & (j.tour == t)).sum())]
                                        for (a, y, t), gg in g.groupby(["slam", "year", "tour"])}
            ao_rg = g[g.slam.isin(["AO", "RG"]) & g.year.between(2022, 2025)]
            ja = j[j.slam.isin(["AO", "RG"]) & j.year.between(2022, 2025)]
            res["ao_rg_2022_2025"] = {"gap_matches": int(len(ao_rg)), "filled": int(len(ja)),
                                      "filled_complete_replay": int(ja["replay"].eq("complete").sum())}
            j = j.drop(columns=["slam"])
        gap_summary[gid] = res
        out_rows.append(j)
    summary["gap_fills"] = gap_summary
    cols = ["gap", "uid", "tour", "level", "draw", "year", "d", "tname", "name1", "name2", "best", "sources",
            "key", "event_id", "m_date", "tournament", "tier", "round", "home", "away", "pass", "delta",
            "replay", "replay_issues", "n_points", "n_tiebreaks", "tb_trailing_point", "m_score", "official_score",
            "score_check"]
    links = pd.concat(out_rows, ignore_index=True)[cols]
    links["d"] = links["d"].dt.date
    links["m_date"] = pd.to_datetime(links["m_date"]).dt.date
    links.to_csv(OUT / "marcosjn2_gap_links.csv", index=False, encoding="utf-8")
    (OUT / "marcosjn2_summary.json").write_text(json.dumps(summary, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("records", "replay", "score_check", "slam_point_order_check", "universe_link")}, indent=1, default=str, ensure_ascii=False)[:6000])
    print(json.dumps(gap_summary, indent=1, default=str))


if __name__ == "__main__":
    main()
