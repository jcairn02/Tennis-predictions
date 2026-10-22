"""The context part's summary: the headline numbers of parts C, D and E (read from their outputs), the SHA-256 of every
input read outside the snapshot, and the check that the live Stage 0 still equals the snapshot's manifest (the brief's
rule 3). Writes data/studies/source_reconciliation/context/summary.json.

Run: ./python.sh src/eda/source_reconciliation/ctx_summary.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import ctx_common as X  # noqa: E402

INPUTS = [
    "data/studies/match_timing/timing.parquet",
    "data/studies/current_best_model/template_2026-10-14/model_frame.parquet",
    "data/studies/data_continuity/tml_vs_sackmann_pairs.parquet",
    "data/dump/points/tennislive/listed.parquet",
    "data/dump/points/tennislive/events.parquet",
    "data/raw/gap_sources/bwandowando/matches.csv",
    "data/dump/points/wta/player_results/2026.parquet",
    "data/dump/points/wta/player_matches/2026.parquet",
    "data/dump/points/wta/editions.parquet",
    "data/dump/points/itf_live/matches.parquet",
    "data/dump/matches/open_tennis_data/completed.parquet",
    "data/dump/matches/live_tennis_api_zenodo/matches.parquet",
    "data/dump/players/sackmann_archive/atp/atp_players.parquet",
    "data/dump/players/sackmann_archive/wta/wta_players.parquet",
    "data/dump/players/tennis_my_life/ATP_Database.parquet",
    "data/dump/players/live_tennis_api_zenodo/players.parquet",
    "data/dump/players/open_tennis_data/players.parquet",
    "data/dump/points/tdi/matches.parquet",
]


def load(name: str):
    p = X.OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main() -> int:
    man = json.loads((C.SNAP / "manifest.json").read_text(encoding="utf-8"))
    live = []
    for f in man["files"]:
        if not f["source"].startswith("data/studies/predictability_diagnostic/"):
            continue
        p = C.ROOT / f["source"]
        live.append({"file": f["source"], "manifest_sha256": f["sha256"], "live_sha256": C.sha256(p),
                     "equal": C.sha256(p) == f["sha256"]})
    inputs = []
    for rel in INPUTS:
        p = C.ROOT / rel
        if p.exists():
            st = p.stat()
            inputs.append({"file": rel, "bytes": st.st_size, "sha256": C.sha256(p),
                           "modified": pd.Timestamp(st.st_mtime, unit="s", tz="UTC").isoformat(timespec="seconds")})
    res = load("results_summary.json") or {}
    summ = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "snapshot_manifest_made_at": man["made_at"],
        "live_stage0_equals_snapshot": live,
        "live_stage0_note": "no ctx_ module reads the live Stage 0: the identity linker and the indoor rule were run on "
                            "the snapshot's tables; checked anyway",
        "inputs_outside_snapshot": inputs,
        "part_c": {k: res.get(k) for k in ("links", "stage0_matches", "stage0_matches_linked",
                                           "stage0_matches_with_an_independent_source", "model_frame_matches",
                                           "model_frame_with_two_or_more_independent_families", "links_by_source",
                                           "contradicted_by_field", "contradicted_in_model_frame_by_field",
                                           "wta_site_sets_reoriented_to_its_winner",
                                           "internal_inconsistency_by_source")},
        "part_c_self_links": load("selflink_summary.json"),
        "part_c_tml_rows": load("tml_rows_summary.json"),
        "part_d_indoor": load("indoor_summary.json"),
        "part_d_dates": {k: v for k, v in (load("dates_summary.json") or {}).items()
                         if k not in ("day_minus_tournament_date", "links_outside_clock_examples")},
        "part_e": {k: v for k, v in (load("dob_summary.json") or {}).items() if k != "pairwise"},
        "handcheck": "handcheck.json",
    }
    X.write_json(X.OUT / "summary.json", summ)
    print(json.dumps(live, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
