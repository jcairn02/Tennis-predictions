"""A1-T, POST-HOC EXPLORATION (not pre-registered; recorded as such in trait_prereg.md): the one trait-like signal of
the pre-registered run, game-level overdispersion of serve points (S4) for men at >= 50 matches per half.

Questions: is it robust (source- and event-centred, strict sequences, main tour only, each era, rank correlation)? And
what is it: dispersion between sets (set-to-set swings), between the two court ends within a set (conditions), or
game-to-game within a set and end? S4 is recomputed around four baselines per player-match:
    S4      the match's serve-point rate (the pre-registered statistic; checked equal to the stored one)
    S4set   the rate in each set (removes set-to-set swings)
    S4end   the rate at each end (the player's odd- and even-numbered service games of each set alternate ends)
    S4se    the rate in each set x end
The V1 replays are regenerated with trait_build.py's seeds (checked identical on S4).

Run after trait_build.py: ./python.sh src/eda/point_sequence/trait_s4_explore.py
Writes data/studies/point_sequence/trait_s4_explore.csv and trait_s4_explore.json.
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

VARS = ["S4", "S4set", "S4end", "S4se"]
MAIN_TOUR = {"GS", "FIN", "T1000", "T500", "T250", "TEAM"}


def s4_variants(P: dict, n: int) -> dict:
    """Per side (1, 2): arrays (n, 2) of X and D for each grouping in VARS."""
    m = P["m"]
    set_no = P["set_no"].astype(np.int64)
    gidx = P["game_idx"].astype(np.int64)
    tb = P["is_tb"].astype(bool)
    srv, win = P["server"].astype(np.int64), P["winner"].astype(np.int64)
    npt = len(m)
    start = np.ones(npt, bool)
    start[1:] = (m[1:] != m[:-1]) | (gidx[1:] != gidx[:-1])
    gid = np.cumsum(start) - 1
    G = int(gid[-1]) + 1
    first = np.flatnonzero(start)
    gm, gset, gtb, gsrv = m[first], set_no[first], tb[first], srv[first]
    gn = np.bincount(gid, minlength=G).astype(float)
    gsw = np.bincount(gid, weights=(win == srv).astype(float), minlength=G)
    out = {}
    for side in (1, 2):
        mine = (gsrv == side) & ~gtb
        # ordinal of the player's service game within its set (0, 1, 2, ...)
        key_set = gm * 8 + gset
        c = np.cumsum(mine.astype(np.int64))
        first_in_set = np.r_[True, key_set[1:] != key_set[:-1]]
        base = (c - mine)[first_in_set]
        set_id = np.cumsum(first_in_set) - 1
        ordinal = (c - mine) - base[set_id]
        parity = ordinal % 2
        groups = {"S4": gm, "S4set": key_set, "S4end": gm * 2 + parity, "S4se": key_set * 2 + parity}
        res = {}
        for name, g in groups.items():
            gg, inv = np.unique(g[mine], return_inverse=True)
            w, k = gsw[mine], gn[mine]
            N = np.bincount(inv, weights=k)
            Wt = np.bincount(inv, weights=w)
            ph = (Wt / N)[inv]
            x = (w - k * ph) ** 2 - k * ph * (1 - ph)
            d = k * ph * (1 - ph)
            res[name] = (np.bincount(gm[mine], weights=x, minlength=n), np.bincount(gm[mine], weights=d, minlength=n))
        out[side] = res
    return out


def stack(var: dict, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Rows in trait_reliability's order (mcode, side): X and D (2n, len(VARS))."""
    X = np.zeros((2 * n, len(VARS)))
    D = np.zeros((2 * n, len(VARS)))
    for j, name in enumerate(VARS):
        for side in (1, 2):
            x, d = var[side][name]
            X[side - 1::2, j] = x
            D[side - 1::2, j] = d
    return X, D


def centred(X, D, keys):
    Xc = X.copy()
    k, _ = pd.factorize(pd.Series(keys))
    for j in range(X.shape[1]):
        sx = np.bincount(k, weights=X[:, j])
        sd = np.bincount(k, weights=D[:, j])
        mu = np.divide(sx, sd, out=np.zeros_like(sx), where=sd > 0)
        Xc[:, j] = X[:, j] - D[:, j] * mu[k]
    return Xc


def main() -> int:
    pop = pd.read_parquet(TC.OUT / "trait_population.parquet")
    n = len(pop)
    P = TC.real_points(pop)
    pm, _ = TC.point_stats(P, n, pop["late_set"].to_numpy())
    rows_rates = TC.player_match_rates(pop, pm)
    pri = TC.fit_priors(rows_rates)
    worlds = {"real": stack(s4_variants(P, n), n)}
    vi = list(TC.VARIANTS).index("V1")
    for r in range(TC.REPLAYS):
        rng = np.random.default_rng([TC.SEED, vi, r])
        true = TC.draw_rates(rows_rates, pri, "V1", rng)
        Q = TC.replay_points(true[:n], true[n:], pop["bo"].to_numpy(), pop["final_code"].to_numpy(),
                             pop["s0"].to_numpy(), rng)
        worlds[f"V1_{r}"] = stack(s4_variants(Q, n), n)
        TC.log(f"V1_{r} regenerated")
    # check: S4 equals the stored statistic in every world
    stored = pd.read_parquet(TC.OUT / "trait_player_matches.parquet", columns=["world", "mcode", "side", "X_S4", "D_S4"])
    checks = {}
    for w, (X, D) in worlds.items():
        s = stored[stored["world"] == w].sort_values(["mcode", "side"])
        checks[w] = float(np.max(np.abs(s["X_S4"].to_numpy("float64") - X[:, 0])))
        assert checks[w] < 1e-2, (w, checks[w])
    _, rows, XD, tot = TR.load()
    assert (rows["mcode"].to_numpy() == np.repeat(np.arange(n), 2)).all()
    Xw = {w: v[0] for w, v in worlds.items()}
    Dw = {w: v[1] for w, v in worlds.items()}
    wl = list(worlds)
    rng = np.random.default_rng(TR.SEED + 1)
    lvl = pop["level"].to_numpy()[rows["mcode"].to_numpy()]
    qual = pop["qualifying"].to_numpy()[rows["mcode"].to_numpy()].astype(bool)
    tid = pop["tournament_id"].to_numpy()[rows["mcode"].to_numpy()]
    out_rows = []
    sets = {
        "ge20": (lambda t: rows["tour"].to_numpy() == t, 20, None),
        "ge50": (lambda t: rows["tour"].to_numpy() == t, 50, None),
        "ge50_strict": (lambda t: (rows["tour"].to_numpy() == t) & rows["strict"].to_numpy().astype(bool), 50, None),
        "ge50_source_centred": (lambda t: rows["tour"].to_numpy() == t, 50, "source"),
        "ge50_event_centred": (lambda t: rows["tour"].to_numpy() == t, 50, "event"),
        "ge20_main_tour": (lambda t: (rows["tour"].to_numpy() == t) & np.isin(lvl, list(MAIN_TOUR)) & ~qual, 20, None),
        "ge50_main_tour": (lambda t: (rows["tour"].to_numpy() == t) & np.isin(lvl, list(MAIN_TOUR)) & ~qual, 50, None),
        "ge20_2013_2018": (lambda t: (rows["tour"].to_numpy() == t) & (rows["year"].to_numpy() <= 2018), 20, None),
        "ge20_2019_2024": (lambda t: (rows["tour"].to_numpy() == t) & (rows["year"].to_numpy() >= 2019), 20, None),
    }
    for tour in ("atp", "wta"):
        for label, (mfn, hm, centre) in sets.items():
            Xo = None
            if centre == "source":
                Xo = {w: centred(Xw[w], Dw[w], rows["source"].astype(str) + "|" + rows["tour"]) for w in wl}
            elif centre == "event":
                Xo = {w: centred(Xw[w], Dw[w], tid) for w in wl}
            res = TR.run_population(label, tour, mfn(tour), rows, {"X": Xw, "D": Dw}, wl, hm, rng, Xover=Xo)
            for j, name in enumerate(VARS):
                d = TR.delta_stats(res, "V1", j)
                d.pop("_boot", None)
                out_rows.append({"tour": tour, "population": label, "stat": name, "players": res["players"],
                                 "player_matches": res["player_matches"],
                                 "matches_per_player_median": res["matches_per_player_median"], **d})
            TC.log(f"{tour} {label}: {res['players']} players")
    ex = pd.DataFrame(out_rows)
    ex.to_csv(TC.OUT / "trait_s4_explore.csv", index=False)
    # rank correlation and player-level correlates at >= 50 per half (real)
    info = {"stored_S4_max_abs_diff": checks, "player_correlates_ge50": {}, "spearman_ge50": {}}
    indoor = pd.read_parquet(TC.S0 / "stage0_matches.parquet", columns=["match_id", "indoor"]).set_index("match_id")["indoor"]
    rows_ind = indoor.reindex(rows["match_id"]).fillna(False).to_numpy().astype(float)
    for tour in ("atp", "wta"):
        res = TR.run_population("ge50", tour, rows["tour"].to_numpy() == tour, rows, {"X": Xw, "D": Dw}, wl, 50, rng,
                                want_boot=False)
        sub, pc, Pn = res["sub"], res["pcode"], res["players"]
        sp = {}
        for w in wl:
            rs = []
            for s_i in range(TR.SPLITS):
                rate, valid = TR.half_rates(pc, Pn, res["halves"][s_i], Xw[w][sub], Dw[w][sub])
                v = valid[:, 0]
                a = pd.Series(rate[v, 0, 0]).rank().to_numpy()
                b = pd.Series(rate[v, 1, 0]).rank().to_numpy()
                rs.append(np.corrcoef(a, b)[0, 1])
            sp[w] = float(np.mean(rs))
        info["spearman_ge50"][tour] = {"real": sp["real"], "V1_mean": float(np.mean([sp[f"V1_{r}"] for r in range(3)]))}
        T = tot["real"][sub]
        S4p = np.bincount(pc, weights=Xw["real"][sub][:, 0], minlength=Pn) / np.bincount(pc, weights=Dw["real"][sub][:, 0], minlength=Pn)
        feats = {
            "hold_rate": np.bincount(pc, weights=T[:, 1], minlength=Pn) / np.bincount(pc, weights=T[:, 0], minlength=Pn),
            "break_rate": np.bincount(pc, weights=T[:, 3], minlength=Pn) / np.bincount(pc, weights=T[:, 2], minlength=Pn),
            "serve_points_won": np.bincount(pc, weights=T[:, 5], minlength=Pn) / np.bincount(pc, weights=T[:, 4], minlength=Pn),
            "indoor_share": np.bincount(pc, weights=rows_ind[sub], minlength=Pn) / np.bincount(pc, minlength=Pn),
            "challenger_itf_share": np.bincount(pc, weights=np.isin(lvl[sub], ["CH", "ITF"]).astype(float), minlength=Pn) / np.bincount(pc, minlength=Pn),
            "sackmann_strings_share": np.bincount(pc, weights=(rows["source"].to_numpy()[sub] == "sackmann_pbp").astype(float), minlength=Pn) / np.bincount(pc, minlength=Pn),
            "mean_season": np.bincount(pc, weights=rows["year"].to_numpy()[sub].astype(float), minlength=Pn) / np.bincount(pc, minlength=Pn),
        }
        info["player_correlates_ge50"][tour] = {k: float(np.corrcoef(S4p, v)[0, 1]) for k, v in feats.items()}
    (TC.OUT / "trait_s4_explore.json").write_text(json.dumps(info, indent=1, default=float) + "\n", encoding="utf-8")
    TC.log("wrote trait_s4_explore.csv / .json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
