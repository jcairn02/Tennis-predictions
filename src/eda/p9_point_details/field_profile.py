"""The P9 point details: what the newer MatchBeats copy's eight per-point fields and its momentum score hold.

Work package P9 (docs/studies/serve_speed_acquisition/README.md, section 9.7) added, beside each point of the older
copy, eight fields of the newer copy (firstServer, lastHitter, serveClassId, tm1Shot, tm2Shot, pointDuration,
tm1AtNet, tm2AtNet) and a momentum score per game (game_momentum_tm1/_tm2). This script measures, field by field,
whether each one carries information the project did not already hold:

* its fill;
* whether it equals a field the older copy or the rally-analysis files already carried;
* for the duration and net fields, at how many events it behaves as its name says.

It reads the staged tables (data/dump/points/infosys_atp_recent/), read only, and no match result. Output:
data/studies/p9_point_details/field_profile.json and field_profile_events.csv (one row per event).

    ./python.sh src/eda/p9_point_details/field_profile.py      # about two minutes
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DUMP = ROOT / "data" / "dump" / "points" / "infosys_atp_recent"
OUT = ROOT / "data" / "studies" / "p9_point_details"

KEY = ["year", "event_id", "match_id"]
NEWER = ["firstServer", "lastHitter", "serveClassId", "tm1Shot", "tm2Shot", "pointDuration", "tm1AtNet", "tm2AtNet"]
SERVE_END = {"A", "DF"}
RALLY_END = {"W", "UE", "FE"}
MIN_RALLY_POINTS = 200          # points with a known rally length an event needs for its duration-rally correlation
RHO_DURATION_LIKE = 0.8         # an event's duration "behaves as a duration" at this Spearman correlation with rally
RATIO_DURATION_LIKE = 2.0       # ... or when its rally-ended points last this many times its serve-ended ones


def load_points() -> pd.DataFrame:
    cols = KEY + ["set", "game", "seq", "server", "scorer", "result", "tm1Rally", "tm2Rally", "rallyLengthMissing",
                  "currentMatchDuration", "game_momentum_tm1", "game_momentum_tm2"] + NEWER
    p = pd.read_parquet(DUMP / "points.parquet", columns=cols)
    for c in ["set", "game", "seq", "tm1Rally", "tm2Rally", "tm1Shot", "tm2Shot", "pointDuration",
              "currentMatchDuration", "game_momentum_tm1", "game_momentum_tm2"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    return p.sort_values(KEY + ["set", "game", "seq"], kind="mergesort").reset_index(drop=True)


def spearman(a: pd.Series, b: pd.Series) -> float:
    if len(a) < 3:
        return float("nan")
    return float(a.rank().corr(b.rank()))


def momentum_rule(p: pd.DataFrame) -> dict:
    """The momentum score per game against the games' outcomes: its step from the previous game of the match, by
    who served and who won the game (the game's last point decides it)."""
    g = p.groupby(KEY + ["set", "game"], sort=False).agg(
        m1=("game_momentum_tm1", "first"), m2=("game_momentum_tm2", "first"),
        n_m1=("game_momentum_tm1", "nunique"), server=("server", "first"), winner=("scorer", "last"),
        n_points=("scorer", "size")).reset_index()
    g["step"] = g["m1"] - g.groupby(KEY)["m1"].shift()
    g["first_of_set"] = g.groupby(KEY + ["set"]).cumcount().eq(0)
    g["cls"] = g["server"].astype(str) + "_" + g["winner"].astype(str)
    s = g.dropna(subset=["step"])
    modal = s.groupby("cls")["step"].agg(lambda x: x.mode().iloc[0])
    follows = s["step"].eq(s["cls"].map(modal))
    finer = s.groupby(["cls", "n_points", "first_of_set"])["step"].transform(lambda x: x.mode().iloc[0])
    return {
        "games": int(len(g)),
        "constant_within_game_share": float((g["n_m1"] <= 1).mean()),
        "sum_tm1_tm2_value_counts": {str(k): int(v) for k, v in (g["m1"] + g["m2"]).value_counts().head(5).items()},
        "modal_step_by_server_winner": {k: float(v) for k, v in modal.items()},
        "share_following_modal_step": float(follows.mean()),
        "share_following_modal_step_given_points_and_set_start": float(s["step"].eq(finer).mean()),
        "note": "cls = server_winner (1_1: player 1 holds; 1_2: player 1 broken; 2_2: player 2 holds; 2_1: player 1 "
                "breaks). The value attached to a game is the score after it.",
    }


def per_event(p: pd.DataFrame) -> pd.DataFrame:
    rally = p["tm1Rally"] + p["tm2Rally"]
    known = p["rallyLengthMissing"].eq("FALSE") & rally.between(1, 60)
    clock_step = p.groupby(KEY)["currentMatchDuration"].diff().shift(-1)
    q = p.assign(rally=rally, known=known, clock_step=clock_step,
                 serve_end=p["result"].isin(SERVE_END), rally_end=p["result"].isin(RALLY_END),
                 net_new=p["tm1AtNet"].eq("TRUE") | p["tm2AtNet"].eq("TRUE"))
    rows = []
    for (year, event), e in q.groupby(["year", "event_id"], sort=True):
        kn = e[e["known"] & e["pointDuration"].notna()]
        se = e.loc[e["serve_end"], "pointDuration"].median()
        re_ = e.loc[e["rally_end"], "pointDuration"].median()
        cs = e[e["clock_step"].between(0, 600) & e["pointDuration"].notna()]
        rows.append({
            "year": year, "event_id": event, "points": len(e), "matches": e["match_id"].nunique(),
            "rally_known_share": float(e["known"].mean()),
            "duration_median": float(e["pointDuration"].median()),
            "duration_serve_end_median": float(se), "duration_rally_end_median": float(re_),
            "duration_ratio_rally_to_serve": float(re_ / se) if se and se > 0 else float("nan"),
            "rho_duration_rally": spearman(kn["pointDuration"], kn["rally"]) if len(kn) >= MIN_RALLY_POINTS
            else float("nan"),
            "rho_duration_clock_step": spearman(cs["pointDuration"], cs["clock_step"]) if len(cs) >= MIN_RALLY_POINTS
            else float("nan"),
            "net_share_new": float(e["net_new"].mean()),
        })
    ev = pd.DataFrame(rows)
    ev["duration_like"] = (ev["rho_duration_rally"].ge(RHO_DURATION_LIKE)
                           | ev["duration_ratio_rally_to_serve"].gt(RATIO_DURATION_LIKE))
    return ev


def net_against_rally_files() -> dict:
    r = pd.read_parquet(DUMP / "rally.parquet", columns=KEY + ["t1NetPoint", "t2NetPoint"])
    r["net"] = r["t1NetPoint"].eq("TRUE") | r["t2NetPoint"].eq("TRUE")
    ev = r.groupby(["year", "event_id"])["net"].any()
    return {"rally_files_t1NetPoint_true": int(r["t1NetPoint"].eq("TRUE").sum()),
            "rally_files_t2NetPoint_true": int(r["t2NetPoint"].eq("TRUE").sum()),
            "rally_files_events_with_net": sorted(f"{y}/{e}" for (y, e), v in ev.items() if v)}


def rally_coverage(p: pd.DataFrame) -> list[dict]:
    m = pd.read_parquet(DUMP / "matches.parquet", columns=KEY + ["level", "draw"])
    known = p["rallyLengthMissing"].eq("FALSE")
    g = known.groupby([p[k] for k in KEY]).mean().rename("rally_share").reset_index().merge(m, on=KEY, how="left")
    g["with_rally"] = g["rally_share"] >= 0.5
    t = g.groupby(["year", "level", "draw"]).agg(matches=("with_rally", "size"), with_rally=("with_rally", "sum"))
    return [{"year": y, "level": lv, "draw": d, "matches": int(r.matches), "with_rally_lengths": int(r.with_rally)}
            for (y, lv, d), r in t.iterrows()]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = load_points()
    newer = p["firstServer"].notna()
    q = p[newer]
    first = q.groupby(KEY, sort=False).first()
    cls_map = {"1": "A", "4": "DF"}
    sc_agree = np.where(q["serveClassId"].isin(cls_map), q["serveClassId"].map(cls_map).eq(q["result"]),
                        ~q["result"].isin(SERVE_END))
    rally_old = q["tm1Rally"] + q["tm2Rally"]
    shots_new = q["tm1Shot"] + q["tm2Shot"]
    differ = q["tm1Shot"].ne(q["tm1Rally"]) | q["tm2Shot"].ne(q["tm2Rally"])
    ev = per_event(q)
    net_files = net_against_rally_files()
    net_events_new = sorted(f"{y}/{e}" for y, e in ev.loc[ev["net_share_new"] > 0, ["year", "event_id"]].values)
    out = {
        "inputs": {"points": str((DUMP / "points.parquet").relative_to(ROOT)), "points_rows": int(len(p)),
                   "rally": str((DUMP / "rally.parquet").relative_to(ROOT)),
                   "matches": str((DUMP / "matches.parquet").relative_to(ROOT))},
        "points_with_newer_copy": int(newer.sum()),
        "matches_with_newer_copy": int(q.groupby(KEY).ngroups),
        "firstServer": {"equals_server_of_first_point_share": float(
            first["firstServer"].str[0].eq(first["server"].astype(str)).mean()),
            "matches": int(len(first))},
        "lastHitter": {"non_empty_points": int(q["lastHitter"].fillna("").ne("").sum())},
        "serveClassId": {"crosstab_with_result": {str(k): {str(r): int(v) for r, v in row.items() if v}
                                                  for k, row in pd.crosstab(q["serveClassId"], q["result"]).iterrows()},
                         "agreement_share_1A_4DF_2rest": float(np.mean(sc_agree))},
        "shot_counts": {"tm1Shot_equals_tm1Rally_share": float(q["tm1Shot"].eq(q["tm1Rally"]).mean()),
                        "tm2Shot_equals_tm2Rally_share": float(q["tm2Shot"].eq(q["tm2Rally"]).mean()),
                        "points_differing": int(differ.sum()),
                        "differing_with_rally_length_present_share": float(
                            q.loc[differ, "rallyLengthMissing"].eq("FALSE").mean()),
                        "fills_old_zero_new_positive": int(((rally_old == 0) & (shots_new > 0)).sum()),
                        "rally_length_known_share": float(q["rallyLengthMissing"].eq("FALSE").mean())},
        "pointDuration": {"quantiles": {str(k): float(v) for k, v in
                                        q["pointDuration"].quantile([.01, .1, .5, .9, .99]).items()},
                          "min": float(q["pointDuration"].min()), "max": float(q["pointDuration"].max()),
                          "events": int(len(ev)),
                          "events_duration_like": int(ev["duration_like"].sum()),
                          "events_ratio_over_2": int(ev["duration_ratio_rally_to_serve"].gt(RATIO_DURATION_LIKE).sum()),
                          "events_rho_rally_ge_0.8": int(ev["rho_duration_rally"].ge(RHO_DURATION_LIKE).sum()),
                          "median_event_ratio_rally_to_serve": float(ev["duration_ratio_rally_to_serve"].median()),
                          "median_event_rho_rally": float(ev["rho_duration_rally"].median()),
                          "median_event_rho_clock_step": float(ev["rho_duration_clock_step"].median()),
                          "matches_at_duration_like_events": int(ev.loc[ev["duration_like"], "matches"].sum())},
        "net": {"tm1AtNet_true": int(q["tm1AtNet"].eq("TRUE").sum()), "tm2AtNet_true": int(q["tm2AtNet"].eq("TRUE").sum()),
                "events_with_net_new": len(net_events_new),
                "events_with_net_rally_files": len(net_files["rally_files_events_with_net"]),
                "same_events": net_events_new == net_files["rally_files_events_with_net"],
                "matches_at_net_events": int(ev.loc[ev["net_share_new"] > 0, "matches"].sum()),
                **{k: v for k, v in net_files.items() if k != "rally_files_events_with_net"},
                "events": net_events_new},
        "momentum": momentum_rule(q),
        "rally_coverage_by_level": rally_coverage(p),
    }
    ev.to_csv(OUT / "field_profile_events.csv", index=False)
    (OUT / "field_profile.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("rally_coverage_by_level",)}, indent=1,
                     default=str)[:6000])


if __name__ == "__main__":
    main()
