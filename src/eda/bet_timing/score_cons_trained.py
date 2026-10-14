"""Bet timing, step 5b: the models retrained on sharp books' closes (fits_cons_trained.py) against the current model, at
BetOnline's last line, 2020-2025.

    today   the current model: trained on the books' average close (all the books OddsPortal lists)
    pb      retrained on Pinnacle's close and BetOnline's last line averaged (Pinnacle alone before 2018)
    bo      retrained on BetOnline's last line (Pinnacle's close before 2018): the free choice once Pinnacle's closes stop

Every model is treated alike: each block's forecasts symmetrised and averaged over seeds 0-3, then one calibration slope
per tour on the log-odds, fitted on the model's own out-of-sample forecasts of 2019 .. Y - 1 fed its own training input
(debut seasons out). The speed stage is left out of all of them: its coefficients were fitted on the current model only,
and it changes men's forecasts alone, by the same rule.

The grid: every model fed every price, on the same matches (Pinnacle's close and BetOnline's last line both priced;
debut seasons out), against one baseline, the current model fed BetOnline's own line (mLL, + = more accurate than the
baseline); each cell's edge over BetOnline's last line; and the money at BetOnline's last line (the owner's staking).
At BetOnline's opening (inputs known at the opening): each model fed the opening line, against the current model.
Writes data/studies/bet_timing/results_cons_trained.json and cons_trained_tables.md. Reads results (score.load) only.
Run: ./python.sh src/eda/bet_timing/score_cons_trained.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.bet_timing import common as C  # noqa: E402
from src.eda.bet_timing import fits_cons_trained as FC  # noqa: E402
from src.eda.bet_timing import score as SS  # noqa: E402
from src.eda.tabpfn_thinking.common import fit_logistic, ll  # noqa: E402

SCORED = tuple(range(2020, 2026))
BLOCKS = ("own",) + FC.QUERY_BLOCKS
MODELS = {"today": "Today's model (trained on the books' average)",
          "pb": "Retrained on Pinnacle + BetOnline", "bo": "Retrained on BetOnline (Pinnacle before 2018)",
          "pf": "Retrained on Pinnacle first (BetOnline where Pinnacle has no faithful close)"}
INPUTS = {"bol_close": "BetOnline's own line", "ps_close": "Pinnacle's close",
          "cons_close": "Pinnacle + BetOnline average", "td": "The books' average",
          "own": "Its own training construction, at the close"}
BASELINE = "q_today_bol_close"


def arm_etas(arm: str) -> pd.DataFrame:
    cols: dict[str, list[pd.Series]] = {b: [] for b in BLOCKS}
    for season in FC.SEASONS:
        zs = [np.load(FC.fit_path(season, k, arm), allow_pickle=False) for k in C.SEEDS]
        try:
            for b in BLOCKS:
                if f"p_{b}" not in zs[0].files:
                    continue
                ids = zs[0][f"ids_{b}"].astype(str)
                per = [0.5 * (z[f"p_{b}"][:len(ids)] + 1 - z[f"p_{b}"][len(ids):]) for z in zs]
                cols[b].append(pd.Series(C.lg(np.mean(per, axis=0)), index=ids))
        finally:
            for z in zs:
                z.close()
    out = pd.DataFrame({f"eta_{arm}_{b}": pd.concat(v) for b, v in cols.items() if v})
    out.index.name = "match_id"
    return out


def arm_slopes(x: pd.DataFrame, arm: str) -> dict:
    """{season: {tour: slope}} on the arm's own-block log-odds of 2019 .. Y - 1, debut out."""
    out = {}
    hist = x[np.isfinite(x[f"eta_{arm}_own"].to_numpy(float)) & ~x["debut_season"].astype(bool).to_numpy()]
    for y in SCORED:
        out[y] = {}
        for t in ("atp", "wta"):
            g = hist[(hist["season"] < y) & (hist["tour"] == t)]
            beta, _ = fit_logistic(g[f"eta_{arm}_own"].to_numpy(float)[:, None], g["y"].to_numpy(float))
            out[y][t] = float(beta[0])
    return out


def current_slopes() -> dict:
    from src.eda.serve_speed_tabpfn import common as SC
    from src.eda.serve_speed_tabpfn import score as S
    P = SC.DEFAULT
    sc = S.Scorer(S.Bank(P, S.frame_index(P), require_checks=True), S.population(P), S.labels(P))
    return {y: sc.slopes("model", y) for y in SCORED}


def apply(eta: np.ndarray, tour: np.ndarray, season: np.ndarray, slopes: dict) -> np.ndarray:
    s = np.array([slopes[int(y)][t] if int(y) in slopes else np.nan for t, y in zip(tour, season)])
    return C.ex(s * eta)


def arms_available() -> list[str]:
    return [a for a in FC.ARMS if all(FC.fit_path(s, k, a).exists() for s in FC.SEASONS for k in C.SEEDS)]


def load() -> pd.DataFrame:
    x = pd.read_parquet(C.FRAME)
    x["match_id"] = x["match_id"].astype(str)
    x = x[x["season"].between(2019, 2025)].reset_index(drop=True)
    y = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "a_won"])          # THE ONLY READER OF RESULTS
    y["match_id"] = y["match_id"].astype(str)
    x = x.merge(y, on="match_id", how="left", validate="one_to_one")
    x["y"] = x["a_won"].astype(float)
    cf = pd.read_parquet(C.CONSENSUS_FRAME, columns=["match_id", "p_ps_close", "p_cons_close"])
    cf["match_id"] = cf["match_id"].astype(str)
    x = x.merge(cf, on="match_id", how="left", validate="one_to_one")
    seasons = tuple(range(2020, 2026))
    main = SS.etas(seasons, blocks=("td", "bol_close", "bol_open"))
    cons = SS.etas(seasons, price_set="consensus", blocks=("cons_close", "ps_close"))
    x = x.join(main, on="match_id").join(cons, on="match_id")
    tour, season = x["tour"].to_numpy(), x["season"].to_numpy()
    cur = current_slopes()
    for b in ("td", "bol_close", "bol_open", "cons_close", "ps_close"):
        x[f"q_today_{b}"] = apply(x[f"eta_{b}"].to_numpy(float), tour, season, cur)
    slopes = {"today": {str(k): v for k, v in cur.items()}}
    for arm in arms_available():
        x = x.join(arm_etas(arm), on="match_id")
        sl = arm_slopes(x, arm)
        slopes[arm] = {str(k): v for k, v in sl.items()}
        for b in BLOCKS:
            x[f"q_{arm}_{b}"] = apply(x[f"eta_{arm}_{b}"].to_numpy(float), tour, season, sl)
    x.attrs["slopes"] = slopes
    return x


def cells(x: pd.DataFrame) -> list[tuple[str, str, str]]:
    out = [("today", i, f"q_today_{i}") for i in INPUTS if i != "own"]
    for arm in [a for a in FC.ARMS if f"q_{a}_own" in x]:
        out += [(arm, i, f"q_{arm}_{i}") for i in ("bol_close", "ps_close", "cons_close")]
        if arm == "pf":       # its own construction is not one of the shared prices (a faithful Pinnacle close first)
            out.append((arm, "own", f"q_{arm}_own"))
    return out


def grid(g: pd.DataFrame, cs: list[tuple[str, str, str]], money: bool) -> list[dict]:
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    base = np.asarray(ll(g[BASELINE].to_numpy(float), y))
    price = np.asarray(ll(g["p_bol_close"].to_numpy(float), y))
    rows = []
    gc = g[g["status"].eq("completed").to_numpy()].reset_index(drop=True) if money else None
    for model, inp, col in cs:
        L = np.asarray(ll(g[col].to_numpy(float), y))
        r = {"model": model, "input": inp, "matches": int(len(g)), "vs_baseline": SS.mean_ci(base - L, blk),
             "edge_over_betonline_last_line": SS.mean_ci(price - L, blk)}
        if money:
            bk = gc["block"].to_numpy()
            own = SS.book_bets(gc, "bol_close", 0.0, q_col=BASELINE)["profit"].to_numpy()
            r["money"] = {}
            for tau in (0.0, 0.02, 0.05):
                s = SS.book_bets(gc, "bol_close", tau, q_col=col)
                own_t = SS.book_bets(gc, "bol_close", tau, q_col=BASELINE)["profit"].to_numpy() if tau else own
                r["money"][f"tau_{tau}"] = {
                    "bets": int(s["bet"].sum()),
                    "roi": SS.ratio_boot(s["profit"].to_numpy(), s["stake"].to_numpy(), bk, SS.seed_of(col, tau)),
                    "minus_baseline_per_100": SS.mean_ci(s["profit"].to_numpy() - own_t, bk, 100.0)}
        rows.append(r)
    return rows


def main() -> int:
    x = load()
    cs = cells(x)
    m = (x["season"].isin(SCORED) & ~x["debut_season"].astype(bool) & x["y"].notna()).to_numpy().copy()
    for c in ["p_bol_close", "p_ps_close", "p_cons_close"] + [c for _, _, c in cs]:
        m &= np.isfinite(x[c].to_numpy(float))
    near = x["h_bol_close"].to_numpy(float) <= 1.0
    res = {"slopes": x.attrs["slopes"], "models": MODELS, "inputs": INPUTS, "baseline": BASELINE, "grids": {}}
    for name, mask, money in (("all_last_lines", m, True), ("stamped_within_1h", m & near, False),
                              ("men", m & (x["tour"] == "atp").to_numpy(), False),
                              ("women", m & (x["tour"] == "wta").to_numpy(), False),
                              ("2020-2022", m & (x["season"] <= 2022).to_numpy(), False),
                              ("2023-2025", m & (x["season"] >= 2023).to_numpy(), False)):
        res["grids"][name] = grid(x[mask].reset_index(drop=True), cs, money)
    o = (x["season"].isin(SCORED) & ~x["debut_season"].astype(bool) & x["y"].notna() &
         x["known_bol_open"].astype(bool)).to_numpy().copy()
    opens = ["q_today_bol_open"] + [f"q_{a}_bol_open" for a in FC.ARMS if f"q_{a}_bol_open" in x]
    for c in opens:
        o &= np.isfinite(x[c].to_numpy(float))
    g = x[o].reset_index(drop=True)
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    base = np.asarray(ll(g["q_today_bol_open"].to_numpy(float), y))
    res["at_the_opening"] = {"matches": int(len(g)), "vs_today_fed_the_opening": {
        c.split("_")[1]: SS.mean_ci(base - np.asarray(ll(g[c].to_numpy(float), y)), blk) for c in opens[1:]}}
    C.write_json(C.OUT / "results_cons_trained.json", res)
    tables(res)
    return 0


def ci(d: dict, p: int = 2, scale: float = 1.0) -> str:
    return f"{scale * d['est']:+.{p}f} [{scale * d['lo']:+.{p}f}, {scale * d['hi']:+.{p}f}]"


def tables(res: dict) -> None:
    md = ["# Models retrained on sharp books (generated by src/eda/bet_timing/score_cons_trained.py)", "",
          "Each cell: one model fed one price, at BetOnline's last line, 2020-2025. mLL against the baseline (today's "
          "model fed BetOnline's own line), + = more accurate; a range spanning 0 is unresolved (the adoption "
          "framework of 9 Oct 2026: no comparison is called a tie).", ""]
    for name, rows in res["grids"].items():
        md += [f"## {name} ({rows[0]['matches']:,} matches)", ""]
        models = list(dict.fromkeys(r["model"] for r in rows))
        md += ["| Price fed | " + " | ".join(MODELS[mo] for mo in models) + " |",
               "|---|" + "---|" * len(models)]
        for inp, label in INPUTS.items():
            cellv = []
            for mo in models:
                r = next((r for r in rows if r["model"] == mo and r["input"] == inp), None)
                cellv.append(ci(r["vs_baseline"]) if r else "not tested")
            md.append(f"| {label} | " + " | ".join(cellv) + " |")
        if "money" in rows[0]:
            md += ["", "| Model | Price fed | Threshold | Bets | ROI | Minus the baseline, per 100 matches |",
                   "|---|---|---|---:|---|---|"]
            for r in rows:
                for tau, s in r["money"].items():
                    md.append(f"| {MODELS[r['model']]} | {INPUTS[r['input']]} | {tau[4:]} | {s['bets']:,} | "
                              f"{ci(s['roi'], 1, 100)}% | {ci(s['minus_baseline_per_100'])} |")
        md.append("")
    o = res["at_the_opening"]
    md += [f"## At BetOnline's opening ({o['matches']:,} matches; each fed the opening line, against today's model)", ""]
    md += [f"* {MODELS[k]}: {ci(v)}" for k, v in o["vs_today_fed_the_opening"].items()]
    (C.OUT / "cons_trained_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {C.OUT / 'cons_trained_tables.md'}")


if __name__ == "__main__":
    sys.exit(main())
