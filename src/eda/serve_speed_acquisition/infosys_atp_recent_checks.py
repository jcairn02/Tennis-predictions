"""Work package P9's decrypted ATP Stats Centre files of 2025-2026: are they what they claim to be?

Every check compares the staged tables (data/dump/points/infosys_atp_recent/, src/ingest/point_sources/
infosys_atp_recent_stage.py) with a record they were not built from. A-E and G are the ATP backfill study's checks
(src/eda/infosys_atp_backfill/checks.py), run on these tables; S and M are the two the plan names (P9 step 4):
    A identity   ManTennisData's row of the same match code (its atptour.com stats link): the two players' ATP codes,
                 the winner, and each set's games from MatchBeats' points
    W outcomes   the winner read from MatchBeats' games, and the file's own, against ManTennisData's (some complete
                 matches are never marked finished in their file and name no winner)
    D2 endings   MatchBeats' ending against the rally analysis's where the rally analysis classifies one
    B box score  the key statistics' match box score against ManTennisData's, statistic by statistic, oriented by the
                 key statistics' own two players
    C points     the box score counted from MatchBeats' points against the key statistics and ManTennisData
    D routes     MatchBeats against the rally analysis of the same match, point by point
    E speeds     "1st Serve Average Speed" against MatchBeats' mean of timed first serves in, "Max Speed" against the
                 fastest timed serve, Court Vision's per-point speed against MatchBeats'
    S sirgenkii  SirGenkii's own decrypted copy of the same host's files, January-April 2025 (data/dump/points/
                 sirgenkii_infotennis/): its rally analysis point by point (serve number, speed, ending) against ours
                 and against MatchBeats; its key statistics per set and player; its Court Vision strokes (coordinates)
                 and points (which a-numbered field holds each of its decoded columns)
    M mantd      ManTennisData's first- and second-serve averages and maximum speed against the key statistics, and
                 its first-serve average against MatchBeats' mean of timed first serves in
    G outliers   speeds outside 50-300 km/h
    P coverage   the plan's match codes against what is staged, by season, level and draw, with the count of MatchBeats
                 files in the older format (no point carries the newer fields the API's copy adds)
These are data checks: they read results (winners, box scores) on purpose. No feature is built here.

Writes data/studies/serve_speed_acquisition/infosys_atp_recent_checks.json and
infosys_atp_recent_check_mismatches.csv.gz (every disagreeing value, for reading).
Run: ./python.sh src/eda/serve_speed_acquisition/infosys_atp_recent_checks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.infosys_atp_backfill import checks as BC  # noqa: E402
from src.ingest.point_sources import infosys_atp as A  # noqa: E402

DUMP = ROOT / "data" / "dump" / "points" / "infosys_atp_recent"
SIRG = ROOT / "data" / "dump" / "points" / "sirgenkii_infotennis"
MANTD = ROOT / "data" / "dump" / "matches" / "mantennisdata"
OUT = ROOT / "data" / "studies" / "serve_speed_acquisition"
KEY = BC.KEY
YEARS = (2025, 2026)
# SirGenkii's key-statistic columns -> (our statistic, what to compare: "count", "fraction" (a/b to 5 decimals),
# "denominator", or "speed")
SIRG_KS = {"aces": ("Aces", "count"), "double_faults": ("Double Faults", "count"),
           "service_games_played": ("Service Games Played", "count"),
           "return_games_played": ("Return Games Played", "count"),
           "serve1": ("1st Serve", "fraction"), "serve1_pts_won": ("1st Serve Points Won", "fraction"),
           "serve2_pts_won": ("2nd Serve Points Won", "fraction"),
           "break_points_faced": ("Break Points Saved", "denominator"),
           "service_points_won": ("Service Points Won", "fraction"),
           "return_points_won": ("Return Points Won", "fraction"),
           "max_speed": ("Max Speed", "speed"), "serve1_avg_speed": ("1st Serve Average Speed", "speed"),
           "serve2_avg_speed": ("2nd Serve Average Speed", "speed")}
SHOT_COLS = [f"{c}_{p}" for p in ("hit", "peak_pre", "net", "bounce", "peak_post") for c in ("x", "y", "z")]
MTD_SPEEDS = {"1st Serve Average Speed": "average_first_serves_kmh", "2nd Serve Average Speed":
              "average_second_serve_kmh", "Max Speed": "fastest_first_serves_kmh"}


# ------------------------------------------------------------------------------------------------ inputs
def matches() -> pd.DataFrame:
    m = pd.read_parquet(DUMP / "matches.parquet")
    m["key"] = BC.key_of(m)
    return m.set_index("key")


def mantd() -> pd.DataFrame:
    parts = []
    for y in YEARS:
        m = pd.read_parquet(MANTD / f"atp_matches_{y}.parquet")
        c = m["stats_url"].map(A.code_of)
        m = m[c.notna()].copy()
        m["key"] = [f"{t[0]}_{t[1]}_{t[2]}" for t in c[c.notna()]]
        parts.append(m)
    return pd.concat(parts, ignore_index=True).drop_duplicates("key").set_index("key")


def oriented_keystats(m: pd.DataFrame) -> pd.DataFrame:
    """The matches with p1_id/p2_id taken from the key statistics' own players where it names them, so that a key
    statistic's player1 is compared with that player's ManTennisData values."""
    return m.assign(p1_id=m["keystats_p1_id"].fillna(m["p1_id"]), p2_id=m["keystats_p2_id"].fillna(m["p2_id"]))


def sirg_key(df: pd.DataFrame) -> pd.Series:
    return df["year"].astype(str) + "_" + df["tournament_id"].astype(str) + "_" + df["match_id"].astype(str).str.upper()


def sirg_num(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    return v.where(v != -999)


# ------------------------------------------------------------------------------------------------ S: SirGenkii
def check_sirgenkii(m: pd.DataFrame, p: pd.DataFrame) -> dict:
    out = {}
    # rally analysis, point by point
    sr = pd.read_parquet(SIRG / "atp_rally_analysis.parquet", columns=["year", "tournament_id", "match_id", "point_id",
                                                                       "serve", "serve_speed", "point_end_type"])
    sr["key"] = sirg_key(sr)
    sr = sr[sr["key"].isin(set(m.index))].drop_duplicates(["key", "point_id"])
    r = pd.read_parquet(DUMP / "rally.parquet", columns=KEY + ["pointId", "serve", "serveSpeed", "pointEndType"])
    r["key"] = BC.key_of(r)
    r = r[r["key"].isin(set(sr["key"]))].drop_duplicates(["key", "pointId"])
    j = r.merge(sr, left_on=["key", "pointId"], right_on=["key", "point_id"], how="outer", indicator=True,
                suffixes=("", "_s"))
    b = j[j["_merge"].eq("both")]
    a, g = pd.to_numeric(b["serveSpeed"], errors="coerce").fillna(0), sirg_num(b["serve_speed"]).fillna(0)
    out["rally_points"] = {
        "matches_in_both": int(len(set(r["key"]) & set(sr["key"]))), "sirgenkii_matches": int(sr["key"].nunique()),
        "points_in_both": int(len(b)), "only_ours": int(j["_merge"].eq("left_only").sum()),
        "only_sirgenkii": int(j["_merge"].eq("right_only").sum()),
        "same_serve_number": int((b["serve"].astype(str) == b["serve_s"].astype(str)).sum()),
        "same_speed": int((a.round(1) == g.round(1)).sum()),
        "same_ending": int((b["pointEndType"].astype(str).str.upper() == b["point_end_type"].astype(str).str.upper())
                           .sum())}
    for k, pid, x, y in zip(b["key"], b["pointId"], a, g):
        if round(x, 1) != round(y, 1):
            BC.mismatch("S", k, f"rally speed {pid}", x, y)
    # MatchBeats on the same point ids (the AO 2025 check's method)
    q = p[p["key"].isin(set(sr["key"]))].drop_duplicates(["key", "pointId"])
    jq = q.merge(sr, left_on=["key", "pointId"], right_on=["key", "point_id"], how="outer", indicator=True,
                 suffixes=("", "_s"))
    bq = jq[jq["_merge"].eq("both")]
    aq, gq = pd.to_numeric(bq["serveSpeed"], errors="coerce").fillna(0), sirg_num(bq["serve_speed"]).fillna(0)
    out["matchbeats_points"] = {
        "matches_in_both": int(bq["key"].nunique()), "points_in_both": int(len(bq)),
        "only_matchbeats": int(jq["_merge"].eq("left_only").sum()),
        "only_sirgenkii": int(jq["_merge"].eq("right_only").sum()),
        "same_serve_number": int((bq["serve"].astype(str) == bq["serve_s"].astype(str)).sum()),
        "same_speed_to_0_1": int((aq.round(1) == gq.round(1)).sum()),
        "same_speed_to_whole_kmh": int((aq.round() == gq.round()).sum()),
        "max_abs_speed_diff_kmh": float((aq - gq).abs().max()) if len(bq) else None}
    out["key_statistics"] = check_sirgenkii_keystats(m)
    out["court_vision"] = check_sirgenkii_court_vision(m)
    return out


def check_sirgenkii_keystats(m: pd.DataFrame) -> dict:
    sk = pd.read_parquet(SIRG / "atp_key_stats.parquet")
    sk["key"] = sirg_key(sk)
    sk = sk[sk["key"].isin(set(m.index))]
    ks = pd.read_parquet(DUMP / "keystats.parquet", columns=KEY + ["set_key", "name", "player1", "player2"])
    ks["key"] = BC.key_of(ks)
    ks = ks[ks["key"].isin(set(sk["key"]))].drop_duplicates(["key", "set_key", "name"])
    look = {(k, s, n): (a, b) for k, s, n, a, b in zip(ks["key"], ks["set_key"], ks["name"], ks["player1"],
                                                       ks["player2"])}
    p1 = m["keystats_p1_id"].fillna(m["p1_id"]).map(BC.code)
    p2 = m["keystats_p2_id"].fillna(m["p2_id"]).map(BC.code)
    res = {c: {"values": 0, "equal": 0} for c in SIRG_KS}
    oriented = 0
    for row in sk.itertuples(index=False):
        k, pid = row.key, BC.code(row.player_id)
        side = 0 if pid == p1.get(k) else 1 if pid == p2.get(k) else None
        if side is None:
            continue
        oriented += 1
        for col, (name, how) in SIRG_KS.items():
            theirs = sirg_num(pd.Series([getattr(row, col)])).iloc[0]
            pair = look.get((k, f"set{row.set_n}", name))
            if pd.isna(theirs) or pair is None:
                continue
            v = BC.ks_value(pair[side])
            if v is None:
                continue
            if how == "fraction":
                if not isinstance(v, tuple) or not v[1]:
                    continue
                ours = round(v[0] / v[1], 5)
                same = abs(ours - round(float(theirs), 5)) < 1e-5
            elif how == "denominator":
                if not isinstance(v, tuple):
                    continue
                ours = v[1]
                same = float(ours) == float(theirs)
            else:
                ours = v if not isinstance(v, tuple) else v[0]
                same = float(ours) == float(theirs)
            res[col]["values"] += 1
            res[col]["equal"] += bool(same)
            if not same:
                BC.mismatch("S", k, f"keystats set{row.set_n} {col} {pid}", ours, float(theirs))
    return {"player_set_rows_oriented": oriented, "player_set_rows": int(len(sk)), "by_statistic": res,
            "values": sum(v["values"] for v in res.values()), "equal": sum(v["equal"] for v in res.values())}


def check_sirgenkii_court_vision(m: pd.DataFrame) -> dict:
    sc = pd.read_parquet(SIRG / "atp_court_vision.parquet")
    sc["key"] = sirg_key(sc)
    sc = sc[sc["key"].isin(set(m.index))]
    path = DUMP / "court_vision_shots.parquet"
    if sc.empty or not path.exists():
        return {"strokes_in_sirgenkii": int(len(sc))}
    sh = pd.read_parquet(path, columns=KEY + ["point_id", "stroke_idx", "labels"] + SHOT_COLS + ["x_last", "y_last",
                                                                                                  "z_last"])
    sh["key"] = BC.key_of(sh)
    sh = sh[sh["key"].isin(set(sc["key"]))]
    j = sh.merge(sc, on=["key", "point_id", "stroke_idx"], how="outer", indicator=True, suffixes=("", "_s"))
    b = j[j["_merge"].eq("both")]
    res = {"matches_in_both": int(b["key"].nunique()), "strokes_in_both": int(len(b)),
           "only_ours": int(j["_merge"].eq("left_only").sum()), "only_sirgenkii": int(j["_merge"].eq("right_only").sum()),
           "coordinates": {}}
    for c in SHOT_COLS:
        ours = pd.to_numeric(b[c], errors="coerce").round(3)
        theirs = sirg_num(b[f"{c}_s"]).round(3)
        both = ours.notna() & theirs.notna()
        res["coordinates"][c] = {"in_both": int(both.sum()), "equal_to_3_decimals": int((ours[both] == theirs[both])
                                                                                          .sum()),
                                 "ours_missing_theirs_present": int((ours.isna() & theirs.notna()).sum()),
                                 "ours_present_theirs_missing": int((ours.notna() & theirs.isna()).sum())}
    # where we hold no peak after the bounce, is SirGenkii's our last tracked position?
    nopk = b[pd.to_numeric(b["x_peak_post"], errors="coerce").isna() & sirg_num(b["x_peak_post_s"]).notna()]
    res["their_peak_post_is_our_last"] = {
        "strokes": int(len(nopk)),
        "equal_to_3_decimals": int((pd.to_numeric(nopk["x_last"], errors="coerce").round(3)
                                    == sirg_num(nopk["x_peak_post_s"]).round(3)).sum())}
    res["point_fields"] = court_vision_field_map(sc)
    return res


def court_vision_field_map(sc: pd.DataFrame) -> dict:
    """For each of SirGenkii's decoded point columns, the a-numbered field of our Court Vision points that equals it
    most often (its first stroke's row per point), and how often."""
    path = DUMP / "court_vision.parquet"
    cv = pd.read_parquet(path)
    cv["key"] = BC.key_of(cv)
    cv = cv[cv["key"].isin(set(sc["key"]))]
    if cv.empty:
        return {}
    other = cv["other_fields"].map(lambda t: json.loads(t) if isinstance(t, str) else {})
    fields = pd.DataFrame(list(other), index=cv.index)
    for c in BC_CV_FIELDS:
        fields[c] = cv[c]
    fields["key"], fields["point_id"] = cv["key"], cv["a81"]
    first = sc.sort_values("stroke_idx").drop_duplicates(["key", "point_id"])
    j = first.merge(fields, on=["key", "point_id"], how="inner", suffixes=("_s", ""))
    out = {"points_joined": int(len(j))}
    norm = lambda s: s.astype(str).str.upper().str.replace(" KPH", "", regex=False).str.strip()  # noqa: E731
    for col in ("server_id", "scorer_id", "receiver_id", "ball_speed_kmh", "point_end_type", "serve_type", "court",
                "set_n", "game", "point", "serve", "hand", "rally_length", "stroke_type"):
        if col not in j:
            continue
        theirs = norm(j[col])
        best, best_n = None, -1
        for f in [c for c in fields.columns if c.startswith("a")]:
            if f not in j:
                continue
            n = int((norm(j[f]) == theirs).sum())
            if n > best_n:
                best, best_n = f, n
        out[col] = {"field": best, "equal": best_n, "of": int(len(j))}
    return out


BC_CV_FIELDS = ["a81", "a13", "a14", "a15", "a16", "a21", "a95", "a97", "a98", "a99", "a100", "a101", "a102"]


# ------------------------------------------------------------------------------------------------ W: outcomes
def check_outcomes(m: pd.DataFrame, md: pd.DataFrame) -> dict:
    """The winner read from MatchBeats' games (winner_from_points) and the file's own (match_winner) against
    ManTennisData's winner, by ATP code; matches the file leaves unfinished (match_winner 0) included."""
    j = m.join(md[["winner_code", "match_ret"]], how="inner")
    out = {}
    for col in ("match_winner", "winner_from_points"):
        w = j[j[col].isin(["1", "2"]) & j["p1_id"].notna() & j["p2_id"].notna()]
        code_of_winner = np.where(w[col].eq("1"), w["p1_id"], w["p2_id"])
        same = [BC.code(a) == BC.code(b) for a, b in zip(code_of_winner, w["winner_code"])]
        for k, ok in zip(w.index, same):
            if not ok:
                BC.mismatch("W", k, col, str(w.at[k, col]), str(w.at[k, "winner_code"]))
        out[col] = {"matches": int(len(w)), "same_winner": int(sum(same))}
    gap = j[~j["match_winner"].isin(["1", "2"]) & j["winner_from_points"].isin(["1", "2"])]
    out["named_only_by_the_games"] = int(len(gap))
    out["no_winner_either_way"] = {
        "matches": int((~j["match_winner"].isin(["1", "2"]) & ~j["winner_from_points"].isin(["1", "2"])
                        & j["points"].astype(int).gt(0)).sum()),
        "of_which_retirements_in_mantennisdata": int((~j["match_winner"].isin(["1", "2"])
                                                      & ~j["winner_from_points"].isin(["1", "2"])
                                                      & j["points"].astype(int).gt(0)
                                                      & j["match_ret"].fillna("").astype(str).str.strip().ne("")).sum())}
    return out


# ------------------------------------------------------------------------------------------------ D2: endings
def check_endings(p: pd.DataFrame) -> dict:
    """MatchBeats' ending against the rally analysis's where the rally analysis classifies it (D counts its
    "UNCLASSIFIED" as a classification: in these files the rally analysis names only aces and double faults)."""
    r = pd.read_parquet(DUMP / "rally.parquet", columns=KEY + ["pointId", "pointEndType"])
    r["key"] = BC.key_of(r)
    j = p[["key", "event_id", "pointId", "result"]].drop_duplicates(["key", "pointId"]).merge(
        r[["key", "pointId", "pointEndType"]].drop_duplicates(["key", "pointId"]), on=["key", "pointId"])
    end = j["pointEndType"].fillna("").astype(str).str.upper()
    cls = end.ne("") & end.ne("UNCLASSIFIED")
    mb = j["result"].map(BC.END_OF)
    return {"points_in_both": int(len(j)), "rally_classified": int(cls.sum()),
            "rally_classified_by_type": end[cls].value_counts().to_dict(),
            "matchbeats_agrees": int((mb[cls] == end[cls]).sum()),
            "matchbeats_unclassified_share_by_event": j.assign(n=j["result"].eq("N")).groupby("event_id")["n"].mean()
            .round(3).to_dict()}


# ------------------------------------------------------------------------------------------------ M: ManTennisData
def check_mantd_speeds(m: pd.DataFrame, ks: pd.DataFrame, p: pd.DataFrame, md: pd.DataFrame) -> dict:
    mk = oriented_keystats(m)
    j = mk.join(md, how="inner", rsuffix="_md")
    out = {}
    for name, stem in MTD_SPEEDS.items():
        k = ks[ks["name"].eq(name)].set_index("key")
        n = eq = within1 = 0
        for no in ("1", "2"):
            ref = BC.oriented_mantd(j, no, stem)
            vals = k[f"player{no}"].reindex(j.index)
            for key, v in vals.items():
                v, t = BC.num(v), ref.at[key]
                if not v or pd.isna(t) or not t:
                    continue
                n += 1
                eq += v == float(t)
                within1 += abs(v - float(t)) <= 1
                if v != float(t):
                    BC.mismatch("M", key, f"{name} p{no}", v, float(t))
        out[name] = {"player_values": n, "equal": eq, "within_1_kmh": within1}
    # MatchBeats' mean of timed first serves in, against ManTennisData's first-serve average
    q = p[p["server"].isin(["1", "2"]) & p["serve"].eq("1") & p["spd"].notna()]
    mean1 = q.groupby(["key", "server"])["spd"].agg(["mean", "size"])
    jm = m.join(md, how="inner", rsuffix="_md")
    rows = []
    for no in ("1", "2"):
        ref = BC.oriented_mantd(jm, no, "average_first_serves_kmh")
        for key in jm.index:
            if (key, no) in mean1.index and pd.notna(ref.at[key]) and ref.at[key]:
                rows.append((float(ref.at[key]) - mean1.loc[(key, no), "mean"], int(mean1.loc[(key, no), "size"])))
    d = pd.DataFrame(rows, columns=["diff", "n"])
    out["matchbeats_first_serve_mean"] = {
        "player_matches": int(len(d)),
        "median_mantd_minus_point_mean_kmh": round(float(d["diff"].median()), 3) if len(d) else None,
        "within_1_kmh": int((d["diff"].abs() <= 1).sum()), "more_than_3_kmh_apart": int((d["diff"].abs() > 3).sum()),
        "note": "positive = ManTennisData's average (the key statistic) is faster than the mean of timed first "
                "serves in"}
    return out


# ------------------------------------------------------------------------------------------------ P: the plan's coverage
NEW_FORMAT_FIELDS = ("pointDuration", "serveClassId", "firstServer")


def plan_coverage(m: pd.DataFrame) -> dict:
    """Planned match codes (the collector's plan on today's ManTennisData) against the staged matches, by season,
    level (tour, Challenger) and draw: with any document, every point (MatchBeats points), timed points, key
    statistics (and their speeds), rally analysis, Court Vision; how many MatchBeats files came by the API; and how
    many matches' MatchBeats are in the older format (no point carries the newer fields: the option of README 9.6)."""
    from src.ingest.point_sources import infosys_atp_recent as R
    plan = R.load_plan(A.parse_years("2025,2026"), "20250101", pd.Timestamp.now().strftime("%Y%m%d"))
    planned = pd.DataFrame([(str(e.year), str(e.event), c, R.tier(e), c[:2]) for e in plan for c in e.codes],
                           columns=["year", "event_id", "match_id", "tier", "family"])
    planned["key"] = BC.key_of(planned)
    num = lambda c: pd.to_numeric(m[c], errors="coerce").fillna(0)  # noqa: E731
    have = pd.DataFrame({"points": num("points") > 0, "timed": num("points_timed") > 0,
                         "keystats": num("keystats_sets") > 0, "ks_speed": m["keystats_speed"].eq("TRUE"),
                         "rally": num("rally_entries") > 0, "cv": num("cv_points") > 0,
                         "mb_api": m["routes"].str.contains("match-beats-api", regex=False)}, index=m.index)
    have["any"] = have[["points", "keystats", "rally", "cv"]].any(axis=1)
    pts = pd.read_parquet(DUMP / "points.parquet", columns=KEY + ["route", "other_fields"])
    pts["key"] = BC.key_of(pts)
    newer = pts["other_fields"].fillna("").str.contains("|".join(NEW_FORMAT_FIELDS))
    fmt = newer.groupby(pts["key"]).any()
    static_mb = pts[pts["route"].eq("match-beats")].groupby("key").size().index
    have["older_format"] = pd.Series(have.index.isin(static_mb), index=have.index) & ~fmt.reindex(have.index)\
        .fillna(False).astype(bool)
    j = planned.join(have, on="key").fillna(False)
    cols = ["any", "points", "timed", "keystats", "ks_speed", "rally", "cv", "mb_api", "older_format"]
    g = j.groupby(["year", "tier", "family"]).agg(planned=("key", "size"), **{c: (c, "sum") for c in cols})
    out = {"|".join(k): {c: int(v) for c, v in r.items()} for k, r in g.iterrows()}
    tot = j[cols].sum()
    out["all"] = {"planned": int(len(j)), **{c: int(tot[c]) for c in cols}}
    out["events_planned"] = len(plan)
    out["staged_outside_the_plan"] = int((~m.index.isin(set(planned["key"]))).sum())
    return out


# ------------------------------------------------------------------------------------------------ run
def coverage(m: pd.DataFrame) -> dict:
    """What the staged files hold, by year and level (tour, Challenger) and family."""
    num = lambda c: pd.to_numeric(m[c], errors="coerce").fillna(0)  # noqa: E731
    tier = np.where(m["series"].isin(["atp", "1000"]), "tour", np.where(m["series"].eq("ch"), "ch", "other"))
    d = pd.DataFrame({"year": m["year"], "tier": tier, "family": m["family"], "points": num("points") > 0,
                      "timed": num("points_timed") > 0, "keystats": num("keystats_sets") > 0,
                      "ks_speed": m["keystats_speed"].eq("TRUE"), "rally": num("rally_entries") > 0,
                      "cv": num("cv_points") > 0})
    g = d.groupby(["year", "tier", "family"]).agg(matches=("points", "size"), with_points=("points", "sum"),
                                                  with_timed_points=("timed", "sum"), with_keystats=("keystats", "sum"),
                                                  with_keystats_speed=("ks_speed", "sum"), with_rally=("rally", "sum"),
                                                  with_court_vision=("cv", "sum"))
    return {"|".join(map(str, k)): {c: int(v) for c, v in r.items()} for k, r in g.iterrows()}


def main() -> int:
    BC.ATP = DUMP                      # the backfill's checks read their tables from this folder at call time
    BC.MISMATCHES.clear()
    m, md = matches(), mantd()
    p, ks = BC.points(), BC.keystats_set0()
    box, games = BC.point_box(p), BC.set_games(p)
    checks = {"built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "tables": str(DUMP),
              "coverage": coverage(m)}
    try:
        checks["P_plan_coverage"] = plan_coverage(m)
    except (KeyError, ValueError, OSError) as err:
        checks["P_plan_coverage"] = {"not_run": f"{type(err).__name__}: {err}"}
    print("P_plan_coverage", json.dumps(checks["P_plan_coverage"].get("all", checks["P_plan_coverage"])), flush=True)
    steps = [("A_identity", lambda: BC.check_identity(m, md, games)),
             ("W_outcomes", lambda: check_outcomes(m, md)),
             ("B_box_keystats_vs_mantennisdata", lambda: BC.check_box_keystats(oriented_keystats(m), ks, md)),
             ("C_points_box", lambda: BC.check_points_box(m, box, ks, md)),
             ("D_matchbeats_vs_rally", lambda: BC.check_routes(p)),
             ("D2_endings", lambda: check_endings(p)),
             ("E_speeds", lambda: BC.check_speeds(p, ks)),
             ("S_sirgenkii", lambda: check_sirgenkii(m, p)),
             ("M_mantennisdata_speeds", lambda: check_mantd_speeds(m, BC.keystats_set0(), p, md)),
             ("G_speed_outliers", BC.check_outliers)]
    for name, fn in steps:
        try:
            checks[name] = fn()
        except (KeyError, ValueError, IndexError) as err:     # a check with nothing to compare (no timed match, say)
            checks[name] = {"not_run": f"{type(err).__name__}: {err}"}
        print(name, json.dumps(checks[name], default=str)[:600], flush=True)
    mm = pd.DataFrame(BC.MISMATCHES)
    checks["mismatches_by_check"] = mm["check"].value_counts().to_dict() if len(mm) else {}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "infosys_atp_recent_checks.json").write_text(json.dumps(checks, indent=1, default=str) + "\n",
                                                        encoding="utf-8")
    mm.to_csv(OUT / "infosys_atp_recent_check_mismatches.csv.gz", index=False, compression="gzip")
    print(f"wrote {OUT / 'infosys_atp_recent_checks.json'} and {len(mm)} mismatch rows", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
