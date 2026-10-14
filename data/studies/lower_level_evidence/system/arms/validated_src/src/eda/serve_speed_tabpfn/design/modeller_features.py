"""Design scratch (agent 2): the candidate speed-state columns on the model frame (2013-2026), their coverage and
distributions, and a black-box leak probe. Feature values only: no result, no statistic target, no price is read.
For 2024-2026 only values, counts and distributions are computed.

Constants (frozen; nothing is fitted here except the system offsets, from seasons <= 2023 only):
    Kalman (modeller_state_<policy>.json, tuned on speeds <= 2022 by one-step-ahead prediction, validated on 2023)
    system offsets: modeller_state.offsets(panel, 2023)

Side values (player before the match; own history: earlier events and earlier rounds of the same event):
    f_hat    posterior mean of the fast state, projected to the match day (km/h); 0 with no timed history
    f_sd     its posterior SD (sqrt(s2f) with no recent timed history)
    dev_hat  L_hat + f_hat - c52: predicted speed in this match minus the 364-day mean (0 where no 364-day history)
    x_raw    the registered statistic (raw 14-day minus 364-day mean; missing without a timed match in 14 days)
Match columns: diff = A - B (spd_dev, spd_f, x_raw); pair = (f_sd_a, f_sd_b).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_features.py [ks_first|pm_first]
Writes data/studies/serve_speed_tabpfn/design/modeller_features_<policy>.parquet and modeller_features_<policy>.json
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
from src.eda.serve_speed_tabpfn.design.modeller_gate import speed_windows  # noqa: E402

FROZEN = 2023


def side_targets() -> pd.DataFrame:
    f = pd.read_parquet(M.FRAME, columns=["match_id", "tour", "season"])
    k = M.match_keys(f["match_id"])
    rows = []
    for s, col in (("A", "player_a_id"), ("B", "player_b_id")):
        x = f.merge(k.drop(columns=["tour"]), on="match_id", how="left")
        x["side"], x["player_id"] = s, x[col]
        rows.append(x)
    t = pd.concat(rows, ignore_index=True)
    return t


def build(p: pd.DataFrame, prm: dict, tg: pd.DataFrame) -> pd.DataFrame:
    ok = tg["player_id"].notna() & tg["obs"].notna()
    out = pd.DataFrame(index=tg.index, columns=["f_hat", "f_sd", "L_hat", "L_sd", "hist", "x_raw", "c52", "last_age"],
                       dtype=float)
    out["f_hat"], out["f_sd"], out["hist"] = 0.0, np.sqrt(prm["s2f"]), 0.0
    for tour, g in tg[ok].groupby("tour"):
        pt = p[p["tour"] == tour]
        kf = S.kalman(pt, g[["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]], prm)
        out.loc[g.index, ["f_hat", "f_sd", "L_hat", "L_sd", "hist"]] = kf[["f_hat", "f_sd", "L_hat", "L_sd", "hist"]].to_numpy()
        sw = speed_windows(pt, g)
        out.loc[g.index, ["x_raw", "c52", "last_age"]] = sw[["x_raw", "c52", "last_age"]].to_numpy()
    out["dev_hat"] = (out["L_hat"] + out["f_hat"] - out["c52"]).where(out["c52"].notna(), 0.0).fillna(0.0)
    return out


def to_match(tg: pd.DataFrame, sv: pd.DataFrame) -> pd.DataFrame:
    x = pd.concat([tg[["match_id", "tour", "season", "side", "level", "round"]], sv], axis=1)
    a, b = x[x["side"] == "A"].set_index("match_id"), x[x["side"] == "B"].set_index("match_id")
    m = a[["tour", "season", "level", "round"]].copy()
    m["spd_dev"] = a["dev_hat"] - b["dev_hat"]
    m["spd_f"] = a["f_hat"] - b["f_hat"]
    m["spd_sd_a"], m["spd_sd_b"] = a["f_sd"], b["f_sd"]
    m["x_raw"] = a["x_raw"] - b["x_raw"]
    m["recent28_a"] = a["last_age"].le(28)
    m["recent28_b"] = b["last_age"].le(28)
    m["hist_a"], m["hist_b"] = a["hist"], b["hist"]
    return m.reset_index()


def probe(p: pd.DataFrame, prm: dict, tg: pd.DataFrame, n_cuts: int = 8, seed: int = 0) -> dict:
    """Speeds of every timed row at or after a random cut in Stage 0's order are replaced by noise (100-250 km/h) and
    the side values recomputed for 3,000 random frame player-matches (2021-2026); no target before the cut, nor at
    it, may move. A leaky control (each target's own match added to its history) must move at the cut."""
    rng = np.random.default_rng(seed)
    pool = tg.index[tg["season"].between(2021, 2026) & tg["obs"].notna() & tg["player_id"].notna()].to_numpy()
    sel = tg.loc[rng.choice(pool, 3000, replace=False)]
    base = build(p, prm, sel)
    orders = np.sort(sel["order"].unique())
    cb = ca = 0
    leaky_at = 0
    for c in rng.choice(orders[len(orders) // 5:], n_cuts, replace=False):
        q = p.copy()
        late = q["order"] >= c
        q.loc[late, "z"] = rng.uniform(100, 250, int(late.sum())) - 180.0
        q.loc[late, "y"] = q.loc[late, "z"] + 180.0
        got = build(q, prm, sel)
        diff = np.zeros(len(sel), dtype=bool)
        for col in ("f_hat", "f_sd", "dev_hat", "x_raw", "L_hat"):
            diff |= ~np.isclose(got[col].to_numpy(float), base[col].to_numpy(float), equal_nan=True)
        o = sel["order"].to_numpy()
        cb += int((diff & (o < c)).sum())
        ca += int((diff & (o == c)).sum())
        # leaky control: shift each target's round so that its own match counts as history
        lk = sel.copy()
        lk["round_order"] = lk["round_order"] + 0.5
        lb, lg = build(p, prm, lk), build(q, prm, lk)
        ld = ~np.isclose(lg["f_hat"].to_numpy(float), lb["f_hat"].to_numpy(float), equal_nan=True)
        leaky_at += int((ld & (o == c)).sum())
    # frozen offsets: recomputed with every row after the freeze perturbed -> unchanged
    q = p.copy()
    late = q["year"] > FROZEN
    q.loc[late, "y"] = rng.uniform(100, 250, int(late.sum()))
    o1, o2 = S.offsets(p, FROZEN), S.offsets(q, FROZEN)
    same = all(abs(o1[t][k] - o2[t][k]) < 1e-12 for t in o1 for k in o1[t] if not k.startswith("_"))
    return {"cuts": n_cuts, "targets": 3000, "changed_before_cut": cb, "changed_at_cut": ca,
            "leaky_control_changed_at_cut": leaky_at, "offsets_unchanged_when_post_freeze_speeds_perturbed": same}


def main() -> None:
    policy = sys.argv[1] if len(sys.argv) > 1 else "ks_first"
    st = json.loads((M.OUT / f"modeller_state_{policy}.json").read_text(encoding="utf-8"))["tours"]
    prm_by = {t: dict(st[t]["kalman_tuned"]["params"]) for t in st}
    nu_by = {t: st[t]["kalman_tuned"]["nu"] for t in st}
    # women: the men's dynamics (half-life, state variance, drift; identified on dense tour-level data), the women's own
    # noise and clipping (Slam-only data cannot separate the level from a slow state; modeller_gate_*_wta_mendyn.json)
    for k in ("hl", "s2f", "q"):
        prm_by["wta"][k] = prm_by["atp"][k]
    M.log(f"features ({policy}); Kalman {prm_by}; nu {nu_by}")
    p0 = M.panel(policy)
    off = S.offsets(p0, FROZEN)
    tg = side_targets()
    M.log(f"{len(tg)} frame player-matches; offsets frozen <= {FROZEN}: "
          f"{ {t: {k: round(v, 2) for k, v in o.items() if not k.startswith('_')} for t, o in off.items()} }")
    svs, ps = [], {}
    for tour in ("atp", "wta"):
        p = S.centre(p0[p0["tour"] == tour], off, nu_by[tour])
        ps[tour] = p
        svs.append(build(p, prm_by[tour], tg[tg["tour"] == tour]))
    sv = pd.concat(svs).reindex(tg.index)
    m = to_match(tg, sv)
    m.to_parquet(M.OUT / f"modeller_features_{policy}.parquet", index=False)
    M.log("coverage and distributions")
    cov = []
    for (t, y), g in m.groupby(["tour", "season"]):
        both28 = g["recent28_a"] & g["recent28_b"]
        cov.append({"tour": t, "season": int(y), "matches": int(len(g)),
                    "x_raw_present": int(g["x_raw"].notna().sum()),
                    "spd_f_nonzero": int((g["spd_f"].abs() > 0.05).sum()),
                    "both_timed_within_28d": int(both28.sum()),
                    "either_timed_within_28d": int((g["recent28_a"] | g["recent28_b"]).sum()),
                    "sd_spd_dev": float(g["spd_dev"].std()), "sd_spd_f": float(g["spd_f"].std()),
                    "sd_x_raw": float(g["x_raw"].std()),
                    "median_sd_a": float(g["spd_sd_a"].median())})
    cov = pd.DataFrame(cov)
    early = m[m["season"] <= 2023]
    pres = early[early["x_raw"].notna()]
    corr = {t: {"rows": int(len(g)), "corr_spd_dev_x_raw": float(np.corrcoef(g["spd_dev"], g["x_raw"])[0, 1]),
                "corr_spd_f_x_raw": float(np.corrcoef(g["spd_f"], g["x_raw"])[0, 1]),
                "corr_spd_dev_spd_f": float(np.corrcoef(g["spd_dev"], g["spd_f"])[0, 1])}
            for t, g in pres.groupby("tour")}
    pr = {}
    for tour in ("atp",):
        M.log("leak probe (men)")
        sub = tg[tg["tour"] == tour]
        pr[tour] = probe(ps[tour], prm_by[tour], sub)
        M.log(f"probe: {pr[tour]}")
    res = {"policy": policy, "frozen_offsets": off, "kalman": prm_by, "nu": nu_by,
           "coverage": cov.to_dict(orient="records"), "corr_where_x_raw_present_le2023": corr, "leak_probe": pr}
    (M.OUT / f"modeller_features_{policy}.json").write_text(json.dumps(res, indent=1, default=float) + "\n",
                                                            encoding="utf-8")
    print(cov.to_string(index=False))
    print(json.dumps(corr, indent=1))


if __name__ == "__main__":
    main()
