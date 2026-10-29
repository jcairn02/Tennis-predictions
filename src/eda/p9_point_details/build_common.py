"""Shared helpers of the P9 point-details builder (src/eda/p9_point_details/build_*.py).

What is here:
    * paths and the build folder (data/studies/p9_point_details/build/);
    * the reader of the ATP's MatchBeats-format point files (P9 = infosys_atp_recent, and the three other staged copies
      of the same format: infosys_atp 2018-22, infosys_challengers 2021-24, infosys_slams AO/RG 2025-26), with each
      point's rally-analysis row beside it;
    * the rally convention: every source in the shot-level study's convention (src/eda/shot_level/points.py): the serve
      is shot 1 and the shot that ended the point is counted (an ace 1, a double fault 0, a return error 2, a serve won
      without an ace 2 as the returner's forced error);
    * the bands of rally length and the match gate (a match carries rally length when at least GATE of its points other
      than aces and double faults have one);
    * Stage 0 loaders and the 52-week as-of sums on Stage 0's clock (tournament date, then round order).

Nothing here reads who won a match. Point winners inside a match are read as raw material for later matches' features.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DUMP = ROOT / "data" / "dump" / "points"
OUT = ROOT / "data" / "studies" / "p9_point_details" / "build"
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
STAGE0_PLAYERS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_match_players.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
SHOT_LEVEL = ROOT / "data" / "studies" / "shot_level"
REBUILDS = ROOT / "data" / "studies" / "data_continuity" / "rebuilds"
T0 = time.time()

# the ATP's MatchBeats-format copies: (folder, what it is)
ATP_SOURCES = {
    "p9": (DUMP / "infosys_atp_recent", "P9: the ATP Stats Centre's files of 2025-26, tour level and Challengers"),
    "infosys_atp": (DUMP / "infosys_atp", "the ATP's own files of 2018 to Oct 2021, decrypted 8 Oct 2026"),
    "infosys_challengers": (DUMP / "infosys_challengers", "the ATP's Challenger files of 2021-24 (P6)"),
    "infosys_slams": (DUMP / "infosys_slams", "the AO and RG Infosys files of 2025-26"),
}
# the shot-level study's common point tables used here (ausopen carries no rally length: aces and double faults only)
SHOT_LEVEL_SOURCES = ["infosys", "sirgenkii", "slamtracker", "slam_pbp", "slam_tracking", "mcp", "tdi"]
# which source's points a Stage 0 match takes when several hold it (P9 first, as the brief asks; then the ATP's own
# files, the Slams' official feeds, TDI's commercial capture, the volunteer charts last)
PREFERENCE = ["p9", "infosys_atp", "infosys_challengers", "infosys", "sirgenkii", "infosys_slams", "slamtracker",
              "slam_pbp", "slam_tracking", "tdi", "mcp"]
CAPPED_SOURCES = {"infosys", "sirgenkii"}       # rally lengths from Infosys's groups: 9 = "9+ odd", 10 = "10+ even"

END = {"unknown": 0, "ace": 1, "df": 2, "winner": 3, "forced": 4, "unforced": 5}
SHOT = {"Serve": 1, "Return": 2, "3rd shot": 3, "4th shot": 4, "5th shot": 5, "6th shot": 6, "7th shot": 7,
        "8th shot": 8, "9+ odd shots": 9, "10+ even shots": 10}
MAX_COUNT = 60                  # MatchBeats counts above this (up to 416,307) or below 0 are garbage
GATE = 0.9                      # a match carries rally length at this share of its non-ace, non-double-fault points
BANDS = {0: "DF", 1: "1-2", 2: "3-4", 3: "5-8", 4: "9+"}
BAND_EDGES = [(1, 2), (3, 4), (5, 8), (9, 10_000)]

MEN_TOUR_LEVELS = ["GS", "FIN", "T1000", "T500", "T250"]


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def num(s) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def atp_code(x) -> str | None:
    """An ATP player code in one spelling: upper case, without the Infosys 'ATP' prefix ('ATPD643' -> 'D643')."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip().upper()
    if len(s) > 4 and s.startswith("ATP"):
        s = s[3:]
    return s or None


def tid_prefix(tid: pd.Series) -> pd.Series:
    """Stage 0's tournament id without the date suffix it gets when an id names two events ('2026-5014-20261007' ->
    '2026-5014'); ITF ids ('2025-M-ITF-...') are returned as they are."""
    s = tid.astype(str)
    parts = s.str.split("-", n=2, expand=True)
    numeric = parts[1].fillna("").str.fullmatch(r"\d+")
    return pd.Series(np.where(numeric, parts[0] + "-" + parts[1].fillna(""), s), index=tid.index)


def band_of(rally) -> np.ndarray:
    r = np.asarray(rally)
    return np.select([r < 0, r == 0, r <= 2, r <= 4, r <= 8], [-1, 0, 1, 2, 3], 4).astype("int8")


def capped(rally) -> np.ndarray:
    """Rally length capped as Infosys's groups are: 9 or more shots -> 9 when odd, 10 when even."""
    r = np.asarray(rally).astype("int64")
    return np.where(r >= 9, np.where(r % 2 == 1, 9, 10), r)


# ------------------------------------------------------------------------------------------------
# The ATP's MatchBeats-format files

def read_atp_matches(source: str) -> pd.DataFrame:
    """One row per match of an ATP-format source: key, year, event_id, match_id, draw, rnd (the round from the match
    code; qualifying codes give none except at the Slams), the two players' ATP codes and names, level and start date
    where the source has them."""
    folder = ATP_SOURCES[source][0]
    m = pd.read_parquet(folder / "matches.parquet")
    if source == "infosys_slams":
        m = m[m["tour"].eq("M")].copy()
    if source == "infosys_atp" and "purpose" in m:
        m = m[m["purpose"].eq("plan")].copy()
    for c in ("year", "event_id", "match_id"):
        m[c] = m[c].astype(str)
    out = pd.DataFrame({
        "source": source,
        "key": source + "|" + m["year"] + "|" + m["event_id"] + "|" + m["match_id"],
        "year": m["year"], "event_id": m["event_id"], "match_id": m["match_id"],
        "tid": m["year"] + "-" + m["event_id"],
        "draw": m["draw"].astype(str).where(m["draw"].isin(["main", "qual"]),
                                            np.where(m["match_id"].str.upper().str.startswith(("Q", "MQ")), "qual",
                                                     "main")) if "draw" in m
        else np.where(m["match_id"].str.upper().str.startswith(("Q", "MQ")), "qual", "main"),
        "rnd": m["round_from_code"].where(m["round_from_code"].notna(), None),
        "c1": m["p1_id"].map(atp_code), "c2": m["p2_id"].map(atp_code),
        "n1": (m["p1_first_name"].fillna("") + " " + m["p1_last_name"].fillna("")).str.strip(),
        "n2": (m["p2_first_name"].fillna("") + " " + m["p2_last_name"].fillna("")).str.strip(),
        "n1_short": m["p1_name"], "n2_short": m["p2_name"],
        "level_src": m["level"] if "level" in m else None,
        "series": m["series"] if "series" in m else None,
        "start": pd.to_datetime(m["tournament_start"].astype(str), format="%Y%m%d", errors="coerce")
        if "tournament_start" in m else pd.NaT,
        "points_src": num(m["points"]).fillna(0).astype("int64") if "points" in m else 0,
    })
    if source == "infosys_slams":
        out["level_src"] = "GS"
    # a name missing in first/last form takes the short form ('J. DUCKWORTH')
    for i in ("1", "2"):
        blank = out[f"n{i}"].eq("")
        out.loc[blank, f"n{i}"] = out.loc[blank, f"n{i}_short"].fillna("")
    return out.reset_index(drop=True)


def read_atp_points(source: str) -> pd.DataFrame:
    """Every MatchBeats point of an ATP-format source, in match order, with the rally-analysis row of the same point
    (category, list, ending, net flags) beside it. Columns: key, set_no, game_no, point_no, server, scorer (1 = the
    file's player 1), result (A, DF, W, FE, UE, N), old (tm1Rally + tm2Rally, the shots that landed in), tracked (the
    file's rallyLengthMissing == FALSE), ra_shot / ra_team / ra_won / ra_end (the rally file's), net1 / net2 (1, 0;
    -1 where the match records no net point)."""
    folder = ATP_SOURCES[source][0]
    keycols = ["slam", "year", "match_id"] if source == "infosys_slams" else ["year", "event_id", "match_id"]
    pcols = keycols + ["set", "game", "point", "pointId", "server", "scorer", "result", "tm1Rally", "tm2Rally",
                       "rallyLengthMissing"]
    if source == "p9":
        pcols += ["tm1AtNet", "tm2AtNet"]
    p = pd.read_parquet(folder / "points.parquet", columns=pcols)
    r = pd.read_parquet(folder / "rally.parquet", columns=keycols + ["category", "list", "pointId", "pointEndType",
                                                                     "t1NetPoint", "t2NetPoint"])
    if source == "infosys_slams":
        ev = {"AO": "580", "RG": "520"}
        for t in (p, r):
            t["event_id"] = t["slam"].map(ev)
        m = pd.read_parquet(folder / "matches.parquet", columns=["slam", "year", "match_id", "tour"])
        men = set(zip(m.loc[m["tour"].eq("M"), "slam"], m.loc[m["tour"].eq("M"), "year"].astype(str),
                      m.loc[m["tour"].eq("M"), "match_id"]))
        p = p[[(a, str(b), c) in men for a, b, c in zip(p["slam"], p["year"], p["match_id"])]]
    for t in (p, r):
        for c in ("year", "event_id", "match_id"):
            t[c] = t[c].astype(str)
        t["key"] = source + "|" + t["year"] + "|" + t["event_id"] + "|" + t["match_id"]
        t["sgp"] = t["pointId"].astype(str).str.rsplit("_", n=1).str[0]
    r = r.drop_duplicates(["key", "sgp"])
    out = pd.DataFrame({
        "key": p["key"].to_numpy(), "sgp": p["sgp"].to_numpy(),
        "set_no": num(p["set"]).to_numpy(), "game_no": num(p["game"]).to_numpy(), "point_no": num(p["point"]).to_numpy(),
        "server": num(p["server"]).to_numpy(), "scorer": num(p["scorer"]).to_numpy(),
        "result": p["result"].astype(str).to_numpy(),
        "old": (num(p["tm1Rally"]) + num(p["tm2Rally"])).to_numpy(),
        "tracked": p["rallyLengthMissing"].astype(str).eq("FALSE").to_numpy()})
    rr = r[["key", "sgp", "category", "list", "pointEndType", "t1NetPoint", "t2NetPoint"]]
    out = out.merge(rr, on=["key", "sgp"], how="left")
    out["ra_shot"] = out["category"].map(SHOT).fillna(0).astype("int16")
    lst = out["list"].fillna("").astype(str)
    out["ra_team"] = np.select([lst.str.startswith("t1"), lst.str.startswith("t2")], [1, 2], 0).astype("int8")
    out["ra_won"] = lst.str.endswith("win")
    out["ra_end"] = out["pointEndType"].fillna("").astype(str).str.upper()
    # net: P9's MatchBeats flags, else the rally files' (the same 24 events: field_profile.json)
    if source == "p9":
        n1 = p["tm1AtNet"].astype(str).eq("TRUE").to_numpy() | out["t1NetPoint"].astype(str).eq("TRUE").to_numpy()
        n2 = p["tm2AtNet"].astype(str).eq("TRUE").to_numpy() | out["t2NetPoint"].astype(str).eq("TRUE").to_numpy()
    else:
        n1 = out["t1NetPoint"].astype(str).eq("TRUE").to_numpy()
        n2 = out["t2NetPoint"].astype(str).eq("TRUE").to_numpy()
    rec = pd.Series(n1 | n2).groupby(out["key"].to_numpy()).transform("any").to_numpy()
    out["net1"] = np.where(rec, n1.astype(int), -1).astype("int8")
    out["net2"] = np.where(rec, n2.astype(int), -1).astype("int8")
    out = out.drop(columns=["category", "list", "pointEndType", "t1NetPoint", "t2NetPoint"])
    out = out.sort_values(["key", "set_no", "game_no", "point_no"], kind="mergesort").reset_index(drop=True)
    return out


INCLUSIVE_MAX = 0.2             # an event whose error counts fit the standard rule at most this often counts the error
STANDARD_MIN = 0.8


def event_rules(p: pd.DataFrame) -> pd.DataFrame:
    """Per event (source|year|event): how its MatchBeats counts treat the erring shot. Among tracked error points (FE,
    UE) with a count of 1..MAX_COUNT, the share whose last ball in was hit by the point's winner (the standard rule:
    the erring shot is not counted). 'standard' at STANDARD_MIN or more, 'inclusive' (the count includes the erring
    shot; the last counted shot was the loser's) at INCLUSIVE_MAX or less, else 'unclear' (read as standard: per-point
    parity and the match gate then drop what does not fit)."""
    ev = p["key"].str.rsplit("|", n=1).str[0]
    err = p["result"].isin(["FE", "UE"]) & p["tracked"] & p["old"].between(1, MAX_COUNT)
    oi = p["old"].fillna(0).astype("int64")
    last_in = np.where(oi % 2 == 1, p["server"], 3 - p["server"])
    std = pd.Series(last_in == p["scorer"].to_numpy(), index=p.index)
    g = pd.DataFrame({"event": ev[err], "std": std[err]}).groupby("event")["std"].agg(["size", "mean"])
    g.columns = ["error_points", "standard_share"]
    g["rule"] = np.select([g["standard_share"] >= STANDARD_MIN, g["standard_share"] <= INCLUSIVE_MAX],
                          ["standard", "inclusive"], "unclear")
    return g.reset_index()


def mb_convention(p: pd.DataFrame, rules: pd.DataFrame | None = None) -> pd.DataFrame:
    """The shot-level convention for MatchBeats points (read_atp_points). Adds rally (-1 unknown), end, ender (1/2, 0
    unknown), how (where the value came from, or why it is unknown) and rule (the event's counting rule, event_rules):

        ace / df        the ending alone: rally 1 / 0 (known in every match; the match gate decides whether the match's
                        rally lengths are measured)
        mb              a winner: the count of shots in; an error (FE, UE): the count + 1 (the erring shot); at an
                        event whose counts include the erring shot ('inclusive', e.g. Roland Garros 2026): the count,
                        and an unclassified ending (N) of 2 or more shots: the count
        mb_svc          a count of 1 won by the server, ended as a winner or unclassified: a serve won without an ace,
                        shot 2 (the returner's forced error, as the shot-level convention classifies it)
        mb_list         an unclassified ending (N) whose rally-file row says whether the last shot won (count) or
                        erred (count + 1)
        ra              no usable count, but the rally file names the shot that ended the point (capped at 9 / 10, as
                        the Infosys groups of the Hugging Face copy)
        untracked       the file flags the point untracked, or a rally-ended point carries a count of 0
        garbage         a count outside 0..MAX_COUNT
        parity          the count's last ball in was not hit by the point's winner (count or winner wrong)
        n_unresolved    an unclassified ending with no rally-file row to tell a winner (count) from an error (+1)
    """
    rules = event_rules(p) if rules is None else rules
    ev = p["key"].str.rsplit("|", n=1).str[0]
    rule = ev.map(rules.set_index("event")["rule"]).fillna("unclear").to_numpy()
    incl = rule == "inclusive"
    srv, sc, res = p["server"].to_numpy(), p["scorer"].to_numpy(), p["result"].to_numpy()
    old = p["old"].to_numpy(dtype="float64")
    tracked = p["tracked"].to_numpy()
    ok_players = np.isin(srv, [1, 2]) & np.isin(sc, [1, 2])
    n = len(p)
    rally = np.full(n, -1, dtype="int64")
    end = np.zeros(n, dtype="int8")
    ender = np.zeros(n, dtype="int8")
    how = np.full(n, "untracked", dtype=object)
    is_a, is_df = res == "A", res == "DF"
    rally[is_a], end[is_a], ender[is_a], how[is_a] = 1, END["ace"], srv[is_a], "ace"
    rally[is_df], end[is_df], ender[is_df], how[is_df] = 0, END["df"], srv[is_df], "df"
    rest = ~is_a & ~is_df & ok_players
    finite = np.isfinite(old)
    garbage = rest & tracked & finite & ((old < 0) | (old > MAX_COUNT))
    how[garbage] = "garbage"
    usable = rest & tracked & finite & (old >= 1) & (old <= MAX_COUNT)
    oi = np.where(finite, old, 0).astype("int64")
    last_in = np.where(oi % 2 == 1, srv, 3 - srv)          # shot k is the server's when k is odd
    loser = 3 - sc
    is_err = np.isin(res, ["FE", "UE"])
    # the standard rule: the last ball counted is the winner's; at an inclusive event an error's last counted shot is
    # the erring one (the loser's) and an unclassified ending cannot be checked
    parity_ok = np.where(incl & is_err, last_in == loser, np.where(incl & (res == "N"), True, last_in == sc))
    bad = usable & ~parity_ok
    how[bad] = "parity"
    good = usable & parity_ok
    # inclusive events: errors and unclassified endings of 2+ shots are the count itself
    inc_err = good & incl & is_err & (oi >= 2)
    rally[inc_err], ender[inc_err], how[inc_err] = oi[inc_err], loser[inc_err], "mb"
    end[inc_err] = np.where(res[inc_err] == "FE", END["forced"], END["unforced"])
    inc_n = good & incl & (res == "N") & (oi >= 2)
    rally[inc_n], how[inc_n] = oi[inc_n], "mb"
    how[good & incl & is_err & (oi < 2)] = "parity"          # a one-shot error at an inclusive event: a double fault?
    how[good & incl & (res == "N") & (oi < 2)] = "n_unresolved"
    good = (good & ~incl) | (good & incl & (res == "W"))
    # winners
    w = good & (res == "W")
    w_svc = w & (oi == 1)
    w_rest = w & (oi >= 2)
    rally[w_rest], end[w_rest], ender[w_rest], how[w_rest] = oi[w_rest], END["winner"], sc[w_rest], "mb"
    rally[w_svc], end[w_svc], ender[w_svc], how[w_svc] = 2, END["forced"], (3 - srv)[w_svc], "mb_svc"
    # errors: the erring shot is not in the count
    for code, e in (("FE", END["forced"]), ("UE", END["unforced"])):
        m_ = good & (res == code)
        rally[m_], end[m_], ender[m_], how[m_] = oi[m_] + 1, e, loser[m_], "mb"
    # unclassified endings
    nn = good & (res == "N")
    n_svc = nn & (oi == 1)                                   # only the serve landed in and the server won: shot 2
    rally[n_svc], end[n_svc], ender[n_svc], how[n_svc] = 2, END["unknown"], (3 - srv)[n_svc], "mb_svc"
    ra_shot, ra_team, ra_won = p["ra_shot"].to_numpy(), p["ra_team"].to_numpy(), p["ra_won"].to_numpy()
    ra_end = p["ra_end"].to_numpy()
    n_more = nn & (oi >= 2)
    by_list_win = n_more & (ra_team == sc) & ra_won & (ra_shot > 0)
    by_list_err = n_more & (ra_team == loser) & ~ra_won & (ra_shot > 0)
    rally[by_list_win], end[by_list_win], ender[by_list_win] = oi[by_list_win], END["winner"], sc[by_list_win]
    how[by_list_win] = "mb_list"
    e_code = np.select([ra_end == "FORCED ERROR", ra_end == "UNFORCED ERROR"], [END["forced"], END["unforced"]],
                       END["unknown"]).astype("int8")
    rally[by_list_err], end[by_list_err], ender[by_list_err] = oi[by_list_err] + 1, e_code[by_list_err], \
        loser[by_list_err]
    how[by_list_err] = "mb_list"
    unres = n_more & ~by_list_win & ~by_list_err
    how[unres] = "n_unresolved"
    # no usable count: the rally file's category, where it names the shot (the Hugging Face copy's reading)
    no_count = rest & (rally < 0) & ~np.isin(how, ["parity", "n_unresolved"]) & (ra_shot > 0) & np.isin(ra_team, [1, 2])
    shot = ra_shot.astype("int64")
    team = ra_team.astype("int64")
    ra_server = np.where(shot % 2 == 1, team, 3 - team)
    ra_winner = np.where(ra_won, team, 3 - team)
    consistent = no_count & (ra_server == srv) & (ra_winner == sc)
    svc = consistent & (shot == 1) & ra_won & (ra_end != "ACE")
    plain = consistent & ~svc & (shot >= 2)
    rally[plain] = shot[plain]
    end[plain] = np.select([ra_won[plain], ra_end[plain] == "FORCED ERROR", ra_end[plain] == "UNFORCED ERROR"],
                           [END["winner"], END["forced"], END["unforced"]], END["unknown"])
    ender[plain] = team[plain]
    how[plain] = "ra"
    rally[svc], end[svc], ender[svc], how[svc] = 2, END["forced"], (3 - srv)[svc], "ra"
    out = p.copy()
    out["rally"] = rally.astype("int16")
    out["end"] = end
    out["ender"] = ender
    out["how"] = how
    out["rule"] = rule
    return out


def match_gate(key: pd.Series, rally: pd.Series, end: pd.Series) -> pd.DataFrame:
    """Per match: points, points other than aces and double faults (rp), how many of those have a rally length
    (rp_known), the share, and carries = share >= GATE (and at least one such point)."""
    rp = ~end.isin([END["ace"], END["df"]])
    known = rp & (rally >= 1)
    g = pd.DataFrame({"key": key.to_numpy(), "rp": rp.to_numpy(), "known": known.to_numpy()})
    a = g.groupby("key").agg(points=("rp", "size"), rp=("rp", "sum"), rp_known=("known", "sum"))
    a["share"] = a["rp_known"] / a["rp"].where(a["rp"] > 0)
    a["carries"] = a["share"].fillna(0).ge(GATE) & a["rp"].gt(0)
    return a.reset_index()


# ------------------------------------------------------------------------------------------------
# Stage 0

def stage0_men(columns: list[str] | None = None, from_year: int = 2010) -> pd.DataFrame:
    cols = None if columns is None else list(dict.fromkeys(["match_id", "tour", "year"] + list(columns)))
    m = pd.read_parquet(STAGE0, columns=cols)
    return m[m["tour"].eq("atp") & (m["year"] >= from_year)].reset_index(drop=True)


def stage0_names(match_ids) -> pd.DataFrame:
    """match_id, side, player_id, player_name (Stage 0's match players; no result column read)."""
    mp = pd.read_parquet(STAGE0_PLAYERS, columns=["match_id", "player_id", "side", "player_name"])
    return mp[mp["match_id"].isin(set(match_ids))].reset_index(drop=True)


def id_remap() -> dict:
    """old -> new Stage 0 match ids over every rebuild since the shot-level study's links (2 Oct 2026), chained."""
    remap: dict = {}
    for f in sorted(REBUILDS.glob("*/id_map.csv")):
        m = pd.read_csv(f, usecols=["old_match_id", "new_match_id"])
        step = dict(zip(m["old_match_id"], m["new_match_id"]))
        remap = {k: step.get(v, v) for k, v in remap.items()}
        for k, v in step.items():
            remap.setdefault(k, v)
    return remap


# ------------------------------------------------------------------------------------------------
# As-of sums over a 52-week window on Stage 0's clock

def window_sums(rows: pd.DataFrame, values: list[str], days: int = 364, player: str = "player_id",
                date: str = "tournament_date", event: str = "tournament_id", rnd: str = "round_order") -> pd.DataFrame:
    """For each player-match row, the sum of ``values`` over the same player's earlier matches within the window:
    events with a tournament date in [date - days + 1, date - 1] (the 51 weeks before, for Monday dates), plus the
    earlier rounds of the same event (same tournament id and date, lower round order). Never the match itself, other
    matches of the same round, or other events of the same date. Stage 0's clock, as predictability_diagnostic
    common.asof_sums, with a window.

    Vectorised: per player, sums by day and their cumulative sums; the window is two searchsorted look-ups."""
    v = rows[[player, date, event, rnd]].copy()
    v[date] = pd.to_datetime(v[date]).astype("datetime64[ns]")
    vals = rows[values].apply(pd.to_numeric, errors="coerce").fillna(0.0).astype("float64")
    v[values] = vals
    by_day = v.groupby([player, date], sort=True)[values].sum().reset_index()
    by_day = by_day.sort_values([player, date], kind="mergesort").reset_index(drop=True)
    cum = by_day.groupby(player, sort=False)[values].cumsum()
    # global position arrays: for each player the slice of by_day rows
    pcodes, puniq = pd.factorize(by_day[player], sort=False)
    start_idx = np.searchsorted(pcodes, np.arange(len(puniq)), side="left") if (np.diff(pcodes) >= 0).all() else None
    if start_idx is None:
        raise RuntimeError("by_day is not grouped by player")
    end_idx = np.append(start_idx[1:], len(by_day))
    pos = {p: i for i, p in enumerate(puniq)}
    dnum = by_day[date].to_numpy().astype("int64")
    cumv = cum.to_numpy()
    out = np.zeros((len(v), len(values)))
    pi = v[player].map(pos)
    has = pi.notna().to_numpy()
    pi = pi.fillna(-1).astype("int64").to_numpy()
    t = v[date].to_numpy().astype("int64")
    lo_t = t - np.int64(days - 1) * 86_400_000_000_000
    for j in np.flatnonzero(has):
        s, e = start_idx[pi[j]], end_idx[pi[j]]
        d = dnum[s:e]
        a = np.searchsorted(d, t[j], side="left")           # days < t
        b = np.searchsorted(d, lo_t[j], side="left")        # days < t - days + 1
        upper = cumv[s + a - 1] if a > 0 else 0.0
        lower = cumv[s + b - 1] if b > 0 else 0.0
        out[j] = upper - lower
    # earlier rounds of the same event (same date)
    by_round = v.groupby([player, date, event, rnd], sort=True)[values].sum()
    before_round = by_round.groupby(level=[0, 1, 2], sort=False).cumsum() - by_round
    b2 = before_round.reindex(pd.MultiIndex.from_frame(v[[player, date, event, rnd]])).to_numpy()
    return pd.DataFrame(out + np.nan_to_num(b2), index=rows.index, columns=values)


def window_sums_slow(rows: pd.DataFrame, values: list[str], days: int = 364, player: str = "player_id",
                     date: str = "tournament_date", event: str = "tournament_id",
                     rnd: str = "round_order") -> pd.DataFrame:
    """The same as window_sums by a direct look-back, row by row (for the tests and the probe)."""
    r = rows.copy()
    r[date] = pd.to_datetime(r[date])
    out = np.zeros((len(r), len(values)))
    grp = {p: g for p, g in r.groupby(player)}
    for i, (p, d, ev, ro) in enumerate(zip(r[player], r[date], r[event], r[rnd])):
        g = grp[p]
        earlier = (g[date] < d) & (g[date] >= d - pd.Timedelta(days=days - 1))
        same = (g[date] == d) & (g[event] == ev) & (g[rnd] < ro)
        out[i] = g.loc[earlier | same, values].apply(pd.to_numeric, errors="coerce").fillna(0).sum().to_numpy()
    return pd.DataFrame(out, index=rows.index, columns=values)
