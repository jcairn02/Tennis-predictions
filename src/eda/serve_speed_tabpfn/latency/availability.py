"""Latency follow-up (data/studies/serve_speed_tabpfn/latency/plan.md): the day from which each speed row may enter any
feature (the filter's history and the as-of edition offsets alike), under the plan's fixed scenarios. Reads no match
result, outcome or price.

Scenarios (all day numbers are days since 1970-01-01, on the match clock of timing.parquet; lf = latest possible finish):
    A        lf + 1 (the backtest as run)
    B        today's sources, going forward, in every season:
             * Slams (Stage 0 level GS, every Slam source, main draw and qualifying): the event's last main-draw day +
               1 + 2 days of collection. The last main-draw day is the latest lf of the Slam-year's singles main-draw
               matches, men's and women's together (the feeds are collected once, after the event).
             * every other row (tour level, Challengers, team events, ITF; key statistics and point means alike): the
               first weekly ManTennisData publication that carries it, usable from the next day. Rule fixed from the
               repository's commit history (latency/evidence/mantd_publication.json): commits come every Sunday at a
               fixed local time (14:10 UTC in summer, 15:10 in winter) and carry matches finished by the Friday; a
               Saturday's or Sunday's matches wait for the following Sunday. So: S = the first Sunday on or after lf + 2,
               release = S + 1 (a Monday). Scored on the 681 matches the 10 fetched weekly versions place: exact 91.0%,
               too early 4.9%, too late 4.1% (the plan's fallback, the first Sunday after lf: 86.5% / 13.4% / 0.1%).
    L1..L14  lf + 1 + L for every speed row
    D        a daily tour-level collector (adaptive plan, data/studies/serve_speed_tabpfn/adaptive/plan.md): every
             non-Slam row at lf + 2 (a 1-day lag behind A: collected the morning after, with a day's slack because lf is
             the latest possible finish); Slam rows as in B
    E        today's weekly tour data with live Slam feeds: non-Slam rows as in B; Slam rows at lf + 2
    box_release  lf + 1 (Tennis My Life's daily download), for every Stage 0 player-match

Live use: pending(match_day, source_watermark) says whether a match's speed is still outstanding at forecast time. A
source's watermark is the last match day it has fully delivered; a match is pending while match_day > watermark. How a
live pipeline sets each watermark:
    ManTennisData     the Friday before its latest Sunday commit (mantd_watermark): a Sunday commit carries the matches
                      finished by the Friday; a missed weekly commit simply leaves the watermark where it was, so the
                      next week's matches stay pending
    daily collector   yesterday (daily_watermark): the morning run has the previous day's matches
    Slam feed         the last day whose matches have been collected (slam_feed_watermark): before an after-the-event
                      collection that is the day before the event began; with a live feed, yesterday
A match at an event that no speed source covers (Barcelona, say) is never pending: pass covered=False.
In the backtest the same logic is the release columns, at day granularity and on lf: with a Sunday commit usable from
the Monday, the first day a match is not pending under mantd_watermark is exactly release_B (tested); D and E's lf + 2
keep one more day of slack than a live "yesterday" watermark.

Writes data/studies/serve_speed_tabpfn/latency/availability.parquet: one row per Stage 0 player-match (rebuilt ids), with
in_panel / use from the speed panel, lf, release_A, release_B, release_L1, release_L3, release_L7, release_L14, rule_B,
slam_last_main_day, box_release, then (added 8 Oct, existing columns unchanged) release_D, release_E, rule_D, rule_E. The
release rules are defined for every row; only in_panel rows carry a speed.
Also writes latency/availability_diagnostics.json (men's 2024-26 frame sides, values only).

Run: ./python.sh src/eda/serve_speed_tabpfn/latency/availability.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "latency"
AVAIL = OUT / "availability.parquet"
DIAG = OUT / "availability_diagnostics.json"
S0_COLS = ["match_id", "tour", "year", "level", "qualifying", "tournament_id", "tournament_name", "player_a_id",
           "player_b_id"]
LAGS = (1, 3, 7, 14)
WEEKLY_GAP = 2            # S = the first Sunday on or after lf + 2
SLAM_COLLECTION = 2       # days after the day after the last main-draw day
DAILY_LAG = 2             # D's non-Slam rows and E's Slam rows: lf + 2
SCENARIOS = {"A": "release_A", "B": "release_B", **{f"L{k}": f"release_L{k}" for k in LAGS}, "D": "release_D",
             "E": "release_E"}


def weekday(day: np.ndarray) -> np.ndarray:
    """Monday = 0 ... Sunday = 6 for days since 1970-01-01 (a Thursday)."""
    return (np.asarray(day, dtype=np.int64) + 3) % 7


def first_sunday_on_or_after(day: np.ndarray) -> np.ndarray:
    d = np.asarray(day, dtype=np.int64)
    return d + (6 - weekday(d)) % 7


def weekly_release(lf: np.ndarray) -> np.ndarray:
    """ManTennisData's weekly publication: S = the first Sunday on or after lf + 2; usable from S + 1."""
    return first_sunday_on_or_after(np.asarray(lf, dtype=np.int64) + WEEKLY_GAP) + 1


def slam_last_main_day(m: pd.DataFrame) -> pd.Series:
    """Latest lf of each Slam-year's singles main-draw matches, both tours together; indexed by (year, slam)."""
    g = m[m["level"].eq("GS") & ~m["qualifying"].astype(bool)]
    return g.groupby(["year", "slam"])["lf"].max()


def build() -> pd.DataFrame:
    m = pd.read_parquet(P.S0, columns=S0_COLS)
    tm = pd.read_parquet(P.TIMING, columns=["match_id", "lf"])
    m = m.merge(tm, on="match_id", how="left", validate="one_to_one")
    assert m["lf"].notna().all()
    m["lf"] = m["lf"].astype("int64")
    m["slam"] = P.slam_of(m["level"], m["tournament_name"])
    last = slam_last_main_day(m)
    rows = pd.concat([m.assign(side="A", player_id=m["player_a_id"]), m.assign(side="B", player_id=m["player_b_id"])],
                     ignore_index=True).drop(columns=["player_a_id", "player_b_id", "tournament_name"])
    lf = rows["lf"].to_numpy(np.int64)
    is_slam = rows["level"].eq("GS").to_numpy()
    slam_last = last.reindex(pd.MultiIndex.from_arrays([rows["year"], rows["slam"]])).to_numpy()
    rows["slam_last_main_day"] = pd.array(np.where(is_slam, slam_last, np.nan), dtype="Int64")
    rows["release_A"] = lf + 1
    rel_b = np.where(is_slam, np.nan_to_num(slam_last, nan=-1) + 1 + SLAM_COLLECTION, weekly_release(lf))
    # a Slam row can never be released before its own match surely finished (guards a qualifying date oddity)
    rows["release_B"] = np.maximum(rel_b, lf + 1).astype("int64")
    rows["rule_B"] = np.where(is_slam, "slam_after_event", "mantd_weekly_sunday")
    for k in LAGS:
        rows[f"release_L{k}"] = lf + 1 + k
    rows["box_release"] = lf + 1
    pan = pd.read_parquet(P.PANEL, columns=["match_id", "side", "use"])
    rows = rows.merge(pan.rename(columns={"use": "use"}), on=["match_id", "side"], how="left")
    rows["in_panel"] = rows["use"].notna()
    rows["use"] = rows["use"].fillna(False).astype(bool)
    cols = ["match_id", "side", "player_id", "tour", "year", "level", "qualifying", "tournament_id", "slam", "in_panel",
            "use", "lf", "release_A", "release_B", "release_L1", "release_L3", "release_L7", "release_L14", "rule_B",
            "slam_last_main_day", "box_release"]
    rows = rows[cols]
    # scenarios of the adaptive plan, appended after the existing columns
    lf64 = rows["lf"].to_numpy(np.int64)
    slam_b = rows["release_B"].to_numpy(np.int64)
    is_slam = rows["level"].eq("GS").to_numpy()
    rows["release_D"] = np.where(is_slam, slam_b, lf64 + DAILY_LAG)
    rows["release_E"] = np.where(is_slam, lf64 + DAILY_LAG, slam_b)
    rows["rule_D"] = np.where(is_slam, "slam_after_event", "daily_collector")
    rows["rule_E"] = np.where(is_slam, "slam_live_feed", "mantd_weekly_sunday")
    for c in ("lf", "release_A", "release_B", "release_L1", "release_L3", "release_L7", "release_L14", "box_release",
              "release_D", "release_E"):
        rows[c] = rows[c].astype("int32")
    assert not rows.duplicated(["match_id", "side"]).any()
    for c in ("release_B", "release_D", "release_E"):
        assert (rows[c] >= rows["release_A"]).all(), c
    return rows


def load(columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(AVAIL, columns=columns)


def panel_with_release(scenario: str, use_only: bool = True) -> pd.DataFrame:
    """The speed panel with a column `release` = the day from which each row may enter features under `scenario`
    (A, B, L1, L3, L7 or L14). EditionOffsets(panel, tour, release="release") then fits on rows released by each day."""
    col = SCENARIOS[scenario]
    p = P.load_panel(use_only=use_only)
    a = load(["match_id", "side", col]).rename(columns={col: "release"})
    p = p.merge(a, on=["match_id", "side"], how="left", validate="one_to_one")
    assert p["release"].notna().all()
    p["release"] = p["release"].astype("int64")
    return p


# ------------------------------------------------------------------------------------------------
# live use: source watermarks
# ------------------------------------------------------------------------------------------------
def _days(x) -> np.ndarray:
    """Day numbers (days since 1970-01-01, as floats so that a missing watermark can be NaN) from ints, dates or
    timestamps."""
    a = np.asarray(x)
    if a.dtype.kind in "iuf":
        return a.astype(np.float64)
    d = pd.to_datetime(pd.Series(np.atleast_1d(a).ravel()))
    out = d.to_numpy().astype("datetime64[D]").astype(np.int64).astype(np.float64)
    out[d.isna().to_numpy()] = np.nan
    return out.reshape(a.shape)


def pending(match_day, source_watermark, covered=True):
    """Whether a match's speed is still outstanding at forecast time: its event is covered by a speed source and the
    match day is later than the source's watermark (the last match day the source has fully delivered). A missing
    watermark (the source has delivered nothing) counts as earlier than every match. Scalars or arrays; day numbers
    or dates. Live, match_day is the day the match finished; in a backtest use lf (the latest possible finish)."""
    md, wm = _days(match_day), _days(source_watermark)
    out = np.asarray(covered, dtype=bool) & ((md > wm) | np.isnan(wm))
    return bool(out) if np.ndim(out) == 0 else out


def mantd_watermark(latest_commit_day):
    """ManTennisData: the Friday before its latest Sunday commit (the last Friday on or before commit day - 2)."""
    d = _days(latest_commit_day).astype(np.int64) - 2
    w = d - (weekday(d) - 4) % 7
    return int(w) if np.ndim(w) == 0 else w


def daily_watermark(today):
    """A daily collector that runs each morning: yesterday."""
    w = _days(today).astype(np.int64) - 1
    return int(w) if np.ndim(w) == 0 else w


def slam_feed_watermark(last_collected_day):
    """A Slam feed: the last day whose matches have been collected (after the event: its last main-draw day; with a
    live feed: yesterday; before any collection: the day before the event began)."""
    w = _days(last_collected_day).astype(np.int64)
    return int(w) if np.ndim(w) == 0 else w


# ------------------------------------------------------------------------------------------------
# values-only diagnostics: men's 2024-26 frame sides
# ------------------------------------------------------------------------------------------------
def diagnostics(av: pd.DataFrame) -> dict:
    f = pd.read_parquet(P.MODEL_FRAME, columns=["match_id", "tour", "season", "debut_season"])
    fk = P.load_frame_keys()
    fk = fk.merge(f[["match_id", "debut_season"]], on="match_id")
    fk = fk[fk["tour"].eq("atp") & fk["season"].between(2024, 2026) & ~fk["debut_season"].astype(bool)]
    p = P.load_panel()
    p = p.merge(av[["match_id", "side", "release_A", "release_B", "release_L7", "release_D", "release_E"]],
                on=["match_id", "side"], how="left")
    p = p[p["tour"].eq("atp")]
    groups = {k: g.sort_values(["tdate", "tournament_id", "round_order"]) for k, g in p.groupby("player_id")}
    out = []
    for side, col in (("A", "player_a_id"), ("B", "player_b_id")):
        for r in fk.itertuples(index=False):
            g = groups.get(getattr(r, col))
            base = {"match_id": r.match_id, "side": side, "season": r.season, "slam_target": r.level == "GS"}
            if g is None:
                out.append({**base, "has_history": False})
                continue
            td, tid, ro, ob = (g["tdate"].to_numpy(), g["tournament_id"].to_numpy(), g["round_order"].to_numpy(),
                               g["obs"].to_numpy())
            earlier = ((td < r.tdate) | ((tid == r.tournament_id) & (ro < r.round_order))) & (ob >= r.es - 364)
            if not earlier.any():
                out.append({**base, "has_history": False})
                continue
            h = g[earlier]
            last = h.iloc[-1]
            rec = {**base, "has_history": True, "latest_same_event": last["tournament_id"] == r.tournament_id,
                   "latest_age": int(r.es - last["obs"]),
                   "latest_usable_A": bool(last["release_A"] <= r.es), "latest_usable_B": bool(last["release_B"] <= r.es),
                   "latest_usable_L7": bool(last["release_L7"] <= r.es),
                   "latest_usable_D": bool(last["release_D"] <= r.es), "latest_usable_E": bool(last["release_E"] <= r.es)}
            for sc in ("A", "B", "L7", "D", "E"):
                u = h[h[f"release_{sc}"] <= r.es]
                rec[f"usable_age_{sc}"] = int(r.es - u["obs"].iloc[-1]) if len(u) else np.nan
            out.append(rec)
    d = pd.DataFrame(out)
    res = {"population": "men's frame sides, seasons 2024-2026, debut seasons out", "sides": int(len(d)),
           "sides_with_history_364d": int(d["has_history"].sum())}
    h = d[d["has_history"]]
    res["all"] = summarise(h)
    res["by_split"] = []
    for (sl, same), g in h.groupby(["slam_target", "latest_same_event"]):
        res["by_split"].append({"slam_target": bool(sl), "latest_same_event": bool(same), **summarise(g)})
    res["by_season"] = [{"season": int(s), **summarise(g)} for s, g in h.groupby("season")]
    return res


def summarise(h: pd.DataFrame) -> dict:
    return {"sides": int(len(h)),
            "latest_usable_share_A": round(float(h["latest_usable_A"].mean()), 4),
            "latest_usable_share_B": round(float(h["latest_usable_B"].mean()), 4),
            "latest_usable_share_L7": round(float(h["latest_usable_L7"].mean()), 4),
            "any_usable_share_B": round(float(h["usable_age_B"].notna().mean()), 4),
            "median_age_latest_reading": float(h["latest_age"].median()),
            "median_age_latest_usable_A": float(h["usable_age_A"].median()),
            "median_age_latest_usable_B": float(h["usable_age_B"].median()),
            "median_age_latest_usable_L7": float(h["usable_age_L7"].median()),
            "latest_usable_share_D": round(float(h["latest_usable_D"].mean()), 4),
            "latest_usable_share_E": round(float(h["latest_usable_E"].mean()), 4),
            "median_age_latest_usable_D": float(h["usable_age_D"].median()),
            "median_age_latest_usable_E": float(h["usable_age_E"].median())}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    av = build()
    av.to_parquet(AVAIL, index=False)
    pr = av[av["in_panel"]]
    print(f"wrote {AVAIL.name}: {len(av):,} Stage 0 player-matches, {int(pr.shape[0]):,} panel rows "
          f"({int(pr['use'].sum()):,} use)")
    lagd = (pr["release_B"] - pr["lf"]).groupby(pr["rule_B"]).describe()
    print(lagd.to_string())
    diag = diagnostics(av)
    diag["release_B_minus_lf_panel_use"] = {
        rule: {str(k): int(v) for k, v in (g["release_B"] - g["lf"]).value_counts().sort_index().items()}
        for rule, g in pr[pr["use"]].groupby("rule_B")}
    DIAG.write_text(json.dumps(diag, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in diag.items() if k != "release_B_minus_lf_panel_use"}, indent=1, default=str))


if __name__ == "__main__":
    main()
