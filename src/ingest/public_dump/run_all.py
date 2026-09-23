"""Run the public data dump: download every planned public source, stage it to Parquet by source, and
rebuild the tracked manifest/coverage files.

Sources (keys for --sources): sackmann (archival mirror), tml (Tennis My Life), mcp (Match Charting
Project), zenodo (Live Tennis API sample), otd (Open Tennis Data), tdcouk (tennis-data.co.uk odds).
Polymarket price histories are long-running and run separately:
    ./python.sh -m src.ingest.public_dump.polymarket_prices --buckets all

Usage:
    ./python.sh -m src.ingest.public_dump.run_all --sources all --start-year 2010
    ./python.sh -m src.ingest.public_dump.run_all --sources tml,tdcouk --refresh
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import (build_manifest, common as C, live_tennis_api_zenodo, match_charting,
                                    open_tennis_data, sackmann_archive, tennis_data_couk, tennis_my_life)

SOURCES = {"sackmann": sackmann_archive, "tml": tennis_my_life, "mcp": match_charting,
           "zenodo": live_tennis_api_zenodo, "otd": open_tennis_data, "tdcouk": tennis_data_couk}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", default="all", help="comma list of " + ",".join(SOURCES) + " or all")
    parser.add_argument("--start-year", type=int, default=C.DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=C.DEFAULT_END_YEAR)
    parser.add_argument("--refresh", action="store_true", help="re-download and re-stage everything selected")
    parser.add_argument("--sackmann-commit", default=sackmann_archive.PINNED_COMMIT)
    parser.add_argument("--no-slam", action="store_true")
    parser.add_argument("--no-doubles", action="store_true")
    parser.add_argument("--mcp-commit", default=match_charting.PINNED_COMMIT)
    parser.add_argument("--mcp-all-eras", action="store_true")
    parser.add_argument("--otd-tag", default=None)
    parser.add_argument("--tdcouk-routes", default=",".join(tennis_data_couk.ALL_ROUTES))
    parser.add_argument("--no-manifest", action="store_true")
    args = parser.parse_args()

    keys = list(SOURCES) if args.sources == "all" else [k.strip() for k in args.sources.split(",") if k.strip()]
    unknown = [k for k in keys if k not in SOURCES]
    if unknown:
        parser.error(f"unknown sources {unknown}; choose from {list(SOURCES)}")
    summaries = {}
    for key in keys:
        C.log(f"===== {key} =====")
        try:
            summaries[key] = SOURCES[key].run(args)
        except Exception as err:  # keep going; the failure is recorded in the run summary
            summaries[key] = {"source": key, "fatal": f"{type(err).__name__}: {err}", "traceback": traceback.format_exc()}
            C.log(f"[{key}] FATAL {type(err).__name__}: {err}")
    C.STUDY_ROOT.mkdir(parents=True, exist_ok=True)
    entry = {"finished_at": C.utc_now_iso(), "args": vars(args), "summaries": summaries}
    with (C.STUDY_ROOT / "run_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    if not args.no_manifest:
        build_manifest.main()
    failed = {k: v for k, v in summaries.items() if v.get("fatal") or v.get("errors")}
    for key, summary in summaries.items():
        C.log(f"[{key}] staged_files={summary.get('staged_files')} rows={summary.get('staged_rows')} "
              f"errors={len(summary.get('errors') or [])} fatal={summary.get('fatal')}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
