"""When can a check on unseen matches answer? (serve/return-leads study, step 2)

Outcome-free for the unseen matches: the men's main-tour matches from 29 Jul 2026 in the newest instance's frame
(template_2026-10-14, read without its result column), and, after its last day, the same calendar days one year earlier
as the projection of what will arrive. The four-week blocks they span (the test's clusters).

The strength each score had where the traits were found (men, 1 Jan 2025 - 28 Jul 2026, seen) and in 2013-24 (seen),
beyond the close with the registered fit. Then the chance that a one-sided test on the unseen matches confirms, for each
date and for several shares of the 2025-26 strength surviving ("realisation"):
    1      the 2025-26 effect is real and unchanged
    0.45   the typical survival of a screened statistic (unpriced leads' cross-era reliability)
    0.25
    r_old  back to the 2013-24 strength
    0      no effect (the false-confirmation rate)
The power uses the noncentral t on G - 1 degrees of freedom, the standard error scaled from the seen window by
sqrt(n_seen / N). Designs: one look at a fixed date (one-sided 0.05), and three looks (Pocock, one-sided 0.0221 each).

Writes data/studies/serve_return_leads/timeline.json and timeline.csv.
Run: ./python.sh src/eda/serve_return_leads/timeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import nct
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

NEWEST = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-14" / "model_frame.parquet"
DATES = ["2026-09-23", "2026-10-31", "2026-11-30", "2027-01-31", "2027-02-28", "2027-03-31", "2027-04-30",
         "2027-05-31", "2027-06-30", "2027-07-31", "2027-08-31", "2027-10-31", "2027-12-31"]
POCOCK_3 = 0.0221          # one-sided nominal level per look for three equally spaced looks, overall 0.05
SCENARIOS = ("1", "0.45", "0.25", "r_old", "0")


def unseen_calendar() -> pd.DataFrame:
    """Men's main-tour matches from 29 Jul 2026 by tournament date: actual to the frame's last day, then projected."""
    f = pd.read_parquet(NEWEST, columns=["tour", "tournament_date", "debut_season"])
    f = f[(f["tour"] == "atp") & ~f["debut_season"].astype(bool)]
    last = f["tournament_date"].max()
    actual = f[f["tournament_date"] >= C.SEALED_FROM]["tournament_date"]
    year_ago = f[(f["tournament_date"] > last - pd.DateOffset(years=1)) &
                 (f["tournament_date"] <= pd.Timestamp("2026-12-31") - pd.DateOffset(years=1))]["tournament_date"]
    proj = year_ago + pd.DateOffset(years=1)
    two_ago = f[(f["tournament_date"] > last - pd.DateOffset(years=2)) &
                (f["tournament_date"] <= pd.Timestamp("2027-12-31") - pd.DateOffset(years=2))]["tournament_date"]
    proj2 = two_ago + pd.DateOffset(years=2)
    proj2 = proj2[proj2 > pd.Timestamp("2026-12-31")]
    d = pd.concat([actual.rename("d").to_frame().assign(kind="actual"),
                   proj.rename("d").to_frame().assign(kind="projected"),
                   proj2.rename("d").to_frame().assign(kind="projected")], ignore_index=True)
    return d.sort_values("d").reset_index(drop=True), last


def seen_readings() -> tuple[dict, dict]:
    f = C.seen("atp")
    sc = C.scales(f)
    s = C.scores(f, sc)
    out = {}
    windows = {"2025-26": (f["season"] >= 2025).to_numpy(), "2013-24": (f["season"] <= 2024).to_numpy(),
               "2020-24": f["season"].between(2020, 2024).to_numpy()}
    for name, sv in s.items():
        out[name] = {}
        for w, m in windows.items():
            g = f[m].reset_index(drop=True)
            r = C.fit(g, sv[m], base="L")
            out[name][w] = {k: r[k] for k in ("beta", "se", "z", "blocks", "p_one_sided", "p_beta_positive", "n",
                                              "beta_per_unit", "se_per_unit", "rms_in_rows")}
    return out, sc


def power(z_exp: float, G: int, alpha: float) -> float:
    df = max(G - 1, 1)
    return float(nct.sf(student_t.isf(alpha, df), df, z_exp))


def sequential_power(z_exps: list[float], Gs: list[int], alpha: float, n_sim: int = 200_000, seed: int = 0) -> float:
    """Three looks at information fractions given by z_exps (expected z grows with sqrt(N)); stop at the first t over
    its boundary. Normal increments; each look's t critical value on its own G - 1."""
    rng = np.random.default_rng(seed)
    k = len(z_exps)
    info = (np.asarray(z_exps) / z_exps[-1]) ** 2 if z_exps[-1] != 0 else np.linspace(1 / k, 1, k)
    inc = np.diff(np.concatenate([[0.0], info]))
    w = rng.standard_normal((n_sim, k)) * np.sqrt(inc)
    S = np.cumsum(w, axis=1)
    Z = S / np.sqrt(info) + np.asarray(z_exps)
    crit = np.array([student_t.isf(alpha, max(g - 1, 1)) for g in Gs])
    return float(np.mean((Z > crit).any(axis=1)))


def main() -> int:
    cal, last = unseen_calendar()
    blk = H.blocks(cal["d"].to_numpy(), 28)
    readings, sc = seen_readings()
    rows = []
    for name in ("R0", "T1", "T2", "T3", "T4"):
        r_seen = readings[name]["2025-26"]
        r_old = readings[name]["2013-24"]
        b, se, n = r_seen["beta_per_unit"], r_seen["se_per_unit"], r_seen["n"]
        if name == "T4":
            # speed is 0 where a match has no speed value; the seen fit's n counts every match
            pass
        ratio_old = r_old["beta_per_unit"] / b if b else np.nan
        for d in DATES:
            k = cal["d"] <= pd.Timestamp(d)
            N = int(k.sum())
            G = int(len(np.unique(blk[k.to_numpy()]))) if N else 0
            se_N = se * np.sqrt(n / N) if N else np.inf
            row = {"score": name, "date": d, "unseen_men": N, "actual_share": float((cal["kind"][k] == "actual").mean()) if N else 0.0,
                   "blocks": G, "se_per_unit": se_N}
            for scn in SCENARIOS:
                r = {"1": 1.0, "0.45": 0.45, "0.25": 0.25, "r_old": ratio_old, "0": 0.0}[scn]
                z = r * b / se_N
                row[f"z_exp_{scn}"] = z
                row[f"power_one_look_{scn}"] = power(z, G, 0.05)
            rows.append(row)
    t = pd.DataFrame(rows)
    # three looks, Pocock: ~Jan 2027, ~May 2027, ~Sep 2027 (by the projected calendar)
    seq = {}
    for name in ("R0", "T4"):
        tt = t[t["score"] == name].set_index("date")
        for plan, dates in {"Jan/May/Aug 2027": ["2027-01-31", "2027-05-31", "2027-08-31"],
                            "Mar/Jul/Dec 2027": ["2027-03-31", "2027-07-31", "2027-12-31"]}.items():
            for scn in SCENARIOS:
                seq.setdefault(name, {}).setdefault(plan, {})[scn] = sequential_power(
                    [float(tt.loc[d, f"z_exp_{scn}"]) for d in dates], [int(tt.loc[d, "blocks"]) for d in dates],
                    POCOCK_3)
    C.write_json(C.OUT / "timeline.json", {"frame_last_day": str(last.date()), "readings_seen": readings,
                                            "scales": sc, "sequential_power": seq})
    t.to_csv(C.OUT / "timeline.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print("frame's last day:", last.date())
    for name, r in readings.items():
        print(name, {w: (round(v["beta_per_unit"], 4), round(v["z"], 2), v["n"], v["blocks"]) for w, v in r.items()})
    print(t[[c for c in t.columns if not c.startswith("z_exp")]].round(3).to_string(index=False))
    print(seq)
    return 0


if __name__ == "__main__":
    sys.exit(main())
