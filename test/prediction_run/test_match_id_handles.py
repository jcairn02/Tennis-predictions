"""A live match's id is predicted as Stage 0 builds it (28 Oct 2026; master pipeline process log, Part 23), offline.

Stage 0 names a match by its players' ids as the source row resolves them and only then maps a player's second id to
the established one, keeping the match id. Tennis My Life gave Kaitlin Quevedo a new id (269267) from Osaka, 19 Oct
2026: her rows carry wta:259733, her matches' names wta:269267. The run predicted her live match's id from the
established id, and the check after the sandbox's build stopped A4. These tests keep the three places that name a
match from players (the live matches, the earlier rounds filled from TennisLive, the published rounds looked up) on
Stage 0's own names, and the check's message on the cause.

Run: ./python.sh -m pytest test/prediction_run/test_match_id_handles.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import earlier_rounds as ER  # noqa: E402
from src.eda.prediction_run import inject as INJ  # noqa: E402
from src.eda.prediction_run import live_rows as LR  # noqa: E402
from src.eda.prediction_run import run as RUN  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

QUEVEDO_NEW, QUEVEDO = "269267", "wta:259733"          # TML's id at the event; the established one


def tml(tid, name, rnd, w, lo, row, date="20261026", src="t.csv"):
    """A staged TML row (as live_rows.staged_tml reads them); w and lo: (id, name)."""
    r = {c: "" for c in B.KEEP}
    r.update({"tourney_id": tid, "tourney_name": name, "surface": "Hard", "draw_size": "32", "tourney_level": "250",
              "indoor": "O", "tourney_date": date, "best_of": "3", "round": rnd, "match_num": str(row),
              "score": "6-3 6-4", "winner_id": w[0], "winner_name": w[1], "loser_id": lo[0], "loser_name": lo[1],
              "_source_file": src, "_row": row, "tour": "wta"})
    return r


def staged(rows) -> pd.DataFrame:
    raw = pd.DataFrame(rows)
    raw["_row"] = pd.to_numeric(raw["_row"]).astype("Int64")
    return raw


def s0(tid, rnd, w, lo, row, source="tml", src="t.csv", date="2026-10-26", has_box=True):
    """A Stage 0 match as stage0_build names it, and its two player rows. w and lo: (the id as the source row
    resolves it, the player's established id, name). The sides follow the name (C.side_is_low), as the builder's do."""
    lo_h, hi_h = sorted([w[0], lo[0]])
    mid = f"wta|{tid}|{rnd}|{lo_h}|{hi_h}"
    a, b = (w, lo) if w[0] == (lo_h if C.side_is_low(mid) else hi_h) else (lo, w)
    match = {"match_id": mid, "tour": "wta", "tournament_id": tid, "round": rnd, "source": source, "source_file": src,
             "source_row": row, "tournament_date": pd.Timestamp(date), "player_a_id": a[1], "player_b_id": b[1],
             "a_won": a is w, "has_box": has_box}
    bio = {"rank": None, "rank_points": None, "age": 25.0, "height": None, "hand": "R", "country": None}
    return match, [{"match_id": mid, "player_id": a[1], "side": "A", "player_name": a[2], **bio},
                   {"match_id": mid, "player_id": b[1], "side": "B", "player_name": b[2], **bio}]


def stage0_folder(folder: Path, built) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = pd.DataFrame([x[0] for x in built]).astype({"source_row": "Int64"})
    p = pd.DataFrame([r for x in built for r in x[1]])
    folder.mkdir(parents=True, exist_ok=True)
    m.to_parquet(folder / "stage0_matches.parquet", index=False)
    p.to_parquet(folder / "stage0_match_players.parquet", index=False)
    return m, p


# Guangzhou 2026's round of 32 as TML wrote it (Quevedo under her new id), and her September final under the old one
RAW = [tml("2026-1023", "Guangzhou", "R32", (QUEVEDO_NEW, "Kaitlin Quevedo"), ("213550", "Shuai Zhang"), 23),
       tml("2026-1023", "Guangzhou", "R32", ("214388", "Anna Bondar"), ("300001", "Ena Chen"), 24),
       tml("2026-1139", "Sao Paulo", "F", ("259733", "Kaitlin Quevedo"), ("206408", "Cara Gamma"), 9,
           date="20260915")]
BUILT = [s0("2026-1023", "R32", ("wta:" + QUEVEDO_NEW, QUEVEDO, "Kaitlin Quevedo"),
            ("wta:213550", "wta:213550", "Shuai Zhang"), 23),
         s0("2026-1023", "R32", ("wta:214388", "wta:214388", "Anna Bondar"), ("wta:300001", "wta:300001", "Ena Chen"),
            24),
         s0("2026-1139", "F", ("wta:259733", QUEVEDO, "Kaitlin Quevedo"), ("wta:206408", "wta:206408", "Cara Gamma"), 9,
            date="2026-09-15"),
         s0("2026-500", "R32", ("wta:259733", QUEVEDO, "Kaitlin Quevedo"), ("wta:206408", "wta:206408", "Cara Gamma"), 5,
            source="sackmann", src="sackmann.csv", date="2026-03-02")]


def test_id_handles_reads_the_ids_stage0s_match_names_carry(tmp_path):
    m, p = stage0_folder(tmp_path, BUILT)
    h = LR.id_handles(m, p, staged(RAW))
    assert h[("wta", QUEVEDO_NEW)] == "wta:" + QUEVEDO_NEW      # her new id names her matches, not wta:259733
    assert h[("wta", "259733")] == QUEVEDO and h[("wta", "214388")] == "wta:214388"
    assert len(h) == 6                                            # the Sackmann match has no TML row: not read
    assert LR.handle_of(h, "wta", QUEVEDO_NEW, QUEVEDO) == "wta:" + QUEVEDO_NEW
    assert LR.handle_of(h, "wta", "", QUEVEDO) == QUEVEDO          # a row without an id: the player's Stage 0 id
    twice = BUILT + [s0("2026-1023", "R16", ("wta:999", "wta:999", "Dana Delta"), ("wta:213550", "wta:213550",
                                                                                     "Shuai Zhang"), 30)]
    m2, p2 = stage0_folder(tmp_path / "two", twice)
    raw2 = staged(RAW + [tml("2026-1023", "Guangzhou", "R16", ("999", "Dana Delta"), (QUEVEDO_NEW, "Shuai Zhang"), 30)])
    assert ("wta", QUEVEDO_NEW) not in LR.id_handles(m2, p2, raw2)  # an id read two ways is left out


def test_a_live_match_is_named_with_the_id_its_row_carries(tmp_path, monkeypatch):
    stage0_folder(tmp_path / "stage0", BUILT)
    monkeypatch.setattr(LR, "staged_tml", lambda seasons: staged(RAW))
    monkeypatch.setattr(RUN, "venue_for", lambda tour, tid, name: "Guangzhou")
    mu = pd.DataFrame([{"tour": "wta", "tourney_id": "2026-1023", "round": "R16", "player_a": "Anna Bondar",
                        "player_b": "Kaitlin Quevedo", "day": "2026-10-29", "p_a": 0.55, "tourney_name": "Guangzhou"}])
    RUN.live_from_matchups(mu, tmp_path / "stage0", tmp_path)
    meta = pd.read_parquet(tmp_path / "live_meta.parquet")
    mid = f"wta|2026-1023|R16|wta:214388|wta:{QUEVEDO_NEW}"
    assert meta["match_id"].tolist() == [mid]                     # 28 Oct 2026's run expected ...|wta:259733
    bondar_is_a = C.side_is_low(mid)                              # her id sorts first: side A when the name's bit says
    assert meta["p_a"].iloc[0] == pytest.approx(0.55 if bondar_is_a else 0.45)
    rows = pd.read_parquet(tmp_path / "live_rows.parquet")
    assert rows["loser_id"].tolist() == [QUEVEDO_NEW]             # the row TML will publish, unchanged


def test_an_earlier_round_fill_is_named_with_the_id_its_row_carries(tmp_path):
    m, p = stage0_folder(tmp_path, BUILT)
    keyed = p.assign(key=B.S.keys_for(p["player_name"])).merge(m[["match_id", "tour"]], on="match_id")
    e = pd.DataFrame([{"tour": "wta", "tourney_id": "2026-1023", "tourney_name": "Guangzhou", "round": "Q2",
                       "winner_name": "Kaitlin Quevedo", "loser_name": "Ena Chen", "score": "6-3 6-4",
                       "day": "2026-10-25", "best_of": "3"}])
    players, raw = LR.stage0_players(tmp_path), staged(RAW)
    _, meta, left = ER.played_rows(e, raw, players, keyed, lambda r: "2026-1023", LR.id_handles(m, p, raw))
    assert not left and meta["match_id"].tolist() == [f"wta|2026-1023|Q2|wta:{QUEVEDO_NEW}|wta:300001"]
    _, before, _ = ER.played_rows(e, raw, players, keyed, lambda r: "2026-1023")       # without: as before
    assert before["match_id"].tolist() == ["wta|2026-1023|Q2|wta:259733|wta:300001"]


def test_a_published_round_is_found_by_its_players_whatever_ids_name_it(tmp_path):
    built = BUILT + [s0("2026-1023", "Q2", ("wta:" + QUEVEDO_NEW, QUEVEDO, "Kaitlin Quevedo"),
                        ("wta:300001", "wta:300001", "Ena Chen"), 20, has_box=True)]
    m, p = stage0_folder(tmp_path, built)
    keyed = p.assign(key=B.S.keys_for(p["player_name"])).merge(m[["match_id", "tour"]], on="match_id")
    e = pd.DataFrame([{"tour": "wta", "tourney_id": "2026-1023", "round": "Q2", "winner_name": "Kaitlin Quevedo",
                       "loser_name": "Ena Chen", "score": "6-3 6-4"}])
    over, rest, notes = RUN.tml_box_fills(e, staged(RAW), tmp_path, keyed, lambda r: "2026-1023")
    assert over.empty and rest.empty                              # found: not taken for an unpublished round
    assert notes == [{"match": "Kaitlin Quevedo v Ena Chen (Q2)", "outcome": "its source holds it with a box score"}]


def test_the_check_names_the_live_ids_stage0_gave_that_were_not_expected(tmp_path, monkeypatch):
    built = f"wta|2026-1023|R16|wta:214388|wta:{QUEVEDO_NEW}"
    pd.DataFrame({"match_id": [built], "status": ["completed"], "evaluation": [True], "has_box": [False],
                  "level": ["T250"], "qualifying": [False], "source_file": ["live_rows"]}
                 ).to_parquet(tmp_path / "m.parquet")
    (tmp_path / "stage0_summary.json").write_text(json.dumps({"live_rows": {"rows": 1}}), encoding="utf-8")
    monkeypatch.setattr(C, "MATCHES", tmp_path / "m.parquet")
    monkeypatch.setattr(C, "OUT", tmp_path)
    monkeypatch.setattr(INJ, "PLAYED", tmp_path / "no_played_meta.parquet")
    with pytest.raises(SystemExit, match=r"stage0_live_ids_not_expected.*wta:" + QUEVEDO_NEW):
        INJ.check(pd.DataFrame({"match_id": ["wta|2026-1023|R16|wta:214388|wta:259733"]}))
    assert INJ.check(pd.DataFrame({"match_id": [built]}))["in_stage0"] == 1
