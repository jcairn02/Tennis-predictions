"""Shared paths, constants and formulas of the IOS product-centring study (src/eda/ios_product_centring/).

The owner's request of 8 Oct 2026: centre the IOS ratings before forming the model's 7 matchup products, and measure
what the uncentred products' drift cost. The plan, written before any result: docs/studies/ios_product_centring/
preregistration.md (its SHA-256, CRLF normalised to LF, in data/studies/ios_product_centring/preregistration.sha256).

The products as the model has them (surface_ios/arms.py recipe "prod"), from the surface-effective ratings
O = O + E_s and D = D + F_s of the decided surface IOS:

    prod   = O_A * (-D_B) - O_B * (-D_A)

and centred on the reference level (m_O, m_D) of the match's own snapshot and surface:

    prod_c = -(O_A - m_O) * (D_B - m_D) + (O_B - m_O) * (D_A - m_D)
           = prod + m_D * (O_A - O_B) - m_O * (D_A - D_B)

The reference level at snapshot day t: the unweighted mean, over every player who served or returned in a main-tour
observation of the statistic released by t (lf + 1 <= t) whose best-estimate day is t - 364 or later, of O + E_s and
D + F_s on each surface s (of O and D for an unknown surface, code 0).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as SI  # noqa: E402

OUT = ROOT / "data" / "studies" / "ios_product_centring"
DOCS = ROOT / "docs" / "studies" / "ios_product_centring"
REF = OUT / "reference"                       # per (tour, statistic): the reference level of every snapshot
LOCAL = OUT / "local"                         # the centred arm's TabPFN fits (and local/repro)
CHECKS = OUT / "checks"                       # the gates G1-G6
PREREG = DOCS / "preregistration.md"
PREREG_SHA = OUT / "preregistration.sha256"
SI_RUNS = SI.OUT / "full_runs"                # the decided surface IOS's stored full-history runs (read only)

TOURS = ("atp", "wta")
STATS = SI.PROFILE_IOS                        # the model's 7: ace, df, first_in, first_won, second_won, hold, bp_saved
N_SURF = SI.N_SURF                            # surface codes 1..4; 0 unknown
WINDOW_DAYS = 364                             # the reference set: main-tour observations of the last 52 weeks
EXACT = 1e-12

log, jdump, sha256 = SI.log, SI.jdump, SI.sha256


def built_product(oa, ob, da, db):
    """The model's product (surface_ios/arms.py, recipe "prod"): A's offence times B's lack of defence minus the
    reverse."""
    return oa * (-db) - ob * (-da)


def centred_product(oa, ob, da, db, m_o, m_d):
    """The product of the ratings centred on the reference level (m_o, m_d)."""
    return -(oa - m_o) * (db - m_d) + (ob - m_o) * (da - m_d)


def level(m, count):
    """The reference level used: m where the snapshot has reference players, else 0 (the product left as built). Settled
    before any result was read, for snapshots with no main-tour observation in the last 52 weeks: women's holds before
    2015 (no women's hold box scores exist then) and the first weeks of 2010."""
    return np.where(np.asarray(count) > 0, m, 0.0)


def prereg_sha256() -> str:
    """SHA-256 of the pre-registration with CRLF normalised to LF."""
    return hashlib.sha256(PREREG.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_prereg() -> str:
    """The pre-registration must equal the hash recorded before any result was read."""
    want = PREREG_SHA.read_text(encoding="utf-8").strip()
    got = prereg_sha256()
    if got != want:
        raise RuntimeError(f"the pre-registration changed after it was hashed ({got} != {want})")
    return got


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def max_gap(x, y) -> tuple[float, bool]:
    """(largest |x - y| where both are finite, whether the missing values coincide)."""
    x, y = np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64")
    same_nan = bool(np.array_equal(np.isnan(x), np.isnan(y)))
    both = np.isfinite(x) & np.isfinite(y)
    return (float(np.max(np.abs(x[both] - y[both]))) if both.any() else 0.0), same_nan
