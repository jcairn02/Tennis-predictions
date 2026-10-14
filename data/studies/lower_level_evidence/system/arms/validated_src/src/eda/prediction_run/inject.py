"""Steps run inside the prediction run's sandbox, between the builders, for the live rows (live_rows.py).

The run's meta table (one row per live match: match_id, day, p_a, venue) says what Stage 0 cannot hold. Each step puts
it where the frame's played matches have it, so the unchanged builders treat a live match as they treat those:
    check   after stage0_build.py: every live match is in Stage 0 under the id expected, completed, an evaluation match,
            with no box score; nothing else of the sandbox's history was dropped but the replay's own rounds
    odds    after stage1_odds.py: the price. Stage 1 keeps a row for every main-draw match at the levels tennis-data
            covers; a live match's row takes the margin-free price as tennis-data's average (p_avg_a, the frame's
            odds input, with the decimal odds it implies). Its tennis-data fields stay empty, the date too: the day
            goes in by the link below, as srcc_tennis_data.py would make it, and that builder skips undated rows (it
            reads the venue off the tennis-data file a dated row names). A replayed match's own tennis-data row may
            have linked; the meta table's price replaces it either way
    remap   after odds: the frozen link files follow every match id Stage 0 changed, as rebuild_stage0.py does
    links   after match_timing/link_sources_c.py: the day. No source has dated a match not yet played, so every link
            file's rows for a live match go (a replay's played matches are still linked by their point logs and
            other sources); then the match takes a tennis-data day link built as srcc_tennis_data.py builds its
            links: a local day, tagged uk_day_venue_east / _west when the venue sits four or more hours from the UK
            clock. Appended to the file as it stands: no other row is rewritten
    pin     after match_timing/timing_check.py: the window. The timeline would give a match dated by tennis-data alone
            a window wider than the frame's matches had (two days before the day at European venues), because once
            played those are dated by several sources and, where a point log exists, exactly. So a live match takes
            its tour's current window around its day: the median, over the dated frame-level matches of the
            PIN_DAYS before it (a year when a tour has fewer than PIN_MIN), of the days between a match's earliest
            start and its day, and likewise of its latest finish. Current, because the dating changes with what is
            collected: ATP matches have been dated exactly since July 2026 (TDI's point logs; 113 of 116 in
            September), a day wide before (the median of 2025)
A meta row whose ``dating`` is "training" keeps its played links and its window (replay.py's check of the code path
alone); every other row is dated as live.
Run (inside the sandbox): python src/eda/prediction_run/inject.py --meta <live_meta.parquet>
                          --step check|odds|remap|links|pin
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import common as P  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

ODDS = C.OUT / "stage1_odds.parquet"
BEFORE = ROOT / "run" / "stage0_before"            # the sandbox's Stage 0 as copied, kept by run.py before the build
TD_TEXT = ["td_file", "td_tournament", "td_round", "td_comment", "td_winner", "td_loser"]
TD_NUM = ["ps_a", "ps_b", "max_a", "max_b", "b365_a", "b365_b", "overround_ps", "p_ps_a"]


def in_sandbox() -> None:
    if not (ROOT / P.MARKER).exists():
        raise SystemExit(f"{ROOT} is not a prediction run's sandbox: inject.py runs only there")


def check(meta: pd.DataFrame) -> dict:
    m = pd.read_parquet(C.MATCHES, columns=["match_id", "status", "evaluation", "has_box", "level", "qualifying"])
    m["match_id"] = m["match_id"].astype(str)
    got = m[m["match_id"].isin(set(meta["match_id"]))]
    missing = sorted(set(meta["match_id"]) - set(got["match_id"]))
    bad = got[~(got["status"].eq("completed") & got["evaluation"] & ~got["has_box"].astype(bool))]
    out = {"live_matches": int(len(meta)), "in_stage0": int(len(got)), "missing": missing[:20],
           "not_as_expected": bad["match_id"].head(20).tolist()}
    s = json.loads((C.OUT / "stage0_summary.json").read_text(encoding="utf-8")).get("live_rows", {})
    out["stage0_live_rows"] = s
    if missing or len(bad):
        raise SystemExit(f"check: live matches missing from Stage 0 or not built as expected: {out}")
    return out


def odds(meta: pd.DataFrame) -> dict:
    o = pd.read_parquet(ODDS)
    o["match_id"] = o["match_id"].astype(str)
    pos = pd.Series(np.arange(len(o)), index=o["match_id"])
    missing = sorted(set(meta["match_id"]) - set(pos.index))
    if missing:
        raise SystemExit(f"odds: {len(missing)} live matches have no Stage 1 row (not a main-draw match at a level "
                         f"tennis-data covers): {missing[:5]}")
    idx = pos.reindex(meta["match_id"]).to_numpy()
    p = meta["p_a"].astype(float).to_numpy()
    if not ((p > 0) & (p < 1)).all():
        raise SystemExit("odds: every live match needs a price strictly between 0 and 1 (p_a)")
    rows = o.index[idx]
    o.loc[rows, "link"] = "live"
    o.loc[rows, "td_date"] = pd.NaT                  # the day goes in by the day link (links())
    o.loc[rows, "td_redated"] = False
    o.loc[rows, "days_from_monday"] = np.nan
    for c in TD_TEXT:
        o.loc[rows, c] = pd.NA
    o.loc[rows, "td_row"] = pd.NA
    o.loc[rows, ["same_set_scores", "rank_agrees_a", "rank_agrees_b"]] = pd.NA
    o.loc[rows, "round_agrees"] = "yes"
    o.loc[rows, "avg_a"], o.loc[rows, "avg_b"] = 1 / p, 1 / (1 - p)
    o.loc[rows, "overround_avg"], o.loc[rows, "avg_coherent"], o.loc[rows, "p_avg_a"] = 1.0, True, p
    o.loc[rows, TD_NUM] = np.nan
    o.loc[rows, "ps_coherent"] = False
    part = ODDS.with_name(ODDS.name + ".part")
    o.to_parquet(part, index=False)
    os.replace(part, ODDS)
    return {"priced": int(len(rows))}


def remap() -> dict:
    """The frozen link files follow every match id the sandbox's Stage 0 build changed (rebuild_stage0.py's remap)."""
    from src.eda.data_continuity import rebuild_stage0 as R

    if not (BEFORE / "stage0_matches.parquet").exists():
        raise SystemExit(f"remap: {BEFORE} holds no Stage 0 copy")
    old = set(pd.read_parquet(BEFORE / "stage0_matches.parquet", columns=["match_id"])["match_id"].astype(str))
    new = set(pd.read_parquet(C.MATCHES, columns=["match_id"])["match_id"].astype(str))
    if not (old - new) or not (new - old):           # nothing can have been renamed (id_map needs both sides)
        pd.DataFrame(columns=["old_match_id", "new_match_id"]).to_csv(ROOT / "run" / "id_map.csv", index=False)
        return {"changed": 0, "left_without_partner": len(old - new), "rows": {}}
    pairs, unpaired = R.id_map(BEFORE, C.OUT)
    pairs.to_csv(ROOT / "run" / "id_map.csv", index=False)
    return {"changed": int(len(pairs)), "left_without_partner": int(len(unpaired)), "rows": R.remap_frozen(pairs)}


def live_dated(meta: pd.DataFrame) -> pd.DataFrame:
    """The meta rows dated as live (all but a replay's "training" rows)."""
    dating = meta["dating"].fillna("live") if "dating" in meta.columns else pd.Series("live", index=meta.index)
    return meta[dating.ne("training")]


def links(meta: pd.DataFrame) -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    from src.eda.match_timing import srcc_common as K
    from src.eda.match_timing import srcc_tennis_data as TD
    from src.eda.match_timing import srcc_tz as TZ
    from src.eda.match_timing import timing as TM

    removed = {}
    for src in TM.SOURCE_RANK:                    # the files the timeline reads
        path = K.LINKS / f"{src}.parquet"
        if not path.exists():
            continue
        table = pq.read_table(path)
        if "match_id" not in table.column_names:
            continue
        ids = meta["match_id"] if src == TD.SOURCE else live_dated(meta)["match_id"]
        gone = pc.is_in(table["match_id"], value_set=pa.array(sorted(set(ids)), table.schema.field("match_id").type))
        n = int(pc.sum(pc.cast(gone, pa.int64())).as_py() or 0)
        if n:
            pq.write_table(table.filter(pc.invert(gone)), path)
            removed[src] = n
    day = pd.to_datetime(meta["day"]).dt.normalize()
    noon = (day + pd.Timedelta(hours=12)).dt.tz_localize("UTC")
    lon = TZ.zoneinfo("Europe/London")
    tags, zones = [], []
    for t, city in zip(noon, meta["venue"]):
        zone = TD.venue_zone(city)
        zones.append(zone)
        if not isinstance(zone, str):
            tags.append("")
            continue
        rel = (t.tz_convert(TZ.zoneinfo(zone)).utcoffset() - t.tz_convert(lon).utcoffset()).total_seconds() / 3600
        tags.append(";uk_day_venue_west" if rel <= -TD.FAR else ";uk_day_venue_east" if rel >= TD.FAR else "")
    live = pd.DataFrame({"match_id": meta["match_id"].astype(str), "source_key": "live#" + meta["match_id"].astype(str),
                         "date_local": day.to_numpy(), "start_utc": pd.NaT, "date_basis": "local",
                         "link_method": ["stage1_live" + t for t in tags], "score_agrees": pd.NA,
                         "round_agrees": True})
    # write_links flags a day outside the match's plausible window; written alone, so no other row is flagged again
    tmp = K.write_links(live, "_prediction_run_live")
    rows = pq.read_table(tmp)
    tmp.unlink()
    rows = rows.set_column(rows.schema.get_field_index("source"), "source",
                           pa.array([TD.SOURCE] * rows.num_rows, pa.string()))
    path = K.LINKS / f"{TD.SOURCE}.parquet"
    current = pq.read_table(path)
    pq.write_table(pa.concat_tables([current, rows.cast(current.schema)]), path)
    return {"links": int(len(live)), "removed_by_source": removed,
            "venues_without_zone": sorted({str(c) for c, z in zip(meta["venue"], zones) if not isinstance(z, str)}),
            "tags": pd.Series(tags).replace("", "none").value_counts().to_dict()}


FRAME_LEVELS = ("GS", "FIN", "T1000", "T500", "T250")
PIN_DAYS, PIN_MIN, PIN_FALLBACK = 60, 100, 365


def pin(meta: pd.DataFrame) -> dict:
    """Each live match's window: its day, widened as its tour's dated frame-level matches of late were."""
    from src.eda.match_timing import common as MTC

    live = live_dated(meta)
    if live.empty:
        return {"pinned": 0}
    path = MTC.OUT / "timing.parquet"
    t = pd.read_parquet(path)
    t["match_id"] = t["match_id"].astype(str)
    m = pd.read_parquet(C.MATCHES, columns=["match_id", "level", "qualifying", "tournament_date"])
    m["match_id"] = m["match_id"].astype(str)
    first = pd.to_datetime(live["day"]).min()
    dated = t.loc[t["exact"].astype(bool), ["match_id", "tour", "es", "lf", "obs"]].merge(
        m[m["level"].isin(FRAME_LEVELS) & ~m["qualifying"].astype(bool) & ~m["match_id"].isin(set(meta["match_id"]))],
        on="match_id")
    before, after, used = {}, {}, {}
    for tour, g in dated.groupby("tour"):
        for span in (PIN_DAYS, PIN_FALLBACK):
            r = g[g["tournament_date"].between(first - pd.Timedelta(days=span), first - pd.Timedelta(days=1))]
            if len(r) >= PIN_MIN or span == PIN_FALLBACK:
                break
        before[tour], after[tour] = (r["obs"] - r["es"]).median(), (r["lf"] - r["obs"]).median()
        used[tour] = {"days": span, "matches": int(len(r))}
    before, after = pd.Series(before, dtype=float), pd.Series(after, dtype=float)
    pos = pd.Series(np.arange(len(t)), index=t["match_id"])
    missing = sorted(set(live["match_id"]) - set(pos.index))
    if missing:
        raise SystemExit(f"pin: live matches missing from the timeline: {missing[:5]}")
    idx = t.index[pos.reindex(live["match_id"]).to_numpy()]
    day = np.array([P.day_of(d) for d in live["day"]], dtype=float)
    b = live["tour"].map(before).to_numpy(dtype=float)
    a = live["tour"].map(after).to_numpy(dtype=float)
    if np.isnan(b).any() or np.isnan(a).any():
        raise SystemExit("pin: a live match's tour has no dated frame-level match in the past year")
    t.loc[idx, "obs"], t.loc[idx, "es"], t.loc[idx, "lf"] = day, day - b, day + a
    t.loc[idx, "width_days"] = a + b
    t.loc[idx, "exact"] = True
    for col, value in (("window_basis", "live_schedule"), ("best_source", "live"), ("sources", "live")):
        if col in t.columns:
            t.loc[idx, col] = value
    part = path.with_name(path.name + ".part")
    t.to_parquet(part, index=False)
    os.replace(part, path)
    return {"pinned": int(len(idx)), "days_before": {k: float(v) for k, v in before.items()},
            "days_after": {k: float(v) for k, v in after.items()}, "measured_on": used}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--step", required=True, choices=["check", "odds", "remap", "links", "pin"])
    a = ap.parse_args()
    in_sandbox()
    meta = pd.read_parquet(a.meta)
    meta["match_id"] = meta["match_id"].astype(str)
    out = {"check": lambda: check(meta), "odds": lambda: odds(meta), "remap": remap, "links": lambda: links(meta),
           "pin": lambda: pin(meta)}[a.step]()
    record = ROOT / "run" / "inject.json"
    done = json.loads(record.read_text(encoding="utf-8")) if record.exists() else {}
    done[a.step] = out
    P.write_json(record, done)
    print(json.dumps(out, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
