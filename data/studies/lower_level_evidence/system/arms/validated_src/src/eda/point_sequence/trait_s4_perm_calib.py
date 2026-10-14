"""POST-HOC calibration of the within-set permutation null (trait_s4_perm.py), recorded as an addition in
trait_s4_perm_results.json, not part of the frozen pre-registration.

In the iid V1 replays the order of points within a set is random by construction, so the permutation null should find
nothing there: replay - permuted replay should be about 0 for the population-level S4 and for its reliability. Any gap
there is a property of the null (it conditions only on complete games, not on the set's length and score), and the real
data's departure from random order is read net of it.

Run after trait_s4_perm.py: ./python.sh src/eda/point_sequence/trait_s4_perm_calib.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import trait_common as TC  # noqa: E402
from src.eda.point_sequence import trait_reliability as TR  # noqa: E402
from src.eda.point_sequence import trait_s4_perm as SP  # noqa: E402


def main() -> int:
    pop = pd.read_parquet(TC.OUT / "trait_population.parquet")
    n = len(pop)
    P = TC.real_points(pop)
    pm, _ = TC.point_stats(P, n, pop["late_set"].to_numpy())
    rr = TC.player_match_rates(pop, pm)
    pri = TC.fit_priors(rr)
    vi = list(TC.VARIANTS).index("V1")
    worlds = {}
    for r in range(TC.REPLAYS):
        rng = np.random.default_rng([TC.SEED, vi, r])
        true = TC.draw_rates(rr, pri, "V1", rng)
        Q = TC.replay_points(true[:n], true[n:], pop["bo"].to_numpy(), pop["final_code"].to_numpy(),
                             pop["s0"].to_numpy(), rng)
        pl = SP.pools_of(Q)
        order, _ = SP.permute(pl, None)
        worlds[f"rep_{r}"] = SP.s4_rows(SP.pseudo_points(pl, order), n)
        order, diag = SP.permute(pl, np.random.default_rng([SP.SEED, 78, r]))
        worlds[f"repperm_{r}"] = SP.s4_rows(SP.pseudo_points(pl, order), n)
        TC.log(f"V1_{r}: replay and its permutation done ({diag['pools_at_cap_kept_real_order']} pools at cap)")
    stored = pd.read_parquet(TC.OUT / "trait_player_matches.parquet", columns=["world", "mcode", "side", "X_S4"])
    s0 = stored[stored["world"] == "V1_0"].sort_values(["mcode", "side"])["X_S4"].to_numpy("float64")
    assert np.max(np.abs(s0 - worlds["rep_0"][0])) < 1e-2, "regenerated V1_0 differs from the stored replay"
    _, rows, _, _ = TR.load()
    wl = list(worlds)
    XD = {"X": {w: worlds[w][0][:, None] for w in wl}, "D": {w: worlds[w][1][:, None] for w in wl}}
    rng = np.random.default_rng(SP.REL_SEED + 1)
    rep = [w for w in wl if w.startswith("rep_")]
    per = [w for w in wl if w.startswith("repperm_")]
    out = {"note": "post-hoc calibration of the permutation null on iid V1 replays (not pre-registered)"}
    for tour in ("atp", "wta"):
        tmask = rows["tour"].to_numpy() == tour
        for label, hm in (("ge20", 20), ("ge50", 50)):
            res = TR.run_population(label, tour, tmask, rows, XD, wl, hm, rng)
            rel, boot = res["rel"][:, 0], res["boot"][:, :, 0]
            ia, ib = [wl.index(w) for w in rep], [wl.index(w) for w in per]
            d = rel[ia].mean() - rel[ib].mean()
            bd = boot[:, ia].mean(1) - boot[:, ib].mean(1)
            bd = bd[np.isfinite(bd)]
            out[f"{tour}_{label}"] = {"replay_r": float(rel[ia].mean()), "permuted_replay_r": float(rel[ib].mean()),
                                      "delta": float(d), "lo": float(np.percentile(bd, 2.5)),
                                      "hi": float(np.percentile(bd, 97.5)), "players": res["players"]}
            TC.log(f"{tour} {label}: {out[f'{tour}_{label}']}")
        sub = np.flatnonzero(tmask)
        tot = lambda w, j: worlds[w][j][sub].sum()  # noqa: E731
        rep_m = np.mean([tot(w, 0) / tot(w, 1) for w in rep])
        per_m = np.mean([tot(w, 0) / tot(w, 1) for w in per])
        out[f"{tour}_population"] = {"replay_S4": float(rep_m), "permuted_replay_S4": float(per_m),
                                     "replay_minus_permuted": float(rep_m - per_m),
                                     "service_games_replay": float(np.mean([tot(w, 2) for w in rep])),
                                     "service_games_permuted": float(np.mean([tot(w, 2) for w in per])),
                                     "hold_rate_replay": float(np.mean([tot(w, 3) / tot(w, 2) for w in rep])),
                                     "hold_rate_permuted": float(np.mean([tot(w, 3) / tot(w, 2) for w in per]))}
        TC.log(f"{tour} population: {out[f'{tour}_population']}")
    path = TC.OUT / "trait_s4_perm_results.json"
    info = json.loads(path.read_text(encoding="utf-8"))
    info["post_hoc_null_calibration"] = out
    info["deviations"].append("Added after the pre-registered results were seen: calibration of the permutation null "
                              "on the iid V1 replays (trait_s4_perm_calib.py); it changes no pre-registered number.")
    path.write_text(json.dumps(info, indent=1, default=float) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
