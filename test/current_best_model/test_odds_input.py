"""Tests of the Pinnacle-first odds input (src/eda/current_best_model/odds_input.py; the owner's decision of 9 Oct 2026).

Synthetic: the order Pinnacle > BetOnline > the books' average; tennis-data's Pinnacle after July 2025 left out;
OddsTrader's late lines dropped; the two Pinnacle recordings reconciled by the other books; the frame rewrite keeps the
average and refuses to run twice. On disk (skipped if absent): the instance of 9 Oct differs from the frozen reference in
the odds input only.

Run: ./python.sh -m pytest test/current_best_model/test_odds_input.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import odds_input as O  # noqa: E402
from src.eda.odds_sources import common as OC  # noqa: E402


def odds(p: float, margin: float = 0.03) -> tuple[float, float]:
    """Decimal odds for A and B with the given chance of A and overround 1 + margin."""
    return 1.0 / (p * (1 + margin)), 1.0 / ((1 - p) * (1 + margin))


def sources(rows: list[dict]) -> pd.DataFrame:
    """A per-source table like odds_sources/table.py's, from rows of chances (None = not priced)."""
    out = []
    for i, r in enumerate(rows):
        row = {"match_id": f"m{i}", "season": r.get("season", 2024), "td_date": pd.Timestamp(r.get("date", "2024-03-01")),
               "a_won": 1.0, "block": i}
        for s in ("ps", "ot20", "ot8", "avg", "b365", "ot44", "ot9", "ot10"):
            p = r.get(s)
            a, b = odds(p) if p is not None else (np.nan, np.nan)
            row.update({f"{s}_a": a, f"{s}_b": b, f"p_{s}": np.nan if p is None else OC.devig(a, b),
                        f"over_{s}": 1 / a + 1 / b if p is not None else np.nan})
            if s.startswith("ot"):
                row[f"after_{s}_min"] = r.get(f"after_{s}", -60.0)
        out.append(row)
    return pd.DataFrame(out)


OTHERS = {"avg": 0.70, "b365": 0.70, "ot44": 0.70, "ot9": 0.70, "ot10": 0.70}


def test_the_order_is_pinnacle_then_betonline_then_the_average():
    s = sources([{**OTHERS, "ps": 0.71, "ot20": 0.71, "ot8": 0.69},
                 {**OTHERS, "ot8": 0.69},
                 {**OTHERS}])
    b = O.construct(s)
    assert b["odds_input"].tolist() == ["pinnacle (tennis-data)", "betonline", "average"]
    assert np.allclose(b["p_input"], [s["p_ps"][0], s["p_ot8"][1], s["p_avg"][2]])
    assert np.isfinite(b.loc[0, "pin_a"]) and np.isnan(b.loc[1, "pin_a"])


def test_tennis_data_pinnacle_after_july_2025_is_not_pinnacle():
    s = sources([{**OTHERS, "ps": 0.71, "ot8": 0.69, "season": 2025, "date": "2025-08-15"},
                 {**OTHERS, "ps": 0.71, "ot20": 0.72, "ot8": 0.69, "season": 2025, "date": "2025-08-15"}])
    b = O.construct(s)
    assert b["odds_input"].tolist() == ["betonline", "pinnacle (oddstrader)"]


def test_late_oddstrader_lines_are_dropped():
    s = sources([{**OTHERS, "ot20": 0.71, "after_ot20": 45.0, "ot8": 0.69}])
    assert O.construct(s)["odds_input"].tolist() == ["betonline"]


def test_the_other_books_decide_between_the_two_pinnacle_recordings():
    s = sources([{**OTHERS, "ps": 0.50, "ot20": 0.71},          # tennis-data's far from the others: OddsTrader's
                 {**OTHERS, "ps": 0.705, "ot20": 0.70}])        # within 0.1 in log-odds: tennis-data's
    b = O.construct(s)
    assert b["odds_input"].tolist() == ["pinnacle (oddstrader)", "pinnacle (tennis-data)"]
    assert np.allclose(OC.devig(b["pin_a"], b["pin_b"]), b["p_input"])


def test_rewrite_keeps_the_average_and_refuses_twice(tmp_path):
    s = sources([{**OTHERS, "ps": 0.71}, {**OTHERS, "ot8": 0.60}])
    built = O.construct(s)
    frame = pd.DataFrame({"match_id": ["m0", "m1"], "tour": ["atp", "wta"], "season": [2024, 2024],
                          "p_mkt": s["p_avg"].to_numpy(), "in_odds_logit": OC.lg(s["p_avg"]), "in_age": [1.0, 2.0]})
    frame.to_parquet(tmp_path / "model_frame.parquet", index=False)
    rec = O.rewrite(tmp_path, built, {})
    f = pd.read_parquet(tmp_path / "model_frame.parquet")
    assert np.allclose(f["p_mkt"], built["p_input"]) and np.allclose(f["p_mkt_avg"], s["p_avg"])
    assert np.allclose(f["in_odds_logit"], np.log(f["p_mkt"] / (1 - f["p_mkt"])))
    assert f["in_age"].tolist() == [1.0, 2.0] and list(f.columns[:6]) == list(frame.columns)
    assert rec["by_source"]["pinnacle (tennis-data)"] == 1 and rec["by_source"]["betonline"] == 1
    with pytest.raises(SystemExit):
        O.rewrite(tmp_path, built, {})


INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "pinnacle_first_2026-10-09" / "model_frame.parquet"
REFERENCE = ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "instance" / \
    "model_frame.parquet"


@pytest.mark.skipif(not (INSTANCE.exists() and REFERENCE.exists()), reason="the instance or the reference is not on disk")
def test_the_instance_differs_from_the_reference_in_the_odds_input_only():
    new, ref = pd.read_parquet(INSTANCE), pd.read_parquet(REFERENCE)
    assert new["match_id"].tolist() == ref["match_id"].tolist()
    changed = [c for c in ref.columns if not ref[c].equals(new[c])]
    assert changed == ["p_mkt", "in_odds_logit"]
    assert np.allclose(new["p_mkt_avg"], ref["p_mkt"])
    assert set(new["odds_input"]) <= set(O.KINDS)
