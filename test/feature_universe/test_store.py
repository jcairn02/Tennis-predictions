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
GROUPS = {"m", "alt", "pp", "rt", "ad", "sl", "mk", "fi", "fp", "lv", "kn", "ds", "ctx", "el", "fe"}
FE = OUT / "form_evidence"
FE_INSTANCE = "template_2026-10-13"                      # the instance the store's fe__ columns were built on
FE_COLUMNS = {"fe__sw_a", "fe__sw_b", "fe__r_a", "fe__r_b", "fe__r_diff"}
K3 = {"atp": 10.0, "wta": 20.0}                          # tpw's K3 (the level layer's pinned Stage B constants)

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


def test_event_levels_columns(reg):
    """el__ (added 8 Oct 2026): a share in [0, 1] per player, the difference is A - B, the pair points at itself, and
    all three are distinct menu columns."""
    el = reg[reg["group"] == "el"].set_index("column")
    assert set(el.index) == {"el__low_share_diff", "el__low_share_a", "el__low_share_b"}
    assert el.at["el__low_share_diff", "kind"] == "diff" and el.at["el__low_share_a", "partner"] == "el__low_share_b"
    assert (el["menu"] == 1).all()
    s = pd.read_parquet(STORE, columns=list(el.index))
    a, b, d = s["el__low_share_a"].to_numpy(float), s["el__low_share_b"].to_numpy(float), \
        s["el__low_share_diff"].to_numpy(float)
    assert np.allclose(d, a - b, rtol=0, atol=1e-12, equal_nan=True)
    assert np.nanmin(np.r_[a, b]) >= 0 and np.nanmax(np.r_[a, b]) <= 1
    assert np.isfinite(d).mean() > 0.99


def test_form_evidence_columns(reg):
    """fe__ (U-126 refreshed, 14 Oct 2026): sw >= 0 per player, r = sw / (sw + K3) with tpw's K3 by tour, r_diff =
    r_a - r_b, the pairs point at each other, all five are distinct menu columns, and they equal the source table."""
    fe = reg[reg["group"] == "fe"].set_index("column")
    assert set(fe.index) == FE_COLUMNS
    assert fe.at["fe__r_diff", "kind"] == "diff" and fe.at["fe__sw_a", "partner"] == "fe__sw_b"
    assert fe.at["fe__r_b", "partner"] == "fe__r_a" and (fe["menu"] == 1).all()
    s = pd.read_parquet(STORE, columns=["match_id", "tour"] + sorted(FE_COLUMNS))
    sa, sb, ra, rb, d = (s[c].to_numpy(float) for c in ("fe__sw_a", "fe__sw_b", "fe__r_a", "fe__r_b", "fe__r_diff"))
    k = s["tour"].map(K3).to_numpy(float)
    assert np.nanmin(np.r_[sa, sb]) >= 0
    assert np.allclose(ra, sa / (sa + k), rtol=0, atol=1e-12, equal_nan=True)
    assert np.allclose(rb, sb / (sb + k), rtol=0, atol=1e-12, equal_nan=True)
    assert np.allclose(d, ra - rb, rtol=0, atol=1e-12, equal_nan=True)
    assert np.nanmax(np.r_[ra, rb]) < 1 and np.isfinite(d).mean() > 0.998
    src = pd.read_parquet(FE / "store_columns.parquet").set_index("match_id").reindex(s["match_id"].astype(str))
    for c in FE_COLUMNS:
        assert np.array_equal(s[c].to_numpy(float), src[c[4:]].to_numpy(float), equal_nan=True), c
    assert set(src["instance"]) == {FE_INSTANCE}


def test_form_evidence_tables():
    """The template population's table covers the instance frame's matches, and the build's checks hold: the model's own
    adjperf_tpw_2w rebuilt from sw bit for bit, the independent recount, and the cut probe (protected rows unmoved
    beyond rounding; the leaky control caught)."""
    t = pd.read_parquet(FE / f"{FE_INSTANCE}.parquet")
    frame = pd.read_parquet(ROOT / "data" / "studies" / "current_best_model" / FE_INSTANCE / "model_frame_chain.parquet",
                            columns=["match_id"])
    assert t["match_id"].is_unique and set(t["match_id"]) == set(frame["match_id"].astype(str))
    k = t["tour"].map(K3).to_numpy(float)
    assert np.isfinite(t[["sw_a", "sw_b", "r_a", "r_b", "r_diff"]].to_numpy()).all()
    assert np.allclose(t["r_a"], t["sw_a"] / (t["sw_a"] + k), rtol=0, atol=1e-12)
    assert np.allclose(t["r_diff"], t["r_a"] - t["r_b"], rtol=0, atol=1e-12)
    c = json.loads((FE / f"{FE_INSTANCE}_checks.json").read_text(encoding="utf-8"))["checks"]
    b = c["b_denominator"]
    assert b["nan_pattern_equal"] and b["bitwise_equal"] == b["frame_matches"] == len(t)
    assert b["sw_positive_but_not_exists"] == 0 and b["negative_sw"] == 0
    assert c["b_recount"]["max_relative_gap"] < 1e-10
    p = c["c_probe"]
    assert p["cuts"] >= 4 and p["protected_changed"] == 0 and p["control_protected_changed"] > 0
    assert p["largest_protected_difference"] < 1e-12 and p["later_changed"] > 0
    assert c["frame_sides_equal_tree_stage0"] and c["women_untouched_by_the_layer"] and c["sw_without_z_equals_sw"]


def test_build_checks_recorded():
    b = json.loads((OUT / "store_build.json").read_text(encoding="utf-8"))
    assert b["fi_swap_failures"] == [] and b["pairs_consistent"] and b["mk_ps_antisymmetric"]
    e = b["external"]
    assert e["ratings_side_a"] >= 0.999 and e["adj_equals_profile"]
    assert e["profile_side_a_max_gap"] <= 1e-9 and e["sides_side_a_max_gap"] <= 1e-9
    el = b["event_levels"]
    assert el["rows_found"] == 63737 and el["side_a_equals_stage0"] and el["diff_is_a_minus_b"]
    fe = b["form_evidence"]
    assert fe["rows_found"] == 63737 and fe["values_found"] > 63500 and fe["side_a_equals_stage0"]
    assert fe["r_is_sw_over_sw_plus_k3"] and fe["diff_is_a_minus_b"] and fe["instance"] == [FE_INSTANCE]


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
    # the history composition the owner added on 8 Oct 2026, unseen on 2025-2026
    for col in ("el__low_share_diff", "el__low_share_a", "el__low_share_b"):
        assert mt.at[col, "feature_id"] == "U-330" and mt.at[col, "seen_2025_2026"] == "no", col
    # the form evidence the owner asked for on 14 Oct 2026: U-126 re-filed with the refreshed columns, unseen
    for col in sorted(FE_COLUMNS):
        assert mt.at[col, "feature_id"] == "U-126" and mt.at[col, "seen_2025_2026"] == "no", col
