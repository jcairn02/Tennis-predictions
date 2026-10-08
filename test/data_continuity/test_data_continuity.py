"""Offline tests for the data-continuity study: the contract's parsing and checks, the agreement measure, the source
readers' pure parts, the canary's flags and licence extraction, and the TML revision diff (no network, no data)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_continuity import canary as Q  # noqa: E402
from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.data_continuity import sources as R  # noqa: E402
from src.eda.data_continuity import tml_revisions as V  # noqa: E402


def box(**values):
    row = {c: np.nan for c in K.COUNTS}
    row.update(values)
    return K.finish(pd.DataFrame([row]))


def test_ratio_reads_sofascore_fractions_and_nothing_else():
    a, b = K.ratio(pd.Series(["38/52 (73%)", "0/0 (0%)", "12", None, "x/y"]))
    assert a.tolist()[:2] == [38.0, 0.0] and b.tolist()[:2] == [52.0, 0.0]
    assert np.isnan(a.iloc[2]) and np.isnan(a.iloc[3]) and np.isnan(b.iloc[4])


def test_finish_derives_serve_points_won_only_when_absent():
    assert box(first_won=30, second_won=12)["sv_won"].iloc[0] == 42
    given = K.finish(pd.DataFrame([{"first_won": np.nan, "second_won": np.nan, "sv_won": 40}]))
    assert given["sv_won"].iloc[0] == 40


def test_invariants_flag_each_impossible_count():
    ok = box(ace=3, df=2, svpt=60, first_in=36, first_won=26, second_won=12, sv_gms=10, bp_saved=3, bp_faced=5)
    assert not K.invariant_failures(ok).any(axis=1).iloc[0]
    cases = {
        "first_in_gt_svpt": dict(svpt=30, first_in=31),
        "first_won_gt_first_in": dict(first_in=20, first_won=21),
        "second_won_gt_second": dict(svpt=40, first_in=30, second_won=11),
        "bp_saved_gt_faced": dict(bp_saved=4, bp_faced=3),
        "df_gt_second": dict(svpt=40, first_in=35, df=6),
        "ace_gt_won": dict(ace=9, first_won=5, second_won=3),
        "breaks_gt_sv_gms": dict(bp_faced=9, bp_saved=1, sv_gms=7),
        "negative": dict(ace=-1),
    }
    for check, values in cases.items():
        assert K.invariant_failures(box(**values))[check].iloc[0], check


def test_agreement_counts_only_rows_where_both_values_exist():
    left = pd.DataFrame({"g": ["a", "a", "a", "b"], "ace": [1, 2, np.nan, 5], "df": [0, 0, 0, 0]})
    right = pd.DataFrame({"ace": [1, 4, 3, 6], "df": [0, 1, 0, np.nan]})
    out = K.agreement(left, right, ["g"], fields=["ace", "df"]).set_index(["g", "field"])
    assert out.loc[("a", "ace"), "n"] == 2 and out.loc[("a", "ace"), "equal"] == 1
    assert out.loc[("a", "ace"), "within1"] == 1 and out.loc[("a", "ace"), "mean_diff"] == 1.0
    assert out.loc[("b", "ace"), "within1_share"] == 1.0 and out.loc[("b", "df"), "n"] == 0
    assert np.isnan(out.loc[("b", "df"), "equal_share"])


def test_tdi_sets_won_reads_tiebreak_sets_and_ignores_unfinished_ones():
    assert R._sets_won("1:6 2:6", "1:3 2:0") == (2, 0)
    assert R._sets_won("1:6 2:6/3", "1:4 2:7/7") == (1, 1)
    assert R._sets_won("1:6 2:2", "1:3 2:1") == (1, 0)          # a retirement in the second set


def test_two_sides_orients_by_winner_and_maps_opponent_columns():
    wide = pd.DataFrame({"source_key": ["k1", "k2"], "winner": ["a", None], "ace_a": [5, 1], "ace_b": [2, 3],
                         "chances_a": [4, 0], "chances_b": [7, 2]})
    mapping = {"ace": lambda f, s, o: f[f"ace_{s}"], "bp_faced": lambda f, s, o: f[f"chances_{o}"]}
    out = R._two_sides(wide, "a", "b", mapping, "demo").set_index(["source_key", "side"])
    assert out.loc[("k1", "a"), "won"] == True and out.loc[("k1", "b"), "won"] == False  # noqa: E712
    assert pd.isna(out.loc[("k2", "a"), "won"])
    assert out.loc[("k1", "a"), "bp_faced"] == 7 and out.loc[("k1", "b"), "bp_faced"] == 4


def test_wta_winner_codes_cover_completed_retired_and_walkover_for_both_players():
    assert {k for k, v in R.WTA_WINNER.items() if v == "a"} == {"2", "4", "6"}
    assert {k for k, v in R.WTA_WINNER.items() if v == "b"} == {"3", "5", "7"}


NOW = pd.Timestamp("2026-10-06T12:00:00Z")


def test_canary_flags_gone_stale_and_archive_states():
    gone = Q.flags("x", None, NOW, {"status": 404, "software_heritage": {"last_full": {"date": "2026-05-08"}}}, None)
    assert gone == ["GONE"]
    stale = Q.flags("x", 10, NOW, {"status": 200, "newest_mtime": "2026-09-01T00:00:00Z"}, None)
    assert stale == ["STALE (35 days)"]
    assert Q.flags("x", 10, pd.Timestamp("2026-12-20T00:00:00Z"),
                   {"status": 200, "newest_mtime": "2026-11-01T00:00:00Z"}, None) == []   # December: off-season
    never = Q.flags("x", None, NOW, {"status": 200, "software_heritage": {"last_full": {"http": 404}}}, None)
    assert never == ["UNARCHIVED (no Software Heritage snapshot)"]
    old = Q.flags("x", None, NOW, {"status": 200, "software_heritage": {"last_full": {"date": "2025-01-03"}}}, None)
    assert old == ["UNARCHIVED (last Software Heritage snapshot 2025-01-03)"]
    unknown = Q.flags("x", None, NOW, {"status": 200, "software_heritage": {"last_full": {"error": "ConnectTimeout"}}}, None)
    assert unknown[0].startswith("ARCHIVE UNKNOWN")


def test_canary_flags_shrinking_revised_and_changed_terms():
    old = {"status": 200, "count": 3, "files": {"2024.csv": ["m1", 656519], "2026.csv": ["m1", 481307],
                                                "ongoing_tourneys.csv": ["m1", 23315]},
           "terms_sha256": "a"}
    cur = {"status": 200, "count": 3, "files": {"2024.csv": ["m2", 653442], "2026.csv": ["m2", 514108],
                                                "ongoing_tourneys.csv": ["m2", 12873]},
           "terms_sha256": "b"}
    got = Q.flags("tml", None, NOW, {**cur, "crlf": {"2024.csv": 3077}}, old)
    assert not any(f.startswith("SHRANK") for f in got)          # 3,077 bytes: exactly the copy's CRLF line endings
    assert "REVISED (1 earlier-season files: 2024.csv)" in got  # ongoing files shrink by design and are ignored
    assert "TERMS" in got
    lost_rows = Q.flags("tml", None, NOW, {**cur, "crlf": {"2024.csv": 0}}, old)
    assert "SHRANK (1 files smaller: 2024.csv)" in lost_rows      # a Unix-ended copy has no line endings to lose
    unheld = {**cur, "files": {**cur["files"], "2024.csv": ["m2", 600000]}}
    assert "SHRANK (1 files smaller: 2024.csv)" in Q.flags("tml", None, NOW, unheld, old)    # over 2%, not held
    fewer = Q.flags("tml", None, NOW, {**cur, "count": 2, "terms_sha256": "a"}, old)
    assert fewer[0] == "SHRANK (files 3 -> 2)"


def test_terms_statements_extract_declared_licences_only():
    html = ('<script>{"isAccessibleForFree":true,"license":"https://opensource.org/licenses/MIT"}</script>'
            '<p><strong>License:</strong> MIT License<br/></p><p>Updated 6 Oct</p>')
    assert Q.terms_statements(html, True) == ["license text: MIT License",
                                              "license url: https://opensource.org/licenses/MIT"]
    md = "# TML\nAll data usage is **non-commercial** unless explicitly permitted.\nUpdated daily.\n"
    assert Q.terms_statements(md, False) == ["All data usage is **non-commercial** unless explicitly permitted."]


def test_revision_diff_separates_corrections_from_additions_and_removals():
    cols = ["tourney_id", "tourney_date", "round", "winner_id", "loser_id", "score"]
    old = pd.DataFrame([["2024-418", "20240729", "QF", "S0S1", "S0H2", "7-6(5) 6-6 RET"],
                        ["2024-418", "20240729", "SF", "S0S1", "X1", "6-4 6-4"],
                        ["2024-418", "20240729", "F", "S0S1", "X2", "6-1 6-1"]], columns=cols)
    new = pd.DataFrame([["2024-418", "20240729", "QF", "S0S1", "S0H2", "7-6(5) 6-6 DEF"],
                        ["2024-418", "20240729", "SF", "S0S1", "X1", "6-4 6-4"],
                        ["2026-339", "20260929", "R32", "A", "B", "6-3 6-3"]], columns=cols)
    stats, cells = V.diff(old, new)
    assert (stats["added"], stats["removed"], stats["corrected"]) == (1, 1, 1)
    assert dict(cells) == {"score": 1} and stats["rows_old"] == stats["rows_new"] == 3
