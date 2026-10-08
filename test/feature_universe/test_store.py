"""The feature universe's invariants: the store (data/studies/feature_universe/store.parquet, gitignored; rebuilt by
src/eda/feature_universe/perplayer_2026.py then build_store.py), its registry, the catalogue (universe.csv, by
src/eda/feature_universe/catalogue/build_universe.py) and the selection pool (menu.csv). Reads no result column.
Skipped when the store is absent.
Run: ./python.sh -m pytest test/feature_universe -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "feature_universe"
STORE = OUT / "store.parquet"
MODEL = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
KEYS = ["match_id", "tour", "season", "tournament_date", "debut_season"]
RESULTS = {"a_won", "won", "y", "winner", "result"}
GROUPS = {"m", "alt", "pp", "rt", "ad", "sl", "mk", "fi", "fp", "lv", "kn", "ds", "ctx"}

pytestmark = pytest.mark.skipif(not STORE.exists(), reason="the store is gitignored; build it first")


@pytest.fixture(scope="module")
def reg() -> pd.DataFrame:
    r = pd.read_csv(OUT / "store_registry.csv", keep_default_na=False)
    r["menu"] = r["menu"].astype(int)
    return r


def test_registry_lists_every_column_once(reg):
    names = pq.read_schema(STORE).names
    assert reg["column"].is_unique
    assert set(reg["column"]) == set(names) - set(KEYS)
    assert not set(names) & RESULTS


def test_rows_are_the_model_population():
    s = pd.read_parquet(STORE, columns=["match_id"])
    mf = pd.read_parquet(MODEL, columns=["match_id"])
    assert len(s) == len(mf) == 63737 and s["match_id"].is_unique
    assert set(s["match_id"].astype(str)) == set(mf["match_id"].astype(str))


def test_model_inputs_equal_the_model_frame(reg):
    m = reg.loc[reg["group"] == "m", "column"].tolist()
    assert len(m) == 58
    s = pd.read_parquet(STORE, columns=["match_id"] + m)
    mf = pd.read_parquet(MODEL, columns=["match_id"] + ["in_" + c[3:] for c in m])
    mf = mf.set_index(mf["match_id"].astype(str)).reindex(s["match_id"].astype(str))
    for c in m:
        assert np.array_equal(s[c].to_numpy(float), mf["in_" + c[3:]].to_numpy(float), equal_nan=True), c


def test_kinds_groups_and_flags(reg):
    assert set(reg["kind"]) <= {"diff", "pair", "context"}
    assert set(reg["group"]) <= GROUPS
    assert (reg.loc[reg["group"] == "mk", "flag"] == "market_internal").all()
    anchor = reg[(reg["hid"] == "B-ANCHOR") & (reg["group"] == "fi")]          # its fp__ fame pair is not market data
    assert len(anchor) == 3 and anchor["flag"].str.contains("market_internal").all()
    bd = reg[reg["flag"].str.contains("base-dependent")]
    assert len(bd) > 0 and set(bd["group"]) == {"fi"}
    assert reg["column"].str.fullmatch(r"[0-9A-Za-z_-]+").all()                # no spaces or slashes in names


def test_pairs_point_at_each_other(reg):
    p = reg[reg["kind"] == "pair"].set_index("column")["partner"]
    for c, q in p.items():
        assert p.get(q) == c, c
        assert c[:-2] == q[:-2] and {c[-2:], q[-2:]} == {"_a", "_b"}, c


def test_menu_has_no_copies(reg):
    menu = reg[reg["menu"] == 1]
    assert (menu["canonical"] == "").all() and (menu["near_dup_of"] == "").all() and (menu["degenerate"] == "").all()
    names = set(reg["column"])
    for col in ("canonical", "near_dup_of"):
        x = reg[reg[col] != ""]
        assert set(x[col]) <= names and (x[col] != x["column"]).all()
    mp = menu[menu["kind"] == "pair"].set_index("column")["partner"]
    assert set(mp.values) <= set(mp.index)                       # pairs enter the menu together


def test_copies_are_copies(reg):
    """Every `canonical` claim, and every near-duplicate's correlation, re-checked on the stored values."""
    x = reg[reg["canonical"] != ""]
    cols = sorted(set(x["column"]) | set(x["canonical"]))
    s = pd.read_parquet(STORE, columns=cols)
    for _, r in x.iterrows():
        a, b = s[r["column"]].to_numpy(float), s[r["canonical"]].to_numpy(float)
        assert np.allclose(a, float(r["dup_sign"]) * b, rtol=0, atol=1e-9, equal_nan=True), r["column"]
    y = reg[reg["near_dup_of"] != ""]
    s = pd.read_parquet(STORE, columns=sorted(set(y["column"]) | set(y["near_dup_of"])))
    for _, r in y.iterrows():
        a, b = s[r["column"]].to_numpy(float), s[r["near_dup_of"]].to_numpy(float)
        ok = np.isfinite(a) & np.isfinite(b)
        assert abs(np.corrcoef(a[ok], b[ok])[0, 1]) >= 0.999, r["column"]


def test_per_player_pairs_reproduce_the_model_differences():
    names = ["form_ace", "form_hold", "formdef_df", "adjperf_tpw_2w", "sets_14d"]
    s = pd.read_parquet(STORE, columns=[f"pp__{n}_{x}" for n in names for x in "ab"] + [f"m__{n}" for n in names]
                        + ["pp__age_pl_a", "pp__age_pl_b", "m__age"])
    for n, a, b in [(n, f"pp__{n}_a", f"pp__{n}_b") for n in names] + [("age", "pp__age_pl_a", "pp__age_pl_b")]:
        d, m = s[a].to_numpy(float) - s[b].to_numpy(float), s[f"m__{n}"].to_numpy(float)
        ok = np.isfinite(d) & np.isfinite(m)
        assert ok.sum() > 50000 and np.max(np.abs(d[ok] - m[ok])) < 1e-5, n


def test_build_checks_recorded():
    b = json.loads((OUT / "store_build.json").read_text(encoding="utf-8"))
    assert b["fi_swap_failures"] == [] and b["pairs_consistent"] and b["mk_ps_antisymmetric"]
    e = b["external"]
    assert e["ratings_side_a"] >= 0.999 and e["adj_equals_profile"]
    assert e["profile_side_a_max_gap"] <= 1e-9 and e["sides_side_a_max_gap"] <= 1e-9


@pytest.mark.skipif(not (OUT / "universe.csv").exists(), reason="universe.csv not built")
def test_universe_references_resolve(reg):
    u = pd.read_csv(OUT / "universe.csv", keep_default_na=False)
    v = json.loads((OUT / "build" / "validation.json").read_text(encoding="utf-8"))
    assert u["feature_id"].is_unique and len(u) == v["rows"]
    assert v["bad_store"] == {} and v["bad_rows"] == [] and v["bad_cov"] == []
    assert v["store_columns_unreferenced"] == [] and v["menu_unreferenced"] == []
    menu = set(reg.loc[reg["menu"] == 1, "column"])
    for cell in u["menu_columns"]:
        assert {t.strip() for t in cell.split(";") if t.strip()} <= menu


@pytest.mark.skipif(not (OUT / "menu.csv").exists(), reason="menu.csv not built")
def test_menu_csv_is_the_registry_menu(reg):
    mt = pd.read_csv(OUT / "menu.csv", keep_default_na=False).set_index("column")
    assert set(mt.index) == set(reg.loc[reg["menu"] == 1, "column"])
    assert set(mt["near_miss_tier"]) <= {"A", "B", "C", "D", "none"}
    assert set(mt["seen_2025_2026"]) <= {"yes", "no"}
    assert set(mt["priority"]) <= {"high", "medium", "low", "exclude"}
    # the owner's tier-A near misses are on the menu as their raw blocks
    for col in ("lv__elo", "fp__f09_venue__f09_ve", "fp__f26_impairment__ret_n_a", "pp__rest_days_a"):
        assert mt.at[col, "near_miss_tier"] == "A", col
