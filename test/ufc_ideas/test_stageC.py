"""Stage C of the study "ideas borrowed from UFC-predictions": strength of schedule, the retrospective credit and the
fatigue measures (src/eda/ufc_ideas/stageC_sos.py, stageC_fatigue.py).

Each family is checked on a hand-made history against a row-by-row reading of the Brief's time rule: a round robin's
matches never see each other, two events of one week never see each other, an earlier round of the same event is
seen, and the retrospective "now" rating never includes the pool match's week. Also: Elo's update reproduces Stage 1's
pass, the late-match decline on a hand-made point sequence, the set-counting simulator against Stage 2's, the grinder
sums, and the probe catching a planted leak.

Run: ./python.sh -m pytest test/ufc_ideas/test_stageC.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402
from src.eda.predictability_diagnostic import stage4_features as F  # noqa: E402
from src.eda.ufc_ideas import stageC_fatigue as FT  # noqa: E402
from src.eda.ufc_ideas import stageC_sos as S  # noqa: E402

CONSTS = {"atp": {"k0": 600.0, "offset": 2.0, "shape": 0.6, "w": 0.3},
          "wta": {"k0": 600.0, "offset": 1.0, "shape": 0.6, "w": 0.25}}
PRIORS = {t: {"m_elo": 9.0, "m_rating": 0.05, "strong_line_elo_points": 1550.0} for t in C.TOURS}
CTX = {"elo": CONSTS, "priors": PRIORS}
LN = S.LN


# ------------------------------------------------------------------------------------------------
# A hand-made history: knockout events, a round robin and a second event in the same week, over 70 weeks

def toy(seed: int = 0, weeks: int = 70, players: int = 12, statuses=True) -> pd.DataFrame:
    """Two rows per match (A then B), chronological, with every column the Stage C builders and the probe read."""
    rng = np.random.default_rng(seed)
    recs = []
    mid = 0
    start = pd.Timestamp("2025-01-06")
    for wk in range(weeks):
        date = start + pd.Timedelta(weeks=wk)
        events = [("K", 8)] + ([("R", 4)] if wk % 3 == 0 else []) + ([("K2", 4)] if wk % 4 == 1 else [])
        for name, size in events:
            ev = f"{name}{wk}"
            surface = "Clay" if (wk // 5) % 2 else "Hard"
            pool = [f"p{x}" for x in rng.permutation(players)[:size]]
            if name == "R":                                   # a round robin: every pairing in one round
                rounds = [("RR", [(pool[i], pool[j]) for i in range(4) for j in range(i + 1, 4)])]
            else:
                rounds = []
                cur = pool
                for rn in (["QF", "SF", "F"] if size == 8 else ["SF", "F"]):
                    pairs = [(cur[i], cur[i + 1]) for i in range(0, len(cur), 2)]
                    rounds.append((rn, pairs))
                    cur = [a if rng.random() < 0.5 else b for a, b in pairs]
            for rn, pairs in rounds:
                for a, b in pairs:
                    st = "completed"
                    if statuses:
                        u = rng.random()
                        st = "walkover" if u < 0.04 else ("retired" if u < 0.08 else "completed")
                    a_won = bool(rng.random() < 0.5)
                    for side, p, o, won in (("A", a, b, a_won), ("B", b, a, not a_won)):
                        recs.append({"match_id": f"m{mid}", "side": side, "player_id": p, "opponent_id": o,
                                     "tournament_id": ev, "tournament_name": ev, "tournament_date": date, "round": rn,
                                     "round_order": C.ROUND_ORDER[rn], "surface": surface, "status": st, "won": won})
                    mid += 1
    df = pd.DataFrame(recs)
    # chronological, matches kept as A, B pairs
    first = df.groupby("match_id", sort=False).head(1).copy()
    first["_k"] = np.arange(len(first))
    first = first.sort_values(["tournament_date", "round_order", "tournament_id", "_k"], kind="mergesort")
    order = {m: i for i, m in enumerate(first["match_id"])}
    df["order"] = df["match_id"].map(order)
    df = df.sort_values(["order", "side"], kind="mergesort").reset_index(drop=True)
    n = len(df)
    df["tour"] = "atp"
    df["year"] = df["tournament_date"].dt.year
    df["level"] = "T250"
    df["qualifying"] = False
    df["evaluation"] = True
    df["format"] = "standard"
    df["best_of"] = 3
    df["minutes"] = rng.integers(60, 180, n // 2).repeat(2).astype("float64")
    df["elo_own"] = rng.normal(1600, 120, n)
    df["elo_surf_own"] = rng.normal(1600, 120, n)
    df["elo_n_own"] = rng.integers(0, 60, n).astype("float64")
    df["elo_nsurf_own"] = rng.integers(0, 30, n).astype("float64")
    p = rng.uniform(0.2, 0.8, n // 2)
    df["p_elo_a"] = p.repeat(2)
    df["serve_own"] = rng.normal(0, 0.2, n)
    df["return_own"] = rng.normal(0, 0.2, n)
    df["serve_opp"] = F.opp(df["serve_own"].to_numpy())
    df["return_opp"] = F.opp(df["return_own"].to_numpy())
    df["rank"] = rng.integers(1, 300, n).astype("float64")
    df["age"] = rng.uniform(18, 35, n)
    df["day"] = df["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    df["pcode"] = pd.factorize(df["player_id"])[0].astype("int64")
    return F.prepare(df)


def visible(df: pd.DataFrame, i: int, played_only: bool = True) -> np.ndarray:
    """The rows the Brief's rule lets row i see (the same player): earlier weeks, and earlier rounds of the same
    event. Never row i, its own round (a round robin), or another event of its week."""
    r = df.iloc[i]
    m = (df["player_id"].eq(r["player_id"]) & ((df["tournament_date"] < r["tournament_date"]) | (
        df["tournament_date"].eq(r["tournament_date"]) & df["tournament_id"].eq(r["tournament_id"])
        & (df["round_order"] < r["round_order"])))).to_numpy()
    return m & df["played"].to_numpy() if played_only else m


def blend(df: pd.DataFrame, j: int) -> float:
    w = CONSTS[df["tour"].iloc[j]]["w"]
    sv = df["elo_surf_own"].iloc[j]
    return (1 - w) * df["elo_own"].iloc[j] + w * (df["elo_own"].iloc[j] if np.isnan(sv) else sv)


# ------------------------------------------------------------------------------------------------
# Family 1: strength of schedule

@pytest.mark.parametrize("K", [0.0, 5.0])
def test_sos_equals_a_row_by_row_reading(K):
    df = toy(seed=1)
    sums = S.sos_sums(df, CTX)
    kk = np.full(len(df), K)
    v52, e52 = S.sos_value(sums, "sos_elo|52 weeks", df, CTX, kk)
    vdec, edec = S.sos_value(sums, "sos_elo|decayed", df, CTX, kk)
    vwon, _ = S.sos_value(sums, "sos_won_elo|52 weeks", df, CTX, kk)
    vrat, _ = S.sos_value(sums, "sos_rating|52 weeks", df, CTX, kk)
    vover, _ = S.sos_value(sums, "over_elo|52 weeks", df, CTX, kk)
    vstr, _ = S.sos_value(sums, "over_elo_strong|52 weeks", df, CTX, kk)
    day = df["day"].to_numpy()
    won = df["won"].to_numpy()
    p_own = np.where(np.arange(len(df)) % 2 == 0, df["p_elo_a"], 1 - df["p_elo_a"])
    checked = 0
    for i in range(0, len(df), 3):
        seen = visible(df, i)
        w52 = seen & (day >= day[i] - S.WEEK52)
        idx = np.flatnonzero(w52)
        assert e52[i] == (len(idx) > 0)
        if not len(idx):
            continue
        s_opp = np.array([LN * blend(df, j ^ 1) for j in idx])
        assert v52[i] == pytest.approx((s_opp.sum() + K * 9.0) / (len(idx) + K), rel=1e-10, abs=1e-12)
        wn = won[idx]
        want_won = (s_opp[wn].sum() + K * 9.0) / (wn.sum() + K) if (wn.sum() + K) > 0 else 9.0
        assert vwon[i] == pytest.approx(want_won, rel=1e-10, abs=1e-12)
        rat = np.array([df["serve_own"].iloc[j ^ 1] + df["return_own"].iloc[j ^ 1] for j in idx])
        assert vrat[i] == pytest.approx((rat.sum() + K * 0.05) / (len(idx) + K), rel=1e-9, abs=1e-12)
        over = won[idx] - p_own[idx]
        assert vover[i] == pytest.approx(over.sum() / (len(idx) + K), rel=1e-9, abs=1e-12)
        strong = np.array([blend(df, j ^ 1) > 1550.0 for j in idx])
        want_s = over[strong].sum() / (strong.sum() + K) if (strong.sum() + K) > 0 else 0.0
        assert vstr[i] == pytest.approx(want_s, rel=1e-9, abs=1e-12)
        all_idx = np.flatnonzero(seen)
        wt = np.exp2(-(day[i] - day[all_idx]) / (7.0 * S.HALF_LIFE))
        s_all = np.array([LN * blend(df, j ^ 1) for j in all_idx])
        assert vdec[i] == pytest.approx(((s_all * wt).sum() + K * 9.0) / (wt.sum() + K), rel=1e-9)
        checked += 1
    assert checked > 100


def test_round_robin_and_same_week_events_are_never_seen():
    """The rule's three cases, on the as-of sums directly: a round robin's matches never see each other, two events
    of one week never see each other, an earlier round of the same event is seen."""
    df = toy(seed=2, statuses=False)
    sums = S.sos_sums(df, CTX)
    n_seen = sums["car"][:, sums["ix"]["n"]]
    rr = np.flatnonzero(df["round"].eq("RR").to_numpy())
    for i in rr:
        same_rr = (df["tournament_id"].eq(df["tournament_id"].iloc[i]) & df["player_id"].eq(df["player_id"].iloc[i])).to_numpy()
        earlier = (df["player_id"].eq(df["player_id"].iloc[i]) & (df["tournament_date"] < df["tournament_date"].iloc[i])).to_numpy()
        assert n_seen[i] == earlier.sum()                      # none of the round robin's other matches
        assert same_rr.sum() >= 2
    two = df[df["tournament_id"].str.startswith("K2")]
    hits = 0
    for i in two.index:
        r = df.iloc[i]
        other = (df["player_id"].eq(r["player_id"]) & df["tournament_date"].eq(r["tournament_date"])
                 & df["tournament_id"].ne(r["tournament_id"])).to_numpy()
        hits += int(other.any())
        want = visible(df, i).sum()
        assert n_seen[i] == want
    assert hits > 0                                            # a player in both events of a week exists
    sf = np.flatnonzero(df["round"].eq("SF").to_numpy() & df["tournament_id"].str.match(r"K\d").to_numpy())
    assert any(n_seen[i] > (visible(df, i) & (df["tournament_date"] < df["tournament_date"].iloc[i]).to_numpy()).sum()
               for i in sf)                                    # the quarter-final of the same event is seen


# ------------------------------------------------------------------------------------------------
# Family 2: the retrospective credit

def reading_credit(df: pd.DataFrame, i: int, d_all: np.ndarray, d_s: np.ndarray) -> tuple[int, float, float]:
    """The rule's words, row by row, for player-row i: every played match of the player that row i may see in the last
    52 weeks; for each, the opponent's blended Elo now (their latest row of an earlier week than row i's, read only if
    it comes after the meeting by Elo's own rule; overall and surface parts separately) minus at the meeting; later
    rematches' updates for the opponent taken out; for "later only", the meeting's own update too."""
    day, ev, rnd, order = (df[c].to_numpy() for c in ("day", "ev", "round_order", "order"))
    pc, surf = df["pcode"].to_numpy(), df["surf"].to_numpy()
    ov, sv = df["elo_own"].to_numpy(), df["elo_surf_own"].to_numpy()
    w = CONSTS["atp"]["w"]
    enc = np.flatnonzero(visible(df, i) & (day >= day[i] - S.WEEK52))
    key = lambda j: (day[j], ev[j], rnd[j], order[j])  # noqa: E731

    def sees(j, x):
        return j is not None and (day[j] > day[x] or (day[j] == day[x] and ev[j] == ev[x] and rnd[j] > rnd[x]))

    def latest(cands):
        return max(cands, key=key) if len(cands) else None
    tot_spec = tot_later = 0.0
    # the pool match's tennis week: Monday to Sunday, a Sunday date counting with the following Monday; "now" reads
    # rows dated before the Sunday that precedes it
    monday = (pd.Timestamp(df["tournament_date"].iloc[i]) + pd.Timedelta(days=1)).to_period("W-SUN").start_time
    first_day = int(np.datetime64((monday - pd.Timedelta(days=1)).date(), "D").astype("int64"))
    for e in enc:
        m = e ^ 1
        O = pc[m]
        mine_o = np.flatnonzero(pc == O)
        j = latest([x for x in mine_o if day[x] < first_day])
        js = latest([x for x in mine_o if day[x] < first_day and surf[x] == surf[e]])
        part_all = ov[j] - ov[m] if sees(j, m) else 0.0
        part_s = sv[js] - sv[m] if sees(js, m) else 0.0
        later_meet = [u for u in enc if key(u) > key(e) and pc[u ^ 1] == O]
        rem_all = sum(d_all[u ^ 1] for u in later_meet if sees(j, u ^ 1))
        rem_s = sum(d_s[u ^ 1] for u in later_meet if surf[u] == surf[e] and sees(js, u ^ 1))
        spec = LN * ((1 - w) * (part_all - rem_all) + w * (part_s - rem_s))
        own = LN * ((1 - w) * (d_all[m] if sees(j, m) else 0.0) + w * (d_s[m] if sees(js, m) else 0.0))
        tot_spec += spec
        tot_later += spec - own
    return len(enc), tot_spec, tot_later


def test_credit_equals_a_row_by_row_reading():
    df = toy(seed=3)
    rng = np.random.default_rng(0)
    d_all, d_s = rng.normal(0, 15, len(df)), rng.normal(0, 15, len(df))
    rows_i = np.arange(0, len(df), 2)
    rs = S.revalue_pairs(df, CONSTS, rows_i, deltas=(d_all, d_s))
    rematch = 0
    for q, i in enumerate(rows_i):
        n, sp, la = reading_credit(df, int(i), d_all, d_s)
        assert rs["n"][q] == n
        assert rs["spec"][q] == pytest.approx(sp, abs=1e-10)
        assert rs["later"][q] == pytest.approx(la, abs=1e-10)
    rematch = rs["rematch_pairs"].sum()
    assert rematch > 0                                         # the history has later rematches inside readings
    assert (rs["with_evidence"] < rs["n"]).any()               # and encounters with no later evidence


def test_now_never_reads_the_pool_matchs_week():
    """F beats O in week 0; O plays another event in week 2, the week of F's pool match, with an absurd rating: the
    credit must read O's week-1 row, never the week-2 one."""
    recs = []
    d0 = pd.Timestamp("2025-03-03")

    def match(mid, ev, wk, rn, a, b, a_won, ea, eb):
        for side, p, won, e in (("A", a, a_won, ea), ("B", b, not a_won, eb)):
            recs.append({"match_id": mid, "side": side, "player_id": p, "tournament_id": ev, "tournament_name": ev,
                         "tournament_date": d0 + pd.Timedelta(weeks=wk), "round_order": C.ROUND_ORDER[rn], "round": rn,
                         "won": won, "elo_own": e})
    match("m0", "E0", 0, "QF", "F", "O", True, 1700.0, 1650.0)       # the meeting
    match("m1", "E1", 1, "QF", "O", "X", True, 1640.0, 1500.0)       # O later: rating 1640 before it
    match("m2", "E2", 2, "QF", "O", "Y", True, 2900.0, 1500.0)       # O in the pool match's week: must not be read
    match("m3", "E3", 2, "QF", "F", "Z", True, 1720.0, 1500.0)       # F's pool match
    df = pd.DataFrame(recs)
    df["order"] = np.repeat(np.arange(4), 2)
    df["elo_surf_own"] = np.nan
    df["surface"] = None
    for c, v in (("tour", "atp"), ("status", "completed"), ("level", "T250"), ("qualifying", False), ("format", "standard"),
                 ("year", 2025), ("best_of", 3), ("evaluation", True)):
        df[c] = v
    df["day"] = df["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    df["pcode"] = pd.factorize(df["player_id"])[0]
    df = F.prepare(df)
    zero = np.zeros(len(df))
    rs = S.revalue_pairs(df, CONSTS, np.array([6]), deltas=(zero, zero))   # F's row of m3
    assert rs["n"][0] == 1
    assert rs["spec"][0] == pytest.approx(LN * (1640.0 - 1650.0), abs=1e-12)  # unknown surface: overall Elo alone
    # with the meeting's own update for O (-20 points), "later only" adds it back
    d_all = zero.copy()
    d_all[1] = -20.0
    rs2 = S.revalue_pairs(df, CONSTS, np.array([6]), deltas=(d_all, zero))
    assert rs2["later"][0] == pytest.approx(LN * (1640.0 - 1650.0 + 20.0), abs=1e-12)


@pytest.mark.parametrize("o_day, pool_day", [(14, 16), (13, 14)])
def test_now_ignores_an_earlier_date_of_the_same_tennis_week(o_day, pool_day):
    """Stage 0 dates some events on another weekday. O's event dated the Monday of the pool match's week, the pool
    match's event dated that Wednesday; or O's event dated the Sunday before a Monday-dated pool match (a draw that
    starts on the Sunday belongs to that week): of the same tennis week, never read, though its date is earlier."""
    recs = []
    d0 = pd.Timestamp("2025-03-03")                          # a Monday

    def match(mid, ev, date, a, b, a_won, ea, eb):
        for side, p, won, e in (("A", a, a_won, ea), ("B", b, not a_won, eb)):
            recs.append({"match_id": mid, "side": side, "player_id": p, "tournament_id": ev, "tournament_name": ev,
                         "tournament_date": date, "round_order": C.ROUND_ORDER["QF"], "round": "QF", "won": won,
                         "elo_own": e})
    match("m0", "E0", d0, "F", "O", True, 1700.0, 1650.0)
    match("m1", "E1", d0 + pd.Timedelta(days=7), "O", "X", True, 1640.0, 1500.0)
    match("m2", "E2", d0 + pd.Timedelta(days=o_day), "O", "Y", True, 2900.0, 1500.0)     # the pool match's week
    match("m3", "E3", d0 + pd.Timedelta(days=pool_day), "F", "Z", True, 1720.0, 1500.0)  # the pool match
    df = pd.DataFrame(recs)
    df["order"] = np.repeat(np.arange(4), 2)
    df["elo_surf_own"] = np.nan
    df["surface"] = None
    for c, v in (("tour", "atp"), ("status", "completed"), ("level", "T250"), ("qualifying", False), ("format", "standard"),
                 ("year", 2025), ("best_of", 3), ("evaluation", True)):
        df[c] = v
    df["day"] = df["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    df["pcode"] = pd.factorize(df["player_id"])[0]
    df = F.prepare(df)
    zero = np.zeros(len(df))
    rs = S.revalue_pairs(df, CONSTS, np.array([6]), deltas=(zero, zero))
    assert rs["spec"][0] == pytest.approx(LN * (1640.0 - 1650.0), abs=1e-12)
    assert rs["date_rule_same_week"][0] == 1                 # an earlier-date rule would have read the 2900


def test_rematch_update_is_taken_out_of_now():
    """F beats O in week 0 and again in week 2; the reading for F's week-4 match: O's latest earlier row is in week 3.
    The week-2 rematch's update for O comes out of the first meeting's credit, not out of the second's."""
    recs = []
    d0 = pd.Timestamp("2025-03-03")

    def match(mid, ev, wk, a, b, a_won, ea, eb):
        for side, p, won, e in (("A", a, a_won, ea), ("B", b, not a_won, eb)):
            recs.append({"match_id": mid, "side": side, "player_id": p, "tournament_id": ev, "tournament_name": ev,
                         "tournament_date": d0 + pd.Timedelta(weeks=wk), "round_order": C.ROUND_ORDER["QF"], "round": "QF",
                         "won": won, "elo_own": e})
    match("m0", "E0", 0, "F", "O", True, 1700.0, 1650.0)
    match("m1", "E1", 2, "F", "O", True, 1710.0, 1630.0)
    match("m2", "E2", 3, "O", "X", True, 1600.0, 1500.0)
    match("m3", "E3", 4, "F", "Z", True, 1720.0, 1500.0)
    df = pd.DataFrame(recs)
    df["order"] = np.repeat(np.arange(4), 2)
    df["elo_surf_own"] = np.nan
    df["surface"] = None
    for c, v in (("tour", "atp"), ("status", "completed"), ("level", "T250"), ("qualifying", False), ("format", "standard"),
                 ("year", 2025), ("best_of", 3), ("evaluation", True)):
        df[c] = v
    df["day"] = df["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    df["pcode"] = pd.factorize(df["player_id"])[0]
    df = F.prepare(df)
    d_all = np.zeros(len(df))
    d_all[1], d_all[3] = -20.0, -30.0           # O's updates at the two meetings
    rs = S.revalue_pairs(df, CONSTS, np.array([6]), deltas=(d_all, np.zeros(len(df))), keep_pairs=True)
    pairs = rs["pairs"].sort_values("e")
    first, second = pairs.iloc[0], pairs.iloc[1]
    assert first["spec"] == pytest.approx(LN * ((1600.0 - 1650.0) - (-30.0)), abs=1e-12)
    assert second["spec"] == pytest.approx(LN * (1600.0 - 1630.0), abs=1e-12)
    assert first["later"] == pytest.approx(LN * ((1600.0 - 1650.0) + 30.0 + 20.0), abs=1e-12)
    assert second["later"] == pytest.approx(LN * ((1600.0 - 1630.0) + 30.0), abs=1e-12)


def test_elo_update_reproduces_stage1_pass():
    df = toy(seed=4, weeks=30)
    a = df.iloc[0::2].reset_index(drop=True)
    m = pd.DataFrame({"tournament_date": a["tournament_date"], "tournament_id": a["tournament_id"],
                      "round_order": a["round_order"], "player_a_id": a["player_id"],
                      "player_b_id": df["player_id"].to_numpy()[1::2], "a_won": a["won"], "surface": a["surface"]})
    h = B.history_arrays(m)
    upd = a["status"].isin(["completed", "retired"]).tolist()
    k = CONSTS["atp"]
    out = B.elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, h["n_players"],
                     k["k0"], k["offset"], k["shape"])
    df["elo_own"] = out[:, [0, 1]].reshape(-1)
    df["elo_n_own"] = out[:, [2, 3]].reshape(-1)
    df["elo_surf_own"] = out[:, [4, 5]].reshape(-1)
    df["elo_nsurf_own"] = out[:, [6, 7]].reshape(-1)
    d_all, d_s = S.elo_deltas(df, CONSTS)
    chk = S.delta_check(df, CONSTS, d_all)
    assert chk["checked"] > 20 and chk["max_abs_error_points"] < 1e-9
    # the surface rating: the next row on the same surface in a later week, nothing else in between
    pc, day, surf = df["pcode"].to_numpy(), df["day"].to_numpy(), df["surf"].to_numpy()
    o, _ = S.sorted_view(df, pc * 8 + surf)
    n_ok = 0
    for x, y in zip(o[:-1], o[1:]):
        if pc[x] != pc[y] or surf[x] != surf[y] or day[y] <= day[x] or not df["played"].iloc[x]:
            continue
        others = (pc == pc[x]) & (surf == surf[x]) & (day == day[x])
        if others.sum() > 1:
            continue
        assert df["elo_surf_own"].iloc[y] - df["elo_surf_own"].iloc[x] == pytest.approx(d_s[x], abs=1e-9)
        n_ok += 1
    assert n_ok > 10


# ------------------------------------------------------------------------------------------------
# Family 3: fatigue

def points(seq):
    """A point table from (set, server is player 1, server won)."""
    return pd.DataFrame({"match_id": "t1", "tour": "atp", "set_no": [s for s, _, _ in seq],
                         "srv1": [p1 for _, p1, _ in seq], "won1": [p1 == sw for _, p1, sw in seq]})


def test_late_decline_on_a_hand_made_point_sequence():
    seq = ([(1, True, True)] * 7 + [(1, True, False)] * 3 + [(2, True, True)] * 5 + [(2, True, False)] * 5     # p1 serves 12/20 early
           + [(1, False, True)] * 6 + [(1, False, False)] * 4 + [(2, False, True)] * 5 + [(2, False, False)] * 5   # p2 11/20
           + [(3, True, True)] * 5 + [(3, True, False)] * 5 + [(3, False, True)] * 8 + [(3, False, False)] * 2)    # 5/10, 8/10
    pts = points(seq)
    early, late = pts["set_no"].to_numpy() < 3, pts["set_no"].to_numpy() >= 3
    mc = FT.match_change(pts, early, late)
    want = (5 / 10 - 12 / 20) - (8 / 10 - 11 / 20)
    assert mc["d1"].iloc[0] == pytest.approx(want, abs=1e-12)
    assert mc["u"].iloc[0] == pytest.approx(1 / (1 / 10 + 1 / 20 + 1 / 10 + 1 / 20), abs=1e-12)
    pc = FT.player_changes(pts)
    assert pc.loc[pc["side"] == 1, "d_sets"].iloc[0] == pytest.approx(want, abs=1e-12)
    assert pc.loc[pc["side"] == 2, "d_sets"].iloc[0] == pytest.approx(-want, abs=1e-12)
    # the points variant: the first 150 points against the rest (the match has 80: no late segment)
    assert pc["u_points150"].iloc[0] == 0 and np.isnan(pc["d_points150"].iloc[0])
    # a player who never served late gives no measure
    mc2 = FT.match_change(pts[~((pts["set_no"] == 3) & pts["srv1"])], early[~((pts["set_no"] == 3) & pts["srv1"]).to_numpy()],
                          late[~((pts["set_no"] == 3) & pts["srv1"]).to_numpy()])
    assert np.isnan(mc2["d1"].iloc[0]) and mc2["u"].iloc[0] == 0


def test_decline_trait_sees_only_earlier_weeks():
    """The trait before a match: earlier Slams only (a Slam's own matches, same tournament Monday, never)."""
    pbp = pd.DataFrame({"pcode": [0, 0, 0, 1], "day": [100, 200, 300, 200], "linked": True,
                        "d_sets": [0.1, -0.2, 0.3, 0.05], "u_sets": [10.0, 20.0, 10.0, 15.0]})
    rows = pd.DataFrame({"pcode": [0, 0, 0, 1, 1], "day": [100, 201, 300, 200, 207], "tour": "atp"})
    tr, ex = FT.decline_trait(pbp, rows, {"atp": 30.0, "wta": 30.0})
    assert list(ex) == [False, True, True, False, True]
    assert tr[1] == pytest.approx((0.1 * 10 - 0.2 * 20) / (30 + 30.0))
    assert tr[2] == pytest.approx((0.1 * 10 - 0.2 * 20) / (30 + 30.0))      # the day-300 Slam itself is not seen
    assert tr[4] == pytest.approx(0.05 * 15 / (15 + 30.0))


def test_simulate_sets_equals_stage2_simulator():
    rng = np.random.default_rng(5)
    n = 400
    pa, pb = rng.uniform(0.5, 0.75, n), rng.uniform(0.5, 0.75, n)
    bo = rng.choice([3, 5], n)
    rule = rng.choice(["TB7@6", "TB10@6", "ADV", "TB7@12"], n)
    a = FT.simulate_sets(pa, pb, bo, rule, seed=9)
    b = M.simulate(pa, pb, bo, rule, seed=9)
    assert np.array_equal(a["served"], b["served"]) and np.array_equal(a["won"], b["won"])
    assert np.array_equal(a["a_won"], b["a_won"])
    need = (bo + 1) // 2
    assert ((a["sets"] >= need) & (a["sets"] <= 2 * need - 1)).all()


def test_grinder_sums_and_contrast_equal_a_row_by_row_reading():
    df = toy(seed=6, statuses=False)
    rng = np.random.default_rng(1)
    n = len(df)
    ok = rng.random(n) < 0.8
    gi = {"ok": ok, "r": np.where(ok, rng.normal(0, 4, n), 0.0), "u": np.where(ok, rng.integers(100, 200, n), 0.0)}
    gi["long"] = ok & (rng.random(n) < 0.35)
    gs = FT.grinder_sums(df, gi)
    day = df["day"].to_numpy()
    K = 50.0
    for form in ("career", "52 weeks"):
        val, ex = FT.grinder_value(gs[form], np.full(n, K))
        for i in range(0, n, 4):
            seen = visible(df, i, played_only=False) & ok
            if form == "52 weeks":
                seen &= day >= day[i] - S.WEEK52
            assert ex[i] == seen.any()
            L, Sh = seen & gi["long"], seen & ~gi["long"]
            UL, US = gi["u"][L].sum(), gi["u"][Sh].sum()
            if UL > 0 and US > 0:
                G = gi["r"][L].sum() / UL - gi["r"][Sh].sum() / US
                Ue = UL * US / (UL + US)
                assert val[i] == pytest.approx(G * Ue / (Ue + K), rel=1e-9, abs=1e-12)
            else:
                assert val[i] == 0.0


def test_split_half_contrast_finds_a_planted_trait_and_not_noise():
    rng = np.random.default_rng(2)
    players, per = 300, 80
    unit = np.repeat(np.arange(players), per)
    L = rng.random(players * per) < 0.4
    u = np.full(players * per, 150.0)
    trait = np.repeat(rng.normal(0, 0.03, players), per)
    noise = rng.normal(0, np.sqrt(0.25 / 150), players * per)
    r_true = (np.where(L, trait / 2, -trait / 2) + noise) * u
    r_null = noise * u
    with_trait = FT.split_half_contrast(unit, r_true, u, L, np.random.default_rng(0), n_grid=[20, 40], draws=5)
    null = FT.split_half_contrast(unit, r_null, u, L, np.random.default_rng(0), n_grid=[20, 40], draws=5)
    assert all(x["r"] > 0.3 for x in with_trait)
    assert all(abs(x["r"]) < 0.15 for x in null)


# ------------------------------------------------------------------------------------------------
# The probe

def test_probe_passes_the_builders_and_catches_a_leak():
    df = toy(seed=7, weeks=40)
    K = {c: {"atp": 5.0, "wta": 5.0} for c in list(S.SOS_ROWS) + list(S.REVALUE_ROWS) if not c.startswith("sos_bt")}
    res = S.probe(df, lambda r, aux, pool: S.build(r, CTX, K, pool=pool), n_cuts=3, seed=1)
    assert res["protected_changed"] == 0
    assert res["later_changed"] > 0
    assert res["control_protected_changed"] > 0

    def leaky(r, aux, pool):                      # the SoS of the match itself included: must be caught
        out = S.build(r, CTX, K, cols=["over_elo|52 weeks"], pool=pool)
        _, A, Bi = S.pool_rows(r, pool)
        w = r["won"].to_numpy().astype(float)
        out["leak"] = out["over_elo|52 weeks"] + (w[A] - w[Bi])
        return out
    res2 = S.probe(df, leaky, n_cuts=3, seed=1)
    assert res2["protected_changed"] > 0 and res2["changed_by_column"].get("leak", 0) > 0
