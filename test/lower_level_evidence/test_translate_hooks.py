"""Tests of the role-08 translation hooks (src/eda/lower_level_evidence/translate_hooks.py).

Synthetic data only: a planted level offset is recovered, the counting rules hold, the hooks are switched off without
the environment variable, translate only lower-level rows by the right offset, are linear in the scale, and refuse a
stored table that the build's own data does not reproduce.
Run: ./python.sh -m pytest test/lower_level_evidence/test_translate_hooks.py -q
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

from src.eda.lower_level_evidence import translate_hooks as H  # noqa: E402

MAP_LEVEL = {"MAIN": "T250", "TQ": "TQ", "GSQ": "GSQ", "CH": "CH", "CHQ": "CHQ", "ITF": "ITF", "ITFQ": "ITFQ",
             "TEAM": "TEAM"}


def synthetic(n_players=150, seasons=(2015, 2016), shift=0.5, buckets=("CH",), tours=("atp", "wta"), rows_each=4,
              seed=0, extra_year_shift=None):
    """Box rows: every player-season has rows_each rows at MAIN and at each bucket; z ~ N(0, 1) at MAIN and
    N(shift, 1) at the bucket (a planted offset). extra_year_shift: (year, value) rows with another shift."""
    rng = np.random.default_rng(seed)
    recs = []
    k = 0
    for t in tours:
        for p in range(n_players):
            for y in seasons:
                for b in ("MAIN",) + tuple(buckets):
                    for _ in range(rows_each):
                        mu = 0.0 if b == "MAIN" else shift
                        if extra_year_shift and y == extra_year_shift[0] and b != "MAIN":
                            mu = extra_year_shift[1]
                        recs.append({"match_id": f"m{k}", "tour": t, "player_id": f"{t}:{p}", "year": y, "bucket": b,
                                     "z": rng.normal(mu, 1.0)})
                        k += 1
    return pd.DataFrame(recs)


def write_stage0(tmp_path: Path, df: pd.DataFrame) -> Path:
    m = pd.DataFrame({"match_id": df["match_id"].to_numpy(), "map_level": df["bucket"].map(MAP_LEVEL).to_numpy()})
    m = m.drop_duplicates("match_id")
    p = tmp_path / "stage0_matches.parquet"
    m.to_parquet(p, index=False)
    return p


def write_config(tmp_path: Path, stage0: Path, scale=1.0, estimate=True, name="cfg.json") -> Path:
    cfg = {"forms_offsets": str(tmp_path / "forms_offsets.csv"), "rates_offsets": str(tmp_path / "rate_offsets.csv"),
           "record_dir": str(tmp_path / "rec"), "estimate_forms": estimate, "scale": scale,
           "stage0_matches": str(stage0)}
    p = tmp_path / name
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


def forms_table(df: pd.DataFrame, key=("tpw", "adjperf")) -> pd.DataFrame:
    Z = {key: df["z"].to_numpy()}
    return H.estimate_forms(Z, df["tour"].to_numpy(), df["player_id"].to_numpy(), df["year"].to_numpy(),
                            df["bucket"].to_numpy())


def test_planted_offset_is_recovered_with_counts_and_interval():
    df = synthetic(n_players=200, shift=0.5, buckets=("CH", "TQ"))
    t = forms_table(df)
    for tour in ("atp", "wta"):
        for b in ("CH", "TQ"):
            r = t[(t["tour"] == tour) & (t["bucket"] == b)].iloc[0]
            assert r["player_seasons"] == 400                  # 200 players x 2 seasons
            assert r["players"] == 200
            assert abs(r["estimate"] - 0.5) < 4 * r["se"]
            assert r["lo"] < 0.5 < r["hi"] or abs(r["estimate"] - 0.5) < 0.1
            assert r["source"] == "own tour" and r["value_used"] == r["estimate"]


def test_estimate_equals_a_brute_force_mean_of_season_differences():
    df = synthetic(n_players=120, shift=0.3, rows_each=3, seed=3)
    t = forms_table(df)
    for tour in ("atp", "wta"):
        g = df[df["tour"] == tour].groupby(["player_id", "year", "bucket"])["z"].mean().unstack("bucket")
        want = float((g["CH"] - g["MAIN"]).mean())
        got = t[(t["tour"] == tour) & (t["bucket"] == "CH")]["estimate"].iloc[0]
        assert got == pytest.approx(want, abs=1e-12)


def test_player_seasons_need_three_rows_at_each_level():
    df = synthetic(n_players=150, shift=0.4, rows_each=3, seed=1)
    # drop one CH row from every player-season of player 0..49 on the men's side: they no longer qualify
    drop = df[(df["tour"] == "atp") & (df["bucket"] == "CH") & df["player_id"].isin([f"atp:{i}" for i in range(50)])]
    drop = drop.groupby(["player_id", "year"]).head(1).index
    t = forms_table(df.drop(index=drop))
    r = t[(t["tour"] == "atp") & (t["bucket"] == "CH")].iloc[0]
    assert r["player_seasons"] == (150 - 50) * 2


def test_seasons_outside_2010_2018_never_enter():
    base = synthetic(n_players=120, seasons=(2016, 2017), shift=0.5, seed=2)
    late = synthetic(n_players=120, seasons=(2019, 2020), shift=3.0, seed=4)
    late["match_id"] = "late_" + late["match_id"]
    t0, t1 = forms_table(base), forms_table(pd.concat([base, late], ignore_index=True))
    a = t0[t0["bucket"] == "CH"]["estimate"].to_numpy()
    b = t1[t1["bucket"] == "CH"]["estimate"].to_numpy()
    assert np.allclose(a, b, rtol=0, atol=1e-12)


def test_fallback_to_both_tours_then_zero_and_the_placeholders():
    men = synthetic(n_players=80, shift=0.6, tours=("atp",), seed=5)          # 160 player-seasons
    women = synthetic(n_players=10, shift=0.2, tours=("wta",), seed=6)         # 20: under 100
    t = forms_table(pd.concat([men, women.assign(match_id="w" + women["match_id"])], ignore_index=True))
    w = t[(t["tour"] == "wta") & (t["bucket"] == "CH")].iloc[0]
    assert w["player_seasons"] == 20 and w["source"].startswith("both tours")
    assert w["value_used"] == pytest.approx(w["both_tours_estimate"])
    # GSQ has no rows at all: zero
    g = t[(t["tour"] == "atp") & (t["bucket"] == "GSQ")].iloc[0]
    assert g["value_used"] == 0.0 and g["source"].startswith("zero")
    # placeholders and zeros
    for tour in ("atp", "wta"):
        ch = t[(t["tour"] == tour) & (t["bucket"] == "CH")]["value_used"].iloc[0]
        itf = t[(t["tour"] == tour) & (t["bucket"] == "ITF")]["value_used"].iloc[0]
        assert itf == ch
        for b in ("MAIN", "TEAM"):
            assert t[(t["tour"] == tour) & (t["bucket"] == b)]["value_used"].iloc[0] == 0.0


def test_rate_offsets_pool_counts_within_the_season():
    rng = np.random.default_rng(7)
    recs = []
    k = 0
    for p in range(110):
        for b, rate in (("MAIN", 0.60), ("CH", 0.63)):
            for _ in range(3):
                d = int(rng.integers(40, 90))
                x = int(rng.binomial(d, rate))
                recs.append({"match_id": f"r{k}", "tour": "atp", "player_id": f"atp:{p}", "year": 2014, "bucket": b,
                             "x": x, "d": d})
                k += 1
    df = pd.DataFrame(recs)
    ok = np.ones(len(df), bool)
    t = H.estimate_rates({"spw": (df["x"].to_numpy(float), df["d"].to_numpy(float), ok)}, df["tour"].to_numpy(),
                         df["player_id"].to_numpy(), df["year"].to_numpy(), df["bucket"].to_numpy())
    g = df.groupby(["player_id", "bucket"])[["x", "d"]].sum()
    r = (g["x"] / g["d"]).unstack("bucket")
    want = float((r["CH"] - r["MAIN"]).mean())
    got = t[(t["tour"] == "atp") & (t["bucket"] == "CH")]["estimate"].iloc[0]
    assert got == pytest.approx(want, abs=1e-12)
    # rows not admitted (ok False) never count
    ok2 = ok.copy()
    ok2[df.index[df["bucket"] == "CH"][:30]] = False
    t2 = H.estimate_rates({"spw": (df["x"].to_numpy(float), df["d"].to_numpy(float), ok2)}, df["tour"].to_numpy(),
                          df["player_id"].to_numpy(), df["year"].to_numpy(), df["bucket"].to_numpy())
    assert t2[(t2["tour"] == "atp") & (t2["bucket"] == "CH")]["player_seasons"].iloc[0] == 100


def test_hooks_are_off_without_the_environment_variable(monkeypatch):
    monkeypatch.delenv(H.ENV, raising=False)
    rows = pd.DataFrame({"match_id": ["a", "a"], "tour": ["atp", "atp"], "year": [2015, 2015],
                         "player_id": ["x", "y"]})
    Z = {("tpw", "adjperf"): np.array([0.3, -0.3])}
    assert H.translate_forms(rows, np.array([0, 1]), Z) is Z
    x = np.array([10.0, 20.0])
    assert H.translate_counts(rows, "spw", x, np.array([30.0, 30.0]), np.array([True, True])) is x


def box_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"z": "z_tpw"})[["match_id", "tour", "year", "player_id", "bucket", "z_tpw"]]


def test_forms_hook_estimates_once_then_translates_only_lower_rows(tmp_path, monkeypatch):
    df = synthetic(n_players=120, shift=0.5, buckets=("CH", "TEAM"), seasons=(2010, 2018), seed=8)
    df.loc[df["bucket"] == "TEAM", "z"] = 0.25
    stage0 = write_stage0(tmp_path, df)
    cfg = write_config(tmp_path, stage0)
    monkeypatch.setenv(H.ENV, str(cfg))
    rows = box_rows(df)
    idx = np.arange(len(rows))
    z = df["z"].to_numpy().copy()
    z[5] = np.nan                                                         # a row without a value stays without one
    Z = {("tpw", "adjperf"): z, ("spw", "adjperf"): z.copy()}
    out = H.translate_forms(rows, idx, Z)
    assert (tmp_path / "forms_offsets.csv").exists() and (tmp_path / "rec" / "forms_z_untranslated.parquet").exists()
    t = pd.read_csv(tmp_path / "forms_offsets.csv")
    d_ch = {tour: t[(t["key"] == "adjperf|tpw") & (t["tour"] == tour) & (t["bucket"] == "CH")]["value_used"].iloc[0]
            for tour in ("atp", "wta")}
    b = df["bucket"].to_numpy()
    tour = df["tour"].to_numpy()
    want = z - np.where(b == "CH", np.where(tour == "atp", d_ch["atp"], d_ch["wta"]), 0.0)
    got = out[("tpw", "adjperf")]
    assert np.array_equal(np.isnan(got), np.isnan(want))
    assert np.allclose(got[np.isfinite(got)], want[np.isfinite(want)], rtol=0, atol=1e-15)
    assert np.array_equal(out[("spw", "adjperf")], Z[("spw", "adjperf")], equal_nan=True)   # not one of the 17
    main_team = np.isin(b, ["MAIN", "TEAM"]) & np.isfinite(z)
    assert np.array_equal(got[main_team], z[main_team])
    # a second full-history call verifies the stored table instead of re-writing it
    H.translate_forms(rows, idx, Z)
    calls = [json.loads(x) for x in (tmp_path / "rec" / "hook_calls.jsonl").read_text().splitlines()]
    assert [c["action"] for c in calls] == ["estimated", "verified"]


def test_forms_hook_is_linear_in_the_scale(tmp_path, monkeypatch):
    df = synthetic(n_players=110, shift=0.5, buckets=("CH", "GSQ"), seasons=(2010, 2018), seed=9)
    stage0 = write_stage0(tmp_path, df)
    rows, idx = box_rows(df), np.arange(len(df))
    Z = {("hold", "adjperf"): df["z"].to_numpy(), ("df", "adjdef"): -df["z"].to_numpy()}
    outs = {}
    for s in (1.0, 0.0, 0.5):
        monkeypatch.setenv(H.ENV, str(write_config(tmp_path, stage0, scale=s, name=f"cfg{s}.json")))
        outs[s] = H.translate_forms(rows, idx, Z)
    for k in Z:
        assert np.array_equal(outs[0.0][k], Z[k])
        assert np.allclose(outs[0.5][k], (outs[0.0][k] + outs[1.0][k]) / 2, rtol=0, atol=1e-14)
    # adjdef reads its own offsets: here the planted shift is negative
    t = pd.read_csv(tmp_path / "forms_offsets.csv")
    assert t[(t["key"] == "adjdef|df") & (t["bucket"] == "CH")]["value_used"].lt(0).all()


def test_forms_hook_refuses_a_table_this_build_does_not_reproduce(tmp_path, monkeypatch):
    df = synthetic(n_players=110, shift=0.5, seasons=(2010, 2018), seed=10)
    stage0 = write_stage0(tmp_path, df)
    monkeypatch.setenv(H.ENV, str(write_config(tmp_path, stage0)))
    rows, idx = box_rows(df), np.arange(len(df))
    H.translate_forms(rows, idx, {("tpw", "adjperf"): df["z"].to_numpy()})
    # the same z everywhere but at the Challenger rows: the stored offsets no longer match this build
    moved = df["z"].to_numpy() + np.where(df["bucket"].to_numpy() == "CH", 0.01, 0.0)
    with pytest.raises(RuntimeError):
        H.translate_forms(rows, idx, {("tpw", "adjperf"): moved})
    # a common shift of every row leaves the offsets (differences) as they were: verified, not refused
    H.translate_forms(rows, idx, {("tpw", "adjperf"): df["z"].to_numpy() + 0.01})


def test_forms_hook_on_a_slice_reads_and_never_estimates(tmp_path, monkeypatch):
    df = synthetic(n_players=110, shift=0.5, seasons=(2023, 2024), seed=11)
    stage0 = write_stage0(tmp_path, df)
    monkeypatch.setenv(H.ENV, str(write_config(tmp_path, stage0)))
    with pytest.raises(FileNotFoundError):
        H.translate_forms(box_rows(df), np.arange(len(df)), {("tpw", "adjperf"): df["z"].to_numpy()})


def test_counts_hook_translates_spw_and_rpw_lower_rows_only(tmp_path, monkeypatch):
    df = synthetic(n_players=110, shift=0.5, buckets=("CH",), seasons=(2022,), seed=12)   # a slice: no verification
    stage0 = write_stage0(tmp_path, df)
    pd.DataFrame([{"kind": "rates", "key": k, "tour": t, "bucket": b,
                   "value_used": (0.02 if k == "spw" else 0.04) if b == "CH" else 0.0}
                  for k in ("spw", "rpw") for t in ("atp", "wta") for b in H.BUCKETS]).to_csv(tmp_path / "rate_offsets.csv",
                                                                                            index=False)
    monkeypatch.setenv(H.ENV, str(write_config(tmp_path, stage0, scale=1.0)))
    rows = df[["match_id", "tour", "year", "player_id"]]
    x = np.full(len(df), 30.0)
    d = np.full(len(df), 50.0)
    ok = np.ones(len(df), bool)
    ok[:3] = False
    ch = (df["bucket"] == "CH").to_numpy()
    got = H.translate_counts(rows, "spw", x, d, ok)
    assert np.allclose(got, np.where(ch & ok, 30.0 - 50.0 * 0.02, 30.0))
    got_r = H.translate_counts(rows, "rpw", x, d, ok)
    assert np.allclose(got_r, np.where(ch & ok, 30.0 - 50.0 * 0.04, 30.0))
    assert H.translate_counts(rows, "hold", x, d, ok) is x
