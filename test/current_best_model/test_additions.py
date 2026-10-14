"""Tests of the accepted lower-level additions (src/eda/current_best_model/additions.py): the merge into a build's Stage 0
and timeline (skips, completions, the order), the timeline pin, and history.py's "accepted" class.
Run: ./python.sh -m pytest test/current_best_model/test_additions.py -q
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

from src.eda.current_best_model import additions as A  # noqa: E402


def stage0(ids, day="2026-06-01", tid="T1", rnd="Q1", box=True):
    m = pd.DataFrame({"match_id": ids, "tour": "atp", "year": 2026, "tournament_id": tid,
                      "tournament_date": pd.Timestamp(day), "round": rnd, "round_order": 1,
                      "match_num": np.arange(len(ids)), "player_a_id": [f"p{i}a" for i in range(len(ids))],
                      "player_b_id": [f"p{i}b" for i in range(len(ids))], "map_level": "CHQ",
                      "has_box": box, "box_status": "full" if box else "none", "sv_gms_incl_tb": False,
                      "order": np.arange(len(ids))})
    mp = pd.concat([pd.DataFrame({"match_id": m["match_id"], "player_id": m["player_a_id"],
                                  "opponent_id": m["player_b_id"], "side": "A", "won": True}),
                    pd.DataFrame({"match_id": m["match_id"], "player_id": m["player_b_id"],
                                  "opponent_id": m["player_a_id"], "side": "B", "won": False})], ignore_index=True)
    mp["has_box"] = box
    mp["ace"] = 3.0 if box else np.nan
    t = pd.DataFrame({"match_id": m["match_id"], "es": 100.0, "lf": 101.0, "obs": 100.0})
    return m, mp, t


def write_package(tmp: Path, m, mp, t, comp=None, name="pkg") -> Path:
    p = tmp / name
    p.mkdir(parents=True)
    m.drop(columns=["order"]).to_parquet(p / "matches.parquet", index=False)
    mp.to_parquet(p / "match_players.parquet", index=False)
    t.to_parquet(p / "timing.parquet", index=False)
    (comp if comp is not None else pd.DataFrame(columns=["match_id", "player_id", "side"])).to_parquet(
        p / "completions.parquet", index=False)
    files = {f: A.sha256(p / f) for f in ("matches.parquet", "match_players.parquet", "timing.parquet",
                                          "completions.parquet")}
    (p / "manifest.json").write_text(json.dumps({"files": files}), encoding="utf-8")
    A.register(name, tmp)
    return p


def test_merge_adds_skips_published_and_sorts(tmp_path):
    m, mp, t = stage0(["x1", "x2"], day="2026-06-08")
    am, amp, at = stage0(["n1", "n2", "x2"], day="2026-06-01", tid="T0")
    # n2 meets as x1 does: the same pair, tournament and round under another id (the feed published it)
    am.loc[1, ["player_a_id", "player_b_id", "tournament_id"]] = ["p0b", "p0a", "T1"]
    amp.loc[amp["match_id"] == "n2", "player_id"] = ["p0b", "p0a"]
    amp.loc[amp["match_id"] == "n2", "opponent_id"] = ["p0a", "p0b"]
    write_package(tmp_path, am, amp, at)
    m2, mp2, t2, rec = A.merge(m, mp, t, A.listed(tmp_path))
    r = rec["packages"][0]
    assert (r["added"], r["skipped_same_id"], r["skipped_same_meeting"]) == (1, 1, 1)
    assert m2["match_id"].tolist() == ["n1", "x1", "x2"]            # chrono_sort: the earlier week first
    assert m2["order"].tolist() == [0, 1, 2]
    assert mp2["match_id"].tolist() == ["n1", "n1", "x1", "x1", "x2", "x2"]
    assert set(t2["match_id"]) == {"x1", "x2", "n1"}


def test_completion_only_where_no_box_score_and_the_same_players(tmp_path):
    m, mp, t = stage0(["x1", "x2"], box=False)
    am, amp, at = stage0([], box=True)
    comp = mp[mp["match_id"] == "x1"][["match_id", "player_id", "side"]].copy()
    comp["match_has_box"], comp["match_box_status"], comp["match_sv_gms_incl_tb"] = True, "full", False
    comp["has_box"], comp["ace"] = True, [5.0, 7.0]
    write_package(tmp_path, am, amp, at, comp)
    m2, mp2, _, rec = A.merge(m, mp, t, A.listed(tmp_path))
    assert rec["packages"][0]["completions_applied"] == 1
    x1 = m2[m2["match_id"] == "x1"].iloc[0]
    assert bool(x1["has_box"]) and x1["box_status"] == "full"
    assert mp2.loc[mp2["match_id"] == "x1", "ace"].tolist() == [5.0, 7.0]
    assert not bool(m2.loc[m2["match_id"] == "x2", "has_box"].iloc[0])
    m3 = m.assign(has_box=True)                                       # already has one: left as it is
    m4, _, _, rec = A.merge(m3, mp, t, A.listed(tmp_path))
    assert rec["packages"][0]["completions_applied"] == 0


def test_a_package_whose_file_changed_is_refused(tmp_path):
    am, amp, at = stage0(["n1"])
    p = write_package(tmp_path, am, amp, at)
    at.assign(es=1.0).to_parquet(p / "timing.parquet", index=False)
    with pytest.raises(SystemExit):
        A.listed(tmp_path)


def test_pin_timing_puts_the_package_rows_back(tmp_path):
    am, amp, at = stage0(["n1"])
    write_package(tmp_path, am, amp, at, name="pkg")
    tree = tmp_path / "tree"
    (tree / A.MT).mkdir(parents=True)
    t = pd.DataFrame({"match_id": ["x1", "n1"], "es": [5.0, 7.0], "lf": [6.0, 9.0], "obs": [5.0, 8.0]})
    t.to_parquet(tree / A.MT / "timing.parquet", index=False)
    assert A.pin_timing(tree, tmp_path)["rows_pinned"] == 1
    got = pd.read_parquet(tree / A.MT / "timing.parquet").set_index("match_id")
    assert got.loc["n1", "es"] == 100.0 and got.loc["n1", "lf"] == 101.0 and got.loc["x1", "es"] == 5.0


def test_history_counts_accepted_additions_apart(tmp_path, monkeypatch):
    from src.eda.current_best_model import history as H
    monkeypatch.setattr(A, "ACCEPTED", tmp_path)
    monkeypatch.setattr(A, "accepted_ids", lambda accepted=tmp_path: ({"n1"}, set()))
    ref = tmp_path / "ref"
    live = tmp_path / "live"
    for d in (ref, live):
        d.mkdir()
    m, mp, t = stage0(["x1"], day="2025-06-01")
    full = {"level": "CH", "qualifying": True, "surface": "Clay", "indoor": False, "best_of": 3, "status": "completed",
            "score": "6-4 6-4", "minutes": 80, "format": "standard", "a_won": True, "source": "tml"}
    for c, v in full.items():
        m[c] = v
    for c in ("rank", "rank_points", "age", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms",
              "bp_saved", "bp_faced"):
        mp[c] = 1.0
    m.to_parquet(ref / "stage0_matches.parquet", index=False)
    mp.to_parquet(ref / "stage0_match_players.parquet", index=False)
    n, nmp, _ = stage0(["n1", "n2"], day="2025-07-01")
    for c, v in full.items():
        n[c] = v
    # n2 from another source: Tennis My Life's own lower-level backfills enter by themselves since 13 Oct 2026
    # (history.py's tml_lower; docs/decisions/2026-10-13-tml-lower-level-revisions.md), so would not be gated
    n.loc[n["match_id"].eq("n2"), "source"] = "tennislive"
    for c in ("rank", "rank_points", "age", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms",
              "bp_saved", "bp_faced"):
        nmp[c] = 1.0
    pd.concat([m, n]).to_parquet(live / "stage0_matches.parquet", index=False)
    pd.concat([mp, nmp]).to_parquet(live / "stage0_match_players.parquet", index=False)
    res = H.check(live, None, ref, None)
    assert res["accepted"]["added"] == 1 and res["new_past"]["matches"] == 1
    assert res["gated"]["new_past"]["matches"] == 1 and not res["template_ok"]   # n2 is not accepted
    assert "accepted 1 (allowed: lower-level additions 1, completions 0, decided repairs 0)" in H.summary_line(res)


# feeds (13 Oct 2026, docs/studies/data_gaps_2026/) ------------------------------------------------------------
def write_snapshot(tmp: Path, m, mp, t, feed="feed", snap="2026-10-13", comp=None) -> Path:
    p = tmp / feed / snap
    p.mkdir(parents=True)
    m.drop(columns=["order"]).to_parquet(p / "matches.parquet", index=False)
    mp.to_parquet(p / "match_players.parquet", index=False)
    t.to_parquet(p / "timing.parquet", index=False)
    (comp if comp is not None else pd.DataFrame(columns=["match_id", "player_id", "side"])).to_parquet(
        p / "completions.parquet", index=False)
    files = {f: A.sha256(p / f) for f in ("matches.parquet", "match_players.parquet", "timing.parquet",
                                          "completions.parquet")}
    (p / "manifest.json").write_text(json.dumps({"files": files}), encoding="utf-8")
    return p


def test_a_feed_snapshot_is_listed_after_the_packages_and_hash_checked(tmp_path):
    am, amp, at = stage0(["n1"])
    write_package(tmp_path, am, amp, at, name="pkg")
    fm, fmp, ft = stage0(["f1"], day="2026-06-15")
    p = write_snapshot(tmp_path, fm, fmp, ft)
    assert [q.name for q in A.listed(tmp_path)] == ["pkg"]               # written, not yet pointed at
    rec = A.set_feed("feed/2026-10-13", tmp_path)
    assert rec == {"feed": "feed", "snapshot": "2026-10-13", "previous": None}
    assert [f"{q.parent.name}/{q.name}" for q in A.listed(tmp_path)] == [f"{tmp_path.name}/pkg", "feed/2026-10-13"]
    ft.assign(es=1.0).to_parquet(p / "timing.parquet", index=False)
    with pytest.raises(SystemExit):
        A.listed(tmp_path)


def test_the_merge_skips_a_meeting_another_feed_published_that_week(tmp_path):
    m, mp, t = stage0(["x1"], day="2026-06-08", tid="TML1")
    mp["player_name"] = ["Ann Alpha", "Bea Beta"]
    am, amp, at = stage0(["n1", "n2", "n3"], day="2026-06-08", tid="NEW1")
    names = {("n1", "A"): "Ann Alpha", ("n1", "B"): "Bea Beta", ("n2", "A"): "Cy Gamma", ("n2", "B"): "Di Delta",
             ("n3", "A"): "Ann Alpha", ("n3", "B"): "Bea Beta"}
    amp["player_name"] = [names[(i, s)] for i, s in zip(amp["match_id"], amp["side"])]
    am.loc[0, ["player_a_id", "player_b_id"]] = ["p0a", "p0b"]           # n1: x1's pair, ids and round: a duplicate
    amp.loc[amp["match_id"] == "n1", "player_id"] = ["p0a", "p0b"]
    am.loc[2, ["player_a_id", "player_b_id"]] = ["other:1", "other:2"]   # n3: x1's pair by name only (other ids)
    am.loc[2, "tournament_date"] = pd.Timestamp("2026-06-15")           # ... a week later: a real rematch, kept
    write_package(tmp_path, am, amp, at, name="pkg")
    m2, _, _, rec = A.merge(m, mp, t, A.listed(tmp_path))
    r = rec["packages"][0]
    assert (r["added"], r["skipped_same_pair_round_week"]) == (2, 1)
    assert set(m2["match_id"]) == {"x1", "n2", "n3"}
    am.loc[2, "tournament_date"] = pd.Timestamp("2026-06-09")           # the same week: the names catch it
    (tmp_path / "pkg").rename(tmp_path / "old")
    (tmp_path / "accepted.json").unlink()
    write_package(tmp_path, am, amp, at, name="pkg")
    _, _, _, rec = A.merge(m, mp, t, A.listed(tmp_path))
    assert rec["packages"][0]["skipped_same_pair_round_week"] == 2


def test_retire_needs_the_feed_to_hold_every_match_of_the_package(tmp_path):
    am, amp, at = stage0(["n1", "n2"])
    write_package(tmp_path, am, amp, at, name="pkg")
    fm, fmp, ft = stage0(["n1"])
    write_snapshot(tmp_path, fm, fmp, ft, snap="a")
    A.set_feed("feed/a", tmp_path)
    with pytest.raises(SystemExit):
        A.retire("pkg", "superseded", tmp_path)
    fm, fmp, ft = stage0(["n1", "n2"])
    write_snapshot(tmp_path, fm, fmp, ft, snap="b")
    A.set_feed("feed/b", tmp_path)
    out = A.retire("pkg", "superseded", tmp_path)
    assert out["superseded_by"] == ["feed/b"]
    cur = A.index(tmp_path)
    assert cur["packages"] == [] and "pkg" in cur["retired"] and cur["feeds"] == {"feed": "b"}
    assert [h["snapshot"] for h in cur["feed_history"]] == ["a", "b"]


def test_retire_counts_the_same_meeting_under_another_new_players_id(tmp_path):
    """13 Oct 2026: a player new to Stage 0 takes a different minted id from each source (Misolic d. Esculcas, Braga
    Q1: 'atp:sofa:1292322' in the package, 'atp:tl:132674' in the feed). The feed holds that meeting as the merge
    judges it (week_duplicates: the same tour, round and both name keys, dates at most 3 days apart); a different
    opponent does not count."""
    am, amp, at = stage0(["n1"])
    am.loc[0, "player_b_id"] = "atp:sofa:9"
    amp.loc[amp["side"].eq("B"), "player_id"] = "atp:sofa:9"
    amp["player_name"] = ["Filip Misolic", "Tiago Esculcas"]
    write_package(tmp_path, am, amp, at, name="pkg")
    fm, fmp, ft = stage0(["f1"])
    fm.loc[0, "player_b_id"] = "atp:tl:7"
    fmp.loc[fmp["side"].eq("B"), "player_id"] = "atp:tl:7"
    fmp["player_name"] = ["Filip Misolic", "Tiago Esculcas"]
    write_snapshot(tmp_path, fm, fmp, ft, snap="a")
    A.set_feed("feed/a", tmp_path)
    fmp2 = fmp.copy()
    fmp2["player_name"] = ["Filip Misolic", "Someone Else"]
    write_snapshot(tmp_path, fm, fmp2, ft, snap="b")
    A.set_feed("feed/b", tmp_path)
    with pytest.raises(SystemExit):
        A.retire("pkg", "superseded", tmp_path)                  # another opponent: not the same meeting
    A.set_feed("feed/a", tmp_path)
    assert A.retire("pkg", "superseded", tmp_path)["superseded_by"] == ["feed/a"]


def test_history_accepts_a_revision_the_decided_tables_name(tmp_path, monkeypatch):
    """13 Oct 2026 (data_gaps_2026): a lower-level match revised by a decided repair (e.g. the Roland Garros repair's
    qualifying box scores, once adopt.py swaps the tables) is accepted, so the template build is not refused."""
    from src.eda.current_best_model import history as H
    monkeypatch.setattr(A, "ACCEPTED", tmp_path)
    monkeypatch.setattr(A, "accepted_ids", lambda accepted=tmp_path: (set(), set()))
    ref, live = tmp_path / "ref", tmp_path / "live"
    for d in (ref, live):
        d.mkdir()
    m, mp, _ = stage0(["x1", "x2"], day="2025-06-01")
    full = {"level": "GS", "qualifying": True, "surface": "Clay", "indoor": False, "best_of": 3, "status": "completed",
            "score": "6-4 6-4", "minutes": 80, "format": "standard", "a_won": True, "source": "sackmann",
            "map_level": "GSQ"}
    for c, v in full.items():
        m[c] = v
    for c in ("rank", "rank_points", "age", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms",
              "bp_saved", "bp_faced"):
        mp[c] = 1.0
    m.to_parquet(ref / "stage0_matches.parquet", index=False)
    mp.to_parquet(ref / "stage0_match_players.parquet", index=False)
    mp2 = mp.copy()
    mp2.loc[mp2["match_id"].isin(["x1", "x2"]), "first_in"] = 2.0          # both revised; only x1 is a decided repair
    m.to_parquet(live / "stage0_matches.parquet", index=False)
    mp2.to_parquet(live / "stage0_match_players.parquet", index=False)
    table = tmp_path / "row_corrections.csv"
    pd.DataFrame({"match_id": ["x1"], "action": ["replace_split"]}).to_csv(table, index=False)
    monkeypatch.setattr(H, "DECIDED_TABLES", {table: "match_id"})
    res = H.check(live, None, ref, None)
    assert res["accepted"]["decided_repairs"] == 1 and res["revised"]["matches"] == 1
    assert res["gated"]["revised"]["examples"] == ["x2"] and not res["template_ok"]
    pd.DataFrame({"match_id": ["x1", "x2"], "action": ["replace_split"] * 2}).to_csv(table, index=False)
    res = H.check(live, None, ref, None)
    assert res["accepted"]["decided_repairs"] == 2 and res["template_ok"]
