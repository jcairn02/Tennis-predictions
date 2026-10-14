"""Are the decrypted ATP Stats Centre files (2018 to Oct 2021) what they claim to be? Checks against independent copies.

The files were decrypted offline on 8 Oct 2026 (src/ingest/point_sources/infosys_atp_decrypt.py) and staged by
src/ingest/point_sources/infosys_atp_stage.py. Every check compares them with a record they were not built from:

    A identity   ManTennisData's plain row for the same match code (its atptour.com stats link): the two players' ATP
                 codes, the winner, and each set's games from MatchBeats' games
    B box score  the key statistics' match box score against ManTennisData's (the ATP's own plain numbers), statistic by
                 statistic, oriented by ATP code
    C points     a box score counted from MatchBeats' points (service points, first serves in, first- and second-serve
                 points won, aces, double faults coded "P" or "DF") against the key statistics and ManTennisData
    D routes     MatchBeats against the rally analysis of the same match, point by point on the point id: the serve's
                 speed, the serve number, and how the point ended
    E speeds     the key statistics' "1st Serve Average Speed" against MatchBeats' mean of timed first serves in (the
                 research's ceiling rule), "Max Speed" against the fastest timed serve, and Court Vision's per-point
                 speed (a16) against MatchBeats' on the same point id
    F handoff    the Hugging Face handoff's own decrypted copy of the same ATP files (2018, 2019, 2021): the key
                 statistics of the match and the rally analysis, point by point
    G outliers   speed values outside 50-300 km/h (the decryption audit's flag), by route and field
    H stage0     Stage 0's match (the live linker's link in speeds.parquet): the winner, and the box score counted from
                 MatchBeats against Stage 0's (Sackmann's) per player
These are data checks: they read results (winners, box scores) on purpose. No feature is built here.

Writes data/studies/infosys_atp_backfill/checks.json and check_mismatches.csv (every disagreeing value, for reading).
Run: ./python.sh src/eda/infosys_atp_backfill/checks.py
"""
from __future__ import annotations

import gzip
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.point_sources import infosys_atp as A  # noqa: E402

OUT = ROOT / "data" / "studies" / "infosys_atp_backfill"
ATP = ROOT / "data" / "dump" / "points" / "infosys_atp"
MANTD = ROOT / "data" / "dump" / "matches" / "mantennisdata"
HANDOFF = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
SPEEDS = ROOT / "data" / "studies" / "serve_speed_acquisition" / "speeds.parquet"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
S0_PLAYERS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_match_players.parquet"
KEY = ["year", "event_id", "match_id"]
DOUBLE_FAULTS = ("P", "DF")
END_OF = {"A": "ACE", "P": "DOUBLE FAULT", "DF": "DOUBLE FAULT", "W": "WINNER", "FE": "FORCED ERROR",
          "UE": "UNFORCED ERROR"}
# key statistic -> ManTennisData's column stem(s): (count) or (numerator, denominator)
KS_TO_MANTD = {
    "Aces": ("aces",), "Double Faults": ("double_faults",),
    "1st Serve": ("first_serves_in", "first_serves_total"),
    "1st Serve Points Won": ("first_serve_points_won", "first_serve_points_total"),
    "2nd Serve Points Won": ("second_serve_points_won", "second_serve_points_total"),
    "Break Points Saved": ("break_points_saved", "break_points_serve_total"),
    "Service Games Played": ("service_games_played",),
    "1st Serve Return Points Won": ("first_serve_return_won", "first_serve_return_total"),
    "2nd Serve Return Points Won": ("second_serve_return_won", "second_serve_return_total"),
    "Break Points Converted": ("break_points_converted", "break_points_return_total"),
    "Return Games Played": ("return_games_played",),
    "Service Points Won": ("service_points_won", "service_points_total"),
    "Return Points Won": ("return_points_won", "return_points_total"),
    "Total Points Won": ("total_points_won", "total_points_total"),
    "Winners": ("winners",), "Unforced Errors": ("unforced_errors",),
    "Net Points Won": ("net_points_won", "net_points_total"),
}
FRACTION = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
MISMATCHES: list[dict] = []


def mismatch(check: str, key: str, what: str, ours, theirs, **extra) -> None:
    MISMATCHES.append({"check": check, "key": key, "what": what, "ours": ours, "theirs": theirs, **extra})


def ks_value(text) -> tuple[float, float] | float | None:
    """'34/57 (60%)' -> (34, 57); '5' -> 5.0; anything else (missing, empty, NaN) None."""
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return None
    t = str(text).strip()
    m = FRACTION.match(t)
    if m:
        return float(m.group(1)), float(m.group(2))
    try:
        v = float(t)
    except ValueError:
        return None
    return None if math.isnan(v) else v


def num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def code(x) -> str | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    s = str(x).strip().upper()
    return (s[3:] if len(s) > 4 and s.startswith("ATP") else s) or None


def key_of(df: pd.DataFrame) -> pd.Series:
    return df["year"].astype(str) + "_" + df["event_id"].astype(str) + "_" + df["match_id"].astype(str)


# ------------------------------------------------------------------------------------------------ inputs
def matches() -> pd.DataFrame:
    m = pd.read_parquet(ATP / "matches.parquet")
    m = m[m["purpose"].eq("plan")].copy()
    m["key"] = key_of(m)
    return m.set_index("key")


def points() -> pd.DataFrame:
    p = pd.read_parquet(ATP / "points.parquet", columns=KEY + ["set", "game", "seq", "pointId", "server", "serve",
                                                              "scorer", "result", "serveSpeed", "faultSrvSpd",
                                                              "isBrkPt"])
    p["key"] = key_of(p)
    p["spd"] = pd.to_numeric(p["serveSpeed"], errors="coerce").where(lambda s: s > 0)
    return p


def keystats_set0() -> pd.DataFrame:
    k = pd.read_parquet(ATP / "keystats.parquet", columns=KEY + ["set_key", "name", "player1", "player2"])
    k = k[k["set_key"].eq("set0")].drop_duplicates(KEY + ["name"])
    k["key"] = key_of(k)
    return k


def mantd() -> pd.DataFrame:
    parts = []
    for y in (2018, 2019, 2020, 2021):
        m = pd.read_parquet(MANTD / f"atp_matches_{y}.parquet")
        c = m["stats_url"].map(A.code_of)
        m = m[c.notna()].copy()
        c = c[c.notna()]
        m["key"] = [f"{t[0]}_{t[1]}_{t[2]}" for t in c]
        parts.append(m)
    return pd.concat(parts, ignore_index=True).drop_duplicates("key").set_index("key")


# ------------------------------------------------------------------------------------------------ point box scores
def point_box(p: pd.DataFrame) -> pd.DataFrame:
    """Per match and server (1/2): service points, first serves in, first- and second-serve points won, aces, double
    faults, break points faced and saved, counted from MatchBeats' points."""
    q = p[p["server"].isin(["1", "2"])].copy()
    won = q["scorer"].eq(q["server"])
    first = q["serve"].eq("1")
    bp = q["isBrkPt"].eq("TRUE")
    g = pd.DataFrame({"key": q["key"], "server": q["server"], "svpt": 1, "first_in": first.astype(int),
                      "first_won": (first & won).astype(int), "second_won": (~first & won).astype(int),
                      "ace": q["result"].eq("A").astype(int), "df": q["result"].isin(DOUBLE_FAULTS).astype(int),
                      "bp_faced": bp.astype(int), "bp_saved": (bp & won).astype(int)})
    return g.groupby(["key", "server"]).sum().reset_index()


def set_games(p: pd.DataFrame) -> dict:
    """{key: [(games of player 1, games of player 2) per set]} from the point order: a game's winner is the scorer of
    its last point."""
    out = {}
    q = p.sort_values(["key", "seq"], kind="mergesort")
    q = q.assign(_o=pd.to_numeric(q["set"], errors="coerce") * 10_000 + pd.to_numeric(q["game"], errors="coerce") * 10
                 , _s=pd.to_numeric(q["seq"], errors="coerce"))
    q = q.sort_values(["key", "_o", "_s"], kind="mergesort")
    last = q.groupby(["key", "set", "game"], sort=False).tail(1)
    for key, g in last.groupby("key", sort=False):
        sets = []
        for _, s in g.groupby(pd.to_numeric(g["set"], errors="coerce"), sort=True):
            sets.append((int((s["scorer"] == "1").sum()), int((s["scorer"] == "2").sum())))
        out[key] = sets
    return out


def score_sets(score: str) -> list[tuple[int, int]] | None:
    """ManTennisData's winner-first score ('64 76(5)') as (winner games, loser games) per set; None when not parsed."""
    out = []
    for tok in str(score or "").split():
        m = re.fullmatch(r"(\d)(\d)(?:\(\d+\))?", tok)
        if not m:
            return None
        out.append((int(m.group(1)), int(m.group(2))))
    return out or None


# ------------------------------------------------------------------------------------------------ checks
def check_identity(m: pd.DataFrame, md: pd.DataFrame, games: dict) -> dict:
    j = m.join(md[["winner_code", "loser_code", "match_score", "match_ret", "stadie_id"]], how="left")
    has = j["winner_code"].notna()
    res = {"plan_matches": int(len(j)), "with_a_mantennisdata_row": int(has.sum())}
    with_players = j["p1_id"].notna() & j["p2_id"].notna() & has
    same = [({code(a), code(b)} == {code(w), code(l)}) for a, b, w, l in
            zip(j.loc[with_players, "p1_id"], j.loc[with_players, "p2_id"], j.loc[with_players, "winner_code"],
                j.loc[with_players, "loser_code"])]
    res["with_both_players_named"] = int(with_players.sum())
    res["same_two_players"] = int(sum(same))
    for k, ok in zip(j.index[with_players], same):
        if not ok:
            mismatch("A", k, "players", f"{j.at[k, 'p1_id']}|{j.at[k, 'p2_id']}",
                     f"{j.at[k, 'winner_code']}|{j.at[k, 'loser_code']}")
    w = with_players & j["match_winner"].isin(["1", "2"])
    win_code = np.where(j.loc[w, "match_winner"].eq("1"), j.loc[w, "p1_id"], j.loc[w, "p2_id"])
    ok_w = [code(a) == code(b) for a, b in zip(win_code, j.loc[w, "winner_code"])]
    res["with_a_matchbeats_winner"] = int(w.sum())
    res["same_winner"] = int(sum(ok_w))
    for k, ok in zip(j.index[w], ok_w):
        if not ok:
            mismatch("A", k, "winner", str(j.at[k, "match_winner"]), str(j.at[k, "winner_code"]))
    # set scores, for matches with points (complete, not retired)
    n = same_sets = 0
    for k in j.index[w]:
        g = games.get(k)
        ref = score_sets(j.at[k, "match_score"])
        if not g or ref is None or str(j.at[k, "match_ret"] or "").strip():
            continue
        win_is_1 = j.at[k, "match_winner"] == "1"
        ours = [(a, b) if win_is_1 else (b, a) for a, b in g]
        n += 1
        if ours == ref:
            same_sets += 1
        else:
            mismatch("A", k, "set games (winner first)", str(ours), str(ref))
    res["matches_with_points_and_a_parsed_score"] = n
    res["same_set_games"] = same_sets
    return res


def oriented_mantd(j: pd.DataFrame, no: str, stem: str) -> pd.Series:
    """ManTennisData's value of a statistic for Infosys player `no`, by ATP code (winner or loser columns)."""
    pid = j[f"p{no}_id"].map(code)
    is_w = pid.eq(j["winner_code"].map(code))
    is_l = pid.eq(j["loser_code"].map(code))
    w = pd.to_numeric(j[f"win_{stem}"], errors="coerce")
    l = pd.to_numeric(j[f"los_{stem}"], errors="coerce")
    return pd.Series(np.where(is_w, w, np.where(is_l, l, np.nan)), index=j.index)


def check_box_keystats(m: pd.DataFrame, ks: pd.DataFrame, md: pd.DataFrame) -> dict:
    j = m.join(md, how="inner", rsuffix="_md")
    out = {}
    for name, stems in KS_TO_MANTD.items():
        k = ks[ks["name"].eq(name)].set_index("key")
        n = eq = 0
        for no in ("1", "2"):
            vals = k[f"player{no}"].reindex(j.index)
            ref = [oriented_mantd(j, no, s) for s in stems]
            for key, v in vals.items():
                v = ks_value(v)
                if v is None:
                    continue
                theirs = tuple(r.at[key] for r in ref)
                if any(pd.isna(t) for t in theirs):
                    continue
                ours = v if isinstance(v, tuple) else (v,)
                ours = ours[:len(theirs)]
                n += 1
                if tuple(float(x) for x in ours) == tuple(float(t) for t in theirs):
                    eq += 1
                else:
                    mismatch("B", key, f"{name} p{no}", str(ours), str(theirs))
        out[name] = {"player_values": n, "equal": eq}
    tot_n = sum(v["player_values"] for v in out.values())
    tot_eq = sum(v["equal"] for v in out.values())
    return {"by_statistic": out, "player_values": tot_n, "equal": tot_eq}


def check_points_box(m: pd.DataFrame, box: pd.DataFrame, ks: pd.DataFrame, md: pd.DataFrame) -> dict:
    b = box.set_index(["key", "server"])
    out = {}
    # against the key statistics of the same match
    pairs = {"1st Serve": ("first_in", "svpt"), "1st Serve Points Won": ("first_won", "first_in"),
             "2nd Serve Points Won": ("second_won", None), "Aces": ("ace",), "Double Faults": ("df",)}
    for name, cols in pairs.items():
        k = ks[ks["name"].eq(name)].set_index("key")
        n = eq = 0
        for no in ("1", "2"):
            for key, v in k[f"player{no}"].items():
                if (key, no) not in b.index:
                    continue
                v = ks_value(v)
                if v is None:
                    continue
                row = b.loc[(key, no)]
                if name == "2nd Serve Points Won":
                    ours = (row["second_won"], row["svpt"] - row["first_in"])
                elif len(cols) == 2:
                    ours = (row[cols[0]], row[cols[1]])
                else:
                    ours = (row[cols[0]],)
                theirs = v if isinstance(v, tuple) else (v,)
                n += 1
                if tuple(float(x) for x in ours) == tuple(float(x) for x in theirs[:len(ours)]):
                    eq += 1
                else:
                    mismatch("C", key, f"points vs keystats {name} p{no}", str(tuple(int(x) for x in ours)),
                             str(theirs))
        out[f"vs_keystats|{name}"] = {"player_values": n, "equal": eq}
    # against ManTennisData
    j = m.join(md, how="inner", rsuffix="_md")
    stems = {"svpt": "first_serves_total", "first_in": "first_serves_in", "first_won": "first_serve_points_won",
             "second_won": "second_serve_points_won", "ace": "aces", "df": "double_faults",
             "bp_faced": "break_points_serve_total", "bp_saved": "break_points_saved"}
    for col, stem in stems.items():
        n = eq = 0
        for no in ("1", "2"):
            ref = oriented_mantd(j, no, stem)
            for key in j.index:
                if (key, no) not in b.index or pd.isna(ref.at[key]):
                    continue
                n += 1
                ours = float(b.loc[(key, no), col])
                if ours == float(ref.at[key]):
                    eq += 1
                else:
                    mismatch("C", key, f"points vs ManTennisData {col} p{no}", ours, float(ref.at[key]),
                             year=key[:4])
        out[f"vs_mantennisdata|{col}"] = {"player_values": n, "equal": eq}
    by_year = {}
    for r in MISMATCHES:
        if r["check"] == "C" and str(r["what"]).startswith("points vs ManTennisData"):
            by_year[r["key"][:4]] = by_year.get(r["key"][:4], 0) + 1
    out["mantennisdata_disagreements_by_year"] = by_year
    return out


def check_routes(p: pd.DataFrame) -> dict:
    r = pd.read_parquet(ATP / "rally.parquet", columns=KEY + ["pointId", "serve", "serveSpeed", "pointEndType"])
    r["key"] = key_of(r)
    r = r.drop_duplicates(["key", "pointId"])
    q = p.drop_duplicates(["key", "pointId"])
    keys = set(q["key"]) & set(r["key"])
    q, r = q[q["key"].isin(keys)], r[r["key"].isin(keys)]
    j = q.merge(r, on=["key", "pointId"], how="outer", suffixes=("_mb", "_ra"), indicator=True)
    both = j[j["_merge"].eq("both")]
    a = pd.to_numeric(both["serveSpeed_mb"], errors="coerce").fillna(0)
    b = pd.to_numeric(both["serveSpeed_ra"], errors="coerce").fillna(0)
    end_mb = both["result"].map(END_OF)
    classified = end_mb.notna() & both["pointEndType"].notna() & both["pointEndType"].ne("")
    timed = (a > 0) & (b > 0)
    return {"matches_with_both_routes": int(len(keys)), "points_in_both": int(len(both)),
            "only_matchbeats": int(j["_merge"].eq("left_only").sum()),
            "only_rally_analysis": int(j["_merge"].eq("right_only").sum()),
            "same_speed": int((a.round(1) == b.round(1)).sum()),
            "timed_in_both": int(timed.sum()),
            "matchbeats_minus_rally_kmh_when_timed": (a[timed] - b[timed]).round(1).value_counts().sort_index()
            .to_dict(),
            "timed_in_one_only": int(((a > 0) ^ (b > 0)).sum()),
            "same_serve_number": int((both["serve_mb"].astype(str) == both["serve_ra"].astype(str)).sum()),
            "endings_classified_in_both": int(classified.sum()),
            "same_ending": int((end_mb[classified] == both.loc[classified, "pointEndType"]).sum()),
            "rally_ending_when_matchbeats_says_N": both.loc[both["result"].eq("N"), "pointEndType"].fillna("")
            .value_counts().head(8).to_dict()}


def check_speeds(p: pd.DataFrame, ks: pd.DataFrame) -> dict:
    q = p[p["server"].isin(["1", "2"])]
    first = q[q["serve"].eq("1") & q["spd"].notna()]
    mean1 = first.groupby(["key", "server"])["spd"].agg(["mean", "size"])
    mx = q.groupby(["key", "server"])["spd"].max()
    out = {}
    rows = []
    for name in ("1st Serve Average Speed", "Max Speed"):
        k = ks[ks["name"].eq(name)].set_index("key")
        for no in ("1", "2"):
            for key, v in k[f"player{no}"].items():
                v = num(v)
                if not v or (key, no) not in mean1.index:
                    continue
                rows.append({"stat": name, "key": key, "no": no, "ks": v, "mean": mean1.loc[(key, no), "mean"],
                             "n": int(mean1.loc[(key, no), "size"]), "max": mx.get((key, no))})
    d = pd.DataFrame(rows)
    s1 = d[d["stat"].eq("1st Serve Average Speed")]
    diff = s1["ks"] - s1["mean"]
    out["first_serve_average"] = {
        "player_matches": int(len(s1)), "median_ks_minus_point_mean_kmh": round(float(diff.median()), 3),
        "equal_to_ceiling_of_point_mean": int((s1["ks"] == np.ceil(s1["mean"] - 1e-9)).sum()),
        "equal_to_rounded_point_mean": int((s1["ks"] == s1["mean"].round()).sum()),
        "within_1_kmh": int((diff.abs() <= 1).sum()), "more_than_3_kmh_apart": int((diff.abs() > 3).sum()),
        "note": "positive = the key statistic is faster than the mean of timed first serves in"}
    sm = d[d["stat"].eq("Max Speed")]
    out["max_speed"] = {"player_matches": int(len(sm)), "equal_to_fastest_timed_point": int((sm["ks"] == sm["max"]).sum()),
                        "within_1_kmh": int(((sm["ks"] - sm["max"]).abs() <= 1).sum())}
    # Court Vision's per-point speed against MatchBeats on the same point id
    cv = pd.read_parquet(ATP / "court_vision.parquet", columns=KEY + ["a81", "a16"])
    cv["key"] = key_of(cv)
    cv["cv_spd"] = pd.to_numeric(cv["a16"].astype(str).str.upper().str.replace("KPH", "", regex=False).str.strip(),
                                 errors="coerce").where(lambda s: s > 0)
    j = cv.merge(p[["key", "pointId", "spd"]], left_on=["key", "a81"], right_on=["key", "pointId"], how="inner")
    t = j[j["cv_spd"].notna() & j["spd"].notna()]
    out["court_vision_vs_matchbeats"] = {
        "cv_points": int(len(cv)), "joined_on_point_id": int(len(j)), "timed_in_both": int(len(t)),
        "within_0_5_kmh": int(((t["cv_spd"] - t["spd"]).abs() <= 0.5).sum()),
        "within_1_kmh": int(((t["cv_spd"] - t["spd"]).abs() <= 1).sum()),
        "matchbeats_equals_rounded_court_vision": int((np.floor(t["cv_spd"] + 0.5) == t["spd"]).sum()),
        "median_cv_minus_matchbeats": round(float((t["cv_spd"] - t["spd"]).median()), 3) if len(t) else None,
        "timed_only_in_court_vision": int((j["cv_spd"].notna() & j["spd"].isna()).sum()),
        "timed_only_in_matchbeats": int((j["cv_spd"].isna() & j["spd"].notna()).sum())}
    # the rally analysis against Court Vision's decimals: whole km/h, cut down (floor) or rounded?
    r = pd.read_parquet(ATP / "rally.parquet", columns=KEY + ["pointId", "serveSpeed"])
    r["key"] = key_of(r)
    r["ra_spd"] = pd.to_numeric(r["serveSpeed"], errors="coerce").where(lambda s: s > 0)
    jr = cv.merge(r.drop_duplicates(["key", "pointId"]), left_on=["key", "a81"], right_on=["key", "pointId"])
    tr = jr[jr["cv_spd"].notna() & jr["ra_spd"].notna()]
    out["court_vision_vs_rally"] = {
        "timed_in_both": int(len(tr)), "rally_equals_floor_of_court_vision": int((np.floor(tr["cv_spd"]) ==
                                                                                   tr["ra_spd"]).sum()),
        "rally_equals_rounded_court_vision": int((np.floor(tr["cv_spd"] + 0.5) == tr["ra_spd"]).sum())}
    return out


def handoff_records(keys: set) -> dict:
    """The handoff's records of the given (year_tid_code) keys: {key: (keystats set0 {name: (p1, p2)}, rally points
    {pointId: (serve, speed, end)}, folder)}; the copy with the most rally points wins."""
    out = {}
    for folder in ("infosys_deep", "infosys_full"):
        for path in sorted((HANDOFF / folder).glob("*_data.jsonl*")):
            if not path.name[:4] in {k[:4] for k in keys}:
                continue
            op = gzip.open if path.suffix == ".gz" else open
            with op(path, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    k = f"{r.get('year')}_{r.get('tournament_id')}_{str(r.get('match_id')).upper()}"
                    if k not in keys:
                        continue
                    s0 = (((r.get("keystats") or {}).get("setStats") or {}).get("set0")) or []
                    stats = {e.get("name"): (str(e.get("player1")), str(e.get("player2"))) for e in s0
                             if isinstance(e, dict)}
                    pts = {}
                    for cat in ((r.get("rally_analysis") or {}).get("rallyData") or []):
                        for side in ("t1err", "t1win", "t2err", "t2win"):
                            for e in cat.get(side) or []:
                                if isinstance(e, dict) and e.get("pointId"):
                                    pts[str(e["pointId"])] = (str(e.get("serve")), num(e.get("serveSpeed")) or 0.0,
                                                              str(e.get("pointEndType")))
                    old = out.get(k)
                    if old is None or len(pts) > len(old[1]):
                        out[k] = (stats if stats or old is None else old[0], pts, folder)
                    elif stats and not old[0]:
                        out[k] = (stats, old[1], old[2])
    return out


def check_handoff(m: pd.DataFrame, ks: pd.DataFrame) -> dict:
    h = handoff_records(set(m.index))
    res = {"matches_in_both": len(h)}
    # key statistics, every statistic of the match
    n = eq = matches_eq = matches_n = 0
    for key, (stats, _, _) in h.items():
        ours = ks[ks["key"].eq(key)]
        if not stats or ours.empty:
            continue
        matches_n += 1
        all_eq = True
        for name, p1, p2 in zip(ours["name"], ours["player1"].astype(str), ours["player2"].astype(str)):
            if name not in stats:
                continue
            n += 1
            if stats[name] == (p1, p2):
                eq += 1
            else:
                all_eq = False
                mismatch("F", key, f"keystats {name}", f"{p1}|{p2}", "|".join(stats[name]))
        matches_eq += all_eq
    res["keystats"] = {"matches": matches_n, "matches_identical": matches_eq, "values": n, "equal": eq}
    # rally analysis, point by point
    r = pd.read_parquet(ATP / "rally.parquet", columns=KEY + ["pointId", "serve", "serveSpeed", "pointEndType"])
    r["key"] = key_of(r)
    r = r[r["key"].isin(set(h))].drop_duplicates(["key", "pointId"])
    ours = {k: {p: (s, num(v) or 0.0, e) for p, s, v, e in zip(g["pointId"], g["serve"], g["serveSpeed"],
                                                                 g["pointEndType"].astype(str))}
            for k, g in r.groupby("key")}
    tot = dict(both=0, only_ours=0, only_handoff=0, same_speed=0, same_serve=0, same_end=0, matches=0,
               matches_identical=0)
    for key, (_, pts, _) in h.items():
        mine = ours.get(key, {})
        if not pts and not mine:
            continue
        tot["matches"] += 1
        common = set(mine) & set(pts)
        tot["both"] += len(common)
        tot["only_ours"] += len(set(mine) - set(pts))
        tot["only_handoff"] += len(set(pts) - set(mine))
        same = 0
        for pid in common:
            a, b = mine[pid], pts[pid]
            tot["same_serve"] += a[0] == b[0]
            tot["same_speed"] += round(a[1], 1) == round(b[1], 1)
            tot["same_end"] += a[2] == b[2]
            same += a == (b[0], b[1], b[2]) or (a[0] == b[0] and round(a[1], 1) == round(b[1], 1) and a[2] == b[2])
        tot["matches_identical"] += same == len(common) == len(mine) == len(pts)
    res["rally_points"] = tot
    res["by_event"] = pd.Series([k.rsplit("_", 1)[0] for k in h]).value_counts().to_dict()
    return res


def check_outliers() -> dict:
    p = pd.read_parquet(ATP / "points.parquet", columns=KEY + ["serveSpeed", "faultSrvSpd", "serve", "result"])
    out = {}
    for f in ("serveSpeed", "faultSrvSpd"):
        v = pd.to_numeric(p[f], errors="coerce")
        pos = v[v > 0]
        out[f"match-beats|{f}"] = {"positive": int(len(pos)), "below_50": int((pos < 50).sum()),
                                   "above_300": int((pos > 300).sum()), "below_40_or_above_270": int(((pos <= 40) |
                                                                                                       (pos > 270)).sum()),
                                   "min": float(pos.min()) if len(pos) else None,
                                   "max": float(pos.max()) if len(pos) else None}
    cv = pd.read_parquet(ATP / "court_vision.parquet", columns=["a16", "a21"])
    for f in ("a16", "a21"):
        v = pd.to_numeric(cv[f].astype(str).str.upper().str.replace("KPH", "", regex=False).str.strip(), errors="coerce")
        pos = v[v > 0]
        out[f"court-vision|{f}"] = {"positive": int(len(pos)), "below_50": int((pos < 50).sum()),
                                    "above_300": int((pos > 300).sum()), "min": float(pos.min()) if len(pos) else None,
                                    "max": float(pos.max()) if len(pos) else None}
    return out


def check_stage0(m: pd.DataFrame, box: pd.DataFrame) -> dict:
    sp = pd.read_parquet(SPEEDS, columns=["source", "source_key", "player_no", "match_id", "side"])
    sp = sp[sp["source"].eq("infosys_atp") & sp["match_id"].notna()]
    s0 = pd.read_parquet(S0, columns=["match_id", "player_a_id", "player_b_id", "a_won", "has_box"]).set_index("match_id")
    pl = pd.read_parquet(S0_PLAYERS, columns=["match_id", "player_id", "won", "ace", "df", "svpt", "first_in",
                                              "first_won", "second_won", "bp_saved", "bp_faced"])
    pl = pl.drop_duplicates(["match_id", "player_id"]).set_index(["match_id", "player_id"])
    sp = sp.join(s0, on="match_id", how="inner")
    sp["player_id"] = np.where(sp["side"].eq("A"), sp["player_a_id"], sp["player_b_id"])
    res = {"linked_player_rows": int(len(sp)), "linked_matches": int(sp["source_key"].nunique())}
    # the winner: Infosys's matchWinner against Stage 0's
    mw = m["match_winner"]
    w = sp[sp["player_no"].eq(1)].copy()
    w["mb_winner"] = w["source_key"].map(mw)
    w = w[w["mb_winner"].isin(["1", "2"])]
    p1_won = w["mb_winner"].eq("1")
    s0_p1_won = np.where(w["side"].eq("A"), w["a_won"].astype(bool), ~w["a_won"].astype(bool))
    res["winner"] = {"matches": int(len(w)), "same": int((p1_won.to_numpy() == s0_p1_won).sum())}
    for k, a, b in zip(w["source_key"], p1_won, s0_p1_won):
        if a != b:
            mismatch("H", k, "winner (player 1 won)", bool(a), bool(b))
    # the box score
    b = box.set_index(["key", "server"])
    cols = ["svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced", "bp_saved"]
    stats = {c: {"player_values": 0, "equal": 0} for c in cols}
    for r in sp.itertuples(index=False):
        bk = (r.source_key, str(r.player_no))
        if bk not in b.index or (r.match_id, r.player_id) not in pl.index:
            continue
        ref = pl.loc[(r.match_id, r.player_id)]
        for c in cols:
            v = pd.to_numeric(ref[c], errors="coerce")
            if pd.isna(v):
                continue
            stats[c]["player_values"] += 1
            if float(b.loc[bk, c]) == float(v):
                stats[c]["equal"] += 1
            else:
                mismatch("H", r.source_key, f"box {c} p{r.player_no}", float(b.loc[bk, c]), float(v),
                         year=r.source_key[:4])
    res["box_score"] = stats
    return res


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    m, p, ks, md = matches(), points(), keystats_set0(), mantd()
    box = point_box(p)
    games = set_games(p)
    checks = {"built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
              "staged": {"plan_matches": int(len(m)), "with_points": int((m["points"].astype(int) > 0).sum()),
                         "with_timed_points": int((m["points_timed"].astype(int) > 0).sum()),
                         "with_keystats": int((m["keystats_sets"].astype(int) > 0).sum()),
                         "with_keystats_speed": int(m["keystats_speed"].eq("TRUE").sum())}}
    checks["A_identity"] = check_identity(m, md, games)
    print("A", json.dumps(checks["A_identity"]), flush=True)
    checks["B_box_keystats_vs_mantennisdata"] = check_box_keystats(m, ks, md)
    print("B", checks["B_box_keystats_vs_mantennisdata"]["player_values"],
          checks["B_box_keystats_vs_mantennisdata"]["equal"], flush=True)
    checks["C_points_box"] = check_points_box(m, box, ks, md)
    print("C", json.dumps(checks["C_points_box"]), flush=True)
    checks["D_matchbeats_vs_rally"] = check_routes(p)
    print("D", json.dumps(checks["D_matchbeats_vs_rally"]), flush=True)
    checks["E_speeds"] = check_speeds(p, ks)
    print("E", json.dumps(checks["E_speeds"]), flush=True)
    checks["F_handoff_copy"] = check_handoff(m, ks)
    print("F", json.dumps(checks["F_handoff_copy"]), flush=True)
    checks["G_speed_outliers"] = check_outliers()
    print("G", json.dumps(checks["G_speed_outliers"]), flush=True)
    checks["H_stage0"] = check_stage0(m, box)
    print("H", json.dumps(checks["H_stage0"]), flush=True)
    mm = pd.DataFrame(MISMATCHES)
    checks["mismatches_by_check"] = mm["check"].value_counts().to_dict() if len(mm) else {}
    (OUT / "checks.json").write_text(json.dumps(checks, indent=1, default=str) + "\n", encoding="utf-8")
    mm.to_csv(OUT / "check_mismatches.csv", index=False)
    print(f"wrote {OUT / 'checks.json'} and {len(mm)} mismatch rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
