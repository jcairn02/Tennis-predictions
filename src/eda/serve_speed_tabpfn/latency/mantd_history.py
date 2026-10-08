"""Latency follow-up (data/studies/serve_speed_tabpfn/latency/plan.md), scenario B's tour-level rule: when does
ManTennisData publish a match's serve speeds? Reads no match result.

Evidence:
    evidence/commits_matches_2026.jsonl, commits_matches_2025.jsonl
        the repository's commits touching atp/matches_2026.csv and matches_2025.csv (read-only `gh api` listings,
        logged in evidence/requests.log)
    the 10 consecutive versions of atp/matches_2026.csv before the held head (26 Jul - 27 Sep 2026), fetched read-only
        from raw.githubusercontent.com (2 s apart) into data/raw/serve_speed_tabpfn_latency/mantennisdata/, receipts in
        evidence/version_receipts.jsonl; the held head (4 Oct 2026, commit 4e2d39f) from data/raw/public_dump/
        mantennisdata/atp/matches_2026.csv (read only)
Method: a match is published with speed in version k when both players' "average first serves" are plausible (40-270
km/h). For each match first published in commit k (the 10 diffs between consecutive versions), the day of the commit
(UTC) is compared with the match's own clock days from timing.parquet (es, lf, obs), through the acquisition's
ManTennisData -> Stage 0 links (speeds.parquet: source_key = ManTennisData match id).

Run: ./python.sh src/eda/serve_speed_tabpfn/latency/mantd_history.py [--fetch]
Writes data/studies/serve_speed_tabpfn/latency/evidence/: version_receipts.jsonl (with --fetch), mantd_publication.json,
mantd_publication_matches.csv
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVID = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "latency" / "evidence"
RAW = ROOT / "data" / "raw" / "serve_speed_tabpfn_latency" / "mantennisdata"
HELD = ROOT / "data" / "raw" / "public_dump" / "mantennisdata" / "atp" / "matches_2026.csv"
HELD_SHA = "4e2d39f99e40b39bb98c3d2b7eb315ab0a510ea4"
TOURNAMENTS = ROOT / "data" / "raw" / "public_dump" / "mantennisdata" / "atp" / "tournaments.csv"
SPEEDS = ROOT / "data" / "studies" / "serve_speed_acquisition" / "speeds.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
RAW_URL = "https://raw.githubusercontent.com/msolonskyi/ManTennisData/{sha}/atp/matches_2026.csv"
N_VERSIONS = 10
COLS = ["id", "tournament_id", "stadie_id", "win_average_first_serves_kmh", "los_average_first_serves_kmh"]


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def commits(year: int) -> pd.DataFrame:
    c = pd.read_json(EVID / f"commits_matches_{year}.jsonl", lines=True)
    c["t"] = pd.to_datetime(c["committer_date"], utc=True)
    c["day"] = c["t"].dt.tz_convert(None).dt.normalize()
    return c.sort_values("t").reset_index(drop=True)


def chosen_versions() -> pd.DataFrame:
    """The 10 commits of matches_2026.csv before the held head, oldest first, plus the head."""
    c = commits(2026)
    i = int(np.flatnonzero(c["sha"].eq(HELD_SHA))[0])
    return c.iloc[i - N_VERSIONS:i + 1].reset_index(drop=True)


def fetch(versions: pd.DataFrame) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    log = EVID / "requests.log"
    rec = EVID / "version_receipts.jsonl"
    for r in versions.itertuples():
        if r.sha == HELD_SHA:
            continue
        dest = RAW / f"matches_2026_{r.day:%Y%m%d}_{r.sha[:7]}.csv"
        if dest.exists():
            continue
        url = RAW_URL.format(sha=r.sha)
        t0 = pd.Timestamp.now(tz="UTC")
        req = urllib.request.Request(url, headers={"User-Agent": "tennis-predictions research (read-only)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, data = resp.status, resp.read()
        dest.write_bytes(data)
        line = {"retrieved_at": t0.isoformat(timespec="seconds"), "url": url, "commit": r.sha,
                "commit_time": r.t.isoformat(), "status": status, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(), "git_blob_sha1": blob_sha1(data), "dest": str(dest.relative_to(ROOT))}
        with rec.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{t0:%Y-%m-%dT%H:%M:%SZ} GET {url} -> {status}, {len(data)} bytes\n")
        time.sleep(2.0 + np.random.default_rng().uniform(0, 1))


def load_version(path: Path) -> pd.DataFrame:
    m = pd.read_csv(path, dtype=str, usecols=COLS, keep_default_na=False)
    for c in ("win_average_first_serves_kmh", "los_average_first_serves_kmh"):
        v = pd.to_numeric(m[c], errors="coerce")
        m[c] = v.where((v > 40) & (v <= 270))
    m["timed"] = m["win_average_first_serves_kmh"].notna() & m["los_average_first_serves_kmh"].notna()
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="fetch the 10 earlier versions (read-only, logged)")
    args = ap.parse_args()
    v = chosen_versions()
    if args.fetch:
        fetch(v)
    # verify the held head against its receipt's blob hash
    held_blob = blob_sha1(HELD.read_bytes())
    paths = {}
    for r in v.itertuples():
        paths[r.sha] = HELD if r.sha == HELD_SHA else RAW / f"matches_2026_{r.day:%Y%m%d}_{r.sha[:7]}.csv"
    tabs = {sha: load_version(p) for sha, p in paths.items()}
    # links to Stage 0 and the clock
    sp = pd.read_parquet(SPEEDS, columns=["source", "source_key", "match_id"])
    sp = sp[sp["source"].eq("mantennisdata") & sp["match_id"].notna()].drop_duplicates("source_key")
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs", "exact", "tournament_date"])
    tn = pd.read_csv(TOURNAMENTS, dtype=str)
    tcols = [c for c in ("id", "name", "series_id", "start_dtm", "finish_dtm") if c in tn.columns]
    tn = tn[tcols].rename(columns={"id": "tournament_id"})
    rows = []
    shas = list(v["sha"])
    for k in range(1, len(shas)):
        prev, cur = tabs[shas[k - 1]], tabs[shas[k]]
        new_timed = set(cur.loc[cur["timed"], "id"]) - set(prev.loc[prev["timed"], "id"])
        new_rows = set(cur["id"]) - set(prev["id"])
        late_speed = new_timed - new_rows                         # rows held earlier, speed added now
        d = cur[cur["id"].isin(new_timed)][["id", "tournament_id", "stadie_id"]].copy()
        d["commit"] = shas[k]
        d["commit_time"] = v.loc[k, "t"]
        d["commit_day"] = v.loc[k, "day"]
        d["row_was_held_without_speed"] = d["id"].isin(late_speed)
        rows.append(d)
    new = pd.concat(rows, ignore_index=True)
    new = new.merge(sp.rename(columns={"source_key": "id"}), on="id", how="left")
    new = new.merge(tm, on="match_id", how="left").merge(tn, on="tournament_id", how="left")
    cday = new["commit_day"].to_numpy().astype("datetime64[D]").astype("int64")
    new["commit_dayn"] = cday
    new["lag_obs"] = cday - new["obs"]
    new["lag_lf"] = cday - new["lf"]
    new["obs_weekday"] = pd.to_datetime(new["obs"], unit="D").dt.day_name()
    new["same_sunday"] = new["obs"].eq(cday)
    if "finish_dtm" in new:
        fin = pd.to_datetime(new["finish_dtm"], format="%Y%m%d", errors="coerce")
        new["event_finished_by_commit"] = fin.dt.normalize() < new["commit_day"]
    # was each linked match published at the first commit after it surely finished?
    cd = np.sort(v["day"].to_numpy().astype("datetime64[D]").astype("int64"))
    first_after_lf = np.array([cd[np.searchsorted(cd, x, side="right")] if np.isfinite(x) and
                               np.searchsorted(cd, x, side="right") < len(cd) else np.nan for x in new["lf"]])
    new["first_commit_after_lf"] = first_after_lf
    new["published_at_first_commit_after_lf"] = new["commit_dayn"].eq(new["first_commit_after_lf"])
    lk = new[new["obs"].notna()]
    # matches played ON a commit Sunday, inside the window: included in that Sunday's commit?
    window = (lk["obs"] > cd[0]) & (lk["obs"] <= cd[-1])
    on_sunday = lk[window & lk["obs"].isin(cd)]
    res = {
        "reads_results": False,
        "versions": [{"commit": r.sha, "time": r.t.isoformat(), "rows": int(len(tabs[r.sha])),
                      "timed": int(tabs[r.sha]["timed"].sum())} for r in v.itertuples()],
        "held_head_blob_sha1": held_blob,
        "new_timed_by_commit": new.groupby("commit_day").size().astype(int).rename(lambda x: f"{x:%Y-%m-%d}").to_dict(),
        "new_timed_total": int(len(new)),
        "linked_with_clock": int(lk.shape[0]),
        "row_was_held_without_speed": int(new["row_was_held_without_speed"].sum()),
        "lag_days_commit_minus_obs": {str(k): int(n) for k, n in lk["lag_obs"].value_counts().sort_index().items()},
        "lag_days_commit_minus_lf_quantiles": lk["lag_lf"].quantile([0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]).to_dict(),
        "published_at_first_commit_after_lf_share": round(float(lk["published_at_first_commit_after_lf"].mean()), 4),
        "published_later_than_first_commit_after_lf": int((~lk["published_at_first_commit_after_lf"]).sum()),
        "matches_played_on_a_commit_sunday": int(len(on_sunday)),
        "of_those_in_that_sundays_commit": int((on_sunday["commit_dayn"] == on_sunday["obs"]).sum()),
        "obs_weekday_by_lag": lk.groupby(["obs_weekday", "lag_obs"]).size().reset_index(name="n")
        .to_dict(orient="records"),
    }
    if "event_finished_by_commit" in new:
        res["published_while_event_in_progress"] = int((~new["event_finished_by_commit"].fillna(True)).sum())
    # candidate release rules: S = the first commit Sunday on or after lf + g (g = 1: the plan's fallback, the first
    # Sunday after lf; g = 2, 3: stricter); the match is usable from S + 1. Scored against the observed commit.
    rules = {}
    for g in (1, 2, 3):
        idx = np.searchsorted(cd, lk["lf"].to_numpy() + g, side="left")
        ok = idx < len(cd)
        pred = np.where(ok, cd[np.minimum(idx, len(cd) - 1)], np.nan)
        act = lk["commit_dayn"].to_numpy()
        m = ok & np.isfinite(pred)
        rules[f"first_sunday_on_or_after_lf_plus_{g}"] = {
            "matches": int(m.sum()), "exact": round(float((pred[m] == act[m]).mean()), 4),
            "rule_too_early_by_a_week_or_more": round(float((pred[m] < act[m]).mean()), 4),
            "rule_too_late": round(float((pred[m] > act[m]).mean()), 4)}
    res["release_rules_scored"] = rules
    # how wide the clock is for these matches
    res["lf_minus_obs_counts"] = {str(k): int(n) for k, n in (lk["lf"] - lk["obs"]).value_counts().sort_index().items()}
    late = lk[~lk["published_at_first_commit_after_lf"]]
    res["late_publications_by_event"] = (late.groupby(["name", "commit_day"]).size().reset_index(name="n")
                                         .astype({"commit_day": str}).to_dict(orient="records"))
    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / "mantd_publication.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    keep = ["id", "match_id", "tournament_id", "name", "series_id", "stadie_id", "commit_day", "obs", "lf", "es",
            "exact", "lag_obs", "lag_lf", "obs_weekday", "row_was_held_without_speed", "published_at_first_commit_after_lf"]
    new[[c for c in keep if c in new.columns]].to_csv(EVID / "mantd_publication_matches.csv", index=False)
    print(json.dumps({k: v_ for k, v_ in res.items() if k not in ("obs_weekday_by_lag",)}, indent=1, default=str))


if __name__ == "__main__":
    main()
