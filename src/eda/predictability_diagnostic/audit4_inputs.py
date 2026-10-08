"""Audit B of Stage 4, check 3: does anything use the match itself, later rounds of the same event, or rankings dated
after the match?

    rankings        every evaluation player row's rank and points (Stage 0, from the match files) against Sackmann's
                    weekly ranking lists on disk: the list in force on the tournament's date (the latest dated on or
                    before it), the one before, the next one, and any later list within eight weeks. A rank that
                    matches only a later list would carry results the match could not know
    qualifying      the same for qualifying matches, which the files date at the main draw's Monday although they are
                    played before it (a Grand Slam's qualifying the week before): the list of that Monday is then
                    dated after the match; whether it differs from the list in force when qualifying began is counted
    format          the match tiebreak read from the match's own score (Stage 0 flags a match "match_tiebreak" when its
                    own score shows a bracketed deciding tiebreak, even where its event plays standard sets): the
                    evaluation matches so flagged, and the effect of reading them as their round-mates are read
                    (standard) on every women's row that uses the format, rescored given Elo and given the market.
                    Best of five read from the score is Stage 4's own finding and is only counted here

Writes, in data/studies/predictability_diagnostic/audit4/:
    rank_check.csv     counts by tour, source, level group, qualifying and how the rank matches the lists
    inputs.json        the summary

Run: ./python.sh src/eda/predictability_diagnostic/audit4_inputs.py   (a few minutes)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import audit4_common as A  # noqa: E402
from src.eda.predictability_diagnostic import audit4_recompute as RC  # noqa: E402

RANKINGS = A.ROOT / "data" / "dump" / "rankings" / "sackmann_archive"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def lists(tour: str) -> pd.DataFrame:
    fr = []
    for f in sorted((RANKINGS / tour).glob(f"{tour}_rankings_*.parquet")):
        r = pd.read_parquet(f, columns=["ranking_date", "rank", "player", "points"])
        fr.append(r)
    r = pd.concat(fr, ignore_index=True)
    r["date"] = pd.to_datetime(r["ranking_date"], format="%Y%m%d")
    r["rank"] = pd.to_numeric(r["rank"], errors="coerce")
    r["points"] = pd.to_numeric(r["points"], errors="coerce")
    r["player_id"] = f"{tour}:" + r["player"].astype(str)
    return r.drop_duplicates(["player_id", "date"])[["player_id", "date", "rank", "points"]]


def rank_check(m: pd.DataFrame, p: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    ev = np.repeat(m["evaluation"].to_numpy() & m["year"].between(2013, 2026).to_numpy(), 2)
    rows = pd.DataFrame({"player_id": p["player_id"].to_numpy(), "rank": p["rank"].to_numpy("float64"),
                         "points": p["rank_points"].to_numpy("float64"), "match": np.arange(len(p)) // 2,
                         "won": p["won"].to_numpy(bool)})[ev & p["rank"].notna().to_numpy()]
    mm = m.iloc[rows["match"].to_numpy()]
    rows = rows.assign(tour=mm["tour"].to_numpy(), date=mm["tournament_date"].to_numpy(), source=mm["source"].to_numpy(),
                       level=mm["level"].to_numpy(), qualifying=mm["qualifying"].to_numpy(bool), year=mm["year"].to_numpy(),
                       tid=mm["tournament_id"].to_numpy())
    out = []
    for tour in ("atp", "wta"):
        L = lists(tour)
        dates = np.sort(L["date"].unique())
        x = rows[rows["tour"].eq(tour)].copy()
        di = np.searchsorted(dates, x["date"].to_numpy(), side="right") - 1          # the list in force
        x["d_in_force"] = np.where(di >= 0, dates[np.maximum(di, 0)], np.datetime64("NaT"))
        x["d_before"] = np.where(di >= 1, dates[np.maximum(di - 1, 0)], np.datetime64("NaT"))
        for k in range(1, 9):                                                           # the next eight lists
            x[f"d_after{k}"] = np.where(di + k < len(dates), dates[np.minimum(di + k, len(dates) - 1)], np.datetime64("NaT"))
        x["covered"] = (di >= 0) & (x["date"].to_numpy() <= dates[-1])
        Li = L.set_index(["player_id", "date"])
        for c in ["d_in_force", "d_before"] + [f"d_after{k}" for k in range(1, 9)]:
            hit = Li.reindex(pd.MultiIndex.from_arrays([x["player_id"].to_numpy(), pd.to_datetime(x[c]).to_numpy()]))
            x[f"{c}_same"] = (hit["rank"].to_numpy() == x["rank"].to_numpy()) & (
                (hit["points"].to_numpy() == x["points"].to_numpy()) | x["points"].isna().to_numpy())
            if c in ("d_in_force", "d_before"):
                x[f"{c}_points"] = hit["points"].to_numpy()
        later_any = np.any([x[f"d_after{k}_same"] for k in range(1, 9)], axis=0)
        x["how"] = np.select([~x["covered"], x["d_in_force_same"], x["d_before_same"], later_any],
                             ["after the last list on disk", "the list in force on the tournament date", "the list before it",
                              "only a later list"], "no list within the window")
        # which later list, in weeks after the tournament date
        first_later = np.full(len(x), np.nan)
        for k in range(8, 0, -1):
            first_later = np.where(x[f"d_after{k}_same"].to_numpy() & ~x["d_in_force_same"].to_numpy() & ~x["d_before_same"].to_numpy(),
                                   ((pd.to_datetime(x[f"d_after{k}"]) - pd.to_datetime(x["date"])).dt.days).to_numpy(), first_later)
        x["later_list_days_after"] = first_later
        out.append(x)
    X = pd.concat(out, ignore_index=True)
    X["group"] = np.where(X["qualifying"], X["level"].map({"GS": "GSQ", "CH": "CHQ"}).fillna("TQ"), X["level"])
    # rows matching no list in the window: the nearest list (any date) whose rank and points they carry
    far = X[X["how"].eq("no list within the window")]
    nearest = []
    for tour in ("atp", "wta"):
        L = lists(tour)
        D: dict = {}
        for r in L.itertuples(index=False):
            D.setdefault(r.player_id, []).append((r.date, r.rank, r.points))
        for r in far[far["tour"].eq(tour)].itertuples(index=False):
            offs = [(d - pd.Timestamp(r.date)).days for d, a, b in D.get(r.player_id, [])
                    if a == r.rank and (b == r.points or pd.isna(r.points))]
            nearest.append({"tour": tour, "source": r.source, "tid": r.tid, "year": int(r.year),
                            "nearest_list_days": min(offs, key=abs) if offs else None})
    near = pd.DataFrame(nearest)
    near["nearest"] = near["nearest_list_days"].map(lambda v: "none on disk" if v is None or pd.isna(v) else str(int(v)))
    tab = X.groupby(["tour", "source", "group", "how"]).size().rename("player_rows").reset_index()
    # does the list dated on the tournament's date hold the match's own result? If it did, a player who won the match
    # would gain more points from the list before to that list than one who lost it. Qualifying (played before the
    # date) is the case that matters; main draws (played on or after it) are the reference
    gain = X["d_in_force_points"] - X["d_before_points"]
    ok = X["d_in_force_same"] & gain.notna()
    own_result = (X[ok].assign(gain=gain[ok]).groupby(["tour", "group", "won"])["gain"]
                  .agg(["count", "mean", "median"]).round(3).reset_index().to_dict("records"))
    # qualifying: is the list of the main draw's Monday different from the one in force a week earlier, and which
    # does the rank follow?
    q = X[X["qualifying"]].copy()
    summ = {"player_rows": int(len(X)), "by_how": X.groupby(["tour", "how"]).size().unstack(fill_value=0).to_dict(),
            "points_gain_to_the_list_in_force_by_result": own_result,
            "only_later": X[X["how"].eq("only a later list")].groupby(["tour", "source", "group", "year"]).size()
            .rename("rows").reset_index().to_dict("records"),
            "only_later_days_after": X.loc[X["how"].eq("only a later list"), "later_list_days_after"].value_counts().sort_index().to_dict(),
            "qualifying_rows": int(len(q)),
            "qualifying_in_force_differs_from_week_before": int((q["d_in_force_same"] != q["d_before_same"]).sum()),
            "qualifying_follows_in_force_not_week_before": int((q["d_in_force_same"] & ~q["d_before_same"]).sum()),
            "qualifying_follows_week_before_not_in_force": int((~q["d_in_force_same"] & q["d_before_same"]).sum()),
            "a_week_or_more_later": X[X["how"].eq("only a later list") & (X["later_list_days_after"] >= 7)][
                ["tour", "player_id", "date", "source", "group", "tid", "rank", "points", "later_list_days_after"]].astype(str).to_dict("records"),
            "last_list_on_disk": {t: str(lists(t)["date"].max().date()) for t in ("atp", "wta")},
            "no_list_in_window_nearest": near.groupby(["tour", "source", "tid", "year", "nearest"]).size().rename("rows")
            .reset_index().astype(str).to_dict("records")}
    return tab, summ


def qualifying_dates(m: pd.DataFrame) -> dict:
    """Whether qualifying rows carry the main draw's date (same tournament id)."""
    q = m[m["qualifying"].astype(bool) & m["evaluation"]]
    md = m[~m["qualifying"].astype(bool)].groupby("tournament_id")["tournament_date"].min()
    d = q["tournament_date"] - q["tournament_id"].map(md)
    return {"qualifying_evaluation_matches": int(len(q)),
            "same_date_as_main_draw": int((d == pd.Timedelta(0)).sum()),
            "other_or_no_main_draw": int((d != pd.Timedelta(0)).sum())}


def format_check(m: pd.DataFrame, p: pd.DataFrame, ctx: dict) -> dict:
    ev = m["evaluation"].to_numpy()
    mtb = m["format"].eq("match_tiebreak").to_numpy()
    br = m["score"].fillna("").str.contains(r"\[").to_numpy()
    evkey = m["ev"].to_numpy()
    # an event "plays match tiebreaks" when most of its matches carry the flag; a flag in an event that does not is
    # the match's own score speaking
    share = pd.Series(mtb).groupby(evkey).transform("mean").to_numpy()
    own = ev & mtb & (share < 0.5)
    rows = m[own][["match_id", "tour", "tournament_name", "year", "round", "score"]]
    sets = p["sets_won_n"].to_numpy("float64").reshape(-1, 2)
    with np.errstate(invalid="ignore"):
        w = np.where(np.isnan(sets).all(axis=1), np.nan, np.fmax(sets[:, 0], sets[:, 1]))
        rec = (m["best_of"].to_numpy("float64") == 5) | (m["format"].to_numpy() == "short_sets")
        bo5_own = ev & (w >= 3) & ~rec
    res = {"evaluation_matches_flagged_match_tiebreak": int((ev & mtb).sum()),
           "of_which_event_plays_standard_sets": int(own.sum()), "matches": rows.astype(str).to_dict("records"),
           "evaluation_matches_with_bracketed_score": int((ev & br).sum()),
           "best_of_five_from_own_score": int(bo5_own.sum()),
           "best_of_five_from_own_score_by_event": m[bo5_own].groupby(["tour", "tournament_name", "round"]).size().rename("n")
           .reset_index().to_dict("records")}
    # rescore the women's format rows with the four read as standard (their round-mates' format)
    f = pd.read_parquet(A.OUT / "stage4_features.parquet")
    fi = pd.Series(np.arange(len(f)), index=f["match_id"].to_numpy())
    target = np.flatnonzero(own)
    rows_of = {k: np.sort(v) for k, v in p.groupby("player_id").indices.items()}
    X = RC.plain_arrays(m, p, ctx)
    s3 = pd.read_parquet(A.OUT / "stage3_ratings.parquet", columns=["match_id", "p_serve_a", "p_serve_b"]).set_index("match_id")
    new_vals = {}
    check = []
    for i in target:
        fmt = RC.match_format(m, p, i)
        for flag in (True, False):
            hf = RC.history_features(X, ctx, rows_of, i, {**fmt, "mtb": flag})
            pa, pb = s3.loc[m.at[i, "match_id"], ["p_serve_a", "p_serve_b"]]
            hf["rating_matchup|single"] = float(A.safe_logit(A.p_match(float(pa), float(pb), fmt["bo"], fmt["rule"], flag)))
            for c in ("rating_matchup|single", "mu_points|52 weeks", "mu_points|decayed", "mu_components|52 weeks",
                      "mu_components|decayed", "mu_games|52 weeks", "mu_games|decayed"):
                if flag:
                    check.append(abs(hf[c] - float(f.at[int(fi[m.at[i, "match_id"]]), c])) if np.isfinite(hf[c]) else 0.0)
                else:
                    new_vals.setdefault(c, {})[int(fi[m.at[i, "match_id"]])] = hf[c]
    res["as_flagged_reproduced_max_abs_diff"] = float(max(check)) if check else None
    keys = A.plan_keys(len(f))
    eff = []
    for c, vals in new_vals.items():
        t = f["tour"].to_numpy() == "wta"
        x0 = f[c].to_numpy("float64")
        x1 = x0.copy()
        for k, v in vals.items():
            x1[k] = v
        rec = {"row": c, "feature_before": {str(k): float(x0[k]) for k in vals}, "feature_after": {str(k): float(v) for k, v in vals.items()}}
        for tag, xx in (("as_built", x0), ("read_as_standard", x1)):
            idx = np.flatnonzero(t & np.isfinite(xx))
            y, yr, evv = f["a_won"].to_numpy()[idx], f["year"].to_numpy()[idx], f["evaluation"].to_numpy()[idx]
            le = A.logit(np.clip(f["p_elo"].to_numpy("float64")[idx], 1e-9, 1 - 1e-9))
            pm = f["p_mkt"].to_numpy("float64")[idx]
            lm = A.logit(np.clip(np.nan_to_num(pm, nan=0.5), 1e-9, 1 - 1e-9))
            for s, base, sub in (("elo", le, None), ("market", lm, np.isfinite(pm))):
                r = A.score_feature(xx[idx][:, None], y, yr, evv, base, 2019, sub=sub)
                rec[f"{tag}_{s}"] = r["all"]["imp"]
        rec["change_elo"] = rec["read_as_standard_elo"] - rec["as_built_elo"]
        rec["change_market"] = rec["read_as_standard_market"] - rec["as_built_market"]
        eff.append(rec)
        log(f"  {c}: given Elo {rec['as_built_elo']:.6f} -> {rec['read_as_standard_elo']:.6f}; market "
            f"{rec['as_built_market']:.6f} -> {rec['read_as_standard_market']:.6f}")
    res["effect"] = eff
    return res


def main() -> int:
    m, p = A.load_tables()
    m = m.merge(pd.read_parquet(A.OUT / "stage0_matches.parquet", columns=["match_id", "source"]), on="match_id", how="left")
    ctx = A.constants()
    log("tables loaded")
    tab, rk = rank_check(m, p)
    A.AUDIT.mkdir(parents=True, exist_ok=True)
    tab.to_csv(A.AUDIT / "rank_check.csv", index=False)
    log(f"rankings: {rk['by_how']}")
    qd = qualifying_dates(m)
    log(f"qualifying dates: {qd}")
    fm = format_check(m, p, ctx)
    log(f"format: {fm['of_which_event_plays_standard_sets']} matches flagged from their own score")
    A.save_json({"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "rankings": rk,
                 "qualifying_dates": qd, "format": fm, "seconds": round(time.time() - T0, 1)}, "inputs.json")
    log("wrote rank_check.csv and inputs.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
