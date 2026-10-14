"""Checks on chunk 1 of the Hugging Face ATP pipeline dump, once downloaded.

* Record counts per source, against the uploader's own progress files where they exist.
* Infosys depth by year and match type: records with point rows, and points with a full outcome
  (winner, forced or unforced error) rather than only ace / double fault / unclassified.
* A test join of the Infosys matches to Tennis My Life (ATP main, Challenger, qualifying) on
  year, ATP tournament id and the pair of ATP player codes.

Usage:
    ./python.sh src/eda/atp_pipeline_handoff/verify_chunk1.py

Writes data/studies/atp_pipeline_handoff/checks.json (tracked).
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
TML = ROOT / "data" / "dump" / "matches" / "tennis_my_life"
OUT = ROOT / "data" / "studies" / "atp_pipeline_handoff" / "checks.json"
FULL_OUTCOMES = {"WINNER", "FORCED ERROR", "UNFORCED ERROR"}


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open(encoding="utf-8", errors="replace")


def count_lines(path: Path) -> int:
    with open_text(path) as handle:
        return sum(1 for line in handle if line.strip())


def load_json(path: Path):
    with open_text(path) as handle:
        return json.load(handle)


def infosys() -> tuple[dict, dict]:
    per_year, keys = {}, {}
    for path in sorted((RAW / "infosys_deep").glob("*_data.jsonl*")):
        year = int(path.name[:4])
        c = Counter()
        with open_text(path) as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                kind = re.sub(r"\d+", "", str(record.get("match_id", "")))
                c["records"] += 1
                c[f"match_type_{kind}"] += 1
                points = outcome_points = 0
                for category in (record.get("rally_analysis") or {}).get("rallyData") or []:
                    for side in ("t1err", "t1win", "t2err", "t2win"):
                        for point in category.get(side) or []:
                            points += 1
                            outcome_points += point.get("pointEndType") in FULL_OUTCOMES
                if points:
                    c["with_points"] += 1
                    c[f"with_points_{kind}"] += 1
                    c["points"] += points
                if outcome_points:
                    c["with_full_outcomes"] += 1
                    c[f"with_full_outcomes_{kind}"] += 1
                centre = (record.get("match_status") or {}).get("matchCenter") or {}
                c["court_vision_flag"] += bool(centre.get("courtVision"))
                key = (year, str(record.get("tournament_id")),
                       frozenset({record.get("player1_id"), record.get("player2_id")}))
                keys[key] = kind
        checkpoint = RAW / "infosys_deep" / f"checkpoint_{year}.json"
        claim = load_json(checkpoint) if checkpoint.exists() else {}
        per_year[str(year)] = {**dict(sorted(c.items())), "claimed_total_matches": claim.get("total_matches"),
                               "claimed_court_vision": claim.get("total_court_vision")}
    return per_year, keys


def tml_keys(years) -> dict:
    keys = {}
    for level in ("atp_main", "atp_challenger", "atp_qualifying"):
        for path in sorted((TML / level).glob("*.parquet")):
            year = int(path.name[:4])
            if year not in years:
                continue
            frame = pd.read_parquet(path, columns=["tourney_id", "winner_id", "loser_id"])
            for tourney_id, winner, loser in zip(frame.tourney_id, frame.winner_id, frame.loser_id):
                prefix, _, tournament = str(tourney_id).partition("-")
                if prefix.isdigit():
                    keys[(int(prefix), tournament, frozenset({winner, loser}))] = level
    return keys


def join(infosys_keys: dict) -> dict:
    years = {key[0] for key in infosys_keys}
    tml = tml_keys(years)
    table = defaultdict(Counter)
    for key, kind in infosys_keys.items():
        level = tml.get(key)
        row = table[f"{key[0]} {kind}"]
        row["infosys_matches"] += 1
        row[f"in_tml_{level}" if level else "not_in_tml"] += 1
    return {k: dict(v) for k, v in sorted(table.items())}


def main() -> int:
    checks = {"generated_by": "src/eda/atp_pipeline_handoff/verify_chunk1.py"}
    per_year, keys = infosys()
    checks["infosys_deep"] = per_year
    checks["infosys_join_to_tennis_my_life"] = join(keys)

    vision = Counter(p.parent.name for p in (RAW / "court_vision").rglob("*.json.gz"))
    checks["court_vision_files_by_year"] = dict(sorted(vision.items()))

    checks["mcp_charts_records"] = sum(count_lines(p) for p in (RAW / "mcp" / "charts").glob("mcp_*.jsonl*"))

    ta = RAW / "tennis_abstract"
    progress = [load_json(p) for p in (ta / "_meta").glob("pass2_progress_*.json")]
    checks["tennis_abstract"] = {
        "player_match_rows": sum(count_lines(p) for p in ta.glob("player_matches_*.jsonl*")),
        "claimed_player_match_rows": sum(p.get("n_matches", 0) for p in progress),
        "bio_rows": sum(count_lines(p) for p in ta.glob("player_bios_*.jsonl*")),
        "claimed_bio_rows": sum(p.get("n_bios", 0) for p in progress)}

    checks["api_tennis_rows"] = {p.name: len(pd.read_csv(p, dtype=str, low_memory=False))
                                 for p in sorted((RAW / "api_tennis").glob("fixtures_*.csv*"))}
    checks["atp_scraped_enriched_rows"] = {
        p.name: len(pd.read_csv(p, dtype=str, low_memory=False))
        for p in sorted((RAW / "atp_scraped_enriched").glob("*.csv*"))}

    OUT.write_text(json.dumps(checks, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in checks.items() if k != "atp_scraped_enriched_rows"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
