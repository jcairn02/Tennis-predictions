"""Design scratch (agent 2): the result-free mechanism gate, men, seasons 2022-2023 only.

Question: does the player's pre-match speed state predict his serve performance in the match (box-score statistic
targets, never the result) beyond his own recent box-score serve form, his long-run speed level and the opponent?

Targets (per player-match, Stage 0 box score; no result column is read):
    ace   aces per serve point            first_won   first-serve points won per first serve in
    spw   serve points won per serve point (a statistic target allowed <= 2023 by the brief)
Speed features (own history only, frozen constants tuned on speeds <= 2022, modeller_state_<policy>.json):
    f_hat     Kalman posterior mean of the fast state, projected to the match day (km/h)
    dev_hat   Kalman predicted deviation from the 364-day mean (L_hat + f_hat - c52)
    x_raw     the registered 14-day minus 364-day mean (raw km/h; 0 where missing, with a missing flag)
Controls (own history, earlier events + earlier rounds): the player's 364-day and two-week-half-life box-score rate of
the same statistic, his long-run speed level (L_hat, or the 364-day mean), the opponent's 364-day rate conceded (aces
against / first-serve points won against / serve points won against), surface and level.

Model: weighted least squares of the rate on the standardised speed feature plus controls (weights = the target's
denominator); the speed coefficient is reported in percentage points per SD of the feature with a 95% 28-day-block
bootstrap interval. Positive = a player whose speed is above his norm does better on serve than his form says.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_gate.py [ks_first|pm_first]
Writes data/studies/serve_speed_tabpfn/design/modeller_gate_<policy>.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import modeller_common as M  # noqa: E402
from src.eda.serve_speed_tabpfn.design import modeller_state as S  # noqa: E402

YEARS = (2022, 2023)
LEVELS = ("GS", "T1000", "T500", "T250", "FIN", "CH")
STATS = {"ace": ("ace_n", "ace_d"), "first_won": ("first_won_n", "first_won_d"), "spw": ("spw_n", "spw_d")}
HL = 14.0


def box_history(years=(2019, 2023), tour: str = "atp") -> pd.DataFrame:
    b = M.box_rows(years)
    b = b[b["tour"].eq(tour) & b["has_box"].astype(bool)].copy()
    t = pd.read_parquet(M.TIMING, columns=["match_id", "obs"])
    b = b.merge(t, on="match_id", how="left")
    b = b[b["obs"].notna()]
    return b


def own_rates(b: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    """For each target row (player-match), the player's 364-day sums and two-week-half-life weighted sums of each
    statistic over earlier matches (earlier events, earlier rounds), plus what his opponents did against him over 364
    days (for the opponent control, looked up from the opponent's own rows)."""
    b = b.sort_values(["player_id", "tdate", "tournament_id", "round_order"], kind="mergesort")
    # what the player conceded: the opponent's numbers in the same match
    opp = b[["match_id", "player_id"] + [c for v in STATS.values() for c in v]].rename(
        columns={"player_id": "opponent_id", **{c: "c_" + c for v in STATS.values() for c in v}})
    b = b.merge(opp, on=["match_id", "opponent_id"], how="left")
    cols = [c for v in STATS.values() for c in v]
    ccols = ["c_" + c for c in cols]
    res = {}
    tg = targets.groupby("player_id").indices
    for pid, g in b.groupby("player_id", sort=False):
        if pid not in tg:
            continue
        td, tid, ro, ob = (g["tdate"].to_numpy(), g["tournament_id"].to_numpy(), g["round_order"].to_numpy(),
                           g["obs"].to_numpy())
        V = g[cols].to_numpy(float)
        C = g[ccols].to_numpy(float)
        V, C = np.nan_to_num(V), np.nan_to_num(C)
        for i in tg[pid]:
            r = targets.iloc[i]
            earlier = (td < r["tdate"]) | ((tid == r["tournament_id"]) & (ro < r["round_order"]))
            age = r["obs"] - ob
            w52 = earlier & (age <= 364)
            if not w52.any():
                continue
            ew = np.where(earlier & (age >= 0), np.exp2(-np.maximum(age, 0) / HL), 0.0)
            res[i] = np.concatenate([V[w52].sum(0), (V * ew[:, None]).sum(0), C[w52].sum(0)])
    names = [f"s52_{c}" for c in cols] + [f"ew_{c}" for c in cols] + [f"c52_{c}" for c in cols]
    out = pd.DataFrame.from_dict(res, orient="index", columns=names)
    return out.reindex(range(len(targets)))


def wls(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    sw = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    return beta


def main() -> None:
    global YEARS, LEVELS
    policy = sys.argv[1] if len(sys.argv) > 1 else "ks_first"
    tour = sys.argv[2] if len(sys.argv) > 2 else "atp"
    if tour == "wta":                       # women: Slams only (no WTA tour-level speeds)
        YEARS, LEVELS = (2016, 2023), ("GS",)
    allst = json.loads((M.OUT / f"modeller_state_{policy}.json").read_text(encoding="utf-8"))["tours"]
    st = allst[tour]
    prm, nu = dict(st["kalman_tuned"]["params"]), st["kalman_tuned"]["nu"]
    mendyn = len(sys.argv) > 3 and sys.argv[3] == "mendyn"
    if mendyn:                              # the men's dynamics (half-life, state variance, drift), own noise
        for k in ("hl", "s2f", "q"):
            prm[k] = allst["atp"]["kalman_tuned"]["params"][k]
        tour_tag = f"{tour}_mendyn"
    else:
        tour_tag = tour
    M.log(f"gate ({policy}, {tour}); Kalman {prm} nu {nu}")
    p = M.panel(policy)
    p = p[(p["tour"] == tour) & (p["year"] <= YEARS[1])].copy()
    off = S.offsets(p, S.SPLIT[tour][0])
    p = S.centre(p, off, nu)
    b = box_history((2013, 2023), tour)
    tg = b[b["year"].between(*YEARS) & b["level"].isin(LEVELS)].reset_index(drop=True)
    for s, (n, d) in STATS.items():
        tg = tg[tg[d] > 0]
    tg = tg.reset_index(drop=True)
    tg["tour"] = tour
    M.log(f"{len(tg)} target player-matches with box scores, {YEARS}")
    kf = S.kalman(p, tg[["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]], prm)
    tg = tg.join(kf)
    # x_raw and the 364-day mean from the timed panel, at these targets
    tw = speed_windows(p, tg)
    tg = tg.join(tw)
    tg["x_raw0"] = tg["x_raw"].fillna(0.0)
    tg["x_raw_miss"] = tg["x_raw"].isna().astype(float)
    tg["dev_hat"] = (tg["L_hat"] + tg["f_hat"] - tg["c52"]).where(tg["c52"].notna(), 0.0).fillna(0.0)
    tg["drift"] = (tg["L_hat"] - tg["c52"]).where(tg["c52"].notna(), 0.0).fillna(0.0)
    orates = own_rates(b, tg)
    tg = tg.join(orates)
    # opponent's 364-day conceded rates: the opponent's own row in the same match
    opp_cols = [c for c in tg.columns if c.startswith("c52_")]
    oppv = tg[["match_id", "player_id"] + opp_cols].rename(columns={"player_id": "opponent_id"})
    tg = tg.merge(oppv, on=["match_id", "opponent_id"], how="left", suffixes=("", "_opp"))
    tg["block"] = (tg["obs"] // 28).astype(int)
    # does the player have a timed earlier round at the same event? (conditions shared with the target) or is his
    # recent speed history from earlier events only (a cross-event state)?
    same_ev = p[["player_id", "tournament_id", "round_order"]].rename(columns={"round_order": "ro_h"})
    x = tg[["player_id", "tournament_id", "round_order"]].reset_index().merge(same_ev, on=["player_id", "tournament_id"])
    x = x[x["ro_h"] < x["round_order"]]
    tg["same_event_hist"] = tg.index.isin(x["index"].unique())
    out = {"policy": policy, "tour": tour, "years": YEARS, "kalman": prm, "nu": nu, "targets": int(len(tg)), "results": {}}
    feats = {"f_hat": "f_hat", "drift": "drift", "dev_hat": "dev_hat", "x_raw": "x_raw0"}
    rng = np.random.default_rng(7)
    for s, (n, d) in STATS.items():
        y = tg[n] / tg[d]
        r52 = tg[f"s52_{n}"] / tg[f"s52_{d}"]
        rew = tg[f"ew_{n}"] / tg[f"ew_{d}"]
        # opponent's conceded rate: what the opponent's opponents did on this statistic
        oc = tg[f"c52_{n}_opp"] / tg[f"c52_{d}_opp"]
        base_ok = r52.notna() & rew.notna() & oc.notna() & tg["L_hat"].notna() & y.notna()
        for subset in ("all", "timed_within_28d", "within_28d_same_event", "within_28d_earlier_events_only"):
            ok = base_ok & ((tg["hist"] > 0) & (tg["f_sd"] < np.sqrt(prm["s2f"]) * 0.999)
                            if subset != "all" else True)
            if subset != "all":
                ok &= tg["last_age"].le(28)
            if subset == "within_28d_same_event":
                ok &= tg["same_event_hist"]
            elif subset == "within_28d_earlier_events_only":
                ok &= ~tg["same_event_hist"]
            g = tg[ok]
            yv, wv = y[ok].to_numpy(), g[d].to_numpy(float)
            surf = pd.get_dummies(g["surface"].fillna("Hard"), drop_first=True).to_numpy(float)
            lev = pd.get_dummies(g["level"], drop_first=True).to_numpy(float)
            ctrl = np.column_stack([np.ones(len(g)), r52[ok], rew[ok], oc[ok], g["L_hat"], surf, lev])
            res = {"rows": int(len(g)), "mean_rate": float(np.average(yv, weights=wv))}
            for fname, col in feats.items():
                F = g[col].to_numpy(float)
                sdF = F.std()
                if sdF == 0:
                    continue
                Fz = F / sdF
                for ctl in ("controls", "no_box_form"):
                    X = np.column_stack([Fz, ctrl if ctl == "controls" else np.column_stack(
                        [np.ones(len(g)), g["L_hat"], oc[ok], surf, lev])])
                    if fname == "x_raw":
                        X = np.column_stack([X, g["x_raw_miss"]])
                    beta = wls(X, yv, wv)
                    bl = g["block"].to_numpy()
                    ub = np.unique(bl)
                    ix = {u: np.flatnonzero(bl == u) for u in ub}
                    bs = []
                    for _ in range(300):
                        sel = np.concatenate([ix[u] for u in rng.choice(ub, len(ub))])
                        bs.append(wls(X[sel], yv[sel], wv[sel])[0])
                    res[f"{fname}|{ctl}"] = {"pp_per_sd": 100 * float(beta[0]),
                                             "ci": [100 * float(np.percentile(bs, 2.5)), 100 * float(np.percentile(bs, 97.5))],
                                             "feature_sd": float(sdF)}
            # joint: fast state and drift together, with the controls
            fz, dz = g["f_hat"].to_numpy(float), g["drift"].to_numpy(float)
            if fz.std() > 0 and dz.std() > 0:
                X = np.column_stack([fz / fz.std(), dz / dz.std(), ctrl])
                beta = wls(X, yv, wv)
                bl = g["block"].to_numpy()
                ub = np.unique(bl)
                ix = {u: np.flatnonzero(bl == u) for u in ub}
                bs = np.array([wls(X[s_], yv[s_], wv[s_])[:2] for s_ in
                               (np.concatenate([ix[u] for u in rng.choice(ub, len(ub))]) for _ in range(300))])
                res["joint|f_hat"] = {"pp_per_sd": 100 * float(beta[0]),
                                      "ci": [100 * float(np.percentile(bs[:, 0], 2.5)), 100 * float(np.percentile(bs[:, 0], 97.5))]}
                res["joint|drift"] = {"pp_per_sd": 100 * float(beta[1]),
                                      "ci": [100 * float(np.percentile(bs[:, 1], 2.5)), 100 * float(np.percentile(bs[:, 1], 97.5))]}
            # the box-score two-week form's own coefficient (for scale): pp per SD of the EW rate
            X = np.column_stack([ctrl])
            beta = wls(X, yv, wv)
            res["ew_form_pp_per_sd"] = 100 * float(beta[2] * rew[ok].std())
            res["r52_form_pp_per_sd"] = 100 * float(beta[1] * r52[ok].std())
            out["results"][f"{s}|{subset}"] = res
            M.log(f"{s} {subset}: rows {len(g)}; " + "; ".join(
                f"{k} {v['pp_per_sd']:+.3f} [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}]" for k, v in res.items()
                if isinstance(v, dict)))
    (M.OUT / f"modeller_gate_{policy}_{tour_tag}.json").write_text(json.dumps(out, indent=1, default=float) + "\n",
                                                        encoding="utf-8")


def speed_windows(p: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    """x_raw (raw km/h), the centred 364-day mean c52 and the age of the last timed match, for arbitrary targets."""
    p = p.sort_values(["player_id", "tdate", "tournament_id", "round_order"], kind="mergesort")
    gi = {pid: g for pid, g in p.groupby("player_id", sort=False)}
    res = np.full((len(tg), 3), np.nan)
    for i, r in enumerate(tg[["player_id", "tdate", "tournament_id", "round_order", "obs"]].itertuples(index=False)):
        g = gi.get(r.player_id)
        if g is None:
            continue
        td, tid, ro, ob = (g["tdate"].to_numpy(), g["tournament_id"].to_numpy(), g["round_order"].to_numpy(),
                           g["obs"].to_numpy())
        earlier = (td < r.tdate) | ((tid == r.tournament_id) & (ro < r.round_order))
        age = r.obs - ob
        w52 = earlier & (age <= 364)
        if not w52.any():
            continue
        y, z, n = g["y"].to_numpy(), g["z"].to_numpy(), g["n"].to_numpy()
        m52 = (y[w52] * n[w52]).sum() / n[w52].sum()
        c52 = (z[w52] * n[w52]).sum() / n[w52].sum()
        w2 = earlier & (age <= 14)
        x = (y[w2] * n[w2]).sum() / n[w2].sum() - m52 if w2.any() else np.nan
        res[i] = (x, c52, age[w52].min())
    return pd.DataFrame(res, columns=["x_raw", "c52", "last_age"], index=tg.index)


if __name__ == "__main__":
    main()
