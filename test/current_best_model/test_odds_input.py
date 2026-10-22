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
    """A per-source table like odds_sources/table.py's, from rows of chances (None = not priced). A row's "te" is
    TennisExplorer's Pinnacle (tex_*, as odds_input.te_prices merges it), "te_timed" (default True) and "te_date"
    (default the row's date) with it."""
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
        if r.get("te") is not None:
            a, b = odds(r["te"], r.get("te_margin", 0.025))
            books = r.get("te_books", r["te"])                     # the site's other books (default: agree with it)
            row.update({"tex_a": a, "tex_b": b, "tex_timed": r.get("te_timed", True),
                        "tex_date": r.get("te_date", r.get("date", "2024-03-01")),
                        "tex_books_z": float(np.log(books / (1 - books))), "tex_books_n": 14.0, "tex_books_iqr": 0.05})
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


LOW = {"avg": 0.10, "b365": 0.10, "ot44": 0.89, "ot9": 0.89, "ot10": 0.89}   # tennis-data's books mirror OddsTrader's


def test_before_the_rule_of_21_oct_a_mirrored_oddstrader_price_was_left_out():
    # the rule as built to 21 Oct 2026 (RULE_BEFORE), kept for reproductions: Bergs v Alcaraz, Shanghai 2026
    s = sources([{**LOW, "ot8": 0.89, "season": 2026, "date": "2026-10-12"},                     # mirror: the average
                 {**LOW, "ot8": 0.12, "season": 2026, "date": "2026-10-12"},                     # agrees: BetOnline
                 {**OTHERS, "avg": 0.035, "ot8": 0.415, "season": 2026, "date": "2026-04-25"},   # gross, no mirror
                 {**LOW, "ot20": 0.89, "ot8": 0.89, "season": 2025, "date": "2025-08-20"}])     # Pinnacle there too
    b = O.construct(s, O.RULE_BEFORE)
    assert b["odds_input"].tolist() == ["average", "betonline", "betonline", "average"]
    assert b["oddstrader_mirror"].tolist() == [True, False, False, True]
    assert b["bol_gross"].tolist() == [False, False, True, False]
    assert np.isnan(b.loc[0, "bol_a"]) and np.isnan(b.loc[3, "pin_a"]) and np.isfinite(b.loc[1, "bol_a"])
    assert np.allclose(b["p_input"], [s["p_avg"][0], s["p_ot8"][1], s["p_ot8"][2], s["p_avg"][3]])
    s = sources([{**LOW, "ps": 0.11, "ot20": 0.89, "ot8": 0.89, "season": 2023, "date": "2023-05-01"}])
    b = O.construct(s, O.RULE_BEFORE)
    assert b["odds_input"].tolist() == ["pinnacle (tennis-data)"] and bool(b.loc[0, "oddstrader_mirror"])
    assert np.isclose(b.loc[0, "p_input"], s["p_ps"][0])


def test_oddstrader_wins_a_mirror_image_of_tennis_datas_books():
    # the owner, 21 Oct 2026: in all four mirrors of the instance of 21 Oct, every book on TennisExplorer sided with
    # OddsTrader (tennis-data's row had the two players' prices swapped)
    s = sources([{**LOW, "ot8": 0.89, "season": 2026, "date": "2026-10-12"},                     # BetOnline stands
                 {**LOW, "ot8": 0.12, "season": 2026, "date": "2026-10-12"},                     # no mirror: BetOnline
                 {**OTHERS, "avg": 0.035, "ot8": 0.415, "season": 2026, "date": "2026-04-25"},   # gross, no mirror
                 {**LOW, "ot20": 0.89, "ot8": 0.89, "season": 2025, "date": "2025-08-20"},      # OddsTrader's Pinnacle
                 {**LOW, "ps": 0.11, "ot20": 0.89, "ot8": 0.89, "season": 2023, "date": "2023-05-01"},  # not tennis-data's
                 {**LOW, "ps": 0.11, "ot8": 0.89, "season": 2024, "date": "2024-05-01"}])  # tennis-data's Pinnacle decides
    b = O.construct(s)
    assert b["odds_input"].tolist() == ["betonline", "betonline", "betonline", "pinnacle (oddstrader)",
                                        "pinnacle (oddstrader)", "pinnacle (tennis-data)"]
    assert b["tennis_data_swapped"].tolist() == [True, False, False, True, True, False]
    assert b["betonline_mirror_listed"].tolist() == [False, False, False, False, False, True]
    assert not b["oddstrader_mirror"].any() and b["bol_gross"].tolist() == [False, False, True, False, False, False]
    assert np.isfinite(b.loc[0, "bol_a"]) and (b.loc[3:4, "pin_source"] == "oddstrader").all()
    assert np.allclose(b["p_input"], [s["p_ot8"][0], s["p_ot8"][1], s["p_ot8"][2], s["p_ot20"][3], s["p_ot20"][4],
                                      s["p_ps"][5]])


def test_a_pinnacle_the_reconciliation_took_from_tennis_data_stays():
    # the 2021 US Open: OddsTrader's recording of Pinnacle failed (squashed toward 50%), its other books agreed with
    # tennis-data; a line that looks like a mirror of tennis-data's books must not replace tennis-data's close
    s = sources([{"avg": 0.31, "b365": 0.31, "ot44": 0.31, "ot9": 0.31, "ot10": 0.31, "ps": 0.30, "ot20": 0.64,
                  "ot8": 0.31, "season": 2021, "date": "2021-08-31"}])
    b = O.construct(s)
    assert b.loc[0, "odds_input"] == "pinnacle (tennis-data)" and not b.loc[0, "tennis_data_swapped"]
    assert np.isclose(b.loc[0, "p_input"], s["p_ps"][0])


def test_tennisexplorer_pinnacle_from_november_2025_where_it_is_time_stamped():
    late = {**OTHERS, "ot8": 0.69, "season": 2026}
    s = sources([{**late, "te": 0.72, "date": "2026-03-10"},                                   # the site's Pinnacle
                 {**late, "te": 0.72, "date": "2025-10-31", "season": 2025},                   # before 1 Nov: BetOnline
                 {**late, "te": 0.72, "te_timed": False, "date": "2026-03-10"},               # no time shown: BetOnline
                 {**late, "te": 0.72, "te_margin": 0.30, "date": "2026-03-10"},               # not a coherent quote
                 {**OTHERS, "te": 0.72, "date": "2026-03-10"},                                 # nothing else: the site
                 {**late, "te": 0.72, "ot20": 0.71, "date": "2025-11-02", "season": 2025}])   # OddsTrader's Pinnacle first
    b = O.construct(s)
    assert b["odds_input"].tolist() == ["pinnacle (tennisexplorer)", "betonline", "betonline", "betonline",
                                        "pinnacle (tennisexplorer)", "pinnacle (oddstrader)"]
    te = OC.devig(s["tex_a"], s["tex_b"])
    assert np.isclose(b.loc[0, "p_input"], te[0]) and np.isclose(b.loc[4, "p_input"], te[4])
    assert b.loc[0, "pin_source"] == "tennisexplorer" and np.isclose(b.loc[0, "pin_a"], s.loc[0, "tex_a"])
    assert np.isfinite(b.loc[0, "bol_a"]) and np.isnan(b.loc[1, "pin_a"])


def test_the_sites_own_errors_leave_betonline_in_place():
    late = {**OTHERS, "season": 2026, "date": "2026-04-14"}
    s = sources([{**late, "ot8": 0.73, "te": 0.27, "te_books": 0.73},   # its Pinnacle row off its own books (Kopriva v Engel)
                 {**late, "avg": 0.265, "b365": 0.27, "ot8": 0.23, "te": 0.76},   # the whole page swapped (Atmane v Tiafoe)
                 {**LOW, "ot8": 0.89, "te": 0.90, "season": 2026, "date": "2026-10-12"}])   # with BetOnline (Bergs)
    b = O.construct(s)
    assert b["odds_input"].tolist() == ["betonline", "betonline", "pinnacle (tennisexplorer)"]
    assert b["te_left_out"].tolist() == ["the site's Pinnacle far from its other books",
                                         "the site against BetOnline and the average", ""]
    assert bool(b.loc[2, "tennis_data_swapped"])


def test_tennisexplorer_far_from_betonline_is_used_and_listed():
    s = sources([{**OTHERS, "ot8": 0.20, "te": 0.72, "season": 2026, "date": "2026-03-10"}])
    b = O.construct(s)
    assert b.loc[0, "odds_input"] == "pinnacle (tennisexplorer)" and bool(b.loc[0, "te_bol_gross"])


def test_tennisexplorer_coverage_by_month():
    frame = pd.DataFrame({"match_id": [f"m{i}" for i in range(120)],
                          "tournament_date": ["2025-10-27"] * 10 + ["2026-01-12"] * 60 + ["2026-02-09"] * 50})
    kinds = [O.K_BOL] * 10 + [O.K_TE] * 55 + [O.K_BOL] * 5 + [O.K_TE] * 30 + [O.K_BOL] * 20
    cov = O.te_coverage(frame, pd.DataFrame({"match_id": frame["match_id"], "odds_input": kinds}))
    assert list(cov["by_month"]) == ["2026-01", "2026-02"]                 # October 2025 is before TE_FROM
    assert cov["by_month"]["2026-01"]["share"] == round(55 / 60, 4) and cov["low_months"] == ["2026-02"]
