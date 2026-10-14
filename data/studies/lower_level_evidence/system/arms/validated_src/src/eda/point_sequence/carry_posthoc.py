"""B1 post-hoc diagnostics, run after the pre-registered result (carry_prereg.md, "Deviations after estimation").
Nothing here changes the pass rule or its verdict.

1. Replay-offset stability. The primary replay null of the replication window centred at -0.0018, just outside its
   pre-set band. 100 further replays per window (tour x surface de-noising, new seeds) show whether that centre is
   stable (an offset tied to this data set, from small departures of set 1 and the late set from exchangeability in
   the replay, such as who serves first in each set) or chance.
2. Exchangeability in the replays. Per replay: the mean late-minus-early residual and the two residuals' spreads,
   split by whether the triple's player served first in set 1.
3. Size and power. The finishing-form contrast per SD of (late - early) residual, turned into next-match serve-point
   percentage points; the minimum detectable Delta (80% power, two-sided 5%); and a post-hoc inverse-variance pool of
   the two windows' Delta (not pre-registered; descriptive only).

Run: ./python.sh src/eda/point_sequence/carry_posthoc.py [--replays 100] [--workers 4]
Writes data/studies/point_sequence/carry_posthoc.json and carry_posthoc_replays.csv.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import carry_fit as F  # noqa: E402
from src.eda.point_sequence import carry_sim as S  # noqa: E402

OUT = ROOT / "data" / "studies" / "point_sequence"
POSTHOC = OUT / "carry_posthoc.json"
POSTHOC_REPLAYS = OUT / "carry_posthoc_replays.csv"
SEED_BASE = 1000


def _job(args) -> list[dict]:
    path, prior_records, seeds = args
    tri_all = pd.read_parquet(path)
    prior = pd.DataFrame(prior_records)
    rows = []
    for seed in seeds:
        for w in ("discovery", "replication"):
            tri = tri_all[tri_all["window"] == w].reset_index(drop=True)
            rep, info = S.replay_triples(tri, prior, seed=seed * 7 + (0 if w == "discovery" else 1))
            rt = F.replayed_exposures(tri, rep)
            res = F.estimate(F.design(rt), F.standard_contrasts())
            first = (tri["s0"].to_numpy() == tri["side_t"].to_numpy())
            dlt = (rt["rL"] - rt["rE"]).to_numpy()
            row = {"window": w, "seed": seed, "never_matched": info["never_matched"],
                   "mean_L_minus_E": float(dlt.mean()),
                   "mean_L_minus_E_served_first": float(dlt[first].mean()),
                   "mean_L_minus_E_served_second": float(dlt[~first].mean()),
                   "sd_rE": float(rt["rE"].std()), "sd_rL": float(rt["rL"].std()),
                   "mean_n1": float(rep["n1"].mean()), "mean_nL": float(rep["nL"].mean())}
            for k, v in res["contrasts"].items():
                row[k] = v["est"]
                row[f"{k}_se"] = v["se"]
            rows.append(row)
    return rows


def main(args) -> None:
    res = json.loads((OUT / "carry_results.json").read_text(encoding="utf-8"))
    tri = pd.read_parquet(F.TRIPLES)
    out: dict = {"note": "post hoc; not part of the pre-registered pass rule"}

    # 1-2. extra replays
    prior = S.frozen_prior()
    seeds = list(range(SEED_BASE + 1, SEED_BASE + args.replays + 1))
    chunks = [seeds[i::args.workers] for i in range(args.workers)]
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for part in ex.map(_job, [(str(F.TRIPLES), prior.to_dict(orient="records"), ch) for ch in chunks if ch]):
            rows += part
    extra = pd.DataFrame(rows).sort_values(["window", "seed"])
    extra.to_csv(POSTHOC_REPLAYS, index=False)
    first50 = pd.read_csv(OUT / "carry_replay_null.csv")
    first50 = first50[first50["mode"] == "tour_mean"]
    for w in ("discovery", "replication"):
        x = extra.loc[extra["window"] == w, "delta"].to_numpy()
        allx = np.concatenate([x, first50.loc[first50["window"] == w, "delta"].to_numpy()])
        d = tri[tri["window"] == w]
        first = d["s0"].to_numpy() == d["side_t"].to_numpy()
        real_dlt = (d["rL"] - d["rE"]).to_numpy()
        e = extra[extra["window"] == w]
        out[f"replay_offset_{w}"] = {
            "extra_replays": int(len(x)), "extra_mean": float(x.mean()), "extra_sd": float(x.std(ddof=1)),
            "extra_se_of_mean": float(x.std(ddof=1) / np.sqrt(len(x))),
            "all_replays": int(len(allx)), "all_mean": float(allx.mean()),
            "all_se_of_mean": float(allx.std(ddof=1) / np.sqrt(len(allx))),
            "replay_mean_L_minus_E": float(e["mean_L_minus_E"].mean()),
            "replay_mean_L_minus_E_served_first": float(e["mean_L_minus_E_served_first"].mean()),
            "replay_mean_L_minus_E_served_second": float(e["mean_L_minus_E_served_second"].mean()),
            "replay_sd_rE": float(e["sd_rE"].mean()), "replay_sd_rL": float(e["sd_rL"].mean()),
            "replay_mean_n1": float(e["mean_n1"].mean()), "replay_mean_nL": float(e["mean_nL"].mean()),
            "real_mean_L_minus_E": float(real_dlt.mean()),
            "real_mean_L_minus_E_served_first": float(real_dlt[first].mean()),
            "real_mean_L_minus_E_served_second": float(real_dlt[~first].mean()),
            "real_share_served_first_in_set1": float(first.mean())}

    # 3. size, power and the post-hoc pool
    for w in ("discovery", "replication"):
        d = tri[tri["window"] == w]
        p = res[f"primary_{w}"]
        sd_ff = float((d["rL"] - d["rE"]).std()) * F.SCALE           # SD of (late - early), in 10-pp units
        pq = float((d["ps_p"] * (1 - d["ps_p"])).mean())
        # forward linear predictor: (b_L - b_E)/2 per 10 pp of (late - early); Delta / 2 is its excess over reverse
        out[f"size_{w}"] = {
            "sd_late_minus_early_pp": sd_ff * 10, "mean_p_one_minus_p_endpoint": pq,
            "delta_per_sd_logodds": p["delta"]["est"] / 2 * sd_ff,
            "delta_per_sd_serve_pp": 100 * pq * p["delta"]["est"] / 2 * sd_ff,
            "delta_hi_per_sd_serve_pp": 100 * pq * p["delta"]["hi"] / 2 * sd_ff,
            "fwd_L_minus_E_per_sd_serve_pp": 100 * pq * p["fwd_L_minus_E"]["est"] / 2 * sd_ff,
            "mde80_delta": 2.80 * p["delta"]["se"],
            "mde80_per_sd_serve_pp": 100 * pq * 2.80 * p["delta"]["se"] / 2 * sd_ff}
    a, b = res["primary_discovery"]["delta"], res["primary_replication"]["delta"]
    wa, wb = 1 / a["se"] ** 2, 1 / b["se"] ** 2
    est = (a["est"] * wa + b["est"] * wb) / (wa + wb)
    se = 1 / np.sqrt(wa + wb)
    out["posthoc_pool_two_windows"] = {"est": est, "se": se, "lo": est - 1.96 * se, "hi": est + 1.96 * se,
                                       "caveat": "inverse-variance pool of independent windows; players recur across "
                                                 "windows, so the interval is slightly optimistic; not pre-registered"}
    POSTHOC.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", type=int, default=100)
    ap.add_argument("--workers", type=int, default=4)
    main(ap.parse_args())
