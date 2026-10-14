"""Adaptive-memory red team (auditor): an independent re-derivation of the late flags and modes, the release
definitions, the applier as a black box, the date command's reads, and values-only diagnostics of what the switch
compares. No outcome, result, target or price: the date command runs under a spy that refuses any a_won read, and its CSV
goes to the scratchpad.

1  late / mode for scenarios B and D (and A, E): EVERY men's 2024-26 frame match (7,070; well above the 2,000
   asked), my code: the frozen panel's use rows, availability.parquet's release days, the frame sides through my R4
   frame join; a side is late when an own earlier usable row (earlier tdate, or the same tournament at an earlier
   round) has lf + 1 < es, obs >= es - 14 and release_S > es; the mode is T when neither side is late
2  release_D / release_E against plan.md (D: tour lf + 2, Slams as B; E: tour as B, Slams lf + 2) and B's rule again
3  adjust.apply on synthetic inputs: women get s_wta * eta whatever the columns; T rows ignore col_L, L rows ignore
   col_T; each (mode, season) takes its own coefficient row; no blending
4  adjust.score_date under a read spy (a_won never requested), its CSV redirected
5  values only: under B, how far mode-T matches' spd_T_B is from the instant spd_f, and how many mode-T sides miss a
   grace-day row; under D and E, the L columns' scale against spd_B_M1 (whose history fits b_L)

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_ad_check.py
Writes data/studies/serve_speed_tabpfn/adaptive/auditor_ad_check.json
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

from src.eda.serve_speed_tabpfn.design import auditor_r4_rebuild as R4  # noqa: E402

AD = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "adaptive"
LAT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "latency"
OUT = AD / "auditor_ad_check.json"
SCRATCH = Path(r"C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/"
               r"48421609-8831-440b-a460-5878ba530dde/scratchpad/ad_date")


def panel() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data" / "studies" / "serve_speed_tabpfn" / "speed_panel.parquet")
    p = p[p["use"]].copy()
    a = pd.read_parquet(LAT / "availability.parquet", columns=["match_id", "side", "release_A", "release_B",
                                                                "release_D", "release_E", "rule_B"])
    p = p.merge(a, on=["match_id", "side"], how="left", validate="one_to_one")
    assert p[["release_A", "release_B", "release_D", "release_E"]].notna().all().all()
    return p.reset_index(drop=True)


def late(p: pd.DataFrame, t: pd.DataFrame, rel_col: str) -> np.ndarray:
    out = np.zeros(len(t), bool)
    g = {k: v.to_numpy() for k, v in p.groupby("player_id").groups.items()}
    td, tid, ro = p["tdate"].to_numpy(), p["tournament_id"].to_numpy(), p["round_order"].to_numpy()
    lf, ob, rel = p["lf"].to_numpy(float), p["obs"].to_numpy(float), p[rel_col].to_numpy(float)
    for i, (pid, ttd, ttid, tro, es) in enumerate(zip(t["player_id"], t["tdate"], t["tournament_id"],
                                                       t["round_order"], t["es"].astype(float))):
        ix = g.get(pid)
        if ix is None:
            continue
        e = (td[ix] < ttd) | ((tid[ix] == ttid) & (ro[ix] < tro))
        out[i] = bool((e & (lf[ix] + 1 < es) & (ob[ix] >= es - 14) & (rel[ix] > es)).any())
    return out


def main() -> None:
    res = {"reads_results": False}
    p = panel()
    t = R4.frame_sides(True)
    t = t[t["tour"].eq("atp") & t["season"].between(2024, 2026) & t["player_id"].notna()].reset_index(drop=True)
    cols = pd.read_parquet(AD / "columns.parquet")
    # 2 release definitions
    a = pd.read_parquet(LAT / "availability.parquet", columns=["level", "lf", "release_A", "release_B", "release_D",
                                                                "release_E", "rule_B", "use"])
    u = a[a["use"]]
    slam = u["rule_B"].eq("slam_after_event")
    res["release_definitions_use_rows"] = {
        "rows": int(len(u)), "A_eq_lf_plus_1": bool((u["release_A"] == u["lf"] + 1).all()),
        "D_tour_eq_lf_plus_2": bool((u.loc[~slam, "release_D"] == u.loc[~slam, "lf"] + 2).all()),
        "D_slam_eq_B": bool((u.loc[slam, "release_D"] == u.loc[slam, "release_B"]).all()),
        "E_tour_eq_B": bool((u.loc[~slam, "release_E"] == u.loc[~slam, "release_B"]).all()),
        "E_slam_eq_lf_plus_2": bool((u.loc[slam, "release_E"] == u.loc[slam, "lf"] + 2).all()),
        "B_weekday_rule": bool((((u.loc[~slam, "release_B"] + 3) % 7) == 0).all()),
        "all_rows_D_E_ge_A": bool(((a["release_D"] >= a["release_A"]) & (a["release_E"] >= a["release_A"])).all())}
    print(res["release_definitions_use_rows"])
    # 1 late flags and modes
    res["late_mode_agreement"] = {}
    for s in ("A", "B", "D", "E"):
        fl = late(p, t, f"release_{s}")
        x = t.assign(late=fl)
        A_, B_ = x[x["side"] == "A"].set_index("match_id"), x[x["side"] == "B"].set_index("match_id")
        m = pd.DataFrame({"la": A_["late"], "lb": B_["late"].reindex(A_.index)})
        m["mode"] = np.where(m["la"] | m["lb"], "L", "T")
        c = cols.set_index("match_id").reindex(m.index)
        r = {"matches": int(len(m)),
             "late_a_equal": float((c[f"late_a_{s}"].astype(bool).to_numpy() == m["la"].to_numpy()).mean()),
             "late_b_equal": float((c[f"late_b_{s}"].astype(bool).to_numpy() == m["lb"].to_numpy()).mean()),
             "mode_equal": float((c[f"mode_{s}"].astype(str).to_numpy() == m["mode"].to_numpy()).mean()),
             "share_L_mine": float((m["mode"] == "L").mean()),
             "share_L_build": float((c[f"mode_{s}"].astype(str) == "L").mean())}
        res["late_mode_agreement"][s] = r
        print(s, r)
    # 3 the applier, as a black box on synthetic inputs
    from src.eda.serve_speed_tabpfn.adaptive import adjust as J
    coef = json.loads((AD / "coefficients.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(1)
    n = 4000
    eta = rng.normal(0, 1.2, n)
    tour = rng.choice(["atp", "wta"], n)
    season = rng.choice([2024, 2025, 2026], n)
    mode = rng.choice(["T", "L"], n)
    ct, cl = rng.normal(0, 1, n), rng.normal(0, 1, n)
    q = J.apply(eta, tour, season, mode, ct, cl, coef)
    exp_ = np.empty(n)
    for i in range(n):
        c = coef[mode[i]][str(season[i])]
        s_ = c["s_atp"] if tour[i] == "atp" else c["s_wta"]
        z = 0.0 if tour[i] == "wta" else (ct[i] if mode[i] == "T" else cl[i])
        exp_[i] = 1 / (1 + np.exp(-(s_ * eta[i] + c["b_shrunk"] * z)))
    q_alt_l = J.apply(eta, tour, season, mode, ct, cl + 5.0, coef)       # perturb col_L only
    q_alt_t = J.apply(eta, tour, season, mode, ct + 5.0, cl, coef)       # perturb col_T only
    w = tour == "wta"
    res["applier"] = {
        "matches_formula_max_diff": float(np.max(np.abs(q - exp_))),
        "T_rows_ignore_col_L": bool(np.array_equal(q[mode == "T"], q_alt_l[mode == "T"])),
        "L_rows_ignore_col_T": bool(np.array_equal(q[mode == "L"], q_alt_t[mode == "L"])),
        "women_ignore_both_columns": bool(np.array_equal(q[w], q_alt_l[w]) and np.array_equal(q[w], q_alt_t[w])),
        "women_s_wta_equal_in_T_and_L": {y: coef["T"][y]["s_wta"] == coef["L"][y]["s_wta"]
                                         for y in ("2024", "2025", "2026")}}
    print(res["applier"])
    # 4 the date command under a read spy
    import src.eda.serve_speed_tabpfn.adaptive.adjust as Jmod
    from src.eda.serve_speed_tabpfn import common as C
    requested = []
    real_read = pd.read_parquet

    def spy(path, *args, **kw):
        cols_ = kw.get("columns")
        requested.append((str(path)[-60:], None if cols_ is None else list(cols_)))
        if cols_ is None or "a_won" in (cols_ or []):
            if cols_ is None or "a_won" in cols_:
                if "model_frame" in str(path):
                    raise RuntimeError(f"result read attempted: {path} {cols_}")
        return real_read(path, *args, **kw)

    SCRATCH.mkdir(parents=True, exist_ok=True)
    real_csv = pd.DataFrame.to_csv

    def redirect(self, path=None, *args, **kw):
        return real_csv(self, SCRATCH / Path(str(path)).name, *args, **kw)

    pd.read_parquet, pd.DataFrame.to_csv = spy, redirect
    try:
        out = Jmod.score_date(C.DEFAULT, "2026-07-06", "B")
        ok = True
    finally:
        pd.read_parquet, pd.DataFrame.to_csv = real_read, real_csv
    res["date_command"] = {"ran": ok, "rows": int(len(out)), "a_won_requested": any(
        c is not None and "a_won" in c for _, c in requested), "reads": requested[:12],
        "modes": out["mode"].value_counts().to_dict() if len(out) else {}}
    print(res["date_command"])
    # 5 values only: what the switch compares
    sp = pd.read_parquet(ROOT / "data" / "studies" / "serve_speed_tabpfn" / "features" / "speed.parquet",
                         columns=["match_id", "spd_f"])
    v = pd.read_parquet(LAT / "variants.parquet", columns=["match_id", "spd_B_M1"])
    men = cols.merge(sp, on="match_id").merge(v, on="match_id").set_index("match_id").reindex(
        t.loc[t["side"] == "A", "match_id"])
    tb = men["mode_B"].astype(str) == "T"
    d = (men["spd_T_B"] - men["spd_f"])[tb]
    # grace rows: under B, a mode-T side whose own earlier usable row finished the day before es (lf + 1 == es) is not
    # in hand at es
    g = {k: v_.to_numpy() for k, v_ in p.groupby("player_id").groups.items()}
    grace = np.zeros(len(t), bool)
    for i, (pid, ttd, ttid, tro, es) in enumerate(zip(t["player_id"], t["tdate"], t["tournament_id"],
                                                       t["round_order"], t["es"].astype(float))):
        ix = g.get(pid)
        if ix is None:
            continue
        e = (p["tdate"].to_numpy()[ix] < ttd) | ((p["tournament_id"].to_numpy()[ix] == ttid)
                                                 & (p["round_order"].to_numpy()[ix] < tro))
        grace[i] = bool((e & (p["lf"].to_numpy(float)[ix] + 1 == es)
                         & (p["release_B"].to_numpy(float)[ix] > es)).any())
    x = t.assign(grace=grace)
    ga = x[x["side"] == "A"].set_index("match_id")["grace"] | x[x["side"] == "B"].set_index("match_id")["grace"]
    res["values"] = {
        "B_mode_T_matches": int(tb.sum()),
        "B_mode_T_corr_spd_T_B_vs_spd_f": float(np.corrcoef(men.loc[tb, "spd_T_B"], men.loc[tb, "spd_f"])[0, 1]),
        "B_mode_T_share_abs_diff_gt_0.5": float((d.abs() > 0.5).mean()),
        "B_mode_T_share_with_a_grace_row_missing": float(ga.reindex(men.index)[tb].mean()),
        "sd_men_2024_26": {c_: float(men[c_].std()) for c_ in ("spd_f", "spd_T_B", "spd_B_M1", "spd_L_B", "spd_L_D",
                                                                "spd_L_E", "spd_T_D", "spd_T_E")},
        "corr_spd_L_D_vs_spd_B_M1": float(np.corrcoef(men["spd_L_D"], men["spd_B_M1"])[0, 1])}
    print(res["values"])
    OUT.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
