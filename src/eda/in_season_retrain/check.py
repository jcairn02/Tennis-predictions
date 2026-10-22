"""The fast check before the first in-season retrain (the owner, 20 Oct 2026; rules fixed before any result:
data/studies/in_season_retrain/check_rules.md; report docs/studies/in_season_retrain/README.md).

Part A, does growing stage 2 harm (no new TabPFN fit): on the active instance's walk-forward fits (seeds 0-3), stage 2
refitted at monthly cut-offs (the 1st of February .. November, 2020-2024) on 2019 .. Y - 1 plus the season's matches
whose results count by the cut-off, against the annual stage 2 (2019 .. Y - 1), each segment scored with the
coefficients in force.
Part B, the guard of 9 Oct (six fits, --fits, in the tennis-tabpfn-local environment): in-season fits at 1 July of
2022, 2023 and 2024 (seeds 0, 1; the decided settings) predict the season's matches from 1 July; the live
configuration (in-season fit + grown stage 2) against the decided one (walk-forward fit + annual stage 2).
Results of seasons <= 2024 only. mLL per match, paired; + = the named arm better.

    ./python_tabpfn_local.sh src/eda/in_season_retrain/check.py --fits
    ./python.sh src/eda/in_season_retrain/check.py --score
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import training_rows as TR  # noqa: E402

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-16"
OUT = ROOT / "data" / "studies" / "in_season_retrain" / "check"
SPEED = ROOT / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
RULES = ROOT / "data" / "studies" / "in_season_retrain" / "check_rules.md"
RULES_SHA256 = "2d92b5d3464b8a081dcd4406cba1b8ae43a3fd957352a15baa7d7fe3cee9f881"
SEASONS_A = tuple(range(2020, 2025))
MONTHS_A = tuple(range(2, 12))          # cut-offs on the 1st of February .. November
SEASONS_B = (2022, 2023, 2024)
SEEDS_B = (0, 1)
THROUGH = 2024
HARM = 0.10
LEAK = 1.0


def timing() -> pd.DataFrame:
    t = pd.read_parquet(TR.TIMING, columns=["match_id", "es", "lf"])
    t["match_id"] = t["match_id"].astype(str)
    return t.set_index("match_id")


def plan_b(frame: pd.DataFrame, clock: pd.DataFrame):
    """Per season: (Y, cut-off day, training mask, predicted mask, admitted count), with the mechanical checks."""
    ids = frame["match_id"].astype(str)
    es = clock["es"].reindex(ids).to_numpy()
    lf = clock["lf"].reindex(ids).to_numpy()
    for Y in SEASONS_B:
        c = TR.day_number(f"{Y}-07-01")
        adm = TR.admitted_by(frame, clock.reset_index(), Y, c)
        tr = TR.train_mask(frame, Y, set(ids[adm]))
        te = (frame["season"] == Y).to_numpy() & (es >= c)
        season_y = (frame["season"] == Y).to_numpy()
        assert np.all(lf[tr & season_y] + 1 <= c), "a training row's result counts after the cut-off"
        assert np.all(es[te] >= c), "a predicted match may start before the cut-off"
        assert not (tr & te).any(), "a match both trained on and predicted"
        assert tr.sum() == TR.train_mask(frame, Y).sum() + adm.sum()
        yield Y, c, tr, te, int(adm.sum())


# --------------------------------------------------------------------------------------------------------------------
# Part B's fits (tennis-tabpfn-local)

def fits() -> int:
    import torch

    from src.eda.model_rebuild import fits as FITS
    from src.eda.serve_speed_tabpfn import arms as A
    from src.eda.serve_speed_tabpfn import common as C
    from src.eda.tabpfn_local import runtime
    from src.eda.training_window import fits as TWF
    P = FITS.paths(INSTANCE)
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    clock = timing()
    X = A.matrix(frame, cols)
    y = frame["a_won"].astype("int64").to_numpy()
    (OUT / "fits").mkdir(parents=True, exist_ok=True)
    frame_sha = C.sha256_file(P.model_frame)
    for Y, c, tr, te, adm in plan_b(frame, clock):
        Xq = X[te].reset_index(drop=True)
        Xall = pd.concat([Xq, A.flip(Xq, P)], ignore_index=True)
        n = len(Xq)
        for seed in SEEDS_B:
            path = OUT / "fits" / f"inseason__{Y}__seed{seed}.npz"
            if path.exists():
                continue
            free = TWF.wait_for_card(patience_s=2 * 3600, processes=True)
            clf = runtime.classifier(**C.CONFIG, random_state=seed)
            torch.cuda.reset_peak_memory_stats()
            t0 = time.monotonic()
            Xt = X[tr].reset_index(drop=True)
            clf.fit(Xt, y[tr])
            p = clf.predict_proba(Xall)[:, 1]
            secs = time.monotonic() - t0
            if [int(k) for k in clf.classes_] != [0, 1] or not np.isfinite(p).all():
                raise RuntimeError(f"{path.name}: invalid probabilities")
            meta = {"season": Y, "seed": seed, "cutoff": TR.day_text(c), "train_rows": int(tr.sum()),
                    "admitted": adm, "predicted": n, "config": {**C.CONFIG, "random_state": seed},
                    "columns": cols, "frame_sha256": frame_sha, "seconds": round(secs, 1),
                    "gpu_free_gb_before": round(free, 1), "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "fingerprint": C.fingerprint(Xt, y[tr], Xall), "checkpoint": str(clf.model_path),
                    "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__}}
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, ids=np.asarray(frame.loc[te, "match_id"].astype(str).tolist(), dtype=str),
                     p=C.symmetrize(p[:n], p[n:]),
                     meta=np.asarray(json.dumps(meta)))
            tmp.replace(path)
            C.log(f"{path.name}: {secs:.0f} s, train {tr.sum():,} rows ({adm:,} of {Y}), {n:,} predicted")
            del clf
            torch.cuda.empty_cache()
    return 0


# --------------------------------------------------------------------------------------------------------------------
# Scoring (tennis env)

def fit_stage2(eta: pd.Series, info: pd.DataFrame, z: pd.Series, hist: pd.Index):
    """(s_atp, s_wta, b_shrunk, b, se_b) on the given history: compare.walk_forward's fit with the rows named."""
    from src.eda.serve_speed_tabpfn import common as C
    e = eta.reindex(hist).to_numpy()
    atp = (info.loc[hist, "tour"] == "atp").to_numpy()
    zz = z.reindex(hist).to_numpy(float)
    if not np.isfinite(zz).all():
        raise SystemExit(f"the speed column lacks {int((~np.isfinite(zz)).sum())} history matches")
    beta, se = C.fit_logistic(np.column_stack([np.where(atp, e, 0.0), np.where(~atp, e, 0.0), zz]),
                              info.loc[hist, "y"].to_numpy(float))
    b = float(beta[2]) * C.TAU_NUDGE ** 2 / (C.TAU_NUDGE ** 2 + float(se[2]) ** 2)
    return float(beta[0]), float(beta[1]), b, float(beta[2]), float(se[2])


def apply(p: pd.DataFrame, info: pd.DataFrame, z: pd.Series, ids: pd.Index, s: np.ndarray, b: np.ndarray):
    """(the seed mean's forecast, per-seed forecasts) on ids with per-match s and b (compare.forecasts' arithmetic)."""
    from src.eda.serve_speed_tabpfn import common as C
    lp = C.lg(p.reindex(ids).to_numpy())
    lm = C.lg(p.reindex(ids).mean(axis=1).to_numpy())
    zz = np.where(info.loc[ids, "tour"].to_numpy() == "wta", 0.0, z.reindex(ids).to_numpy(float))
    return expit(s * lm + b * zz), expit(s[:, None] * lp + (b * zz)[:, None])


def per_match(params: dict, ids: pd.Index, info: pd.DataFrame, key) -> tuple[np.ndarray, np.ndarray]:
    """s (by tour) and b per match from {key: coefficients}."""
    tour = info.loc[ids, "tour"].to_numpy()
    k = key(ids)
    s = np.array([params[x][0] if t == "atp" else params[x][1] for x, t in zip(k, tour)])
    b = np.array([params[x][2] for x in k])
    return s, b


def recal(q: np.ndarray, y: np.ndarray, atp: np.ndarray) -> dict:
    """The recalibration slope of a forecast's log-odds per tour (1 = right-sized) and its SE."""
    from src.eda.serve_speed_tabpfn import common as C
    x = C.lg(q)
    out = {}
    for name, m in (("men", atp), ("women", ~atp)):
        beta, se = C.fit_logistic(x[m][:, None], y[m])
        out[name] = {"slope": round(float(beta[0]), 4), "se": round(float(se[0]), 4), "matches": int(m.sum())}
    return out


def score() -> int:
    from src.eda.current_best_model import compare as CMP
    from src.eda.serve_speed_tabpfn import common as C
    if TR.sha256_file(RULES) != RULES_SHA256:
        raise SystemExit("the rules file changed since it was fixed")
    _, P, _ = CMP.candidate(str(INSTANCE))
    ref = CMP.inputs_frame(P)
    y = CMP.outcomes(P, THROUGH)
    info = CMP.scoring_info(ref, ref, y, y, THROUGH)
    clock = timing()
    info["es"] = clock["es"].reindex(info.index).to_numpy()
    info["lf"] = clock["lf"].reindex(info.index).to_numpy()
    if info[["es", "lf"]].isna().any().any():
        raise SystemExit("matches without a timing row")
    p4 = CMP.seed_table(P, ref, tuple(range(CMP.FIT_FROM, THROUGH + 1))).reindex(info.index)
    if p4.isna().any().any():
        raise SystemExit("walk-forward forecasts missing")
    eta = pd.Series(C.lg(p4.mean(axis=1).to_numpy()), index=info.index)
    z = pd.read_parquet(SPEED, columns=["match_id", "spd_L_B"]).astype({"match_id": str}).set_index("match_id")["spd_L_B"]
    keep = ~info["debut"]
    out: dict = {"rules_sha256": RULES_SHA256, "instance": INSTANCE.name, "results_read_through": THROUGH,
                 "unit": "mLL per match, paired; + = the named arm better"}

    # ---- Part A ----
    annual, grown = {}, {}
    seg_key = pd.Series(index=info.index, dtype=object)
    for Y in SEASONS_A:
        hist = info.index[(info["season"] < Y) & keep]
        annual[Y] = fit_stage2(eta, info, z, hist)
        cuts = [TR.day_number(f"{Y}-{m:02d}-01") for m in MONTHS_A]
        for k, c in enumerate(cuts):
            hi = cuts[k + 1] if k + 1 < len(cuts) else np.inf
            seg = (info["season"] == Y) & keep & (info["es"] >= c) & (info["es"] < hi)
            key = f"{Y}:{TR.day_text(c)}"
            seg_key[seg] = key
            hist_g = info.index[((info["season"] < Y) & keep)
                                | ((info["season"] == Y) & keep & (info["lf"] + 1 <= c))]
            grown[key] = fit_stage2(eta, info, z, hist_g)
    ids_a = seg_key.dropna().index
    s_an, b_an = per_match(annual, ids_a, info, lambda ix: info.loc[ix, "season"].astype(int).to_numpy())
    s_gr, b_gr = per_match(grown, ids_a, info, lambda ix: list(seg_key.loc[ix]))
    fa = apply(p4, info, z, ids_a, s_an, b_an)
    fg = apply(p4, info, z, ids_a, s_gr, b_gr)
    pos = {m: i for i, m in enumerate(ids_a)}

    def sub(f, ids):
        ix = np.array([pos[m] for m in ids])
        return f[0][ix], f[1][ix]
    rows = []
    tour_a = info.loc[ids_a, "tour"]
    for name, ids in [("both tours", ids_a), ("men", ids_a[(tour_a == "atp").to_numpy()]),
                      ("women", ids_a[(tour_a == "wta").to_numpy()])] + \
            [(str(Y), ids_a[(info.loc[ids_a, "season"] == Y).to_numpy()]) for Y in SEASONS_A]:
        r = CMP.paired(info, ids, sub(fa, ids), sub(fg, ids))
        rows.append({"part": "A", "population": name, "comparison": "grown vs annual stage 2", **r})
    prim_a = rows[0]
    harm_a = bool(prim_a["estimate"] < -HARM and prim_a["hi"] < 0)
    out["part_a"] = {"primary": prim_a, "harm": harm_a, "segments": int(seg_key.nunique()), "matches": len(ids_a),
                     "annual": {str(Y): v for Y, v in annual.items()}, "grown": grown}

    # ---- Part B ----
    fits_dir = OUT / "fits"
    have = all((fits_dir / f"inseason__{Y}__seed{k}.npz").exists() for Y in SEASONS_B for k in SEEDS_B)
    if have:
        live, decided, tab_in, tab_an, ids_all = [], [], [], [], []
        diag = {}
        for Y in SEASONS_B:
            cols = {}
            meta = None
            for k in SEEDS_B:
                # this study's own files; the first six (20 Oct, 18:55) stored the ids as an object array
                with np.load(fits_dir / f"inseason__{Y}__seed{k}.npz", allow_pickle=True) as d:
                    cols[k] = pd.Series(d["p"], index=d["ids"].astype(str))
                    meta = json.loads(str(d["meta"]))
            p_in = pd.DataFrame(cols)
            c = TR.day_number(f"{Y}-07-01")
            ids = p_in.index[keep.reindex(p_in.index).fillna(False).astype(bool).to_numpy()]
            ids = ids[(info.loc[ids, "es"] >= c).to_numpy()]
            p_an = p4.loc[ids, list(SEEDS_B)]
            p_in = p_in.loc[ids]
            hist_g = info.index[((info["season"] < Y) & keep) | ((info["season"] == Y) & keep & (info["lf"] + 1 <= c))]
            g = fit_stage2(eta, info, z, hist_g)
            a = annual[Y]
            atp = (info.loc[ids, "tour"] == "atp").to_numpy()
            ones = np.ones(len(ids))
            s_g, b_g = np.where(atp, g[0], g[1]), g[2] * ones
            s_a, b_a = np.where(atp, a[0], a[1]), a[2] * ones
            live.append(apply(p_in, info, z, ids, s_g, b_g))
            decided.append(apply(p_an, info, z, ids, s_a, b_a))
            tab_in.append(apply(p_in, info, z, ids, s_a, b_a))
            tab_an.append(decided[-1])
            ids_all.append(ids)
            mk = info.loc[ids, "p_ref"].to_numpy(float)
            spread = lambda pp: float(np.std(C.lg(pp.mean(axis=1).to_numpy()) - C.lg(mk)))
            diag[str(Y)] = {"predicted": len(ids), "train_rows": meta["train_rows"], "admitted": meta["admitted"],
                            "grown_stage2": g, "annual_stage2": a,
                            "spread_in_season": round(spread(p_in), 4), "spread_walk_forward": round(spread(p_an), 4)}
        ids_b = pd.Index(np.concatenate([np.asarray(i) for i in ids_all]))

        def cat(fs):
            return np.concatenate([f[0] for f in fs]), np.concatenate([f[1] for f in fs], axis=0)
        L, D, TI, TA = cat(live), cat(decided), cat(tab_in), cat(tab_an)
        prim_b = CMP.paired(info, ids_b, D, L)
        tab_b = CMP.paired(info, ids_b, TA, TI)
        rows.append({"part": "B", "population": "both tours", "comparison": "live config vs decided", **prim_b})
        rows.append({"part": "B", "population": "both tours", "comparison": "TabPFN part: in-season vs walk-forward",
                     **tab_b})
        atp_b = (info.loc[ids_b, "tour"] == "atp").to_numpy()
        for name, m in (("men", atp_b), ("women", ~atp_b)):
            sub_ids = ids_b[m]
            rows.append({"part": "B", "population": name, "comparison": "live config vs decided",
                         **CMP.paired(info, sub_ids, (D[0][m], D[1][m]), (L[0][m], L[1][m]))})
        yb = info.loc[ids_b, "y"].to_numpy(float)
        fail = bool(prim_b["estimate"] < -HARM and prim_b["hi"] < 0) or bool(tab_b["estimate"] > LEAK)
        out["part_b"] = {"primary": prim_b, "tabpfn_part": tab_b, "guard_fails": fail,
                         "recalibration": {"live": recal(L[0], yb, atp_b), "decided": recal(D[0], yb, atp_b)},
                         "seasons": diag}
    else:
        out["part_b"] = "fits missing: run --fits first"
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "results.csv", index=False)
    C.write_json(OUT / "results.json", out)
    show = pd.DataFrame(rows)[["part", "population", "comparison", "matches", "estimate", "lo", "hi", "p_better",
                               "reading"]]
    pd.set_option("display.width", 200)
    print(show.round(3).to_string(index=False))
    print("Part A harm:", out["part_a"]["harm"], "| Part B guard fails:",
          out["part_b"]["guard_fails"] if isinstance(out["part_b"], dict) else out["part_b"])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fits", action="store_true", help="Part B's six fits (tennis-tabpfn-local)")
    ap.add_argument("--score", action="store_true", help="score Parts A and B (tennis env)")
    ap.add_argument("--plan", action="store_true", help="Part B's plan and mechanical checks only (no fit, no result)")
    a = ap.parse_args()
    if a.plan:
        from src.eda.model_rebuild import fits as FITS
        from src.eda.serve_speed_tabpfn import arms as A
        P = FITS.paths(INSTANCE)
        frame = A.load_frame([], P, labels=True)
        for Y, c, tr, te, adm in plan_b(frame, timing()):
            print(f"{Y}: cut-off {TR.day_text(c)}; train {tr.sum():,} rows (season rule {tr.sum() - adm:,} + {adm:,} "
                  f"admitted); predict {te.sum():,}; mechanical checks passed")
        return 0
    if a.fits:
        return fits()
    if a.score:
        return score()
    raise SystemExit("--plan, --fits or --score")


if __name__ == "__main__":
    sys.exit(main())
