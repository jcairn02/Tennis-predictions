"""Flashscore's point records of the P6 matches SofaScore lacks (docs/studies/p6_data_issues/): mostly ATP qualifying
of 2018-2020 and Challengers of 2020-2023, by the match ids of the Flashscore copy on disk.

SofaScore has no point record for 20,619 of work package P6's targets. The Flashscore copy on disk (the Hugging Face
handoff) holds a record listing Flashscore's point-by-point tab ("MH") for 3,480 of them
(src/eda/p6_data_issues/flashscore_coverage.py; data/studies/p6_data_issues/flashscore/targets.csv.gz), and
Flashscore's live feed serves that tab as a complete record (work package P13's research,
docs/research/gap-sources/itf_2025_points.md). This asks for those feeds with work package P13's client and parser
(flashscore_points.py), into its raw folder and receipts, so nothing is fetched twice; flashscore_points --stage-only
stages every feed on disk, these included.

One collector per host: it refuses to start while flashscore_points' receipts have been written in the last
BUSY_MINUTES minutes (P13 running). Pace and stops are P13's: 2 s plus up to 1 s, a --max-requests budget, a stop on a
block. Collected under the owner's decision of 8 Oct 2026 (docs/decisions/2026-10-08-scraping-approved.md).

Writes data/studies/p6_data_issues/flashscore/: fetch_matches.csv.gz (one row per target: its feed's status and shape,
the verdict against Flashscore's own set score, and ``link_refused``), fetch_summary.json and runs.jsonl. Also stages
the copy's record of each feed (date, players, set score, duration; its grade is Flashscore's category) as
data/dump/points/flashscore_points/handoff_p6.parquet, which flashscore_points' staging reads beside its ITF extract.

**Refused links.** The targets were linked by shared name words (flashscore_coverage.py), first names included, so a
link can be borrowed. The link check (src/eda/gap_downloads/verify_flashscore.py --p6) lists the links failing both
of P6's tests, the surnames and the official result, in link_vetoes.csv; a target listed there is marked
``link_refused``, and the data map does not place its record there.

Usage:
    ./python.sh -m src.ingest.point_sources.flashscore_p6 --trial 100 --max-requests 150   # a seeded trial
    ./python.sh -m src.ingest.point_sources.flashscore_p6 --max-requests 4000              # the run (resumes)
    ./python.sh -m src.ingest.point_sources.flashscore_p6 --stage-only                     # no HTTP: the evidence
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import flashscore_points as F

OUT = P.PROJECT_ROOT / "data" / "studies" / "p6_data_issues" / "flashscore"
TARGETS = OUT / "targets.csv.gz"
VETOES = OUT / "link_vetoes.csv"
INFO = "handoff_p6.parquet"
BUSY_MINUTES = 10
RESULT_COLUMNS = ["feed_status", "fb_sets", "fb_games", "fb_points", "fb_score", "fb_verdict"]


def host_busy(now: float | None = None) -> str | None:
    """Why not to start: flashscore_points' receipts written in the last BUSY_MINUTES minutes; else None."""
    path = P.raw_path(F.SOURCE, "_receipts.jsonl")
    if not path.exists():
        return None
    idle = (now or time.time()) - path.stat().st_mtime
    if idle < BUSY_MINUTES * 60:
        return (f"Flashscore's host is in use: {P.rel(path)} was written {idle / 60:.0f} min ago (work package P13); "
                f"one collector per host, so try again once it has been idle for {BUSY_MINUTES} min")
    return None


def load_targets(trial: int | None = None, seed: int = 13) -> pd.DataFrame:
    """The targets whose Flashscore record lists the point-by-point tab; with ``trial``, about that many spread over the
    gaps and years (seeded)."""
    t = pd.read_csv(TARGETS, low_memory=False)
    t = t[t["fs_mh"].astype(str).eq("True")].copy()
    if trial:
        rng, cells = random.Random(seed), list(t.groupby(["gap", "year"]))
        per = max(1, trial // len(cells))
        picks = []
        for _, g in cells:
            picks += rng.sample(sorted(g.index), min(per, len(g)))
        t = t.loc[sorted(picks)]
    return t.sort_values("fs_date", ascending=False, kind="stable")


def info_rows(t: pd.DataFrame) -> list[list]:
    """The copy's record of each feed of ``t`` in flashscore_points.HANDOFF_COLUMNS (dates as YYYYMMDD; the grade is
    Flashscore's category), one per feed."""
    rows = []
    for r in t.drop_duplicates("fs_id").itertuples(index=False):
        rec = {"fs_id": r.fs_id, "fs_date": str(r.fs_date).replace("-", ""), "tour": r.tour, "grade": r.fs_category,
               "fs_tournament": r.fs_tournament, "fs_home": r.fs_home, "fs_away": r.fs_away, "fs_score": r.fs_score,
               "fs_duration": r.fs_duration, "handoff_file": "flashscore_full (flashscore_coverage.py's index)"}
        rows.append([None if pd.isna(rec.get(c)) else P.s(rec.get(c)) for c in F.HANDOFF_COLUMNS])
    return rows


def stage_info(t: pd.DataFrame) -> dict:
    return P.stage_table(F.SOURCE, P.dump_path(F.SOURCE, INFO), F.HANDOFF_COLUMNS, info_rows(t),
                         source_file=P.rel(TARGETS), retrieved_at=None)


def load_vetoes() -> set[tuple[str, str]]:
    """(uid, fs_id) of the links the link check refused (link_vetoes.csv); none before it has run."""
    if not VETOES.exists():
        return set()
    v = pd.read_csv(VETOES, dtype=str, keep_default_na=False)
    return set(zip(v["uid"], v["fs_id"]))


def refused(t: pd.DataFrame, vetoes: set) -> pd.Series:
    return pd.Series([(str(u), str(f)) in vetoes for u, f in zip(t["uid"], t["fs_id"])], index=t.index)


def results(receipts, t: pd.DataFrame) -> pd.DataFrame:
    out = []
    for r in t.itertuples(index=False):
        row = {"feed_status": F.feed_status(receipts, r.fs_id)}
        text = F.read_feed(receipts, r.fs_id)
        if text is not None:
            parsed = F.parse_feed(text)
            row.update(fb_sets=parsed["n_sets"], fb_games=parsed["n_games"], fb_points=parsed["n_points"],
                       fb_score=parsed["score"], fb_verdict=F.verdict(parsed, r.fs_score))
        out.append(row)
    return pd.DataFrame(out, columns=RESULT_COLUMNS, index=t.index)


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    t = load_targets(args.trial, args.seed)
    ids = list(dict.fromkeys(t["fs_id"]))
    P.log(f"[flashscore_p6] {len(t):,} targets with Flashscore's point tab; {len(ids):,} feeds")
    receipts = P.receipts_for(F.SOURCE)
    summary = {"source": "flashscore_p6", "started_at": P.utc_now_iso(), "args": vars(args), "targets": int(len(t))}
    outcomes = Counter()
    if not args.stage_only:
        busy = host_busy()
        if busy:
            raise SystemExit(busy)
        client = F.make_client(args)
        try:
            outcomes = F.fetch_feeds(client, receipts, ids)
        except (P.Blocked, P.BudgetExhausted) as stop:
            summary["stopped"] = f"{type(stop).__name__}: {stop}"
            P.log(f"[flashscore_p6] STOPPED: {stop}")
        summary["client"] = client.stats()
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    summary["info_staged"] = stage_info(load_targets())["rows"]
    t = pd.concat([t, results(receipts, t)], axis=1)
    t["link_refused"] = refused(t, load_vetoes())
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / "fetch_matches.csv.gz", index=False, compression="gzip")
    summary["verdicts"] = {str(k): int(v) for k, v in t["fb_verdict"].value_counts(dropna=False).items()}
    summary["link_refused"] = int(t["link_refused"].sum())
    summary["by_gap"] = {g: {"targets": int(len(x)), "complete": int(x["fb_verdict"].eq("complete").sum()),
                             "absent": int(x["feed_status"].astype(str).eq("absent").sum()),
                             "link_refused": int(x["link_refused"].sum())} for g, x in t.groupby("gap")}
    summary["matches_selected"] = int(t["feed_status"].astype(str).eq("200").sum())
    summary["finished_at"], summary["seconds"] = P.utc_now_iso(), round(time.time() - started, 1)
    P.write_summary("fetch_summary.json", summary, root=OUT)
    P.log(f"[flashscore_p6] verdicts {summary['verdicts']}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--trial", type=int, help="only about N targets, spread over the gaps and years")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--max-requests", type=int, default=4000)
    parser.add_argument("--min-interval", type=float, default=2.0)
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--fsign", default=F.FSIGN, help="the x-fsign header the site's pages send")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rewrite the evidence")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
