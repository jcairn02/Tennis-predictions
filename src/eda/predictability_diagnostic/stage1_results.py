"""Stage 1 of the predictability diagnostic, part 3: how well each baseline predicts, and where.

Reads stage0_matches, stage1_baselines and stage1_odds; scores every baseline on the evaluation matches
(2013-2026, completed and retired; the player who advanced won) by log loss, the average of
-ln(probability given to the actual winner). A coin scores ln 2 = 0.6931; lower is better.

    by cell     tour x level x best of x surface x era, and every margin of it, and by season
    market      the closing odds exist for tour-level main draws only, so every comparison with the market
                is made on the same matches (the "market subset"); the gap between Elo and the market,
                with a 95% interval from the per-match differences, is the room left between a rating
                and the price
    favourite   how often the favourite of each baseline won
    calibration how often favourites won against the probability they were given, by tour, 2022-2026
    checks      retirements counted or skipped; the market average against Pinnacle where both exist

Writes, in data/studies/predictability_diagnostic/:
    stage1_logloss_cells.csv     one row per tour x level x best of x surface x era cell
    stage1_calibration.csv       the calibration bins
    stage1_results.json          everything the report and stage1.md quote

Run: ./python.sh src/eda/predictability_diagnostic/stage1_results.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as E  # noqa: E402

CELLS = C.OUT / "stage1_logloss_cells.csv"
CALIBRATION = C.OUT / "stage1_calibration.csv"
RESULTS = C.OUT / "stage1_results.json"

BASELINES = {  # column in stage1_baselines -> label
    "p_coin": "Coin", "p_rank": "Ranking", "p_points": "Ranking points",
    "p_elo_ret": "Elo", "p_elo_surf_ret": "Surface Elo",
    "p_elo_noret": "Elo, retirements skipped", "p_elo_surf_noret": "Surface Elo, retirements skipped",
    "p_market": "Market (closing odds)"}
MARKET_SET = ["p_rank", "p_points", "p_elo_ret", "p_elo_surf_ret", "p_elo_noret", "p_elo_surf_noret", "p_market"]
ELO_CHART = "p_elo_surf_ret"   # the Elo the report's charts show: surface-blended, retirements counted
LEVEL_GROUPS = [  # Stage 0's map_level codes, in the report's order
    ("GS", "Grand Slams"), ("FIN", "Tour Finals"), ("T1000", "1000s"), ("T500", "500s"), ("T250", "250s"),
    ("GSQ", "Grand Slam qualifying"), ("TQ", "Tour qualifying"), ("CH", "Challenger / WTA 125"),
    ("CHQ", "Challenger / 125 qualifying")]
WINDOWS = {"2013-2026": range(2013, 2027), "2013-2018 (tuning)": range(2013, 2019),
           "2019-2026": range(2019, 2027), "2022-2026 (headline)": range(2022, 2027)}
BINS = np.round(np.arange(0.5, 1.0001, 0.05), 2)
CALIBRATION_YEARS = range(2022, 2027)
MIN_N = C.DIRECTIONAL_ONLY_BELOW


def losses(frame: pd.DataFrame, cols) -> pd.DataFrame:
    """Per-match log loss of each probability column (probability that A wins)."""
    y = frame["a_won"].to_numpy(dtype=bool)
    out = {}
    for c in cols:
        p = np.clip(frame[c].to_numpy(dtype="float64"), E.EPS, 1 - E.EPS)
        out[c] = np.where(y, -np.log(p), -np.log(1 - p))
    return pd.DataFrame(out, index=frame.index)


def summarise(ll: pd.DataFrame, keys: pd.DataFrame | None, cols) -> pd.DataFrame:
    """n and mean log loss per group (every column's mean over the same matches)."""
    if keys is None:
        return pd.DataFrame([{"n": len(ll), **{c: float(ll[c].mean()) for c in cols}}])
    g = ll[cols].groupby([keys[k] for k in keys.columns], dropna=False, observed=True)
    out = g.mean()
    out.insert(0, "n", g.size())
    return out.reset_index()


def gap(ll: pd.DataFrame, a: str, b: str) -> dict:
    """a minus b in milli-log-loss on the same matches, with a 95% interval from the per-match differences."""
    d = (ll[a] - ll[b]).to_numpy()
    n = len(d)
    if n == 0:
        return {"n": 0}
    mean, se = 1000 * d.mean(), 1000 * d.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return {"n": int(n), "milli": round(float(mean), 2), "lo": round(float(mean - 1.96 * se), 2),
            "hi": round(float(mean + 1.96 * se), 2), "directional_only": bool(n < MIN_N)}


def records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records"))


def wilson(k: float, n: float) -> tuple[float, float]:
    if n == 0:
        return np.nan, np.nan
    z, p = 1.96, k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half


def calibration(frame: pd.DataFrame, col: str) -> pd.DataFrame:
    """Bins of the favourite's probability: matches, mean probability, share the favourite won."""
    p = frame[col].to_numpy(dtype="float64")
    y = frame["a_won"].to_numpy(dtype=bool)
    fav = np.maximum(p, 1 - p)
    fav_won = np.where(p >= 0.5, y, ~y)
    b = np.clip(np.digitize(fav, BINS[1:-1]), 0, len(BINS) - 2)
    rows = []
    for i in range(len(BINS) - 1):
        s = b == i
        n, k = int(s.sum()), int(fav_won[s].sum())
        lo, hi = wilson(k, n)
        rows.append({"bin": f"{BINS[i]:.2f}-{BINS[i + 1]:.2f}", "lo_edge": float(BINS[i]), "n": n,
                     "mean_p": float(fav[s].mean()) if n else np.nan, "won": float(k / n) if n else np.nan,
                     "won_lo": lo, "won_hi": hi})
    return pd.DataFrame(rows)


def signed_calibration(frame: pd.DataFrame, col: str) -> dict:
    """How far favourites' results sat from what they were given, over all matches: the share the favourite
    won minus the average probability it was given (positive: favourites won more than they were given)."""
    p = frame[col].to_numpy(dtype="float64")
    y = frame["a_won"].to_numpy(dtype=bool)
    fav, won = np.maximum(p, 1 - p), np.where(p >= 0.5, y, ~y)
    return {"n": int(len(p)), "given_pct": round(100 * float(fav.mean()), 2), "won_pct": round(100 * float(won.mean()), 2),
            "won_minus_given_points": round(100 * float(won.mean() - fav.mean()), 2)}


def split_identity_matches(m: pd.DataFrame) -> tuple[set, dict]:
    """Matches in which a Tennis My Life row carries a player id that Sackmann's rows never use, although the
    same name (as scan.py keys names) has a Sackmann id: one player split across two ids, so Elo meets them
    as a newcomer. Stage 0 finding, reported, not fixed here."""
    from src.eda.merge_feasibility import scan as S
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "player_id", "player_name"])
    mp = mp.merge(m[["match_id", "tour", "source", "evaluation", "year"]], on="match_id")
    sack = mp[mp["source"].eq("sackmann")]
    ids = set(sack["player_id"])
    names = set(zip(sack["tour"], S.keys_for(sack["player_name"])))
    t = mp[mp["source"].eq("tml") & ~mp["player_id"].isin(ids)].copy()
    t["named"] = [(a, k) in names for a, k in zip(t["tour"], S.keys_for(t["player_name"]))]
    split = t[t["named"]]
    out = {}
    for tour, g in split.groupby("tour"):
        out[tour] = {"player_rows": int(len(g)), "player_ids": int(g["player_id"].nunique()),
                     "matches": int(g["match_id"].nunique()), "evaluation_matches": int(g.loc[g["evaluation"], "match_id"].nunique()),
                     "seasons": {str(k): int(v) for k, v in g["year"].value_counts().sort_index().items()},
                     "examples": sorted(g.drop_duplicates("player_id")["player_name"].head(8).tolist())}
    unknown = mp[mp["source"].eq("tml") & ~mp["player_id"].isin(ids)]
    for tour, g in unknown.groupby("tour"):
        out.setdefault(tour, {})["tml_rows_with_an_id_sackmann_never_uses"] = int(len(g))
    return set(split["match_id"]), out


def favourites(frame: pd.DataFrame, col: str) -> dict:
    p = frame[col].to_numpy(dtype="float64")
    y = frame["a_won"].to_numpy(dtype=bool)
    tie = p == 0.5
    won = np.where(p > 0.5, y, ~y)[~tie]
    return {"n": int(len(p)), "ties": int(tie.sum()), "favourite_won_pct": round(100 * float(won.mean()), 2) if len(won) else None}


def main() -> int:
    m = C.load_matches(["match_id", "tour", "year", "era", "level", "qualifying", "map_level", "best_of", "surface",
                        "status", "evaluation", "a_won", "format", "tournament_name", "source"])
    b = pd.read_parquet(C.OUT / "stage1_baselines.parquet").drop(columns=["tour", "year", "evaluation", "a_won"])
    ev = m[m["evaluation"]].merge(b, on="match_id", how="left", validate="one_to_one")
    ev["surface"] = ev["surface"].fillna("unknown")
    ev["best_of"] = ev["best_of"].astype(int)
    cols = list(BASELINES)
    ll = losses(ev, cols)
    mk = ev["p_market"].notna()
    llm = ll.loc[mk, MARKET_SET]
    res = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
           "baselines": BASELINES, "market_set": MARKET_SET, "level_groups": LEVEL_GROUPS,
           "windows": {k: [v[0], v[-1]] for k, v in WINDOWS.items()}, "directional_only_below": MIN_N,
           "coin": float(np.log(2))}

    # ---- headline: every window, all evaluation matches and the market subset
    head = []
    for tour in C.TOURS:
        for name, years in WINDOWS.items():
            s = ev["tour"].eq(tour) & ev["year"].isin(list(years))
            row = {"tour": tour, "window": name, **summarise(ll[s], None, cols).iloc[0].to_dict()}
            sm = s & mk
            row["market_subset"] = summarise(ll.loc[sm, MARKET_SET], None, MARKET_SET).iloc[0].to_dict()
            row["gaps_milli"] = {c: gap(ll[sm], c, "p_market") for c in ("p_elo_ret", "p_elo_surf_ret", "p_rank")}
            row["elo_minus_rank_milli"] = gap(ll[s], "p_elo_ret", "p_rank")
            row["surface_minus_overall_milli"] = gap(ll[s], "p_elo_surf_ret", "p_elo_ret")
            row["noret_minus_ret_milli"] = gap(ll[s], "p_elo_noret", "p_elo_ret")
            row["surf_noret_minus_ret_milli"] = gap(ll[s], "p_elo_surf_noret", "p_elo_surf_ret")
            head.append(row)
    res["headline"] = head

    # ---- margins by dimension, all evaluation matches and the market subset
    ev["level_group"] = ev["map_level"]
    dims = {"level": ["tour", "level_group"], "best_of": ["tour", "best_of"], "surface": ["tour", "surface"],
            "era": ["tour", "era"], "year": ["tour", "year"],
            "level_era": ["tour", "level_group", "era"], "level_surface": ["tour", "level_group", "surface"]}
    margins = {}
    for name, keys in dims.items():
        allm = summarise(ll, ev[keys], cols)
        sub = summarise(llm, ev.loc[mk, keys], MARKET_SET).rename(columns={"n": "n_market", **{c: f"{c}__m" for c in MARKET_SET}})
        t = allm.merge(sub, on=keys, how="left")
        gaps = []
        for key, g in ev[mk].groupby(keys, observed=True):
            key = key if isinstance(key, tuple) else (key,)
            idx = g.index
            gaps.append({**dict(zip(keys, key)), "gap_elo": gap(ll.loc[idx], "p_elo_ret", "p_market"),
                         "gap_surf": gap(ll.loc[idx], "p_elo_surf_ret", "p_market")})
        margins[name] = {"rows": records(t), "gaps": json.loads(json.dumps(gaps, default=float))}
    res["margins"] = margins

    # ---- the full cross, as a CSV
    keys = ["tour", "level_group", "best_of", "surface", "era"]
    allm = summarise(ll, ev[keys], cols)
    sub = summarise(llm, ev.loc[mk, keys], MARKET_SET).rename(columns={"n": "n_market", **{c: f"{c}__market_subset" for c in MARKET_SET}})
    cells = allm.merge(sub, on=keys, how="left")
    for c in ("p_elo_ret", "p_elo_surf_ret"):
        cells[f"gap_{c}_minus_market_milli"] = 1000 * (cells[f"{c}__market_subset"] - cells["p_market__market_subset"])
    cells["directional_only"] = cells["n"] < MIN_N
    cells["market_directional_only"] = cells["n_market"].fillna(0) < MIN_N
    cells.to_csv(CELLS, index=False)
    res["cells"] = {"rows": int(len(cells)), "at_least_min_n": int((cells["n"] >= MIN_N).sum()),
                    "with_market": int(cells["n_market"].notna().sum()),
                    "with_market_at_least_min_n": int((cells["n_market"].fillna(0) >= MIN_N).sum())}

    # ---- favourites
    fav = []
    for tour in C.TOURS:
        for lg, _ in LEVEL_GROUPS + [("ALL", "all")]:
            s = ev["tour"].eq(tour) & (ev["level_group"].eq(lg) if lg != "ALL" else True)
            if not s.any():
                continue
            row = {"tour": tour, "level_group": lg}
            for c in ("p_rank", "p_elo_ret", "p_elo_surf_ret"):
                row[c] = favourites(ev[s], c)
            sm = s & mk
            row["market_subset"] = {c: favourites(ev[sm], c) for c in ("p_rank", "p_elo_ret", "p_elo_surf_ret", "p_market")} if sm.any() else None
            fav.append(row)
    res["favourites"] = fav
    res["favourites_headline"] = [{"tour": t, **{c: favourites(ev[ev["tour"].eq(t) & ev["year"].isin(list(CALIBRATION_YEARS)) & mk], c)
                                                  for c in ("p_rank", "p_elo_ret", "p_elo_surf_ret", "p_market")}}
                                  for t in C.TOURS]

    # ---- calibration, 2022-2026
    cal = []
    for tour in C.TOURS:
        s = ev["tour"].eq(tour) & ev["year"].isin(list(CALIBRATION_YEARS))
        for label, frame, col in (("Elo, all evaluation matches", ev[s], "p_elo_ret"),
                                  ("Elo, matches with odds", ev[s & mk], "p_elo_ret"),
                                  ("Surface Elo, matches with odds", ev[s & mk], "p_elo_surf_ret"),
                                  ("Market, matches with odds", ev[s & mk], "p_market")):
            c = calibration(frame, col)
            c.insert(0, "series", label)
            c.insert(0, "tour", tour)
            cal.append(c)
    cal = pd.concat(cal, ignore_index=True)
    cal.to_csv(CALIBRATION, index=False)
    res["calibration"] = records(cal)
    res["calibration_years"] = [CALIBRATION_YEARS[0], CALIBRATION_YEARS[-1]]

    # ---- checks: retirements, completed matches only, the market against Pinnacle
    comp = ev["status"].eq("completed")
    res["completed_only"] = []
    for tour in C.TOURS:
        for name, years in WINDOWS.items():
            s = ev["tour"].eq(tour) & ev["year"].isin(list(years))
            res["completed_only"].append({"tour": tour, "window": name,
                                          "retired_share_pct": round(100 * float((~comp[s]).mean()), 2),
                                          **summarise(ll[s & comp], None, cols).iloc[0].to_dict(),
                                          "noret_minus_ret_milli": gap(ll[s & comp], "p_elo_noret", "p_elo_ret")})
    rr = summarise(ll, ev[["tour", "level_group", "era"]], ["p_elo_ret", "p_elo_noret", "p_elo_surf_ret", "p_elo_surf_noret"])
    rr["elo_diff_milli"] = 1000 * (rr["p_elo_noret"] - rr["p_elo_ret"])
    rr["surf_diff_milli"] = 1000 * (rr["p_elo_surf_noret"] - rr["p_elo_surf_ret"])
    big = rr[rr["n"] >= MIN_N]
    res["retirement_rule_by_cell"] = {"cells": int(len(big)),
                                      "largest_abs_milli": round(float(big[["elo_diff_milli", "surf_diff_milli"]].abs().max().max()), 2),
                                      "rows": records(rr)}
    ps = ev["p_pinnacle"].notna() & mk
    llp = losses(ev[ps], ["p_market", "p_pinnacle", "p_elo_ret"])
    pin = []
    for (tour, year), g in ev[ps].groupby(["tour", "year"]):
        pin.append({"tour": tour, "year": int(year), **gap(llp.loc[g.index], "p_market", "p_pinnacle")})
    both = ev[ps]
    res["pinnacle_check"] = {
        "by_tour": [{"tour": t, **gap(llp.loc[g.index], "p_market", "p_pinnacle"),
                     "market": float(llp.loc[g.index, "p_market"].mean()), "pinnacle": float(llp.loc[g.index, "p_pinnacle"].mean()),
                     "mean_abs_prob_diff": float((g["p_market"] - g["p_pinnacle"]).abs().mean()),
                     "correlation": float(np.corrcoef(g["p_market"], g["p_pinnacle"])[0, 1])}
                    for t, g in both.groupby("tour")],
        "by_tour_year": pin}

    # ---- the order of the baselines, season by season
    order = []
    for (tour, year), g in ev.groupby(["tour", "year"]):
        s = g.index
        row = {"tour": tour, "year": int(year),
               "all_elo_below_rank": bool(ll.loc[s, ELO_CHART].mean() < ll.loc[s, "p_rank"].mean())}
        sm = s[mk[s].to_numpy()]
        if len(sm):
            a, e, k = ll.loc[sm, "p_market"].mean(), ll.loc[sm, ELO_CHART].mean(), ll.loc[sm, "p_rank"].mean()
            row.update({"odds_matches": int(len(sm)), "market_below_elo_below_rank": bool(a < e < k)})
        order.append(row)
    res["order_by_season"] = order
    res["order_holds_every_season"] = {
        t: {"with_odds": all(o.get("market_below_elo_below_rank", True) for o in order if o["tour"] == t),
            "all_evaluation_elo_below_rank": all(o["all_elo_below_rank"] for o in order if o["tour"] == t)} for t in C.TOURS}

    # ---- calibration, signed: over all matches, and by best of three or five sets
    sc = []
    for tour in C.TOURS:
        for bo in (None, 3, 5):
            s = ev["tour"].eq(tour) & ev["year"].isin(list(CALIBRATION_YEARS)) & (ev["best_of"].eq(bo) if bo else True)
            if not s.any():
                continue
            for label, frame, col in (("Surface Elo, all evaluation matches", ev[s], ELO_CHART),
                                      ("Surface Elo, matches with odds", ev[s & mk], ELO_CHART),
                                      ("Market, matches with odds", ev[s & mk], "p_market")):
                if len(frame):
                    sc.append({"tour": tour, "best_of": bo or "all", "series": label, **signed_calibration(frame, col)})
        for bo in (3, 5):   # every evaluation year, for the best-of-five contrast
            s = ev["tour"].eq(tour) & ev["best_of"].eq(bo) & mk
            if s.any():
                sc.append({"tour": tour, "best_of": bo, "series": "Surface Elo, matches with odds, 2013-2026", **signed_calibration(ev[s], ELO_CHART)})
                sc.append({"tour": tour, "best_of": bo, "series": "Market, matches with odds, 2013-2026", **signed_calibration(ev[s], "p_market")})
    res["calibration_signed"] = sc
    res["best_of_gaps"] = [{"tour": t, "best_of": int(bo), **gap(ll.loc[g.index], ELO_CHART, "p_market")}
                           for (t, bo), g in ev[mk].groupby(["tour", "best_of"])]

    # ---- a Stage 0 identity problem, and its effect (reported, not fixed)
    split, split_counts = split_identity_matches(m)
    res["split_identities"] = split_counts
    sens = []
    for tour in C.TOURS:
        for name, years in (("2022-2026 (headline)", range(2022, 2027)), ("2026", range(2026, 2027)), ("2013-2026", range(2013, 2027))):
            s = ev["tour"].eq(tour) & ev["year"].isin(list(years))
            keep = s & ~ev["match_id"].isin(split)
            sens.append({"tour": tour, "window": name, "gap_all": gap(ll[s & mk], ELO_CHART, "p_market"),
                         "gap_without": gap(ll[keep & mk], ELO_CHART, "p_market"),
                         "elo_all": float(ll.loc[s, ELO_CHART].mean()), "elo_without": float(ll.loc[keep, ELO_CHART].mean()),
                         "matches_left_out": int((s & ~keep).sum()), "odds_matches_left_out": int((s & mk & ~keep).sum())})
    res["split_identity_sensitivity"] = sens

    # ---- the Next Gen ATP Finals (Stage 0 decision 2): the Tour Finals cell with and without them
    fin = ev["tour"].eq("atp") & ev["level_group"].eq("FIN")
    ng = fin & ev["tournament_name"].str.contains("Next", case=False, na=False)
    res["next_gen_finals"] = {"matches": int(ng.sum()), "tour_finals_matches": int(fin.sum()),
                              "surface_elo_with": float(ll.loc[fin, ELO_CHART].mean()),
                              "surface_elo_without": float(ll.loc[fin & ~ng, ELO_CHART].mean()),
                              "surface_elo_next_gen": float(ll.loc[ng, ELO_CHART].mean()),
                              "with_odds": int((ng & mk).sum())}

    # ---- what the market subset is, and the evaluation counts
    res["counts"] = {t: {"evaluation": int(ev["tour"].eq(t).sum()), "market_subset": int((ev["tour"].eq(t) & mk).sum()),
                         "tour_level_main_draw": int((ev["tour"].eq(t) & ev["level_group"].isin(["GS", "FIN", "T1000", "T500", "T250"])).sum())}
                     for t in C.TOURS}
    RESULTS.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"wrote {RESULTS.name}, {CELLS.name} ({len(cells)} cells), {CALIBRATION.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
