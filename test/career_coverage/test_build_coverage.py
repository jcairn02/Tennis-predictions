"""Parsing and matching rules of the career-coverage study (offline)."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "career_coverage"))

import build_coverage as B  # noqa: E402


def test_quarter_final_is_not_qualifying():
    assert B.level_of("FU", "QF") == "ITF main draw"
    assert B.level_of("FU", "Q1") == "ITF qualifying"
    assert B.level_of("CH", "Q3") == "Challenger qualifying"
    assert B.level_of("CH", "F") == "Challenger main draw"
    assert B.level_of("GS", "Q2") == "Tour qualifying"
    assert B.level_of("GS", "R128") == "Tour main draw"
    assert B.level_of("DC", "RR") == "Davis Cup"


def test_round_code_maps_title_win_to_final():
    assert B.round_code("W") == "F"
    assert B.round_code(" qf ") == "QF"


def test_name_score_tolerates_spelling_but_not_other_people():
    assert B.name_score("Tsung-Hao", "Huang", "Tsung Hao Huang") == 3
    assert B.name_score("François", "Musitelli", "Francois Musitelli") == 3
    assert B.name_score("Aidan", "McHugh", "Aidan Mchugh") == 3
    assert B.name_score("Toby", "Kodat", "Toby Alex Kodat") == 2
    assert B.name_score("Alejandro", "Tabilo", "A Tabilo") == 1
    assert B.name_score("Alessandro", "Pecci", "Andrea Pellegrino") == 0
    assert B.name_score("Alessandro", "Pecci", "") == 0


def test_itf_start_handles_events_crossing_new_year():
    assert B.itf_start("18 Dec to 24 Dec 2023") == pd.Timestamp("2023-12-18")
    assert B.itf_start("30 Dec to 05 Jan 2025") == pd.Timestamp("2024-12-30")
    assert pd.isna(B.itf_start(""))


def test_parse_atp_file_reads_shifted_tails_skips_byes_and_reattaches_misplaced_lines(tmp_path):
    f = tmp_path / "G0BY_2025.txt"
    f.write_text("\n".join([
        "T|8297|Hamburg|CH|2025-10-20|Hard|I|32|274|4|2",
        "M|en/scores/match-stats/archive/2025/8297/ms012|R16|Round of 16|L|L0CF|George|Loffhagen|GBR|215|||W/O|false",
        "M|en/scores/match-stats/archive/2025/8297/ms025|R32|Round of 32|W|V09T|Pedro|Vives Marcos|ESP|517|6-4 6-1|||true",
        "T|7235|Drummondville|CH|2025-11-10|Hard|I|32|247|75|2",
        "M|en/scores/match-stats/archive/2025/7235/ms001|W|Winner|W|C0OF|Duncan|Chan|CAN|1440|6-4 6-2|||true",
        "M|en/scores/match-stats/archive/2025/8297/ms030|R32|Round of 32|W|X1|Some|One|ESP|1|6-1 6-1||false|true",
        "M|en/scores/match-stats/archive/2025/7235/ms040|R32|Round of 32|W|||||||true|true",
    ]), encoding="utf-8")
    issues = []
    events, matches = B.parse_atp_file("G0BY", 2025, f, issues)
    assert len(events) == 2
    by_url = {m["url"].rsplit("/", 1)[-1]: m for m in matches}
    assert by_url["ms012"]["reason"] == "W/O" and by_url["ms012"]["score"] == ""
    assert by_url["ms025"]["has_stats_atp"] is True and by_url["ms025"]["score"] == "6-4 6-1"
    assert by_url["ms001"]["round"] == "F"
    assert by_url["ms030"]["event_id"] == "8297" and by_url["ms030"]["event_name"] == "Hamburg"
    assert by_url["ms040"]["is_bye"] is True
    assert any("re-attached" in i for i in issues)


def test_parse_itf_maps_qualifying_rounds_and_drops_byes(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "ITF_RAW", tmp_path)
    (tmp_path / "P0HY_2023.txt").write_text("\n".join([
        "E|M15 Perugia|ITF|ITF World Tennis Tour|/en/tournament/m15-perugia/ita/2023/m-itf-ita-16a-2023/|24 Jul to 30 Jul 2023|C|Qualifying Draw|DA|3",
        "X|1169663423|3rd Round|W||Daniel|Bagnolini|ITA|800457746|6-2 3-6 10-0",
        "X|1169663434|2nd Round|W||Antonio|Caruso|ITA|800592578|6-2 7-6(7)",
        "X|1169663456|1st Round|B|||||||",
        "E|M15 Perugia|ITF|ITF World Tennis Tour|/en/tournament/m15-perugia/ita/2023/m-itf-ita-16a-2023/|24 Jul to 30 Jul 2023|C|Main Draw|Q|1",
        "X|1169663401|2nd Round|L||Luca|Tomasetto|ITA|800338823|4-6 6-3 2-6",
        "END|totalItems=1",
    ]), encoding="utf-8")
    itf, issues = B.parse_itf(["P0HY"])
    assert issues == []
    assert list(itf["round"]) == ["Q3", "Q2", "R16"]
    assert list(itf["level"]) == ["ITF qualifying", "ITF qualifying", "ITF main draw"]
    assert itf["itf_key"].iloc[0] == "m-itf-ita-16a-2023"
    assert (itf["event_date"] == pd.Timestamp("2023-07-24")).all()


def test_season_files_prefer_split_versions_and_add_fixes(tmp_path):
    for name in ("H0A4_2019.txt", "H0A4_2019_a.txt", "H0A4_2019_b.txt", "H0A4_2020.txt", "H0A4_2020_fix1.txt",
                 "H0A4_2021_p0.txt", "H0A4_2021_p1.txt", "H0A4_id.txt"):
        (tmp_path / name).write_text("", encoding="utf-8")
    files = B.season_files(tmp_path, "H0A4")
    assert [f.name for f in files[2019]] == ["H0A4_2019_a.txt", "H0A4_2019_b.txt"]
    assert [f.name for f in files[2020]] == ["H0A4_2020.txt", "H0A4_2020_fix1.txt"]
    assert [f.name for f in files[2021]] == ["H0A4_2021_p0.txt", "H0A4_2021_p1.txt"]
    assert set(files) == {2019, 2020, 2021}


def test_davis_cup_rubbers_sharing_a_url_are_both_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "ATP_RAW", tmp_path)
    (tmp_path / "H0A4_2021.txt").write_text("\n".join([
        "T|9616|G2 TUN vs DOM Round 1|DC|2021-09-13|Hard|O|4|355|0|2",
        "M|en/scores/match-stats/archive/2021/9616/ms000|RR|Round Robin|L|DF88|Aziz|Dougaz|TUN|335|3-6 2-6||false|false",
        "M|en/scores/match-stats/archive/2021/9616/ms000|RR|Round Robin|W|J267|Malek|Jaziri|TUN|272|4-6 6-1 6-5|RET|false|false",
        "M|en/scores/match-stats/archive/2021/9616/ms000|RR|Round Robin|W|J267|Malek|Jaziri|TUN|272|4-6 6-1 6-5|RET|false|false",
    ]), encoding="utf-8")
    atp, _, issues = B.parse_atp(["H0A4"])
    assert sorted(atp["opp_last"]) == ["Dougaz", "Jaziri"]
    assert atp["ref_id"].is_unique
    assert any("repeated" in i for i in issues)


def test_fix_file_replaces_or_removes_tournaments(tmp_path):
    (tmp_path / "CH12_2018.txt").write_text("\n".join([
        "T|5067|Savannah|CH|2018-04-30|Clay|O|32|300|0|2",
        "M|en/scores/match-stats/archive/2018/5067/qs005|Q3|3rd Round Qualifying|L|A1|Ann|One|USA|300|3-6 3-6||false|true",
        "M|en/scores/match-stats/archive/2018/5067/ms023|R32|Round of 32|L|B2|Bob|Two|USA|200|4-6 4-6||false|true",
        "T|9999|Invented|CH|2018-05-07|Clay|O|32|300|0|1",
        "M|en/scores/match-stats/archive/2018/9999/ms001|R32|Round of 32|W|C3|Cy|Three|USA|200|6-1 6-1||false|true",
        "T|1111|Kept|CH|2018-05-14|Clay|O|32|300|0|1",
        "M|en/scores/match-stats/archive/2018/1111/ms002|R32|Round of 32|W|D4|Di|Four|USA|200|6-2 6-2||false|true",
    ]), encoding="utf-8")
    (tmp_path / "CH12_2018_fix1.txt").write_text("\n".join([
        "T|5067|Savannah|CH|2018-04-30|Clay|O|32|300|0|1",
        "M|en/scores/match-stats/archive/2018/5067/ms023|R32|Round of 32|L|B2|Bob|Two|USA|200|4-6 4-6||false|true",
        "NONE|9999",
    ]), encoding="utf-8")
    files = B.season_files(tmp_path, "CH12")[2018]
    kept = B.season_matches("CH12", 2018, files, [])
    assert sorted((m["event_id"], m["url"].rsplit("/", 1)[-1]) for m in kept) == [("1111", "ms002"), ("5067", "ms023")]


def test_played_match_mislabelled_as_bye_is_kept(tmp_path):
    f = tmp_path / "CH12_2014.txt"
    f.write_text("\n".join([
        "T|3628|Trnava|CH|2014-09-22|Clay|O|32|500|0|1",
        "M|en/scores/match-stats/archive/2014/3628/ms022|R32|Round of 32|L|X9|Some|One|SVK|200|1-6 0-6||true|true",
        "M|en/scores/match-stats/archive/2014/3628/qs001|Q1|1st Round Qualifying|W||||||||true|false",
    ]), encoding="utf-8")
    _, ms = B.parse_atp_file("CH12", 2014, f, [])
    assert [m["is_bye"] for m in ms] == [False, True]


def test_walkover_recognised_in_reason_or_score_field(tmp_path):
    f = tmp_path / "P0I6_2024.txt"
    f.write_text("\n".join([
        "T|4472|M25 Somewhere|FU|2024-05-06|Clay|O|32|500|1|2",
        "M|en/scores/match-stats/archive/2024/4472/ms003|QF|Quarter-Finals|L|A1|Ann|Other|ITA|300|W/O|||false",
        "M|en/scores/match-stats/archive/2024/4472/ms010|R16|Round of 16|W|B2|Bob|Other|ITA|400|4-6 1-0|RET||false",
    ]), encoding="utf-8")
    _, ms = B.parse_atp_file("P0I6", 2024, f, [])
    ref = pd.DataFrame(ms).assign(depth=0, event_date=pd.Timestamp("2024-05-06"), level="ITF main draw",
                                  code="P0I6", event_name="M25 Somewhere", ref_id=["a", "b"])
    graded = B.grade(ref, pd.DataFrame(columns=["link", "ref_id", "source", "has_box", "has_points", "score_states",
                                                "has_odds", "has_prices"]))
    assert list(graded["walkover"]) == [True, False]


def test_name_score_accepts_transliterations_sharing_a_long_token():
    assert B.name_score("Nikita", "Mashtakov", "Mykyta Mashtakov") == 1
    assert B.name_score("Mukund", "Sasikumar", "Sasi Kumar Mukund") == 1
    assert B.name_score("Joao", "Graca", "Joao Graa") == 1
    assert B.name_score("Dimitris", "Azoidis", "Demetris Azoides") == 1
    assert B.name_score("Milan", "Welte", "Alexandre Aubriot") == 0


def test_games_orients_a_loss_winner_first_and_drops_tiebreak_points():
    assert B.games("6-7(5) 6-3 4-6", flip=True) == ((7, 6), (3, 6), (6, 4))
    assert B.games("7-6(3) 6-1") == ((7, 6), (6, 1))
    assert B.games("W/O") == ()
