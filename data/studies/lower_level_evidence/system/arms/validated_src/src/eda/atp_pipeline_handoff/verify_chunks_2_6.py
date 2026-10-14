"""Checks on chunks 2-6 of the Hugging Face ATP pipeline dump, once downloaded.

* Flashscore (``flashscore_full``, ``flashscore_gql_stats``): records per file against the uploader's
  progress files, date range, categories, and how many records carry start times, statistics, and
  winners / unforced errors; distinct Flashscore match ids across all files, since the head-to-head
  passes re-fetch matches the year files already hold.
* Infosys: whether ``infosys_full`` holds the same matches as ``infosys_deep``, and how many carry
  embedded Court Vision.

Usage:
    ./python.sh src/eda/atp_pipeline_handoff/verify_chunks_2_6.py [--workers 6]

Writes data/studies/atp_pipeline_handoff/checks_chunks_2_6.json (tracked).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
OUT = ROOT / "data" / "studies" / "atp_pipeline_handoff" / "checks_chunks_2_6.json"


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open(encoding="utf-8", errors="replace")


def filled(value) -> bool:
    return value not in (None, "", [], {})


def name_class(name) -> str:
    """Rough tour class from a Flashscore tournament name; head-to-head records carry no category."""
    text = name or ""
    if re.match(r"^M\d{2,3}\b", text):
        return "ITF men (M15, M25 ...)"
    if re.match(r"^W\d{2,3}\b", text):
        return "ITF women (W15, W35 ...)"
    if re.match(r"^J\d{2,3}\b", text) or "junior" in text.lower():
        return "juniors"
    if re.search(r"Australian Open|French Open|Wimbledon|US Open", text):
        return "Grand Slam (either tour)"
    return "other named events (ATP, WTA, Challenger, WTA 125, team)"


def scan_flashscore(path_text: str) -> tuple[str, dict, list]:
    path = Path(path_text)
    c, categories, ids = Counter(), Counter(), []
    first = last = None
    with open_text(path) as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                c["unparseable"] += 1
                continue
            c["records"] += 1
            date = str(record.get("match_date") or "")
            if date:
                first = date if first is None or date < first else first
                last = date if last is None or date > last else last
            categories[record.get("category") or "(none)"] += 1
            c["with_start_time"] += filled(record.get("match_start_ts"))
            c["with_statistics"] += filled(record.get("home_aces"))
            c["with_winners_and_errors"] += filled(record.get("home_winners"))
            c["with_set_durations"] += filled(record.get("set_durations"))
            ids.append((record.get("match_id"), date[:4], name_class(record.get("tournament_name")),
                        filled(record.get("home_aces"))))
    return path_text, {**c, "first_date": first, "last_date": last, "categories": dict(categories.most_common())}, ids


def scan_infosys(path_text: str) -> tuple[str, dict, list]:
    path = Path(path_text)
    c, keys = Counter(), []
    with open_text(path) as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            c["records"] += 1
            c["with_court_vision"] += filled(record.get("court_vision"))
            keys.append(f"{record.get('year')}|{record.get('tournament_id')}|{record.get('match_id')}")
    return path_text, dict(c), keys


def claim_for(name: str) -> int | None:
    """The uploader's own count for a Flashscore file, from its progress file."""
    folder = RAW / "flashscore_full"
    stem = re.sub(r"\.jsonl(\.gz)?$", "", name)
    candidates = []
    if match := re.fullmatch(r"flashscore_full_(\d{4}_\d{4})_atp", stem):
        candidates = [(f"checkpoint_full_{match.group(1)}_atp.json", "total_matches")]
    elif match := re.fullmatch(r"flashscore_full_(\d{4}_\d{4})_challenger", stem):
        candidates = [(f"checkpoint_{match.group(1)}_challenger.json", "total_matches")]
    elif match := re.fullmatch(r"flashscore_full_h2h_(pass\d+_shard\d+)", stem):
        candidates = [(f"checkpoint_h2h_{match.group(1)}.json", "total_fetched")]
    for file_name, key in candidates:
        path = folder / file_name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8")).get(key)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    args = parser.parse_args()

    def finished(folder: str, pattern: str) -> list[str]:  # not *.part (in progress) or *.bad-* (failed hash)
        return sorted(str(p) for p in (RAW / folder).glob(pattern) if p.name.endswith((".jsonl", ".jsonl.gz")))

    flash = finished("flashscore_full", "*.jsonl*") + finished("flashscore_gql_stats", "*.jsonl*")
    infosys = finished("infosys_deep", "*_data.jsonl*") + finished("infosys_full", "*_data.jsonl*")
    files = {}
    groups: dict[str, dict] = {"year files": {}, "head-to-head passes": {}, "statistics files": {}}  # match id -> year
    recent: dict[str, tuple] = {}  # match id -> (year, tournament-name class, has statistics), 2025 onward
    infosys_keys = {"infosys_deep": set(), "infosys_full": set()}
    infosys_files = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        # the largest files first, so the slowest ones don't start last
        flash.sort(key=lambda p: -Path(p).stat().st_size)
        for path_text, stats, ids in pool.map(scan_flashscore, flash):
            path = Path(path_text)
            name = f"{path.parent.name}/{path.name}"
            stats["claimed"] = claim_for(path.name) if path.parent.name == "flashscore_full" else None
            files[name] = stats
            group = ("statistics files" if path.parent.name == "flashscore_gql_stats" else
                     "head-to-head passes" if "_h2h_" in path.name else "year files")
            for match_id, year, kind, has_stats in ids:
                if match_id:
                    groups[group].setdefault(match_id, year)
                    if year >= "2025":
                        recent[match_id] = (year, kind, has_stats or recent.get(match_id, ("", "", False))[2])
            print(f"{name}: {stats['records']:,} records (claimed {stats['claimed']}), "
                  f"{stats['first_date']}..{stats['last_date']}", flush=True)
        for path_text, stats, keys in pool.map(scan_infosys, infosys):
            path = Path(path_text)
            infosys_files[f"{path.parent.name}/{path.name}"] = stats
            infosys_keys[path.parent.name].update(keys)

    everything = {**groups["head-to-head passes"], **groups["statistics files"], **groups["year files"]}
    year_and_stats = groups["year files"].keys() | groups["statistics files"].keys()
    h2h_only = groups["head-to-head passes"].keys() - year_and_stats
    by_year: dict[str, Counter] = {}
    for match_id, year in everything.items():
        row = by_year.setdefault(year or "(no date)", Counter())
        row["all files"] += 1
        row["in year files"] += match_id in groups["year files"]
        row["only in head-to-head passes"] += match_id in h2h_only
    checks = {
        "generated_by": "src/eda/atp_pipeline_handoff/verify_chunks_2_6.py",
        "flashscore_files": dict(sorted(files.items())),
        "flashscore_distinct_match_ids": {
            **{group: len(ids) for group, ids in groups.items()},
            "all files": len(everything),
            "head-to-head only (not in year or statistics files)": len(h2h_only),
            "statistics files not in year files": len(groups["statistics files"].keys() - groups["year files"].keys()),
        },
        "flashscore_distinct_match_ids_by_year": {y: dict(c) for y, c in sorted(by_year.items())},
        "flashscore_2025_onward_by_name_class": {
            f"{year} {kind}": {"matches": n, "with_statistics": sum(1 for y, k, s in recent.values()
                                                                    if (y, k) == (year, kind) and s)}
            for (year, kind), n in sorted(Counter((y, k) for y, k, _ in recent.values()).items())},
        "flashscore_totals": {
            "records": sum(f["records"] for f in files.values()),
            "claimed_where_known": sum(f["claimed"] or 0 for f in files.values()),
            "records_in_files_with_a_claim": sum(f["records"] for f in files.values() if f["claimed"] is not None),
        },
        "infosys_files": infosys_files,
        "infosys_full_vs_deep": {
            "deep_matches": len(infosys_keys["infosys_deep"]),
            "full_matches": len(infosys_keys["infosys_full"]),
            "in_both": len(infosys_keys["infosys_deep"] & infosys_keys["infosys_full"]),
            "only_deep": len(infosys_keys["infosys_deep"] - infosys_keys["infosys_full"]),
            "only_full": len(infosys_keys["infosys_full"] - infosys_keys["infosys_deep"]),
        },
    }
    OUT.write_text(json.dumps(checks, indent=1), encoding="utf-8")
    print(json.dumps({k: checks[k] for k in ("flashscore_distinct_match_ids", "flashscore_totals",
                                             "infosys_full_vs_deep", "flashscore_distinct_match_ids_by_year",
                                             "flashscore_2025_onward_by_name_class")},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
