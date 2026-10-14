"""Tests of the history check (src/eda/current_best_model/history.py): the template keeps the reference's matches and
takes only the matches played from the freeze on, from the feeds that fed it; a reference match the feed was still
publishing at the freeze may be completed, corrected or dropped (the owner, 8 Oct 2026).

Since 9 Oct 2026 (the owner narrowed the rule to lower-level data): any other LOWER-LEVEL change (qualifying,
Challengers, ITF, or an unknown level) is a candidate and refuses a template build; a MAIN-TOUR change (the main draws of
the Slams, Finals, 1000s, 500s, 250s, and team events) is listed under allowed_main_tour but does not refuse it. The
all-level counts (new_past, dropped, revised) keep their meaning.

Since 13 Oct 2026 (the owner; docs/decisions/2026-10-13-tml-lower-level-revisions.md): Tennis My Life's own lower-level
corrections, drops and backfills (source "tml", at a tour, level and qualifying flag its rows held in the reference) are
listed under tml_lower and do not refuse a build. Other sources' lower-level changes, Tennis My Life at a level it never
fed, and a candidate's box layers on a Tennis My Life row stay gated.

Run: ./python.sh -m pytest test/current_best_model -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import history as H  # noqa: E402


def match(mid, source="tml", tour="atp", level="CH", date="2026-09-01", score="6-4 6-4"):
    return {"match_id": mid, "source": source, "tour": tour, "map_level": level, "year": int(date[:4]),
            "level": level, "qualifying": False, "round": "R32", "surface": "Hard", "indoor": False, "best_of": 3,
            "tournament_id": f"{date[:4]}-1", "tournament_date": pd.Timestamp(date), "status": "completed",
            "score": score, "minutes": 90.0, "format": "standard", "has_box": True, "player_a_id": "a",
            "player_b_id": "b", "a_won": True}


def players(mid, ace=5):
    base = {"match_id": mid, "rank": 100.0, "rank_points": 500.0, "age": 25.0, "df": 2.0, "svpt": 60.0,
            "first_in": 40.0, "first_won": 30.0, "second_won": 10.0, "sv_gms": 10.0, "bp_saved": 3.0, "bp_faced": 4.0,
            "has_box": True}
    return [{**base, "side": "a", "player_id": "a", "opponent_id": "b", "won": True, "ace": float(ace)},
            {**base, "side": "b", "player_id": "b", "opponent_id": "a", "won": False, "ace": 3.0}]


def write(folder: Path, ms: list[dict], ps: list[dict]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(ms).to_parquet(folder / "stage0_matches.parquet", index=False)
    pd.DataFrame(ps).to_parquet(folder / "stage0_match_players.parquet", index=False)
    return folder


@pytest.fixture
def ref(tmp_path):
    ms = [match("m1", date="2022-05-01", source="sackmann"), match("m2", date="2026-09-20"),
          match("m3", date="2026-10-05", level="T1000")]
    ps = sum((players(m["match_id"]) for m in ms), [])
    return write(tmp_path / "ref", ms, ps), ms, ps


def run(tmp_path, ref, ms, ps, timing=None, ref_timing=None):
    live = write(tmp_path / "live", ms, ps)
    return H.check(live, timing=timing, ref_stage0=ref[0], ref_timing=ref_timing)


def day(date: str) -> float:
    return float((pd.Timestamp(date) - H.EPOCH).days)


def timeline(path: Path, windows: dict[str, tuple[str, str]]) -> Path:
    """A timing.parquet holding each match's earliest start and latest finish."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"match_id": k, "es": day(a), "lf": day(b)} for k, (a, b) in windows.items()]).to_parquet(path)
    return path


def without_box(ps: list[dict], mid: str) -> list[dict]:
    out = [dict(r) for r in ps]
    for r in out:
        if r["match_id"] == mid:
            r.update({c: None for c in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms",
                                        "bp_saved", "bp_faced")}, has_box=False)
    return out


def test_identical_history_lets_the_template_build(tmp_path, ref):
    res = run(tmp_path, ref, ref[1], ref[2])
    assert res["template_ok"] and res["future"]["matches"] == res["new_past"]["matches"] == 0


def test_row_order_does_not_matter(tmp_path, ref):
    res = run(tmp_path, ref, ref[1][::-1], ref[2][::-1])
    assert res["template_ok"] and res["revised"]["matches"] == 0


def test_a_future_match_from_a_feeding_source_is_an_update(tmp_path, ref):
    ms = ref[1] + [match("m4", date="2026-10-12")]                       # tml / atp / CH fed the reference lately
    res = run(tmp_path, ref, ms, ref[2] + players("m4"))
    assert res["template_ok"] and res["future"]["matches"] == 1


def test_a_lower_level_backfill_is_new_history(tmp_path, ref):
    ms = ref[1] + [match("m5", date="2022-03-07", source="tennislive", level="ITF")]
    res = run(tmp_path, ref, ms, ref[2] + players("m5"))
    assert not res["template_ok"] and res["new_past"]["matches"] == 1
    assert res["new_past"]["by"][0]["source"] == "tennislive" and res["new_past"]["by"][0]["map_level"] == "ITF"


def test_a_future_match_from_a_new_source_is_not_an_update(tmp_path, ref):
    ms = ref[1] + [match("m6", date="2026-10-12", source="itf_live", level="ITF")]
    res = run(tmp_path, ref, ms, ref[2] + players("m6"))
    assert not res["template_ok"] and res["new_past"]["matches"] == 1 and res["future"]["matches"] == 0


def test_a_late_result_of_a_past_date_is_new_history(tmp_path, ref):
    ms = ref[1] + [match("m7", date="2025-06-01")]                       # same feed, but long before the freeze
    res = run(tmp_path, ref, ms, ref[2] + players("m7"))
    assert res["new_past"]["matches"] == 1
    # Tennis My Life's own Challenger backfill: listed under tml_lower, allowed since 13 Oct 2026
    assert res["tml_lower"]["new_past"]["examples"] == ["m7"] and res["gated"]["new_past"]["matches"] == 0
    assert res["template_ok"]


def test_a_revised_box_score_is_caught(tmp_path, ref):
    ps = [dict(r) for r in ref[2]]
    ps[0]["ace"] = 9.0                                                   # m1, player a
    res = run(tmp_path, ref, ref[1], ps)
    assert not res["template_ok"] and res["revised"]["examples"] == ["m1"]


def test_a_revised_score_is_caught(tmp_path, ref):
    ms = [dict(r) for r in ref[1]]
    ms[1]["score"] = "7-6 6-4"
    res = run(tmp_path, ref, ms, ref[2])
    assert res["revised"]["examples"] == ["m2"]
    # m2 is Tennis My Life's own Challenger: its correction is listed under tml_lower, allowed since 13 Oct 2026
    assert res["tml_lower"]["revised"]["examples"] == ["m2"] and res["template_ok"]
    ms = [dict(r) for r in ref[1]]
    ms[0]["score"] = "7-6 6-4"                                           # m1, a Sackmann row: still refused
    res = run(tmp_path, ref, ms, ref[2])
    assert not res["template_ok"] and res["gated"]["revised"]["examples"] == ["m1"]


def test_a_dropped_match_is_caught(tmp_path, ref):
    res = run(tmp_path, ref, ref[1][1:], ref[2][2:])
    assert not res["template_ok"] and res["dropped"]["examples"] == ["m1"]


# A reference match the feed was still publishing at the freeze (played from FREEZE - GRACE_DAYS on) may change.

def test_a_box_score_completed_on_a_recent_match_is_an_update(tmp_path):
    ms = [match("m1", date="2022-05-01", source="sackmann"), match("m2", date="2026-09-20"),
          match("m3", date="2026-10-05", level="T1000")]
    ps = sum((players(m["match_id"]) for m in ms), [])
    held = [dict(r, has_box=False) if r["match_id"] == "m3" else r for r in ms]
    ref = (write(tmp_path / "ref", held, without_box(ps, "m3")), held, without_box(ps, "m3"))
    res = run(tmp_path, ref, ms, ps)                                    # the feed now gives m3's box score
    assert res["template_ok"] and res["updated"]["revised"] == 1 and res["updated"]["examples"] == ["m3"]
    assert res["revised"]["matches"] == 0


def test_a_recent_match_corrected_is_an_update(tmp_path, ref):
    ms = [dict(r) for r in ref[1]]
    ms[2]["score"] = "7-6 6-4"                                           # m3, played 5 Oct
    res = run(tmp_path, ref, ms, ref[2])
    assert res["template_ok"] and res["updated"]["revised"] == 1 and res["revised"]["matches"] == 0


def test_a_recent_match_dropped_is_an_update(tmp_path, ref):
    res = run(tmp_path, ref, ref[1][:2], ref[2][:4])                    # m3 gone
    assert res["template_ok"] and res["updated"]["dropped"] == 1 and res["dropped"]["matches"] == 0


def test_a_recent_match_taken_over_by_another_source_is_caught(tmp_path, ref):
    ms = [dict(r) for r in ref[1]]
    ms[2]["source"] = "wta_api"
    ps = [dict(r) for r in ref[2]]
    ps[4]["ace"] = 9.0                                                   # m3's box score, now from a feed that never fed it
    res = run(tmp_path, ref, ms, ps)
    assert res["revised"]["examples"] == ["m3"] and res["updated"]["matches"] == 0
    # m3 is a 1000's main-draw match: since 9 Oct 2026 it is listed, not refused
    assert res["allowed_main_tour"]["revised"]["examples"] == ["m3"] and res["template_ok"]


def test_a_recent_lower_level_match_taken_over_by_another_source_is_refused(tmp_path):
    ms = [match("m2", date="2026-09-20"), match("m10", date="2026-10-06")]           # m10: a Challenger at the freeze
    ps = sum((players(m["match_id"]) for m in ms), [])
    ref = (write(tmp_path / "ref", ms, ps), ms, ps)
    live = [dict(r, source="wta_api") if r["match_id"] == "m10" else r for r in ms]
    ps2 = [dict(r, ace=9.0) if (r["match_id"] == "m10" and r["side"] == "a") else r for r in ps]
    res = run(tmp_path, ref, live, ps2)
    assert not res["template_ok"] and res["gated"]["revised"]["examples"] == ["m10"]


def test_a_reference_match_is_placed_by_the_references_timeline(tmp_path):
    # both of a 1000's matches began on 30 Sep; m4's window reaches 7 Oct, m5's closed on 3 Oct
    ms = [match("m2", date="2026-09-20"), match("m4", date="2026-09-30", level="T1000"),
          match("m5", date="2026-09-30", level="T1000")]
    ps = sum((players(m["match_id"]) for m in ms), [])
    ref = (write(tmp_path / "ref", ms, ps), ms, ps)
    ref_timing = timeline(tmp_path / "ref_timing" / "timing.parquet",
                          {"m4": ("2026-10-02", "2026-10-07"), "m5": ("2026-10-01", "2026-10-03")})
    live = [dict(r, score="7-6 6-4") if r["match_id"] in ("m4", "m5") else r for r in ms]
    late = timeline(tmp_path / "live_timing" / "timing.parquet",             # a revision cannot move a match in
                    {"m4": ("2026-10-06", "2026-10-07"), "m5": ("2026-10-06", "2026-10-07")})
    res = run(tmp_path, ref, live, ps, timing=late, ref_timing=ref_timing)
    assert res["updated"]["examples"] == ["m4"] and res["revised"]["examples"] == ["m5"]
    # m5 is a 1000's main-draw match: since 9 Oct 2026 its revision is listed, not refused
    assert res["allowed_main_tour"]["revised"]["examples"] == ["m5"] and res["template_ok"]


def test_a_new_match_whose_window_reaches_the_grace_days_is_an_update(tmp_path, ref):
    # an undated 1000's next round: its window opens before the grace days (as Shanghai 2026's did) but reaches them
    ms = ref[1] + [match("m8", date="2026-10-01", level="T1000"), match("m9", date="2026-09-25", level="T1000")]
    t = timeline(tmp_path / "live_timing" / "timing.parquet",
                 {"m8": ("2026-10-03", "2026-10-12"), "m9": ("2026-09-26", "2026-10-02")})
    res = run(tmp_path, ref, ms, ref[2] + players("m8") + players("m9"), timing=t)
    assert res["future"]["matches"] == 1 and res["new_past"]["examples"] == ["m9"]
    # m9 is a 1000's main-draw match: since 9 Oct 2026 it is listed, not refused
    assert res["allowed_main_tour"]["new_past"]["examples"] == ["m9"] and res["template_ok"]


# Since 9 Oct 2026: main-tour changes are listed but allowed; lower-level changes are refused.

@pytest.fixture
def main_ref(tmp_path):
    ms = [match("c1", date="2023-04-10"), match("t1", date="2023-06-01", level="T250"),
          match("g1", date="2023-05-28", level="GS"), match("d1", date="2023-09-15", level="TEAM")]
    ps = sum((players(m["match_id"]) for m in ms), [])
    return write(tmp_path / "ref", ms, ps), ms, ps


def test_a_main_tour_correction_is_listed_but_allowed(tmp_path, main_ref):
    ps = [dict(r, ace=9.0) if (r["match_id"] == "t1" and r["side"] == "a") else r for r in main_ref[2]]
    res = run(tmp_path, main_ref, main_ref[1], ps)
    assert res["template_ok"] and res["revised"]["matches"] == 1
    assert res["allowed_main_tour"]["revised"]["examples"] == ["t1"] and res["gated"]["revised"]["matches"] == 0


def test_a_main_tour_backfill_from_a_new_source_is_allowed(tmp_path, main_ref):
    ms = main_ref[1] + [match("g2", date="2023-05-30", source="rg_official", level="GS")]
    res = run(tmp_path, main_ref, ms, main_ref[2] + players("g2"))
    assert res["template_ok"] and res["new_past"]["matches"] == 1
    assert res["allowed_main_tour"]["new_past"]["by"][0]["source"] == "rg_official"


def test_a_dropped_main_tour_match_is_listed_but_allowed(tmp_path, main_ref):
    ms = [m for m in main_ref[1] if m["match_id"] != "g1"]
    ps = [r for r in main_ref[2] if r["match_id"] != "g1"]
    res = run(tmp_path, main_ref, ms, ps)
    assert res["template_ok"] and res["allowed_main_tour"]["dropped"]["examples"] == ["g1"]


def test_team_events_count_as_main_tour(tmp_path, main_ref):
    ms = [dict(r, score="7-5 6-4") if r["match_id"] == "d1" else r for r in main_ref[1]]
    res = run(tmp_path, main_ref, ms, main_ref[2])
    assert res["template_ok"] and res["allowed_main_tour"]["revised"]["examples"] == ["d1"]


def test_qualifying_is_gated(tmp_path, main_ref):
    q = dict(match("q1", date="2023-05-25", level="GS"), map_level="GSQ", qualifying=True)
    res = run(tmp_path, main_ref, main_ref[1] + [q], main_ref[2] + players("q1"))
    assert not res["template_ok"] and res["gated"]["new_past"]["examples"] == ["q1"]
    # a qualifying match filed under a main-tour map_level is still gated, by its qualifying flag
    q2 = dict(match("q2", date="2023-05-26", level="GS"), qualifying=True)
    res = run(tmp_path, main_ref, main_ref[1] + [q2], main_ref[2] + players("q2"))
    assert not res["template_ok"] and res["gated"]["new_past"]["examples"] == ["q2"]


def test_an_unknown_level_is_gated(tmp_path, main_ref):
    ms = main_ref[1] + [match("u1", date="2023-03-01", source="api_tennis", level="UTR")]
    res = run(tmp_path, main_ref, ms, main_ref[2] + players("u1"))
    assert not res["template_ok"] and res["gated"]["new_past"]["examples"] == ["u1"]


def test_mixed_changes_split_and_the_lower_level_part_refuses(tmp_path, main_ref):
    ps = [dict(r, ace=9.0) if (r["match_id"] == "t1" and r["side"] == "a") else r for r in main_ref[2]]
    ms = main_ref[1] + [match("i1", date="2022-03-07", source="tennislive", level="ITF")]
    res = run(tmp_path, main_ref, ms, ps + players("i1"))
    assert not res["template_ok"]
    assert res["allowed_main_tour"]["revised"]["matches"] == 1 and res["gated"]["new_past"]["matches"] == 1
    assert res["revised"]["matches"] == 1 and res["new_past"]["matches"] == 1          # all-level counts unchanged
    line = H.summary_line(res)
    assert "main-tour changes 1" in line and "lower-level new past 1" in line and "refused" in line


# Since 13 Oct 2026: Tennis My Life's own lower-level changes are listed under tml_lower and allowed.

def test_tml_lower_level_corrections_and_backfills_are_listed_and_allowed(tmp_path, ref):
    ms = [dict(r, score="7-6 6-4") if r["match_id"] == "m2" else r for r in ref[1]]    # m2: a tml Challenger, 20 Sep
    ms = ms + [match("m11", date="2024-05-01")]                                      # a tml Challenger backfill
    res = run(tmp_path, ref, ms, ref[2] + players("m11"))
    assert res["template_ok"]
    assert res["tml_lower"]["revised"]["examples"] == ["m2"] and res["tml_lower"]["new_past"]["examples"] == ["m11"]
    assert res["gated"]["revised"]["matches"] == res["gated"]["new_past"]["matches"] == 0
    assert res["revised"]["matches"] == 1 and res["new_past"]["matches"] == 1          # all-level counts unchanged
    line = H.summary_line(res)
    assert "Tennis My Life's own lower-level changes 2" in line and "the template may be built" in line


def test_a_dropped_tml_lower_level_match_is_allowed_but_a_sackmann_one_is_not(tmp_path):
    ms = [match("m1", date="2022-05-01", source="sackmann"), match("m2", date="2026-09-20")]
    ps = sum((players(m["match_id"]) for m in ms), [])
    ref = (write(tmp_path / "ref", ms, ps), ms, ps)
    res = run(tmp_path, ref, ms[:1], ps[:2])                                         # m2 (tml) gone
    assert res["template_ok"] and res["tml_lower"]["dropped"]["examples"] == ["m2"]
    res = run(tmp_path, ref, ms[1:], ps[2:])                                         # m1 (sackmann) gone
    assert not res["template_ok"] and res["gated"]["dropped"]["examples"] == ["m1"]


def test_tml_at_a_level_it_never_fed_is_still_gated(tmp_path, ref):
    q = dict(match("q3", date="2024-05-20", level="GS"), map_level="GSQ", qualifying=True)   # no tml GSQ in ref
    res = run(tmp_path, ref, ref[1] + [q], ref[2] + players("q3"))
    assert not res["template_ok"] and res["gated"]["new_past"]["examples"] == ["q3"]
    assert res["tml_lower"]["new_past"]["matches"] == 0


def test_a_candidates_box_layer_on_a_tml_row_stays_gated(tmp_path, ref):
    ps = [dict(r, ace=9.0) if (r["match_id"] == "m2" and r["side"] == "a") else r for r in ref[2]]
    live = write(tmp_path / "live", ref[1], ps)
    pd.DataFrame({"match_id": ["m2"], "applied": [True]}).to_parquet(live / "box_layers.parquet", index=False)
    res = H.check(live, timing=None, ref_stage0=ref[0], ref_timing=None)
    assert not res["template_ok"] and res["gated"]["revised"]["examples"] == ["m2"]
    assert res["tml_lower"]["revised"]["matches"] == 0


@pytest.mark.skipif(not (H.REF_STAGE0 / "stage0_matches.parquet").exists(), reason="the reference is not frozen")
def test_the_frozen_stage0_against_itself():
    res = H.check(H.REF_STAGE0, timing=None)
    assert res["template_ok"] and res["matches"] == res["reference_matches"] and res["updated"]["matches"] == 0
