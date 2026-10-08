"""The TDI Tennis Results adapter: listings, the id index, match pages, the 404 rule and staging (offline).

Fixtures are cut from pages the research session saved on 24 Sep 2026, re-serialised as one RSC push. Listings keep
the cards' own rows and the rows they reference, with the filter lists shortened:
    tdi_listing_date_2026_06_24.html          ?date=2026-06-24, in the window then: two singles cards (Draper, and
                                              Diallo with two tiebreaks) and two doubles cards (one whose players
                                              and scores sit in lazy "$L" rows)
    tdi_listing_date_2026_05_18_outside.html  ?date=2026-05-18, outside the window: answered with the default
                                              listing (two cards of 24 Sep; Safiullin's shows no country)
Match pages keep the rows reachable from the header and the Summary tab (the match and set 1), the metadata and
the points of set 1's first two games, without class names, SVG paths or translations; each parses as its whole
page does:
    tdi_match_2026_challenger_200.html          Comesana v Estevez, Buenos Aires Challenger, 22 Sep 2026 (200)
    tdi_match_2025_tour_404.html                Tiafoe v Walton, Brisbane, 31 Dec 2024 (404 with every point)
    tdi_match_2025_challenger_no_outcomes.html  Holt v Trongcharoenchaikul, Nonthaburi 3, Jan 2025
    tdi_match_2025_challenger_doubles.html      Damm/Rybakov v Maloney/Martinez, Winston-Salem, Sep 2025
"""
import gzip
import json
import sys
import types
from collections import Counter
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "official_point_feeds"))

import verify_tdi as V  # noqa: E402
from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402
from src.ingest.point_sources import tdi as T  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
IN_WINDOW = "tdi_listing_date_2026_06_24.html"
OUTSIDE = "tdi_listing_date_2026_05_18_outside.html"


def rows_of(name: str) -> dict:
    return T.page_rows((FIXTURES / name).read_text(encoding="utf-8"))[0]


def cards_of(name: str) -> dict:
    return {c["match_id"]: c for c in T.listing_cards(rows_of(name))}


# the RSC payload ----------------------------------------------------------------------
def test_push_strings_are_decoded_and_joined_even_with_an_escaped_quote_before_brackets():
    text = '0:["a"]\n1:{"b":"x\\"])y"}\n'
    html = "".join(f"<script>self.__next_f.push([1,{json.dumps(part)}])</script>" for part in (text[:10], text[10:]))
    joined, undecoded = T.rsc_text(html)
    assert (joined, undecoded) == (text, 0)
    assert T.rsc_rows(joined) == {"0": ["a"], "1": {"b": 'x"])y'}}


def test_text_rows_are_skipped_by_byte_length_and_the_next_row_still_read():
    text = '2:T6,héllo3:["$","p",null,{"children":"ok"}]\n4:I["x"]\n5:"$undefined"\n'
    rows = T.rsc_rows(text)
    assert rows["2"] == "héllo"  # six bytes in UTF-8, no newline after a text row
    assert rows["3"] == ["$", "p", None, {"children": "ok"}]
    assert "4" not in rows and rows["5"] == "$undefined"


# cards ---------------------------------------------------------------------------------
def test_singles_card_reads_round_tournament_stamp_players_scores_and_winner():
    card = cards_of(IN_WINDOW)["9a7322be-7fae-4997-bf8f-bb197e821be0"]
    assert (card["round"], card["tournament"], card["stamp"], card["stamp_day"]) == \
        ("Round of 16", "Lexus Eastbourne Open", "2026-06-24T16:12:33.456Z", "2026-06-24")
    assert (card["draw_type"], card["players"]) == ("singles", 2)
    assert (card["team1_player_ids"], card["team1_names"], card["team1_countries"]) == \
        ("435dacd2-5d8b-4440-b3da-9bf0f81e8268", "J.Draper", "GBR")
    assert (card["team2_names"], card["team1_scores"], card["team2_scores"]) == ("J.Pinnington Jones", "1:7 2:6", "1:5 2:4")
    assert (card["team1_winner_mark"], card["team2_winner_mark"]) == (True, False)


def test_tiebreak_points_and_seeds_are_kept():
    card = cards_of(IN_WINDOW)["0783d04c-3403-4ca0-94e8-2bf984432705"]
    assert (card["team1_scores"], card["team2_scores"]) == ("1:6/11 2:6 3:6", "1:7/13 2:3 3:2")
    assert (card["team1_entry"], card["team2_entry"]) == (None, "4")


def test_doubles_cards_group_four_players_into_two_teams_following_lazy_rows():
    cards = cards_of(IN_WINDOW)
    eastbourne = cards["8c1b536b-03fa-4f0b-a6af-c9fe7bc25e76"]
    assert (eastbourne["draw_type"], eastbourne["players"]) == ("doubles", 4)
    assert (eastbourne["team1_names"], eastbourne["team2_names"]) == ("D.Stevenson;M.Willis", "C.Harrison;N.Skupski")
    assert (eastbourne["team2_countries"], eastbourne["team2_entry"], eastbourne["team2_scores"]) == ("USA;GBR", "2", "1:6 2:7/7")
    plovdiv = cards["b4173b1c-4a36-479d-b836-6450cb05a1ca"]  # A.Ganchev's scores and A.Genov's row are "$L" rows
    assert (plovdiv["team1_names"], plovdiv["team1_entry"]) == ("S.Banthia;A.Donski", "1")
    assert (plovdiv["team2_names"], plovdiv["team2_scores"], plovdiv["team2_winner_mark"]) == ("A.Ganchev;A.Genov", "1:6 2:6", True)
    assert len(plovdiv["team2_player_ids"].split(";")) == 2


def test_a_player_without_a_country_keeps_his_name():
    card = cards_of(OUTSIDE)["d74c5847-c489-4a7a-8895-ca6fea9fcfc3"]
    assert (card["team2_names"], card["team2_countries"]) == ("R.Safiullin", None)


def test_filter_lists_are_found_by_their_keys():
    lists = T.filter_lists(rows_of(IN_WINDOW))
    assert lists["tournaments"][0] == {"id": "bcf52306-a13b-45c0-9547-8d26706e5807", "title": " Buenos Aires Challenger",
                                       "city": "Buenos Aires"}
    assert "435dacd2-5d8b-4440-b3da-9bf0f81e8268" in {p["id"] for p in lists["players"]}  # Draper's card key


# validating a listing -----------------------------------------------------------------
def test_a_date_listing_is_in_the_window_only_when_every_stamp_is_on_that_day():
    assert T.date_listing_status("2026-06-24", T.listing_cards(rows_of(IN_WINDOW))) == "in_window"
    outside = T.listing_cards(rows_of(OUTSIDE))
    assert T.date_listing_status("2026-05-18", outside) == "outside_window"  # the default listing, stamped 24 Sep
    assert T.date_listing_status("2026-09-24", outside) == "in_window"
    assert T.date_listing_status("2026-06-24", [{"stamp_day": "2026-06-24"}, {"stamp_day": "2026-06-25"}]) == "mixed"
    assert T.date_listing_status("2026-06-24", []) == "empty"
    assert T.stamp_day("$D2026-06-24T23:59:59.000Z") == "2026-06-24" and T.stamp_day(None) is None


def test_a_tournament_listing_shows_one_tournament_named_as_in_the_filter():
    cards = [{"tournament": "PLOVDIV CHALLENGER"}, {"tournament": "Plovdiv  Challenger"}]
    assert T.tournament_listing_status(" Plovdiv Challenger", cards) == ("one_tournament", True)
    assert T.tournament_listing_status("Sofia", cards + [{"tournament": "Other"}]) == ("several_tournaments", False)
    assert T.tournament_listing_status("x", []) == ("empty", None)


# sweeps: names, plans, resuming ---------------------------------------------------------
SWEEP = {"sweep": "20260925T1422Z", "first_day": "2026-06-22", "last_day": "2026-09-25", "settle_days": 3}


def test_settled_days_are_read_once_ever_and_recent_days_once_per_sweep():
    days = T.plan_days(SWEEP)
    assert (days[0], days[-1], len(days)) == ("2026-06-22", "2026-09-25", 96)
    assert T.date_name("2026-09-21", SWEEP) == "list/date/2026-09-21"
    assert T.date_name("2026-09-22", SWEEP) == "list/date/2026-09-22@20260925T1422Z"
    assert T.home_name(SWEEP) == "list/home/20260925T1422Z"
    assert T.tournament_name("abc", SWEEP) == "list/tournament/abc@20260925T1422Z"
    dest = T.listing_dest("list/date/2026-09-22@20260925T1422Z")
    assert dest.parts[-3:] == ("listings", "date", "2026-09-22@20260925T1422Z.html.gz")


def sweep_args(**kw):
    return types.SimpleNamespace(**{"sweep": None, "new_sweep": False, "days_back": 95, "settle_days": 3,
                                    "recent": None, **kw})


def test_an_unfinished_sweep_is_resumed_with_its_own_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "SWEEPS", tmp_path / "_sweeps.jsonl")
    first = T.open_sweep(sweep_args())
    assert first["event"] == "started" and first["last_day"] == T.today_utc().isoformat()
    assert T.open_sweep(sweep_args()) == first  # resumed, not re-planned
    with (tmp_path / "_sweeps.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"sweep": "cut short by a crash"')  # an interrupted write: skipped, and the next line is whole
    T.append_sweep_line({"sweep": first["sweep"], "event": "finished", "at": "later"})
    second = T.open_sweep(sweep_args())
    assert second["sweep"] != first["sweep"]  # a new label even within the same second
    assert T.open_sweep(sweep_args(sweep=first["sweep"])) == first
    with pytest.raises(SystemExit):
        T.open_sweep(sweep_args(sweep="nope"))
    third = T.open_sweep(sweep_args(new_sweep=True))
    assert T.open_sweep(sweep_args()) == third  # the latest unfinished sweep, by start time
    lines = (tmp_path / "_sweeps.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines[1] == '{"sweep": "cut short by a crash"'  # kept as it was, never rewritten
    assert all(json.loads(line) for line in lines[2:])


def test_only_one_run_fetches_at_a_time(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "LOCK", tmp_path / "_run.lock")
    with T.run_lock():
        with pytest.raises(SystemExit):
            with T.run_lock():
                pass
    with T.run_lock():  # released when the first run ended
        pass


def test_a_fetch_is_done_when_saved_or_terminally_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    name = "list/date/2026-07-01"
    assert not T.done(None) and not T.done({"name": name, "error": "HTTP 500"})
    assert T.done({"name": name, "status": 404}) and T.done({"name": name, "absent": "why"})
    assert not T.done({"name": name, "status": 200})  # the file is gone: fetch again
    T.listing_dest(name).parent.mkdir(parents=True)
    T.listing_dest(name).write_bytes(gzip.compress(b"<!DOCTYPE html>"))
    assert T.done({"name": name, "status": 200})


def test_research_listings_are_imported_once_with_a_marked_receipt(tmp_path, monkeypatch):
    source = tmp_path / "research"
    source.mkdir()
    (source / "list.html").write_bytes((FIXTURES / IN_WINDOW).read_bytes())
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(T, "RESEARCH_DIRS", (tmp_path / "gone", source))
    monkeypatch.setattr(T, "RESEARCH_LISTINGS", {"list.html": ("date", "2026-06-24", "https://x/en?date=2026-06-24"),
                                                "missing.html": ("home", None, "https://x/en")})
    receipts = C.Receipts("tdi", root=tmp_path / "raw")
    assert T.import_research_listings(receipts) == {"imported": 1, "missing": 1}
    (name, receipt), = receipts.all().items()
    assert name.startswith("list/date/2026-06-24@research-") and receipt["imported"] and receipt["status"] == 200
    assert gzip.decompress(T.listing_dest(name).read_bytes()) == (FIXTURES / IN_WINDOW).read_bytes()
    assert T.import_research_listings(receipts) == {"already imported": 1, "missing": 1}


# the id index ----------------------------------------------------------------------------
def card(match_id, kind, key, stamp_day, **kw):
    base = {"match_id": match_id, "listing_kind": kind, "listing_key": key, "found_by": f"{kind}:{key}",
            "stamp": f"{stamp_day}T10:00:00.000Z", "stamp_day": stamp_day, "round": "R1", "tournament": "T",
            "draw_type": "singles", "team1_player_ids": "a", "team1_names": "A", "team2_player_ids": "b",
            "team2_names": "B", "retrieved_at": "2026-09-25T14:30:00+00:00",
            "stamp_matches_listing_day": (stamp_day == key) if kind == "date" else None}
    return {**base, **kw}


def test_the_index_dates_a_match_only_from_a_listing_of_its_own_day():
    cards = [card("m1", "date", "2026-07-01", "2026-07-01"), card("m1", "tournament", "t1", "2026-07-01"),
             card("m2", "date", "2026-05-18", "2026-09-24"),  # the default listing served for an old day
             card("m3", "tournament", "t1", "2026-07-02", round="R2"), card("m3", "home", "s", "2026-07-02", round="QF")]
    index = {r["match_id"]: r for r in T.id_index(cards, {"t1": {"title": " Somewhere Open "}})}
    assert (index["m1"]["listing_day"], index["m1"]["tournament_id"], index["m1"]["tournament_title"]) == \
        ("2026-07-01", "t1", "Somewhere Open")
    assert index["m1"]["in_date_listing"] and index["m1"]["in_tournament_listing"] and index["m1"]["sightings"] == 2
    assert index["m2"]["listing_day"] is None and not index["m2"]["in_date_listing"]
    assert index["m3"]["conflicts"] == "round:QF|R2" and index["m3"]["in_home_listing"]


# match pages ---------------------------------------------------------------------------
MATCH_2026 = "tdi_match_2026_challenger_200.html"
MATCH_404 = "tdi_match_2025_tour_404.html"
MATCH_NO_OUTCOMES = "tdi_match_2025_challenger_no_outcomes.html"
MATCH_DOUBLES = "tdi_match_2025_challenger_doubles.html"
IDS = {MATCH_2026: "bd0a2c43-be75-4b85-9f7a-7e931915d976", MATCH_404: "dd5b89e8-c6ad-4a09-aaec-07829cd64db8",
       MATCH_NO_OUTCOMES: "2057f644-d696-404a-ac91-c30148a516c4", MATCH_DOUBLES: "f5ed8c93-6800-47af-b0f1-ad6b5941676d"}


def parsed(name: str) -> dict:
    return T.parse_match_page((FIXTURES / name).read_text(encoding="utf-8"), IDS[name])


def test_the_title_gives_the_atp_code_and_the_description_the_event_place_and_score():
    m = parsed(MATCH_2026)["match"]
    assert (m["atp_code"], m["atp_year"], m["atp_tournament_id"], m["atp_match_code"]) == \
        ("2026#7395#MS016", "2026", "7395", "MS016")
    assert (m["event_code"], m["draw_type"], m["draw"]) == ("MS", "singles", "main")
    assert (m["description_event"], m["description_place"], m["description_score"]) == \
        ("Men's Singles", "Buenos Aires 2", "6/1 4/6 6/2")
    assert T.title_fields("Poullain vs Orlov | 2026#3105#QS009 | Tennis Results")["draw"] == "qualifying"
    assert T.title_fields("no code here")["atp_code"] is None


def test_the_header_links_each_player_uuid_to_an_atp_id():
    m = parsed(MATCH_2026)["match"]
    assert (m["h1"], m["completed_on"], m["tournament"], m["place"]) == \
        ("Comesana vs Estevez", "2026-09-22T18:55:35.736Z", "Buenos Aires Challenger", "Buenos Aires, Argentina")
    assert (m["team_a_player_ids"], m["team_a_atp_ids"], m["team_a_names"], m["team_a_countries"], m["team_a_entry"]) == \
        ("ad60bfba-9a60-465c-8625-8aed7094e07b", "C0DF", "Francisco Comesana", "ARG", "1")
    assert (m["team_b_atp_ids"], m["team_b_short_names"], m["team_b_entry"]) == ("E0DI", "J.Estevez", None)
    assert (m["team_a_scores"], m["team_b_scores"]) == ("1:6 2:4 3:6", "1:1 2:6 3:2")
    assert (m["point_team_a_name"], m["point_team_b_name"]) == ("Comesana", "Estevez")


def test_points_are_flattened_with_the_rally_kept():
    points = parsed(MATCH_2026)["points"]
    assert len(points) == 12 and {(p["id_set"], p["id_game"]) for p in points} == {(1, 1), (1, 2)}
    first = points[0]
    assert (first["point_id"], first["set"], first["game"], first["point"]) == \
        ("bd0a2c43-be75-4b85-9f7a-7e931915d976-01-01-001", 1, 1, 1)
    assert (first["time"], first["completed_utc"], first["winner"], first["team_serving"]) == \
        ("2026-09-22T17:09:14.2560000+00:00", "2026-09-22T17:09:21.2750000+00:00", "teamA", "teamA")
    assert (first["player_serving"], first["team_a_game_score"], first["team_b_game_score"], first["team_a_sets"]) == \
        ("ad60bfba-9a60-465c-8625-8aed7094e07b", "15", "0", "1:0/0")
    assert (first["outcome"], first["serve"], first["total_shots"], first["winning_shot_type"], first["error_type"],
            first["situation"], first["rally"]) == ("winner", "FIRST", "3", "forehand", None, "baseline", "SERVE/POINT_COMPLETE")
    ace = points[2]
    assert (ace["rally"], ace["serve"], ace["ace"], ace["game_point"], ace["streak_count"]) == \
        ("SERVE/ACE/POINT_COMPLETE", "ACE", True, "teamA", 3)
    assert all(p["extra"] is None for p in points)


def test_statistics_rows_carry_period_category_and_both_values():
    stats = parsed(MATCH_2026)["statistics"]
    assert len(stats) == 50 and {s["period"] for s in stats} == {"match", "1"}
    by = {(s["period"], s["label"]): s for s in stats}
    total = by["match", "Total Points Won"]
    assert (total["category"], total["team_a"], total["team_b"]) == ("Points", "87", "68")
    assert (by["match", "Performance Rating (0-10)"]["team_a"], by["match", "Shots In Attack"]["team_b"]) == ("6.74", "20%")
    assert (by["1", "Aces"]["team_a"], by["1", "Aces"]["team_b"]) == ("2", "0")


def test_an_old_page_served_with_404_parses_like_a_current_one():
    out = parsed(MATCH_404)
    m = out["match"]
    assert (m["atp_code"], m["completed_on"], m["team_a_atp_ids"], m["team_b_atp_ids"]) == \
        ("2025#339#MS020", "2024-12-31T04:07:36.793Z", "TD51", "W09E")
    assert (m["team_a_scores"], m["team_b_scores"], m["description_score"]) == ("1:7/7 2:6", "1:6/5 2:3", "7/6(5) 6/3")
    first = out["points"][0]  # a double fault
    assert (first["rally"], first["faults"], first["serve"], first["outcome"], first["error_type"]) == \
        ("SERVE/FAULT/SERVE/FAULT/POINT_COMPLETE", 2, "DOUBLE FAULT", "unforced", "out")
    assert all(p["completed_utc"] is None and p["time"] for p in out["points"])


def test_a_2025_challenger_page_has_serves_and_times_but_no_outcomes():
    out = parsed(MATCH_NO_OUTCOMES)
    assert all(p[k] is None for p in out["points"]
               for k in ("outcome", "total_shots", "winning_shot_type", "error_type", "situation"))
    assert [p["serve"] for p in out["points"][:2]] == ["FIRST", "SECOND"] and out["points"][1]["faults"] == 1
    by = {(s["period"], s["label"]): s for s in out["statistics"]}
    assert by["match", "Aces"]["team_a"] == "3" and by["match", "Performance Rating (0-10)"]["team_a"] == "–"


def test_doubles_teams_are_two_players_each_and_the_server_belongs_to_the_serving_team():
    out = parsed(MATCH_DOUBLES)
    m = out["match"]
    assert (m["draw_type"], m["players_in_header"]) == ("doubles", 4)
    assert (m["team_a_atp_ids"], m["team_a_names"]) == ("D0DT;RG42", "Martin Damm;Alex Rybakov")
    assert (m["team_b_atp_ids"], m["team_b_entry"]) == ("M0RE;MF70", "4")
    assert (m["team_a_scores"], m["team_b_scores"]) == ("1:4 2:6 3:1/10", "1:6 2:4 3:0/6")
    teams = {"teamA": m["team_a_player_ids"].split(";"), "teamB": m["team_b_player_ids"].split(";")}
    assert all(p["player_serving"] in teams[p["team_serving"]] and p["player_receiving"] not in teams[p["team_serving"]]
               for p in out["points"])


def test_a_path_reference_inside_a_point_is_resolved():
    # 25 pages of 5,836 write a repeated streak once and point back to it
    rows = {"62": ["$", "$L63", None, {"children": "$L64"}],
            "64": ["$", "$L65", None, {"details": [{"streak": {"owner": "teamB", "count": 2}}]}]}
    point = {"id": "x", "streak": "$62:props:children:props:details:0:streak", "rally": ["$62:props:children"]}
    resolved = T.resolved_point(point, rows)
    assert resolved["streak"] == {"owner": "teamB", "count": 2}
    assert T.deref("$62:props:nowhere", rows) == "$62:props:nowhere"  # unresolvable: kept, and reported by point_record
    record = T.point_record({"id": "x", "streak": "$99:props:streak"})
    assert record["streak_owner"] is None and record["extra"] == {"unresolved.streak": "$99:props:streak"}


def test_level_comes_from_the_atp_tournament_id_then_the_name():
    levels = {7395: ("C", "Buenos Aires CH", 2025), 339: ("A", "Brisbane", 2026)}
    assert T.match_level("7395", ["Buenos Aires Challenger"], levels)["level_source"] == "sackmann_2025"
    assert T.match_level("339", [], levels) == {"sackmann_level": "A", "sackmann_name": "Brisbane", "level": "tour",
                                                "level_source": "sackmann_2026"}
    assert T.match_level("9999", ["Intaro Challenger"], levels)["level_source"] == "name"
    assert T.match_level("9999", ["Kia Open"], levels)["level"] == "unknown"
    assert T.match_level(None, [None], levels)["level"] == "unknown"


# fetching match pages ----------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status: int, body: bytes):
        self.status_code, self.content, self.headers, self.url = status, body, {"content-type": "text/html"}, "https://x"


class FakeClient:
    def __init__(self, answers: dict):
        self.answers, self.requests = answers, 0

    def get(self, url, headers=None):
        self.requests += 1
        return self.answers[url.rsplit("/", 1)[-1]]


def test_a_404_is_kept_when_it_carries_the_matchs_own_points_and_absent_otherwise(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("tdi", root=tmp_path)
    old = (FIXTURES / MATCH_404).read_bytes()
    gone, other, broken = ("00000000-0000-4000-8000-000000000000", "11111111-1111-4111-8111-111111111111",
                           "22222222-2222-4222-8222-222222222222")
    client = FakeClient({IDS[MATCH_404]: FakeResponse(404, old), gone: FakeResponse(404, b"<!DOCTYPE html><html>no</html>"),
                         other: FakeResponse(404, old),  # another match's points do not count
                         IDS[MATCH_2026]: FakeResponse(200, (FIXTURES / MATCH_2026).read_bytes()),
                         broken: FakeResponse(500, b"")})
    kept = T.fetch_match(client, receipts, IDS[MATCH_404])
    assert (kept["status"], kept["document"], kept["point_ids"], T.match_state(kept)) == (404, True, 9, "404_with_points")
    assert gzip.decompress(T.match_dest(IDS[MATCH_404]).read_bytes()) == old
    absent = T.fetch_match(client, receipts, gone)
    assert absent["absent"] == "HTTP 404 without points" and not T.match_dest(gone).exists()
    assert T.fetch_match(client, receipts, other)["absent"]
    assert T.fetch_match(client, receipts, IDS[MATCH_2026])["document"]
    assert T.fetch_match(client, receipts, broken)["error"] == "HTTP 500"  # retried by the next run
    asked = client.requests
    assert all(T.fetch_match(client, receipts, m)["skipped"] for m in (IDS[MATCH_404], gone, IDS[MATCH_2026]))
    assert client.requests == asked  # nothing done is asked for again


def test_old_pages_count_as_documents_so_a_run_of_them_is_not_stopped(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("tdi", root=tmp_path)
    old = (FIXTURES / MATCH_404).read_bytes()
    ids = [f"{n:08x}-0000-4000-8000-000000000000" for n in range(6)]
    client = FakeClient({i: FakeResponse(404, old.replace(IDS[MATCH_404].encode(), i.encode())) for i in ids})
    report, outcomes = {}, Counter()
    T.fetch_pages(client, receipts, F.FailureStreak(5), ids, "test", outcomes, report)
    assert report == {"source": "test", "ids": 6, "done_before": 0, "fetched": 6, "remaining": 0}
    assert outcomes == {"match:404_with_points": 6}
    gone = [f"{n:08x}-1111-4111-8111-111111111111" for n in range(5)]
    report = {}
    with pytest.raises(F.Stopped):
        T.fetch_pages(FakeClient({i: FakeResponse(404, b"<!DOCTYPE html>") for i in gone}), receipts,
                      F.FailureStreak(5), gone, "test", Counter(), report)
    assert (report["fetched"], report["remaining"]) == (5, 0)  # the report survives the stop


def test_a_recent_sweep_reads_the_default_listing_and_its_days_but_no_tournament(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    monkeypatch.setattr(T, "SWEEPS", tmp_path / "_sweeps.jsonl")
    sweep = T.open_sweep(sweep_args(recent=2))
    assert (sweep["kind"], sweep["tournaments_from"], len(T.plan_days(sweep))) == ("recent", None, 3)
    page = (FIXTURES / IN_WINDOW).read_bytes()  # its filter lists hold three tournaments
    client = FakeClient({"en": FakeResponse(200, page),
                         **{f"en?date={day}": FakeResponse(200, page) for day in T.plan_days(sweep)}})
    receipts = C.Receipts("tdi", root=tmp_path)
    out = T.sweep_listings(client, receipts, F.FailureStreak(5), sweep, types.SimpleNamespace(dates=None, tournaments=None),
                           Counter())
    assert (out["finished"], out["planned"], client.requests) == (True, 4, 4)
    assert T.open_sweep(sweep_args(recent=2))["sweep"] != sweep["sweep"]  # finished: the next run starts a new one


def test_staging_accounts_for_every_id_and_streams_the_points(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(T, "sackmann_levels", lambda: {7395: ("C", "Buenos Aires CH", 2025), 339: ("A", "Brisbane", 2025)})
    unfetched = "33333333-3333-4333-8333-333333333333"
    (tmp_path / "wayback.csv").write_text(f"tdi_match_id,wayback_timestamp\n{IDS[MATCH_404]},20250514000000\n"
                                          f"{unfetched},20250514000000\n", encoding="utf-8")
    monkeypatch.setattr(T, "WAYBACK_IDS", tmp_path / "wayback.csv")
    receipts = C.Receipts("tdi", root=tmp_path / "raw")
    client = FakeClient({IDS[MATCH_2026]: FakeResponse(200, (FIXTURES / MATCH_2026).read_bytes()),
                         IDS[MATCH_404]: FakeResponse(404, (FIXTURES / MATCH_404).read_bytes())})
    for match_id in (IDS[MATCH_2026], IDS[MATCH_404]):
        T.fetch_match(client, receipts, match_id)
    out = T.stage_matches(receipts)
    assert [out[t]["rows"] for t in ("matches", "points", "statistics", "players")] == [3, 21, 100, 4]
    matches = {r["match_id"]: r for r in T.read_table("matches")}
    assert matches[unfetched]["record"] == "not fetched"
    old = matches[IDS[MATCH_404]]
    assert (old["record"], old["http_status"], old["level"], old["points"], old["points_with_outcome"]) == \
        ("points", "404", "tour", "9", "9")
    assert (matches[IDS[MATCH_2026]]["level"], matches[IDS[MATCH_2026]]["stats_periods"]) == ("challenger", "match;1")
    assert out["pages"]["documents_by_http_status"] == {"200": 1, "404": 1}
    players = {r["atp_id"]: r for r in T.read_table("players")}
    assert players["C0DF"]["player_id"] == "ad60bfba-9a60-465c-8625-8aed7094e07b"


# the checks (verify_tdi) -------------------------------------------------------------------
def pts(set_no: int, game_no: int, rows: str) -> list[dict]:
    """Points of one game from "winner:a-score/b-score" items, e.g. "A:15/0 B:15/15"."""
    out = []
    for item in rows.split():
        winner, scores = item.split(":")
        a, b = scores.split("/")
        out.append({"set": str(set_no), "game": str(game_no), "winner": f"team{winner}",
                    "team_a_game_score": a, "team_b_game_score": b})
    return out


DEUCE_GAME = "A:15/0 B:15/15 A:30/15 B:30/30 A:40/30 B:40/40 A:Av/40 A:0/0"


def test_the_replay_plays_advantage_in_singles_and_no_ad_in_doubles():
    singles = V.replay(pts(1, 1, DEUCE_GAME), doubles=False)
    assert (singles["sets"][0]["a"], singles["gaps"], singles["state_mismatches"]) == (1, [], 0)
    # the same points in doubles: the game ends at the deciding point (seventh), so the eighth comes after its end
    doubles = V.replay(pts(1, 1, "A:15/0 B:15/15 A:30/15 B:30/30 A:40/30 B:40/40 A:0/0 A:0/0"), doubles=True)
    assert (doubles["sets"][0]["a"], doubles["points_after_game_end"], doubles["state_mismatches"]) == (1, 1, 0)


def test_the_replay_reads_tiebreaks_and_marks_games_whose_points_stop():
    tiebreak = " ".join(["A:1/0", "A:2/0", "B:2/1", "A:3/1", "A:4/1", "A:5/1", "B:5/2", "A:6/2", "A:0/0"])
    out = V.replay(pts(1, 13, tiebreak), doubles=False)
    assert (out["sets"][0]["tiebreak"], out["state_mismatches"]) == ((7, 2), 0)
    stopped = V.replay(pts(2, 12, "B:0/15 B:0/30"), doubles=False)
    assert stopped["gaps"] == ["2.12"] and not stopped["complete"]
    assert V.is_tiebreak(1, pts(3, 1, "A:1/0")) and not V.is_tiebreak(1, pts(1, 1, "A:15/0"))


def test_winners_that_contradict_the_score_are_counted_even_on_a_games_last_point():
    game = pts(1, 1, "A:15/0 B:30/0 A:40/0 B:0/0")  # point 2 says B, but A's score rose; point 4 says B, but A's games rose
    for p, (a, b) in zip(game, [("1:0/0", "1:0/0")] * 3 + [("1:1/0", "1:0/0")]):
        p["team_a_sets"], p["team_b_sets"] = a, b
    assert V.winner_contradictions(game) == 2
    assert V.score_winner(("40", "Av"), ("40", "40"), False) == "teamA"  # B loses the advantage
    assert V.score_winner(("15", "13"), ("16", "13"), True) == "teamA"  # a long tiebreak, not "15" of a game
    assert V.score_winner(("40", "30"), ("0", "0"), False) is None


def test_result_labels_and_the_winners_description():
    won = {"sets": [{"a": 7, "b": 6, "tiebreak": (7, 5), "match_tiebreak": False},
                    {"a": 6, "b": 3, "tiebreak": None, "match_tiebreak": False}],
           "winner": "teamA", "complete": True, "gaps": []}
    match = {"team_a_scores": "1:7/7 2:6", "team_b_scores": "1:6/5 2:3", "description_score": "7/6(5) 6/3"}
    assert V.result_check(match, won) == {"result": "reproduced", "replayed_sets": "7-6 6-3", "header_sets": "7-6 6-3",
                                          "gaps": None, "description_agrees": True}
    lost = {**won, "winner": "teamB", "sets": [{"a": 4, "b": 6, "tiebreak": None, "match_tiebreak": False},
                                               {"a": 0, "b": 1, "tiebreak": (6, 10), "match_tiebreak": True}]}
    assert V.description_numbers(lost["sets"], "teamB") == [6, 4, 10, 6]
    retired = {**won, "complete": False, "winner": None, "sets": won["sets"][:1] + [{"a": 2, "b": 1, "tiebreak": None,
                                                                                    "match_tiebreak": False}]}
    assert V.result_check({"team_a_scores": "1:7/7 2:2", "team_b_scores": "1:6/5 2:1"}, retired)["result"] == \
        "reproduced, unfinished"
    assert V.result_check(match, {**won, "gaps": ["2.9"]})["result"] == "points missing"
    assert V.result_check({**match, "team_b_scores": "1:6/5 2:4"}, won)["result"] == "differs"


def test_games_compare_across_sources_whichever_side_the_player_is_on():
    game1 = [{**p, "team_serving": "teamB"} for p in pts(1, 1, "B:0/15 B:0/30 A:15/30 B:15/40 B:0/0")]
    game2 = [{**p, "team_serving": "teamA"} for p in pts(1, 2, "A:15/0 A:30/0 A:40/0 A:0/0")]
    ours = V.tdi_games(game1 + game2, "teamB")  # the career player is team B: serves and wins game 1
    assert ours[(1, 1)] == {"points": 5, "winner": "me", "server": "me",
                            "states": [("15", "0"), ("30", "0"), ("30", "15"), ("40", "15")]}
    sofa = V.sofascore_games(
        [{"set": "1", "game": "1", "point": str(i), "home_point": h, "away_point": a, "scoring": "2", "serving": "2",
          "tiebreak": "FALSE"} for i, (h, a) in enumerate([("0", "15"), ("0", "30"), ("15", "30"), ("15", "40")], 1)]
        + [{"set": "1", "game": "2", "point": str(i), "home_point": h, "away_point": a, "scoring": "1", "serving": "1",
            "tiebreak": "FALSE"} for i, (h, a) in enumerate([("15", "0"), ("30", "0"), ("40", "0")], 1)], home_is_me=False)
    assert V.compare_games(ours, sofa, "sofa")["sofa_identical"]
    tl = V.tennislive_games([{"set": "1", "game": "1", "server_index": "0", "winner_index": "0", "tiebreak": "FALSE"}],
                            [{"set": "1", "game": "1", "point": str(i), "player1_point": x, "player2_point": y}
                             for i, (x, y) in enumerate([("15", "0"), ("30", "0"), ("30", "15"), ("40", "15")], 1)],
                            first_is_me=True)
    assert tl[(1, 1)] == {"points": 5, "winner": "me", "server": "me",
                          "states": [("15", "0"), ("30", "0"), ("30", "15"), ("40", "15")]}
    assert V.norm_state("AD") == V.norm_state("Av") == "A"
