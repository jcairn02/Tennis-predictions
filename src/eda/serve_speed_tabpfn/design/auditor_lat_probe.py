"""Latency red team (auditor): my own Probe B on spd_B_M1 (half-life 28 d), on my independent rebuild
(auditor_lat_rebuild.side_fhat), which equals the build's spd_B_M1 to 2.5e-14 on every frame match. features_latency.py
is not imported. Feature values only.

For each cut day D (13 in 2024-26 plus 2 in 2023; inside events, including week-two days of two-week Masters where
week-one rows are released on the Monday, a release Monday itself and the Sunday before one):
    perturb   every panel row with release_B > D: y <- U(100, 250) (+30 km/h shift on alternate days), in the filter
              input AND the snapshot input (the snapshots are refitted on the perturbed panel)
    clean     no f_hat of ANY frame side with es <= D may move (tolerance 1e-12); the snapshot gammas at D, D - 1 and
              D - 7 are identical
    power     sides with D < es <= D + 42 (a sample of 2,000): the perturbation must move some
    leaky     rows admitted at lf + 1 instead of release_B (history and snapshots), same perturbation: some side with
              es <= D, es >= D - 28 must move

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_lat_probe.py
Writes data/studies/serve_speed_tabpfn/latency/auditor_lat_probe.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import auditor_lat_rebuild as LR  # noqa: E402
from src.eda.serve_speed_tabpfn.design import auditor_r4_rebuild as R4  # noqa: E402

OUT = LR.LAT / "auditor_lat_probe.json"
HL = 28.0
TOL = 1e-12
RNG = np.random.default_rng(8102026)
DAYS = ["2023-09-06", "2023-03-15", "2024-03-13", "2024-03-27", "2024-05-01", "2024-05-15", "2024-07-10",
        "2024-10-09", "2025-01-22", "2025-03-17", "2025-08-13", "2025-09-03", "2026-03-15", "2026-05-13",
        "2026-07-08"]
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def day_num(s: str) -> float:
    return float((pd.Timestamp(s) - pd.Timestamp("1970-01-01")).days)


def moved(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return ~(np.isclose(a, b, rtol=0.0, atol=TOL) | (np.isnan(a) & np.isnan(b)))


def main() -> None:
    p = LR.panel_with_release(True)
    t = R4.frame_sides(True)
    t = t[t["player_id"].notna() & t["es"].notna()].reset_index(drop=True)
    es_t = t["es"].to_numpy(float)
    log("clean B-M1 build")
    f_clean, _, _ = LR.side_fhat(p, t, "release_B", HL, True)
    var = pd.read_parquet(LR.VAR, columns=["match_id", "spd_B_M1"]).set_index("match_id")["spd_B_M1"]
    m = LR.to_match(t, f_clean)
    sd = json.loads(LR.META.read_text(encoding="utf-8"))["standardisation_sd_km_h"]["B_M1"]
    col = np.where(m["tour"].eq("atp"), np.clip(m["d"] / sd, -4, 4), 0.0)
    eq = float(np.max(np.abs(col - var.reindex(m["match_id"]).to_numpy())))
    log(f"clean rebuild against variants.parquet spd_B_M1: max |diff| {eq:.2e}")
    relB = p["release_B"].to_numpy(float)
    res = {"reads_results": False, "variant": "B_M1 (half-life 28 d)", "clean_rebuild_max_abs_diff": eq,
           "tolerance": TOL, "days": []}
    for k, ds in enumerate(DAYS):
        D = day_num(ds)
        late = relB > D
        y = p["y"].to_numpy(float).copy()
        kind = "noise U(100,250)" if k % 2 == 0 else "shift +30"
        y[late] = RNG.uniform(100.0, 250.0, int(late.sum())) if k % 2 == 0 else y[late] + 30.0
        q = p.assign(y=y)
        chk = np.flatnonzero(es_t <= D)
        f_q, _, _ = LR.side_fhat(q, t.iloc[chk].reset_index(drop=True), "release_B", HL, True)
        mv = moved(f_clean[chk], f_q)
        # snapshot gammas at D, D - 1, D - 7, every edition, both tours
        gdiff = 0.0
        for tour in ("atp", "wta"):
            pt = p[p["tour"] == tour].reset_index(drop=True)
            qt = q[q["tour"] == tour].reset_index(drop=True)
            sp, sq = LR.SnapRel(pt, pt["release_B"].to_numpy(float)), LR.SnapRel(qt, qt["release_B"].to_numpy(float))
            for dd in (D, D - 1, D - 7):
                gdiff = max(gdiff, float(np.max(np.abs(sp.at(dd) - sq.at(dd)))))
        # power: sides starting within six weeks after D
        aft = np.flatnonzero((es_t > D) & (es_t <= D + 42))
        smp = RNG.choice(aft, min(2000, len(aft)), replace=False) if len(aft) else aft
        f_pa, _, _ = LR.side_fhat(p, t.iloc[smp].reset_index(drop=True), "release_B", HL, True)
        f_pq, _, _ = LR.side_fhat(q, t.iloc[smp].reset_index(drop=True), "release_B", HL, True)
        power = int(moved(f_pa, f_pq).sum())
        # leaky control: admitted at lf + 1 (history and snapshots)
        near = np.flatnonzero((es_t <= D) & (es_t >= D - 28))
        TN = t.iloc[near].reset_index(drop=True)
        l0, _, _ = LR.side_fhat(p, TN, "release_A", HL, True)
        l1, _, _ = LR.side_fhat(q, TN, "release_A", HL, True)
        leaky = int(moved(l0, l1).sum())
        r = {"date": ds, "weekday": pd.Timestamp(ds).day_name(), "perturbation": kind,
             "rows_perturbed": int(late.sum()), "sides_checked": int(len(chk)), "moved": int(mv.sum()),
             "gamma_max_abs_diff": gdiff, "power_moved": power, "power_sample": int(len(smp)),
             "leaky_moved": leaky, "leaky_sides": int(len(near))}
        r["pass"] = r["moved"] == 0 and gdiff <= TOL and power > 0 and leaky > 0
        res["days"].append(r)
        log(f"{ds} ({r['weekday'][:3]}, {kind}): checked {r['sides_checked']}, moved {r['moved']}, gamma diff "
            f"{gdiff:.1e}, power {power}/{len(smp)}, leaky {leaky}/{len(near)} -> {'ok' if r['pass'] else 'FAIL'}")
    res["days_total"] = len(res["days"])
    res["days_2024_26"] = int(sum(d["date"] >= "2024" for d in res["days"]))
    res["moved_total"] = int(sum(d["moved"] for d in res["days"]))
    res["leaky_fired"] = int(sum(d["leaky_moved"] > 0 for d in res["days"]))
    res["pass"] = all(d["pass"] for d in res["days"])
    OUT.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    log(f"probe B on B-M1: pass {res['pass']}; moved {res['moved_total']}; leaky fired {res['leaky_fired']}/"
        f"{res['days_total']}")


if __name__ == "__main__":
    main()
