"""Round 2, the body analyst's result-free diagnostics of f20-f28 (builders.md step 5): coverage per tour x window, the
distribution of x and of every block member, novelty R^2 on the 58 inputs (2014-2021 rows; the batch's own least
squares), the nearest inputs and their correlations, member correlations, data-quality shares (imputed loads, known
continents and time zones, indoor statuses, trait evidence) and I-052's sensitivities. The panel's result column is
dropped on load; seasons stop at 2024 (2025-2026 only as the row counts of round1/test_counts.json).

Writes data/studies/feature_interactions/round2/body/diagnostics.json.
Run: ./python.sh src/eda/feature_interactions/round2/body/diagnostics.py
"""
from __future__ import annotations

import importlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.features import f20_fatigue as F  # noqa: E402

OUT = C.OUT / "round2" / "body"
MODULES = ["f20_fatigue", "f21_constitution", "f22_demand", "f23_arrival", "f24_onsite", "f25_switch",
           "f26_impairment", "f27_home", "f28_state"]
MEMBERS = {"B-LOAD": ("f20_fatigue", "load_members"), "B-PREV": ("f20_fatigue", "prev_members"),
           "B9a": ("f21_constitution", "b9a_members"), "B9b": ("f22_demand", "b9b_members"),
           "B10": ("f23_arrival", "b10_members"), "B11": ("f24_onsite", "b11_members"),
           "B-INJ": ("f26_impairment", "inj_members"), "B-STATE": ("f28_state", "state_members")}


def r2_batch(P: pd.DataFrame, x: np.ndarray) -> float:
    """The batch's novelty R^2: least squares of x on the raw 58 inputs (missing -> 0), 2014-2021 rows."""
    X58 = np.nan_to_num(P[[c for c in P.columns if c.startswith("in_")]].to_numpy(float))
    ok = F.disc(P) & np.isfinite(x)
    if ok.sum() < 100 or np.var(x[ok]) == 0:
        return np.nan
    beta, *_ = np.linalg.lstsq(X58[ok], x[ok], rcond=None)
    return float(1 - np.var(x[ok] - X58[ok] @ beta) / np.var(x[ok]))


def coverage(P: pd.DataFrame, x: np.ndarray) -> dict:
    X = np.asarray(x, float).reshape(len(P), -1)
    out = {}
    for t in C.TOURS:
        for w, ss in (("2014-21", C.DISCOVERY), ("2022-24", C.REPLICATION)):
            m = (P["tour"] == t).to_numpy() & P["season"].isin(ss).to_numpy()
            fin = np.isfinite(X[m]).all(axis=1)
            out[f"{t} {w}"] = {"finite": round(float(fin.mean()), 4),
                               "nonzero": round(float((fin & (np.abs(X[m]).sum(axis=1) > 0)).mean()), 4)}
    return out


def dist(P: pd.DataFrame, x: np.ndarray) -> dict:
    v = np.asarray(x, float)[F.disc(P)]
    v = v[np.isfinite(v)]
    q = np.quantile(v, [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]) if len(v) else [np.nan] * 7
    return {"sd": round(float(np.std(v)), 5), "q01_q99": [round(float(a), 4) for a in q],
            "zero_share": round(float(np.mean(v == 0)), 4)}


def nearest_r(P: pd.DataFrame, x: np.ndarray, names: list[str]) -> dict:
    X = np.asarray(x, float).reshape(len(P), -1)
    out = {}
    for n in names:
        v = F.col(P, f"in_{n}")
        rs = []
        for j in range(X.shape[1]):
            m = F.disc(P) & np.isfinite(X[:, j]) & np.isfinite(v)
            rs.append(round(float(np.corrcoef(X[m, j], v[m])[0, 1]), 3) if m.sum() > 100 else np.nan)
        out[n] = rs if len(rs) > 1 else rs[0]
    return out


def one(P: pd.DataFrame, L: pd.DataFrame, mod, spec) -> tuple[dict, pd.DataFrame]:
    new = spec["prepare"](P, L) if spec.get("prepare") else {}
    Q = P.assign(**new)
    r = spec["combine"](Q)
    x = np.asarray(r["x"], float)
    X = x.reshape(len(P), -1)
    near = F.nearest(Q, x, exclude={n[3:] for n in r["control_names"] if n.startswith("in_")})
    res = {"hid": spec["hid"], "module": mod.__name__.rsplit(".", 1)[-1], "coverage": coverage(Q, x),
           "dist": [dist(Q, X[:, j]) for j in range(X.shape[1])] if X.shape[1] > 1 else dist(Q, x),
           "novelty_r2": [round(r2_batch(Q, X[:, j]), 4) for j in range(X.shape[1])] if X.shape[1] > 1
           else round(r2_batch(Q, x), 4),
           "controls": r["control_names"], "nearest_selected": near,
           "nearest_r": nearest_r(Q, x, [n[3:] for n in r["control_names"] if n.startswith("in_")])}
    if spec["hid"] in MEMBERS:
        m = importlib.import_module(f"src.eda.feature_interactions.features.{MEMBERS[spec['hid']][0]}")
        M = {k: v for k, v in getattr(m, MEMBERS[spec["hid"]][1])(Q).items() if not k.startswith("_")}
        res["members"] = {k: {"coverage": coverage(Q, v), "dist": dist(Q, v), "novelty_r2": round(r2_batch(Q, v), 4),
                              "corr_with_x": round(float(pd.Series(v[F.disc(Q)]).corr(pd.Series(x[F.disc(Q)]))), 3)}
                          for k, v in M.items()}
        keys = list(M)
        res["member_corr"] = {f"{a} ~ {b}": round(float(pd.Series(M[a][F.disc(Q)]).corr(pd.Series(M[b][F.disc(Q)]))), 3)
                              for i, a in enumerate(keys) for b in keys[i + 1:]}
    return res, Q


def by_window(P: pd.DataFrame, v: np.ndarray) -> dict:
    """Mean of v per tour x window (2014-2021, 2022-2024)."""
    out = {}
    for t in C.TOURS:
        for w, ss in (("2014-21", C.DISCOVERY), ("2022-24", C.REPLICATION)):
            m = (P["tour"] == t).to_numpy() & P["season"].isin(ss).to_numpy() & np.isfinite(v)
            out[f"{t} {w}"] = round(float(np.mean(v[m])), 4) if m.any() else None
    return out


def extra(P: pd.DataFrame, L: pd.DataFrame, frames: dict) -> dict:
    """Data-quality shares and sensitivities (result-free)."""
    from src.eda.feature_interactions.features import f23_arrival as G
    from src.eda.feature_interactions.features import f28_state as ST
    H = F.history(P, L)
    pa, pb = F.positions(P, H)
    both = (pa >= 0) & (pb >= 0)
    rd = lambda v: (v[np.maximum(pa, 0)], v[np.maximum(pb, 0)])    # noqa: E731
    out = {"rows_in_history_both": by_window(P, both.astype(float))}
    # loads: imputed share of the kernel, and I-052's sensitivities
    f3, imp = F.fat(H)
    ia, ib = rd(imp)
    out["fat_imputed_share_gt_half_either"] = by_window(P, (np.fmax(ia, ib) > 0.5).astype(float))
    sens = {}
    base = rd(f3)[0] - rd(f3)[1]
    for name, (tau, unit) in {"tau1.5": (1.5, "load"), "tau5": (5.0, "load"), "fit21": (21.0, "load"),
                              "games3": (3.0, "games")}.items():
        v, _ = F.fat(H, tau, unit)
        d = rd(v)[0] - rd(v)[1]
        m = F.disc(P) & np.isfinite(d) & np.isfinite(base)
        sens[name] = round(float(np.corrcoef(base[m], d[m])[0, 1]), 3)
    off = F.off_site(H)
    d = rd(off)[0] - rd(off)[1]
    m = F.disc(P) & np.isfinite(d)
    sens["off3 (B-LOAD member)"] = round(float(np.corrcoef(base[m], d[m])[0, 1]), 3)
    out["dfat3_corr_with"] = sens
    # geography at the model rows
    G.arrival(H)
    for name in ("cont", "trav", "dz", "away"):
        v = H[name].to_numpy(object if name == "cont" else float)
        known = np.array([isinstance(x, str) for x in v]) if name == "cont" else np.isfinite(v.astype(float))
        ka, kb = rd(known.astype(float))
        out[f"known_both_{name}"] = by_window(P, ka * kb)
    dz, gap = H["dz"].to_numpy(float), H["gap"].to_numpy(float)
    trig = ((np.abs(dz) >= 5) & (gap <= 5)).astype(float)
    ta, tb = rd(trig)
    out["jetlag_trigger_either"] = by_window(P, np.fmax(ta, tb))
    dzz = H["dz_zone"].to_numpy(float)
    za, zb = rd(np.nan_to_num(dz)), rd(np.nan_to_num(dzz))
    m = F.disc(P)
    out["dz_proxy_vs_zone_corr"] = round(float(np.corrcoef((za[0] - za[1])[m], (zb[0] - zb[1])[m])[0, 1]), 3)
    # INFO-1's premise: does the IOS state at m already hold X's uncounted previous match k?
    one = ST.one_step(H)
    dO = H["_info1_dO"].to_numpy(float)
    Om = np.r_[P["ios_srfO_spw_a"].to_numpy(float), P["ios_srfO_spw_b"].to_numpy(float)]
    pos = np.r_[pa, pb]
    k = pos - 1
    ok = (pos >= 1)
    kk = np.maximum(k, 0)
    sameP = ok & (H["pid"].to_numpy()[kk] == H["pid"].to_numpy()[np.maximum(pos, 0)])
    S = ST.ios_states(H)
    Ok = S["O"][kk]
    surf_same = H["surface"].astype(str).to_numpy()[kk] == H["surface"].astype(str).to_numpy()[np.maximum(pos, 0)]
    unc = H["lf"].to_numpy(float)[kk] + 1 > H["es"].to_numpy(float)[np.maximum(pos, 0)]
    res = {}
    for tag, sel in (("uncounted", unc), ("counted", ~unc)):
        mm = sameP & surf_same & sel & np.isfinite(Om) & np.isfinite(Ok) & np.isfinite(dO[kk])
        x, y = dO[kk][mm], (Om - Ok)[mm]
        res[tag] = {"n": int(mm.sum()), "corr": round(float(np.corrcoef(x, y)[0, 1]), 3),
                    "slope": round(float(np.polyfit(x, y, 1)[0]), 3)}
    out["info1_premise_check"] = res
    tot, flag, cnt = ST.uncounted(H)
    ca, cb = rd(cnt)
    out["info1_uncounted_either"] = by_window(P, (np.fmax(ca, cb) > 0).astype(float))
    fa_, fb_ = rd(flag)
    out["info1_update_missing_either"] = by_window(P, np.fmax(fa_, fb_))
    return out


def main() -> int:
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=C.REPLICATION[-1]).drop(columns=["a_won"])
    L = long_table()
    out, frames = {}, {}
    for name in MODULES:
        mod = importlib.import_module(f"src.eda.feature_interactions.features.{name}")
        for spec in mod.HYPOTHESES:
            res, Q = one(P, L, mod, spec)
            out[spec["hid"]] = res
            frames[spec["hid"]] = Q
            C.log(f"{spec['hid']}: R2 {res['novelty_r2']}; nearest {res['nearest_selected']}")
    out["_extra"] = extra(P, L, frames)
    out["_test_rows_2025_2026"] = json.loads((C.OUT / "round1" / "test_counts.json").read_text())["model_rows_2025_2026"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagnostics.json").write_text(json.dumps(out, indent=1, default=str))
    C.log("written diagnostics.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
