"""Verify repair provenance while retaining the original numerical evidence."""
from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.feature_alpha_audit.audit_inputs import digest

DATA = ROOT / "data/studies/feature_alpha_audit"
OUT = DATA / "repairs"


def main():
    original = pd.read_csv(DATA / "input_manifest.csv")
    evidence = original[original.path.str.startswith("data/studies/")]
    changed_data = [r.path for r in evidence.itertuples() if digest(ROOT / r.path) != r.sha256]
    assert not changed_data, changed_data
    with zipfile.ZipFile(OUT / "pre_repair_studies.zip") as archive:
        expected = original[~original.path.str.endswith(".parquet")]
        for r in expected.itertuples():
            assert hashlib.sha256(archive.read(r.path)).hexdigest() == r.sha256, r.path
    changed_code_docs = [r.path for r in original.itertuples() if digest(ROOT / r.path) != r.sha256]
    rows = pd.read_parquet(OUT / "repair_rows.parquet")
    frame = pd.read_parquet(OUT / "repair_features.parquet")
    assert rows.tournament_date.is_monotonic_increasing
    assert rows.side.iloc[::2].eq("A").all() and rows.side.iloc[1::2].eq("B").all()
    assert np.array_equal(rows.match_id.iloc[::2], rows.match_id.iloc[1::2])
    assert frame.match_id.is_unique and frame.match_date.notna().all()
    assert frame.tournament_date.equals(frame.match_date)
    assert set(frame.match_id).issubset(set(rows.match_id))
    features = json.loads((OUT / "repair_features_summary.json").read_text(encoding="utf-8"))
    assert features["input_sha256"] == digest(OUT / "repair_rows.parquet")
    assert features["output_sha256"] == digest(OUT / "repair_features.parquet")
    scoring = json.loads((OUT / "scoring_protocol.json").read_text(encoding="utf-8"))
    assert scoring["feature_sha256"] == features["output_sha256"]
    assert np.isfinite(frame.p_elo).all()
    for report in ("predictability_diagnostic", "ufc_ideas"):
        text = (ROOT / "docs/studies" / report / "report.html").read_text(encoding="utf-8")
        assert "Historical results — superseded" in text
        assert "feature_alpha_audit/repairs.html" in text
    # Targeted retries after a final fix replace earlier cases, not inflate the
    # count by counting repeated tests twice.
    cases = {}
    for path in sorted(OUT.glob("test_results*.xml"), key=lambda p: p.stat().st_mtime):
        for case in ET.parse(path).getroot().iter("testcase"):
            cases[(case.get("classname"), case.get("name"))] = case
    totals = {"tests": len(cases),
              "failures": sum(c.find("failure") is not None for c in cases.values()),
              "errors": sum(c.find("error") is not None for c in cases.values()),
              "skipped": sum(c.find("skipped") is not None for c in cases.values())}
    assert totals["failures"] == totals["errors"] == 0, totals
    assert totals["tests"] >= 290, totals
    summary = {"original_evidence_files_unchanged": len(evidence),
               "pre_repair_archive_files_verified": len(expected),
               "changed_original_code_and_docs": changed_code_docs,
               "repaired_history_matches": len(rows) // 2, "repaired_feature_rows": len(frame),
               "paired_rows_and_actual_dates_verified": True,
               "feature_input_hash_verified": True,
               "tests": totals,
               "repaired_artifact_hashes": {p.name: digest(p) for p in sorted(OUT.glob("*.parquet"))}}
    (OUT / "verification.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in
                      {"changed_original_code_and_docs", "repaired_artifact_hashes"}}))


if __name__ == "__main__":
    main()
