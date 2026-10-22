"""Part F, step 3: a "Pinnacle proxy", fitted where Pinnacle's close is known, and how close it comes to Pinnacle.

Where Pinnacle's reconciled close is known (2018 to 7 Sep 2025; pools.reconciled, the model's own Pinnacle input),
Pinnacle's margin-free log-odds are regressed on the other books' (ordinary least squares, no intercept: side A is
random, so a proxy must treat the two sides alike). One fit per pattern of priced books, so a match lacking a book uses
the fit made without it. The fits read no result.

    proxy          books {BetOnline, Bet365, average, maximum, OddsTrader's other books' median}; fitted on
                   2018-01-01 .. 2025-07-31 (declared)
    proxy_recent   the same books, fitted on 2023-08-01 .. 2025-07-31 (declared variant)
    proxy_bol      BetOnline alone, rescaled to Pinnacle's scale (declared variant)
    proxy_b105     the five books and Bet105 (added; Bet105 is listed from April 2025, so its patterns are fitted on
                   2025-04 .. 2025-07)

Scored against Pinnacle itself, out of sample (reads no result):
    * walk-forward by season, 2019-2025 (fit on 2018 .. Y-1, up to 31 Jul 2025; scored on season Y to 31 Jul 2025);
    * the post-change window, 1 Aug - 7 Sep 2025: the books' average and maximum changed their panel in August 2025 and
      Pinnacle is known there only through OddsTrader's recording. Fit on 2018-01-01 .. 2025-07-31.
Distance: KL(Pinnacle || candidate), mLL (the log loss a candidate gives away if Pinnacle's chance were the truth), and
the root mean square gap in log-odds. Each candidate against BetOnline (today's stand-in) on the same matches, with
95% intervals: four-week blocks for the seasons, match days for the five-week window.
Scored against results in the gap: odds_score.py.

Writes data/studies/source_reconciliation/odds/proxy.json and proxy_tables.md (coefficients and aggregates only).
Run: ./python.sh src/eda/source_reconciliation/odds_proxy.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import odds_common as O  # noqa: E402

BOOKS = ["bol", "b365", "avg", "max", "otmed"]
VARIANTS = {
    "proxy": (BOOKS, "2018-01-01", "2025-07-31"),
    "proxy_recent": (BOOKS, "2023-08-01", "2025-07-31"),
    "proxy_bol": (["bol"], "2018-01-01", "2025-07-31"),
    "proxy_b105": (BOOKS + ["b105"], "2018-01-01", "2025-07-31"),
}
DROP_ORDER = ["b105", "max", "otmed", "b365", "bol", "avg"]   # a pattern with too few fit rows loses these first
MIN_FIT = 300
WINDOW = ("2025-08-01", "2025-09-07")


class Proxy:
    """Per-pattern least-squares fits of Pinnacle's log-odds on the books' log-odds, no intercept."""

    def __init__(self, members: list[str]):
        self.members = list(members)
        self.fits: dict[tuple[str, ...], dict] = {}

    def _fit_pattern(self, Z: np.ndarray, zp: np.ndarray, fit: np.ndarray, pat: tuple[str, ...]):
        if pat in self.fits:
            return self.fits[pat]
        cols = [self.members.index(m) for m in pat]
        rows = fit & np.isfinite(Z[:, cols]).all(axis=1)
        if rows.sum() < MIN_FIT:
            self.fits[pat] = None
            return None
        X = Z[rows][:, cols]
        beta, *_ = np.linalg.lstsq(X, zp[rows], rcond=None)
        resid = zp[rows] - X @ beta
        self.fits[pat] = {"books": list(pat), "beta": [round(float(b), 4) for b in beta], "n_fit": int(rows.sum()),
                          "rmse_in_sample": round(float(np.sqrt(np.mean(resid ** 2))), 4), "_beta": beta}
        return self.fits[pat]

    def fit_predict(self, df: pd.DataFrame, fit_mask: np.ndarray, pred_mask: np.ndarray) -> np.ndarray:
        Z = O.lg(df[[f"p_{m}" for m in self.members]].to_numpy(float))
        zp = O.lg(df["p_pin"].to_numpy(float))
        fit = fit_mask & np.isfinite(zp)
        have = np.isfinite(Z)
        out = np.full(len(df), np.nan)
        idx = np.flatnonzero(pred_mask & have.any(axis=1))
        keys = pd.Series([tuple(m for m, h in zip(self.members, have[i]) if h) for i in idx], index=idx)
        for pat, rows in keys.groupby(keys).groups.items():
            p = tuple(pat)
            res = self._fit_pattern(Z, zp, fit, p)
            while res is None and len(p) > 1:
                drop = next(m for m in DROP_ORDER if m in p)
                p = tuple(m for m in p if m != drop)
                res = self._fit_pattern(Z, zp, fit, p)
            if res is None:
                continue
            r = np.asarray(list(rows))
            cols = [self.members.index(m) for m in p]
            out[r] = O.ex(Z[r][:, cols] @ res["_beta"])
        return out

    def describe(self) -> list[dict]:
        return [{k: v for k, v in f.items() if k != "_beta"} for f in self.fits.values() if f]


def fit_mask(df: pd.DataFrame, lo: str, hi: str) -> np.ndarray:
    return ((df["td_date"] >= lo) & (df["td_date"] <= hi) & df["pin_known"]).to_numpy()


def proxies(df: pd.DataFrame, pred_mask: np.ndarray, hi: str | None = None) -> tuple[dict, dict]:
    """Every proxy variant fitted on its window (cut at `hi` when given) and predicted on pred_mask."""
    out, fits = {}, {}
    for name, (members, lo, top) in VARIANTS.items():
        top = min(top, hi) if hi else top
        pr = Proxy(members)
        out[name] = pr.fit_predict(df, fit_mask(df, lo, top), pred_mask)
        fits[name] = {"books": members, "fit_from": lo, "fit_to": top, "patterns": pr.describe()}
    return out, fits


def distance_table(df: pd.DataFrame, cands: dict, mask: np.ndarray, clusters: np.ndarray, base: str = "bol") -> dict:
    """KL(Pinnacle || candidate) (mLL) and RMSE of log-odds for each candidate on its own priced rows, and the paired
    KL difference against `base` (+ = the candidate further from Pinnacle)."""
    pin = df["p_pin"].to_numpy(float)
    zp = O.lg(pin)
    out = {}
    for name, p in cands.items():
        m = mask & np.isfinite(p) & np.isfinite(pin)
        if m.sum() < 30:
            out[name] = {"n": int(m.sum())}
            continue
        k = O.kl(pin[m], p[m])
        row = {"n": int(m.sum()), "kl_mll": round(1000 * float(k.mean()), 4),
               "rmse_logodds": round(float(np.sqrt(np.mean((O.lg(p[m]) - zp[m]) ** 2))), 4),
               "median_abs_logodds": round(float(np.median(np.abs(O.lg(p[m]) - zp[m]))), 4)}
        if name != base:
            b = cands[base]
            mm = m & np.isfinite(b)
            if mm.sum() >= 30:
                row["kl_minus_" + base] = O.ci(O.kl(pin[mm], p[mm]) - O.kl(pin[mm], b[mm]), clusters[mm])
        out[name] = row
    return out


def candidates(df: pd.DataFrame, extra: dict) -> dict:
    c = {s: df[f"p_{s}"].to_numpy(float) for s in ["bol", "b105", "b105_pre", "otmed", "max", "avg", "b365", "bfe",
                                                   "psx", "pm"]}
    c["eq_bol+b105"] = O.equal(df, ["bol", "b105"])
    c["eq_bol+otmed"] = O.equal(df, ["bol", "otmed"])
    c["eq_bol+bfe"] = O.equal(df, ["bol", "bfe"])
    c["eq_bol+max"] = O.equal(df, ["bol", "max"])
    c.update(extra)
    return c


def walk_forward(df: pd.DataFrame) -> dict:
    season = df["season"].to_numpy()
    out = {}
    for yr in range(2019, 2026):
        pred = (season == yr) & (df["td_date"] <= "2025-07-31").to_numpy() & df["pin_known"].to_numpy()
        hi = f"{yr - 1}-12-31"
        prx, fits = proxies(df, pred, hi=hi)
        prx = {k: v for k, v in prx.items() if k != "proxy_recent" or yr >= 2025}   # its window needs 2023-08 on
        out[str(yr)] = distance_table(df, candidates(df, prx), pred, df["block"].to_numpy())
    return out


def window(df: pd.DataFrame) -> tuple[dict, dict]:
    pred = ((df["td_date"] >= WINDOW[0]) & (df["td_date"] <= WINDOW[1]) & df["pin_known"]).to_numpy()
    prx, fits = proxies(df, pred)
    day = (df["td_date"].to_numpy("datetime64[D]") - np.datetime64("2010-01-01")).astype(int)
    return distance_table(df, candidates(df, prx), pred, day), {
        "n": int(pred.sum()), "pinnacle_recording": {k: int(v) for k, v in
                                                     pd.Series(df.loc[pred, "pin_choice"]).value_counts().items()}}


def gap_coverage(df: pd.DataFrame) -> dict:
    pred = df["gap"].to_numpy()
    prx, fits = proxies(df, pred)
    return {"fits": fits, "gap_rows": int(pred.sum()),
            "priced": {k: int(np.isfinite(v[pred]).sum()) for k, v in prx.items()}}


def tables(res: dict) -> str:
    L = ["# Pinnacle proxy: distance to Pinnacle's own close (generated by odds_proxy.py)", "",
         "KL = KL(Pinnacle || candidate), mLL: the log loss the candidate gives away if Pinnacle's chance were the truth "
         "(lower = nearer Pinnacle). \"− BetOnline\": the paired KL difference, + = the candidate further from "
         "Pinnacle than BetOnline. Reads no result.", ""]
    w = res["window"]
    L += [f"## The post-change window, {WINDOW[0]} .. {WINDOW[1]} ({res['window_info']['n']} matches with Pinnacle's "
          "close; 95% intervals over match days)", "",
          "| Candidate | Matches | KL, mLL | RMSE log-odds | KL − BetOnline |", "|---|---:|---:|---:|---|"]
    for name, r in sorted(w.items(), key=lambda kv: kv[1].get("kl_mll", 9e9)):
        if "kl_mll" not in r:
            continue
        L.append(f"| {O.short(name)} | {r['n']:,} | {r['kl_mll']:.3f} | {r['rmse_logodds']:.4f} | "
                 f"{O.fmt_v(r.get('kl_minus_bol'), 3)} |")
    L += ["", "## Walk-forward by season (fit on 2018 .. Y−1; scored on Y to 31 Jul 2025): KL, mLL "
          "(KL − BetOnline, 95% interval over four-week blocks)", ""]
    names = ["proxy", "proxy_recent", "proxy_bol", "proxy_b105", "bol", "otmed", "max", "avg", "b365", "b105",
             "eq_bol+otmed", "eq_bol+max"]
    L += ["| Season | " + " | ".join(O.short(n) for n in names) + " |", "|---|" + "---|" * len(names)]
    for yr, row in res["walk_forward"].items():
        cells = []
        for n in names:
            r = row.get(n, {})
            if "kl_mll" not in r:
                cells.append("—")
            elif n == "bol":
                cells.append(f"{r['kl_mll']:.3f} ({r['n']:,})")
            else:
                d = r.get("kl_minus_bol")
                cells.append(f"{r['kl_mll']:.3f}" + (f" ({O.fmt(d, 3)})" if d and d.get("est") is not None else ""))
        L.append(f"| {yr} | " + " | ".join(cells) + " |")
    L += ["", "## The fits used in the gap (fitted on their declared windows)", ""]
    for name, f in res["gap"]["fits"].items():
        L.append(f"**{name}** (books {', '.join(f['books'])}; fitted {f['fit_from']} .. {f['fit_to']}):")
        L.append("")
        L.append("| Books in the pattern | Coefficients | Fit rows | In-sample RMSE |")
        L.append("|---|---|---:|---:|")
        for p in sorted(f["patterns"], key=lambda r: -r["n_fit"]):
            L.append(f"| {', '.join(p['books'])} | {', '.join(f'{b:+.3f}' for b in p['beta'])} | {p['n_fit']:,} | "
                     f"{p['rmse_in_sample']:.4f} |")
        L.append("")
    L += [f"Gap rows priced by each proxy: {res['gap']['priced']} of {res['gap']['gap_rows']:,}.", ""]
    return "\n".join(L) + "\n"


def main() -> int:
    O.OUT.mkdir(parents=True, exist_ok=True)
    df = O.load_table()
    w, winfo = window(df)
    res = {"rule": {"variants": {k: {"books": v[0], "fit_from": v[1], "fit_to": v[2]} for k, v in VARIANTS.items()},
                    "min_fit_rows": MIN_FIT, "drop_order": DROP_ORDER, "window": WINDOW},
           "window": w, "window_info": winfo, "walk_forward": walk_forward(df), "gap": gap_coverage(df),
           "inputs_sha256": O.sha_inputs()}
    O.write_json(O.OUT / "proxy.json", res)
    (O.OUT / "proxy_tables.md").write_text(tables(res), encoding="utf-8")
    print(tables(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
