"""Shared definitions of the study "serve-speed change in the best TabPFN model" (src/eda/serve_speed_tabpfn/).

The owner's request of 7 Oct 2026, the binding rules and the team: docs/studies/serve_speed_tabpfn/brief.md and
team.md. The design was settled in data/studies/serve_speed_tabpfn/design/2_audit.md (the auditor's rulings) and
lead_notes.md. This module holds the harness's constants (the integration strategist's build, audit C5-C6).

The expanding-window test. For each test season Y in 2024, 2025, 2026, every arm is the local, non-thinking TabPFN-3.5
trained on the model frame's matches of 2013 .. Y - 1 and scored on season Y. Seasons 2019-2023 are fitted the same way
(each trained on 2013 .. season - 1) only to calibrate: one slope per tour, fitted for season Y on the arm's own
out-of-sample seasons 2019 .. Y - 1.

Every path lives on a `Paths` object, so tests can point the harness at synthetic stand-ins; the default is the real
study tree. The base arm's earlier fits (feature interactions' and the rating race's folders) are read-only.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402  (symmetrise, log loss, blocks, intervals, fingerprint)

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn"
DOCS = ROOT / "docs" / "studies" / "serve_speed_tabpfn"


@dataclass(frozen=True)
class Paths:
    out: Path = OUT
    local: Path = OUT / "local"                       # this study's fits (and local/repro: the reproduction fits)
    checks: Path = OUT / "checks"                     # the CPU fingerprint check and the reproduction check
    features: Path = OUT / "features"                 # registry.json (this harness), speed.parquet + speed_meta.json
    model_frame: Path = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
    model_inputs: Path = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_inputs.json"
    fi_local: Path = ROOT / "data" / "studies" / "feature_interactions" / "local"     # read only: model seeds 3-15
    race_local: Path = ROOT / "data" / "studies" / "surface_rating_race" / "local"    # read only: model(_noodds) 0-2
    early: Path = ROOT / "data" / "studies" / "surface_elo_pieces" / "early_price_frame.parquet"
    stage0_pre: Path = (ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" /
                        "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet")
    prereg: Path = DOCS / "preregistration.md"
    panel: Path = OUT / "speed_panel.parquet"                                   # the engineer's R3 panel (C1)
    features_py: Path = ROOT / "src" / "eda" / "serve_speed_tabpfn" / "features.py"   # the modeller's builder (C3)

    @property
    def feature_file(self) -> Path:
        return self.features / "speed.parquet"

    @property
    def feature_meta(self) -> Path:
        return self.features / "speed_meta.json"

    @property
    def registry(self) -> Path:
        return self.features / "registry.json"

    @property
    def repro(self) -> Path:
        return self.local / "repro"

    @property
    def prereg_sha(self) -> Path:
        return self.prereg.with_suffix(".sha256")

    def with_(self, **kw) -> "Paths":
        return replace(self, **kw)


DEFAULT = Paths()

TOURS = ("atp", "wta")
TRAIN_FROM = 2013
CALIB_FROM = 2019                     # the decided calibration: out-of-sample seasons from 2019
CAL_SEASONS = tuple(range(2019, 2024))
TEST_SEASONS = (2024, 2025, 2026)
PRICE_SEASONS = (2025, 2026)          # arms with the odds also predict at Polymarket's 24-hour and 30-minute prices
CAL_SEEDS = (0, 1, 2, 3)              # every calibration slope, every arm and the base (audit Q5)
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}
EPS = 1e-6                            # as feature interactions' harness (the reused fits' query prices are clipped so)
TAU_NUDGE = 0.05                      # S9: prior SD of the nudge's coefficient, log-odds per SD (published evidence)
REPRO_TOL = 1e-6                      # C5: a reproduction fit must equal the stored forecasts within this

# Logged mean fit seconds per season (data/studies/serve_speed_tabpfn/design/strategist_gpu.json), plus overhead.
FIT_SECONDS = {"odds": {2019: 14.9, 2020: 16.4, 2021: 20.2, 2022: 24.7, 2023: 28.5, 2024: 33.4, 2025: 39.3,
                        2026: 47.4},
               "noodds": {2019: 14.6, 2020: 16.2, 2021: 20.4, 2022: 23.1, 2023: 27.5, 2024: 32.3, 2025: 37.6,
                          2026: 41.2}}
FIT_OVERHEAD_S = 1.5

T0 = time.time()
ll, blocks, symmetrize, fit_logistic, fingerprint = T.ll, T.blocks, T.symmetrize, T.fit_logistic, T.fingerprint


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def lg(p) -> np.ndarray:
    from scipy.special import logit
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def sha256_file(path: Path) -> str:
    return T.sha256_file(Path(path))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, value) -> None:
    T.write_json(Path(path), value)


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def race_names(cols: list[str]) -> list[str]:
    """The rating race's fits name the 21 surface-built IOS profile inputs sf_<name> (surface_rating_race/arms.py,
    'surface-built profile inputs are sf_<name>; in the model they keep their names'); model_frame.py drops the prefix.
    Values are the same (model_inputs.json check surface_profile_equals_sprof_arm). Applied to race files only."""
    return [c[3:] if c.startswith("sf_") else c for c in cols]


CODE_FILES = ("src/eda/serve_speed_tabpfn/common.py", "src/eda/serve_speed_tabpfn/arms.py",
              "src/eda/serve_speed_tabpfn/forecasts.py", "src/eda/serve_speed_tabpfn/score.py",
              "src/eda/serve_speed_tabpfn/local_fits.py", "src/eda/tabpfn_thinking/common.py")


def code_hash() -> str:
    """SHA-256 over the harness's code (and the shared module it imports), in a fixed order: the pre-registration
    records it and `score.py --run` refuses to run on other code."""
    h = hashlib.sha256(b"serve_speed_tabpfn/harness/v1")
    for rel in CODE_FILES:
        h.update(rel.encode())
        h.update((ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()
