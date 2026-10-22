"""SofaScore's box scores and a recount from its own point records, on Stage 0's ids (readers tp_sofascore_box and
tp_sofascore_recount of the source-reconciliation study; brief: docs/studies/source_reconciliation/subagent_briefs.md).

Inputs (read-only): the three staged collections data/dump/points/{sofascore, sofascore_editions,
sofascore_tournaments}/ (events.parquet, statistics.parquet, points.parquet) and the study's frozen link file
_snapshot/links/sofascore.parquet (source_key "sofascore:<event_id>" -> Stage 0 match_id).

An event in two collections is read from the first that holds its statistics (box) or its points (recount), in the
order sofascore, sofascore_editions, sofascore_tournaments (data_continuity/sources.sofascore keeps the first
collection that lists the event, which can drop statistics fetched by a later collection).

Box (period ALL; the mapping of data_continuity/sources.py sofascore()):
    ace aces · df doubleFaults · first_in / svpt firstServeAccuracy "in/attempts" · first_won
    firstServePointsAccuracy numerator · second_won secondServePointsAccuracy numerator · sv_gms serviceGamesTotal ·
    bp_saved / bp_faced breakPointsSaved "saved/faced" · sv_won servicePointsScored.
    Kept beside them: the first-serve-points denominator (x_first_den, should equal first_in), the second-serve-points
    denominator (x_second_den, should equal svpt - first_in) and secondServeAccuracy "in/attempts" (x_second_in,
    x_second_att): SofaScore's own consistency.
    Two readers with the same mapping: tp_sofascore_box reads the match totals SofaScore publishes (period ALL);
    tp_sofascore_setbox sums its per-set periods (1ST..5TH; a count only where every set period has it). They
    differ: from late 2024 the ALL period is often not the sum of the set periods (observed 16 Oct 2026: aces,
    double faults, serve points, points won and break points in Dec 2024 - Aug 2025; break points in Feb - Jun
    2026; first serves in throughout, ALL higher), while the set periods equal the point recount.
    x_all_equals_setsum (ALL box): the player's ALL totals equal the set sums on every count both have (NaN where the
    event has no set periods).

Recount, from the point records (what the records say, observed 16 Oct 2026 on all three collections):
    * Each game lists the score AFTER each point (home_point, away_point: 0 15 30 40 A; tiebreak points as numbers).
      A non-tiebreak game's last point is NOT listed: the game ends one point after the last listed score, won by the
      game's winner (``scoring``). Tiebreak listings include their last point.
    * ``serving`` is the server of a non-tiebreak game (the point described as an ace is won by that side in 11,693 of
      11,734 listed points). In a tiebreak game ``serving`` is not the first server (an ace is won by the side the field
      implies in 55% of tiebreak points only); the normal rotation is: the tiebreak's first server is the opponent of
      the previous game's server (or of the previous tiebreak's first server), then two points each (aces won by that
      side in 6,463 of 6,479 tiebreak points, double faults lost by it in 3,755 of 3,757).
    * point_description 1 = ace, 2 = double fault, 0 = other. home/away_point_type codes describe break-point states
      (2 = the returner holds a break point after the point) and are not used.
    * No serve number: first_in, first_won, second_won cannot be recounted (NaN).
    * Aces and double faults: the last point of each non-tiebreak game is not listed, so its type is unknown. The
      recount gives the listed points' aces and double faults (x_ace_listed, x_df_listed) and the bounds the unlisted
      points allow (x_ace_max = listed + games held: an ace can only win the server the game; x_df_max = listed + games
      lost on serve); ``ace`` and ``df`` are NaN.
    * svpt (every point served, the unlisted last points included), sv_won, sv_gms (completed non-tiebreak games
      served), bp_faced (points of the player's non-tiebreak service games at which the returner would win the game by
      winning the point; the state before a game's last point is its last listed score) and bp_saved; the set scores.
    * complete: every game's listing is a valid point-by-point progression (one point at a time, a last point that can
      end the game), the set scores from the games equal the event's own, and they equal Stage 0's score.

Orientation: SofaScore's home and away names graded against Stage 0's A and B names (tp_common.orient); never by
who won. x_src_won is the event's winner_code oriented by names (box) or the recount's winner by finished sets
(recount; only where SofaScore marks the match "Ended": a retirement's winner can trail in sets).
Extra recount columns: x_bp_at_adv (break points faced at the returner's advantage), x_bp_games (service games with
a break point), x_games_broken, x_tb_points_served, x_unlisted_last_points (non-tiebreak games' last points).

Writes box/readers/tp_sofascore_box.{parquet,json}, tp_sofascore_setbox.{parquet,json},
tp_sofascore_recount.{parquet,json} and tp_sofascore_games.parquet (one row per recounted game, for re-checking).
Run: ./python.sh src/eda/source_reconciliation/tp_sofascore.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import tp_common as T  # noqa: E402

COLLECTIONS = ("sofascore", "sofascore_editions", "sofascore_tournaments")
DUMP = C.DUMP / "points"
FAMILY = "sofascore"
KEYS = {("Service", "aces"): "ace", ("Service", "doubleFaults"): "df",
        ("Service", "firstServeAccuracy"): "first_serve", ("Service", "secondServeAccuracy"): "second_serve",
        ("Service", "firstServePointsAccuracy"): "first_pts", ("Service", "secondServePointsAccuracy"): "second_pts",
        ("Service", "serviceGamesTotal"): "sv_gms", ("Service", "breakPointsSaved"): "bp",
        ("Points", "servicePointsScored"): "sv_won"}
RATIO = re.compile(r"^\s*(-?\d+)\s*/\s*(-?\d+)")
GAME_VAL = {"0": 0, "15": 1, "30": 2, "40": 3, "A": 4, "AD": 4}
EV_COLS = ["event_id", "start_timestamp", "category_name", "tournament_name", "season_year", "round_name",
           "status_description", "winner_code", "first_to_serve", "doubles", "home_id", "home_name", "away_id",
           "away_name"] + [f"{s}_set{k}" for k in range(1, 6) for s in ("home", "away")]


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.strip().replace("", pd.NA), errors="coerce").astype("float64")


def ratio(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    parts = s.astype("string").str.extract(RATIO)
    return num(parts[0]), num(parts[1])


# ------------------------------------------------------------------------------------------------ inputs
def load_events() -> pd.DataFrame:
    frames = []
    for c in COLLECTIONS:
        path = DUMP / c / "events.parquet"
        have = set(pq.read_schema(path).names)
        t = pq.read_table(path, columns=[x for x in EV_COLS if x in have]).to_pandas()
        frames.append(t.assign(collection=c))
    ev = pd.concat(frames, ignore_index=True)
    ev["event_id"] = ev["event_id"].astype(str)
    lists = ev.groupby("event_id")["collection"].agg(lambda s: ";".join(s))
    ev = ev.drop_duplicates("event_id").copy()
    ev["listed_in"] = ev["event_id"].map(lists)
    return ev.set_index("event_id")


SET_PERIODS = ["1ST", "2ND", "3RD", "4TH", "5TH"]
# (field, numerator column, denominator column) of each statistic; a plain number has no denominator
PARSED = {"ace": ("ace", None), "df": ("df", None), "sv_gms": ("sv_gms", None), "sv_won": ("sv_won", None),
          "first_serve": ("first_in", "svpt"), "first_pts": ("first_won", "x_first_den"),
          "second_pts": ("second_won", "x_second_den"), "second_serve": ("x_second_in", "x_second_att"),
          "bp": ("bp_saved", "bp_faced")}


def _wide(st: pd.DataFrame) -> pd.DataFrame:
    """Statistics rows of one period (event_id, field, home, away) -> one row per event: home_<col>, away_<col>."""
    out = pd.DataFrame(index=pd.Index(sorted(st["event_id"].unique()), name="event_id"))
    for f, (a, b) in PARSED.items():
        x = st[st["field"].eq(f)].drop_duplicates("event_id").set_index("event_id")
        for side in ("home", "away"):
            v = x[side].reindex(out.index)
            if b is None:
                out[f"{side}_{a}"] = num(v)
            else:
                out[f"{side}_{a}"], out[f"{side}_{b}"] = ratio(v)
    return out


def load_box() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """The statistics of every event, one collection per event (the first with a period ALL), as two wide tables
    (home_<f>, away_<f>): the match totals SofaScore publishes (period ALL), and the sum of its per-set periods
    (1ST..5TH; x_set_periods counts them; a count is summed only where every set period has it)."""
    seen: set[str] = set()
    alls, sums, stats = [], [], {}
    for c in COLLECTIONS:
        st = pq.read_table(DUMP / c / "statistics.parquet",
                           columns=["event_id", "period", "group", "key", "home", "away"]).to_pandas()
        st["event_id"] = st["event_id"].astype(str)
        ids = set(st.loc[st["period"].eq("ALL"), "event_id"]) - seen
        stats[c] = {"events_with_period_all": int(st.loc[st["period"].eq("ALL"), "event_id"].nunique()),
                    "taken_from_here": len(ids)}
        seen |= ids
        st = st[st["event_id"].isin(ids)]
        st = st[[(g, k) in KEYS for g, k in zip(st["group"], st["key"])]]
        st = st.assign(field=[KEYS[(g, k)] for g, k in zip(st["group"], st["key"])])
        alls.append(_wide(st[st["period"].eq("ALL")]).assign(box_collection=c))
        per = [_wide(st[st["period"].eq(p)]).assign(period=p) for p in SET_PERIODS if st["period"].eq(p).any()]
        if per:
            P = pd.concat(per).reset_index()
            num_cols = [x for x in P.columns if x not in ("event_id", "period")]
            g = P.groupby("event_id")
            S = g[num_cols].sum(min_count=1)
            full = g[num_cols].count().eq(g["period"].count(), axis=0)     # every set period has the count
            S = S.where(full)
            S["x_set_periods"] = g["period"].count()
            sums.append(S.assign(box_collection=c))
    return pd.concat(alls), pd.concat(sums), stats


def load_points() -> tuple[pd.DataFrame, dict]:
    seen: set[str] = set()
    frames, stats = [], {}
    cols = ["event_id", "set", "game", "point", "home_point", "away_point", "point_description", "serving", "scoring",
            "tiebreak", "game_home_score", "game_away_score"]
    for c in COLLECTIONS:
        pt = pq.read_table(DUMP / c / "points.parquet", columns=cols).to_pandas()
        pt["event_id"] = pt["event_id"].astype(str)
        ids = set(pt["event_id"]) - seen
        stats[c] = {"events_with_points": int(pt["event_id"].nunique()), "taken_from_here": len(ids),
                    "point_rows": int(len(pt))}
        seen |= ids
        frames.append(pt[pt["event_id"].isin(ids)].assign(collection=c))
    pt = pd.concat(frames, ignore_index=True)
    for c in ("set", "game", "point", "game_home_score", "game_away_score"):
        pt[c] = pd.to_numeric(pt[c], errors="coerce")
    return pt, stats


# ------------------------------------------------------------------------------------------------ the recount
def _val(text, tb: bool):
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return None
    s = str(text).strip()
    if tb:
        try:
            return int(s)
        except ValueError:
            return None
    return GAME_VAL.get(s.upper())


def _bp(s: int, r: int) -> bool:
    """A break point before the point: the returner wins the game by winning it (non-tiebreak; s, r on 0..4)."""
    return (r == 3 and s < 3) or r == 4


def _step_ok(prev: tuple[int, int], new: tuple[int, int]) -> tuple[bool, int]:
    """Is ``new`` (home, away after the point; 0..3 = 0/15/30/40, 4 = advantage) one listed point after ``prev``?
    Returns (ok, winner: 0 home, 1 away, -1 unknown). A point that ends the game is never listed."""
    h, a = prev
    nh, na = new
    if h == 4:                       # home advantage: home wins -> game (not listed); away wins -> deuce
        return (nh, na) == (3, 3), 1
    if a == 4:
        return (nh, na) == (3, 3), 0
    if (h, a) == (3, 3):
        if (nh, na) == (4, 3):
            return True, 0
        if (nh, na) == (3, 4):
            return True, 1
        return False, -1
    if (nh, na) == (h + 1, a):
        return h < 3, 0              # from 40 (the other below 40) the next point won would end the game
    if (nh, na) == (h, a + 1):
        return a < 3, 1
    return False, -1


def _final_ok(prev: tuple[int, int], winner: int) -> bool:
    h, a = prev
    if winner == 0:
        return (h == 3 and a < 3) or h == 4
    return (a == 3 and h < 3) or a == 4


def recount_event(g: pd.DataFrame) -> tuple[dict, list]:
    """One event's points (sorted) -> per side (0 home, 1 away) counts, the games, and the checks."""
    cnt = {k: [0, 0] for k in ("svpt", "sv_won", "sv_gms", "bp_faced", "bp_saved", "ace_listed", "df_listed",
                              "holds", "breaks", "tb_pts", "finals", "bp_at_adv", "bp_games", "bp_first_in_game")}
    ok_all, games_out = True, []
    sets: dict[int, list[int]] = {}
    prev_first = None                      # the previous game's (first) server: 0 home, 1 away
    unfinished = 0
    ss, gg = g["set"].to_numpy(), g["game"].to_numpy()
    keys = list(dict.fromkeys(zip(ss, gg)))
    idx = {k: [] for k in keys}
    for i, k in enumerate(zip(ss, gg)):
        idx[k].append(i)
    hp, ap = g["home_point"].to_numpy(), g["away_point"].to_numpy()
    desc, serving = g["point_description"].astype(str).to_numpy(), g["serving"].astype(str).to_numpy()
    scoring, tbf = g["scoring"].astype(str).to_numpy(), g["tiebreak"].astype(str).str.upper().to_numpy()
    last_set, last_game = None, 0
    for (s, gm) in keys:
        rows = idx[(s, gm)]
        tb = bool((tbf[rows] == "TRUE").any())
        sc = scoring[rows[-1]]
        winner = 0 if sc == "1" else 1 if sc == "2" else None
        game_ok = True
        if s != last_set:
            game_ok &= (gm == 1)
            last_set, last_game = s, gm
        else:
            game_ok &= (gm == last_game + 1)
            last_game = gm
        if not tb:
            sv = 0 if serving[rows[0]] == "1" else 1 if serving[rows[0]] == "2" else None
            if sv is None or len(set(serving[rows])) != 1:
                game_ok = False
                sv = sv if sv is not None else 0
            state = (0, 0)
            game_bp = 0
            for i in rows:
                new = (_val(hp[i], False), _val(ap[i], False))
                if new[0] is None or new[1] is None:
                    game_ok = False
                    break
                s_before, r_before = (state[0], state[1]) if sv == 0 else (state[1], state[0])
                ok, w = _step_ok(state, new)
                game_ok &= ok
                cnt["svpt"][sv] += 1
                if _bp(s_before, r_before):
                    cnt["bp_faced"][sv] += 1
                    game_bp += 1
                    cnt["bp_at_adv"][sv] += int(r_before == 4)
                    if w == sv:
                        cnt["bp_saved"][sv] += 1
                if w == sv:
                    cnt["sv_won"][sv] += 1
                if desc[i] == "1":
                    cnt["ace_listed"][sv] += 1
                    game_ok &= (w == sv)
                elif desc[i] == "2":
                    cnt["df_listed"][sv] += 1
                    game_ok &= (w == 1 - sv)
                state = new
            if winner is None:
                unfinished += 1
            else:
                game_ok &= _final_ok(state, winner)
                s_before, r_before = (state[0], state[1]) if sv == 0 else (state[1], state[0])
                cnt["svpt"][sv] += 1
                cnt["finals"][sv] += 1
                if _bp(s_before, r_before):
                    cnt["bp_faced"][sv] += 1          # a last point at break point is lost on serve (the game ends)
                    game_bp += 1
                    cnt["bp_at_adv"][sv] += int(r_before == 4)
                    if winner == sv:
                        game_ok = False               # a server cannot win the game from a break point in one point
                cnt["bp_games"][sv] += int(game_bp > 0)
                if winner == sv:
                    cnt["sv_won"][sv] += 1
                    cnt["holds"][sv] += 1
                else:
                    cnt["breaks"][sv] += 1
                cnt["sv_gms"][sv] += 1
            first = sv
        else:
            first = None if prev_first is None else 1 - prev_first
            if first is None:                          # a tiebreak with no game before it: the field is all we have
                first = 0 if serving[rows[0]] == "1" else 1
                game_ok = False
            st = (0, 0)
            for i in rows:
                new = (_val(hp[i], True), _val(ap[i], True))
                if new[0] is None or new[1] is None:
                    game_ok = False
                    break
                k = st[0] + st[1] + 1                  # the point's number in the tiebreak
                srv = first if (k == 1 or ((k - 2) // 2) % 2 == 1) else 1 - first
                if new == (st[0] + 1, st[1]):
                    w = 0
                elif new == (st[0], st[1] + 1):
                    w = 1
                else:
                    game_ok, w = False, -1
                cnt["svpt"][srv] += 1
                cnt["tb_pts"][srv] += 1
                if w == srv:
                    cnt["sv_won"][srv] += 1
                if desc[i] == "1":
                    cnt["ace_listed"][srv] += 1
                    game_ok &= (w == srv)
                elif desc[i] == "2":
                    cnt["df_listed"][srv] += 1
                    game_ok &= (w == 1 - srv)
                st = new
            if winner is None:
                unfinished += 1
            else:
                hi, lo = max(st), min(st)
                game_ok &= hi >= 7 and hi - lo >= 2 and (0 if st[0] > st[1] else 1) == winner
            sv = first
        if winner is not None:
            sets.setdefault(int(s), [0, 0])[winner] += 1
        else:
            sets.setdefault(int(s), [0, 0])
        prev_first = first
        ok_all &= game_ok
        games_out.append((int(s), int(gm), tb, sv, winner, len(rows), game_ok))
    return {"cnt": cnt, "ok": ok_all, "sets": sets, "unfinished": unfinished}, games_out


def recount_all(pt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pt = pt.sort_values(["event_id", "set", "game", "point"], kind="mergesort").reset_index(drop=True)
    starts = np.flatnonzero(np.r_[True, pt["event_id"].to_numpy()[1:] != pt["event_id"].to_numpy()[:-1]])
    ends = np.r_[starts[1:], len(pt)]
    rows, games = [], []
    t0 = time.time()
    for n, (a, b) in enumerate(zip(starts, ends)):
        g = pt.iloc[a:b]
        eid = g["event_id"].iat[0]
        res, gl = recount_event(g)
        r = {"event_id": eid, "collection": g["collection"].iat[0], "listing_ok": res["ok"],
             "unfinished_games": res["unfinished"],
             "sets": tuple(tuple(res["sets"][k]) for k in sorted(res["sets"]))}
        for k, v in res["cnt"].items():
            r[f"home_{k}"], r[f"away_{k}"] = v[0], v[1]
        rows.append(r)
        games.extend((eid,) + x for x in gl)
        if n % 10000 == 0:
            T.log(f"  recount: {n:,} events ({time.time() - t0:.0f}s)")
    R = pd.DataFrame(rows).set_index("event_id").rename(columns={"collection": "pts_collection"})
    G = pd.DataFrame(games, columns=["event_id", "set", "game", "tiebreak", "server", "winner", "listed_points",
                                     "game_ok"])
    return R, G


# ------------------------------------------------------------------------------------------------ assembly
def event_sets(ev: pd.DataFrame) -> pd.Series:
    out = []
    for _, r in ev.iterrows():
        sets = []
        for k in range(1, 6):
            a, b = r.get(f"home_set{k}"), r.get(f"away_set{k}")
            try:
                a, b = int(float(a)), int(float(b))
            except (TypeError, ValueError):
                break
            sets.append((a, b))
        out.append(tuple(sets))
    return pd.Series(out, index=ev.index)


BOX_EXTRA = ["x_first_den", "x_second_den", "x_second_in", "x_second_att", "x_all_equals_setsum", "x_src_won",
             "x_src_side"]


def build_box(L: pd.DataFrame, box: pd.DataFrame, reader: str, what: str, common: dict) -> pd.DataFrame:
    """One box reader on the contract from a wide statistics table (load_box), linked and oriented through L."""
    B = L.join(box, how="inner")
    w = pd.DataFrame({"source_key": "sofascore:" + B.index.astype(str), "match_id": B["match_id"].to_numpy(),
                      "a1": B["a1"].to_numpy()})
    for side, k in (("home", "p1"), ("away", "p2")):
        for f in C.FIELDS + ["x_first_den", "x_second_den", "x_second_in", "x_second_att", "x_all_equals_setsum"]:
            w[f"{k}_{f}"] = B[f"{side}_{f}"].to_numpy() if f"{side}_{f}" in B else np.nan
        wc = B["winner_code"].astype(str)
        w[f"{k}_x_src_won"] = np.where(wc.isin(["1", "2"]), wc.eq("1" if side == "home" else "2"), np.nan)
        w[f"{k}_x_src_side"] = side
    w["complete"] = B["status_description"].isin(["Ended", "Retired"]).to_numpy() &         B[["home_svpt", "away_svpt"]].notna().all(axis=1).to_numpy()
    w["link_method"] = B["link_method"].to_numpy()
    w["x_collection"] = B["box_collection"].to_numpy()
    w["x_status"] = B["status_description"].to_numpy()
    w["x_score_agrees"] = B["score_agrees"].astype("boolean").to_numpy()
    w["x_season"] = B["season"].to_numpy()
    w["x_set_periods"] = B["x_set_periods"].to_numpy() if "x_set_periods" in B else np.nan
    w["x_name_grade_same"], w["x_name_grade_swap"] = B["g_same"].to_numpy(), B["g_swap"].to_numpy()
    rows = T.to_contract(w, reader, FAMILY, "box", player_extra=BOX_EXTRA,
                         match_extra=["x_collection", "x_status", "x_score_agrees", "x_season", "x_set_periods",
                                      "x_name_grade_same", "x_name_grade_swap"])
    rows["x_src_won"] = rows["x_src_won"].astype("boolean")
    rows["x_all_equals_setsum"] = rows["x_all_equals_setsum"].astype("boolean")
    # SofaScore's own consistency
    cons = pd.DataFrame({
        "first_den_equals_first_in": (rows["x_first_den"] == rows["first_in"]),
        "second_den_equals_svpt_minus_first_in": (rows["x_second_den"] == rows["svpt"] - rows["first_in"]),
        "second_att_equals_svpt_minus_first_in": (rows["x_second_att"] == rows["svpt"] - rows["first_in"]),
        "df_equals_second_att_minus_second_in": (rows["df"] == rows["x_second_att"] - rows["x_second_in"]),
        "sv_won_equals_first_won_plus_second_won": (rows["sv_won"] == rows["first_won"] + rows["second_won"]),
    })
    have = rows[["svpt", "first_in", "x_first_den", "x_second_den"]].notna().all(axis=1)
    rows["x_self_consistent"] = cons.all(axis=1) & have
    summary = {
        **common, "what": what,
        "linked": {"events_with_box_linked_to_stage0": int(len(B)),
                   "by_link_method": T.tidy_counts(B["link_method"].value_counts())},
        "dropped": {"box_events_not_in_link_file": int(len(box) - len(B)),
                    "orientation_unresolved": int(B["a1"].isna().sum())},
        "contract_checks": T.check_contract(rows),
        "complete_rows": int(rows["complete"].sum()),
        "self_consistency_share": {k: round(float(v[have].mean()), 5) for k, v in cons.items()},
        "winner_vs_stage0": T.winner_check(rows),
        "score_agrees_link_file": T.tidy_counts(B["score_agrees"].astype(str).value_counts()),
        "definitions": __doc__.split("Box (period ALL")[1].split("Recount, from")[0].strip(),
    }
    summary["sanity_vs_stage0_by_tour"] = T.records(T.sanity(rows, by=["tour"]))
    summary["hand_check"] = {"keys": T.sample_keys(rows), "status": "pending"}
    T.write_reader(rows, reader, summary)
    return rows


def main() -> int:
    t0 = time.time()
    inputs = [DUMP / c / f for c in COLLECTIONS for f in ("events.parquet", "statistics.parquet", "points.parquet")]
    rec = T.receipts(inputs)
    T.log("events")
    ev = load_events()
    links = C.links("sofascore")
    links["event_id"] = links["source_key"].str.replace("sofascore:", "", regex=False)
    S = T.s0_frame().set_index("match_id")
    in_s0 = links["match_id"].isin(S.index)
    link_not_in_s0 = int((~in_s0).sum())
    lk = links[in_s0].set_index("event_id")
    # orientation by names, for every linked event
    L = ev.loc[ev.index.intersection(lk.index)].copy()
    L["match_id"] = lk.loc[L.index, "match_id"]
    L["link_method"] = lk.loc[L.index, "link_method"].str.split(";").str[0]
    L["score_agrees"] = lk.loc[L.index, "score_agrees"]
    na, nb = S.loc[L["match_id"], "name_a"].to_numpy(), S.loc[L["match_id"], "name_b"].to_numpy()
    o = [T.orient(h, a, x, y) for h, a, x, y in zip(L["home_name"], L["away_name"], na, nb)]
    L["a1"] = [x[0] for x in o]
    L["g_same"], L["g_swap"] = [x[1] for x in o], [x[2] for x in o]
    L["a_won"] = S.loc[L["match_id"], "a_won"].to_numpy()
    L["s0_sets"] = S.loc[L["match_id"], "sets_w"].to_numpy()
    L["ev_sets"] = event_sets(L)
    L["season"] = pd.to_datetime(pd.to_numeric(L["start_timestamp"], errors="coerce"), unit="s").dt.year
    orient_counts = {"link_rows_whose_match_is_not_in_the_snapshot": link_not_in_s0,
                     "linked_events": int(len(L)), "oriented": int(L["a1"].notna().sum()),
                     "orientation_unresolved": int(L["a1"].isna().sum()),
                     "unresolved_examples": T.records(L.loc[L["a1"].isna(), ["home_name", "away_name", "match_id"]]
                                                      .head(8).reset_index())}

    # ---------------------------------------------------------------- boxes
    T.log("box")
    box_all, box_sets, box_stats = load_box()
    # per side: do SofaScore's match totals (ALL) equal the sum of its set periods, on every count both have?
    shared = box_all.index.intersection(box_sets.index)
    for side in ("home", "away"):
        cols = [f"{side}_{f}" for f in C.FIELDS]
        a, s = box_all.loc[shared, cols], box_sets.loc[shared, cols]
        both = a.notna() & s.notna()
        eq = ((a == s) | ~both).all(axis=1) & both.any(axis=1)
        box_all[f"{side}_x_all_equals_setsum"] = np.nan
        box_all.loc[shared, f"{side}_x_all_equals_setsum"] = eq.astype(float).where(both.any(axis=1))
    common = {"inputs": rec, "collections": box_stats, "orientation": orient_counts,
              "records_read": {"events_listed": int(len(ev)), "events_with_box": int(len(box_all))}}
    build_box(L, box_all, "tp_sofascore_box", "period ALL (SofaScore's match totals)", common)
    build_box(L, box_sets, "tp_sofascore_setbox",
              "the sum of SofaScore's per-set periods 1ST..5TH (a count only where every set period has it)", common)

    # ---------------------------------------------------------------- recount
    T.log("points")
    pt, pt_stats = load_points()
    pt = pt[pt["event_id"].isin(set(L.index))]
    T.log(f"recount {pt['event_id'].nunique():,} linked events, {len(pt):,} points")
    R, G = recount_all(pt)
    RL = L.join(R, how="inner")
    # set scores: recount vs the event's own vs Stage 0's
    sets_ev_ok = [tuple(map(tuple, s)) == tuple(e) for s, e in zip(RL["sets"], RL["ev_sets"])]
    s0_ok = []
    rec_win = []
    for sets, a1, a_won, s0s, st in zip(RL["sets"], RL["a1"], RL["a_won"], RL["s0_sets"], RL["status_description"]):
        if a1 is None or (isinstance(a1, float) and np.isnan(a1)) or not sets:
            s0_ok.append(False)
            rec_win.append(None)
            continue
        ab = [(x, y) if a1 else (y, x) for x, y in sets]            # A first
        wf = ab if a_won else [(y, x) for x, y in ab]              # Stage 0's winner first
        s0_ok.append(bool(K_sets_equal(wf, s0s)))
        sa = sum(1 for x, y in ab if x > y and _set_done(x, y))
        sb = sum(1 for x, y in ab if y > x and _set_done(y, x))
        # the recount's winner (A won?), by finished sets; only where SofaScore says the match ended (a retirement's
        # winner can trail in sets, so the points cannot name him)
        rec_win.append(None if (sa == sb or st != "Ended") else (sa > sb))
    RL["x_sets_equal_event"] = sets_ev_ok
    RL["x_sets_equal_stage0"] = s0_ok
    RL["rec_a_won"] = rec_win
    complete = RL["listing_ok"].astype(bool) & RL["x_sets_equal_event"] & RL["x_sets_equal_stage0"]
    w = pd.DataFrame({"source_key": "sofascore:" + RL.index.astype(str), "match_id": RL["match_id"].to_numpy(),
                      "a1": RL["a1"].to_numpy(), "complete": complete.to_numpy(),
                      "link_method": RL["link_method"].to_numpy()})
    for side, k in (("home", "p1"), ("away", "p2")):
        for f in ("svpt", "sv_won", "sv_gms", "bp_faced", "bp_saved"):
            w[f"{k}_{f}"] = RL[f"{side}_{f}"].astype("float64").to_numpy()
        for f in ("ace", "df", "first_in", "first_won", "second_won"):
            w[f"{k}_{f}"] = np.nan
        w[f"{k}_x_ace_listed"] = RL[f"{side}_ace_listed"].to_numpy()
        w[f"{k}_x_df_listed"] = RL[f"{side}_df_listed"].to_numpy()
        w[f"{k}_x_ace_max"] = (RL[f"{side}_ace_listed"] + RL[f"{side}_holds"]).to_numpy()
        w[f"{k}_x_df_max"] = (RL[f"{side}_df_listed"] + RL[f"{side}_breaks"]).to_numpy()
        w[f"{k}_x_unlisted_last_points"] = RL[f"{side}_finals"].to_numpy()
        w[f"{k}_x_tb_points_served"] = RL[f"{side}_tb_pts"].to_numpy()
        w[f"{k}_x_src_side"] = side
        w[f"{k}_x_bp_at_adv"] = RL[f"{side}_bp_at_adv"].to_numpy()
        w[f"{k}_x_bp_games"] = RL[f"{side}_bp_games"].to_numpy()
        w[f"{k}_x_games_broken"] = RL[f"{side}_breaks"].to_numpy()
    # the recount's winner, oriented: p1 (home) won?
    a1v = RL["a1"].to_numpy()
    rw = RL["rec_a_won"].to_numpy()
    p1_won = [None if (r is None or a is None) else (r if a else (not r)) for r, a in zip(rw, a1v)]
    w["p1_x_src_won"] = [np.nan if v is None else v for v in p1_won]
    w["p2_x_src_won"] = [np.nan if v is None else (not v) for v in p1_won]
    w["x_collection"] = RL["pts_collection"].to_numpy()
    w["x_listing_ok"] = RL["listing_ok"].to_numpy()
    w["x_sets_equal_event"] = RL["x_sets_equal_event"].to_numpy()
    w["x_sets_equal_stage0"] = RL["x_sets_equal_stage0"].to_numpy()
    w["x_unfinished_games"] = RL["unfinished_games"].to_numpy()
    w["x_status"] = RL["status_description"].to_numpy()
    w["x_season"] = RL["season"].to_numpy()
    rc = T.to_contract(w, "tp_sofascore_recount", FAMILY, "recount",
                       player_extra=["x_ace_listed", "x_df_listed", "x_ace_max", "x_df_max", "x_unlisted_last_points",
                                     "x_tb_points_served", "x_bp_at_adv", "x_bp_games", "x_games_broken", "x_src_won",
                                     "x_src_side"],
                       match_extra=["x_collection", "x_listing_ok", "x_sets_equal_event", "x_sets_equal_stage0",
                                    "x_unfinished_games", "x_status", "x_season"])
    rc["x_src_won"] = rc["x_src_won"].astype("boolean")
    G.to_parquet(T.READERS / "tp_sofascore_games.parquet", index=False)
    rc_summary = {
        "inputs": rec, "collections": pt_stats,
        "records_read": {"events_with_points": int(sum(v["taken_from_here"] for v in pt_stats.values())),
                         "linked_events_recounted": int(len(RL))},
        "dropped": {"point_events_not_in_link_file": int(sum(v["taken_from_here"] for v in pt_stats.values()) - len(RL)),
                    "orientation_unresolved": int(RL["a1"].isna().sum())},
        "checks": {"listing_ok": int(RL["listing_ok"].sum()), "sets_equal_event": int(sum(sets_ev_ok)),
                   "sets_equal_stage0": int(sum(s0_ok)), "complete": int(complete.sum()),
                   "games": int(len(G)), "games_ok": int(G["game_ok"].sum()),
                   "tiebreak_games": int(G["tiebreak"].sum())},
        "complete_by_collection": T.tidy_counts(RL.loc[complete, "pts_collection"].value_counts()),
        "contract_checks": T.check_contract(rc),
        "winner_vs_stage0_complete_matches": T.winner_check(rc[rc["complete"]]),
        "winner_vs_stage0_all": T.winner_check(rc),
        "definitions": __doc__.split("Recount, from the point records")[1].split("Orientation:")[0].strip(),
    }
    san = T.sanity(rc[rc["complete"]], by=["tour"])
    rc_summary["sanity_vs_stage0_complete_by_tour"] = T.records(san)
    rc_summary["hand_check"] = {"keys": T.sample_keys(rc, where=rc["complete"]), "status": "pending"}
    T.write_reader(rc, "tp_sofascore_recount", rc_summary)
    T.log(f"done in {time.time() - t0:.0f}s")
    return 0


def _set_done(w: int, l: int) -> bool:
    """A finished set, the winner's games first: 6+ with a two-game lead, 7-6, or a match tiebreak written 1-0."""
    return (w >= 6 and w - l >= 2) or (w == 7 and l == 6) or (w == 1 and l == 0)


def K_sets_equal(x, y) -> bool:
    return T.K.sets_equal(tuple(tuple(s) for s in x), y)


if __name__ == "__main__":
    sys.exit(main())
