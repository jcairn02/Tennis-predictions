"""Stage 3, part 2b: the serve-point test split into the serve's own attributes and the rally's.

The owner's question of 8 Oct 2026 separates point-by-point data about the serve (its speed and direction) from
shot-by-shot data about the rally (how many shots, how points end, net play, return depth). Part 2 (stage3_points.py)
scored the shot features together, speed included. Here the same models are fitted with each half alone:

    M4r  M2 + the rally inputs only: every input of stage3_points.SHOT except serve speed and serve placement
    M4s  M2 + the serve inputs only: first- and second-serve speed, first serves to the T and out wide

each scored per serve point against M2 (the ratings and box-score form), as in part 2; M4 (both) is refitted beside
them and must reproduce part 2. Then, as in part 2, each model's two serve forecasts become a match forecast through
the iid model, and its difference from M2's (log-odds) is scored as a feature given the closing odds with the
harness's walk-forward fit.

Run:  ./python.sh src/eda/shot_level/stage3_points_split.py   (under a minute)
Writes data/studies/shot_level/stage3_points_split.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as I  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stage3_points as P  # noqa: E402

SERVE_ATTR = {"spd1", "spd2", "t_share", "wide_share"}
WINDOWS = ((P.FIRST_SCORED, 2026, "all"), (2019, 2026, "2019_26"), (2022, 2026, "2022_26"))


def main() -> int:
    sides = pd.read_parquet(S.OUT / "stage3_sides.parquet")
    rows = P.server_rows(sides)
    box = [f"{r}|{n}" for r, n in P.BOX]
    rally = [f"{r}|{n}" for r, n in P.SHOT if n.split("|")[0] not in SERVE_ATTR]
    serve = [f"{r}|{n}" for r, n in P.SHOT if n.split("|")[0] in SERVE_ATTR]
    models = {"M2": box, "M4": box + rally + serve, "M4r": box + rally, "M4s": box + serve}
    res = {"inputs": {"rally": rally, "serve": serve}, "points": {}, "seasons": [], "match": {}}
    frames = []
    for t in C.TOURS:
        df = rows[rows["tour"] == t].reset_index(drop=True)
        pred = {m: P.walk(df, cols) for m, cols in models.items()}
        frames.append(df.assign(**{f"p_{m}": v for m, v in pred.items()}))
        sc = df["evaluation"].to_numpy(dtype=bool) & np.isfinite(pred["M2"])
        x, d, yr = df["x"].to_numpy(), df["d"].to_numpy(), df["year"].to_numpy()
        ll = {m: P.point_ll(pred[m], x, d) for m in models}
        wk = pd.to_datetime(df["date"]).dt.to_period("W-SUN").astype(str).to_numpy()
        for m, label in (("M4", "rally and serve inputs"), ("M4r", "rally inputs only"), ("M4s", "serve inputs only")):
            g = ll["M2"] - ll[m]
            for w0, w1, wname in WINDOWS:
                mm = sc & (yr >= w0) & (yr <= w1)
                mean, lo, hi = P.clustered(g[mm], d[mm], wk[mm])
                res["points"][f"{t}|{m}-M2|{wname}"] = {"label": label, "gain_per_point_milli": mean, "lo": lo, "hi": hi,
                                                       "serve_points": int(d[mm].sum())}
            for Y in range(P.FIRST_SCORED, 2027):
                mm = sc & (yr == Y)
                if mm.any():
                    res["seasons"].append({"tour": t, "season": Y, "comparison": f"{m}-M2",
                                           "gain_per_point_milli": 1000 * g[mm].sum() / d[mm].sum()})
        S.log(f"  {t}: " + "; ".join(f"{k.split('|')[1]} {k.split('|')[2]} {v['gain_per_point_milli']:+.4f} "
                                     f"({v['lo']:+.4f} to {v['hi']:+.4f})" for k, v in res["points"].items() if k.startswith(t)))
    # from points to matches, as in stage3_points: each model's iid match forecast, its difference from M2's as a
    # feature given the closing odds
    allr = pd.concat(frames, ignore_index=True)
    a = allr[allr["server"] == "A"].set_index("match_id")
    b = allr[allr["server"] == "B"].set_index("match_id")
    both = a.index.intersection(b.index)
    mt = sides.set_index("match_id").loc[both]
    bo = np.where(mt["best_of"].to_numpy() == 5, 5, 3)
    rule = np.full(len(both), I.STANDARD, dtype=object)
    match = pd.DataFrame({"tour": mt["tour"].to_numpy(), "year": mt["year"].to_numpy(), "a_won": mt["a_won"].to_numpy(),
                          "p_mkt": mt["p_mkt"].to_numpy(), "evaluation": mt["evaluation"].to_numpy(),
                          "date": mt["tournament_date"].to_numpy()})
    for m in models:
        pa, pb = a.loc[both, f"p_{m}"].to_numpy(), b.loc[both, f"p_{m}"].to_numpy()
        ok = np.isfinite(pa) & np.isfinite(pb)
        pm = np.full(len(both), np.nan)
        pm[ok] = I.match_win_by(pa[ok], pb[ok], bo[ok], rule[ok])
        match[f"p_iid_{m}"] = pm
    y = match["a_won"].to_numpy().astype(bool)
    wk = pd.to_datetime(match["date"]).dt.to_period("W-SUN").astype(str).to_numpy()
    yr = match["year"].to_numpy()
    for t in C.TOURS:
        mo = (match["tour"].eq(t) & match["evaluation"] & match["p_iid_M2"].notna() & match["p_mkt"].notna()).to_numpy()
        lb = logit(np.clip(match["p_mkt"].to_numpy(dtype="float64")[mo], 1e-9, 1 - 1e-9))
        for m in ("M4", "M4r", "M4s"):
            feat = (logit(np.clip(match[f"p_iid_{m}"].to_numpy(), 1e-6, 1 - 1e-6))
                    - logit(np.clip(match["p_iid_M2"].to_numpy(), 1e-6, 1 - 1e-6)))[mo]
            Z = np.column_stack([lb, feat / np.nanstd(feat)])[None]
            w = R.walk(np.ascontiguousarray(Z), y[mo], yr[mo], list(range(P.FIRST_SCORED + 1, 2027)), lb)
            dd = (w["llb"][None, :] - w["llm"])[0]
            for w0, w1, wname in WINDOWS:
                okd = np.isfinite(dd) & (yr[mo] >= w0) & (yr[mo] <= w1)
                mean, lo, hi = P.clustered(dd[okd], np.ones(okd.sum()), wk[mo][okd])
                res["match"][f"{t}|{m} given the odds|{wname}"] = {"gain_milli": mean, "lo": lo, "hi": hi, "n": int(okd.sum())}
        S.log(f"  {t} matches given the odds: " + "; ".join(
            f"{k.split('|')[1]} {k.split('|')[2]} {v['gain_milli']:+.3f} ({v['lo']:+.3f} to {v['hi']:+.3f}) n={v['n']}"
            for k, v in res["match"].items() if k.startswith(t)))
    (S.OUT / "stage3_points_split.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
