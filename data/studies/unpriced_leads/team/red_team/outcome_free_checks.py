"""R2: outcome-free checks on every season (no result column is ever loaded here).

1. Look A's size, its four-week blocks (G), its odds-input sources and BetOnline freshness;
2. each registered score's RMS and non-zero share by season (frozen projections and scales): does a score's spread move
   between discovery and Look A (the "uneven input" warning sign; and look.py rescales to the window's RMS)?
3. orientation of the bases look.py builds (book closes, the instance's forecast) against the odds input;
4. bol_after_listed_min missing where BetOnline's close exists (look.py counts those as stale).
Writes outcome_free_checks.json and score_rms_by_season.csv.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rt_common as R  # noqa: E402


def main() -> int:
    reg = R.registry()
    f = R.outcome_free_frame()
    td = pd.to_datetime(f["tournament_date"])
    lookA = (f["season"].between(2025, 2026) & (td < pd.Timestamp("2026-07-29"))).to_numpy()
    disc = f["season"].between(2013, 2024).to_numpy()
    sealed = (td >= pd.Timestamp("2026-07-29")).to_numpy()
    out = {"lookA_matches": int(lookA.sum()), "lookA_by_tour": f.loc[lookA, "tour"].value_counts().to_dict(),
           "lookA_blocks_G": int(f.loc[lookA, "block"].nunique()),
           "lookA_matches_per_block": f.loc[lookA].groupby("block").size().describe().to_dict(),
           "dryrun_blocks_G_2023_24": int(f.loc[f["season"].between(2023, 2024).to_numpy(), "block"].nunique()),
           "disc_blocks_G": int(f.loc[disc, "block"].nunique()),
           "lookA_odds_input": f.loc[lookA, "odds_input"].value_counts().to_dict(),
           "sealed_matches_in_frame": int(sealed.sum())}
    # Look A per tour x source
    out["lookA_source_by_tour"] = pd.crosstab(f.loc[lookA, "tour"], f.loc[lookA, "odds_input"]).to_dict()
    # books and the forecast (the bases look.py builds), outcome-free
    b = pd.read_parquet(R.INST / "book_prices.parquet", columns=["match_id", "pin_a", "pin_b", "bol_a", "bol_b",
                                                                  "bol_after_listed_min"])
    b = b.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    Lb = {}
    for book in ("pin", "bol"):
        ia, ib = 1 / b[f"{book}_a"].to_numpy(float), 1 / b[f"{book}_b"].to_numpy(float)
        p = np.clip(ia / (ia + ib), 1e-6, 1 - 1e-6)
        Lb[book] = np.log(p / (1 - p))
    a = pd.read_parquet(R.ROOT / "data" / "studies" / "edge_anatomy" / "analysis.parquet", columns=["match_id", "q_full"])
    q = a.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id")["q_full"].reindex(f["match_id"])
    q = np.clip(q.to_numpy(float), 1e-6, 1 - 1e-6)
    Lb["model"] = np.log(q / (1 - q))
    L = f["L"].to_numpy(float)
    orient = {}
    for k, v in Lb.items():
        for lab, m in (("disc", disc), ("lookA", lookA)):
            ok = m & np.isfinite(v)
            orient[f"{k}_{lab}"] = {"n": int(ok.sum()), "corr_with_L": float(np.corrcoef(v[ok], L[ok])[0, 1]) if ok.sum() > 2
                                    else None, "share_sign_agree": float(np.mean(np.sign(v[ok]) == np.sign(L[ok])))
                                    if ok.sum() else None}
    out["orientation"] = orient
    after = b["bol_after_listed_min"].to_numpy(float)
    for lab, m in (("disc", disc), ("lookA", lookA), ("2023_24", f["season"].between(2023, 2024).to_numpy())):
        has = m & np.isfinite(Lb["bol"])
        out[f"bol_{lab}"] = {"with_bol_close": int(has.sum()),
                             "after_listed_missing": int((has & ~np.isfinite(after)).sum()),
                             "fresh_ge_minus60": int((has & (after >= -60)).sum()),
                             "stale_lt_minus60": int((has & (after < -60)).sum())}
    # Look A, BetOnline period only: freshness of the odds input itself
    bolp = lookA & f["odds_input"].astype(str).str.contains("betonline").to_numpy()
    out["lookA_betonline_period"] = {"n": int(bolp.sum()), "fresh": int((bolp & (after >= -60)).sum()),
                                     "stale": int((bolp & (after < -60)).sum()),
                                     "after_missing": int((bolp & ~np.isfinite(after)).sum())}
    # 2. score RMS by season with the frozen recipe (outcome-free)
    mem, grp, omni, gs = R.scores(f, reg, own_projection=False)
    rows = []
    allsc = {"omnibus": omni, **grp, **mem}
    for name, s in allsc.items():
        for tour in ("both", "atp", "wta"):
            tm = np.ones(len(f), bool) if tour == "both" else (f["tour"] == tour).to_numpy()
            for season in range(2013, 2027):
                m = tm & (f["season"] == season).to_numpy() & ~sealed
                if m.sum() == 0:
                    continue
                rows.append({"score": name, "tour": tour, "season": season, "n": int(m.sum()),
                             "rms": float(np.sqrt(np.mean(s[m] ** 2))), "nonzero": float(np.mean(s[m] != 0))})
            for lab, mm in (("disc", disc), ("lookA", lookA)):
                m = tm & mm
                rows.append({"score": name, "tour": tour, "season": lab, "n": int(m.sum()),
                             "rms": float(np.sqrt(np.mean(s[m] ** 2))), "nonzero": float(np.mean(s[m] != 0))})
    T = pd.DataFrame(rows)
    T.to_csv(R.OUT / "score_rms_by_season.csv", index=False)
    piv = T[(T["tour"] == "both")].pivot(index="score", columns="season", values="rms")
    out["rms_disc_vs_lookA_both"] = {k: {"disc": float(piv.loc[k, "disc"]), "lookA": float(piv.loc[k, "lookA"]),
                                         "ratio": float(piv.loc[k, "lookA"] / piv.loc[k, "disc"])} for k in piv.index}
    (R.OUT / "outcome_free_checks.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rms_disc_vs_lookA_both"}, indent=1, default=float))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    cols = [c for c in piv.columns if c not in ("disc", "lookA")] + ["disc", "lookA"]
    print(piv[cols].round(3).to_string())
    nz = T[(T["tour"] == "both")].pivot(index="score", columns="season", values="nonzero")
    print(nz[cols].round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
