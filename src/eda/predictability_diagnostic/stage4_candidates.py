"""The Stage 4 plan: how much of the data each candidate covers, and how many comparisons the plan makes.

The candidate list (docs/studies/predictability_diagnostic/candidates.md, with the hand-made table
data/studies/predictability_diagnostic/stage4_candidates.csv) is fixed before Stage 4 computes anything against
results. This script only counts: for every candidate and form, the evaluation matches on which the feature would
be defined for both players, by tour, level group and year; how often a few features are non-zero; and how many
comparisons the scoring plan makes. It reads no result: not Stage 0's won or a_won, no baseline's probability, no
tennis-data winner. Where a past match's score is used (did it reach a deciding set?), it is read without asking
who won it.

Every history count follows the Brief's time rule through common.asof_sums (earlier events and earlier rounds of
the same event only), as Stage 4's features will.

Coverage rules (what "defined" means here, as the plan states them):
    statistics      the player has at least one earlier match carrying the statistic in the form's window:
                    career (also the decayed and opponent-adjusted forms), the last 52 weeks, or the target's surface.
                    History is Stage 3's: completed matches in the standard format from 2010, every level (match wins
                    and meetings also count retirements). "halfK": the career history carries at least Stage 3's
                    shrinkage constant K in units, so the player's own rate counts at least half.
    head to head    at least one earlier meeting (completed or retired) in the window.
    matchups        every statistic of the matchup defined for both players.
    single features as listed in key_rows() below.

Writes, in data/studies/predictability_diagnostic/:
    stage4_candidates_coverage.csv   coverage key x tour x level group x year: evaluation matches, matches with
                                     the feature defined for both players
    stage4_candidates_summary.json   pooled coverage per candidate and form, prevalences, the entry-recording
                                     gaps, the point-by-point name link, the event-country sources and the
                                     comparison counts

Run: ./python.sh src/eda/predictability_diagnostic/stage4_candidates.py   (about two minutes)
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic.stage3_traits import sums_before  # noqa: E402

CANDIDATES = C.OUT / "stage4_candidates.csv"
COVERAGE = C.OUT / "stage4_candidates_coverage.csv"
SUMMARY = C.OUT / "stage4_candidates_summary.json"
SHRINKAGE = C.OUT / "stage3_shrinkage.csv"
RATINGS = C.OUT / "stage3_ratings.parquet"
ODDS = C.OUT / "stage1_odds.parquet"
PBP_PLAYERS = C.OUT / "stage2_pbp_players.parquet"
WTA_EDITIONS = C.DUMP / "points" / "wta" / "editions.parquet"
OTD_TOURNAMENTS = C.DUMP / "matches" / "open_tennis_data" / "tournaments.parquet"

LEVEL_GROUPS = {"GS": "Grand Slams", "FIN": "Tour Finals", "T1000": "1000s", "T500": "500s", "T250": "250s",
                "GSQ": "Grand Slam qualifying", "TQ": "Tour qualifying", "CH": "Challenger / WTA 125",
                "CHQ": "Challenger / 125 qualifying"}
MAIN_TOUR = ("GS", "FIN", "T1000", "T500", "T250")
SURFACES = {"Hard": 1, "Clay": 2, "Grass": 3, "Carpet": 4}
WEEK52 = 364                       # days: the last 52 weeks (Stage 3's)
WINDOWS = (7, 14)                  # days between tournament Mondays: the fatigue windows
ELO_CHANGE = {"elo_change_26w": 182, "elo_change_52w": 364}
SURFACE_FIRST = 3                  # "one of the first matches": fewer than this many earlier on the surface this season
ENTRY_TYPES = {"q": ["Q"], "ll": ["LL"], "wc": ["WC"], "pr": ["PR", "SR"]}   # SR: the WTA's special (protected) ranking
AGE_RANGE = (14.0, 50.0)           # ages outside are read as missing (one source value is 3,387)
ESTABLISHED = 2000                 # rated serve points of an established player (Stage 3's sanity check)
SCORE_STATS = ("tb_won", "sets_won", "games_won", "win", "deciding")
DERIVED = ("rpw_first", "rpw_second", "bp_over", "win", "deciding")
HIST_STATS = list(C.RATES) + list(DERIVED)
FORM_WINDOW = {"career": "career", "52 weeks": "52w", "decayed": "career", "surface": "surface",
               "adjusted": "career", "single": None}
COPIES = 20                        # shuffled copies per comparison (the null band)
ERAS = list(C.ERAS)
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def level_group(level: pd.Series, qualifying: pd.Series) -> pd.Series:
    """Stage 1's nine groups: the five main-tour levels, Grand Slam and tour qualifying, Challenger / WTA 125 and
    its qualifying."""
    q = qualifying.astype(bool).to_numpy()
    lv = level.astype(object).to_numpy().copy()
    lv[q & (lv == "GS")] = "GSQ"
    lv[q & np.isin(lv, ["T1000", "T500", "T250", "FIN"])] = "TQ"
    lv[q & (lv == "CH")] = "CHQ"
    return pd.Series(lv, index=level.index)


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s.replace("-", " ")).split())


# ------------------------------------------------------------------------------------------------
# Inputs

def load() -> pd.DataFrame:
    """Every player-match, two rows per match (A then B), in the table's order. No result column is read."""
    rate_cols = [f"{r}_{x}" for r in C.RATES for x in ("n", "d")]
    mp = C.load_match_players(["match_id", "player_id", "opponent_id", "side", "player_name", "rank", "rank_points",
                               "entry", "age", "height", "hand", "country"] + rate_cols,
                              match_columns=["tour", "year", "level", "qualifying", "evaluation", "status", "format",
                                             "surface", "best_of", "minutes", "tournament_name"])
    assert "won" not in mp.columns and "a_won" not in mp.columns
    assert (mp["side"].to_numpy()[0::2] == "A").all() and (mp["side"].to_numpy()[1::2] == "B").all()
    assert (mp["match_id"].to_numpy()[0::2] == mp["match_id"].to_numpy()[1::2]).all()
    mp["day"] = mp["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    mp["pcode"] = pd.factorize(mp["player_id"])[0].astype("int64")
    mp["group"] = level_group(mp["level"], mp["qualifying"])
    return mp


def opp(a: np.ndarray) -> np.ndarray:
    """The other player's value in the same match (rows come in A, B pairs)."""
    a = np.asarray(a)
    return a.reshape(-1, 2)[:, ::-1].reshape(-1)


def both(a: np.ndarray) -> np.ndarray:
    """Per match (A, B pairs): whether the condition holds for both players."""
    return np.asarray(a, dtype=bool).reshape(-1, 2).all(axis=1)


def history_units(mp: pd.DataFrame) -> dict:
    """Per statistic, the units each player-match adds to a history (0 where it adds none)."""
    st, fmt = mp["status"].to_numpy(), mp["format"].to_numpy()
    box_hist = (st == "completed") & (fmt == "standard")
    played = np.isin(st, ["completed", "retired"])
    units = {}
    for s in C.RATES:
        n, d = mp[f"{s}_n"].to_numpy(dtype="float64"), mp[f"{s}_d"].to_numpy(dtype="float64")
        ok = box_hist & ~np.isnan(n) & ~np.isnan(d)
        units[s] = np.where(ok, d, 0.0)
    fw_n, fw_d = (mp[c].to_numpy(dtype="float64") for c in ("first_won_n", "first_won_d"))
    sw_n, sw_d = (mp[c].to_numpy(dtype="float64") for c in ("second_won_n", "second_won_d"))
    ok = box_hist & ~np.isnan(opp(fw_n)) & ~np.isnan(opp(fw_d))
    units["rpw_first"] = np.where(ok, opp(fw_d), 0.0)
    ok = box_hist & ~np.isnan(opp(sw_n)) & ~np.isnan(opp(sw_d))
    units["rpw_second"] = np.where(ok, opp(sw_d), 0.0)
    bps, bpc = units["bp_saved"], units["bp_conv"]
    spw = mp["spw_d"].to_numpy(dtype="float64")
    ok = (bps + bpc > 0) & box_hist & ~np.isnan(spw) & ~np.isnan(opp(spw)) & (mp["bp_saved_d"].notna() & mp["bp_conv_d"].notna()).to_numpy()
    units["bp_over"] = np.where(ok, bps + bpc, 0.0)
    units["win"] = played.astype("float64")
    units["deciding"] = (deciding_set(mp) & (st == "completed")).astype("float64")
    return units


def deciding_set(mp: pd.DataFrame) -> np.ndarray:
    """Whether the match reached a deciding set, from the score alone: the sets played equal twice the larger of
    the two players' sets won, less one (2-1 or 3-2). A match tiebreak in place of the deciding set counts as one.
    Read without asking which player won."""
    total = mp["sets_won_d"].to_numpy(dtype="float64")
    sets = mp["sets_won_n"].to_numpy(dtype="float64").reshape(-1, 2)
    w = np.where(np.isnan(sets).all(axis=1), np.nan, np.fmax(sets[:, 0], sets[:, 1])).repeat(2)
    with np.errstate(invalid="ignore"):
        return (w >= 2) & (total == 2 * w - 1)


def asof(mp: pd.DataFrame, values: dict, key: np.ndarray) -> dict:
    """common.asof_sums of each value column, grouped by ``key`` instead of the player alone."""
    tmp = mp[["tournament_date", "tournament_id", "round_order"]].copy()
    tmp["_key"] = key
    names = list(values)
    for i, name in enumerate(names):
        tmp[f"_v{i}"] = values[name]
    s = C.asof_sums(tmp, [f"_v{i}" for i in range(len(names))], player="_key")
    return {name: s[f"_v{i}"].to_numpy() for i, name in enumerate(names)}


def before(mp: pd.DataFrame, values: dict, key: np.ndarray, days: int) -> dict:
    """Sums over the same key's rows of events starting more than ``days`` before this event (Stage 3's
    sums_before): subtracted from the as-of sums, it leaves the window of the last ``days`` days."""
    names = list(values)
    V = np.column_stack([values[n] for n in names])
    day = mp["day"].to_numpy()
    s = sums_before(key, day, V, key, day - days)
    return {n: s[:, i] for i, n in enumerate(names)}


def previous_row(mp: pd.DataFrame, mask: np.ndarray) -> np.ndarray:
    """For every row in ``mask``: the index of the same player's previous row in ``mask`` under the time rule, or
    -1. An earlier round of the same event comes first; otherwise the last row of the latest earlier tournament
    week. Never another match of the same round (a round robin) or another event of the same week."""
    idx = np.flatnonzero(mask)
    sub = pd.DataFrame({"i": idx, "p": mp["pcode"].to_numpy()[idx], "d": mp["day"].to_numpy()[idx],
                        "e": pd.factorize(mp["tournament_id"])[0][idx], "r": mp["round_order"].to_numpy()[idx],
                        "o": mp["order"].to_numpy()[idx]})
    sub = sub.sort_values(["p", "d", "e", "r", "o"], kind="mergesort").reset_index(drop=True)
    p, d, e, r = (sub[c].to_numpy() for c in ("p", "d", "e", "r"))
    n = len(sub)
    pos = np.arange(n)
    new_day = np.r_[True, (p[1:] != p[:-1]) | (d[1:] != d[:-1])]
    cand_b = np.maximum.accumulate(np.where(new_day, pos, 0)) - 1
    cb = np.maximum(cand_b, 0)
    ok_b = (cand_b >= 0) & (p[cb] == p)
    new_round = np.r_[True, (p[1:] != p[:-1]) | (d[1:] != d[:-1]) | (e[1:] != e[:-1]) | (r[1:] != r[:-1])]
    cand_a = np.maximum.accumulate(np.where(new_round, pos, 0)) - 1
    ca = np.maximum(cand_a, 0)
    ok_a = (cand_a >= 0) & (p[ca] == p) & (d[ca] == d) & (e[ca] == e)
    prev_pos = np.where(ok_a, cand_a, np.where(ok_b, cand_b, -1))
    out = np.full(len(mp), -1, dtype="int64")
    out[sub["i"].to_numpy()] = np.where(prev_pos >= 0, sub["i"].to_numpy()[np.maximum(prev_pos, 0)], -1)
    return out


# ------------------------------------------------------------------------------------------------
# Coverage per row

def key_rows(mp: pd.DataFrame, shr: pd.DataFrame) -> tuple[dict, dict, dict]:
    """Per coverage key, whether each player-row has the feature defined; and a few prevalences (per row)."""
    rows, prev, info = {}, {}, {}
    n = len(mp)
    pcode, day = mp["pcode"].to_numpy(), mp["day"].to_numpy()
    st = mp["status"].to_numpy()
    played = np.isin(st, ["completed", "retired"])
    surf = mp["surface"].map(SURFACES).fillna(0).astype("int64").to_numpy()
    year = mp["year"].to_numpy().astype("int64")
    tour = mp["tour"].to_numpy()

    # statistics: career, last 52 weeks, surface; and whether the career history reaches K units
    units = history_units(mp)
    for chunk in (HIST_STATS[:11], HIST_STATS[11:]):
        vals = {s: units[s] for s in chunk}
        car = asof(mp, vals, pcode)
        bef = before(mp, vals, pcode, WEEK52)
        sur = asof(mp, vals, pcode * 8 + surf)
        for s in chunk:
            rows[f"hist:{s}:career"] = car[s] > 0
            rows[f"hist:{s}:52w"] = (car[s] - bef[s]) > 0.5
            rows[f"hist:{s}:surface"] = (sur[s] > 0) & (surf > 0)
            if s in C.RATES:
                K = shr[(shr["stat"] == s) & (shr["surface"] == "all") & (shr["years"] == "2010-2018")].set_index("tour")["K_units"]
                rows[f"hist:{s}:halfK"] = car[s] >= np.where(tour == "atp", K["atp"], K["wta"])
        log(f"  histories: {chunk[0]} ... {chunk[-1]}")

    # head to head: earlier meetings of the same two players
    pair = pd.factorize(np.where(mp["player_id"] < mp["opponent_id"], mp["player_id"] + "|" + mp["opponent_id"],
                                 mp["opponent_id"] + "|" + mp["player_id"]))[0].astype("int64")
    one = {"m": 0.5 * played}                  # both rows of a meeting carry the pair's key: half each
    car = asof(mp, one, pair)["m"]
    bef = before(mp, one, pair, WEEK52)["m"]
    sur = asof(mp, one, pair * 8 + surf)["m"]
    rows["h2h:career"], rows["h2h:52w"], rows["h2h:surface"] = car > 0.5, (car - bef) > 0.5, (sur > 0.5) & (surf > 0)
    info["h2h_meetings"] = car

    # rankings, ratings, players
    rows["rank_known"] = mp["rank"].notna().to_numpy()
    rows["points_known"] = mp["rank_points"].notna().to_numpy()
    age = mp["age"].to_numpy(dtype="float64")
    rows["age"] = (age >= AGE_RANGE[0]) & (age <= AGE_RANGE[1])
    rows["height"] = mp["height"].notna().to_numpy()
    hand = mp["hand"].to_numpy(dtype=object)
    rows["hand"] = np.isin(hand, ["R", "L"])
    rows["country_player"] = mp["country"].notna().to_numpy()
    rt = pd.read_parquet(RATINGS, columns=["match_id", "serve_pts_a", "serve_pts_b"]).set_index("match_id")
    rt = rt.reindex(mp["match_id"].to_numpy()[0::2])
    pts = np.column_stack([rt["serve_pts_a"].to_numpy(), rt["serve_pts_b"].to_numpy()]).reshape(-1)
    rows["ratings_any"] = pts > 0
    rows["ratings_established"] = pts >= ESTABLISHED

    # record against the opponent's hand: total points won history against players of that hand
    hcode = np.select([hand == "R", hand == "L"], [1, 2], 0)
    tpw_units = {"t": units["tpw"]}
    vs = asof(mp, tpw_units, pcode * 3 + opp(hcode))["t"]
    rows["vs_hand"] = rows["hand"] & opp(rows["hand"]) & (vs > 0)

    # the previous match: played (completed or retired) for rest and fatigue; scheduled (any status) for an early end
    minutes = mp["minutes"].to_numpy(dtype="float64")
    sets_total = mp["sets_won_d"].to_numpy(dtype="float64")
    pp = previous_row(mp, played)
    ps = previous_row(mp, np.ones(n, dtype=bool))
    rows["prev_played"] = pp >= 0
    rows["prev_scheduled"] = ps >= 0
    rows["prev_minutes"] = (pp >= 0) & ~np.isnan(minutes[np.maximum(pp, 0)])
    rows["prev_sets"] = (pp >= 0) & ~np.isnan(sets_total[np.maximum(pp, 0)])
    prev["prev_scheduled_early"] = (ps >= 0) & np.isin(st[np.maximum(ps, 0)], ["retired", "walkover"])
    prev["prev_scheduled_walkover"] = (ps >= 0) & (st[np.maximum(ps, 0)] == "walkover")
    gap = np.where(pp >= 0, day - day[np.maximum(pp, 0)], -1)
    info["days_since"] = gap

    # fatigue windows: this event's earlier rounds plus events starting up to 7 or 14 days before this one
    wv = {"m": played.astype("float64"), "no_min": (played & np.isnan(minutes)).astype("float64"),
          "no_sets": (played & np.isnan(sets_total)).astype("float64")}
    car = asof(mp, wv, pcode)
    for w in WINDOWS:
        bef = before(mp, wv, pcode, w)
        rows[f"win{w}_minutes"] = (car["no_min"] - bef["no_min"]) < 0.5
        rows[f"win{w}_sets"] = (car["no_sets"] - bef["no_sets"]) < 0.5
        info[f"win{w}_matches"] = car["m"] - bef["m"]
    bef = before(mp, wv, pcode, WEEK52)
    rows["recent_level"] = (car["m"] - bef["m"]) > 0.5
    info["played_career"] = car["m"]

    # the rating's change: the player's first match on or before 26 (52) weeks ago
    first = pd.Series(day[played]).groupby(pcode[played]).min()
    fday = first.reindex(pcode).to_numpy()
    for k, d in ELO_CHANGE.items():
        rows[k] = fday <= day - d

    # one of the first matches on this surface this season
    season = asof(mp, {"m": played.astype("float64")}, (pcode * 20 + (year - 2009)) * 8 + surf)["m"]
    rows["surface_known"] = surf > 0
    prev["surface_first"] = (surf > 0) & (season < SURFACE_FIRST)

    # entry type: an event records entries when some player of its main draw (its qualifying) carries a code
    code = mp["entry"].notna().to_numpy()
    q = mp["qualifying"].to_numpy(dtype=bool)
    ev = pd.factorize(mp["tournament_id"].astype(str) + "|" + mp["tournament_date"].astype(str))[0]
    rec_main = pd.Series(code & ~q).groupby(ev).any().reindex(ev).to_numpy()
    rec_qual = pd.Series(code & q).groupby(ev).any().reindex(ev).to_numpy()
    rows["entry_recorded"] = np.where(q, rec_qual, rec_main)
    # each type only in tour x level group x year cells where its code appears at least once among such events; a
    # qualifier or lucky loser exists only in a main draw
    entry = mp["entry"].fillna("").to_numpy(dtype=object)
    cell = (mp["tour"] + "|" + mp["group"] + "|" + mp["year"].astype(str)).to_numpy()
    rec = rows["entry_recorded"].astype(bool)
    evl = mp["evaluation"].to_numpy(dtype=bool)
    for k, codes in ENTRY_TYPES.items():
        has_code = np.isin(entry, codes)
        prev[f"entry_{k}"] = has_code
        seen = pd.Series(has_code & rec & evl).groupby(cell).any()
        ok = seen.reindex(cell).fillna(False).to_numpy(dtype=bool)
        rows[f"entry_{k}"] = rec & ok & (~q if k in ("q", "ll") else True)

    # left-handed against right-handed: exactly one of the two is left-handed (both hands known)
    prev["lefty_vs_righty"] = rows["hand"] & opp(rows["hand"]) & ((hand == "L") != (opp(hand) == "L"))
    return rows, prev, info


def name_parts(name: str) -> tuple[list, list]:
    """A name's words and its initials ("R. Nadal", "Ka. Pliskova", "N Djokovic"), each normalised."""
    words, initials = [], []
    for tok in str(name).replace("-", " ").split():
        t = norm_name(tok).replace(" ", "")
        if not t:
            continue
        (initials if tok.endswith(".") or len(t) == 1 else words).append(t)
    return words, initials


def link_in_event(name: str, cands: list) -> str | None:
    """The Stage 0 id of a point-by-point player among the players of the same Grand Slam draw (``cands``: id and
    name words). In turn: the same words; the file's words all in a candidate's name, or the reverse, with the
    initials agreeing with the first name; the same last word. Only a single candidate links."""
    words, initials = name_parts(name)
    if not words:
        return None

    def initials_ok(cw):
        return not initials or any(cw[0].startswith(i) for i in initials)
    for test in (lambda cw: cw == words,
                 lambda cw: (set(words) <= set(cw) or set(cw) <= set(words)) and initials_ok(cw),
                 lambda cw: cw[-1] == words[-1] and initials_ok(cw)):
        hit = {pid for pid, cw in cands if cw and test(cw)}
        if len(hit) == 1:
            return hit.pop()
        if len(hit) > 1:
            return None
    return None


def pbp_rows(mp: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """Whether each player-row has at least one earlier Grand Slam match in the point-by-point files (Stage 2's
    validated matches). The files name players, often by initial and surname (2018-2021), so each is linked to a
    Stage 0 id among the players of the same Slam's main draw that year (link_in_event)."""
    p = pd.read_parquet(PBP_PLAYERS, columns=["match_id", "tour", "player"])
    p["year"] = p["match_id"].str.slice(0, 4).astype(int)
    slam = {"ausopen": "australian open", "frenchopen": "roland garros", "wimbledon": "wimbledon", "usopen": "us open"}
    p["slam"] = p["match_id"].str.split("-").str[1].map(slam)
    gs = mp[mp["level"].eq("GS") & ~mp["qualifying"].astype(bool)][["tour", "year", "tournament_name", "day", "player_id", "player_name"]]
    gs = gs.assign(slam=gs["tournament_name"].str.lower())
    days = gs.drop_duplicates(["tour", "year", "slam"])[["tour", "year", "slam", "day"]]
    p = p.merge(days, on=["tour", "year", "slam"], how="left")
    draw = {k: [(pid, name_parts(nm)[0]) for pid, nm in g[["player_id", "player_name"]].drop_duplicates().itertuples(index=False)]
            for k, g in gs.groupby(["tour", "year", "slam"])}
    p["player_id"] = [link_in_event(nm, draw.get((t, y, s), [])) for nm, t, y, s in
                      p[["player", "tour", "year", "slam"]].itertuples(index=False)]
    linked = p[p["player_id"].notna() & p["day"].notna()]
    pcode_of = pd.Series(mp["pcode"].to_numpy(), index=mp["player_id"].to_numpy())
    pcode_of = pcode_of[~pcode_of.index.duplicated()]
    hp = pcode_of.reindex(linked["player_id"]).to_numpy().astype("int64")
    hd = linked["day"].to_numpy().astype("int64")
    count = sums_before(hp, hd, np.ones((len(hp), 1)), mp["pcode"].to_numpy(), mp["day"].to_numpy())[:, 0]
    stats = {"player_rows": int(len(p)), "players": int(p["player"].nunique()),
             "linked_rows": int(p["player_id"].notna().sum()), "unlinked_rows": int(p["player_id"].isna().sum()),
             "unlinked_blank_name": int((p["player"].fillna("").str.strip() == "").sum()),
             "unlinked_examples": p.loc[p["player_id"].isna(), "player"].value_counts().head(12).to_dict(),
             "no_event_date": int(p["day"].isna().sum()),
             "linked_players": int(linked["player_id"].nunique()),
             "by_tour": {t: {"rows": int((p["tour"] == t).sum()), "linked": int(((p["tour"] == t) & p["player_id"].notna()).sum())}
                         for t in C.TOURS}}
    return count > 0, stats


# ------------------------------------------------------------------------------------------------
# Aggregation

def cells(em: pd.DataFrame, present: np.ndarray) -> pd.DataFrame:
    g = em.assign(present=present.astype("int64"), matches=1).groupby(["tour", "group", "year"])[["matches", "present"]].sum()
    return g.reset_index()


def pooled(tab: pd.DataFrame, first_year: dict | None = None) -> dict:
    """Shares by tour (over the scored years), by level group, the lowest group and the lowest year."""
    out = {}
    for tour in C.TOURS:
        t = tab[tab["tour"].eq(tour)]
        fy = (first_year or {}).get(tour, C.EVAL_YEARS[0])
        t = t[t["year"] >= fy]
        if t["matches"].sum() == 0:
            continue
        by_g = t.groupby("group")[["matches", "present"]].sum()
        by_y = t.groupby("year")[["matches", "present"]].sum()
        share_g = (by_g["present"] / by_g["matches"]).reindex([g for g in LEVEL_GROUPS if g in by_g.index])
        share_y = by_y["present"] / by_y["matches"]
        main = t[t["group"].isin(MAIN_TOUR)]
        head = t[t["year"] >= C.HEADLINE_YEARS[0]]
        out[tour] = {"from": int(fy), "matches": int(t["matches"].sum()), "present": int(t["present"].sum()),
                     "share": float(t["present"].sum() / t["matches"].sum()),
                     "share_main_tour": float(main["present"].sum() / main["matches"].sum()) if len(main) else None,
                     "share_2022_2026": float(head["present"].sum() / head["matches"].sum()) if head["matches"].sum() else None,
                     "by_group": {g: round(float(v), 4) for g, v in share_g.items()},
                     "lowest_group": [str(share_g.idxmin()), float(share_g.min())],
                     "lowest_year": [int(share_y.idxmin()), float(share_y.min())],
                     "by_year": {int(y): round(float(v), 4) for y, v in share_y.items()}}
    return out


def comparisons(cand: pd.DataFrame) -> dict:
    """How many (candidate x form x tour x score) comparisons the plan makes, and what rides on them."""
    rows = []
    for _, c in cand.iterrows():
        forms = c["forms"].split(";")
        for tour in c["tours"].split(";"):
            for form in forms:
                for score in c["scores"].split(";"):
                    rows.append({"id": c["id"], "group": c["group"], "form": form, "tour": tour, "score": score})
    r = pd.DataFrame(rows)
    per = r.groupby(["tour", "score"]).size()
    rows_per_tour = r.drop_duplicates(["id", "form", "tour"]).groupby("tour").size()
    n = int(len(r))
    return {"candidates": int(len(cand)), "by_group": cand["group"].value_counts().to_dict(),
            "rows_per_tour": {t: int(v) for t, v in rows_per_tour.items()},
            "comparisons": n, "by_tour_score": {f"{t}|{s}": int(v) for (t, s), v in per.items()},
            "shuffled_copies": COPIES, "null_fits": n * COPIES,
            "expected_chance_clearings": n / (COPIES + 1),
            "direction_looks_given_elo": int(rows_per_tour.sum() * (len(ERAS) + len(LEVEL_GROUPS)))}


# ------------------------------------------------------------------------------------------------

def main() -> int:
    mp = load()
    log(f"player-matches: {len(mp):,}")
    shr = pd.read_csv(SHRINKAGE)
    rows, prev, info = key_rows(mp, shr)
    rows["pbp"], pbp_stats = pbp_rows(mp)
    log("per-row coverage done")

    em = mp.iloc[0::2][["match_id", "tour", "year", "group", "evaluation", "level", "qualifying", "best_of", "format",
                        "minutes"]].reset_index(drop=True)
    ev = em["evaluation"].to_numpy(dtype=bool)
    em = em[ev].reset_index(drop=True)
    odds = pd.read_parquet(ODDS, columns=["match_id", "link", "p_avg_a"]).set_index("match_id")
    o = odds.reindex(em["match_id"])
    match_keys = {k: both(v)[ev] for k, v in rows.items()}
    match_keys["odds"] = o["p_avg_a"].notna().to_numpy()
    match_keys["td_location"] = o["link"].notna().to_numpy() & o["link"].ne("none").to_numpy()
    match_keys["all"] = np.ones(len(em), dtype=bool)

    cand = pd.read_csv(CANDIDATES)
    # matchups: every statistic of the matchup defined for both players, per window
    for _, c in cand[cand["coverage"].eq("match")].iterrows():
        for w in ("career", "52w", "surface"):
            match_keys[f"match:{c['id']}:{w}"] = np.all([match_keys[f"hist:{s}:{w}"] for s in c["stats"].split(";")], axis=0)

    tabs = []
    for k, v in match_keys.items():
        tabs.append(cells(em, v).assign(key=k))
    cov = pd.concat(tabs, ignore_index=True)[["key", "tour", "group", "year", "matches", "present"]]
    cov.to_csv(COVERAGE, index=False)
    log(f"wrote {COVERAGE.name}: {len(cov):,} rows")

    # pooled coverage of every candidate x form, over its scored years
    single_key = {"rank": "all", "always": "all", "ratings": "all", "home": "country_player", "entry": "entry_recorded",
                  "pbp": "pbp", "hand": "hand"}
    per_row = []
    for _, c in cand.iterrows():
        first = {"atp": C.EVAL_YEARS[0], "wta": C.WTA_BOX_FROM if c["wta_box_from_2019"] == "yes" else C.EVAL_YEARS[0]}
        for form in c["forms"].split(";"):
            w = FORM_WINDOW[form]
            if c["coverage"] == "hist":
                key = f"hist:{c['stats']}:{w}"
            elif c["coverage"] == "h2h":
                key = f"h2h:{w}"
            elif c["coverage"] == "match":
                key = f"match:{c['id']}:{w}"
            else:
                key = single_key.get(c["coverage"], c["coverage"])
            tab = cov[cov["key"].eq(key) & cov["tour"].isin(c["tours"].split(";"))]
            per_row.append({"id": c["id"], "form": form, "key": key, "coverage": pooled(tab, first)})
    keys_out = {}
    info_keys = ["rank_known", "points_known", "ratings_any", "ratings_established", "country_player", "odds",
                 "td_location", "entry_recorded"] + [f"hist:{s}:halfK" for s in C.RATES]
    for k in info_keys:
        box = (k.startswith("hist:") and k.split(":")[1] not in SCORE_STATS) or k.startswith("ratings_")
        first = {"atp": C.EVAL_YEARS[0], "wta": C.WTA_BOX_FROM if box else C.EVAL_YEARS[0]}
        keys_out[k] = pooled(cov[cov["key"].eq(k)], first)
    # a qualifier or lucky loser exists only in a main draw: their coverage among main-draw matches
    for k in ENTRY_TYPES:
        t = cov[cov["key"].eq(f"entry_{k}") & cov["group"].isin(["GS", "T1000", "T500", "T250", "CH"])]
        keys_out[f"entry_{k}_main_draws"] = pooled(t)

    # prevalences: share of evaluation matches where the feature is non-zero for at least one player
    preval = {}
    for k, v in prev.items():
        anyp = np.asarray(v, dtype=bool).reshape(-1, 2).any(axis=1)[ev]
        preval[k] = pooled(cells(em, anyp))
    for k in ENTRY_TYPES:
        rec = match_keys[f"entry_{k}"]
        anyp = np.asarray(prev[f"entry_{k}"], dtype=bool).reshape(-1, 2).any(axis=1)[ev]
        preval[f"entry_{k}_where_recorded"] = pooled(cells(em[rec], anyp[rec]))
    # best of five as Stage 2 reads it, from the score: the larger of the two players' sets won is 3 (a retirement
    # keeps the recorded format); the Next Gen Finals' short sets are best of five
    sets = mp["sets_won_n"].to_numpy(dtype="float64").reshape(-1, 2)
    w = np.where(np.isnan(sets).all(axis=1), np.nan, np.fmax(sets[:, 0], sets[:, 1]))[ev]
    with np.errstate(invalid="ignore"):
        bo5 = (w >= 3) | em["best_of"].eq(5).to_numpy() | em["format"].eq("short_sets").to_numpy()
    preval["best_of_five"] = pooled(cells(em, bo5))
    h2h_any = both(info["h2h_meetings"] > 0)[ev]
    preval["h2h_met_before"] = pooled(cells(em, h2h_any))

    # entry-recording gaps: cells (tour x group x year) where a type is never recorded (its code never appears in
    # the cell's events that record entries); the Finals have no qualifiers and no wild cards
    gaps = {}
    for k in ENTRY_TYPES:
        groups = ["GS", "T1000", "T500", "T250", "CH"] if k in ("q", "ll") else [g for g in LEVEL_GROUPS if g != "FIN"]
        t = cov[cov["key"].eq(f"entry_{k}") & cov["group"].isin(groups)]
        gaps[k] = [f"{a}|{b}|{c}" for a, b, c, v in t[["tour", "group", "year", "present"]].itertuples(index=False) if v == 0]
    erow = np.asarray(rows["entry_recorded"], dtype=bool)
    unrec = mp[["tour", "group", "year", "evaluation"]].assign(rec=erow)
    unrec = unrec[unrec["evaluation"].astype(bool)]
    unrec_cells = unrec.groupby(["tour", "group", "year"])["rec"].mean()
    entry_unrecorded = {f"{a}|{b}|{c}": round(1 - float(v), 3) for (a, b, c), v in unrec_cells.items() if v < 0.5}

    # the tournament's country: sources on disk
    evm = mp.iloc[0::2][ev]
    names = evm.assign(key=evm["tournament_name"].map(lambda s: re.sub(r"\d+", "", norm_name(s)).strip()))
    distinct = {t: {"event_names": int(names[names["tour"].eq(t)]["key"].nunique()),
                    "by_group": names[names["tour"].eq(t)].groupby("group")["key"].nunique().to_dict()} for t in C.TOURS}
    wta_ed = pd.read_parquet(WTA_EDITIONS, columns=["year", "level", "country"])
    otd = pd.read_parquet(OTD_TOURNAMENTS, columns=["tour", "year", "country"])
    country_sources = {"distinct_event_names_2013_2026": distinct,
                       "tennis_data_location": keys_out["td_location"],
                       "wta_api_editions": {"rows": int(len(wta_ed)), "years": sorted(int(y) for y in wta_ed["year"].unique()),
                                            "by_level": wta_ed["level"].value_counts().to_dict(),
                                            "country_blank": int(wta_ed["country"].isna().sum())},
                       "open_tennis_data_tournaments": {"rows": int(len(otd)), "with_country": int(otd["country"].notna().sum()),
                                                        "years": [int(otd["year"].min()), int(otd["year"].max())]}}

    # source checks quoted in the plan: ages outside the range read as missing; match minutes by tour, level and year
    evr = mp["evaluation"].to_numpy(dtype=bool)
    age = mp["age"].to_numpy(dtype="float64")
    out_of_range = evr & ~np.isnan(age) & ((age < AGE_RANGE[0]) | (age > AGE_RANGE[1]))
    checks = {"age_out_of_range_evaluation_player_rows": int(out_of_range.sum()),
              "age_max_evaluation": float(np.nanmax(age[evr])),
              "minutes_known_evaluation": {f"{t}|{g}|{y}": round(float(v), 4) for (t, g, y), v in
                                           em.assign(k=em["minutes"].notna()).groupby(["tour", "group", "year"])["k"].mean().items()}}

    # days since the last match among evaluation rows (tournament weeks)
    gap = info["days_since"].reshape(-1, 2)[ev].reshape(-1)
    gap = gap[gap >= 0]
    days = {"player_rows": int(len(gap)), "same_event": float(np.mean(gap == 0)), "one_week": float(np.mean(gap == 7)),
            "over_8_weeks": float(np.mean(gap > 56)), "median_days": float(np.median(gap))}

    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "settings": {"week52_days": WEEK52, "windows_days": list(WINDOWS), "elo_change_days": ELO_CHANGE,
                            "surface_first_below": SURFACE_FIRST, "age_range": list(AGE_RANGE),
                            "established_serve_points": ESTABLISHED, "copies": COPIES,
                            "wta_box_from": C.WTA_BOX_FROM, "eval_years": [C.EVAL_YEARS[0], C.EVAL_YEARS[-1]]},
               "evaluation_matches": {t: int(em["tour"].eq(t).sum()) for t in C.TOURS},
               "evaluation_matches_with_odds": {t: int((em["tour"].eq(t) & match_keys["odds"]).sum()) for t in C.TOURS},
               "candidates": records(cand), "rows": per_row, "keys": keys_out, "prevalence": preval,
               "entry_gaps": gaps, "entry_unrecorded_cells": entry_unrecorded, "pbp_link": pbp_stats,
               "country_sources": country_sources, "days_since_last_match": days, "source_checks": checks,
               "comparisons": comparisons(cand), "seconds": round(time.time() - T0, 1)}
    SUMMARY.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    log(f"wrote {SUMMARY.name}")
    return 0


def records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records"))


if __name__ == "__main__":
    sys.exit(main())
