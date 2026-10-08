"""Offline tests of the Flashscore start-time link (src/eda/match_timing/link_flashscore.py and its helpers):
name keys, head-to-head feed entries, round labels, daily-board names, cities and zones, the local date, and the
choice of one Flashscore match per Stage 0 match (ambiguity, duplicate ids, one-to-one)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.match_timing import flashscore_names as N  # noqa: E402
from src.eda.match_timing import flashscore_parse as P  # noqa: E402
from src.eda.match_timing import flashscore_tz as Z  # noqa: E402
from src.eda.match_timing import link_flashscore as L  # noqa: E402


# ---------------------------------------------------------------- names

def shares_key(fs_name, slug, full):
    return bool((N.fs_strict_keys(fs_name, slug) | N.fs_loose_keys(fs_name)) & N.stage0_keys(full))


def test_surname_initial_forms_meet_full_names():
    assert N.fs_parts("Del Potro J. M.") == (("del", "potro"), "j")
    assert N.fs_parts("Wang Xiy.") == (("wang",), "x")
    assert N.fs_parts("Tsonga J.-W.") == (("tsonga",), "j")
    for fs_name, slug, full in [("Nishikori K.", "nishikori-kei", "Kei Nishikori"),
                                ("Del Potro J. M.", "", "Juan Martin Del Potro"),
                                ("Auger-Aliassime F.", "", "Felix Auger Aliassime"),
                                ("O'Connell C.", "oconnell-christopher", "Christopher O'Connell"),
                                ("Zhang S.", "", "Zhang Shuai"),            # written surname first
                                ("Son H. Y.", "son-ha-yoon", "Ha Yoon Son")]:
        assert shares_key(fs_name, slug, full), fs_name


def test_slug_key_ignores_order_and_married_name_needs_loose_key():
    assert "F:den guy ouden" in N.fs_strict_keys("Den Ouden G.", "guy-den-ouden")
    assert "F:den guy ouden" in N.stage0_keys("Guy Den Ouden")
    strict = N.fs_strict_keys("Zahlavova Strycova B.", "")
    assert not strict & N.stage0_keys("Barbora Strycova")
    assert "S:strycova b" in N.fs_loose_keys("Zahlavova Strycova B.")
    assert not N.fs_loose_keys("De Minaur A.") & {"S:de a"}                 # particles alone are no key


# ---------------------------------------------------------------- feed entries, labels

def test_feed_entry_winner_marker_and_fields():
    sep_f, sep_kv = P.SEP_F, P.SEP_KV
    chunk = sep_f.join(f"{k}{sep_kv}{v}" for k, v in [
        ("KC", "1776241800"), ("KP", "23MJBd1d"), ("KF", "W15 Monastir 11"), ("AC", "3"), ("KH", "Tunisia"),
        ("UQ", "jmQcRxm4"), ("UO", "z7fKYZz3"), ("KJ", "Son H. Y."), ("UE", "son-ha-yoon"), ("KK", "*Bedini V."),
        ("UG", "bedini-viola"), ("KU", "0"), ("KT", "2"), ("EC", "women"), ("ED", "abc.png")])
    blob = "SA" + sep_kv + "2" + sep_f + "~" + chunk + sep_f + "~"
    (kp, got), = list(P.feed_entries(blob))
    e = P.entry_tuple(P.entry_of(got))
    assert kp == "23MJBd1d" and e[0] == "23MJBd1d" and e[1] == 1776241800
    assert e[8:10] == ("Son H. Y.", "Bedini V.") and e[14] == "away"         # the asterisk marks the winner
    assert e[12:14] == (0, 2) and e[15:] == ("w", "")


def test_round_codes_and_daily_board_names():
    assert [P.round_code(x) for x in ["Final", "1/8-finals", "1/64-finals", "Quarter-finals", "", None]] == \
        ["F", "R16", "R128", "QF", None, None]
    assert P.split_daily_tournament("Tyler (USA) - Qualification, hard") == ("Tyler", "USA", "hard", "Qualification")
    assert P.split_daily_tournament("Rome (Italy), clay") == ("Rome", "Italy", "clay", None)


# ---------------------------------------------------------------- places and dates

def test_city_keys_and_zones():
    assert Z.city_key("W75+H Vero Beach, FL 2") == "vero beach" and Z.region_of("W75+H Vero Beach, FL 2") == "FL"
    assert Z.city_key("M15 Rancho Santa Fe, CA") == "rancho santa fe"
    assert Z.zone_of("USA", ["W25 Evansville, IN"]) == ("America/Chicago", "city (state code)")
    assert Z.zone_of("USA", ["M25 Pensacola, FL"])[0] == "America/Chicago"
    assert Z.zone_of("USA", ["US Open"])[0] == "America/New_York"
    assert Z.zone_of("USA", ["Lakewood"]) == (None, "city not known (USA, several zones)")
    assert Z.zone_of("ESP", ["W15 Telde 4"])[0] == "Atlantic/Canary"
    assert Z.zone_of("ESP", ["Madrid"])[0] == "Europe/Madrid"
    assert Z.zone_of("CHN", ["Wuhan"])[0] == "Asia/Shanghai"
    assert Z.itf_country("2023-M-ITF-THA-9A-2023") == "THA" and Z.itf_country("2019-7584") is None
    assert Z.ioc_of_fs_country("South Korea") == "KOR" and Z.ioc_of_fs_country("World") is None


def test_local_date_of_an_evening_match():
    # Acapulco 2015 final (Flashscore rRGryvhQ): 03:10 UTC on 1 March is 21:10 on 28 February in Acapulco
    start = pd.Series(pd.to_datetime([1425179400], unit="s", utc=True))
    zone, _ = Z.zone_of("MEX", ["Acapulco"])
    assert start.dt.tz_convert(zone).dt.date.iloc[0] == pd.Timestamp("2015-02-28").date()


# ---------------------------------------------------------------- choosing links

def cand(li, ri, tier=3, wa=2, ra=1, ca=1, strict=True, outside=0, dev=2.0, pref=0, start_key=0, gap=2):
    return dict(li=li, ri=ri, tier=tier, wa=wa, ra=ra, ca=ca, strict=strict, outside=outside, dev=dev, pref=pref,
                start_key=start_key, gap=gap)


def test_choose_ambiguity_duplicates_and_one_to_one():
    c = pd.DataFrame([
        cand(0, 10), cand(0, 11, tier=2),                          # clear winner: 10
        cand(1, 20, start_key=100), cand(1, 21, start_key=200),    # tie, different starts: ambiguous
        cand(2, 30, start_key=5, pref=0), cand(2, 31, start_key=5, pref=3),   # tie, same start: duplicate ids, 30 kept
        cand(3, 40), cand(4, 40, tier=2), cand(4, 41, tier=1),     # 40 goes to 3; 4 falls back to 41
        cand(5, 50, tier=0),                                       # unconfirmed: never linked
    ])
    kept, amb, dup, lost = L.choose(c)
    pairs = dict(zip(kept["li"], kept["ri"]))
    assert pairs == {0: 10, 2: 30, 3: 40, 4: 41}
    assert set(amb["li"]) == {1}
    assert set(dup["li"]) == {2} and set(dup["kept_ri"]) == {30}
    assert lost == set()
    assert kept["ri"].is_unique


def test_choose_reports_matches_left_without_a_free_candidate():
    c = pd.DataFrame([cand(0, 10), cand(1, 10, tier=2)])
    kept, amb, dup, lost = L.choose(c)
    assert dict(zip(kept["li"], kept["ri"])) == {0: 10} and lost == {1}


def test_pairs_frame_orientation():
    p = L.pairs_frame(np.array([7]), [[1, 5]], [[3]])
    assert set(p["pair"]) == {1 * (1 << 32) + 3, 3 * (1 << 32) + 5}
    row = p.set_index("pair").loc[3 * (1 << 32) + 5]
    assert not bool(row["first_lo"]) and not bool(row["eq"])                # first player's key 5 > 3
