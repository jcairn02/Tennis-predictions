"""Tests of the adaptive-memory columns (adaptive/plan.md; src/eda/serve_speed_tabpfn/adaptive/columns.py).

Run: ./python.sh -m pytest test/serve_speed_tabpfn/test_ssp_adaptive_columns.py -q
No match result, outcome or price is read anywhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import columns as C  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import availability as AV  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import features_latency as FL  # noqa: E402

META = json.loads(C.META.read_text(encoding="utf-8")) if C.META.exists() else None
pytestmark = pytest.mark.skipif(META is None, reason="adaptive columns not built yet")


@pytest.fixture(scope="module")
def built():
    c = pd.read_parquet(C.COLUMNS)
    keys = P.load_frame_keys()
    return {"c": c, "keys": keys}


# ------------------------------------------------------------------------------------------------ the build
def test_ssp_adapt_shape_and_never_nan(built):
    c, keys = built["c"], built["keys"]
    assert len(c) == 63737 and c["match_id"].is_unique and (c["match_id"].to_numpy() == keys["match_id"].to_numpy()).all()
    for s in META["scenarios"]:
        for col in (f"spd_T_{s}", f"spd_L_{s}", f"late_a_{s}", f"late_b_{s}", f"mode_{s}"):
            assert col in c.columns and c[col].notna().all(), col
        assert (c[f"spd_T_{s}"].abs() <= 4).all() and (c[f"spd_L_{s}"].abs() <= 4).all()
        assert set(c[f"mode_{s}"].unique()) <= {"T", "L"}
        assert ((c[f"mode_{s}"] == "L") == (c[f"late_a_{s}"] | c[f"late_b_{s}"])).all()


def test_ssp_adapt_required_equalities(built):
    c = built["c"].set_index("match_id")
    spd_f = pd.read_parquet(F.FEATURES, columns=["match_id", "spd_f"]).set_index("match_id")["spd_f"]
    b_m1 = pd.read_parquet(FL.VARIANTS, columns=["match_id", "spd_B_M1"]).set_index("match_id")["spd_B_M1"]
    assert (c["spd_T_A"].to_numpy() == spd_f.reindex(c.index).to_numpy()).all()
    assert (c["spd_L_B"].to_numpy() == b_m1.reindex(c.index).to_numpy()).all()
    assert C.S_F == json.loads(F.META.read_text(encoding="utf-8"))["s_f"]
    assert C.SD_L == json.loads(FL.META.read_text(encoding="utf-8"))["standardisation_sd_km_h"]["B_M1"]


def test_ssp_adapt_no_side_late_under_A(built):
    c = built["c"]
    assert not c["late_a_A"].any() and not c["late_b_A"].any() and (c["mode_A"] == "T").all()


def test_ssp_adapt_women_zero_and_timely(built):
    c, keys = built["c"], built["keys"]
    w = keys["tour"].eq("wta").to_numpy()
    for s in META["scenarios"]:
        assert (c.loc[w, f"spd_T_{s}"] == 0).all() and (c.loc[w, f"spd_L_{s}"] == 0).all()
        assert not c.loc[w, f"late_a_{s}"].any() and (c.loc[w, f"mode_{s}"] == "T").all()


def test_ssp_adapt_flags_match_release_days(built):
    """The stored flags equal the rule recomputed from the stored release days on 3,000 men's sides (B and D)."""
    p = FL.load_panel()
    rt = C.release_table(p)
    keys = built["keys"]
    t = F.side_targets(keys)
    tm = t[t["tour"].eq("atp")].reset_index(drop=True)
    sub = tm.sample(3000, random_state=5).reset_index(drop=True)
    c = built["c"].set_index("match_id")
    for s in ("B", "D"):
        got = C.late_flags(p, sub, rt[s].to_numpy(np.int64))
        want = np.where(sub["side"].eq("A"), c.loc[sub["match_id"], f"late_a_{s}"].to_numpy(),
                        c.loc[sub["match_id"], f"late_b_{s}"].to_numpy())
        assert (got == want).all(), s


def test_ssp_adapt_flip_antisymmetry(built):
    p = FL.load_panel()
    rt = C.release_table(p)
    keys = built["keys"]
    k = keys[keys["tour"].eq("atp") & keys["season"].ge(2023)].sample(300, random_state=8).reset_index(drop=True)
    flip = k.copy()
    flip["player_a_id"], flip["player_b_id"] = k["player_b_id"].to_numpy(), k["player_a_id"].to_numpy()
    out = {}
    for lab, kk in (("orig", k), ("flip", flip)):
        t = F.side_targets(kk)
        out[lab] = C.build_scenario(p, kk, t, rt, "D")["cols"]
    o, f = out["orig"], out["flip"]
    for col in ("spd_T_D", "spd_L_D"):
        assert (f[col].to_numpy() == -o[col].to_numpy()).all()
    assert (f["late_a_D"].to_numpy() == o["late_b_D"].to_numpy()).all()
    assert (f["late_b_D"].to_numpy() == o["late_a_D"].to_numpy()).all()
    assert (f["mode_D"].to_numpy() == o["mode_D"].to_numpy()).all()
    stored = built["c"].set_index("match_id").loc[k["match_id"]]
    assert (stored["spd_T_D"].to_numpy() == o["spd_T_D"].to_numpy()).all()
    assert (stored["mode_D"].to_numpy() == o["mode_D"].to_numpy()).all()


def test_ssp_adapt_probe_b_record():
    pr = META["probes"].get("D")
    assert pr is not None and pr["pass"] and META["probes_pass"]
    assert pr["moved"] == 0 and pr["leaky_columns_moved"] > 0 and pr["leaky_flag_moved"] > 0 and pr["days"] >= 15
    assert {"spd_T_D", "spd_L_D", "late_a_D", "late_b_D", "mode_D"} == set(pr["values_checked"])


# ------------------------------------------------------------------------------------------------ the rule, by hand
def _rows(rows: list[dict]) -> pd.DataFrame:
    base = {"player_id": "x", "tournament_id": "e1", "round_order": 12, "tdate": 100, "lf": 0, "obs": 0}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_ssp_adapt_late_rule_by_hand():
    es = 200
    t = pd.DataFrame({"player_id": ["x"], "tdate": [190], "tournament_id": ["e9"], "round_order": [11], "es": [es]})

    def late(row, rel):
        return bool(C.late_flags(_rows([row]), t, np.array([rel]))[0])

    ok = {"tdate": 180, "lf": es - 2, "obs": es - 2}
    assert late(ok, es + 1)                                          # pending, finished two days ago: late
    assert not late(ok, es)                                          # in hand at es: not late
    assert not late({**ok, "lf": es - 1, "obs": es - 1}, es + 5)     # finished yesterday: the 1-day grace
    assert late({**ok, "obs": es - 14}, es + 1)                      # 14 days back: inside the window
    assert not late({**ok, "obs": es - 15}, es + 1)                  # 15 days back: outside
    assert not late({**ok, "player_id": "y"}, es + 1)                # another player's match
    # own order: the same event at a later or equal round is not earlier; an earlier round is
    same_ev = {**ok, "tdate": 190, "tournament_id": "e9"}
    assert not late({**same_ev, "round_order": 11}, es + 1)
    assert not late({**same_ev, "round_order": 12}, es + 1)
    assert late({**same_ev, "round_order": 10}, es + 1)
    # an untimed event has no panel row, so nothing can make the player late
    assert not C.late_flags(_rows([])[:0].reindex(columns=list(ok) + ["player_id", "tournament_id", "round_order"]),
                            t, np.array([], float)).any()


def test_ssp_adapt_live_rule_by_hand():
    """Live: watermarks instead of release days. Player x's recent matches at day now = 300 (a Tuesday):
       m1  tour event (ManTennisData), finished day 296, not yet published -> outstanding
       m2  Barcelona-like event with no speed source -> never late
       m3  finished yesterday (299) -> the 1-day grace
       m4  Slam, its feed collected after the event -> outstanding but 20 days old -> outside the window
    and player y, whose m5 speed is already in hand."""
    now = 300
    rows = pd.DataFrame([
        {"player_id": "x", "match_id": "t_x", "tdate": 301, "tournament_id": "next", "round_order": 11, "target": True,
         "lf": np.nan, "obs": np.nan, "source": ""},
        {"player_id": "y", "match_id": "t_y", "tdate": 301, "tournament_id": "next", "round_order": 11, "target": True,
         "lf": np.nan, "obs": np.nan, "source": ""},
        {"player_id": "x", "match_id": "m1", "tdate": 294, "tournament_id": "e1", "round_order": 14, "target": False,
         "lf": 296, "obs": 296, "source": "mantd"},
        {"player_id": "x", "match_id": "m2", "tdate": 294, "tournament_id": "e2", "round_order": 12, "target": False,
         "lf": 297, "obs": 297, "source": ""},
        {"player_id": "x", "match_id": "m3", "tdate": 294, "tournament_id": "e3", "round_order": 13, "target": False,
         "lf": 299, "obs": 299, "source": "daily"},
        {"player_id": "x", "match_id": "m4", "tdate": 270, "tournament_id": "slam", "round_order": 16, "target": False,
         "lf": 280, "obs": 280, "source": "slam_feed"},
        {"player_id": "y", "match_id": "m5", "tdate": 294, "tournament_id": "e1", "round_order": 13, "target": False,
         "lf": 296, "obs": 296, "source": "mantd"},
    ])
    wm = {"mantd": AV.mantd_watermark(298), "daily": AV.daily_watermark(now), "slam_feed": AV.slam_feed_watermark(260)}
    assert wm["mantd"] < 296                                 # the last commit (Sunday 298) delivered up to Friday 289
    hand = pd.DataFrame({"match_id": ["m5"], "player_id": ["y"]})
    got = C.late_flags_live(rows, hand, wm, now)
    assert got.to_dict() == {0: True, 1: False}
    # m1 delivered (watermark past its day) -> x is no longer late
    wm2 = dict(wm, mantd=296)
    assert C.late_flags_live(rows, hand, wm2, now).to_dict() == {0: False, 1: False}
    # m3 outside the grace (now = 301) with the daily source behind (watermark 298) -> late again
    assert C.late_flags_live(rows, hand, dict(wm2, daily=298), 301).to_dict() == {0: True, 1: False}
    # m4 inside the window at now = 290 (its Slam feed still pending) -> late; m2 never matters
    early = rows.copy()
    early.loc[early["target"], "tdate"] = 291
    early = early[early["match_id"].isin(["t_x", "t_y", "m2", "m4"])]
    assert C.late_flags_live(early, hand, wm, 290).to_dict() == {0: True, 1: False}


def test_ssp_adapt_live_equals_backtest_rule():
    """With watermarks set so that 'outstanding' == release > now, the live and backtest flags agree."""
    rng = np.random.default_rng(2)
    n = 400
    h = pd.DataFrame({"player_id": rng.choice(list("abcdefgh"), n), "match_id": [f"m{i}" for i in range(n)],
                      "tdate": rng.integers(100, 200, n), "tournament_id": rng.choice(["e1", "e2", "e3"], n),
                      "round_order": rng.integers(1, 17, n), "target": False})
    h["lf"] = h["tdate"] + rng.integers(0, 12, n)
    h["obs"] = h["lf"] - rng.integers(0, 2, n)
    rel = h["lf"] + 1 + rng.integers(0, 15, n)
    t = pd.DataFrame({"player_id": list("abcdefgh"), "match_id": [f"t{i}" for i in range(8)], "tdate": 205,
                      "tournament_id": "tt", "round_order": 11, "target": True, "lf": np.nan, "obs": np.nan})
    for now in (205, 210, 214):
        back = C.late_flags(h, t.assign(es=now), rel.to_numpy())
        # live: one source per match whose watermark is just below its lf iff it is not released by now
        src = [f"s{i}" for i in range(n)]
        wm = {s: (lf - 1 if r > now else lf) for s, lf, r in zip(src, h["lf"], rel)}
        frame = pd.concat([t.assign(source=""), h.assign(source=src)], ignore_index=True)
        live = C.late_flags_live(frame, pd.DataFrame({"match_id": [], "player_id": []}), wm, now)
        assert (live.to_numpy() == back).all(), now
