"""R2 robustness of the registered scores, seasons <= 2024 only (outcomes read through rt_common.disc_frame()).

A. The base: the registered per-tour slope + curvature against
   B1 a per-tour restricted cubic spline in L (5 knots), B2 the registered base + per-tour slopes by context (level,
   best of 5, round group, surface, indoor), B3 both: does any score borrow the price's shape or a context-specific
   miscalibration?
B. The odds source: 2018-24 matches priced by both Pinnacle (the odds input) and BetOnline: the registered fit on
   Pinnacle, on BetOnline's close, and on a hybrid that switches from Pinnacle to BetOnline mid-window as Look A does,
   with a pooled base (as registered) and a base by period; and BetOnline fresh vs stale last lines.
C. Retirements: the registered fit without matches that ended in a retirement (Stage 0's status, seasons <= 2024).
D. Joint fits: the five group scores together; G4 and G5 with and without their seed-related members.
E. Beyond the instance's own forecast (q_full), 2020-24, per group (the registered secondary on discovery seasons).
Writes robustness.csv and robustness.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rt_common as R  # noqa: E402


def rcs(x: np.ndarray, knots: np.ndarray) -> list[np.ndarray]:
    """Restricted cubic spline basis (Harrell) without the linear term's intercept: x, then k-2 nonlinear terms."""
    k = len(knots)
    t = knots
    out = [x]
    d = (t[-1] - t[0]) ** 2
    for j in range(k - 2):
        a = np.clip(x - t[j], 0, None) ** 3
        b = np.clip(x - t[-2], 0, None) ** 3 * (t[-1] - t[j]) / (t[-1] - t[-2])
        c = np.clip(x - t[-1], 0, None) ** 3 * (t[-2] - t[j]) / (t[-1] - t[-2])
        out.append((a - b + c) / d)
    return out


def spline_base(fr: pd.DataFrame) -> list[np.ndarray]:
    cols = []
    L = fr["L"].to_numpy(float)
    for t in ("atp", "wta"):
        m = (fr["tour"] == t).to_numpy()
        if not m.any():
            continue
        kn = np.quantile(L[m], [0.05, 0.275, 0.5, 0.725, 0.95])
        for c in rcs(L, kn)[1:]:             # the linear term comes from the base's per-tour slope
            cols.append(np.where(m, c, 0.0))
    return cols


def context_slopes(fr: pd.DataFrame) -> list[np.ndarray]:
    """Per-tour slope modifiers L x context dummy (reference: 250-level, best of 3, R32+ early rounds, hard, outdoor)."""
    L = fr["L"].to_numpy(float)
    lv = fr["in_level"].to_numpy(float)
    rd = fr["in_round"].to_numpy(float)
    dummies = {"slam": lv == 0, "finals": lv == 1, "m1000": lv == 2, "t500": lv == 3,   # men's Slams = best of 5
               "r_first2": np.isin(rd, [11, 12]), "r_r16": rd == 14, "r_qfplus": rd >= 15,
               "clay": fr["in_surface"].to_numpy(float) == 1, "grass": fr["in_surface"].to_numpy(float) == 2,
               "indoor": fr["in_indoor"].to_numpy(float) == 1}
    cols = []
    for t in ("atp", "wta"):
        m = (fr["tour"] == t).to_numpy()
        for k, dm in dummies.items():
            c = np.where(m & dm, L, 0.0)
            if np.count_nonzero(c) > 100:
                cols.append(c)
    return cols


def fit(fr, s, extra=None, curv=True, L=None):
    return R.beta_z(fr, s, extra=extra, curv=curv, L=L)


def main() -> int:
    reg = R.registry()
    d = R.disc_frame()
    mem, grp, omni, _ = R.scores(d, reg)
    sc = {"omnibus": omni, **grp}
    rows = []

    def rec(part, variant, name, r, extra_info=None):
        rows.append({"part": part, "variant": variant, "score": name, "beta": r["beta"], "se": r["se"], "z": r["z"],
                     "n": r["n"], "G": r["G"], **(extra_info or {})})

    # A. the base
    spl, ctx = spline_base(d), context_slopes(d)
    for name, s in sc.items():
        rec("A", "registered", name, fit(d, s))
        rec("A", "spline_no_curv", name, fit(d, s, extra=spl, curv=False))
        rec("A", "context_slopes", name, fit(d, s, extra=ctx))
        rec("A", "spline+context", name, fit(d, s, extra=spl + ctx, curv=False))
    for name, s in mem.items():
        rec("A", "registered", name, fit(d, s))
        rec("A", "spline+context", name, fit(d, s, extra=spl + ctx, curv=False))
    # B. the odds source, 2018-24 with both books
    b = pd.read_parquet(R.INST / "book_prices.parquet", columns=["match_id", "bol_a", "bol_b", "bol_after_listed_min"])
    b = b.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id").reindex(d["match_id"])
    ia, ib = 1 / b["bol_a"].to_numpy(float), 1 / b["bol_b"].to_numpy(float)
    pb = np.clip(ia / (ia + ib), 1e-6, 1 - 1e-6)
    d["L_bol"] = np.log(pb / (1 - pb))
    d["fresh"] = b["bol_after_listed_min"].to_numpy(float) >= -60
    both = (d["season"] >= 2018).to_numpy() & np.isfinite(d["L_bol"].to_numpy()) & \
        d["odds_input"].astype(str).str.contains("pinnacle").to_numpy()
    db = d[both].reset_index(drop=True)
    td = pd.to_datetime(db["tournament_date"])
    # a switch at the median date of the window, as Look A switches about half way (7 Sep 2025)
    switch = td.quantile(0.48)
    late = (td >= switch).to_numpy()
    Lh = np.where(late, db["L_bol"].to_numpy(float), db["L"].to_numpy(float))
    atp = (db["tour"] == "atp").to_numpy()
    per_period = []
    for per in (late, ~late):
        for tm in (atp, ~atp):
            per_period += [np.where(per & tm, Lh, 0.0), np.where(per & tm, Lh * np.abs(Lh), 0.0)]
    sw_info = {"rows": int(len(db)), "switch_date": str(switch.date()), "late_share": float(late.mean())}
    for name, s in sc.items():
        s2 = s[both]
        rec("B", "pinnacle_all", name, fit(db, s2))
        rec("B", "betonline_all", name, fit(db, s2, L=db["L_bol"].to_numpy(float)))
        rec("B", "hybrid_pooled_base", name, fit(db, s2, L=Lh))
        # base by period: replace the pooled base entirely (curv=False, then the per-period columns)
        X = R.beta_z(db.assign(L=0.0), s2, extra=per_period, curv=False)
        rec("B", "hybrid_base_by_period", name, X)
        fr_ = db["fresh"].to_numpy(bool)
        rec("B", "betonline_fresh", name, fit(db[fr_].reset_index(drop=True), s2[fr_],
                                               L=db.loc[fr_, "L_bol"].to_numpy(float)))
        rec("B", "betonline_stale", name, fit(db[~fr_].reset_index(drop=True), s2[~fr_],
                                               L=db.loc[~fr_, "L_bol"].to_numpy(float)))
    # calibration of the two books on the same matches (slope and curvature by tour), outcome <= 2024
    calib = {}
    for lab, Lx in (("pinnacle", db["L"].to_numpy(float)), ("betonline", db["L_bol"].to_numpy(float))):
        X = np.column_stack(R.base_cols(db, Lx, True))
        r = R.logit_fit(db["y"].to_numpy(float), X, db["block"].to_numpy())
        calib[lab] = {"coef(atp L, wta L, atp L|L|, wta L|L|)": r["b"].tolist(), "se": r["se"].tolist(),
                      "ll": r["ll"]}
    # C. retirements
    import pyarrow.parquet as pq  # noqa: F401
    st = pd.read_parquet(R.ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet",
                         columns=["match_id", "status", "tournament_date"],
                         filters=[("tournament_date", "<", R.CUT)])
    assert pd.to_datetime(st["tournament_date"]).max() < R.CUT
    st = st.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id")["status"]
    status = st.reindex(d["match_id"]).astype(str).to_numpy()
    ret = status == "retired"
    ret_info = {"status_counts": pd.Series(status).value_counts().to_dict(), "retired_share": float(ret.mean())}
    for name, s in list(sc.items()) + list(mem.items()):
        rec("C", "no_retirements", name, fit(d[~ret].reset_index(drop=True), s[~ret]))
        rec("C", "registered", name, fit(d, s))
    # D. joint fits
    G = np.column_stack([grp[k] / np.sqrt(np.mean(grp[k] ** 2)) for k in grp])
    X = np.column_stack(R.base_cols(d) + [G[:, i] for i in range(G.shape[1])])
    r = R.logit_fit(d["y"].to_numpy(float), X, d["block"].to_numpy())
    joint = {k: {"beta": float(r["b"][4 + i]), "z": float(r["b"][4 + i] / r["se"][4 + i])} for i, k in enumerate(grp)}
    # G4 without seeded, G5 without the bye seed, jointly with each other and with the seeded/bye members
    m4 = [k for k in mem if k.startswith("G4:")]
    m5 = [k for k in mem if k.startswith("G5:")]
    g4_ns = np.mean(np.column_stack([mem[k] for k in m4 if "seeded" not in k]), axis=1)
    g5_nb = np.mean(np.column_stack([mem[k] for k in m5 if "rb14" not in k]), axis=1)
    for name, s in (("G4_without_seeded", g4_ns), ("G5_without_bye_seed", g5_nb)):
        rec("D", "alone", name, fit(d, s))
    seeded, bye = mem["G4:rb__pp__seeded_a-b"], mem["G5:rb14_cold28"]
    Xs = np.column_stack(R.base_cols(d) + [seeded / np.sqrt(np.mean(seeded ** 2)), bye / np.sqrt(np.mean(bye ** 2))])
    rs = R.logit_fit(d["y"].to_numpy(float), Xs, d["block"].to_numpy())
    seed_bye = {"seeded": {"z": float(rs["b"][4] / rs["se"][4])}, "bye_seed": {"z": float(rs["b"][5] / rs["se"][5])},
                "corr": float(np.corrcoef(seeded, bye)[0, 1])}
    # E. beyond the instance's forecast, 2020-24
    a = pd.read_parquet(R.ROOT / "data" / "studies" / "edge_anatomy" / "analysis.parquet",
                        columns=["match_id", "q_full", "tournament_date"], filters=[("tournament_date", "<", R.CUT)])
    q = a.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id")["q_full"].reindex(d["match_id"])
    q = q.to_numpy(float)
    okm = np.isfinite(q) & d["season"].between(2020, 2024).to_numpy()
    dm = d[okm].reset_index(drop=True)
    qq = np.clip(q[okm], 1e-6, 1 - 1e-6)
    Lm = np.log(qq / (1 - qq))
    for name, s in list(sc.items()) + list(mem.items()):
        rec("E", "beyond_model_2020_24", name, fit(dm, s[okm], L=Lm))
        rec("E", "close_2020_24", name, fit(dm, s[okm]))
    out = pd.DataFrame(rows)
    out.to_csv(R.OUT / "robustness.csv", index=False)
    info = {"switch": sw_info, "book_calibration_2018_24_both": calib, "retirements": ret_info,
            "joint_five_groups": joint, "seeded_vs_bye_seed_joint": seed_bye}
    (R.OUT / "robustness.json").write_text(json.dumps(info, indent=1, default=float), encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    for part in "ABCE":
        p = out[out["part"] == part]
        print(f"--- part {part}")
        print(p.pivot_table(index="score", columns="variant", values="z", sort=False).round(2).to_string())
        if part in "AB":
            print(p.pivot_table(index="score", columns="variant", values="beta", sort=False).round(4).to_string())
    print(out[out["part"] == "D"][["variant", "score", "beta", "z"]].round(3).to_string(index=False))
    print(json.dumps(info, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
