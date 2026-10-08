"""The summary: the corners and their comparison with Stage 4 (summary_results.py), and the number check
(summary_number_check.py).

The corners are checked on hand-made points: each corner, the borderline rule and the gap around the line for
"decides". The comparison is checked on hand-made Stage 4 rows. The number check's parts are checked one by one: how a
printed number is read and classed, the tour, years and level its context names, the tagged numbers that carry their
JSON path through arithmetic and formatting, the search of JSON values, and the planted exchange the self-test uses.
"""
import json
import math
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import report_summary as RS  # noqa: E402
from src.eda.predictability_diagnostic import summary_number_check as NC  # noqa: E402
from src.eda.predictability_diagnostic import summary_results as SR  # noqa: E402


# ------------------------------------------------------------------------------------------------ the corners
def test_corner_of_names_the_four_corners():
    assert SR.corner_of(0.8, 500, 0.5, 173.3) == "trait"
    assert SR.corner_of(0.9, 20, 0.5, 173.3) == "style"
    assert SR.corner_of(0.4, 693, 0.5, 173.3) == "luck"
    assert SR.corner_of(0.1, 80, 0.5, 173.3) == "noise"
    assert SR.corner_of(0.5, 173.3, 0.5, 173.3) == "trait"       # on a line counts as reaching it


def test_borderline_is_a_range_that_holds_the_line():
    assert SR.borderline(0.46, 0.54, 0.5)
    assert not SR.borderline(0.51, 0.6, 0.5)
    assert not SR.borderline(None, 0.6, 0.5)


def test_gaps_give_the_nearest_statistics_on_either_side_of_the_line():
    pts = [{"tour": t, "stat": s, "impact_all": a, "impact_defined": d} for t in ("atp", "wta")
           for s, a, d in (("x", 85.0, 94.0), ("y", 247.0, 247.0), ("z", 74.0, 228.0))]
    g = {(r["tour"], r["basis"]): r for r in SR.gaps(pts, 173.3)}
    assert (g[("atp", "all")]["below_max"], g[("atp", "all")]["above_min"]) == (85.0, 247.0)
    assert (g[("atp", "defined")]["below_stat"], g[("atp", "defined")]["above_stat"]) == ("x", "z")


def stage4_rows(tour, stat, readings, alone="moderate", sign=0.05):
    gains = {"career": 0.1, "52 weeks": 0.5, "decayed": 0.3, "surface": 0.2, "adjusted": 0.0}
    return [{"tour": tour, "id": stat, "form": f, "reading": r, "elo_imp": gains[f], "elo_lo": 0.0, "elo_hi": 1.0,
             "elo_2019-2026": 0.1, "elo_2022-2026": 0.1, "elo_clears_line": r == "finding", "eras_positive": 3,
             "eras_scored": 4, "sign_coef": sign, "alone_imp": 20.0, "alone_observed": alone, "market_imp": 0.0,
             "market_lo": -1.0, "market_hi": 1.0, "market_above_band": False, "market_below_band": False,
             "market_clears_line": False, "elo_coverage": 1.0, "rank_given_elo": 1.0}
            for f, r in zip(SR.FORMS, readings)]


def test_against_stage4_reads_each_corner_s_expectation():
    s4 = {"ranking": stage4_rows("atp", "a", ["worse", "finding", "possible", "worse", "worse"])
          + stage4_rows("atp", "b", ["no sign"] * 5, alone="weak")
          + stage4_rows("atp", "c", ["no sign", "finding", "no sign", "no sign", "no sign"], alone="weak", sign=-0.04)
          + stage4_rows("atp", "d", ["worse"] * 5, alone="strong")}
    pts = [{"tour": "atp", "stat": s, "label": s, "corner_all": c, "corner_defined": c, "borderline": False, "in_match_sign": 1}
           for s, c in (("a", "trait"), ("b", "style"), ("c", "noise"), ("d", "luck"))]
    comp = {c["stat"]: c for c in SR.against_stage4(pts, s4)}
    assert comp["a"]["elo_agrees"] and comp["a"]["alone_agrees"]            # a trait with a finding
    assert comp["b"]["elo_agrees"] and comp["b"]["alone_agrees"]            # style: no finding, weak alone
    assert not comp["c"]["elo_agrees"] and comp["c"]["findings_reversed"] == 1   # noise with a reversed finding
    assert comp["d"]["elo_agrees"] and not comp["d"]["alone_agrees"]        # luck that predicts strongly alone
    assert comp["a"]["best_elo"]["form"] == "52 weeks" and comp["a"]["worse_forms"] == ["career", "surface", "adjusted"]
    pts[2]["in_match_sign"] = -1                      # where less is better, a negative sign is not reversed
    assert [c["findings_reversed"] for c in SR.against_stage4(pts, s4) if c["stat"] == "c"] == [0]
    tal = SR.tallies(list(comp.values()))
    assert (tal["atp|trait"]["statistics"], tal["atp|other"]["elo_agree"], tal["all|alone_agree"]) == (1, 2, 3)


def test_both_writes_one_figure_when_the_tours_print_alike():
    assert RS.both("28%", "28%") == "28%"
    assert RS.both("0.06", "0.06", " on both tours") == "0.06 on both tours"
    assert RS.both("28%", "29%") == "28% (men) and 29% (women)"
    m = NC.MARK
    assert RS.both(f"0.3%{m}1{m}", f"0.3%{m}2{m}") == f"0.3%{m}1{m}"         # the number check's tags are not printed


def test_every_candidate_sits_in_one_family_and_sizes_read_plainly():
    ids = [i for _, _, _, family in SR.FAMILIES for i in family]
    assert len(ids) == len(set(ids)) == 59
    assert [RS.size_word(x) for x in (0.28, 0.09, 0.03, 0.006)] == ["the best", "yes", "a little", "negligible"]
    assert (RS.pc(0.28), RS.pc(0.006), RS.width(1.4), RS.width(-0.1)) == ("28%", "0.6%", "100.0", "0.0")


# ------------------------------------------------------------------------------------------------ the number check
def tok(text):
    m = next(NC.NUM_RE.finditer(text))
    return NC.parse(m), text


def test_parse_reads_sign_separators_decimals_and_percent():
    t, _ = tok("better by −1,234.56% overall")
    assert (t["value"], t["decimals"], t["percent"], t["signed"]) == (-1234.56, 2, True, True)
    assert math.isclose(t["half"], 0.005)
    t, _ = tok("difference 1.1e-14 here")
    assert math.isclose(t["value"], 1.1e-14)
    assert [m.group(0) for m in NC.NUM_RE.finditer("R32, Q1, W15, stage0_summary and 2nd")] == []


@pytest.mark.parametrize("text,kind", [
    ("seasons 2013–2026", "year"), ("2013–16", "year"), ("Stage 4 found", "stage"), ("250 qualifying", "level name"),
    ("the WTA's 1000, 500", "level name"), ("atp|2026-600|R32|atp:200266", "identifier"), ("(95% range 0.1 to 0.2)", "range level"),
    ("3.61 better", "value"),
])
def test_kind_of_classes_what_is_not_a_result(text, kind):
    item = {"svg": None}
    ms = list(NC.NUM_RE.finditer(text))
    m = ms[-1] if kind in ("identifier",) or text.startswith("the WTA") else ms[0]
    if text == "2013–16":
        m = ms[1]
    assert NC.kind_of(item, NC.parse(m), text) == kind


def test_kind_of_axis_and_heading():
    t, text = tok("0.25")
    assert NC.kind_of({"svg": ""}, t, text) == "axis"
    t, text = tok("1. Repeats against decides")
    assert NC.kind_of({"svg": None, "heading": True}, t, text) == "heading"


def test_tour_hint_reads_the_context_and_not_level_names():
    assert NC.tour_hint({}, " (women) and") == "wta"
    assert NC.tour_hint({}, " for the men") == "atp"
    assert NC.tour_hint({}, " (men 2.19 against 5.05)") is None          # a parenthesis about other numbers
    assert NC.tour_hint({"group": "ATP (men)"}, "") == "atp"
    assert NC.tour_hint({"row": "Challenger / WTA 125"}, "") is None
    assert NC.tour_hint({"col": "WTA | Alone"}, "") == "wta"
    assert NC.tour_hint({"col": "Men | Consistent"}, "") == "atp"             # a header in capitals
    assert NC.tour_hint({"chart": "Women (WTA)"}, "") == "wta"
    assert NC.tour_hint({"row": "Women's singles | Men's singles"}, "") is None   # both named: no single tour
    assert NC.tour_hint({"row": "atp|2026-600|R32"}, "") is None              # an id is not a tour


def test_tour_of_reads_tour_keys_and_lists_under_them():
    assert NC.tour_of("s.json.rows[tour=atp,window=2022-2026].v") == "atp"
    assert NC.tour_of("summary.points.wta[stat=ace,label=Aces].rel") == "wta"
    assert NC.tour_of("s.json.tours.atp.best") == "atp"
    assert NC.tour_of("s.json.pairs[tour=atp].other.wta.x") is None


def test_years_and_levels_named_and_in_paths():
    assert NC.years_named("Room | 2022–26") == {(2022, 2026)}
    assert NC.years_named("season 2013 | 2019–2026") == {(2013, 2013), (2019, 2026)}
    assert NC.years_in_path("x.rows[tour=atp,window=2022-2026 (headline)].p") == {(2022, 2026)}
    assert NC.years_in_path("x[era=2013-16,n=5]") == {(2013, 2016)}
    assert NC.level_named("Grand Slams | ATP") == "GS"
    assert NC.level_named("Grand Slam qualifying") == "GSQ"
    assert NC.levels_in_path("x[tour=atp,level=CH,qualifying=True]") == {"CHQ"}


def test_context_checks_flag_the_other_tour_window_and_level():
    r = {"tour": "atp", "header": "Grand Slams | 2022–2026"}
    good = [("s.json.rows[tour=atp,window=2022-2026,level=GS].v", 1.0, "atp")]
    assert NC.context_checks(r, good) == []
    assert NC.context_checks(r, [("s.json.rows[tour=wta,window=2022-2026,level=GS].v", 1.0, "wta")])
    assert NC.context_checks(r, [("s.json.rows[tour=atp,window=2013-2026,level=GS].v", 1.0, "atp")])
    assert NC.context_checks(r, [("s.json.rows[tour=atp,window=2022-2026,level=T250].v", 1.0, "atp")])


def test_tagged_numbers_keep_their_paths_through_arithmetic_and_formatting():
    doc = NC.tagged({"rows": [{"tour": "atp", "x": 0.25, "count": 1234}, {"tour": "wta", "x": 0.5, "count": 10}]}, "f.json")
    a, b = doc["rows"]
    s = f"{100 * a['x']:.1f}% of {a['count'] + b['count']:,} and {a['x']} plain"
    text, marks = NC.strip_tags(s)
    assert text == "25.0% of 1,244 and 0.25 plain"                   # a plain '{x}' is never tagged
    assert len(marks) == 2
    share, total = (NC.PROV[i] for _, i in marks)
    assert share[1] == ("f.json.rows[tour=atp].x",) and math.isclose(share[2], 25.0)
    assert set(total[1]) == {"f.json.rows[tour=atp].count", "f.json.rows[tour=wta].count"} and total[2] == 1244
    assert isinstance(NC._t_round(a["x"] * 4), NC.TI) and NC._t_float(a["count"]).leaves == a["count"].leaves


def test_index_finds_values_at_a_scale_and_two_leaf_values_exactly(tmp_path, monkeypatch):
    (tmp_path / "s.json").write_text(json.dumps({"rows": [{"tour": "atp", "p": 0.6, "q": 0.25}, {"tour": "wta", "p": 0.59, "q": 0.3}]}))
    monkeypatch.setattr(NC.C, "OUT", tmp_path)
    idx = NC.Index(["s.json"])
    assert [idx.paths[i] for i in idx.find(25.0, 0.05, 100.0)] == ["s.json.rows[tour=atp].q"]
    ex = idx.exact(math.log(2) - 0.6)
    assert ex and ex[0][0].startswith("ln 2 − s.json.rows[tour=atp].p") and ex[0][2] == "atp"
    assert idx.exact(-0.25, signed=False)[0][0] == "s.json.rows[tour=atp].q"
    assert idx.exact(-0.25) == []


def test_swap_exchanges_the_key_field_of_the_matched_records_only():
    doc = {"h": [{"tour": "atp", "w": "a", "v": 1}, {"tour": "wta", "w": "a", "v": 2}, {"tour": "atp", "w": "b", "v": 3}]}
    NC.swap(doc, {"list": ["h"], "match": {"w": "a"}, "field": "tour", "values": ["atp", "wta"]})
    assert [(r["tour"], r["v"]) for r in doc["h"]] == [("wta", 1), ("atp", 2), ("atp", 3)]
