"""B1, finishing-form carry-over: the triple table (audit round 3, item 3). Builds data only; fits nothing.

A triple is three consecutive matches (t-1, t, t+1) of one player at one event (Stage 0 tournament_id: qualifying and
main draw together), all three completed, each gap between consecutive matches 0-3 days on the match-timing clock's
best-estimate day (timing.parquet `obs`; its `start` column is the tournament's start date, the same for every round,
so it cannot measure a gap). Match t needs a usable point sequence (data/studies/point_sequence/sequences.parquet,
tiers 0-2); t-1 and t+1 need the player's serve points (the usable sequence when there is one, else the Stage 0 box
score). Everything is read with year <= 2024 at the reader: 2025-26 is a closed holdout and is never loaded.

Chains. A player's matches at an event, in round order (then start day, then match number). Walkovers (no ball struck)
are left out of the chain; retirements, defaults and unknown endings stay in it and break every triple that contains
them. Team events and the season finals (round robins) are left out, and so is any round-robin round, because their
order within a stage is not fixed by the draw. A player-event with two matches in one round is dropped (ambiguous order).

Columns of carry_triples.parquet (one row per triple; "player" is the triple's player, "opp" the opponent in that match):
    keys        player_id, tour, tournament_id, year (of match t), window ("discovery" 2013-2021, "replication"
                2022-2024, "warmup" before 2013: never analysed), level / map_level / qualifying of t, round_m/t/p
    matches     mid_m, mid_t, mid_p (t-1, t, t+1), side_m/t/p (1 = Stage 0 side A, 2 = side B)
    days        day_m, day_t, day_p (best-estimate day), exact_m/t/p, gap_rev = day_t - day_m, gap_fwd = day_p - day_t
    offsets     ps_m, ps_t, ps_p: the player's pre-match expected serve-point share (stage3_ratings p_serve);
                pso_m, pso_t, pso_p: the opponent's (for the return-point secondary)
    endpoints   sv_n_m, sv_w_m, sv_n_p, sv_w_p: serve points played / won in t-1 and t+1; rt_n_*, rt_w_*: return points
                played / won; ep_src_m/p: "seq" or "box"; won_m, won_p: the player won t-1 / t+1
    match t     bo (3 or 5, from the replay rule), rule, final, late_set (2 or 3), source, tier, strict, s0 (the
                match's first server, 1/2), winner_t (1/2), surface,
                n1, w1, n2, w2, n3, w3: the player's serve points played / won in sets 1-3;
                on1, ow1, ... on3, ow3: the opponent's (his return points are on - ow);
                n_tot, w_tot, on_tot, ow_tot: whole match
    exposures   rE, rL: serve-point residual of set 1 and of the late set, (won - n * ps_t) / n (a share; the fit
                scales it to 10 percentage points); retE, retL: the return-point twins against 1 - pso_t;
                r_tot: whole-match serve residual (a sensitivity control)
    form        form_m: box-score serve form as of t-1 (decayed residual of earlier matches, see form_asof);
                form_p_lit: the same as of t+1 (includes t-1 and t; the audit-literal control, a sensitivity only);
                form_n_m, form_n_p_lit: their weighted serve points

Run: ./python.sh src/eda/point_sequence/carry_data.py   (about two minutes)
Writes data/studies/point_sequence/carry_triples.parquet and carry_data_summary.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as PD  # noqa: E402

OUT = ROOT / "data" / "studies" / "point_sequence"
SEQ = OUT / "sequences.parquet"
SEQ_MATCHES = OUT / "seq_matches.parquet"
RATINGS = PD.OUT / "stage3_ratings.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
TRIPLES = OUT / "carry_triples.parquet"
SUMMARY = OUT / "carry_data_summary.json"

LAST_YEAR = 2024                 # 2025-26: closed holdout, never read
DISCOVERY = (2013, 2021)
REPLICATION = (2022, 2024)
MAX_GAP = 3                      # days between consecutive matches of a triple
FORM_HALF_LIFE = 14.0            # days: the box-score form's decay (the model's two-week half-life)
FORM_K = 50.0                    # serve points of pseudo-count shrinking the form toward 0
FORM_LOOKBACK = 180.0            # days
EXCLUDED_LEVELS = ("TEAM", "FIN")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def window_of(year: pd.Series) -> pd.Series:
    y = year.astype(int)
    return pd.Series(np.select([y.between(*DISCOVERY), y.between(*REPLICATION)], ["discovery", "replication"],
                               "warmup"), index=year.index)


# ------------------------------------------------------------------------------------------------
# Loaders (every one filtered to year <= 2024 at the reader)

def load_stage0() -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["match_id", "tour", "year", "level", "map_level", "qualifying", "round", "round_order", "match_num",
            "surface", "best_of", "format", "tournament_id", "tournament_date", "status", "has_box",
            "player_a_id", "player_b_id", "a_won", "order"]
    m = pd.read_parquet(PD.MATCHES, columns=cols, filters=[("year", "<=", LAST_YEAR)])
    ids = set(m["match_id"])
    mp = pd.read_parquet(PD.MATCH_PLAYERS, columns=["match_id", "player_id", "side", "won", "spw_n", "spw_d",
                                                    "rpw_n", "rpw_d", "has_box"])
    mp = mp[mp["match_id"].isin(ids)].copy()
    return m, mp


def load_sequences() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The chosen usable sequences of matches <= 2024: per match (rule, source, tier, strict, first server, replay
    winner) and per match x set x server (points served, won by the server)."""
    sm = pd.read_parquet(SEQ_MATCHES, columns=["match_id", "source", "chosen", "usable", "strict", "tier", "rule",
                                               "replay_winner", "a1", "year", "status", "score_check"],
                         filters=[("year", "<=", LAST_YEAR)])
    sm = sm[sm["chosen"] & sm["usable"]].drop(columns=["chosen", "usable"]).drop_duplicates("match_id")
    # seq_matches' replay_winner is in the source's orientation; a1 says whether the source's player 1 is side A
    sm["replay_winner_s0"] = np.where(sm["a1"].astype(bool), sm["replay_winner"], 3 - sm["replay_winner"])
    ids = sm["match_id"].tolist()
    tab = pq.read_table(SEQ, columns=["match_id", "usable", "seq", "set_no", "server", "winner"],
                        filters=[("match_id", "in", ids)])
    pts = tab.to_pandas()
    pts["match_id"] = pts["match_id"].astype(str)
    pts = pts[pts["usable"] & pts["server"].isin([1, 2]) & pts["winner"].isin([1, 2]) & (pts["set_no"] >= 1)]
    ordered = pts.sort_values(["match_id", "seq"]).groupby("match_id", sort=False)
    first = ordered["server"].first().rename("s0")
    last_winner = ordered["winner"].last().rename("last_point_winner")
    pts = pts.assign(srv_won=(pts["server"] == pts["winner"]).astype("int64"))
    agg = (pts.groupby(["match_id", "set_no", "server"], observed=True)["srv_won"].agg(["size", "sum"])
           .rename(columns={"size": "n", "sum": "w"}).reset_index())
    sm = sm.merge(first, on="match_id", how="left").merge(last_winner, on="match_id", how="left")
    sets_played = pts.groupby("match_id")["set_no"].max().rename("sets_played")
    sm = sm.merge(sets_played, on="match_id", how="left")
    return sm, agg


def load_ratings() -> pd.DataFrame:
    return pd.read_parquet(RATINGS, columns=["match_id", "p_serve_a", "p_serve_b"],
                           filters=[("year", "<=", LAST_YEAR)])


def load_timing() -> pd.DataFrame:
    """The clock's best-estimate day of each match, ``obs`` (timing.py rule 5: the exact day, else the class's median
    offset placed inside the window), renamed ``start`` here. timing.parquet's own ``start`` column is the tournament's
    start date, the same for every round, so it cannot give a gap between rounds."""
    t = pd.read_parquet(TIMING, columns=["match_id", "obs", "exact"], filters=[("year", "<=", LAST_YEAR)])
    return t.rename(columns={"obs": "start"})


# ------------------------------------------------------------------------------------------------
# Per player-match serve and return counts (sequence first, else box score)

def player_match_counts(m: pd.DataFrame, mp: pd.DataFrame, sm: pd.DataFrame, agg: pd.DataFrame) -> pd.DataFrame:
    side = mp["side"].map({"A": 1, "B": 2}).astype("int64")
    pmc = mp.assign(side=side)[["match_id", "player_id", "side", "won", "spw_n", "spw_d", "rpw_n", "rpw_d",
                                "has_box"]].copy()
    tot = agg.groupby(["match_id", "server"])[["n", "w"]].sum().reset_index()
    seq_ids = set(sm["match_id"])
    own = tot.rename(columns={"server": "side", "n": "seq_sv_n", "w": "seq_sv_w"})
    opp = tot.assign(side=3 - tot["server"]).rename(columns={"n": "seq_on", "w": "seq_ow"}).drop(columns="server")
    pmc = pmc.merge(own, on=["match_id", "side"], how="left").merge(opp, on=["match_id", "side"], how="left")
    has_seq = pmc["match_id"].isin(seq_ids) & pmc["seq_sv_n"].gt(0) & pmc["seq_on"].gt(0)
    has_box = pmc["has_box"].fillna(False).astype(bool) & pmc["spw_d"].gt(0) & pmc["rpw_d"].gt(0)
    pmc["sv_n"] = np.where(has_seq, pmc["seq_sv_n"], np.where(has_box, pmc["spw_d"], np.nan))
    pmc["sv_w"] = np.where(has_seq, pmc["seq_sv_w"], np.where(has_box, pmc["spw_n"], np.nan))
    pmc["rt_n"] = np.where(has_seq, pmc["seq_on"], np.where(has_box, pmc["rpw_d"], np.nan))
    pmc["rt_w"] = np.where(has_seq, pmc["seq_on"] - pmc["seq_ow"], np.where(has_box, pmc["rpw_n"], np.nan))
    pmc["ep_src"] = np.where(has_seq, "seq", np.where(has_box, "box", "none"))
    return pmc[["match_id", "player_id", "side", "won", "sv_n", "sv_w", "rt_n", "rt_w", "ep_src"]]


# ------------------------------------------------------------------------------------------------
# Chains and triples

def build_chains(m: pd.DataFrame, pmc: pd.DataFrame, timing: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    keep = ~m["level"].isin(EXCLUDED_LEVELS) & m["round"].ne("RR") & m["status"].ne("walkover")
    mm = m[keep].merge(timing, on="match_id", how="left")
    rows = pmc.merge(mm[["match_id", "tour", "year", "level", "map_level", "qualifying", "round", "round_order",
                         "match_num", "surface", "best_of", "format", "tournament_id", "tournament_date", "status",
                         "start", "exact"]], on="match_id", how="inner")
    rows["_mn"] = pd.to_numeric(rows["match_num"], errors="coerce")
    rows = rows.sort_values(["tour", "player_id", "tournament_id", "round_order", "start", "_mn", "match_id"],
                            kind="mergesort").reset_index(drop=True)
    dup = rows.duplicated(["tour", "player_id", "tournament_id", "round_order"], keep=False)
    bad_pe = rows.loc[dup, ["tour", "player_id", "tournament_id"]].drop_duplicates()
    info = {"player_matches_in_chains": int(len(rows)),
            "player_events_dropped_two_matches_one_round": int(len(bad_pe))}
    if len(bad_pe):
        rows = rows.merge(bad_pe.assign(_bad=True), on=["tour", "player_id", "tournament_id"], how="left")
        rows = rows[rows["_bad"].isna()].drop(columns="_bad").reset_index(drop=True)
    rows = rows.drop(columns="_mn")
    return rows, info


def make_triples(rows: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    key = ["tour", "player_id", "tournament_id"]
    g = rows.groupby(key, sort=False)
    pos = g.cumcount()
    size = g["match_id"].transform("size")
    mid = rows[(pos >= 1) & (pos <= size - 2)].index.to_numpy()        # candidate t: has a previous and a next
    prev_i, next_i = mid - 1, mid + 1
    t = rows.loc[mid].reset_index(drop=True)
    pm = rows.loc[prev_i].reset_index(drop=True)
    pn = rows.loc[next_i].reset_index(drop=True)
    info = {"candidate_triples": int(len(t))}
    out = pd.DataFrame({
        "player_id": t["player_id"], "tour": t["tour"], "tournament_id": t["tournament_id"], "year": t["year"],
        "level": t["level"], "map_level": t["map_level"], "qualifying": t["qualifying"], "surface": t["surface"],
        "format_t": t["format"],
        "round_m": pm["round"], "round_t": t["round"], "round_p": pn["round"],
        "mid_m": pm["match_id"], "mid_t": t["match_id"], "mid_p": pn["match_id"],
        "side_m": pm["side"], "side_t": t["side"], "side_p": pn["side"],
        "status_m": pm["status"], "status_t": t["status"], "status_p": pn["status"],
        "day_m": pm["start"], "day_t": t["start"], "day_p": pn["start"],
        "exact_m": pm["exact"], "exact_t": t["exact"], "exact_p": pn["exact"],
        "won_m": pm["won"], "won_t": t["won"], "won_p": pn["won"],
        "sv_n_m": pm["sv_n"], "sv_w_m": pm["sv_w"], "sv_n_p": pn["sv_n"], "sv_w_p": pn["sv_w"],
        "rt_n_m": pm["rt_n"], "rt_w_m": pm["rt_w"], "rt_n_p": pn["rt_n"], "rt_w_p": pn["rt_w"],
        "ep_src_m": pm["ep_src"], "ep_src_p": pn["ep_src"],
        "tdate_m": pm["tournament_date"], "tdate_t": t["tournament_date"], "rorder_m": pm["round_order"],
        "rorder_p": pn["round_order"], "tdate_p": pn["tournament_date"],
    })
    out["gap_rev"] = out["day_t"] - out["day_m"]
    out["gap_fwd"] = out["day_p"] - out["day_t"]
    steps = []

    def step(label, mask):
        nonlocal out
        before = len(out)
        out = out[mask(out)].reset_index(drop=True)
        steps.append({"step": label, "kept": int(len(out)), "dropped": int(before - len(out))})

    step("all three completed", lambda d: d["status_m"].eq("completed") & d["status_t"].eq("completed")
         & d["status_p"].eq("completed"))
    step("both gaps known", lambda d: d["gap_rev"].notna() & d["gap_fwd"].notna())
    step("no negative gap (impossible order on the clock)", lambda d: (d["gap_rev"] >= 0) & (d["gap_fwd"] >= 0))
    step(f"both gaps <= {MAX_GAP} days", lambda d: (d["gap_rev"] <= MAX_GAP) & (d["gap_fwd"] <= MAX_GAP))
    info["steps"] = steps
    return out, info


# ------------------------------------------------------------------------------------------------
# Box-score form (own history, in order)

def form_asof(pmc_known: pd.DataFrame, targets: pd.DataFrame, label: str) -> pd.DataFrame:
    """Decayed serve-point residual of a player's earlier matches, as of a target match.

    form = sum_j w_j (won_j - n_j p_j) / (FORM_K + sum_j w_j n_j), w_j = 0.5 ** ((day_target - day_j) / 14), over the
    player's matches j with known serve points (sequence or box score) that are earlier under the own-history rule
    (an earlier tournament date, or the same event and an earlier round), within FORM_LOOKBACK days. A share; 0 with no
    history. targets: player_id, tour, tdate, tournament_id, rorder, day (one row per target), index kept."""
    hist = pmc_known.sort_values(["tour", "player_id", "tournament_date", "round_order"]).reset_index(drop=True)
    groups = {k: (g["tournament_date"].to_numpy(), g["tournament_id"].to_numpy(), g["round_order"].to_numpy(),
                  g["start"].to_numpy(), g["res"].to_numpy(), g["n"].to_numpy())
              for k, g in hist.groupby(["tour", "player_id"], sort=False)}
    num = np.zeros(len(targets))
    den = np.zeros(len(targets))
    for i, (tour, pid, tdate, tid, ro, day) in enumerate(targets[["tour", "player_id", "tdate", "tournament_id",
                                                                   "rorder", "day"]].itertuples(index=False)):
        g = groups.get((tour, pid))
        if g is None:
            continue
        g_date, g_tid, g_ro, g_start, g_res, g_n = g
        earlier = (g_date < np.datetime64(tdate)) | ((g_tid == tid) & (g_ro < ro))
        dd = day - g_start
        sel = earlier & (dd <= FORM_LOOKBACK)
        if not sel.any():
            continue
        w = 0.5 ** (np.clip(dd[sel], 0, None) / FORM_HALF_LIFE)
        num[i] = float((w * g_res[sel]).sum())
        den[i] = float((w * g_n[sel]).sum())
    return pd.DataFrame({f"form_{label}": num / (FORM_K + den), f"form_n_{label}": den}, index=targets.index)


# ------------------------------------------------------------------------------------------------

def main() -> None:
    log("loading Stage 0, sequences, ratings, timing (year <= 2024)")
    m, mp = load_stage0()
    sm, agg = load_sequences()
    rt = load_ratings()
    timing = load_timing()
    summary: dict = {"built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                     "last_year_read": LAST_YEAR, "stage0_matches": int(len(m)),
                     "sequences_chosen_usable": int(len(sm)),
                     "sequences_not_in_stage0": int((~sm["match_id"].isin(set(m["match_id"]))).sum())}
    log(f"{len(m)} Stage 0 matches, {len(sm)} usable sequences")
    pmc = player_match_counts(m, mp, sm, agg)
    rows, info = build_chains(m, pmc, timing)
    summary["chains"] = info
    tri, info = make_triples(rows)
    summary["triples"] = info
    log(f"{len(tri)} triples after status and gap rules")

    # match t's sequence: per set counts for the player and the opponent
    seq_t = sm.set_index("match_id")
    tri = tri[tri["mid_t"].isin(seq_t.index)].reset_index(drop=True)
    summary["triples"]["steps"].append({"step": "match t has a usable sequence", "kept": int(len(tri))})
    a = agg.set_index(["match_id", "set_no", "server"])
    for s in (1, 2, 3):
        for who in ("", "o"):
            srv = tri["side_t"] if who == "" else 3 - tri["side_t"]
            idx = pd.MultiIndex.from_arrays([tri["mid_t"], np.full(len(tri), s), srv.to_numpy()])
            got = a.reindex(idx)
            tri[f"{who}n{s}"] = got["n"].to_numpy()
            tri[f"{who}w{s}"] = got["w"].to_numpy()
    tot = agg.groupby(["match_id", "server"])[["n", "w"]].sum()
    for who in ("", "o"):
        srv = tri["side_t"] if who == "" else 3 - tri["side_t"]
        got = tot.reindex(pd.MultiIndex.from_arrays([tri["mid_t"], srv.to_numpy()]))
        tri[f"{who}n_tot"] = got["n"].to_numpy()
        tri[f"{who}w_tot"] = got["w"].to_numpy()
    st = seq_t.reindex(tri["mid_t"])
    tri["rule"] = st["rule"].to_numpy()
    tri["source"] = st["source"].to_numpy()
    tri["tier"] = st["tier"].to_numpy()
    tri["strict"] = st["strict"].to_numpy()
    tri["s0"] = st["s0"].to_numpy()
    tri["sets_played"] = st["sets_played"].to_numpy()
    tri["replay_winner"] = st["replay_winner_s0"].to_numpy()
    tri["last_point_winner"] = st["last_point_winner"].to_numpy()
    tri["bo"] = tri["rule"].str.extract(r"^bo(\d)")[0].astype(float)
    tri["final"] = tri["rule"].str.extract(r"^bo\d/([a-z0-9]+)")[0]
    tri["short_sets"] = tri["rule"].str.contains("sets4", na=False)
    tri["late_set"] = np.where(tri["bo"] == 5, 3, 2)
    mw = m.set_index("match_id")["a_won"]
    tri["winner_t"] = np.where(mw.reindex(tri["mid_t"]).to_numpy().astype(bool), 1, 2)
    tri["nL"] = np.where(tri["late_set"] == 3, tri["n3"], tri["n2"])
    tri["wL"] = np.where(tri["late_set"] == 3, tri["w3"], tri["w2"])
    tri["onL"] = np.where(tri["late_set"] == 3, tri["on3"], tri["on2"])
    tri["owL"] = np.where(tri["late_set"] == 3, tri["ow3"], tri["ow2"])

    # offsets
    r = rt.set_index("match_id")
    for k in ("m", "t", "p"):
        got = r.reindex(tri[f"mid_{k}"])
        side = tri[f"side_{k}"].to_numpy()
        tri[f"ps_{k}"] = np.where(side == 1, got["p_serve_a"].to_numpy(), got["p_serve_b"].to_numpy())
        tri[f"pso_{k}"] = np.where(side == 1, got["p_serve_b"].to_numpy(), got["p_serve_a"].to_numpy())

    steps = summary["triples"]["steps"]

    def step(label, mask):
        nonlocal tri
        before = len(tri)
        tri = tri[mask].reset_index(drop=True)
        steps.append({"step": label, "kept": int(len(tri)), "dropped": int(before - len(tri))})

    step("match t: best of 3 or 5, not short sets", tri["bo"].isin([3, 5]) & ~tri["short_sets"])
    step("match t: the sequence's winner (replay and last point) is Stage 0's",
         tri["replay_winner"].eq(tri["winner_t"]) & tri["last_point_winner"].eq(tri["winner_t"]))
    step("match t: set 1 and the late set served by both players",
         tri["n1"].gt(0) & tri["nL"].gt(0) & tri["on1"].gt(0) & tri["onL"].gt(0))
    step("endpoints t-1 and t+1 have serve and return points (sequence or box score)",
         tri["sv_n_m"].gt(0) & tri["sv_n_p"].gt(0) & tri["rt_n_m"].gt(0) & tri["rt_n_p"].gt(0))
    step("pre-match p_serve known for t-1, t, t+1 (both players)",
         tri[["ps_m", "ps_t", "ps_p", "pso_m", "pso_t", "pso_p"]].notna().all(axis=1))

    # exposures
    tri["rE"] = (tri["w1"] - tri["n1"] * tri["ps_t"]) / tri["n1"]
    tri["rL"] = (tri["wL"] - tri["nL"] * tri["ps_t"]) / tri["nL"]
    tri["r_tot"] = (tri["w_tot"] - tri["n_tot"] * tri["ps_t"]) / tri["n_tot"]
    pr = 1 - tri["pso_t"]
    tri["retE"] = ((tri["on1"] - tri["ow1"]) - tri["on1"] * pr) / tri["on1"]
    tri["retL"] = ((tri["onL"] - tri["owL"]) - tri["onL"] * pr) / tri["onL"]

    # box-score form (own history): as of t-1 (primary control, the same in both directions) and as of t+1 (literal)
    log("box-score form")
    known = pmc[pmc["sv_n"].gt(0)].merge(m[["match_id", "tour", "tournament_id", "tournament_date", "round_order"]],
                                         on="match_id").merge(timing[["match_id", "start"]], on="match_id")
    rr = rt.set_index("match_id").reindex(known["match_id"])
    known["p"] = np.where(known["side"].to_numpy() == 1, rr["p_serve_a"].to_numpy(), rr["p_serve_b"].to_numpy())
    known = known[known["p"].notna() & known["start"].notna()].copy()
    known["res"] = known["sv_w"] - known["sv_n"] * known["p"]
    known["n"] = known["sv_n"]
    known = known[["tour", "player_id", "tournament_id", "tournament_date", "round_order", "start", "res", "n"]]
    tri["tdate_m"] = pd.to_datetime(tri["tdate_m"])
    tri["tdate_p"] = pd.to_datetime(tri["tdate_p"])
    tm = pd.DataFrame({"tour": tri["tour"], "player_id": tri["player_id"], "tdate": tri["tdate_m"],
                       "tournament_id": tri["tournament_id"], "rorder": tri["rorder_m"], "day": tri["day_m"]})
    tp = pd.DataFrame({"tour": tri["tour"], "player_id": tri["player_id"], "tdate": tri["tdate_p"],
                       "tournament_id": tri["tournament_id"], "rorder": tri["rorder_p"], "day": tri["day_p"]})
    tri = tri.join(form_asof(known, tm, "m")).join(form_asof(known, tp, "p_lit"))

    tri["window"] = window_of(tri["year"])
    tri["triple_id"] = np.arange(len(tri))
    tri.to_parquet(TRIPLES, index=False)

    # counts
    def counts(d):
        return {w: {tour: int(((d["window"] == w) & (d["tour"] == tour)).sum()) for tour in ("atp", "wta")}
                for w in ("warmup", "discovery", "replication")}

    summary["triples_final"] = counts(tri)
    summary["triples_by_window_tour_bo"] = (tri.groupby(["window", "tour", "bo"]).size().rename("n").reset_index()
                                            .to_dict(orient="records"))
    summary["triples_by_window_source"] = (tri.groupby(["window", "source"]).size().rename("n").reset_index()
                                           .to_dict(orient="records"))
    summary["triples_by_window_level"] = (tri.groupby(["window", "map_level"]).size().rename("n").reset_index()
                                          .to_dict(orient="records"))
    summary["players_by_window"] = tri.groupby("window")["player_id"].nunique().to_dict()
    summary["endpoint_source"] = {k: tri[f"ep_src_{k}"].value_counts().to_dict() for k in ("m", "p")}
    summary["gaps"] = {"fwd": tri["gap_fwd"].value_counts().sort_index().to_dict(),
                       "rev": tri["gap_rev"].value_counts().sort_index().to_dict()}
    summary["both_gaps_exact_share"] = float((tri["exact_m"] & tri["exact_t"] & tri["exact_p"]).mean())
    summary["won_m_share"] = float(tri["won_m"].mean())
    summary["won_t_share"] = float(tri["won_t"].mean())
    summary["strict_share"] = float(tri["strict"].mean())
    summary["serve_points_set1_mean"] = float(tri["n1"].mean())
    summary["serve_points_late_mean"] = float(tri["nL"].mean())
    summary["endpoint_serve_points_mean"] = {"m": float(tri["sv_n_m"].mean()), "p": float(tri["sv_n_p"].mean())}
    summary["form_m_has_history_share"] = float((tri["form_n_m"] > 0).mean())
    summary["settings"] = {"max_gap_days": MAX_GAP, "form_half_life_days": FORM_HALF_LIFE, "form_k": FORM_K,
                           "form_lookback_days": FORM_LOOKBACK, "excluded_levels": list(EXCLUDED_LEVELS),
                           "discovery": DISCOVERY, "replication": REPLICATION}
    SUMMARY.write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    log(f"wrote {TRIPLES.name}: {len(tri)} triples; {json.dumps(summary['triples_final'])}")


if __name__ == "__main__":
    main()
