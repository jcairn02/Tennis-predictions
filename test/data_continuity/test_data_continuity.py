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


def test_canary_counts_matches_where_both_versions_are_held():
    """28 Oct 2026 (the owner: "fix the alarm"): a re-save with Unix line endings and corrected cells had raised SHRANK
    on 34 files that kept every match, the line endings counted in a copy the download had already replaced."""
    old = {"status": 200, "count": 1, "files": {"2024.csv": ["m1", 656519]}}
    cur = {"status": 200, "count": 1, "files": {"2024.csv": ["m2", 650000]}, "crlf": {"2024.csv": 0}}
    assert not any(f.startswith("SHRANK") for f in Q.flags("tml", None, NOW, {**cur, "rows": {"2024.csv": [3076, 3076]}},
                                                           old))
    assert "SHRANK (1 files hold fewer matches: 2024.csv 3076 -> 3075)" in Q.flags(
        "tml", None, NOW, {**cur, "rows": {"2024.csv": [3076, 3075]}}, old)
    assert not any(f.startswith("SHRANK") for f in Q.flags("tml", None, NOW, {**cur, "crlf_then": {"2024.csv": 6600}},
                                                           old))   # only the version listed then held: its endings
    assert "SHRANK (1 files smaller: 2024.csv)" in Q.flags("tml", None, NOW, {**cur, "crlf_then": {"2024.csv": 3077}}, old)


def _copy(path: Path, rows: int, crlf: bool, extra: str = "") -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    end = "\r\n" if crlf else "\n"
    path.write_bytes(end.join(["tourney_id,score"] + [f"2024-{i},6-4 6-4{extra}" for i in range(rows)]).encode() +
                     end.encode())
    return path.stat().st_size


def test_canary_finds_both_versions_among_the_projects_copies(tmp_path, monkeypatch):
    monkeypatch.setattr(Q, "TML_HELD", tmp_path)
    then = _copy(tmp_path / "superseded" / "2024.20261020143004.0123456789ab.csv", 3, True)
    now = _copy(tmp_path / "2024.csv", 3, False)                                  # re-saved, every match kept
    old = {"files": {"2024.csv": ["m1", then], "ongoing_tourneys.csv": ["m1", 9]}}
    cur = {"files": {"2024.csv": ["m2", now], "ongoing_tourneys.csv": ["m2", 1]}}
    assert Q.shrink_evidence(cur, old) == {"rows": {"2024.csv": [3, 3]}, "crlf_then": {}}
    lost = _copy(tmp_path / "2024.csv", 2, False)                                 # a match gone
    assert Q.shrink_evidence({"files": {"2024.csv": ["m2", lost]}}, old)["rows"] == {"2024.csv": [3, 2]}
    _copy(tmp_path / "2024.csv", 3, True)                                         # the download held the new version
    held = _copy(tmp_path / "held" / "2024.ba9876543210.csv", 1, False)
    assert Q.shrink_evidence({"files": {"2024.csv": ["m2", held]}}, old)["rows"] == {"2024.csv": [3, 1]}
    _copy(tmp_path / "2024.csv", 3, False, extra=" RET")                          # listed now: a version never fetched
    assert Q.shrink_evidence({"files": {"2024.csv": ["m2", then - 2]}}, old) == {"rows": {}, "crlf_then": {"2024.csv": 4}}
    q_then = _copy(tmp_path / "superseded" / "atp_quali" / "2026_atp_quali.20261020143004.0123456789ab.csv", 2, True)
    q_now = _copy(tmp_path / "atp_quali" / "2026_atp_quali.csv", 2, False)
    assert Q.shrink_evidence({"files": {"atp_quali/2026_atp_quali.csv": ["m2", q_now]}},
                             {"files": {"atp_quali/2026_atp_quali.csv": ["m1", q_then]}})["rows"] == {
        "atp_quali/2026_atp_quali.csv": [2, 2]}


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
