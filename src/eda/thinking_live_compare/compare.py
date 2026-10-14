"""TabPFN-3.5-Thinking on live matches: step 3, Thinking beside the local model (tennis env). Computes nothing paid.

Reads predict_api.py's probabilities, symmetrises each match's two orientations as the local fit does
(serve_speed_tabpfn.common.symmetrize), and sets beside each match of the runs:
    local_tabpfn_a     the local model's symmetrised 16-seed mean, before stage 2 (predictions.csv p_base_a)
    local_final_a      the current best model's forecast: stage 2 applied (q_a, read off its curve at the price used)
    thinking_a         Thinking, seed 0, symmetrised, NOT calibrated (the owner's word): its own probability
    thinking_speed_a   for reference only: Thinking plus stage 2's serve-speed term without the slope,
                       expit(logit(thinking_a) + b_shrunk * spd_L) (the 8 Oct research rule's form)
each at the price of the run's latest bet-sheet record (Pinnacle's, read off the grid when it moved), and the expected
profit per unit at Pinnacle's odds (margin included) and at a venue's prices (venue_prices.json: {player: odds}).

    ./python.sh src/eda/thinking_live_compare/compare.py --out <folder> <run folder> [<run folder> ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "eda" / "daily_prediction"))

import dp_fit  # noqa: E402

from src.eda.merge_feasibility.scan import name_key  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.tabpfn_thinking58 import guard as G  # noqa: E402
from src.pipeline.diagnostics import _payout  # noqa: E402  (odds or a share price -> decimal payout)


def thinking_curves(out: Path) -> dict:
    """{match_id: (grid of 91 symmetrised probabilities of side A, own-price probability, own logit)}."""
    q = json.loads((out / "query.json").read_text(encoding="utf-8"))
    _, p1, _, _ = G.load_predictions(out / "predictions.npz", None, int(q["rows"]))
    res = {}
    for s in q["segments"]:
        p = np.asarray(p1[s["start"]:s["start"] + s["rows"]], dtype="float64")
        k, n = s["stored_rows"], s["matches"]
        ps = C.symmetrize(p[:k], p[k:])
        grid = ps[:n * len(dp_fit.GRID)].reshape(n, -1)
        own = ps[n * len(dp_fit.GRID):]
        for i, mid in enumerate(s["match_id"]):
            res[str(mid)] = (grid[i], float(own[i]), float(s["own_logit"][i]))
    return res


def latest_record(run: Path) -> pd.DataFrame:
    """The run's newest bet-sheet record (predictions/<day>/records/bet_sheet_*.csv naming this run)."""
    pred = pd.read_csv(run / "predictions.csv")
    day = str(pred["day"].min())[:10]
    recs = []
    for f in sorted((ROOT / "predictions" / day / "records").glob("bet_sheet_*.csv")):
        prov = f.with_suffix(".provenance.json")
        if prov.exists() and run.name in prov.read_text(encoding="utf-8"):
            recs.append(f)
    if not recs:
        raise SystemExit(f"{run.name}: no bet-sheet record")
    r = pd.read_csv(recs[-1])
    return r[r["match_id"].notna() & r["player_a_id"].notna()].astype({"match_id": str}).assign(_record=recs[-1].name)


def compare(runs: list[Path], out: Path) -> pd.DataFrame:
    curves = thinking_curves(out)
    venue = json.loads((out / "venue_prices.json").read_text(encoding="utf-8")) if (out / "venue_prices.json").exists() else {}
    vkeys = {name_key(k): v for k, v in venue.items()}
    rows = []
    for run in runs:
        pred = pd.read_csv(run / "predictions.csv").astype({"match_id": str}).set_index("match_id")
        prov = json.loads((run / "provenance.json").read_text(encoding="utf-8"))
        coef = prov["stage2"]["coefficients"][str(int(str(pred["day"].iloc[0])[:4]))]
        for _, r in latest_record(run).iterrows():
            mid = r["match_id"]
            grid, own, own_logit = curves[mid]
            p_now = float(r["p_market_a"])
            th = own if abs(logit(p_now) - own_logit) < 1e-9 else float(dp_fit.interp(np.array([logit(p_now)]),
                                                                                   grid[None, :])[0])
            spd = float(pred.loc[mid, "spd_L"])
            th_speed = float(expit(logit(th) + coef["b_shrunk"] * spd))
            row = {"match": f"{r['player_a']} v {r['player_b']}", "player_a": r["player_a"], "player_b": r["player_b"],
                   "start_utc": r.get("start_utc"), "price_quoted_at": r.get("price_quoted_at"),
                   "market_a": p_now, "local_tabpfn_a": float(pred.loc[mid, "p_base_a"]),
                   "local_final_a": float(r["q_a"]), "thinking_a": th, "thinking_own_price_a": own,
                   "thinking_speed_a": th_speed, "spd_L": spd,
                   "pinnacle_odds_a": float(r["pinnacle_odds_a"]), "pinnacle_odds_b": float(r["pinnacle_odds_b"]),
                   "record": r["_record"], "run": run.name, "match_id": mid}
            for side, name in (("a", r["player_a"]), ("b", r["player_b"])):
                v = vkeys.get(name_key(name))
                row[f"venue_odds_{side}"] = float(_payout(v)) if v is not None else np.nan
            for model in ("local_final", "thinking", "thinking_speed"):
                qa = row[f"{model}_a"]
                for book in ("pinnacle", "venue"):
                    ev_a = qa * row[f"{book}_odds_a"] - 1
                    ev_b = (1 - qa) * row[f"{book}_odds_b"] - 1
                    best = "a" if ev_a >= ev_b else "b"
                    row[f"{model}_{book}_pick"] = row[f"player_{best}"] if max(ev_a, ev_b) > 0 else "no bet"
                    row[f"{model}_{book}_ev"] = max(ev_a, ev_b)
            rows.append(row)
    res = pd.DataFrame(rows).sort_values("start_utc")
    res.to_csv(out / "comparison.csv", index=False)
    show = res[["match", "market_a", "local_tabpfn_a", "local_final_a", "thinking_a", "thinking_speed_a",
                "local_final_pinnacle_pick", "local_final_pinnacle_ev", "thinking_pinnacle_pick", "thinking_pinnacle_ev",
                "thinking_venue_pick", "thinking_venue_ev"]]
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.float_format", "{:.4f}".format):
        print(show.to_string(index=False))
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("runs", nargs="+", type=Path)
    a = ap.parse_args()
    compare(a.runs, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
