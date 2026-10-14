"""Tests of the level layer of the lower-level-evidence system (src/eda/lower_level_evidence/level_layer.py) and of C1's
sandbox patches (system_sandbox.py).

Synthetic data and synthetic parameter files that follow SPEC 6.2's schema (B's parameters do not exist yet). They check
that the hooks are off without LLE_LAYER (the same objects come back), that the config and the hashes are enforced, the
exchange-rate and ITF rules, the translation's formula, sign and class gating, that every hook at the identity settings
reproduces its input exactly, that the patched Elo passes are the original ones with booleans and that w = 0 equals
"does not move", and that the weighted step-1 moments equal Stage B's own at w = 1.
Run: ./python.sh -m pytest test/lower_level_evidence/test_level_layer.py -q
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import level_layer as L  # noqa: E402
from src.eda.lower_level_evidence import system_sandbox as S  # noqa: E402

MAP_LEVEL = {"MAIN": "T250", "TQ": "TQ", "GSQ": "GSQ", "CH": "CH", "CHQ": "CHQ", "ITF": "ITF", "ITFQ": "ITFQ",
             "TEAM": "TEAM"}
BUCKETS = ("MAIN", "TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ", "TEAM")
FAMILIES_ON = {f: True for f in L.FAMILIES}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(autouse=True)
def fresh_caches(monkeypatch):
    monkeypatch.delenv(L.ENV, raising=False)
    for c in (L._CFG, L._TABLES, L._BUCKETS, L._BOX, L._SHA):
        c.clear()
    yield
    for c in (L._CFG, L._TABLES, L._BUCKETS, L._BOX, L._SHA):
        c.clear()


def rows_frame(n_per_bucket=4, tours=("atp", "wta"), seasons=(2019, 2020)):
    """Two rows per match (A then B), every bucket, both tours: match_id, side, tour, year, player_id."""
    recs, k = [], 0
    for t in tours:
        for y in seasons:
            for b in BUCKETS:
                for _ in range(n_per_bucket):
                    for side in ("A", "B"):
                        recs.append({"match_id": f"{t}{y}{b}{k}", "side": side, "tour": t, "year": y, "bucket": b,
                                     "player_id": f"{t}:{k % 7}:{side}"})
                    k += 1
    return pd.DataFrame(recs)


def write_stage0(tmp: Path, rows: pd.DataFrame) -> Path:
    m = rows.drop_duplicates("match_id")[["match_id", "bucket"]]
    p = tmp / "stage0_matches.parquet"
    pd.DataFrame({"match_id": m["match_id"], "map_level": m["bucket"].map(MAP_LEVEL)}).to_parquet(p, index=False)
    return p


def write_strength(tmp: Path, rows: pd.DataFrame, seed=1) -> dict:
    rng = np.random.default_rng(seed)
    m = rows.drop_duplicates("match_id")[["match_id"]].copy()
    m["elo_a_ret"] = rng.normal(1600, 150, len(m)).astype("float32")
    m["elo_b_ret"] = rng.normal(1600, 150, len(m)).astype("float32")
    p = tmp / "strength.parquet"
    m.to_parquet(p, index=False)
    return {"path": str(p), "sha256": sha(p)}


def write_params(tmp: Path, seasons=(2019, 2020), stats=("spw", "rpw", "ace", "def_ace", "tpw", "first_won",
                                                          "rpw_first", "results"),
                 gamma=-0.3, delta=0.05, w=0.6, ref=1700.0) -> tuple[str, str]:
    recs = []
    for y in seasons:
        for t in ("atp", "wta"):
            for s in stats:
                for lv in L.LOWER:
                    recs.append({"season_used": y, "tour": t, "stat": s, "level": lv, "gamma": gamma,
                                 "delta": delta + 0.01 * L.LOWER.index(lv), "w": w, "w_joint": w + 0.05,
                                 "w_lo": w - 0.1, "w_hi": w + 0.1,
                                 "delta_lo": 0.0, "delta_hi": 0.1, "n_players": 100, "strength_ref": ref,
                                 "prior_mu": 0.0, "prior_k": 5.0, "fit_through": f"{y - 1}-12-31",
                                 "method_version": "test"})
    p = tmp / "params.parquet"
    pd.DataFrame(recs).to_parquet(p, index=False)
    return str(p), sha(p)


def write_classes(tmp: Path, inputs: dict, stats: dict) -> str:
    """A's schema: inputs {name: (class, "CH,CHQ" | "none")}, stats {name: (class, delta_levels)}; both tours."""
    recs = []
    for kind, entries in (("input", inputs), ("stat", stats)):
        for name, (cls, levels) in entries.items():
            for t in ("atp", "wta"):
                recs.append({"name": name, "kind": kind, "tour": t, "base_stat": name, "side": "serve",
                             "family": "test", "class": cls, "gamma": "-0.3", "gamma_unit": "logit per 100 Elo",
                             "rule": "test", "delta_levels": levels})
    p = tmp / "classes.csv"
    pd.DataFrame(recs).to_csv(p, index=False)
    (tmp / "classes.sha256").write_text(f"{sha(p)}  classes.csv\n", encoding="utf-8")
    return str(p)


def config(tmp: Path, stage0: Path, monkeypatch=None, **kw) -> dict:
    cfg = {"name": "TEST", "tours": ["atp"], "params": None, "translate": False, "weight": 1.0,
           "weight_results": 1.0, "prior": "pool", "itf_box": "as_is", "families": dict(FAMILIES_ON),
           "stage0_matches": str(stage0), "record_dir": str(tmp / "rec")}
    cfg.update(kw)
    p = tmp / f"cfg_{len(list(tmp.glob('cfg_*.json')))}.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    if monkeypatch is not None:
        monkeypatch.setenv(L.ENV, str(p))
    return cfg


# ------------------------------------------------------------------------------------------------
# Off: the same objects come back

def test_hooks_off_return_their_input_objects():
    x, d, ok = np.arange(4.0), np.arange(4.0) + 5, np.ones(4, bool)
    rows = pd.DataFrame({"match_id": list("abcd")})
    assert L.points_counts(rows, "spw", x, d, ok)[0] is x and L.points_counts(rows, "spw", x, d, ok)[1] is d
    Z = {("ace", "adjperf"): np.zeros(3)}
    assert L.forms_z(object(), {}, Z) is Z
    h = {"n_a": [1.0]}
    assert L.ratings_arrays(rows, h) is h
    upd = [True, False]
    assert L.elo_weights(rows, upd) is upd
    out = np.zeros((2, 8))
    assert L.elo_rerun(rows, upd, out, lambda u: 1 / 0) is out
    chosen = {("atp", "spw"): {}}
    assert L.pin("stageB_adjperf", chosen) is chosen

    class Ctx:
        def step3(self, *a):
            return "builder's step3"
    assert L.forms_step3(Ctx(), "ace", "adjperf", [], None, None, 0, ()) == "builder's step3"


def test_a_family_switched_off_returns_its_input(tmp_path, monkeypatch):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    config(tmp_path, st0, monkeypatch, weight=0.0, families={**FAMILIES_ON, "points_52w": False, "elo": False})
    x = np.ones(len(rows))
    assert L.points_counts(rows, "spw", x, x, x > 0)[0] is x
    upd = [True] * len(rows)
    assert L.elo_weights(rows, upd) is upd


# ------------------------------------------------------------------------------------------------
# The config and the hashes

def test_config_refusals(tmp_path):
    st0 = tmp_path / "s.parquet"
    good = {"name": "T", "tours": ["atp"], "params": None, "translate": False, "weight": 1.0, "weight_results": 1.0,
            "prior": "pool", "itf_box": "as_is", "families": dict(FAMILIES_ON), "stage0_matches": str(st0)}
    L.validate(good)
    for bad, err in ((dict(good, weight=1.6), ValueError), (dict(good, weight="half"), ValueError),
                     (dict(good, weight="fitted"), ValueError),                 # fitted needs params
                     (dict(good, translate=True), ValueError),                  # translate needs params
                     (dict(good, prior="newcomer"), NotImplementedError),
                     (dict(good, itf_box="drop"), ValueError), (dict(good, tours=["itf"]), ValueError),
                     (dict(good, families={"forms": True}), ValueError),
                     (dict(good, elo_count="all"), NotImplementedError)):
        with pytest.raises(err):
            L.validate(bad)
    with pytest.raises(KeyError):
        L.validate({k: v for k, v in good.items() if k != "itf_box"})
    with pytest.raises(ValueError):                                             # params without its hash
        L.validate(dict(good, params="p.parquet", weight="fitted"))
    with pytest.raises(ValueError):                                             # translate needs the strength
        L.validate(dict(good, params="p.parquet", params_sha256="x", translate=True))


def test_params_and_classes_hashes_are_checked(tmp_path):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    p, h = write_params(tmp_path)
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256="0" * 64, weight="fitted"))
    with pytest.raises(RuntimeError):
        L.params_table(cfg)
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256=h, weight="fitted"))
    assert len(L.params_table(cfg)) > 0
    c = write_classes(tmp_path, {"points_52w": ("OPP", "CH")}, {"spw": ("OPP", "CH")})
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256=h, classes=c))
    assert len(L.classes_table(cfg)) == 4
    (tmp_path / "classes.sha256").write_text("f" * 64 + "  classes.csv\n", encoding="utf-8")
    L._TABLES.clear()
    with pytest.raises(RuntimeError):
        L.classes_table(cfg)


# ------------------------------------------------------------------------------------------------
# w and T

def test_weights_separation_and_itf_rules(tmp_path):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    b, t, y = rows["bucket"].to_numpy(), rows["tour"].to_numpy(), rows["year"].to_numpy()
    sep = L.validate(config(tmp_path, st0, tours=["atp"], weight=0.0, weight_results=0.0, itf_box="exclude"))
    w = L.weights(sep, "spw", t, b, y, "box")
    low = np.isin(b, L.LOWER)
    assert (w[low & (t == "atp")] == 0).all() and (w[~low] == 1).all() and (w[t == "wta"] == 1).all()
    wr = L.weights(sep, "results", t, b, y, "results")
    assert (wr[low & (t == "atp")] == 0).all() and (wr[t == "wta"] == 1).all()
    noitf = L.validate(config(tmp_path, st0, tours=["atp", "wta"], itf_box="exclude"))
    w = L.weights(noitf, "spw", t, b, y, "box")
    assert (w[np.isin(b, ("ITF", "ITFQ"))] == 0).all() and (w[~np.isin(b, ("ITF", "ITFQ"))] == 1).all()
    assert (L.weights(noitf, "results", t, b, y, "results") == 1).all()      # ITF results stay in Elo
    asis = L.validate(config(tmp_path, st0, tours=["atp"], weight=0.5, itf_box="as_is"))
    w = L.weights(asis, "spw", t, b, y, "box")
    itf = np.isin(b, ("ITF", "ITFQ"))
    assert (w[itf] == 1).all() and (w[low & ~itf & (t == "atp")] == 0.5).all()   # as_is: ITF as the reference has it


def test_fitted_weights_read_their_own_season_and_refuse_missing_keys(tmp_path):
    rows = rows_frame(seasons=(2019, 2020))
    st0 = write_stage0(tmp_path, rows)
    p, h = write_params(tmp_path, seasons=(2019, 2020), w=0.6)
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256=h, weight="fitted", itf_box="exclude"))
    b, t, y = rows["bucket"].to_numpy(), rows["tour"].to_numpy(), rows["year"].to_numpy()
    w = L.weights(cfg, "spw", t, b, y, "box")
    m = np.isin(b, ("TQ", "GSQ", "CH", "CHQ")) & (t == "atp")
    assert np.allclose(w[m], 0.6) and (w[np.isin(b, ("ITF", "ITFQ")) & (t == "atp")] == 0).all()
    late = rows_frame(seasons=(2021,))
    st1 = write_stage0(tmp_path, late)
    cfg = L.validate(config(tmp_path, st1, params=p, params_sha256=h, weight="fitted"))
    with pytest.raises(KeyError):                                             # no 2021 parameters: no guessing
        L.weights(cfg, "spw", late["tour"], late["bucket"], late["year"], "box")
    cfg = L.validate(config(tmp_path, st1, params=p, params_sha256=h, weight="fitted", params_season_floor=None))
    with pytest.raises(KeyError):
        L.weights(cfg, "spw", late["tour"], late["bucket"], late["year"], "box")


def test_fitted_weights_are_capped_at_one_and_the_capped_rows_recorded_for_dev_seasons_only(tmp_path):
    """The lead's ruling at checkpoint 1: a fitted w above 1 is set to 1, whichever column is read (w, w_joint) and for
    w_results; numeric weights (the dose arms) are untouched; B's own bound of 3 is still enforced; the records and
    capped_cells describe seasons before 2025 only."""
    rows = rows_frame(seasons=(2024, 2025))
    st0 = write_stage0(tmp_path, rows)
    p, h = write_params(tmp_path, seasons=(2024, 2025), w=2.82)            # w_joint = 2.87
    b, t, y = rows["bucket"].to_numpy(), rows["tour"].to_numpy(), rows["year"].to_numpy()
    low = np.isin(b, ("TQ", "GSQ", "CH", "CHQ")) & (t == "atp")
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256=h, weight="fitted", weight_results="fitted",
                            itf_box="exclude"))
    assert cfg["fitted_cap"] == 1.0 and cfg["fitted_cap_results"] == 1.0       # the ruling is the default
    assert (L.weights(cfg, "spw", t, b, y, "box")[low] == 1.0).all()
    assert (L.weights(cfg, "spw", t, b, y, "box", column="w_joint")[low] == 1.0).all()
    wr = L.weights(cfg, "results", t, b, y, "results")
    assert (wr[np.isin(b, L.LOWER) & (t == "atp")] == 1.0).all()
    recs = [json.loads(x) for x in (tmp_path / "rec" / "layer_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    capped = [r for r in recs if r.get("capped_at") == 1.0]
    assert len(capped) == 3 and {r["column"] for r in capped} == {"w", "w_joint"}
    n_dev = int((np.isin(b, L.LOWER) & (t == "atp") & (y == 2024)).sum())
    box_dev = int((low & (y == 2024)).sum())
    assert [r["rows_dev_seasons"] for r in capped] == [box_dev, box_dev, n_dev]
    assert [round(r["max_before_dev_seasons"], 6) for r in capped] == [2.82, 2.87, 2.82]
    assert all("sealed" in r["sealed_seasons"] for r in capped)
    cells = L.capped_cells(cfg)
    assert set(cells["season_used"]) == {2024} and set(cells["tour"]) == {"atp"}
    assert set(cells["column"]) == {"w", "w_joint"} and (cells["capped_to"] == 1.0).all()
    # no cap: B's values as fitted (up to its bound of 3); a numeric weight is never capped
    free = L.validate(config(tmp_path, st0, params=p, params_sha256=h, weight="fitted", itf_box="exclude",
                             fitted_cap=None))
    assert np.allclose(L.weights(free, "spw", t, b, y, "box")[low], 2.82)
    dose = L.validate(config(tmp_path, st0, weight=1.5, itf_box="exclude"))
    assert (L.weights(dose, "spw", t, b, y, "box")[low] == 1.5).all()
    p3, h3 = write_params(tmp_path, seasons=(2024, 2025), w=3.2)
    L._TABLES.clear()
    over = L.validate(config(tmp_path, st0, params=p3, params_sha256=h3, weight="fitted", itf_box="exclude"))
    with pytest.raises(ValueError):                                          # beyond B's own bound: refused
        L.weights(over, "spw", t, b, y, "box")
    base = config(tmp_path, st0)
    for bad in (0.0, 3.5, "one", True):
        with pytest.raises(ValueError):
            L.validate(dict(base, fitted_cap=bad))
    s = L.summary(np.full(len(b), 0.5), np.zeros(len(b)), b, np.isin(b, L.LOWER), y)
    assert s["CH"]["rows_dev_seasons"] == int((np.isin(b, "CH") & (y == 2024)).sum())
    assert s["CH"]["rows_sealed_seasons"] == int((np.isin(b, "CH") & (y == 2025)).sum()) and "w_mean" in s["CH"]
    s25 = L.summary(np.full(len(b), 0.5), np.zeros(len(b)), b, np.isin(b, L.LOWER) & (y == 2025), y)
    assert all("w_mean" not in v for v in s25.values())                     # sealed rows: counts only


def test_missing_parameters_are_refused_or_left_untouched_by_choice(tmp_path):
    rows = rows_frame(seasons=(2019, 2020))
    st0 = write_stage0(tmp_path, rows)
    p, h = write_params(tmp_path, seasons=(2019,))                 # 2020 has no parameters
    strength = write_strength(tmp_path, rows)
    b, t, y = rows["bucket"].to_numpy(), rows["tour"].to_numpy(), rows["year"].to_numpy()
    s = np.full(len(rows), 1500.0)
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256=h, translate=True, strength=strength,
                            weight="fitted", itf_box="exclude"))
    with pytest.raises(KeyError):
        L.translation(cfg, "points_52w", "spw", t, b, y, s)
    keep = L.validate(config(tmp_path, st0, params=p, params_sha256=h, translate=True, strength=strength,
                             weight="fitted", itf_box="exclude", missing_params="untouched"))
    T = L.translation(keep, "points_52w", "spw", t, b, y, s)
    w = L.weights(keep, "spw", t, b, y)
    low20 = np.isin(b, ("TQ", "GSQ", "CH", "CHQ")) & (t == "atp") & (y == 2020)
    low19 = np.isin(b, ("TQ", "GSQ", "CH", "CHQ")) & (t == "atp") & (y == 2019)
    assert (T[low20] == 0).all() and (w[low20] == 1).all()       # no parameters: as the reference has them
    assert (T[low19] != 0).all() and np.allclose(w[low19], 0.6)
    valid = y == 2019                                              # a row whose observation does not exist: no lookup
    assert (L.translation(cfg, "points_52w", "spw", t, b, y, s, valid=valid)[low20] == 0).all()


def test_translation_formula_sign_and_classes(tmp_path):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    p, h = write_params(tmp_path, gamma=-0.3, delta=0.05, ref=1700.0)
    strength = write_strength(tmp_path, rows)
    b, t, y = rows["bucket"].to_numpy(), rows["tour"].to_numpy(), rows["year"].to_numpy()
    s_opp = np.full(len(rows), 1500.0)                       # opponents 200 points weaker than the reference
    # classes null (SYS_NOCLASS): gamma and delta at every lower level
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256=h, translate=True, strength=strength,
                            itf_box="exclude"))
    T = L.translation(cfg, "points_52w", "spw", t, b, y, s_opp)
    m = np.isin(b, ("TQ", "GSQ", "CH", "CHQ")) & (t == "atp")
    dl = np.array([0.05 + 0.01 * L.LOWER.index(x) for x in b[m]])
    exp = -0.3 * (1500.0 - 1700.0) / 100.0 + dl
    assert np.allclose(T[m], exp)
    assert (T[m] > 0).all()                                  # weaker opponents inflate serve points: T > 0, value down
    assert (T[~m] == 0).all()                                # MAIN, TEAM, ITF (excluded) and women: 0
    Tc = L.translation(cfg, "form_first_won", "rpw_first", t, b, y, s_opp, sign=-1.0)
    assert np.allclose(Tc[m], -exp)                          # a complement reads its statistic's terms negated
    # A's schema: the input's class gates gamma; the statistic's delta_levels gate delta; INTR is untouched
    c = write_classes(tmp_path, {"points_52w": ("OPP", "TQ,GSQ,CH,CHQ"), "form_ace": ("ENV", "TQ"),
                                 "age": ("INTR", "n/a"), "ratings_iid": ("OPP", "GSQ")},
                      {"spw": ("OPP", "CH"), "ace": ("ENV", "TQ"), "def_ace": ("OPP", "none")})
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256=h, translate=True, strength=strength,
                            itf_box="exclude", classes=c))
    T = L.translation(cfg, "points_52w", "spw", t, b, y, s_opp)
    g = 0.6
    assert np.allclose(T[m & (b == "CH")], g + 0.05 + 0.01 * L.LOWER.index("CH"))
    assert np.allclose(T[m & (b == "TQ")], g)               # gamma only where the statistic's delta is not real
    T = L.translation(cfg, "form_ace", "ace", t, b, y, s_opp)
    assert np.allclose(T[m & (b == "TQ")], 0.05) and (T[m & (b != "TQ")] == 0).all()   # ENV: delta only (TQ's)
    T = L.translation(cfg, "form_ace", "def_ace", t, b, y, s_opp)
    assert (T == 0).all()                                    # ENV input, and def_ace's delta is not real anywhere
    assert (L.translation(cfg, "age", "ace", t, b, y, s_opp) == 0).all()
    T = L.translation(cfg, "ratings_iid", "spw", t, b, y, None, gamma_term=False, delta_from="input")
    assert np.allclose(T[m & (b == "GSQ")], 0.05 + 0.01 * L.LOWER.index("GSQ")) and (T[m & (b != "GSQ")] == 0).all()
    off = L.validate(config(tmp_path, st0, params=p, params_sha256=h, translate=False, strength=strength))
    assert (L.translation(off, "points_52w", "spw", t, b, y, s_opp) == 0).all()


def test_form_views_follow_the_observation_owner():
    assert L.form_views("ace", "adjperf")["norm"] == ("def_ace", 1.0)          # what the opponent allowed: def_
    assert L.form_views("first_won", "adjperf")["norm"] == ("rpw_first", -1.0)  # the mirror's complement
    assert L.form_views("tpw", "adjperf")["norm"] == ("tpw", -1.0)
    assert L.form_views("brk", "adjperf")["norm"] == ("hold", -1.0)
    assert L.form_views("ace", "adjdef") == {"norm": ("ace", 1.0), "own": ("ace", 1.0), "step3": ("def_ace", 1.0)}
    assert all(L.form_views(s, ch)["own"] == (s, 1.0) for s, ch in L.FORM_SPECS)


def test_opponent_strength_reads_the_other_side(tmp_path):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    strength = write_strength(tmp_path, rows)
    p, h = write_params(tmp_path)
    cfg = L.validate(config(tmp_path, st0, params=p, params_sha256=h, translate=True, strength=strength))
    s = L.opponent_strength(cfg, rows["match_id"], rows["side"])
    tab = pd.read_parquet(strength["path"]).set_index("match_id")
    a = rows["side"].eq("A").to_numpy()
    assert np.array_equal(s[a], tab.loc[rows["match_id"][a], "elo_b_ret"].to_numpy("float64"))
    assert np.array_equal(s[~a], tab.loc[rows["match_id"][~a], "elo_a_ret"].to_numpy("float64"))


# ------------------------------------------------------------------------------------------------
# The hooks at the identity settings, and what they do otherwise

def test_points_counts_identity_is_exact_and_translation_follows_the_formula(tmp_path, monkeypatch):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    rng = np.random.default_rng(3)
    d = rng.integers(20, 90, len(rows)).astype(float)
    x = np.floor(d * rng.uniform(0.3, 0.8, len(rows)))
    ok = rng.random(len(rows)) > 0.1
    x, d = np.where(ok, x, 0.0), np.where(ok, d, 0.0)
    config(tmp_path, st0, monkeypatch, tours=["atp", "wta"])
    x2, d2 = L.points_counts(rows, "spw", x, d, ok)
    assert np.array_equal(x2, x) and np.array_equal(d2, d)
    p, h = write_params(tmp_path)
    strength = write_strength(tmp_path, rows)
    config(tmp_path, st0, monkeypatch, params=p, params_sha256=h, translate=True, strength=strength, weight=0.5)
    cfg = L.config()
    x3, d3 = L.points_counts(rows, "rpw", x, d, ok)
    s_opp = L.opponent_strength(cfg, rows["match_id"], rows["side"])
    T = L.translation(cfg, "points_52w", "rpw", rows["tour"], rows["bucket"], rows["year"], s_opp)
    r = (x + 0.5) / (d + 1.0)
    from scipy.special import expit, logit
    xt = np.where(ok & (T != 0), x + d * (expit(logit(r) - T) - r), x)
    w = L.weights(cfg, "rpw", rows["tour"], rows["bucket"], rows["year"])
    assert np.allclose(x3[ok], (xt * w)[ok]) and np.allclose(d3[ok], (d * w)[ok])
    assert np.array_equal(x3[~ok], x[~ok])
    assert (x3[ok & (T > 0)] / np.maximum(d3[ok & (T > 0)], 1e-9) < x[ok & (T > 0)] / d[ok & (T > 0)] + 1e-12).all()
    assert L.points_counts(rows, "ace", x, d, ok)[0] is x                     # only spw and rpw


def test_ratings_arrays_identity_is_exact_and_w_scales_the_points(tmp_path, monkeypatch):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    t = rows.drop_duplicates("match_id").reset_index(drop=True)
    rng = np.random.default_rng(4)
    h = {"n_a": rng.integers(40, 90, len(t)).astype(float).tolist(), "w_a": rng.integers(10, 40, len(t)).astype(float).tolist(),
         "n_b": rng.integers(40, 90, len(t)).astype(float).tolist(), "w_b": rng.integers(10, 40, len(t)).astype(float).tolist(),
         "mu": rng.normal(0.6, 0.05, len(t)).tolist(), "upd": [True] * len(t)}
    config(tmp_path, st0, monkeypatch, tours=["atp", "wta"])
    out = L.ratings_arrays(t, h)
    for c in ("n_a", "w_a", "n_b", "w_b", "mu"):
        assert out[c] == h[c]
    config(tmp_path, st0, monkeypatch, tours=["atp"], weight=0.0, itf_box="exclude")
    out = L.ratings_arrays(t, h)
    low = np.isin(t["bucket"], L.LOWER) & t["tour"].eq("atp").to_numpy()
    assert (np.asarray(out["n_a"])[low] == 0).all() and np.array_equal(np.asarray(out["n_a"])[~low],
                                                                        np.asarray(h["n_a"])[~low])
    assert out["mu"] == h["mu"]                               # no translation: the intercept is untouched
    p, hh = write_params(tmp_path)
    config(tmp_path, st0, monkeypatch, tours=["atp"], weight="fitted", params=p, params_sha256=hh, translate=True,
           strength=write_strength(tmp_path, rows), itf_box="exclude")
    out = L.ratings_arrays(t, h)
    low = np.isin(t["bucket"], ("TQ", "GSQ", "CH", "CHQ")) & t["tour"].eq("atp").to_numpy()
    assert np.allclose(np.asarray(out["n_a"])[low], np.asarray(h["n_a"])[low] * 0.65)   # w_joint, one per observation
    assert out["mu"] == h["mu"]                               # no level term in the solve by default


# ------------------------------------------------------------------------------------------------
# The patched Elo passes

def patched_function(rel: str, name: str, namespace: dict):
    """A function of the patched version of a builder (C1's patch text applied to the repository's file; since 10 Oct
    2026 the repository's builders carry it, and patched_text returns them as they are)."""
    return _function(S.patched_text((ROOT / rel).read_text(encoding="utf-8"), rel), rel, name, namespace)


def original_function(rel: str, name: str, namespace: dict):
    """The same function of the DECIDED builder: the repository's file with C1's edits undone (unpatched_text)."""
    return _function(S.unpatched_text((ROOT / rel).read_text(encoding="utf-8"), rel), rel, name, namespace)


def _function(text: str, rel: str, name: str, namespace: dict):
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = dict(namespace)
    exec(compile(ast.Module(body=[node], type_ignores=[]), rel, "exec"), ns)
    return ns[name]


def elo_history(n=400, players=25, seed=5):
    rng = np.random.default_rng(seed)
    week = np.sort(rng.integers(0, 60, n)) * 7
    event = rng.integers(0, 3, n)
    rnd = rng.integers(1, 4, n)
    o = np.lexsort((rnd, event, week))
    a = rng.integers(0, players, n)
    b = (a + rng.integers(1, players, n)) % players
    return {"week": week[o].tolist(), "event": event[o].tolist(), "rnd": rnd[o].tolist(), "a": a.tolist(),
            "b": b.tolist(), "a_won": (rng.random(n) < 0.5).tolist(), "surf": rng.integers(-1, 4, n).tolist(),
            "n_players": players}


def test_patched_stage1_pass_is_the_original_with_booleans_and_w0_means_no_move():
    from src.eda.predictability_diagnostic import stage1_baselines as B1
    rel = "src/eda/predictability_diagnostic/stage1_baselines.py"
    ns = {"np": np, "START": B1.START, "SURFACES": B1.SURFACES}
    f = patched_function(rel, "elo_pass", ns)
    orig = original_function(rel, "elo_pass", ns)            # the decided pass (the repository's carries the hooks)
    h = elo_history()
    upd = (np.random.default_rng(6).random(len(h["week"])) < 0.9).tolist()
    args = (h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"])
    k = (h["n_players"], 600.0, 2.0, 0.6)
    ref = orig(*args, upd, *k)
    assert np.array_equal(f(*args, upd, *k), ref, equal_nan=True)
    assert np.array_equal(B1.elo_pass(*args, upd, *k), ref, equal_nan=True)   # the repository's builder, layer off
    assert np.array_equal(f(*args, [1.0 if u else 0.0 for u in upd], *k), ref, equal_nan=True)
    w0 = [u and i % 3 != 0 for i, u in enumerate(upd)]                    # w = 0 on every third match
    assert np.array_equal(f(*args, [1.0 if u else 0.0 for u in w0], *k), orig(*args, w0, *k), equal_nan=True)
    # two matches in two weeks, player 0 in both: the first result at weight 0.5 moves him by half and counts 0.5
    two = ([0, 7], [0, 0], [1, 1], [0, 0], [1, 2], [True, True], [0, 0])
    full = f(*two, [True, True], 3, 600.0, 2.0, 0.6)
    half = f(*two, [0.5, 1.0], 3, 600.0, 2.0, 0.6)
    assert np.isclose(half[1, 0] - B1.START, 0.5 * (full[1, 0] - B1.START))
    assert half[1, 2] == 0.5 and full[1, 2] == 1
    assert np.isclose(half[1, 4] - B1.START, 0.5 * (full[1, 4] - B1.START))  # the surface rating likewise


def test_patched_pieces_and_stage4_passes_are_the_originals_with_booleans():
    from src.eda.predictability_diagnostic import stage1_baselines as B1
    from src.eda.predictability_diagnostic import stage4_features as F4
    from src.eda.surface_elo_pieces import common as PC
    from src.eda.surface_elo_pieces import pieces as PI
    h = elo_history(seed=7)
    upd = (np.random.default_rng(8).random(len(h["week"])) < 0.9).tolist()
    args = (h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"])
    g = patched_function("src/eda/surface_elo_pieces/pieces.py", "elo_pass_ext",
                         {"np": np, "START": PI.START, "C": PC})
    g0 = original_function("src/eda/surface_elo_pieces/pieces.py", "elo_pass_ext",
                           {"np": np, "START": PI.START, "C": PC})
    for mode, kd in (("stage1", {}), ("anchored", {}), ("offset", {"kd0": 80.0, "kd_off": 10.0, "kd_shape": 0.6})):
        ref = g0(*args, upd, h["n_players"], 600.0, 2.0, 0.6, mode=mode, **kd)
        assert np.array_equal(PI.elo_pass_ext(*args, upd, h["n_players"], 600.0, 2.0, 0.6, mode=mode, **kd), ref,
                              equal_nan=True)                    # the repository's builder, layer off
        assert np.array_equal(g(*args, upd, h["n_players"], 600.0, 2.0, 0.6, mode=mode, **kd), ref, equal_nan=True)
        assert np.array_equal(g(*args, [float(u) for u in upd], h["n_players"], 600.0, 2.0, 0.6, mode=mode, **kd), ref,
                              equal_nan=True)
    wf = patched_function("src/eda/predictability_diagnostic/stage4_features.py", "weighted_elo_pass",
                          {"np": np, "B": B1})
    wf0 = original_function("src/eda/predictability_diagnostic/stage4_features.py", "weighted_elo_pass",
                            {"np": np, "B": B1})
    weight = np.random.default_rng(9).uniform(0.8, 1.2, len(upd)).tolist()
    ref = wf0(*args, upd, weight, h["n_players"], 600.0, 2.0, 0.6)
    assert np.array_equal(F4.weighted_elo_pass(*args, upd, weight, h["n_players"], 600.0, 2.0, 0.6), ref,
                          equal_nan=True)
    assert np.array_equal(wf(*args, upd, weight, h["n_players"], 600.0, 2.0, 0.6), ref, equal_nan=True)
    assert np.array_equal(wf(*args, [float(u) for u in upd], weight, h["n_players"], 600.0, 2.0, 0.6), ref,
                          equal_nan=True)


def test_elo_weights_and_rerun(tmp_path, monkeypatch):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    t = rows.drop_duplicates("match_id").reset_index(drop=True)
    upd = [i % 5 != 0 for i in range(len(t))]
    config(tmp_path, st0, monkeypatch, tours=["atp"], weight_results=0.0, weight=0.0)
    w = L.elo_weights(t, upd)
    low = np.isin(t["bucket"], L.LOWER) & t["tour"].eq("atp").to_numpy()
    assert all(wi == 0.0 for wi, l_ in zip(w, low) if l_)
    assert all(wi == float(u) for wi, u, l_ in zip(w, upd, low) if not l_)
    assert L.elo_rerun(t, upd, "out", lambda u: ("rerun", u))[0] == "rerun"


# ------------------------------------------------------------------------------------------------
# Stage B's step-1 moments

def test_weighted_moments_equal_stage_b_at_unit_weights_and_drop_w0_rows():
    from src.eda.ufc_ideas import stageB_common as B
    rng = np.random.default_rng(10)
    n = 600
    rows = pd.DataFrame({"pcode": rng.integers(0, 12, n), "day": np.sort(rng.integers(0, 400, n)) // 7 * 7,
                         "ev": rng.integers(0, 4, n), "round_order": rng.integers(1, 4, n), "order": np.arange(n)})
    box = np.arange(n)
    P = B.PairIndex(rows, box)
    a, ok, units = rng.normal(0, 1, n), rng.random(n) > 0.1, rng.integers(20, 80, n).astype(float)
    sp = {"x": (P.to_sorted(a), P.to_sorted(ok), P.to_sorted(units))}
    wanted = [("x", 26.0, 0), ("x", np.inf, 1)]
    ref = B.pair_moments(P, sp, wanted)
    one = L.pair_moments_w(P, {"x": sp["x"] + (np.ones(n),)}, wanted)
    for k in wanted:
        for u, v in zip(ref[k], one[k]):
            assert np.array_equal(u, v)
    rw = (rng.random(n) > 0.3).astype(float)
    dropped = B.pair_moments(P, {"x": (P.to_sorted(a), P.to_sorted(ok & (rw > 0)), P.to_sorted(units))}, wanted)
    got = L.pair_moments_w(P, {"x": sp["x"] + (P.to_sorted(rw),)}, wanted)
    for k in wanted:
        for u, v in zip(dropped[k], got[k]):
            assert np.allclose(u, v)


# ------------------------------------------------------------------------------------------------
# The patches and the pin

def test_every_patch_anchor_is_found_once_and_the_files_compile():
    for rel, specs in S.PATCH_SPECS.items():
        repo = (ROOT / rel).read_text(encoding="utf-8")
        text = S.patched_text(repo, rel)
        assert text == repo                                   # since 10 Oct 2026 the repository's builders carry it
        compile(text, rel, "exec")
        assert text.count("level_layer as _LLE") == 1
        for _, repl in specs:
            assert text.count(repl) == 1
        dec = S.unpatched_text(text, rel)                     # the decided builder, recovered
        compile(dec, rel, "exec")
        assert "_LLE" not in dec and all(dec.count(anchor) == 1 for anchor, _ in specs)
        assert S.patched_text(dec, rel) == text               # and patched again: the integrated builder


def test_the_integrated_builders_equal_the_validated_snapshot_comments_aside():
    """The code the study's G1 validated (system/arms/validated_src/, written under the sandbox tags) is the code the
    repository's builders now carry: the same text once the tags are mapped (system_sandbox.normalize) and the listed
    post-validation edits applied (system_sandbox.POST_VALIDATION: the 2027 fix of 10 Oct 2026), and nothing else."""
    from src.eda.lower_level_evidence import level_layer_ios as C2
    snap = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "arms" / "validated_src"
    if not snap.exists():
        pytest.skip("the validated snapshot is not in this tree")
    for rel in list(S.PATCH_SPECS) + list(C2.PATCHES):
        assert (ROOT / rel).read_text(encoding="utf-8") == S.validated_now((snap / rel).read_text(encoding="utf-8"),
                                                                            rel), rel
    assert set(S.POST_VALIDATION) <= set(S.PATCH_SPECS) | set(C2.PATCHES)


def test_delta_levels_parse_as_a_writes_them():
    assert L.parse_levels("CH,CHQ") == frozenset({"CH", "CHQ"})
    assert L.parse_levels("none") == frozenset() and L.parse_levels("n/a") == frozenset() and L.parse_levels("") == frozenset()
    with pytest.raises(ValueError):
        L.parse_levels("CH,XX")


def test_build_plan_splits_lane_1_around_the_ios_part_only_when_needed():
    from src.eda.lower_level_evidence import system_arms as SA
    fam = {f: True for f in L.FAMILIES}
    off = {**fam, "ios": False, "ios_points_short": False}
    p = SA.lane_plan({"families": fam}, {"c2": {"applied": True}})
    assert p["ios_part"] and [n for n, _ in p["lane1b"]] == ["leakproof_frame", "elo_pieces", "elo_frames"]
    assert not SA.lane_plan({"families": off}, {"c2": {"applied": True}})["ios_part"]
    assert not SA.lane_plan({"families": fam}, {})["ios_part"]                  # no C2 patch: nothing to run
    cand = SA.lane_plan({"families": fam}, {"c2": {"applied": True}, "candidate_stage0": {"timing": True}})
    assert [n for n, _ in cand["lane0"]] == ["stage1_odds", "timing_features"] and not cand["ios_part"]
    cand = SA.lane_plan({"families": fam}, {"candidate_stage0": {"timing": False}})
    assert [n for n, _ in cand["lane0"]] == ["stage1_odds", "timeline", "timing_features"]


def test_a_candidate_stage0_without_ready_is_refused(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "data" / "studies").mkdir(parents=True)
    with pytest.raises(SystemExit):
        S.put_candidate_stage0(tmp_path, tmp_path / "C0_now")
    with pytest.raises(SystemExit):
        S.refuse(ROOT)                                                          # never the repository


def test_pin_replaces_stage_b_constants_and_records_equality(tmp_path, monkeypatch):
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    ref = {"chosen": [{"tour": t, "stat": s, "h1": "inf" if s == "rpw" else 26.0, "K1": 2.0, "tau": 0, "h3": 2.0,
                       "K3": 10.0, "improvement": 1.0, "rank_in_grid": 1, "settings": 3600}
                      for t in ("atp", "wta") for s in ("spw", "rpw", "tpw")]}
    pp = tmp_path / "pin.json"
    pp.write_text(json.dumps(ref), encoding="utf-8")
    config(tmp_path, st0, monkeypatch, pins={"stageB_adjperf": {"path": str(pp), "sha256": sha(pp)}})
    tuned = {(t, s): {"h1": 52.0, "K1": 2.0, "tau": 0, "h3": 2.0, "K3": 10.0} for t in ("atp", "wta")
             for s in ("spw", "rpw", "tpw")}
    out = L.pin("stageB_adjperf", tuned)
    assert out[("atp", "rpw")]["h1"] == float("inf") and out[("atp", "spw")]["h1"] == 26.0
    rec = [json.loads(x) for x in (tmp_path / "rec" / "layer_calls.jsonl").read_text().splitlines()]
    assert rec[-1]["hook"] == "pin" and rec[-1]["tuned_equals_reference"]["atp|spw"] is False


def test_g4_dose_judges_size_and_direction_across_the_dose_arms(tmp_path, monkeypatch):
    """G4 on synthetic frames: a change that grows with w and keeps its direction passes; one that shrinks fails."""
    from src.eda.lower_level_evidence import system_gates as G
    rng = np.random.default_rng(3)
    n = 400
    base = {"match_id": [f"m{i}" for i in range(n)], "tour": ["atp"] * n}
    effect = rng.normal(0, 1, n)
    ins = G.BOX_INPUTS
    ref = rng.normal(0, 1, (n, len(ins)))
    for arm, w in G.DOSE_ARMS:
        ww = {"fitted": 0.7}.get(w, w)
        cols = {f"in_{x}": ref[:, j] + ww * effect for j, x in enumerate(ins)}
        if arm == "SYS_w50":
            cols["in_points_52w"] = ref[:, 0] + 2.0 * effect           # bigger at 0.5 than at 1: not monotone
        d = tmp_path / arm
        d.mkdir()
        pd.DataFrame({**base, **cols}).to_parquet(d / "model_frame.parquet", index=False)
    monkeypatch.setattr(G, "ARMS", tmp_path)
    out, t = G.g4()
    assert out["inputs_judged"] == len(ins) and out["pass"] is False
    assert [f["input"] for f in out["failed"]] == ["points_52w"]
    assert np.allclose(t.loc[t["input"] == "ratings_iid", "SYS_over_w100"], 0.7)


def test_pins_return_the_reference_constants_only_when_the_config_names_them(tmp_path, monkeypatch):
    """level_pins (the NEW arms): off, every pin returns its input; with pin_constants, the reference's values, a record
    of the tuning's own choice, and a refused file whose hash differs."""
    from src.eda.lower_level_evidence import level_pins as P
    from src.eda.lower_level_evidence import system_new_arms as N
    rows = rows_frame()
    st0 = write_stage0(tmp_path, rows)
    ref = {"stage1_chosen": [{"tour": "atp", "rule": "ret", "k0": 600.0, "offset": 2.0, "shape": 0.6, "w": 0.3}],
           "offset_constants": {"atp": {"kd0": 80.0, "kd_off": 10.0, "kd_shape": 0.6}},
           "offset_surface_blind_constants": {"atp": {"kd0": 20.0, "kd_off": 40.0, "kd_shape": 0.8}},
           "stage3_chosen": {"atp": "{'var_serve': 0.02, 'var_return': 0.005, 'drift': 0.0002, 'start_serve': -0.2, "
                                    "'start_return': 0.0}"}}
    rp = tmp_path / "reference_constants.json"
    rp.write_text(json.dumps(ref), encoding="utf-8")
    k = {"k0": 400.0, "offset": 1.0, "shape": 0.5}
    assert P.stage1_k("atp", "ret", k) is k                                   # layer off: the input itself
    config(tmp_path, st0, monkeypatch)
    assert P.stage1_k("atp", "ret", k) is k                                   # layer on, no pin_constants
    P._REF.clear()
    config(tmp_path, st0, monkeypatch, pin_constants={"path": str(rp), "sha256": sha(rp)})
    assert P.stage1_k("atp", "ret", k) == {"k0": 600.0, "offset": 2.0, "shape": 0.6}
    assert P.stage1_w("atp", "ret", 0.2) == 0.3
    assert P.offset_kd("offset_surface_blind", "atp", {"kd0": 1.0, "kd_off": 1.0, "kd_shape": 1.0})["kd_off"] == 40.0
    s3 = P.stage3({"atp": {"var_serve": 0.01, "var_return": 0.005, "drift": 0.0, "start_serve": 0.0,
                           "start_return": 0.0}})
    assert s3["atp"]["var_serve"] == 0.02 and s3["atp"]["start_serve"] == -0.2
    recs = [json.loads(x) for x in (tmp_path / "rec" / "layer_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    pins = [r for r in recs if r.get("hook") == "pin_constants"]
    assert len(pins) == 4 and not any(r["tuned_equals_reference"] for r in pins)
    P._REF.clear()
    config(tmp_path, st0, monkeypatch, pin_constants={"path": str(rp), "sha256": "0" * 64})
    with pytest.raises(RuntimeError):
        P.stage1_k("atp", "ret", k)
    for rel in N.PIN_SPECS:                                                   # the pins apply on C1's text, once each
        t = N.pinned_text(rel)
        ast.parse(t)
        assert all(t.count(r) == 1 for _, r in N.PIN_SPECS[rel])
