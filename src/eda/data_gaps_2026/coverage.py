"""Coverage of the history the model reads: matches and box scores by tour, level and month, against the same months a
year earlier, and the latest weeks against the same weeks a year earlier. Outcome-free: no result column is read.

Why (13 Oct 2026, docs/studies/data_gaps_2026/): Sackmann's files ended in early June 2026; Stage 0 has since read new
results only from Tennis My Life, and the levels Tennis My Life does not publish (ITF, women's qualifying, WTA 125, men's
Challenger qualifying) fell out of the history for four months before anyone saw it. This check flags such a loss within
weeks.

The measures, per tour and level (Stage 0's map_level, plus ALL and LOWER = TQ, GSQ, CH, CHQ, ITF, ITFQ):
    monthly   matches, and matches with a box score, over a month and its two neighbours, against the same three months a
              year earlier: the unpriced-leads gate's measure (src/eda/unpriced_leads/look.py, gate_mask). Flagged below
              RATIO where the year before held at least MIN_PRIOR; only months whose window has ended LAG_DAYS before
              the as-of day. Counts are judged only for the levels played every week (STEADY) and for ALL and LOWER (a
              Slam or a 1000 that changes month moves a level's count, not the feed); the share of matches with a box
              score ("box_share") is judged for every level (Roland Garros 2026's main draws: 127 matches, 0 box scores).
    recent    the RECENT_DAYS days ending LAG_DAYS before the as-of day, against the same days 52 weeks earlier (tournament
              dates are Mondays, so 364 days keeps them aligned); the same ratio and floor; only the levels played every
              week (STEADY), whose counts do not jump with the calendar. Catches a feed lost in the last few weeks.
A window counts the matches of the events that started in it (Stage 0's tournament_date).

Inputs: a Stage 0 matches table (default the repository's), optionally with the accepted packages and feeds merged by
additions.merge, as every build merges them (--with-accepted).
Outputs (--out, default data/studies/data_gaps_2026/coverage/<label>/): cells.csv (tour, level, month: matches, box),
monthly.csv, flags.csv, summary.json. Exit code 3 when the alarm is up: a recent flag, or a monthly flag in the last
ALARM_MONTHS judged months (older flags are history; the scheduled job alerts on the exit code).
Run: ./python.sh src/eda/data_gaps_2026/coverage.py [--stage0 <folder or parquet>] [--with-accepted] [--as-of YYYY-MM-DD]
     [--label <name>] [--from YYYY-MM]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
OUT = ROOT / "data" / "studies" / "data_gaps_2026" / "coverage"
COLS = ["match_id", "tour", "map_level", "tournament_date", "has_box", "tournament_id", "round", "player_a_id",
        "player_b_id"]
LOWER = ("TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ")     # the unpriced-leads gate's "lower_level": qualifying, CH, ITF
STEADY = ("TQ", "CH", "CHQ", "ITF", "ITFQ")           # levels with events every week of the season
RATIO = 0.7                                           # the registered gate's ratio (look.GATE_RATIO)
MIN_PRIOR = 30                                        # a cell the year before smaller than this is not judged
RECENT_DAYS = 28
LAG_DAYS = 3                                          # results reach the feeds a day or two late
MEASURES = ("matches", "box")
ALARM_MONTHS = 2                                      # monthly flags in the last two judged months raise the alarm
BASELINE_YEARS = (1, 2)                               # the baseline: the larger of 1 and 2 years earlier
UNJUDGED = ("TEAM", "FIN")                            # irregular, and outside the model's frame
# gaps known and accepted, reported but not alarmed: "<tour> <level> <measure>" -> (why, until when[, (first month,
# last month)]): with months, only the monthly cells of those months are acknowledged (a new gap in another month, and
# the recent window, still raise the alarm)
_ITF_HOLE = ("ITF box scores of 1 June - 14 September 2026: no source counts as Stage 0 does (the ITF's live data starts "
             "on 15 Sep; SofaScore's 2026 ITF box scores lack break points; TennisLive's miss points in 15% of matches; "
             "docs/studies/data_gaps_2026/ § 7); the all-level and lower-level totals follow it", "2027-01-31",
             ("2026-05", "2026-10"))
KNOWN = {
    "wta GSQ box_share": ("results only by design since 13 Oct 2026: the WTA API's Slam box scores count differently "
                          "from Stage 0's (4-37% of counts equal); box scores from the Slam feeds are separate work "
                          "(docs/studies/data_gaps_2026/)", "2027-03-31"),
    "wta GSQ box": ("as above", "2027-03-31"),
    **{f"{t} {lv} {ms}": _ITF_HOLE for t in ("atp", "wta") for lv in ("ITF", "LOWER", "ALL")
       for ms in ("box", "box_share")},
}


def known(tour: str, level: str, measure: str, as_of: pd.Timestamp, month: str | None = None) -> str | None:
    """The acknowledgement's reason, if this cell (a monthly one: `month`; a recent one: None) is acknowledged."""
    k = KNOWN.get(f"{tour} {level} {measure}")
    if not k or as_of > pd.Timestamp(k[1]):
        return None
    if len(k) > 2:
        if month is None or not (k[2][0] <= str(month) <= k[2][1]):
            return None
    return k[0]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(stage0: Path = STAGE0, with_accepted: bool = False, accepted: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """The matches table (COLS), with the accepted packages and feeds merged by additions.merge itself, as every build
    and prediction run merges them."""
    stage0 = Path(stage0)
    path = stage0 if stage0.suffix == ".parquet" else stage0 / "stage0_matches.parquet"
    rec = {"stage0": str(path), "stage0_sha256": sha256(path), "packages": []}
    if with_accepted:
        from src.eda.current_best_model import additions as AD
        packages = AD.listed(accepted or AD.ACCEPTED)
        m = pd.read_parquet(path)
        mp = pd.read_parquet(path.with_name("stage0_match_players.parquet"))
        t = pd.DataFrame({"match_id": pd.Series(dtype=str)})
        m, _, _, merged = AD.merge(m, mp, t, packages)
        m = m[COLS]
        rec["packages"] = merged["packages"]
    else:
        m = pd.read_parquet(path, columns=COLS)
    m["tournament_date"] = pd.to_datetime(m["tournament_date"])
    return m, rec


def cells(m: pd.DataFrame) -> pd.DataFrame:
    """Matches and box scores by tour, level and month, with ALL and LOWER rows per tour."""
    f = pd.DataFrame({"tour": m["tour"].astype(str), "level": m["map_level"].astype(str),
                      "month": m["tournament_date"].dt.to_period("M"), "box": m["has_box"].astype(bool)})
    parts = [f, f.assign(level="ALL"), f[f["level"].isin(LOWER)].assign(level="LOWER")]
    g = pd.concat(parts, ignore_index=True).groupby(["tour", "level", "month"], observed=True)
    return g.agg(matches=("box", "size"), box=("box", "sum")).reset_index()


def _window_sum(c: pd.DataFrame, months: list) -> dict:
    s = c[c["month"].isin(months)]
    return {k: int(s[k].sum()) for k in MEASURES}


def monthly(c: pd.DataFrame, as_of: pd.Timestamp, start: pd.Period, ratio: float = RATIO,
            min_prior: int = MIN_PRIOR, years: tuple = BASELINE_YEARS) -> pd.DataFrame:
    """The three-month ratio per tour, level and month from `start` to the last month whose window ended LAG_DAYS
    before as_of: counts (judged for STEADY, ALL and LOWER only) and the box-score share (judged everywhere but TEAM
    and FIN). The baseline is the larger of the same months 1 and 2 years earlier (`years`), so that a level lost for
    over a year still shows; years=(1,) is the unpriced-leads gate's own measure."""
    last_end = (as_of - pd.Timedelta(days=LAG_DAYS)).to_period("M") - 1   # m + 1 must be a finished month
    rows = []
    for (tour, level), g in c.groupby(["tour", "level"], observed=True):
        judged = level in STEADY or level in ("ALL", "LOWER")
        judged_share = level not in UNJUDGED
        mo = start
        while mo + 1 <= last_end:
            now = [mo - 1, mo, mo + 1]
            cur = _window_sum(g, now)
            base = [_window_sum(g, [p - 12 * y for p in now]) for y in years]
            # each measure against its own larger baseline (ITF had box scores only from 2025: the year with more
            # matches, 2024, would be a baseline of zero box scores); the share against the larger judged share
            prev = {k: max(b[k] for b in base) for k in MEASURES}
            shares = [b["box"] / b["matches"] for b in base if b["matches"] >= min_prior]
            prev_share = max(shares) if shares else np.nan
            for k in MEASURES:
                r = cur[k] / prev[k] if prev[k] else np.nan
                rows.append({"tour": tour, "level": level, "month": str(mo), "measure": k, "now": cur[k],
                             "year_before": prev[k], "ratio": r,
                             "flag": bool(judged and prev[k] >= min_prior and np.isfinite(r) and r < ratio)})
            sn = cur["box"] / cur["matches"] if cur["matches"] else np.nan
            sb = prev_share
            r = sn / sb if np.isfinite(sn) and np.isfinite(sb) and sb > 0 else np.nan
            rows.append({"tour": tour, "level": level, "month": str(mo), "measure": "box_share",
                         "now": round(sn, 4) if np.isfinite(sn) else np.nan,
                         "year_before": round(sb, 4) if np.isfinite(sb) else np.nan, "ratio": r,
                         "flag": bool(judged_share and cur["matches"] >= min_prior and np.isfinite(r) and r < ratio)})
            mo += 1
    return pd.DataFrame(rows)


def recent(m: pd.DataFrame, as_of: pd.Timestamp, days: int = RECENT_DAYS, ratio: float = RATIO,
           min_prior: int = MIN_PRIOR, years: tuple = BASELINE_YEARS) -> pd.DataFrame:
    """The last `days` days ending LAG_DAYS before as_of against the same days 52 (and 104) weeks earlier, the larger
    of the two, steady levels only."""
    end = (as_of - pd.Timedelta(days=LAG_DAYS)).normalize()
    start = end - pd.Timedelta(days=days)
    d = m["tournament_date"]
    rows = []
    for tour in sorted(m["tour"].astype(str).unique()):
        for level in STEADY + ("LOWER",):
            sel_l = (m["tour"].astype(str) == tour) & (m["map_level"].isin(LOWER) if level == "LOWER"
                                                        else m["map_level"].astype(str) == level)
            cur = sel_l & (d > start) & (d <= end)
            newest = d[sel_l].max()
            for k in MEASURES:
                hb = m["has_box"].astype(bool) if k == "box" else pd.Series(True, index=m.index)
                a = int((cur & hb).sum())
                b = max(int((sel_l & hb & (d > start - pd.Timedelta(days=364 * y))
                             & (d <= end - pd.Timedelta(days=364 * y))).sum()) for y in years)
                r = a / b if b else np.nan
                rows.append({"tour": tour, "level": level, "window": f"{start.date() + pd.Timedelta(days=1)}..{end.date()}",
                             "measure": k, "now": a, "year_before": b, "ratio": r,
                             "newest_tournament_date": None if pd.isna(newest) else str(newest.date()),
                             "flag": bool(b >= min_prior and np.isfinite(r) and r < ratio)})
    return pd.DataFrame(rows)


def run(stage0: Path = STAGE0, with_accepted: bool = False, as_of: pd.Timestamp | None = None,
        start: str | None = None, out: Path | None = None, accepted: Path | None = None) -> dict:
    m, rec = load(stage0, with_accepted, accepted)
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.now().normalize()
    start_p = pd.Period(start, "M") if start else (as_of.to_period("M") - 12)
    c = cells(m)
    mon = monthly(c, as_of, start_p)
    rec_ = recent(m, as_of)
    flags = pd.concat([mon[mon["flag"]].assign(kind="monthly"), rec_[rec_["flag"]].assign(kind="recent")],
                      ignore_index=True)
    judged = sorted(mon["month"].unique())[-ALARM_MONTHS:] if len(mon) else []
    alarm = flags[flags["kind"].eq("recent") | flags["month"].isin(judged)] if len(flags) else flags
    ack = alarm.apply(lambda r: known(r["tour"], r["level"], r["measure"], as_of,
                                      r["month"] if r["kind"] == "monthly" else None), axis=1) if len(alarm) else []
    acknowledged = alarm[pd.Series(ack, index=alarm.index).notna()] if len(alarm) else alarm
    alarm = alarm[pd.Series(ack, index=alarm.index).isna()] if len(alarm) else alarm
    summary = {**rec, "as_of": str(as_of.date()), "ratio": RATIO, "min_prior": MIN_PRIOR, "recent_days": RECENT_DAYS,
               "lag_days": LAG_DAYS, "matches": int(len(m)), "newest_tournament_date": str(m["tournament_date"].max().date()),
               "flags": int(len(flags)), "alarm_months": judged, "alarm": int(len(alarm)),
               "alarm_cells": sorted({f"{r['tour']} {r['level']} {r['measure']} ({r['kind']} "
                                      f"{r['month'] if r['kind'] == 'monthly' else r['window']}: "
                                      f"{r['now']} against {r['year_before']})" for r in alarm.to_dict("records")}),
               # stable keys for the scheduler's memory: a recent cell keeps its key while it lasts, a monthly one is
               # new each month
               "alarm_cell_keys": sorted({f"{r['tour']} {r['level']} {r['measure']} "
                                          f"{r['month'] if r['kind'] == 'monthly' else 'recent'}"
                                          for r in alarm.to_dict("records")}),
               "acknowledged": sorted({f"{r['tour']} {r['level']} {r['measure']} "
                                       f"{r['month'] if r['kind'] == 'monthly' else 'recent'}: "
                                       f"{known(r['tour'], r['level'], r['measure'], as_of, r['month'] if r['kind'] == 'monthly' else None)}"
                                       for r in acknowledged.to_dict("records")}),
               "flagged_cells": sorted({f"{r['tour']} {r['level']} {r['measure']} ({r['kind']} "
                                        f"{r['month'] if r['kind'] == 'monthly' else r['window']})"
                                        for r in flags.to_dict("records")})[:400],
               "recent": rec_.to_dict("records")}
    if out is not None:
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        c.assign(month=c["month"].astype(str)).to_csv(out / "cells.csv", index=False)
        flags.to_csv(out / "flags.csv", index=False)
        mon.to_csv(out / "monthly.csv", index=False)
        (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    summary["_monthly"], summary["_recent"], summary["_flags"] = mon, rec_, flags
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0", default=str(STAGE0), help="a Stage 0 folder or its stage0_matches.parquet")
    ap.add_argument("--with-accepted", action="store_true", help="merge the accepted lower-level packages first")
    ap.add_argument("--as-of", default=None, help="the day the check stands on (default today)")
    ap.add_argument("--from", dest="start", default=None, help="first month judged (default 12 months before as-of)")
    ap.add_argument("--label", default="latest", help="the output folder's name under --out")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    s = run(Path(a.stage0), a.with_accepted, pd.Timestamp(a.as_of) if a.as_of else None, a.start,
            Path(a.out) / a.label)
    pd.set_option("display.width", 220)
    r = s["_recent"]
    print(f"as of {s['as_of']}: {s['matches']:,} matches, newest tournament {s['newest_tournament_date']}; "
          f"{s['flags']} flags, {s['alarm']} raising the alarm (recent, or in {', '.join(s['alarm_months'])})")
    print(r[r["measure"] == "matches"][["tour", "level", "window", "now", "year_before", "ratio",
                                        "newest_tournament_date", "flag"]].to_string(index=False))
    if s["alarm"]:
        print("ALARM:", "; ".join(s["alarm_cells"][:60]))
    return 3 if s["alarm"] else 0


if __name__ == "__main__":
    sys.exit(main())
