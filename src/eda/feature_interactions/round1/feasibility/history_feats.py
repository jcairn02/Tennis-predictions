"""Per-player, pre-match quantities from each player's own earlier matches (round-1 feasibility; result-free).

Every value at a row uses only the same player's strictly earlier rows (own order, safe by construction under the match
clock), read at the model matches by base.at_model. Approximations adequate for coverage and R-squared, not the
analysts' final builds: windows use the clock's lf of earlier matches against this match's es.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _kernel(pid, es, lf, load, tau):
    """sum over the player's earlier rows j of load_j * exp(-(es_i - lf_j)/tau), recursively (own order)."""
    n = len(pid)
    out = np.zeros(n)
    acc, prev_es = 0.0, 0.0
    for i in range(n):
        if i == 0 or pid[i] != pid[i - 1]:
            acc, prev_es = 0.0, es[i]
            out[i] = 0.0
            continue
        gap_prev = max(es[i] - prev_es, 0.0)
        add = load[i - 1] * np.exp(-max(es[i] - lf[i - 1], 0.0) / tau) if np.isfinite(load[i - 1]) else 0.0
        acc = acc * np.exp(-gap_prev / tau) + add
        prev_es = es[i]
        out[i] = acc
    return out


def _window(pid, es, lf, val, w):
    """sum of val over the player's earlier rows whose lf lies in [es - w, es); also the count of missing val there."""
    key_l = pid.astype(np.int64) * 10_000_000 + np.floor(lf).astype(np.int64)
    o = np.argsort(key_l, kind="stable")
    ks = key_l[o]
    v = np.nan_to_num(val[o])
    miss = (~np.isfinite(val[o])).astype(float)
    cv, cm = np.concatenate([[0.0], np.cumsum(v)]), np.concatenate([[0.0], np.cumsum(miss)])
    hi = np.searchsorted(ks, pid.astype(np.int64) * 10_000_000 + np.floor(es).astype(np.int64), side="left")
    lo = np.searchsorted(ks, pid.astype(np.int64) * 10_000_000 + np.floor(es - w).astype(np.int64), side="left")
    return cv[hi] - cv[lo], cm[hi] - cm[lo], hi - lo


def build(L: pd.DataFrame) -> pd.DataFrame:
    pid = pd.factorize(L["player_id"])[0]
    es, lf = L["es"].to_numpy(float), L["lf"].to_numpy(float)
    played = L["played"].to_numpy(bool)
    mins = np.where(played, L["minutes"].to_numpy(float), 0.0)
    games = np.where(played, L["games"].to_numpy(float), 0.0)
    H = pd.DataFrame(index=L.index)
    g = L.groupby("player_id", sort=False)
    # load kernels and windows (minutes and games); a window is complete when no earlier match in it lacks the unit
    for tau in (3.0, 28.0):
        H[f"fat_min_{tau:g}"] = np.log1p(_kernel(pid, es, lf, mins, tau))
        H[f"fat_games_{tau:g}"] = np.log1p(_kernel(pid, es, lf, games, tau))
    for w in (7, 14, 28):
        s, m, n = _window(pid, es, lf, mins, w)
        H[f"min_{w}d"] = np.where(m < 0.5, s, np.nan)
        H[f"n_{w}d"] = n
        sg, mg, _ = _window(pid, es, lf, games, w)
        H[f"games_{w}d"] = np.where(mg < 0.5, sg, np.nan)
    # on-site: earlier matches at this event (same tournament id)
    H["onsite_n"] = L.groupby(["player_id", "tournament_id"], sort=False).cumcount().to_numpy(float)
    H["rest_min"] = L["rest_min"].to_numpy(float)
    # previous match facts (the player's own previous match)
    best = L["best_of"].to_numpy(float)
    deciding = (L["sets"].to_numpy(float) >= np.where(best == 5, 5, 3)).astype(float)
    deciding[~np.isfinite(L["sets"].to_numpy(float))] = np.nan
    H["prev_deciding"] = pd.Series(deciding, index=L.index).groupby(L["player_id"]).shift(1).to_numpy()
    H["prev_won"] = g["won"].shift(1).astype(float).to_numpy()
    H["prev_tid"] = g["tournament_id"].shift(1).to_numpy()
    H["prev_round"] = g["round"].shift(1).to_numpy()
    H["prev_level"] = g["level"].shift(1).to_numpy()
    indoor = L["indoor"].map({True: 1.0, False: 0.0}).astype(float)
    H["prev_indoor"] = indoor.groupby(L["player_id"]).shift(1).to_numpy()
    H["prev_surface"] = g["surface"].shift(1).to_numpy()
    H["prev_retired_self"] = g["retired_self"].shift(1).astype(float).to_numpy()
    # retirement and walkover-given history: last 730 days (counts of matches and of own retirements/walkovers given)
    gave = (L["retired_self"] | (L["walkover"] & ~L["won"])).to_numpy(float)
    r730, _, n730 = _window(pid, es, lf, gave, 730)
    H["ret_rate_730"] = (r730 + 0.5) / (n730 + 20.0)
    H["gap_days"] = L["rest_days"].to_numpy(float)
    # season odometer: matches played earlier this calendar year
    year = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    H["odo_season"] = L.assign(_y=year).groupby(["player_id", "_y"], sort=False).cumcount().to_numpy(float)
    # team ties: decayed load from TEAM matches (games)
    team = (L["level"] == "TEAM").to_numpy() & played
    H["team_load"] = np.log1p(_kernel(pid, es, lf, np.where(team, games, 0.0), 7.0))
    # titles (won finals at main-tour levels) and Slam quarter-finals or better, before the match
    main = L["level"].isin(["GS", "FIN", "T1000", "T500", "T250"]).to_numpy() & ~L["qualifying"].to_numpy(bool)
    title = (main & (L["round"] == "F").to_numpy() & L["won"].to_numpy(bool)).astype(float)
    slam_qf = ((L["level"] == "GS").to_numpy() & ~L["qualifying"].to_numpy(bool)
               & (L["round_order"].to_numpy() >= 15)).astype(float)
    for name, v in (("titles", title), ("slam_qf", slam_qf)):
        H[f"{name}_before"] = pd.Series(v, index=L.index).groupby(L["player_id"]).cumsum().to_numpy() - v
    # head to head: earlier meetings and wins against this opponent
    pair = L.groupby(["player_id", "opponent_id"], sort=False)
    H["h2h_n"] = pair.cumcount().to_numpy(float)
    w = L["won"].astype(float)
    H["h2h_w"] = (w.groupby([L["player_id"], L["opponent_id"]]).cumsum() - w).to_numpy()
    # the previous event's wins (a deep run last time out), carried through this event's rounds
    ev = L[["player_id", "tournament_id"]].assign(won=w.to_numpy(),
                                                  title=((L["round"] == "F") & L["won"]).to_numpy(float))
    evt = ev.groupby(["player_id", "tournament_id"], sort=False).agg(wins=("won", "sum"), title=("title", "max")).reset_index()
    evt["prev_event_wins"] = evt.groupby("player_id")["wins"].shift(1)
    evt["prev_event_title"] = evt.groupby("player_id")["title"].shift(1)
    back = ev.merge(evt[["player_id", "tournament_id", "prev_event_wins", "prev_event_title"]],
                    on=["player_id", "tournament_id"], how="left")
    H["prev_event_wins"] = back["prev_event_wins"].to_numpy(float)
    H["prev_event_title"] = back["prev_event_title"].to_numpy(float)
    # pace: seconds per point of each earlier played match, decayed mean (half-life 52 weeks), NaN without any
    pts = L["tpw_d"].to_numpy(float)
    spp = np.where(played & (pts > 0), L["minutes"].to_numpy(float) * 60.0 / pts, np.nan)
    tau = 364.0 / np.log(2.0)
    num = _kernel(pid, es, lf, np.where(np.isfinite(spp), spp, 0.0), tau)
    den = _kernel(pid, es, lf, np.isfinite(spp).astype(float), tau)
    H["spp_mean"] = np.where(den > 0.05, num / np.maximum(den, 1e-12), np.nan)
    # layoffs: the gap before this match, matches since the last gap over 42 days, and how that layoff began
    gap = H["gap_days"].to_numpy()
    long_gap = np.nan_to_num(gap) > 42
    grp = pd.Series(long_gap.astype(int)).groupby(pid).cumsum().to_numpy()
    H["n_since_layoff"] = pd.Series(np.ones(len(L))).groupby([pid, grp]).cumcount().to_numpy(float)
    H.loc[grp == 0, "n_since_layoff"] = np.nan
    gap_at = pd.Series(np.where(long_gap, gap, np.nan)).groupby([pid, grp]).transform("first").to_numpy()
    H["layoff_days"] = gap_at
    inj_at = pd.Series(np.where(long_gap, H["prev_retired_self"].to_numpy(), np.nan)).groupby([pid, grp]) \
        .transform("first").to_numpy()
    H["layoff_injury"] = inj_at
    return H
