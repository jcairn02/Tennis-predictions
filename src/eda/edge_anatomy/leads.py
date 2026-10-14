"""The edge-anatomy study's per-statistic ledger: for each of the model's non-price inputs and each tour, what the
recent (2025 - 28 Jul 2026) closing line prices, with the multiplicity of the scan accounted for.

Joins scan_inputs.csv / scan_learning.csv (each input beyond the model's own close, by era) and linemove.csv (beyond
BetOnline's opening line, the open-to-close move, beyond BetOnline's last line). Benjamini-Hochberg q-values over the
2025-26 tests of one tour (about 49 inputs), from the two-sided normal p of the scan's z, and (since 12 Oct 2026, the red
team's F7) from t on G - 1 degrees of freedom, G the window's four-week blocks: the small-sample version. Labels (descriptive, fixed in
this file before the table was read):
    never priced         |z| >= 2 beyond the close in the scan and beyond BetOnline's last line, same sign
    learned by the close |z_open| >= 2, z_move of the same sign with |z_move| >= 2, and |z| < 2 beyond both closes
    partly learned       |z_open| >= 2, |z_move| >= 2 of the same sign, and still |z| >= 2 beyond a close
    priced               |z| < 2 beyond the opening and both closes
    mixed                anything else
Writes data/studies/edge_anatomy/ledger.csv.
Run: ./python.sh src/eda/edge_anatomy/leads.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402

STAT = {"ace": "aces", "df": "double faults", "first_in": "first serves in", "first_won": "first-serve points won",
        "second_won": "second-serve points won", "hold": "service games held", "bp_saved": "break points saved",
        "bp_faced_pg": "break points faced per service game", "brk": "return games won",
        "bp_conv": "break points converted", "rpw_first": "return points won on the first serve",
        "rpw_second": "return points won on the second serve"}
FIXED = {"adjperf_tpw_2w": "two-week opponent-adjusted share of points won",
         "ratings_iid": "serve/return rating matchup (point model)", "elo_games": "games-weighted Elo",
         "elo_overall": "overall Elo", "elo_surf_offset": "surface part of Elo", "points_52w": "ranking points, 52 weeks",
         "sets_14d": "sets played in the last 14 days (incl. this event)", "age": "age", "age_sq": "age squared",
         "surf_season": "matches on this surface this season", "surf_layoff": "days since the last match on this surface",
         "speed": "recent change in first-serve speed (stage 2)"}


def plain(c: str) -> str:
    if c in FIXED:
        return FIXED[c]
    for pre, txt in (("formdef_", "two-week defence: opponents held below their norm on "),
                     ("form_", "two-week form: "), ("iosO_", "long-memory serving strength: "),
                     ("iosD_", "long-memory returning strength (suppressing the server): "),
                     ("prod_", "serve-vs-return matchup product: ")):
        if c.startswith(pre):
            return txt + STAT.get(c[len(pre):], c[len(pre):])
    return c


def bh(p: np.ndarray) -> np.ndarray:
    n = len(p)
    order = np.argsort(p)
    q = p[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(q, 1.0)
    return out


def label(r) -> str:
    zc1, zc2, zo, zm = r["z_2025_26"], r["z_close_bol"], r["z_open"], r["z_move"]
    if not np.isfinite(zo):
        return "—"
    if abs(zc1) >= 2 and abs(zc2) >= 2 and np.sign(zc1) == np.sign(zc2):
        if abs(zo) >= 2 and abs(zm) >= 2 and np.sign(zm) == np.sign(zo):
            return "partly learned by the close"
        return "never priced"
    if abs(zo) >= 2 and abs(zm) >= 2 and np.sign(zm) == np.sign(zo) and abs(zc1) < 2 and abs(zc2) < 2:
        return "learned by the close"
    if abs(zo) < 2 and abs(zc1) < 2 and abs(zc2) < 2:
        return "priced"
    return "mixed"


def run() -> pd.DataFrame:
    learn = pd.read_csv(E.OUT / "scan_learning.csv")
    learn = learn[learn["tour"].isin(["atp", "wta"])]
    lm = pd.read_csv(E.OUT / "linemove.csv")
    lm = lm[lm["window"] == "2025-26"][["tour", "input", "z_open", "z_move", "z_close"]].rename(
        columns={"z_close": "z_close_bol"})
    t = learn.merge(lm, on=["tour", "input"], how="left")
    t["p_2025_26"] = 2 * norm.sf(np.abs(t["z_2025_26"]))
    t["q_2025_26"] = np.nan
    # Small-sample version (the red team's F7, 12 Oct 2026): the z's are cluster-robust over the window's four-week
    # blocks, so the p-value comes from t on G - 1 degrees of freedom, G the blocks of 2025 - 28 Jul 2026
    a = pd.read_parquet(E.OUT / "analysis.parquet", columns=["season", "tour", "block", "debut"])
    a = a[a["season"].isin((2025, 2026)) & ~a["debut"]]
    G = {tour: int(g["block"].nunique()) for tour, g in a.groupby("tour")}
    t["blocks_2025_26"] = t["tour"].map(G)
    t["p_t_2025_26"] = [2 * student_t.sf(abs(z), g - 1) for z, g in zip(t["z_2025_26"], t["blocks_2025_26"])]
    t["q_t_2025_26"] = np.nan
    for tour, g in t.groupby("tour"):
        t.loc[g.index, "q_2025_26"] = bh(g["p_2025_26"].to_numpy())
        t.loc[g.index, "q_t_2025_26"] = bh(g["p_t_2025_26"].to_numpy())
    t["what"] = t["input"].map(plain)
    t["label"] = t.apply(label, axis=1)
    t["direction"] = np.where(t["z_2025_26"] > 0, "the player higher on it beats the price",
                              "the player higher on it loses to the price")
    cols = ["tour", "family", "input", "what", "label", "direction", "z_2013_24", "z_2025_26", "q_2025_26",
            "blocks_2025_26", "p_t_2025_26", "q_t_2025_26",
            "beta_2013_24", "beta_2025_26", "z_change", "z_open", "z_move", "z_close_bol"]
    return t[cols].sort_values(["tour", "label", "family", "input"])


def main() -> int:
    t = run()
    t.to_csv(E.OUT / "ledger.csv", index=False)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 200)
    pd.set_option("display.max_colwidth", 60)
    print(t.drop(columns=["what", "direction"]).round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
