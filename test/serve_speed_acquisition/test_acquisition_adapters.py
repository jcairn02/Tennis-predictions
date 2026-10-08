"""The serve-speed acquisition's two adapters (offline): the AO/RG Infosys files' key derivation, decryption, plan,
calibration and staging, and ManTennisData's plan and speed census."""
import base64
import gzip
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import infosys_slams as I  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import mantennisdata as M  # noqa: E402


def encrypt(obj, last_modified: int) -> dict:
    """An envelope as the Infosys hosts serve it: the object's JSON, PKCS#7-padded, AES-128-CBC under key_iv."""
    from Crypto.Cipher import AES

    key, iv = I.key_iv(last_modified)
    plain = json.dumps(obj).encode("utf-8")
    pad = 16 - len(plain) % 16
    cipher = AES.new(key, AES.MODE_CBC, iv).encrypt(plain + bytes([pad]) * pad)
    return {"lastModified": last_modified, "response": base64.b64encode(cipher).decode("ascii"), "data": None}


# ----------------------------------------------------------------------------------- key derivation and decryption
@pytest.mark.parametrize("ms, key", [
    # computed with the public implementation (nipunagarwalla/courtside, backend/scrapers/infosys/decrypt.py)
    (1749418445123, "#417kmljorn1m03$"),
    (1737936000000, "#40s2h3o0lc23i3$"),
    (1780000000999, "#42jkuxtl7d2hb7$"),
    (1704067199999, "#3ziv286t95gf34$"),   # 31 Dec 2023, the last millisecond before a new UTC year
])
def test_key_iv_matches_the_public_implementation(ms, key):
    k, iv = I.key_iv(ms)
    assert k == key.encode() and iv == key.upper().encode()
    assert len(k) == 16


def test_to_base_matches_javascript():
    assert I.to_base(0, 36) == "0"
    assert I.to_base(35, 36) == "z"
    assert I.to_base(36, 36) == "10"
    assert I.to_base(4095, 24) == "72f"   # 7 x 576 + 2 x 24 + 15


def test_decrypt_round_trip():
    obj = {"setData": [{"gameData": []}], "speed": 201.5, "name": "Ćorić"}
    assert I.decrypt(encrypt(obj, 1749418445123)) == obj


def test_decrypt_wrong_key_raises():
    env = encrypt({"a": 1}, 1749418445123)
    env["lastModified"] = 1749418445124
    with pytest.raises(ValueError):
        I.decrypt(env)


def test_decrypt_unencrypted_and_empty():
    assert I.decrypt({"lastModified": 1, "response": "", "data": {"x": 1}}) == {"x": 1}
    assert I.decrypt({"lastModified": 1, "response": None, "data": None}) is None


def test_blocks_of():
    env = {"lastModified": 1, "response": "abc", "data": None}
    assert I.blocks_of("match-beats", env) == {"mbData": env}
    assert I.blocks_of("keystats-api", env) == {"stats": env}
    doc = {"mbData": env, "stats": env, "quiz": env}
    assert I.blocks_of("match-centre", doc) == doc


@pytest.mark.parametrize("body, ok", [
    (b'{"lastModified": 1, "response": "x", "data": null}', True),
    (b'{"mbData": {"lastModified": 1, "response": "x"}, "quiz": {"data": null, "lastModified": 2, "response": ""}}', True),
    (b'{"message": "Match Not Found"}', False),
    (b"<html>blocked</html>", False),
    (b"[1, 2]", False),
])
def test_envelope_validator(body, ok):
    assert (I.envelope_validator(body) is None) == ok


# ----------------------------------------------------------------------------------- the plan
@pytest.mark.parametrize("slam, family, n, first, last", [
    ("AO", "MS", 127, ("MS701", "F"), ("MS164", "R128")),
    ("AO", "WQ", 112, ("WQ301", "Q3"), ("WQ164", "Q1")),
    ("RG", "SM", 127, ("SM001", "F"), ("SM127", "R128")),
    ("RG", "QD", 112, ("QD016", "Q3"), ("QD127", "Q1")),
])
def test_match_codes(slam, family, n, first, last):
    codes = I.match_codes(slam, family)
    assert len(codes) == n == len({c for c, _ in codes})
    assert codes[0] == first and codes[-1] == last


def test_rounds_by_code():
    r = I.round_lookup()
    assert r[("RG", "SM002")] == r[("RG", "SM003")] == "SF"
    assert r[("RG", "SM063")] == "R64" and r[("RG", "SM064")] == "R128"
    assert r[("RG", "QM031")] == "Q3" and r[("RG", "QM032")] == "Q2"
    assert r[("AO", "MS232")] == "R64" and r[("AO", "MQ116")] == "Q1"


def test_tours_and_draws():
    assert [I.family_tour("AO", f) for f in I.FAMILIES["AO"]] == ["M", "W", "M", "W"]
    assert [I.family_tour("RG", f) for f in I.FAMILIES["RG"]] == ["M", "W", "M", "W"]
    assert [I.is_qualifying("AO", f) for f in I.FAMILIES["AO"]] == [False, False, True, True]
    assert [I.is_qualifying("RG", f) for f in I.FAMILIES["RG"]] == [False, False, True, True]


def test_urls():
    assert I.url_of("AO", 2025, "match-beats", "MS701") == \
        "https://itp-ao-sls.infosys-platforms.com/static/prod/match-beats/2025/580/MS701/data.json"
    assert I.url_of("RG", 2026, "keystats-api", "SM001") == \
        "https://itp-rg-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2026/eventId/520/matchId/SM001"


class FakeResponse:
    def __init__(self, status, content=b"", headers=None):
        self.status_code, self.content, self.headers = status, content, headers or {}


class FakeReceipts:
    def __init__(self, recs):
        self._recs = recs

    def all(self):
        return self._recs


def test_calibration_reads_s3_403_as_absent_only_on_a_route_that_served_a_file():
    cal = I.Calibration(FakeReceipts({"RG/2025/match-centre/SM001": {"status": 200},
                                      "AO/2025/match-beats/MS701": {"status": 403, "error": "HTTP 403"}}))
    denied = FakeResponse(403, b"<?xml version='1.0'?><Error><Code>AccessDenied</Code></Error>")
    cal.current = ("RG", "match-centre")
    assert cal.not_found(denied)
    assert cal.not_found(FakeResponse(403, b'{"message": "Forbidden"}')) is None   # not S3's answer: a refusal
    cal.current = ("AO", "match-beats")                                            # never served a file yet
    assert cal.not_found(denied) is None
    assert cal.not_found(FakeResponse(200, b"{}")) is None


# ----------------------------------------------------------------------------------- staging
def match_beats(server_speeds):
    points = [{"pointId": f"1_1_{i}_{serve}", "point": i, "server": "1", "serve": serve, "serveSpeed": spd,
               "faultSrvSpd": 0.0, "brandNewField": i} for i, (serve, spd) in enumerate(server_speeds, 1)]
    return {"matchId": "SM064", "eventType": "Men's Singles", "courtName": "Court 14", "isMatchComplete": True,
            "matchStatus": "C", "matchWinner": 1, "setsComplete": 1,
            "playerData": {"tm1Ply1Id": "1", "tm1Ply1Name": "A.PLAYER", "tm1Ply1FirstName": "Ann",
                           "tm1Ply1LastName": "PLAYER", "tm1Ply1Country": "FRA", "tm2Ply1Id": "2",
                           "tm2Ply1Name": "B.OTHER", "tm2Ply1FirstName": "Bea", "tm2Ply1LastName": "OTHER",
                           "tm2Ply1Country": "ESP"},
            "setData": [{"set": 1, "gamesComplete": 1, "gameData": [{"game": 1, "gameWinner": 1,
                                                                     "pointData": points}]}]}


def test_stage_decrypts_and_tabulates(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump")
    lm = 1749418445123
    stats = {"courtName": "Court 14", "players": [], "setStats": {"set0": [
        {"order": 13, "name": "1st Serve Average Speed", "player1": "190", "player2": "180", "player1Bar": 51}]}}
    doc = {"mbData": encrypt(match_beats([(1, 190.0), (2, 150.0), (1, 0.0)]), lm), "stats": encrypt(stats, lm),
           "quiz": {"data": None, "lastModified": lm, "response": ""},
           "rally": {"lastModified": lm, "response": "bm90IGEgcmVhbCBibG9jaw==", "data": None}}   # fails to open
    path = I.dest_of("RG", 2025, "match-centre", "SM064")
    path.parent.mkdir(parents=True)
    path.write_bytes(gzip.compress(json.dumps(doc).encode()))
    receipts = FakeReceipts({"RG/2025/match-centre/SM064": {"status": 200, "sha256": "x", "retrieved_at": "t"},
                             "RG/2025/match-centre/SM065": {"status": 403, "absent": "S3 AccessDenied"}})
    out = I.stage(receipts, ["RG2025"])
    assert out["decrypt_failures"] == {"RG2025:match-centre:rally": 1}
    m = pd.read_parquet(P.dump_path(I.SOURCE, "matches.parquet")).set_index("match_id")
    assert m.loc["SM064", "points"] == "3" and m.loc["SM064", "points_timed"] == "2"
    assert m.loc["SM064", "first_serve_points_timed"] == "1"
    assert m.loc["SM064", "round_from_code"] == "R128" and m.loc["SM064", "tour"] == "M"
    assert m.loc["SM064", "p2_last_name"] == "OTHER"
    assert (m.loc["SM064", "blocks_ok"], m.loc["SM064", "blocks_empty"], m.loc["SM064", "blocks_failed"]) == ("2", "1", "1")
    assert json.loads(m.loc["SM065", "route_status"]) == {"match-centre": "absent"}
    assert m.loc["SM065", "files"] == "0"
    pts = pd.read_parquet(P.dump_path(I.SOURCE, "points.parquet"))
    assert pts["serveSpeed"].tolist() == ["190.0", "150.0", "0.0"]
    assert json.loads(pts["other_fields"].iloc[0]) == {"brandNewField": 1}      # unknown fields are kept
    ks = pd.read_parquet(P.dump_path(I.SOURCE, "keystats.parquet"))
    assert ks[["set_key", "name", "player1", "player2"]].values.tolist() == [["set0", "1st Serve Average Speed", "190", "180"]]
    blocks = pd.read_parquet(P.dump_path(I.SOURCE, "blocks.parquet")).set_index("block")
    assert blocks.loc["quiz", "decrypt_outcome"] == "empty"
    assert blocks.loc["rally", "decrypt_outcome"].startswith("failed")
    assert json.loads(blocks.loc["stats", "json"]) == stats


# ----------------------------------------------------------------------------------- ManTennisData
def test_mantennisdata_plan():
    years = M.parse_years("2021-2026")
    assert years == set(range(2021, 2027))
    assert M.wanted("atp/matches_2021.csv", years) and M.wanted("atp/tournaments.csv", years)
    assert not M.wanted("atp/matches_2020.csv", years) and not M.wanted("dc/matches_2024.csv", years)
    assert M.wanted("atp/matches_1999.csv", M.parse_years("all"))


def test_mantennisdata_blob_sha1_is_gits():
    assert M.git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_speed_census(tmp_path):
    f = tmp_path / "matches_2025.csv"
    f.write_text("id,win_average_first_serves_kmh,los_average_first_serves_kmh\n"
                 "1,190,185\n2,,180\n3,0,0\n4,201.5,177\n", encoding="utf-8")
    assert M.speed_census(f) == {"rows": 4, "rows_both_first_serve_speeds": 2}
