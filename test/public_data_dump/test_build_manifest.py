"""Offline tests for the manifest builder (no network)."""
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import build_manifest, common as C  # noqa: E402


def test_scan_reads_an_empty_file_that_repeats_a_column_name(tmp_path):
    # some WTA point files are empty and carry two "year" columns; pq.read_table refused to read any
    # column of such a file, which stopped the whole manifest build
    path = tmp_path / "2019.parquet"
    empty = pa.array([], pa.string())
    pq.write_table(pa.table([empty, empty, empty, empty], names=["year", "match_id", "Tier", "year"]), path)
    columns = pq.ParquetFile(path).schema_arrow.names
    assert build_manifest.date_bounds(path, columns) == (None, None, None)
    assert build_manifest.tier_counts(path, columns) == ("Tier", {})


def test_download_log_lists_small_sources_and_counts_large_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(build_manifest, "LISTED_RECEIPTS_MAX", 2)
    for source, n in (("small", 2), ("large", 3)):
        folder = tmp_path / "raw" / source
        folder.mkdir(parents=True)
        lines = [json.dumps({"name": f"f{i}", "route": "live", **({"error": "HTTP 404"} if i == 0 else {})})
                 for i in range(n)]
        (folder / "_receipts.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log = build_manifest.read_download_log()
    assert [r["name"] for r in log["small"]["receipts"]] == ["f0", "f1"]
    assert "receipts" not in log["large"] and (log["large"]["objects"], log["large"]["errors"]) == (3, 1)
    assert log["large"]["error_details"][0]["error"] == "HTTP 404"
    assert "raw/large/_receipts.jsonl" in log["large"]["receipts_note"]
