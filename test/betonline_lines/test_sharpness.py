"""Offline tests for the BetOnline-against-Pinnacle sharpness study (no data files)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.betonline_lines import sharpness as SH  # noqa: E402


def test_american_prices_become_decimal_odds():
    assert np.allclose(SH.american_to_decimal([-450, 360, 100, -100, -125]), [1 + 100 / 450, 4.6, 2.0, 2.0, 1.8])


def test_betonline_prices_follow_the_side_that_won_and_flags_drop_uncertain_closes():
    td = pd.DataFrame({"td_id": ["a", "b"], "winner": ["Sinner J.", "Fritz T."]})
    bo = pd.DataFrame({"eid": [1, 2], "mw_close_home": [-450, -450], "mw_close_away": [360, 360],
                       "mw_open_home": [-375, -375], "mw_open_away": [305, 305],
                       "mw_close_uncertain": [False, True], "mw_open_uncertain": [False, False],
                       "mw_close_after_listed_min": [-500.0, 200.0]})
    # row a: the home side (Sinner) won; row b: the away side (Fritz) won
    links = pd.DataFrame({"td_id": ["a", "b"], "condition_id": [1, 2], "a_won": [False, True], "gap": [0, 0]})
    m = SH.attach_betonline(td, bo, links).set_index("td_id")
    assert np.isclose(m.at["a", "BOLCW"], 1 + 100 / 450) and np.isclose(m.at["a", "BOLCL"], 4.6)
    assert np.isclose(m.at["b", "BOLCW"], 4.6) and np.isclose(m.at["b", "BOLOW"], 4.05)
    assert m.at["a", "ok_bol"] and not m.at["b", "ok_bol"]   # b's close is flagged uncertain
    assert m.at["b", "ok_bol_any"] and m.at["b", "ok_bolo"]   # but it is coherent, and its opening is fine
    assert np.isclose(m.at["a", "overround_bol"], 1 / (1 + 100 / 450) + 1 / 4.6)


def test_line_shopping_takes_each_sides_best_price_and_is_only_cheaper_when_the_books_split():
    rows = ([{"PSW": 1.50, "PSL": 2.70, "BOLCW": 1.55, "BOLCL": 2.50}] * 20     # split: BetOnline's favourite, Pinnacle's dog
            + [{"PSW": 1.50, "PSL": 2.70, "BOLCW": 1.45, "BOLCL": 2.60}] * 20)  # Pinnacle best on both sides
    m = pd.DataFrame(rows)
    m["ok_ps"] = m["ok_bol"] = True
    out = SH.line_shopping(m, pd.Series(True, index=m.index))
    split_margin, ps_margin = 1 / 1.55 + 1 / 2.70 - 1, 1 / 1.50 + 1 / 2.70 - 1
    assert out["n"] == 40 and out["split_share"] == 0.5 and out["below_zero_share"] == 0.0
    assert np.isclose(out["mean_pct"]["best_of"], round(100 * (split_margin + ps_margin) / 2, 3))
    assert np.isclose(out["best_of_minus_cheapest_book_pp"], round(100 * (split_margin - ps_margin) / 2, 3))
    assert out["favourite"]["betonline_better_share"] == 0.5 and out["underdog"]["pinnacle_better_share"] == 1.0


def test_margins_compare_betonline_with_pinnacle_on_the_same_rows():
    n = 40
    m = pd.DataFrame({f"overround_{b}": [s] * n for b, s in (("ps", 1.03), ("bol", 1.04), ("b365", 1.05), ("avg", 1.06))})
    for b in ("ps", "bol", "b365", "avg"):
        m[f"ok_{b}"] = True
    m.loc[0, "ok_bol"] = False                                  # one row without a coherent BetOnline close
    out = SH.margins(m, pd.Series(True, index=m.index))
    assert out["n"] == n - 1
    assert np.isclose(out["mean_pct"]["bol"], 4.0) and np.isclose(out["mean_pct"]["ps"], 3.0)
    assert np.isclose(out["bol_minus_ps_pp"]["est"], 1.0) and np.isclose(out["bol_over_ps_ratio"]["est"], 4 / 3)
    assert out["bol_wider_share"] == 1.0
