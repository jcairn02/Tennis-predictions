"""Harness verifier, P2: the fixed-trait permutation under SYNTHETIC outcomes with career-long player effects.

y ~ Bernoulli(sigmoid(a_tour * eta + v_A - v_B + beta * x0)), v ~ N(0, tau^2) per player, redrawn per draw. The traits:
    UFIX     u_A - u_B, u ~ N(0, 1) per player (complete, fixed across draws)
    HEIGHT   the real height difference (missing values; control miss x eta, as the batch forms it)
The permutation is the batch's own `_trait_permuter` (on a slim panel with the trait columns), and the P2 loop mirrors
screen.run lines 424-434 (the same calls) so the permutation null's spread can be kept; one draw per trait is also run
through screen.run itself to confirm that the mirrored p-value is identical. Real results are never used.

Run: ./python.sh src/eda/feature_interactions/verify/p2_check.py --trait UFIX --tau 0.1 --draws 60 --perms 49 [--delta 0]
Writes data/studies/feature_interactions/verify/p2_<trait>_<tag>.parquet
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions import screen_batch as SB  # noqa: E402
from src.eda.feature_interactions.verify import simlib as V  # noqa: E402


def slim_panel(F: pd.DataFrame, trait: str):
    """(Q, pos, column stem): the rows the batch would permute over, with the trait as <stem>_a/_b."""
    if trait == "UFIX":
        rng = np.random.default_rng(99)
        ids = pd.unique(np.r_[F["player_a_id"].astype(str), F["player_b_id"].astype(str)])
        u = dict(zip(ids, rng.normal(size=len(ids))))
        Q = pd.DataFrame({"player_a_id": F["player_a_id"].astype(str), "player_b_id": F["player_b_id"].astype(str),
                          "tour": F["tour"].astype(str)})
        Q["ufix_a"], Q["ufix_b"] = Q["player_a_id"].map(u), Q["player_b_id"].map(u)
        return Q, np.arange(len(F)), "ufix"
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=2024)
    Q = P[["match_id", "player_a_id", "player_b_id", "tour", "height_a", "height_b"]].copy()
    pos = pd.Series(np.arange(len(P)), index=P["match_id"]).reindex(F["match_id"]).to_numpy().astype(int)
    return Q, pos, "height"


def main() -> int:
    warnings.simplefilter("ignore")
    arg = lambda n, d: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d  # noqa: E731
    trait, tau = arg("--trait", "UFIX"), float(arg("--tau", 0.1))
    draws, perms, delta, tag = int(arg("--draws", 60)), int(arg("--perms", 49)), float(arg("--delta", 0)), arg("--tag", "main")
    F = S.load(with_model=True)
    F["a_won"] = False                                     # the real results are never used below
    Q, pos, stem = slim_panel(F, trait)
    spec = {"trait_cols": [stem], "combine": lambda R: {"x": (R[f"{stem}_a"].astype(float) -
                                                               R[f"{stem}_b"].astype(float)).to_numpy()}}
    x = spec["combine"](Q)["x"][pos]
    miss = ~np.isfinite(x)
    Cm = (miss.astype(float) * F["z_model"].to_numpy(float))[:, None] if miss.any() else None
    h = S.Hypothesis(trait, x, Cm, ["miss x eta"] if Cm is not None else [], "+", trait="fixed")
    h.permute = SB._trait_permuter(Q, spec, pos, None)
    xs, Cs, prep = S.prepare(F, h, "model")
    x0 = V.std_disc(F, x)
    beta = V.calibrate(F, x0, delta, Cs, prep)[0] if delta > 0 else 0.0
    base, rng = V.base_logit(F), np.random.default_rng(2026)
    disc, rep = (F["window"] == "discovery").to_numpy(), (F["window"] == "replication").to_numpy()
    rows, path = [], C.OUT / "verify" / f"p2_{trait}_{tag}.parquet"
    redraw = "--redraw" in sys.argv and trait == "UFIX"     # a new trait per draw: the permutation test's own null
    for d in range(draws):
        if redraw:
            ids = pd.unique(np.r_[Q["player_a_id"], Q["player_b_id"]])
            u = dict(zip(ids, rng.normal(size=len(ids))))
            Q["ufix_a"], Q["ufix_b"] = Q["player_a_id"].map(u), Q["player_b_id"].map(u)   # the permuter reads Q
            h.x = spec["combine"](Q)["x"][pos]
            x0 = V.std_disc(F, h.x)
        F["a_won"] = V.draw(F, base + V.player_effects(F, tau, rng) + beta * x0, rng)
        seed = int(rng.integers(1 << 30))
        r = S.run(F, h, n_p1=0, n_p2=0, sizes=False, seed=seed)
        prng, null = np.random.default_rng(seed), []          # mirrors screen.run's P2 loop (n_p1 = 0)
        for _ in range(perms):
            hp = S.Hypothesis(h.hid, h.permute(prng), h.controls, h.control_names, h.sign)
            xsp, Csp, prp = S.prepare(F, hp, "model")
            a = S.coef_test(F, disc, xsp, Csp, "model", prp)["z"]
            b = S.coef_test(F, rep, xsp, Csp, "model", prp)["z"]
            null.append(S.joint_z(a, b, r["n1"], r["n2"]))
        null = np.asarray(null)
        rec = {"trait": trait, "tau": tau, "delta": delta, "beta": beta, "draw": d, "z1": r["z1"], "z2": r["z2"],
               "z_joint": r["z_joint"], "p_normal": r["p_joint"], "filter_pass": r["filter_pass"],
               "replicates": r["replicates"]}
        if perms > 1:
            rec.update({"null_sd": float(null.std(ddof=1)), "null_mean": float(null.mean()),
                        "p2_mirror": float((1 + (null >= r["z_joint"]).sum()) / (1 + perms))})
        if d == 0 and perms > 1:                               # the harness's own P2 on the same seed
            r_full = S.run(F, h, n_p1=0, n_p2=perms, sizes=False, seed=seed)
            rec["p2_harness"] = r_full["p2_perm"]
        rows.append(rec)
        pd.DataFrame(rows).to_parquet(path, index=False)
    C.log(f"written {path.name}: {len(rows)} draws; first-draw p2 harness {rows[0].get('p2_harness')} vs mirror "
          f"{rows[0].get('p2_mirror')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
