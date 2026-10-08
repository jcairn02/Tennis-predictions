"""The AO/RG point-data study: the Hawk-Eye copy's adapter, the SofaScore by-tournament adapter's import and the gap
linker, and the data map's reading of the copy (offline: synthetic files in a temporary folder)."""
import gzip
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.ao_rg_points import link_sofascore as L  # noqa: E402
from src.eda.data_map import measure as M  # noqa: E402
from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import sofascore_tournaments as T  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import slam_ball_tracking as H  # noqa: E402


# ----------------------------------------------------------------------------------- the Hawk-Eye copy's adapter
def test_git_blob_sha1_is_gits():
    assert H.git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


@pytest.mark.parametrize("value, years", [("2022-2024", {2022, 2023, 2024}), ("2019,2024", {2019, 2024}),
                                          ("all", None), ("none", set())])
def test_parse_years(value, years):
    assert H.parse_years(value) == years


@pytest.mark.parametrize("path, kind", [
    ("README.md", "meta"),
    ("players_matches_catalogue/catalogue_all_matches_available.csv", "catalogue"),
    ("pbp_data_csvs/roland_garros/wta/wta_roland_garros_2019_SD001_pbp.csv", "csv"),
    ("all_json/australian_open/atp/atp_AO_Open_year_2022_MS101_tracking_data.json", "json"),
    ("all_json/roland_garros/wta/wta_year_RG_2024_SD112_tracking_data.json", "json"),
    ("all_json/australian_open/atp/atp_AO_Open_year_2020_MS101_tracking_data.json", None),   # year not asked for
    ("all_json/ranking_history/atp/atp_A0E2_player_ranking_history.json", None)])
def test_kind_of(path, kind):
    assert H.kind_of(path, {2022, 2023, 2024}) == kind


def test_catalogue_files_finds_each_matchs_csv_and_json():
    cat = pd.DataFrame({"year": ["2022", "2024"], "tournament": ["australian_open", "roland_garros"],
                        "league": ["atp", "wta"], "match_id": ["2022_MS101", "SD112"]})
    tree = {"all_json/australian_open/atp/atp_AO_Open_year_2022_MS101_tracking_data.json",
            "all_json/roland_garros/wta/wta_year_RG_2024_SD112_tracking_data.json"}
    out = H.catalogue_files(cat, tree)
    assert out["pbp_file"].tolist() == ["pbp_data_csvs/australian_open/atp/atp_australian_open_2022_MS101_pbp.csv",
                                        "pbp_data_csvs/roland_garros/wta/wta_roland_garros_2024_SD112_pbp.csv"]
    assert out["json_file"].tolist() == sorted(tree)
    assert out[["slam", "tour", "code"]].values.tolist() == [["AO", "M", "MS101"], ["RG", "W", "SD112"]]


def _write_match(raw: Path, year: int, code: str, points: int, tracked: int) -> None:
    """A Roland Garros men's match: its per-point CSV (one row per point) and its gzipped Court Vision JSON."""
    rows = ["point_ID,set_num,game_num,point_num,serve_num,is_track_avail,point_winner_id"]
    records = {}
    for n in range(1, points + 1):
        key = f"1_1_{n}_1"
        rows.append(f"{key},1,1,{n},1,{n <= tracked},A")
        records[key] = {"pointId": key, "set": 1, "game": 1, "point": n, "serve": 1, "isTieBreak": False,
                        "trajectoryData": [{"x": 1.5, "y": -2, "z": 0.1, "position": "hit"},
                                           {"x": 0, "y": 0, "z": 1, "position": "net"}] if n <= tracked else []}
    csv = raw / f"pbp_data_csvs/roland_garros/atp/atp_roland_garros_{year}_{code}_pbp.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    doc = {"courtVisionData": [{"isMatchComplete": True, "eventType": "Men's Singles", "pointsData": records}]}
    js = raw / f"all_json/roland_garros/atp/atp_RG_year_{year}_{code}_tracking_data.json.gz"
    js.parent.mkdir(parents=True, exist_ok=True)
    js.write_bytes(gzip.compress(json.dumps(doc).encode("utf-8")))


def test_stage_keeps_roland_garros_matches_of_different_years_apart(tmp_path, monkeypatch):
    """Roland Garros match ids repeat every year ('SM001'); counts must not carry from one year to another."""
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "DUMP_ROOT", tmp_path / "dump")
    raw = tmp_path / "raw" / H.SOURCE
    _write_match(raw, 2022, "SM001", points=10, tracked=10)
    _write_match(raw, 2023, "SM001", points=4, tracked=1)
    cat = pd.DataFrame({"year": ["2022", "2023"], "player1": ["A.ONE", "C.THREE"], "player2": ["B.TWO", "D.FOUR"],
                        "tournament": ["roland_garros"] * 2, "league": ["atp"] * 2, "match_id": ["SM001", "SM001"]})
    tree = {f"all_json/roland_garros/atp/atp_RG_year_{y}_SM001_tracking_data.json" for y in (2022, 2023)}
    out = H.stage(C.Receipts(H.SOURCE), H.catalogue_files(cat, tree))
    m = pd.read_parquet(tmp_path / "dump" / "points" / H.SOURCE / "matches.parquet").set_index("year")
    assert m.loc["2022", ["n_csv_points", "n_json_points", "n_json_points_tracked", "tracked"]].tolist() == \
        ["10", "10", "10", "TRUE"]
    assert m.loc["2023", ["n_csv_points", "n_json_points", "n_json_points_tracked", "tracked"]].tolist() == \
        ["4", "4", "1", "FALSE"]
    shots = pd.read_parquet(tmp_path / "dump" / "points" / H.SOURCE / "shots" / "RG_2022.parquet")
    assert len(shots) == 20 and shots[["seq", "position", "x"]].iloc[0].tolist() == ["1", "hit", "1.5"]
    assert sum(f["rows"] for f in out["points"]) == 14


# ----------------------------------------------------------------------------------- the data map's reading
def test_court_vision_rounds():
    assert [M.court_vision_round("AO", c) for c in ("MS101", "WS264", "MS701")] == ["R128", "R64", "F"]
    assert [M.court_vision_round("RG", c) for c in ("SM001", "SD003", "SM007", "SM064", "SD127", "")] == \
        ["F", "SF", "QF", "R128", "R128", None]


def test_load_slam_ball_tracking_grains(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "DUMP", tmp_path)
    folder = tmp_path / "points" / "slam_ball_tracking"
    folder.mkdir(parents=True)
    pd.DataFrame({"tour": ["M", "W", "W"], "year": ["2022", "2023", "2023"], "slam": ["AO", "RG", "RG"],
                  "match_id": ["2022_MS701", "SD001", "SD100"], "player1": ["R.NADAL", "I.SWIATEK", "X.ONE"],
                  "player2": ["D.MEDVEDEV", "K.MUCHOVA", "Y.TWO"], "n_csv_points": ["380", "200", None],
                  "tracked": ["TRUE", "FALSE", None]}).to_parquet(folder / "matches.parquet")
    starts = {(2022, "AO"): pd.Timestamp("2022-01-17"), (2023, "RG"): pd.Timestamp("2023-05-28")}
    out = M.load_slam_ball_tracking(starts)
    assert out["grain"].tolist() == ["shot", "point", "result"]
    assert out["round"].tolist() == ["F", "F", "R128"]
    three = pd.Timedelta(days=3)   # the offset the linker expects of a source dated by the day played
    assert out["d"].tolist() == [starts[(2022, "AO")] + three, starts[(2023, "RG")] + three, starts[(2023, "RG")] + three]
    assert set(out["level"]) == {"GS"}


def test_court_vision_uids_tells_sisters_apart_and_reads_run_together_surnames():
    matches = pd.DataFrame({
        "uid": [1, 2, 3, 4], "level": ["GS", "GS", "GS", "T250"], "tour": ["W", "W", "M", "W"],
        "year": [2024, 2024, 2022, 2024], "tname": ["Roland Garros", "Roland Garros", "Australian Open", "Strasbourg"],
        "name1": ["Aryna Sabalenka", "Mirra Andreeva", "Alejandro Davidovich Fokina", "Mirra Andreeva"],
        "name2": ["Erika Andreeva", "Aryna Sabalenka", "Felix Auger-Aliassime", "Aryna Sabalenka"],
        "rnd": ["R128", "QF", "R64", "R16"]})
    rows = pd.DataFrame({"tour": ["W", "W", "M", "M"], "year": [2024.0, 2024.0, 2022.0, 2022.0],
                         "tname": ["Roland Garros", "Roland Garros", "Australian Open", "Australian Open"],
                         "name1": ["M.ANDREEVA", "E.ANDREEVA", "A.DAVIDOVICHFOKINA", "X.NOBODY"],
                         "name2": ["A.SABALENKA", "A.SABALENKA", "F.AUGERALIASSIME", "F.AUGERALIASSIME"],
                         "round": ["QF", "R128", "R64", "R64"]})
    assert M.court_vision_uids(rows, matches).tolist()[:3] == [2, 1, 3]
    assert pd.isna(M.court_vision_uids(rows, matches).iloc[3])


def test_sofascore_slam_uids_tells_namesakes_apart_and_ignores_the_week_before():
    matches = pd.DataFrame({
        "uid": [1, 2, 3, 4], "level": ["GS", "GS", "T250", "GS"], "tour": ["W", "W", "M", "M"],
        "year": [2024, 2024, 2026, 2026], "tname": ["US Open", "US Open", "Eastbourne", "Wimbledon"],
        "name1": ["Diane Parry", "Yafan Wang", "Zizou Bergs", "Zizou Bergs"],
        "name2": ["Xiyu Wang", "Diane Parry", "Ugo Humbert", "Ugo Humbert"], "rnd": ["R128", "R64", "R32", "R128"]})
    rows = pd.DataFrame({"tour": ["W", "M", "M"], "year": [2024, 2026, 2026], "tname": ["US Open", "Wimbledon", "Wimbledon"],
                         "name1": ["Diane Parry", "Ugo Humbert", "Fábián Marozsán"],
                         "name2": ["Yafan Wang", "Zizou Bergs", "Alejandro Davidovich Fokina"],
                         "round": ["Round of 64", "Round of 128", "Round of 64"]})
    out = M.sofascore_slam_uids(rows, matches)
    assert out.tolist()[:2] == [2, 4] and pd.isna(out.iloc[2])


# ----------------------------------------------------------------------------------- linking the gap to SofaScore
def test_words_keeps_two_letter_names_when_nothing_longer():
    assert L.words("Li Tu") == {"li", "tu"}
    assert L.words("Alex de Minaur") == {"alex", "minaur"}
    assert L.words("Jiří Lehečka") == {"jiri", "lehecka"}


def _event(eid, home, away, day, round_name=None):
    e = {"id": eid, "startTimestamp": int(pd.Timestamp(day, tz="UTC").timestamp()),
         "homeTeam": {"name": home, "slug": home.lower().replace(" ", "-")},
         "awayTeam": {"name": away, "slug": away.lower().replace(" ", "-")},
         "roundInfo": {"name": round_name} if round_name else None, "status": {"description": "Ended"}, "winnerCode": 1}
    return dict(e, _hw=L.team_words(e["homeTeam"]), _aw=L.team_words(e["awayTeam"]))


def test_link_prefers_the_main_draw_meeting_of_a_pair_that_met_twice():
    """Pouille and Rodionov, Roland Garros 2023: qualifying on 25 May (no round name), first round on 28 May."""
    cands = [_event(1, "Lucas Pouille", "Jurij Rodionov", "2023-05-25 14:00"),
             _event(2, "Lucas Pouille", "Jurij Rodionov", "2023-05-28 17:25", "Round of 128")]
    row = pd.Series({"name1": "Lucas Pouille", "name2": "Jurij Rodionov"})
    out = L.link_one(row, cands, pd.Timestamp("2023-05-29"))
    assert out["event_id"] == 2 and out["candidates"] == 2 and out["winner_agrees"] is True


def test_link_reports_a_tie_and_orientation():
    cands = [_event(1, "Li Tu", "Jiri Lehecka", "2025-01-12", "Round of 128"),
             _event(2, "Li Tu", "Jiri Lehecka", "2025-01-13", "Round of 128")]
    tie = L.link_one(pd.Series({"name1": "Jiri Lehecka", "name2": "Li Tu"}), cands, pd.Timestamp("2025-01-13"))
    assert tie["note"] == "tie: 1;2" and "event_id" not in tie
    one = L.link_one(pd.Series({"name1": "Jiri Lehecka", "name2": "Li Tu"}), cands[:1], pd.Timestamp("2025-01-13"))
    assert one["event_id"] == 1 and one["name1_side"] == "away" and one["winner_agrees"] is False


def test_fetch_order_puts_matches_without_a_complete_record_first(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "OUT", tmp_path)
    pd.DataFrame({"map_uid": [1, 2], "fills_point": [True, False]}).to_csv(tmp_path / "hawkeye_gap.csv", index=False)
    links = pd.DataFrame({"map_uid": [1, 2, 3, 4], "event_id": [11, 12, 13, None], "edition": ["e"] * 4,
                          "name1": list("abcd"), "name2": list("wxyz"),
                          "ss_start": ["2022-01-17 01:00", "2022-01-18 01:00", "2026-05-25 10:00", None]})
    order = L.fetch_order(links)
    assert order["event_id"].tolist() == [13, 12, 11]          # unlinked left out; newest first within a priority
    assert order["priority"].tolist() == [1, 1, 2]


# ----------------------------------------------------------------------------------- SofaScore: checking the records
def test_scores_drop_an_unplayed_last_set():
    from src.eda.ao_rg_points import sofascore_check as K
    assert K.set_scores("7-6(5) 3-6 6-4") == [(7, 6), (3, 6), (6, 4)]
    assert K.set_scores("6-2 0-0 RET") == [(6, 2)] == K.set_scores("6-2 RET")
    ev = pd.Series({"home_set1": "5", "away_set1": "7", "home_set2": "1", "away_set2": "6", "home_set3": "0",
                    "away_set3": "0"})
    assert K.sofascore_sets(ev, "away") == [(7, 5), (6, 1)]      # the winner played away; 0-0 is a retirement


def _pbp(games_per_set):
    return [{"set": n, "games": [{"game": g, "points": [{}]} for g in range(1, k + 1)]}
            for n, k in enumerate(games_per_set, 1)]


@pytest.mark.parametrize("games, status, verdict", [
    ([10, 9], "Ended", "complete"), ([10, 10], "Retired", "complete to retirement"), ([9, 9], "Ended", "short"),
    ([11, 8], "Ended", "other")])
def test_record_verdict(games, status, verdict):
    from src.eda.ao_rg_points import sofascore_check as K
    ev = pd.Series({"home_set1": "6", "away_set1": "4", "home_set2": "6", "away_set2": "3", "status_description": status})
    assert K.record_verdict(_pbp(games), ev)["pbp_verdict"] == verdict


# ----------------------------------------------------------------------------------- SofaScore: importing the probe
def _probe_answer(cache: Path, receipts: C.Receipts, name: str, rel: str | None, body, status=200, sha=None):
    dest = cache / (rel or f"{name}.json.gz")                     # a 404 answer names a file it did not write
    rec = {"name": name, "url": f"https://api.sofascore.com/api/v1/{name}", "dest": dest.as_posix(),
           "retrieved_at": "2026-09-29T17:00:00+00:00", "status": status}
    if status == 200:
        raw = json.dumps(body).encode("utf-8")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(gzip.compress(raw))
        rec.update(bytes=len(raw), sha256=sha or P.sha256_bytes(raw), compressed=True)
    receipts.record(rec)


def test_import_cache_copies_only_the_seasons_asked_for_and_their_events(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    cache = tmp_path / "probe" / "sofascore"
    old = C.Receipts("sofascore", root=cache.parent)
    ev = lambda i, ut, sid: {"id": i, "tournament": {"uniqueTournament": {"id": ut}}, "season": {"id": sid}}
    _probe_answer(cache, old, "season/10_20/last_0", "season/10_20/last_0.json.gz",
                  {"events": [ev(1, 10, 20), ev(2, 10, 20)], "hasNextPage": False})
    _probe_answer(cache, old, "season/11_21/last_0", "season/11_21/last_0.json.gz", {"events": [ev(3, 11, 21)]})
    _probe_answer(cache, old, "events/1/point-by-point", "events/1/point-by-point.json.gz", {"pointByPoint": []})
    _probe_answer(cache, old, "events/2/point-by-point", None, None, status=404)
    _probe_answer(cache, old, "events/2/statistics", "events/2/statistics.json.gz", {"statistics": []}, sha="0" * 64)
    _probe_answer(cache, old, "events/3/point-by-point", "events/3/point-by-point.json.gz", {"pointByPoint": []})
    _probe_answer(cache, old, "category/3/2022-01-19", "category/3/2022-01-19.json.gz", {"events": [ev(1, 10, 20)]})
    _probe_answer(cache, old, "category/3/2022-01-20", "category/3/2022-01-20.json.gz", {"events": [ev(3, 11, 21)]})
    receipts = P.receipts_for(T.SOURCE)
    counts = T.import_cache(cache, receipts, {"10_20"})
    assert counts == {"category:200": 1, "events:200": 1, "events:404": 1, "events:not imported (hash differs)": 1,
                      "season:200": 1}
    assert set(receipts.all()) == {"seasons/10_20/events_last_0", "events/1/point-by-point",
                                   "events/2/point-by-point", "days/3/2022-01-19"}
    assert sorted(T.load_season_events()) == [1, 2]
    assert P.read_json(T.event_doc_path(1, "point-by-point")) == {"pointByPoint": []}
    assert not T.event_doc_path(2, "point-by-point").exists()
    assert receipts.get("events/1/point-by-point")["imported_from"].endswith("events/1/point-by-point.json.gz")
    assert T.import_cache(cache, receipts, {"10_20"}) == {"category:already held": 1, "events:already held": 2,
                                                          "events:not imported (hash differs)": 1,
                                                          "season:already held": 1}
