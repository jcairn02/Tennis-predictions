"""Score the TabPFN-3.5-Plus jobs: each arm against the stage's reference arm (the current best model's inputs) and
against the closing odds, season by season (each season one sample) and pooled. Written before any paid call and
amended after the audit (docs/studies/surface_elo_pieces/audit.md: B1, B2, S2, S4, G4) before any call either.

Forecasts. A job's query holds each match as stored and with A and B swapped; a seed's forecast is the mean of
P(A | x) and 1 - P(A | swapped x). In a comparison of two arms, each arm's forecast is the mean over the seeds present
for BOTH arms in EVERY season of the stage (the same seeds for both arms; S2): a lost job never silently drops a
season. The primary endpoint (confirm: primary against base) refuses to run if that seed set is empty.

    market      the closing odds' log-odds recalibrated per tour by one slope (no intercept), fitted on the fold's own
                training matches (2013 .. season - 1), as the original study recalibrated them on its training matches

Population (pre-registered after the audit's B1). Every comparison leaves out the matches with a player whose first
match in Stage 0 falls in the match's season (debut_season: the 2026 WTA identity split, 73 test matches, plus 0-5 true
debuts a season). The full population is reported as a sensitivity ("population": "all").

Comparisons (milli-log-loss, positive = the second-named forecast is better, paired 95% intervals clustered in four-week
blocks of tournament dates, calendar weeks as a sensitivity), per tour and both tours:
    arm vs reference     per season and pooled over the stage's seasons
    arm vs market        the same
    seed-matched         reference seed s against arm seed s (the pilot is read this way: S4); reference seed s
                         against reference seed 0 (the noise floor)
    seasons as samples   the seasonal gains of arm vs reference: mean, t interval on (seasons - 1) df, seasons positive
    subsets              early surface season (either player < 3 matches on the surface this season), both new
                         (both < 3), the rest, grass (grass has about 10 four-week blocks over 2022-2026: directional,
                         read with the calendar-week interval too; G4)

The pilot also writes the pre-registered minimum detectable effect (B2): the seed-matched paired SE of primary against
base on 2019-2021, scaled by sqrt(pilot matches / confirmation matches), times (z 0.975 + z 0.80). It is conservative:
the single seeds carry fit noise that the confirmation's three-seed means mostly average away.

Writes data/studies/surface_elo_pieces/results_<stage>.json, results_<stage>.csv and predictions_<stage>.parquet (and
mde.json from the pilot). Run: ./python.sh src/eda/surface_elo_pieces/score.py --stage pilot|confirm|diagnostic
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.surface_elo_pieces import guard as G  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

SEED_COL = re.compile(r"^p_(.+)_s(\d+)$")              # one seed's forecast: p_<arm>_s<seed>
REFERENCE = {"pilot": "base", "confirm": "base", "diagnostic": "base_noodds"}   # each stage's reference arm
ENDPOINT = {"confirm": ("base", "primary")}            # the pre-registered primary endpoint
KEY = ("milli-log-loss; positive = the second-named forecast has the lower log loss (better); a 95% interval that "
       "spans 0 is a tie")
Z80 = float(norm.ppf(0.975) + norm.ppf(0.80))


def market_recalibrated(frame: pd.DataFrame, season: int) -> np.ndarray:
    """P(A) from the odds recalibrated per tour on the fold's training matches; for the season's matches."""
    te_all = (frame["season"] == season).to_numpy()
    out = np.full(int(te_all.sum()), np.nan)
    for tour in C.TOURS:
        tr = (frame["season"].between(C.TRAIN_FROM, season - 1) & (frame["tour"] == tour)).to_numpy()
        te = te_all & (frame["tour"] == tour).to_numpy()
        beta, _ = T.fit_logistic(frame.loc[tr, ["x_odds_logit"]].to_numpy(), frame.loc[tr, "a_won"].to_numpy(float))
        out[(frame.loc[te_all, "tour"] == tour).to_numpy()] = expit(frame.loc[te, "x_odds_logit"].to_numpy() * beta[0])
    return out


def load(stage: str, root: Path | None = None, frame: pd.DataFrame | None = None, jobs: list | None = None):
    """Per-seed forecasts of every finished job of the stage (missing where a job has no saved predictions), and
    which seeds each arm has in each season."""
    root = G.canonical_root() if root is None else Path(root)
    frame = pd.read_parquet(C.OUT / "frame.parquet") if frame is None else frame
    js = json.loads((C.OUT / "jobs.json").read_text(encoding="utf-8")) if jobs is None else jobs
    js = [j for j in js if j["stage"] == stage]
    seasons = sorted({j["season"] for j in js})
    avail: dict = {}
    parts = []
    for season in seasons:
        g = frame[frame["season"] == season].reset_index(drop=True)
        cols = {"match_id": g["match_id"], "tour": g["tour"], "season": g["season"], "a_won": g["a_won"],
                "tournament_date": g["tournament_date"], "p_market_raw": g["p_mkt"],
                "p_market": market_recalibrated(frame, season), "season_n_a": g["season_n_a"],
                "season_n_b": g["season_n_b"], "surface": g["x_surface"], "debut_season": g["debut_season"]}
        n = len(g)
        for j in [j for j in js if j["season"] == season]:
            path = root / j["job"] / "predictions.npz"
            if not path.exists():
                continue
            p_a, _ = G.load_predictions(path, G.binding_for(j, G.job_config(j["seed"])), 2 * n)
            cols[f"p_{j['arm']}_s{j['seed']}"] = T.symmetrize(p_a[:n], p_a[n:])
            cols[f"gap_{j['arm']}_s{j['seed']}"] = np.abs(p_a[:n] - (1 - p_a[n:]))
            avail.setdefault(j["arm"], {}).setdefault(season, set()).add(j["seed"])
        parts.append(pd.DataFrame(cols))
    f = pd.concat(parts, ignore_index=True)
    return f, avail, seasons


def common_seeds(avail: dict, arms: list[str], seasons: list[int]) -> list[int]:
    """Seeds present for every named arm in every season."""
    sets = [avail.get(a, {}).get(s, set()) for a in arms for s in seasons]
    return sorted(set.intersection(*sets)) if sets else []


def forecast(f: pd.DataFrame, arm: str, seeds: list[int]) -> np.ndarray:
    return f[[f"p_{arm}_s{s}" for s in seeds]].mean(axis=1).to_numpy()


def compare(g: pd.DataFrame, pa: np.ndarray, pb: np.ndarray) -> dict:
    y = g["a_won"].to_numpy()
    return T.compare(T.ll(pa, y), T.ll(pb, y), g["tournament_date"].to_numpy())


def seasons_as_samples(gains: list[float]) -> dict:
    g = np.asarray(gains, dtype=float)
    k = len(g)
    if k < 2:
        return {"seasons": k}
    r = student_t.ppf(0.975, k - 1) * g.std(ddof=1) / np.sqrt(k)
    return {"seasons": k, "mean": float(g.mean()), "lo": float(g.mean() - r), "hi": float(g.mean() + r),
            "positive": int((g > 0).sum()), "gains": [float(x) for x in g]}


def pairs_for(stage: str, avail: dict, seasons: list[int]) -> list[dict]:
    """Every comparison of the stage: (label of base, label of model, base arm, model arm, seeds of each)."""
    ref = REFERENCE[stage]
    arms = sorted(avail)
    out = []
    for arm in arms:
        if arm != ref:
            s = common_seeds(avail, [ref, arm], seasons)
            if s:
                out.append({"base": ref, "model": arm, "base_arm": ref, "model_arm": arm, "seeds": s})
        s = common_seeds(avail, [arm], seasons)
        if s:
            out.append({"base": "market", "model": arm, "base_arm": "market", "model_arm": arm, "seeds": s})
        for seed in common_seeds(avail, [ref, arm], seasons):
            if arm != ref:
                out.append({"base": f"{ref}_s{seed}", "model": f"{arm}_s{seed}", "base_arm": ref, "model_arm": arm,
                            "seeds": [seed]})
    for seed in common_seeds(avail, [ref], seasons):
        if seed != 0 and 0 in common_seeds(avail, [ref], seasons):
            out.append({"base": f"{ref}_s0", "model": f"{ref}_s{seed}", "base_arm": ref, "model_arm": ref,
                        "seeds": [0], "model_seeds": [seed]})
    return out


def score(stage: str, f: pd.DataFrame, avail: dict, seasons: list[int]) -> tuple[pd.DataFrame, dict]:
    ref = REFERENCE[stage]
    if ref not in avail:
        raise SystemExit(f"no {ref} predictions yet")
    if stage in ENDPOINT:
        a, b = ENDPOINT[stage]
        if not common_seeds(avail, [a, b], seasons):
            raise SystemExit(f"the primary endpoint needs at least one seed of both {a} and {b} in every season "
                             f"{seasons}; available: { {k: {s: sorted(v) for s, v in d.items()} for k, d in avail.items() if k in (a, b)} }")
    early = (f["season_n_a"] < 3) | (f["season_n_b"] < 3)
    subsets = {"all": np.ones(len(f), bool), "early surface season": early.to_numpy(),
               "both new": ((f["season_n_a"] < 3) & (f["season_n_b"] < 3)).to_numpy(), "rest of season": ~early.to_numpy(),
               "grass": (f["surface"] == 2).to_numpy()}
    pops = {"excl_debut": ~f["debut_season"].to_numpy(bool), "all": np.ones(len(f), bool)}
    tours = {"atp": (f["tour"] == "atp").to_numpy(), "wta": (f["tour"] == "wta").to_numpy(), "both": np.ones(len(f), bool)}
    windows = [(f"{seasons[0]}-{seasons[-1]}", seasons)] + [(str(s), [s]) for s in seasons]
    rows = []
    for pr in pairs_for(stage, avail, seasons):
        pb = f["p_market"].to_numpy() if pr["base_arm"] == "market" else forecast(f, pr["base_arm"], pr["seeds"])
        pm = forecast(f, pr["model_arm"], pr.get("model_seeds", pr["seeds"]))
        for pop, pm_ in pops.items():
            for tour, tm in tours.items():
                for label, ss in windows:
                    for sub, sm in (subsets.items() if label == windows[0][0] else [("all", subsets["all"])]):
                        k = pm_ & tm & sm & f["season"].isin(ss).to_numpy() & np.isfinite(pb) & np.isfinite(pm)
                        if not k.any():
                            continue
                        c = compare(f[k], pb[k], pm[k])
                        rows.append({"population": pop, "tour": tour, "window": label, "subset": sub,
                                     "base": pr["base"], "model": pr["model"],
                                     "seeds": ",".join(map(str, pr.get("model_seeds", pr["seeds"]))),
                                     "matches": c["n"], "gain": c["gain"], "lo": c["lo"], "hi": c["hi"],
                                     "blocks": c["blocks"], "week_lo": c["week_lo"], "week_hi": c["week_hi"]})
    R = pd.DataFrame(rows)
    samples = {}
    for pop in pops:
        for tour in tours:
            for arm in avail:
                if arm == ref:
                    continue
                per = R[(R["population"] == pop) & (R["tour"] == tour) & (R["subset"] == "all") & (R["base"] == ref)
                        & (R["model"] == arm) & R["window"].isin([str(s) for s in seasons])].sort_values("window")
                samples[f"{pop}|{tour}|{arm}"] = seasons_as_samples(per["gain"].tolist())
    # log loss of each forecast on identical rows (the scored population, every arm's complete seeds)
    full = {arm: common_seeds(avail, [arm], seasons) for arm in avail}
    ok = pops["excl_debut"].copy()
    for arm, s in full.items():
        if s:
            ok &= np.isfinite(forecast(f, arm, s))
    ll = {}
    for tour, tm in tours.items():
        k = ok & tm
        y = f.loc[k, "a_won"].to_numpy()
        ll[tour] = {"matches": int(k.sum()),
                    **{name: float(T.ll(f.loc[k, f"p_{name}"].to_numpy(), y).mean()) for name in ("market_raw", "market")},
                    **{arm: float(T.ll(forecast(f, arm, s)[k], y).mean()) for arm, s in full.items() if s}}
    meta = {"seeds_available": {a: {str(s): sorted(v) for s, v in d.items()} for a, d in avail.items()},
            "log_loss_identical_rows": ll, "seasons_as_samples": samples,
            "orientation_gap_mean": {c[4:]: float(f[c].mean()) for c in f.columns if c.startswith("gap_")}}
    return R, meta


def mde(R: pd.DataFrame, n_confirm: dict) -> dict:
    """Pre-registered minimum detectable effect for the confirmation (audit B2), from the pilot's seed-matched pair."""
    out = {"rule": "SE of base_s0 vs primary_s0 on the pilot (2019-2021, scored population), x sqrt(pilot matches / "
                   "confirmation matches), x (z 0.975 + z 0.80) = MDE at 80% power, two-sided 5%; conservative "
                   "(single seeds)", "z_sum": Z80}
    for tour in ("atp", "wta", "both"):
        r = R[(R["population"] == "excl_debut") & (R["tour"] == tour) & (R["window"] == "2019-2021")
              & (R["subset"] == "all") & (R["base"] == "base_s0") & (R["model"] == "primary_s0")]
        noise = R[(R["population"] == "excl_debut") & (R["tour"] == tour) & (R["window"] == "2019-2021")
                  & (R["subset"] == "all") & (R["base"] == "base_s0") & (R["model"] == "base_s1")]
        if r.empty:
            continue
        r = r.iloc[0]
        se = (r["hi"] - r["lo"]) / 2 / student_t.ppf(0.975, max(int(r["blocks"]) - 1, 1))
        se_c = se * np.sqrt(r["matches"] / n_confirm[tour])
        out[tour] = {"pilot_matches": int(r["matches"]), "pilot_gain": float(r["gain"]), "pilot_se": float(se),
                     "confirm_matches": int(n_confirm[tour]), "confirm_se": float(se_c), "mde80": float(Z80 * se_c),
                     "seed_noise_gain": float(noise["gain"].iloc[0]) if not noise.empty else None,
                     "seed_noise_interval": [float(noise["lo"].iloc[0]), float(noise["hi"].iloc[0])]
                     if not noise.empty else None}
    return out


THINKING = ROOT / "data" / "studies" / "tabpfn_leakproof" / "test_predictions.parquet"


def thinking_reference(f: pd.DataFrame, avail: dict, seasons: list[int]) -> pd.DataFrame:
    """A reference, not part of the pre-registered test: the current best model itself (the leak-proof
    TabPFN-3.5-Thinking fit, one fit trained on 2013-2021 and predicting all of 2022-2026) against this study's
    non-thinking base arm on the same matches. In the 2022 fold the two have identical training rows and inputs, so
    2022 compares Plus with Thinking like for like; later seasons also differ by the walk-forward's extra training."""
    if not THINKING.exists() or "base" not in avail:
        return pd.DataFrame()
    th = pd.read_parquet(THINKING, columns=["match_id", "p_leakproof"])
    p_th = f[["match_id"]].merge(th, on="match_id", how="left")["p_leakproof"].to_numpy()
    seeds = common_seeds(avail, ["base"], seasons)
    p_base = forecast(f, "base", seeds)
    keep = ~f["debut_season"].to_numpy(bool) & np.isfinite(p_th)
    rows = []
    for tour, tm in (("atp", f["tour"] == "atp"), ("wta", f["tour"] == "wta"), ("both", f["tour"].notna())):
        for label, ss in [(f"{seasons[0]}-{seasons[-1]}", seasons)] + [(str(s), [s]) for s in seasons]:
            k = keep & tm.to_numpy() & f["season"].isin(ss).to_numpy()
            if not k.any():
                continue
            for base, pb, model, pm in (("thinking", p_th, "base", p_base),
                                        ("market", f["p_market"].to_numpy(), "thinking", p_th)):
                c = compare(f[k], pb[k], pm[k])
                rows.append({"population": "excl_debut", "tour": tour, "window": label, "subset": "all",
                             "base": base, "model": model, "seeds": ",".join(map(str, seeds)), "matches": c["n"],
                             "gain": c["gain"], "lo": c["lo"], "hi": c["hi"], "blocks": c["blocks"],
                             "week_lo": c["week_lo"], "week_hi": c["week_hi"]})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=list(REFERENCE), required=True)
    a = ap.parse_args()
    f, avail, seasons = load(a.stage)
    R, meta = score(a.stage, f, avail, seasons)
    if a.stage == "confirm":
        ref = thinking_reference(f, avail, seasons)
        meta["thinking_reference"] = ref.to_dict("records")
    res = {"key": KEY, "stage": a.stage, "seasons": seasons, "reference": REFERENCE[a.stage],
           "population_rule": "excl_debut leaves out matches with a player whose first Stage 0 match is in the "
                              "match's season (audit B1); 'all' is the sensitivity", **meta,
           "comparisons": R.to_dict("records")}
    if a.stage == "pilot":
        fr = pd.read_parquet(C.OUT / "frame.parquet", columns=["season", "tour", "debut_season"])
        conf = fr[fr["season"].between(2022, 2026) & ~fr["debut_season"]]
        n_conf = {"atp": int((conf["tour"] == "atp").sum()), "wta": int((conf["tour"] == "wta").sum()),
                  "both": int(len(conf))}
        res["mde"] = mde(R, n_conf)
        C.write_json(C.OUT / "mde.json", res["mde"])
    C.write_json(C.OUT / f"results_{a.stage}.json", res)
    R.to_csv(C.OUT / f"results_{a.stage}.csv", index=False)
    f.to_parquet(C.OUT / f"predictions_{a.stage}.parquet", index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 500):
        show = R[(R["population"] == "excl_debut") & (R["subset"] == "all") & (R["window"] == f"{seasons[0]}-{seasons[-1]}")]
        print(show.drop(columns=["population", "subset", "window"]).round(3).to_string(index=False))
        print(json.dumps({k: v for k, v in meta["seasons_as_samples"].items() if k.startswith("excl_debut")}, indent=1))
        print(json.dumps(meta["log_loss_identical_rows"], indent=1))
        if "mde" in res:
            print(json.dumps(res["mde"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
