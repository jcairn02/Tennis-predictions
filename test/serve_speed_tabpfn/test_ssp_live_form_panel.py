"""Offline tests of the live panel, the live 28-day form and the runner (no network). No match result is read."""
from __future__ import annotations

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

from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import availability as AV  # noqa: E402
from src.eda.serve_speed_tabpfn.live import common as LC  # noqa: E402
from src.eda.serve_speed_tabpfn.live import form as FM  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402
from src.ingest import speed_daily as SD  # noqa: E402

COLUMNS = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "adaptive" / "columns.parquet"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_sd_l_is_the_latency_runs_standardiser():
    assert FM.SD_L == 1.9496051535048338 and FM.HL_L == 28.0


def test_live_form_reproduces_the_backtest_column():
    """With the frozen panel and scenario D's release days, spd_L on a frame match's es equals the adaptive study's
    spd_L_D exactly (40 men's matches 2024-26)."""
    pan = P.load_panel(use_only=True).merge(AV.load(["match_id", "side", "release_D"]), on=["match_id", "side"])
    fk = P.load_frame_keys().merge(pd.read_parquet(COLUMNS, columns=["match_id", "spd_L_D"]), on="match_id")
    men = fk[fk["tour"].eq("atp") & fk["season"].between(2024, 2026) & fk["spd_L_D"].ne(0)].sample(40, random_state=3)
    rel = pan["release_D"].to_numpy()
    for r in men.itertuples():
        v = FM.spd_L(r.player_a_id, r.player_b_id, int(r.es), panel=pan, release=rel)
        assert abs(v - r.spd_L_D) < 1e-9, r.match_id


def test_spd_l_is_antisymmetric_clipped_and_zero_without_data():
    form = pd.DataFrame({"player_id": ["a", "b", "c"], "f_hat": [3.0, -1.0, 40.0]})
    ab = FM.spd_L_from_form(form, ["a"], ["b"])[0]
    assert abs(ab - 4.0 / FM.SD_L) < 1e-12 and FM.spd_L_from_form(form, ["b"], ["a"])[0] == -ab
    assert FM.spd_L_from_form(form, ["c"], ["b"])[0] == 4.0
    assert FM.spd_L_from_form(form, ["x"], ["y"])[0] == 0.0


def test_new_rows_follow_the_key_statistic_basis():
    lk = pd.DataFrame([{
        "match_id": "atp|2026-5014|R64|atp:1|atp:2", "side_p1": "B", "pid_p1": "atp:2", "pid_p2": "atp:1",
        "in_stage0": False, "level_s0": None, "round_s0": None, "qualifying_s0": None, "level_tml": "T1000",
        "round_tml": "R64", "qual_tml": False, "round": "R64", "year": 2026, "tid": "2026-5014", "event_id": "5014",
        "match_code": "MS040", "tdate": 20727.0, "es": 20732.0, "lf": 20733.0, "obs": 20732.0, "source": "infosys_atp_daily",
        "p1_spd1": 201.0, "p2_spd1": 190.0, "p1_first_in": 40.0, "p2_first_in": 8.0, "p1_first_total": 60.0,
        "p2_first_total": 20.0, "p1_spd2": 160.0, "p2_spd2": 150.0, "p1_max": 220.0, "p2_max": 210.0,
        "collected_on": "2026-10-08", "link_method": "tml"}])
    n = LP.new_rows(lk).set_index("side")
    assert n.loc["B", "player_id"] == "atp:2" and n.loc["B", "y"] == 200.5 and n.loc["B", "y_raw"] == 201.0
    assert n.loc["A", "y"] == 189.5 and n.loc["A", "n"] == 8 and not n.loc["A", "use"] and n.loc["A", "drop_reason"] == "low_n"
    assert (n["basis"] == "ks").all() and (n["release"] == LC.day_of("2026-10-08")).all()
    assert (n["release"] >= n["lf"] + 1).all() and set(n["family"]) == {"tour|M"}
    # Lead's rule (8 Oct 2026, the first live run): data in hand that the source reports COMPLETED count from the
    # collection day, even when the clock's cautious lf + 1 is later; a match NOT reported completed keeps lf + 1.
    early = lk.assign(lf=20734.0, es=20733.0, obs=20733.0)
    done = LP.new_rows(early.assign(match_completed=True))
    assert (done["release"] == LC.day_of("2026-10-08")).all()             # 20734, before lf + 1 = 20735
    open_ = LP.new_rows(early.assign(match_completed=False))
    assert (open_["release"] == 20735).all()                              # held back to lf + 1
    assert (LP.new_rows(early)["release"] == LC.day_of("2026-10-08")).all()   # no flag (ManTennisData): completed


def test_runner_offline(tmp_path):
    """The runner without network: stages, links, builds the live panel and the form; the frozen files are untouched;
    the collector reports itself skipped."""
    frozen = {p: sha(p) for p in (P.PANEL, P.FRAME_KEYS)}
    rec = SD.run(LC.day_of("2026-10-08"), tmp_path, mantd="skip", network=False)
    # without network the collector is skipped whatever the switch says (the real live/collector.json was enabled by
    # the lead on 8 Oct 2026, so the reported flag follows the config, not a fixed False)
    assert rec["collector"]["status"].startswith("skipped") and rec["collector"]["enabled"] is SD.AD.enabled()
    live = pd.read_parquet(tmp_path / LC.PANEL_LIVE.name)
    fr = LP.frozen_panel()        # the frozen panel without the audit's impossible records (decision 2026-10-08)
    head = live.iloc[:len(fr)][fr.columns]
    pd.testing.assert_frame_equal(head.reset_index(drop=True), fr.reset_index(drop=True), check_dtype=False)
    assert not live.duplicated(["match_id", "side"]).any()
    # the clock's guard (never before the match surely finished, lf + 1) holds for the frozen rows and for live rows
    # not reported completed; a live row its source reports completed counts from the day it was collected
    # (live_panel.new_rows: "data in hand")
    done = live["live_source"].eq("daily") & live["match_completed"].fillna(False).astype(bool)
    assert (live.loc[~done, "release"] >= live.loc[~done, "lf"] + 1).all()
    assert (live.loc[done, "release"] == [LC.day_of(c) for c in live.loc[done, "collected_on"]]).all()
    form = pd.read_parquet(tmp_path / "speed_form_2026-10-08.parquet")
    assert len(form) > 1000 and set(form.columns) >= {"player_id", "f_hat", "f_sd", "L_hat", "last_reading"}
    assert (tmp_path / LC.RUNS.name).exists()
    assert {p: sha(p) for p in frozen} == frozen


def test_plan_only_sends_nothing_and_stages_nothing(tmp_path):
    rec = SD.run(LC.day_of("2026-10-08"), tmp_path, network=False, plan_only=True)
    assert "plan_requests" in rec["collector"] and not (tmp_path / "staging").exists()
    assert all(r[0] >= 2026 for r in rec["collector"]["plan"])


def test_live_history_drops_the_audits_impossible_records():
    """The live feed's history never uses a record of the audit's speed exclusions (a player-match left without a valid
    record keeps an unused row, as the panel does): the corrected copy, and the history the live panel reads (since
    8 Oct with the ATP backfill of 2018-21, docs/studies/infosys_atp_backfill/). The corrected copy differs from the
    study's frozen panel only on the player-matches that had one (plus the players' own-outlier flags); the backfilled
    history keeps every player-match of the corrected copy."""
    from src.eda.input_data_audit import corrections as K
    ex = pd.read_csv(K.SPEED_EXCLUSIONS, dtype=str, keep_default_na=False)
    corrected, live, frozen = pd.read_parquet(LP.CORRECTED), LP.frozen_panel(), P.load_panel(use_only=False)
    for fr in (corrected, live):
        used = fr[fr["use"]]
        chosen = set(zip(used["match_id"], used["side"], used["source"], used["source_key"].astype(str)))
        assert not chosen & set(zip(ex["match_id"], ex["side"], ex["source"], ex["source_key"]))
        left = fr[fr["drop_reason"].eq("audit_impossible")]
        assert len(left) and not left["use"].any()
    hit = set(zip(ex["match_id"], ex["side"]))
    a = frozen.set_index(["match_id", "side"]).sort_index()
    b = corrected.set_index(["match_id", "side"]).sort_index()
    cols = [c for c in a.columns if c != "flag_own_outlier"]
    moved = ~((a[cols] == b[cols]) | (a[cols].isna() & b[cols].isna())).all(axis=1)
    assert set(moved[moved].index) <= hit and len(corrected) == len(frozen)
    assert set(zip(corrected["match_id"], corrected["side"])) <= set(zip(live["match_id"], live["side"]))
