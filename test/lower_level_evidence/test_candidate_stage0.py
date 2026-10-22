"""Offline tests of role F's candidate Stage 0 builder (src/eda/lower_level_evidence/candidate_stage0.py): the parsers,
the identity rules, the weekly-venue and duplicate rules, the Stage 0 rows of a new match and the timeline windows.
Synthetic frames only (the timeline test reads the frozen timeline's class table and the schedule rules, two small CSVs).

Run: ./python.sh -m pytest test/lower_level_evidence/test_candidate_stage0.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import candidate_stage0 as F  # noqa: E402

COUNTS = F.COUNTS


# ------------------------------------------------------------------------------------------------ parsers
def test_score_text_writes_the_tiebreak_losers_points_as_stage0_does():
    assert F.score_text([(7, 6), (3, 6), (6, 2)], [5, None, None]) == "7-6(5) 3-6 6-2"
    assert F.score_text([(6, 7), (6, 4)], [3, None]) == "6-7(3) 6-4"
    assert F.score_text([(6, 4), (6, 4)], [0, 0]) == "6-4 6-4"          # no tiebreak, no parentheses


def test_wta_rounds_from_the_round_id_and_draw_size():
    assert F.wta_round("main_singles", "1", 32) == "R32"
    assert F.wta_round("main_singles", "2", 30) == "R16"       # a 30-draw is a 32-draw with byes
    assert F.wta_round("main_singles", "1", 56) == "R64"
    assert F.wta_round("main_singles", "Q", 32) == "QF"
    assert F.wta_round("main_singles", "S", 32) == "SF"
    assert F.wta_round("qual_singles", "2", 48) == "Q2"
    assert F.wta_round("qual_singles", "", 48) is None


def test_qualifying_rounds_inferred_from_the_draw():
    # a 4-player qualifying: two first-round matches, then the final round between the two winners
    rows = pd.DataFrame({"sid": ["a", "b", "c"], "ev_key": "e", "qual": True, "rnd": [None, None, None],
                         "start_utc": pd.to_datetime(["2026-05-20 10:00", "2026-05-20 12:00", "2026-05-21 10:00"],
                                                     utc=True),
                         "id1": ["p1", "p3", "p1"], "id2": ["p2", "p4", "p3"]})
    assert F.infer_qual_rounds(rows).tolist() == ["Q1", "Q1", "Q2"]
    # two players who disagree on how many matches they have played keep no round
    bad = rows.assign(id2=["p2", "p4", "p9"])
    assert F.infer_qual_rounds(bad).tolist()[2] is None


def test_set_parsers():
    assert F.itf_sets("1:7/7 2:6/0 3:4/0") == [(7, 7), (6, 0), (4, 0)]
    assert F.tl_sets("7(7) 3 2") == [(7, 7), (3, None), (2, None)]


def test_nearest_monday_follows_the_timeline_anchor_rule():
    d = pd.Series(pd.to_datetime(["2026-09-13", "2026-09-14", "2026-09-17", "2026-09-18"]))   # Sun, Mon, Thu, Fri
    assert F.nearest_monday(d).dt.strftime("%Y-%m-%d").tolist() == ["2026-09-14", "2026-09-14", "2026-09-14",
                                                                    "2026-09-21"]


def test_country_codes():
    assert F.ioc("DEU") == "GER" and F.ioc("PRT") == "POR" and F.ioc("ITA") == "ITA"
    assert F.ioc("great-britain") == "GBR" and F.ioc(None) is None and F.ioc("") is None


# ------------------------------------------------------------------------------------------------ identity
def _links(rows):
    return pd.DataFrame(rows, columns=["sid", "match_id", "p1_side"])


def test_crosswalk_keeps_agreeing_shared_claims_and_refuses_namesakes():
    R = pd.DataFrame({"sid": [f"s{i}" for i in range(11)], "tour": "atp",
                      "id1": ["10", "10", "11", "20", "21", "30", "30", "30", "40", "40", "40"],
                      "id2": [f"9{i}" for i in range(11)],
                      "p1": ["Ann Lee", "Ann Lee", "Ann Lee", "Bea Cho", "Zoe Cho", "Cy Fox", "Cy Fox", "Cy Fox",
                             "Gus Hale", "Gus Hale", "Gus Hale"],
                      "p2": [f"X {c}" for c in "ABCDEFGHIJK"]})
    S = pd.DataFrame({"match_id": [f"m{i}" for i in range(11)],
                      "player_a_id": ["A", "A", "A", "B", "B", "C1", "C2", "C3", "D1", "D1", "D2"],
                      "player_b_id": [f"o{i}" for i in range(11)],
                      "name_a": ["Ann Lee"] * 3 + ["Bea Cho", "Bea Cho", "Cy Fox", "Di Lim", "Ed Wu"] + ["Gus Hale"] * 3,
                      "name_b": [f"X {c}" for c in "ABCDEFGHIJK"]})
    links = _links([(f"s{i}", f"m{i}", "A") for i in range(11)])
    xw, conflicting, contested = F.crosswalk(R, links, S)
    m = {k.split("|", 1)[1]: v for k, v in zip(xw["src"], xw["s0"])}          # keys are "<tour>|<source id>"
    conflicting = {k.split("|", 1)[1] for k in conflicting}
    assert m["10"] == "A" and m["11"] == "A"               # one player under two source ids, names agree: both kept
    assert m["20"] == "B" and "21" not in m                # 'Zoe Cho' claims Bea Cho's id: refused
    assert "21" in conflicting and "B" in contested
    assert "30" in conflicting and "30" not in m           # links split between three differently named players
    assert m["40"] == "D1"                                 # split between two Stage 0 ids of one name: the majority


class _Names(F.Names):
    def __init__(self, ids, countries):            # noqa: D401 - a stub with given tables
        self.ids, self.countries, self.by_last = {}, countries, {}
        for (tour, key), pids in ids.items():
            self.ids[(tour, key)] = set(pids)
            for p in pids:
                self.by_last.setdefault((tour, key.split()[-1]), set()).add((p, key))


def test_resolve_ids_routes():
    names = _Names({("atp", "jan novak"): {"atp:1"}, ("atp", "petr dvorak"): {"atp:2"},
                    ("atp", "joelle lilly steur"): {"atp:3"}, ("atp", "ivo karl"): {"atp:4", "atp:5"}},
                   {"atp:1": {"CZE"}, "atp:2": {"CZE"}, "atp:3": {"GER"}})
    xw = pd.DataFrame({"src": ["atp|7"], "s0": ["atp:2"]})
    R = pd.DataFrame({"tour": "atp", "id1": ["7", "8", "9", "10", "11"], "p1": ["Petr Dvorak", "Jan Novak",
                                                                               "Petr Dvorak", "Joelle Steur", "Ivo Karl"],
                      "c1": ["CZE", "CZE", "CZE", "GER", "CZE"], "id2": ["1", "2", "3", "4", "5"],
                      "p2": ["New One", "New Two", "New Three", "New Four", "New Five"], "c2": [None] * 5})
    out = F.resolve_ids(R, xw, conflicting={"atp|5"}, contested=set(), names=names, tag="tl")
    assert out.loc[0, "x1"] == "atp:2" and out.loc[0, "route1"] == "crosswalk"
    assert out.loc[1, "x1"] == "atp:1" and out.loc[1, "route1"] == "name"
    # another source id already maps to Petr Dvorak: a namesake, a new id (strict rule)
    assert out.loc[2, "x1"] == "atp:tl:9" and out.loc[2, "route1"] == "new"
    assert out.loc[3, "x1"] == "atp:3" and out.loc[3, "route1"] == "name_subset"
    assert out.loc[4, "route1"] == "new"                  # two Stage 0 players share the name: never guessed
    assert out.loc[4, "route2"] == "conflict"             # a source id whose links disagree
    relaxed = F.resolve_ids(R, xw, set(), set(), names, "wtaid", relax=True)
    assert relaxed.loc[2, "x1"] == "atp:2" and relaxed.loc[2, "route1"] == "name"   # same name and country


# ------------------------------------------------------------------------------------------------ weekly venues
def _S(rows):
    S = pd.DataFrame(rows, columns=["match_id", "tour", "tournament_id", "tdate", "round", "player_a_id",
                                    "player_b_id"])
    S["tdate"] = pd.to_datetime(S["tdate"])
    S["tournament_date"] = S["tdate"]
    return S


def test_weekly_venue_link_into_another_week_needs_identical_sets():
    S = _S([("w1", "atp", "MON-1", "2024-03-04", "R32", "a", "b"), ("x", "atp", "MON-2", "2024-03-11", "R16", "c", "d")])
    R = pd.DataFrame({"sid": ["r1", "r2"], "ev_key": ["tl:monastir-2", "tl:monastir-2"]})
    evmap = pd.DataFrame({"tournament_id": ["MON-2"], "tournament_date": [pd.Timestamp("2024-03-11")]},
                         index=pd.Index(["tl:monastir-2"], name="ev_key"))
    links = pd.DataFrame({"sid": ["r1", "r2"], "match_id": ["w1", "w1"], "sc": [False, True], "rd": [2, 2],
                          "p1_side": ["A", "A"], "pass": ["pair", "pair"]})
    kept, dropped = F.weekly_venue_filter(R, links, evmap, S)
    assert kept["sid"].tolist() == ["r2"] and dropped["sid"].tolist() == ["r1"]


def _cls_inputs():
    S = _S([("s1", "atp", "MON-1", "2024-03-04", "R32", "a", "b"), ("s2", "atp", "MON-2", "2024-03-11", "R32", "e", "f")])
    facts = pd.DataFrame({"level": ["ITF", "ITF"]}, index=pd.MultiIndex.from_tuples(
        [("MON-1", pd.Timestamp("2024-03-04")), ("MON-2", pd.Timestamp("2024-03-11"))]))
    evmap = pd.DataFrame({"tournament_id": ["MON-2"], "tournament_date": [pd.Timestamp("2024-03-11")]},
                         index=pd.Index(["tl:mon2"], name="ev_key"))
    R = pd.DataFrame({"sid": ["n1", "n2", "n3", "n4", "n5"], "source": "tennislive", "tour": "atp", "season": 2024,
                      "ev_key": ["tl:mon2", "tl:mon2", "tl:mon2", "tl:mon2", "tl:tour"],
                      "ev_name": "M15 Monastir", "ev_date": pd.Timestamp("2024-03-11"),
                      "qual": [False, False, True, True, False], "rnd": ["R16", "R32", "Q1", "Q2", "R32"],
                      "ev_level": ["ITF", "ITF", "ITF", "ITF", "T250"]})
    ids = pd.DataFrame({"x1": ["a", "e", "g", "i", "k"], "x2": ["b", "f", "h", "j", "l"],
                        "route1": "crosswalk", "route2": "crosswalk"}, index=R.index)
    return S, facts, evmap, R, ids


def test_classify_keeps_a_rematch_a_week_later_and_catches_clashes():
    S, facts, evmap, R, ids = _cls_inputs()
    links = pd.DataFrame(columns=["sid", "match_id"])
    out = F.classify(R, links, {}, evmap, ids, S, facts).set_index("sid")["why"]
    assert out["n1"] == "new"                              # a v b met at last week's Monastir: a real rematch
    assert out["n2"].startswith("left_out: the same pair already in Stage 0 at this event")
    assert out["n3"] == "new" and out["n4"] == "new"       # the event's qualifying joins Stage 0's tournament
    assert out["n5"].startswith("left_out: main tour")    # a main-tour match is not lower-level data


def test_classify_player_twice_in_a_round():
    S, facts, evmap, R, ids = _cls_inputs()
    ids.loc[1, ["x1", "x2"]] = ["e", "z"]                  # e already plays MON-2's R32 against f
    out = F.classify(R, pd.DataFrame(columns=["sid", "match_id"]), {}, evmap, ids, S, facts).set_index("sid")["why"]
    assert out["n2"] == "left_out: a player already plays this round of the event"


# ------------------------------------------------------------------------------------------------ Stage 0 rows
def _new_rows(**over):
    row = {"sid": "tennislive:x:1", "source": "tennislive", "tour": "atp", "season": 2024, "event_tid": "2024-M-TL-1",
           "event_date": pd.Timestamp("2024-03-11"), "tname": "M15 Monastir", "level": "ITF", "rnd": "R32",
           "surface": "Hard", "indoor": None, "best_of": 3, "draw_size": 32, "score": "6-4 3-6 7-6(5)", "minutes": None,
           "winner": 2, "x1": "atp:tl:1", "x2": "atp:105000", "p1": "Ann One", "p2": "Bob Two", "c1": "TUN", "c2": "FRA"}
    for k in (1, 2):
        for c in COUNTS:
            row[f"p{k}_{c}"] = np.nan
    row.update(over)
    return pd.DataFrame([row])


def test_build_rows_gives_stage0_rows_for_a_new_match():
    m, mp = F.build_rows(_new_rows())
    r = m.iloc[0]
    assert r["match_id"] == "atp|2024-M-TL-1|R32|atp:105000|atp:tl:1"
    assert r["map_level"] == "ITF" and not r["qualifying"] and r["status"] == "completed" and not r["has_box"]
    winner = mp.loc[mp["won"], "player_id"].iloc[0]
    assert winner == "atp:105000"                          # winner 2: the second player won
    assert set(mp["side"]) == {"A", "B"} and len(mp) == 2
    assert mp.loc[mp["won"], "games_won_n"].iloc[0] == 6 + 3 + 7          # the winner's games, from the score
    q, _ = F.build_rows(_new_rows(rnd="Q2", score="6-1 2-0 RET"))
    assert q.iloc[0]["map_level"] == "ITFQ" and q.iloc[0]["status"] == "retired"


def test_build_rows_runs_stage0s_box_checks():
    good = {"p1_ace": 3, "p1_df": 2, "p1_svpt": 70, "p1_first_in": 40, "p1_first_won": 28, "p1_second_won": 15,
            "p1_sv_gms": 13, "p1_bp_saved": 4, "p1_bp_faced": 6, "p2_ace": 5, "p2_df": 1, "p2_svpt": 72,
            "p2_first_in": 45, "p2_first_won": 33, "p2_second_won": 14, "p2_sv_gms": 13, "p2_bp_saved": 3,
            "p2_bp_faced": 5}
    m, mp = F.build_rows(_new_rows(score="6-4 3-6 7-6(5)", **good))
    assert bool(m.iloc[0]["has_box"]) and mp["svpt"].notna().all()
    bad = dict(good, p1_first_in=90)                       # first serves in above serve points: check B1
    m2, mp2 = F.build_rows(_new_rows(**bad))
    assert m2.iloc[0]["box_status"] == "failed_check" and mp2["svpt"].isna().all()


# ------------------------------------------------------------------------------------------------ timeline
def test_timeline_exact_days_and_cautious_windows():
    m = pd.DataFrame({"match_id": ["a", "b", "c"], "tour": "atp", "year": 2024, "level": "ITF",
                      "qualifying": [False, True, False], "round": ["R32", "Q1", "R32"], "round_order": [13, 1, 13],
                      "tournament_id": "T", "tournament_name": "M15 Monastir",
                      "tournament_date": pd.Timestamp("2024-03-11")})
    R = pd.DataFrame({"match_id": ["a", "b", "c"], "source": ["itf_live", "tennislive", "wta_site"],
                      "day": pd.to_datetime(["2024-03-12", "2024-03-09", None]),
                      "date_basis": ["local", "utc_date", None], "end_utc": pd.NaT})
    t = F.timeline(m, R, {"tennislive": {"before": 1, "after": 2}}).set_index("match_id")
    d = F.MT.to_day(pd.Series(pd.to_datetime(["2024-03-12", "2024-03-09"])))
    assert t.loc["a", "exact"] and t.loc["a", "es"] == d[0] - 1 and t.loc["a", "lf"] == d[0] + 1      # local day, slack 1
    assert t.loc["b", "exact"] and t.loc["b", "es"] == d[1] - 2 and t.loc["b", "lf"] == d[1] + 3      # UTC day +- 1, clock
    assert not t.loc["c", "exact"] and t.loc["c", "width_days"] > 3                                    # a class window
    assert (t["lf"] >= t["es"]).all()


def test_source_clock_measures_the_days_needed():
    R = pd.DataFrame({"sid": [f"s{i}" for i in range(300)], "day": pd.Timestamp("2024-03-12"), "date_basis": "utc_date"})
    links = pd.DataFrame({"sid": R["sid"], "match_id": [f"m{i}" for i in range(300)]})
    obs = F.MT.to_day(pd.Series([pd.Timestamp("2024-03-12")]))[0]
    ref = pd.DataFrame({"match_id": links["match_id"], "exact": True, "obs": obs - np.r_[np.zeros(297), [2, 2, 2]]})
    c = F.source_clock(R, links, ref)
    assert c["basis"] == "calibrated" and c["before"] == 1 and c["after"] == 0


def test_an_event_map_with_no_event_changes_nothing():
    S, facts, _, R, ids = _cls_inputs()
    empty = pd.DataFrame({"tournament_id": pd.Series(dtype=object),
                          "tournament_date": pd.Series(dtype="datetime64[ns]")}, index=pd.Index([], name="ev_key"))
    links = pd.DataFrame({"sid": ["n1"], "match_id": ["s1"], "sc": [False], "rd": [2], "p1_side": ["A"],
                          "pass": ["pair"]})
    kept, dropped = F.weekly_venue_filter(R.assign(ev_key=R["ev_key"].astype("string")), links, empty, S)
    assert len(kept) == 1 and dropped.empty
    out = F.classify(R, links, {}, empty, ids, S, facts).set_index("sid")["why"]
    assert out["n1"] == "in_stage0"


def test_wta_site_rounds_take_the_records_own_qualifying_round():
    m = pd.DataFrame({"pseudo_tournament_id": [1, 1, 1, 2, 2],
                      "qpm_flag": ["Q", "Q", "Q", "Q", "M"],
                      "round_name": ["R32", "R16", "Q", "R16", "Q"],
                      "tourn_round": [1, 2, 3, 2, 4]})
    # tournament 2 lists only its second qualifying round: its own index says Q2 (the first-round rule would say Q1)
    assert F.wta_site_rounds(m).tolist() == ["Q1", "Q2", "Q3", "Q2", "QF"]


def test_repair_and_dedupe_drops_new_matches_the_repair_makes_duplicates():
    rows = []
    for mid, a, b, rnd in (("ref1", "wta:1", "wta:2", "Q1"), ("new1", "wta:1", "wta:x", "Q1"),
                           ("new2", "wta:3", "wta:4", "Q2")):
        rows.append({"match_id": mid, "tour": "wta", "tournament_id": "T", "tournament_date": pd.Timestamp("2015-03-02"),
                     "round": rnd, "player_a_id": a, "player_b_id": b, "source": "sackmann" if mid == "ref1" else "wta_site",
                     "score": "6-1 6-1", "level": "ITF", "status": "completed", "format": "standard", "minutes": np.nan,
                     "has_box": False, "box_status": "blank", "score_flag": ""})
    m = pd.DataFrame(rows)
    mp = pd.concat([pd.DataFrame({"match_id": m["match_id"], "player_id": m["player_a_id"], "side": "A", "won": True,
                                  "player_name": ["Ann Lee", "Ann Lee", "Cy Fox"], "country": "AUS", "age": np.nan}),
                    pd.DataFrame({"match_id": m["match_id"], "player_id": m["player_b_id"], "side": "B", "won": False,
                                  "player_name": ["Bea Cho", "Bea Cho", "Di Lim"], "country": "AUS", "age": np.nan})],
                   ignore_index=True)
    for c in F.COUNTS:
        mp[c] = np.nan
    m2, mp2, info, gone = F.repair_and_dedupe(m, mp, ref_ids={"ref1"})
    # 'Bea Cho' under a name id is merged into the reference's wta:2: new1 then repeats ref1 and is dropped
    assert gone == {"new1"} and set(m2["match_id"]) == {"ref1", "new2"}
    assert info["reference_player_rows_changed"] == 0


def test_one_source_number_in_two_tours_is_two_players():
    # TennisLive numbers ATP and WTA players separately: id 42 is a man in one tour and a woman in the other
    R = pd.DataFrame({"sid": ["a", "b", "c"], "tour": ["wta", "wta", "atp"], "id1": ["42", "42", "42"],
                      "id2": ["7", "8", "9"], "p1": ["Laura Siegemund"] * 2 + ["Michael Shabaz"],
                      "p2": ["X A", "X B", "X C"], "c1": None, "c2": None})
    S = pd.DataFrame({"match_id": ["m1", "m2"], "player_a_id": ["wta:1", "wta:1"], "player_b_id": ["wta:7", "wta:8"],
                      "name_a": ["Laura Siegemund"] * 2, "name_b": ["X A", "X B"]})
    xw, conflicting, contested = F.crosswalk(R, _links([("a", "m1", "A"), ("b", "m2", "A")]), S)
    assert dict(zip(xw["src"], xw["s0"])) == {"wta|42": "wta:1", "wta|7": "wta:7", "wta|8": "wta:8"}
    names = _Names({}, {})
    out = F.resolve_ids(R, xw, conflicting, contested, names, tag="tl")
    assert out.loc[0, "x1"] == "wta:1" and out.loc[2, "x1"] == "atp:tl:42"     # the man keeps a man's new id


def test_timeline_covers_both_dates_when_the_source_dates_the_event_a_week_later():
    m = pd.DataFrame({"match_id": ["q"], "tour": "wta", "year": 2018, "level": "ITF", "qualifying": [True],
                      "round": ["Q1"], "round_order": [1], "tournament_id": "T", "tournament_name": "Antalya $15K",
                      "tournament_date": pd.Timestamp("2018-04-16")})
    R = pd.DataFrame({"match_id": ["q"], "source": ["wta_site"], "day": [pd.NaT], "date_basis": [None],
                      "end_utc": pd.NaT, "ev_date": [pd.Timestamp("2018-04-23")]})
    t = F.timeline(m, R, {}).iloc[0]
    alone = F.timeline(m, R.drop(columns="ev_date"), {}).iloc[0]
    later = F.MT.to_day(pd.Series([pd.Timestamp("2018-04-23")]))[0]
    assert t["lf"] >= later and t["es"] == alone["es"] and t["lf"] > alone["lf"]


# ------------------------------------------------------------------------------------------------ a dated subset
def _toy_candidate(tmp_path):
    """A reference of two result-only ITF matches (2024 and 2025), and a parent candidate that completed both and added
    one match in each year."""
    def m_rows(ids, dates, has_box):
        return pd.DataFrame({"match_id": ids, "tournament_date": pd.to_datetime(dates), "has_box": has_box,
                             "box_status": np.where(has_box, "ok", "blank"),
                             "sv_gms_incl_tb": np.where(has_box, 1.0, np.nan), "order": np.arange(len(ids))})

    def mp_rows(ids, has_box):
        p = pd.concat([pd.DataFrame({"match_id": ids, "player_id": [f"p{i}a" for i in range(len(ids))], "side": "A"}),
                       pd.DataFrame({"match_id": ids, "player_id": [f"p{i}b" for i in range(len(ids))], "side": "B"})],
                      ignore_index=True)
        hb = p["match_id"].map(dict(zip(ids, has_box))).astype(bool)
        p["has_box"] = hb
        for c in F.COUNTS + F.BOX_RATES:
            p[c] = np.where(hb, 50.0, np.nan)
        return p

    m_ref = m_rows(["r1", "r2"], ["2024-06-03", "2025-03-03"], [False, False])
    mp_ref = mp_rows(["r1", "r2"], [False, False])
    ids, dates = ["r1", "n1", "r2", "n2"], ["2024-06-03", "2024-07-01", "2025-03-03", "2025-04-07"]
    m = m_rows(ids, dates, [True, False, True, False])
    mp = mp_rows(ids, [True, False, True, False])
    mp.loc[mp["match_id"].isin(["r1", "r2"]), "player_id"] = mp_ref.set_index(["match_id", "side"]).loc[
        list(zip(mp.loc[mp["match_id"].isin(["r1", "r2"]), "match_id"], mp.loc[mp["match_id"].isin(["r1", "r2"]),
                                                                                "side"])), "player_id"].to_numpy()
    parent = tmp_path / "parent"
    (parent / "evidence").mkdir(parents=True)
    m.to_parquet(parent / "stage0_matches.parquet", index=False)
    mp.to_parquet(parent / "stage0_match_players.parquet", index=False)
    pd.DataFrame({"match_id": ids, "es": [1, 2, 3, 4], "lf": [2, 3, 4, 5], "obs": [1, 2, 3, 4],
                  "exact": False}).to_parquet(parent / "timing.parquet", index=False)
    pd.DataFrame({"match_id": ["n1", "n2"], "sid": ["s1", "s2"], "source": "tennislive", "tour": "atp",
                  "season": [2024, 2025], "ev_key": ["e1", "e2"], "map_level": "ITF", "rnd": "R32", "x1": "a",
                  "x2": "b", "route1": "new", "route2": "crosswalk"}).to_parquet(parent / "additions.parquet",
                                                                                    index=False)
    pd.DataFrame({"match_id": ["r1", "r2"], "source": "sofascore", "kind": "completion",
                  "applied": True}).to_parquet(parent / "box_layers.parquet", index=False)
    cols = ["sid", "source", "tour", "season", "ev_key", "ev_name", "qual", "rnd", "x1", "x2", "route1", "route2",
            "match_id", "map_level", "why", "pass", "sc", "rd"]
    pd.DataFrame([dict.fromkeys(cols, "") | {"why": "left_out: level unknown"}]).to_csv(
        parent / "left_out.csv.gz", index=False, compression="gzip")
    (parent / "evidence" / "links_x.parquet").write_bytes(b"")
    (parent / "identity_verdicts.csv").write_text("source,verdict\n", encoding="utf-8")
    (parent / "manifest.json").write_text("{}", encoding="utf-8")
    (parent / "build_record.json").write_text('{"inputs": {}}', encoding="utf-8")
    return parent, m_ref, mp_ref


def test_derive_keeps_only_the_additions_dated_up_to_the_cut(tmp_path, monkeypatch):
    parent, m_ref, mp_ref = _toy_candidate(tmp_path)
    monkeypatch.setattr(F, "load_reference", lambda folder=None: (m_ref, mp_ref))
    out = tmp_path / "pre"
    rec = F.derive("_pre", parent, "2024-12-29", out)
    m = pd.read_parquet(out / "stage0_matches.parquet").set_index("match_id")
    mp = pd.read_parquet(out / "stage0_match_players.parquet")
    assert list(m.index) == ["r1", "n1", "r2"] and m["order"].tolist() == [0, 1, 2]
    assert bool(m.loc["r1", "has_box"]) and not bool(m.loc["r2", "has_box"])         # the 2025 completion is undone
    assert m.loc["r2", "box_status"] == "blank" and np.isnan(m.loc["r2", "sv_gms_incl_tb"])
    r2 = mp[mp["match_id"].eq("r2")]
    assert (~r2["has_box"]).all() and r2[F.COUNTS + F.BOX_RATES].isna().all().all()
    assert mp[mp["match_id"].eq("r1")][F.COUNTS].notna().all().all()
    assert set(pd.read_parquet(out / "timing.parquet")["match_id"]) == {"r1", "n1", "r2"}
    L = pd.read_parquet(out / "box_layers.parquet").set_index("match_id")["applied"]
    assert bool(L["r1"]) and not bool(L["r2"])
    lo = pd.read_csv(out / "left_out.csv.gz")
    assert lo.loc[lo["match_id"].eq("n2"), "why"].tolist() == ["left_out: dated after 2024-12-29 (the cut of _pre)"]
    assert (out / "identity_verdicts.csv").exists() and (out / "evidence" / "links_x.parquet").exists()
    assert rec["new_matches"] == 1 and rec["new_matches_dropped_as_later"] == 1
    assert rec["box_completions_undone_as_later"] == 1 and rec["until"] == "2024-12-29"


def test_derive_needs_a_ready_parent(tmp_path):
    with pytest.raises(SystemExit):
        F.main(["--label", "_pre", "--derive-from", str(tmp_path), "--out", str(tmp_path / "pre")])


def test_a_candidate_without_new_matches_writes_additions_the_checks_can_read(tmp_path):
    """A box-only source's candidate (14 Oct 2026, the TennisLive box-score package) adds no match: its additions table
    keeps its columns, so the checks read it (an empty frame without columns stopped check_rules)."""
    adds = F.empty_additions()
    assert len(adds) == 0 and list(adds.columns) == F.ADDITION_COLUMNS + F.ADDITION_DERIVED
    adds.to_parquet(tmp_path / "additions.parquet", index=False)
    back = pd.read_parquet(tmp_path / "additions.parquet")
    assert list(back.columns) == list(adds.columns)
    # text columns read back as text, as a written table's do (inventory's merge on player ids needs matching dtypes)
    assert all(isinstance(back[c].dtype, pd.StringDtype) for c in ("match_id", "source", "x1", "x2", "player_a_id"))
    m = pd.DataFrame({"match_id": ["r1", "r2"], "status_detail": "completed", "format": "standard",
                      "box_status": ["full", "no_svgms"], "score_flag": "", "a_won": [True, False]})
    layers = pd.DataFrame({"match_id": ["r2"], "source": ["tennislive_pages"], "kind": ["completion"],
                           "passes_checks": [True], "applied": [True]})
    out = F.check_rules({"m": m, "adds": back, "layers": layers}, m[["match_id"]])
    assert out["status"] == [] and out["box_status"] == [] and out["side_a_won_new"]["n"] == 0
    assert out["box_layers"] == [{"source": "tennislive_pages", "kind": "completion", "matches": 1, "pass_checks": 1,
                                  "failed_checks": 0, "applied": 1}]


def test_identity_precision_counts_errors_with_an_exact_upper_bound(tmp_path):
    v = pd.DataFrame({"kind": "links", "source": ["a"] * 20 + ["b"] * 10, "route": "", "row": range(30),
                      "verdict": ["right"] * 20 + ["right"] * 8 + ["wrong", "unsure"], "note": ""})
    v.to_csv(tmp_path / "identity_verdicts.csv", index=False)
    p = F.identity_precision(tmp_path).set_index("source")
    assert p.loc["a", "wrong"] == 0 and abs(p.loc["a", "upper95"] - (1 - 0.025 ** (1 / 20))) < 1e-4   # 0 of 20
    assert p.loc["b", "error_rate"] == 0.1 and p.loc["b", "error_rate_unsure_as_wrong"] == 0.2
    v.loc[0, "verdict"] = "maybe"
    v.to_csv(tmp_path / "identity_verdicts.csv", index=False)
    with pytest.raises(SystemExit):
        F.identity_precision(tmp_path)


def test_round_union_widens_only_a_window_disjoint_from_the_frozen_round():
    # frozen semifinals of event T on day 26 (exact); a new semifinal the source dates 20 (window 19-21) is disjoint:
    # it takes the union 19-26. A new quarterfinal overlapping the frozen ones, and a round the frozen data lacks, stay.
    ref = pd.DataFrame({"match_id": ["r1", "r2", "r3"], "tournament_id": "T", "round": ["SF", "SF", "QF"],
                        "es": [26.0, 26.0, 24.0], "lf": [26.0, 26.0, 25.0]})
    new = pd.DataFrame({"match_id": ["n1", "n2", "n3"], "tournament_id": "T", "round": ["SF", "QF", "F"],
                        "es": [19.0, 25.0, 27.0], "lf": [21.0, 27.0, 29.0], "obs": [20.0, 26.0, 28.0],
                        "width_days": [3.0, 3.0, 3.0], "exact": True, "window_basis": "exact", "demoted": ""})
    t, widened = F.round_union(new, ref, {"r1", "r2", "r3"})
    t = t.set_index("match_id")
    assert list(widened["match_id"]) == ["n1"]
    assert (t.loc["n1", "es"], t.loc["n1", "lf"], t.loc["n1", "width_days"]) == (19.0, 26.0, 8.0)
    assert not t.loc["n1", "exact"] and t.loc["n1", "window_basis"] == "exact+frozen_round_union"
    assert 19.0 <= t.loc["n1", "obs"] <= 26.0
    assert t.loc["n2"].equals(new.set_index("match_id").loc["n2"]) and t.loc["n3"].equals(new.set_index("match_id").loc["n3"])
    # a new row dated after the frozen round's last finish (the R16 of USA-21): es moves back to the round's start
    late = new.iloc[[1]].assign(match_id="n4", round="QF", es=30.0, lf=32.0, obs=31.0)
    t2, w2 = F.round_union(late, ref, {"r1", "r2", "r3"})
    assert (t2["es"].iloc[0], t2["lf"].iloc[0]) == (24.0, 32.0) and len(w2) == 1


# ------------------------------------------------------------------------------------------------ the 2026 gaps (13 Oct)
def test_orient_sets_turns_a_listing_players_score_to_the_winner():
    sets, flipped = F.orient_sets("2-6  4-6", "W")
    assert flipped and sets == [(6, 2, None), (6, 4, None)]
    sets, flipped = F.orient_sets("7-6(5)  6-3", "W")
    assert not flipped and sets == [(7, 6, "(5)"), (6, 3, None)]
    sets, flipped = F.orient_sets("6-4  3-6  1-0", "R")      # a retirement with the sets level keeps the listed side
    assert not flipped


def test_tdi_sets_reads_games_per_set_team_a_first():
    assert F.tdi_sets("1:6/4 2:4", "1:7/7 2:6") == ((6, 7), (4, 6))
    assert F.tdi_sets("1:4 2:7/7 3:6", "1:6 2:6/5 3:4") == ((4, 6), (7, 6), (6, 4))
    assert F.tdi_sets("", "1:6") == ()


def test_derive_keeps_the_lost_levels_from_their_dates_and_blanks_results_only_levels(tmp_path, monkeypatch):
    def m_rows(ids, tours, levels, dates, has_box):
        return pd.DataFrame({"match_id": ids, "tour": tours, "map_level": levels, "year": [int(d[:4]) for d in dates],
                             "tournament_date": pd.to_datetime(dates), "has_box": has_box,
                             "box_status": np.where(has_box, "full", "blank"),
                             "sv_gms_incl_tb": np.where(has_box, 1.0, np.nan), "order": np.arange(len(ids))})

    def mp_rows(ids, has_box):
        p = pd.concat([pd.DataFrame({"match_id": ids, "player_id": [f"{i}a" for i in ids], "side": "A"}),
                       pd.DataFrame({"match_id": ids, "player_id": [f"{i}b" for i in ids], "side": "B"})],
                      ignore_index=True)
        hb = p["match_id"].map(dict(zip(ids, has_box))).astype(bool)
        p["has_box"] = hb
        for c in F.COUNTS + F.BOX_RATES:
            p[c] = np.where(hb, 50.0, np.nan)
        return p

    ref = (["r1", "r2"], ["wta", "wta"], ["ITFQ", "GSQ"], ["2024-06-03", "2026-01-19"], [False, False])
    m_ref, mp_ref = m_rows(*ref), mp_rows(ref[0], ref[4])
    ids = ["r1", "r2", "n1", "n2", "n3", "n4"]
    tours = ["wta", "wta", "wta", "wta", "atp", "wta"]
    levels = ["ITFQ", "GSQ", "ITFQ", "ITF", "ITF", "GSQ"]
    dates = ["2024-06-03", "2026-01-19", "2025-03-03", "2026-07-06", "2025-05-05", "2026-06-29"]
    boxes = [False, True, True, True, True, True]                  # r2 completed by the parent; the additions boxed
    parent = tmp_path / "parent"
    (parent / "evidence").mkdir(parents=True)
    m_rows(ids, tours, levels, dates, boxes).to_parquet(parent / "stage0_matches.parquet", index=False)
    mp_rows(ids, boxes).to_parquet(parent / "stage0_match_players.parquet", index=False)
    pd.DataFrame({"match_id": ids, "es": range(6), "lf": range(1, 7), "obs": range(6), "exact": False}).to_parquet(
        parent / "timing.parquet", index=False)
    pd.DataFrame({"match_id": ["n1", "n2", "n3", "n4"], "sid": ["s1", "s2", "s3", "s4"], "source": "x",
                  "tour": ["wta", "wta", "atp", "wta"], "season": [2025, 2026, 2025, 2026], "ev_key": "e",
                  "map_level": ["ITFQ", "ITF", "ITF", "GSQ"], "rnd": "R32", "x1": "a", "x2": "b", "route1": "new",
                  "route2": "new"}).to_parquet(parent / "additions.parquet", index=False)
    pd.DataFrame({"match_id": ["r2"], "source": "wta_api", "kind": "completion", "applied": True}).to_parquet(
        parent / "box_layers.parquet", index=False)
    cols = ["sid", "source", "tour", "season", "ev_key", "ev_name", "qual", "rnd", "x1", "x2", "route1", "route2",
            "match_id", "map_level", "why", "pass", "sc", "rd"]
    pd.DataFrame([dict.fromkeys(cols, "") | {"why": "left_out: level unknown"}]).to_csv(
        parent / "left_out.csv.gz", index=False, compression="gzip")
    (parent / "identity_verdicts.csv").write_text("source,verdict\n", encoding="utf-8")
    (parent / "manifest.json").write_text("{}", encoding="utf-8")
    (parent / "build_record.json").write_text('{"inputs": {}}', encoding="utf-8")
    monkeypatch.setattr(F, "load_reference", lambda folder=None: (m_ref, mp_ref))
    keep = {"since": ["wta:ITFQ:2024-12-16", "wta:ITF:2026-06-01", "wta:GSQ:2026-01-19"],
            "results_only": ["wta:ITFQ", "wta:GSQ"]}
    out = tmp_path / "gaps"
    rec = F.derive("_gaps", parent, None, out, keep)
    m = pd.read_parquet(out / "stage0_matches.parquet").set_index("match_id")
    mp = pd.read_parquet(out / "stage0_match_players.parquet")
    assert sorted(m.index) == ["n1", "n2", "n4", "r1", "r2"]                  # n3: men's ITF of 2025, outside the scope
    assert bool(m.loc["n2", "has_box"])                                        # women's ITF keeps its box score
    for i in ("n1", "n4"):                                                     # results only: the added box blanked
        assert not bool(m.loc[i, "has_box"]) and m.loc[i, "box_status"] == "blank"
        assert mp[mp["match_id"].eq(i)][F.COUNTS + F.BOX_RATES].isna().all().all()
    assert not bool(m.loc["r2", "has_box"])                                    # its completion undone
    assert not bool(pd.read_parquet(out / "box_layers.parquet").set_index("match_id").loc["r2", "applied"])
    assert rec["added_box_scores_blanked_results_only"] == 2 and rec["new_matches"] == 3
    with pytest.raises(SystemExit):
        F.since_rules(["wta:ITF"])


def test_the_repair_puts_back_a_reference_fact_a_completed_box_score_moved(monkeypatch):
    """13 Oct 2026: repair_tables blanks a duration the box score makes implausible; a reference match's facts stay the
    reference's (a layer completed its box score), a new match's are repaired as usual."""
    import src.eda.feature_alpha_audit.repair_data as RD

    def fake_repair(m, mp):
        m = m.copy()
        m["minutes"] = np.nan                                    # the rule blanks every duration
        return m, mp.copy(), {}
    monkeypatch.setattr(RD, "repair_tables", fake_repair)
    m = pd.DataFrame({"match_id": ["r1", "n1"], "tour": "wta", "tournament_id": ["t1", "t2"],
                      "tournament_date": pd.to_datetime(["2018-01-01", "2026-07-06"]), "round": "Q1",
                      "player_a_id": ["a", "c"], "player_b_id": ["b", "d"], "minutes": [83.0, 50.0],
                      "score": ["6-0 0-0", "6-1 6-1"]})
    mp = pd.DataFrame({"match_id": ["r1", "r1", "n1", "n1"], "side": list("ABAB"), "player_id": list("abcd")})
    m2, mp2, info, gone = F.repair_and_dedupe(m, mp, {"r1"})
    assert m2.set_index("match_id").loc["r1", "minutes"] == 83.0 and np.isnan(m2.set_index("match_id").loc["n1", "minutes"])
    assert info["reference_facts_restored"] == 1 and not gone


def test_a_wta_id_one_source_minted_joins_the_player_another_source_links_it_to():
    """13 Oct 2026 (the lower-level feed's hand check): the WTA API minted 'wta:wtaid:330740' for a WTA id the WTA
    website's records link to Stage 0's wta:236978; the new matches take wta:236978. A name that shares no surname word
    is refused, and a match that would become one player against herself keeps its ids."""
    xws = {"wta_api": pd.DataFrame(columns=["src", "s0", "s0_name"]),
           "wta_site": pd.DataFrame({"src": ["wta|330740", "wta|330741", "wta|330742", "wta|330743"],
                                     "s0": ["wta:236978", "wta:9", "wta:5", "wta:wtaid:999"],
                                     "s0_name": ["Iva Primorac", "Ann Lee", "Cy Fox", "Not In Reference"]}),
           "tennislive": pd.DataFrame({"src": ["wta|330740"], "s0": ["wta:777"], "s0_name": ["Iva Primorac"]})}
    idmap = F.shared_id_map(xws, ref_players={"wta:236978", "wta:9", "wta:5", "wta:777"})
    # TennisLive's ids are another system ('tl'): its 330740 is not the WTA's
    assert idmap == {"wta:wtaid:330740": ("wta:236978", "Iva Primorac"), "wta:wtaid:330741": ("wta:9", "Ann Lee"),
                     "wta:wtaid:330742": ("wta:5", "Cy Fox"), "wta:tl:330740": ("wta:777", "Iva Primorac")}
    mn = pd.DataFrame({"match_id": ["n1", "n2", "n3"], "player_a_id": ["wta:wtaid:330740", "wta:wtaid:330741", "wta:5"],
                       "player_b_id": ["wta:111", "wta:112", "wta:wtaid:330742"]})
    mpn = pd.DataFrame({"match_id": ["n1", "n1", "n2", "n2", "n3", "n3"], "side": list("ABABAB"),
                        "player_id": ["wta:wtaid:330740", "wta:111", "wta:wtaid:330741", "wta:112", "wta:5",
                                      "wta:wtaid:330742"],
                        "opponent_id": ["wta:111", "wta:wtaid:330740", "wta:112", "wta:wtaid:330741",
                                        "wta:wtaid:330742", "wta:5"]})
    N = pd.DataFrame({"match_id": ["n1", "n2", "n3"], "x1": ["wta:wtaid:330740", "wta:wtaid:330741", "wta:5"],
                      "p1": ["Iva Primorac Pavicic", "Zoe Brown", "Cy Fox"], "route1": ["new", "new", "crosswalk"],
                      "x2": ["wta:111", "wta:112", "wta:wtaid:330742"], "p2": ["B One", "B Two", "Cy Fox"],
                      "route2": ["crosswalk", "crosswalk", "new"]})
    counts = F.unify_shared_ids([mn], [mpn], [N], idmap)
    m = mn.set_index("match_id")
    assert m.loc["n1", "player_a_id"] == "wta:236978"                          # a fuller name of the same player
    assert m.loc["n2", "player_a_id"] == "wta:wtaid:330741"                    # 'Zoe Brown' is not 'Ann Lee'
    assert (m.loc["n3", "player_a_id"], m.loc["n3", "player_b_id"]) == ("wta:5", "wta:wtaid:330742")   # kept apart
    p = mpn.set_index(["match_id", "side"])
    assert p.loc[("n1", "A"), "player_id"] == "wta:236978" and p.loc[("n1", "B"), "opponent_id"] == "wta:236978"
    assert N.loc[0, "x1"] == "wta:236978" and N.loc[0, "route1"] == "shared_crosswalk" and N.loc[1, "route1"] == "new"
    assert counts == {"minted_ids_a_shared_crosswalk_maps": 3, "unified_ids": 2, "refused_names_differ": 1,
                      "player_rows": 1, "matches_kept_apart": 1}


def test_a_name_written_with_other_punctuation_is_the_same_player():
    idmap = {"wta:wtaid:322605": ("wta:214974", "Francesca Delledera")}
    mn = pd.DataFrame({"match_id": ["n1"], "player_a_id": ["wta:wtaid:322605"], "player_b_id": ["wta:1"]})
    mpn = pd.DataFrame({"match_id": ["n1", "n1"], "side": ["A", "B"], "player_id": ["wta:wtaid:322605", "wta:1"]})
    N = pd.DataFrame({"match_id": ["n1"], "x1": ["wta:wtaid:322605"], "p1": ["Francesca Dell'Edera"], "route1": ["new"],
                      "x2": ["wta:1"], "p2": ["B One"], "route2": ["crosswalk"]})
    assert F.unify_shared_ids([mn], [mpn], [N], idmap)["unified_ids"] == 1
    assert mn.loc[0, "player_a_id"] == "wta:214974" and mpn.loc[0, "player_id"] == "wta:214974"


def test_wta_site_leaves_out_the_copys_misfiled_editions_and_takes_the_wta_apis_rows(tmp_path, monkeypatch):
    """The copy's last ten editions (7-14 Sep 2026) file their matches under the wrong editions, ITF W50s under WTA 125
    titles among them (P6 data issues, 14 Oct 2026): their listings are left out, and the WTA API's player-matches row
    places the match under its true edition and level."""
    site, api = tmp_path / "bwandowando", tmp_path / "player_results"
    site.mkdir()
    api.mkdir()
    monkeypatch.setattr(F, "WTA_SITE", site)
    monkeypatch.setattr(F, "WTA_PLAYER_RESULTS", api)
    monkeypatch.setitem(F.WTA_SITE_API, "on", True)
    montreux, guiyang = 163248187558, 322715938447
    assert {montreux, guiyang} <= F.WTA_SITE_MISFILED
    pd.DataFrame({"pseudo_tournament_id": [montreux, guiyang],
                  "title": ["Montreux Nestlé Open - Montreux, SUI", "WTT W50 - GUIYANG, CHINA"],
                  "startDate": ["2026-09-07"] * 2, "surface": ["CLAY", "HARD"], "inOutdoor": ["O", "O"],
                  "country": ["SUI", "CHN"], "level": ["WTA 125", "ITF"], "singlesDrawSize": [32, 32],
                  "tournamentGroupId": [1112, 4209]}).to_csv(site / "tournaments.csv", index=False)
    pd.DataFrame({"pseudo_match_id": [1], "pseudo_tournament_id": [montreux], "player_1": [330001],
                  "player_2": [330002], "player_3": [None], "player_4": [None], "qpm_flag": ["M"],
                  "reason_code": ["W"], "round_name": ["R32"], "tourn_round": [1], "scores": ["7-6(5)  7-5"],
                  "team_name_1": ["WANG,  YAFAN  CHN"], "team_name_2": ["ASTAKHOVA,  ALEKSANDRA  RUS"],
                  "winner": [1]}).to_csv(site / "matches.csv", index=False)
    pd.DataFrame({"match_key": ["4209:2026:MS001"], "tournament_group_id": ["4209"], "start_date": ["2026-09-07"],
                  "title": ["WTT W50 - GUIYANG, CHINA"], "level": ["ITF"], "surface": ["HARD"], "in_outdoor": ["O"],
                  "country": ["CHN"], "qpm_flag": ["M"], "round_name": ["R32"], "tourn_round": [1],
                  "winner_id": [330001], "winner_name": ["Yafan Wang"], "winner_country": ["CHN"],
                  "loser_id": [330002], "loser_name": ["Aleksandra Astakhova"], "loser_country": ["RUS"],
                  "scores": ["7-6(5)  7-5"], "reason_code": ["W"]}).to_parquet(api / "2026.parquet", index=False)
    rows, stats = F.load_wta_site()
    assert stats["misfiled_editions_left_out"] == 1
    assert len(rows) == 1
    r = rows.iloc[0]
    assert r["ev_name"] == "WTT W50 - GUIYANG, CHINA" and r["ev_level"] == "ITF" and r["ev_surface"] == "Hard"
    assert r["ev_key"] == f"wta_site:{guiyang}" and r["sid"].startswith("wta_site:api:")
