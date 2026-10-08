"""Offline tests of the daily collector's decrypt-and-stage step and its refusals (live/atp_daily.py). Synthetic
envelopes only; no file under data/raw/point_sources/infosys_atp/ is read; no request is sent."""
from __future__ import annotations

import base64
import gzip
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.live import atp_daily as AD  # noqa: E402
from src.ingest.point_sources import infosys_slams as I  # noqa: E402

KEYSTATS = {"matchCompleted": True, "setsCompleted": 2,
            "players": [{"player1Id": "S0AG", "player1Name": "J. SINNER"}, {"player1Id": "A0E2", "player1Name": "C. ALCARAZ"}],
            "setStats": {"set0": [{"name": "1st Serve Average Speed", "player1": "201", "player2": "196"},
                                  {"name": "2nd Serve Average Speed", "player1": "160", "player2": "158"},
                                  {"name": "Max Speed", "player1": "219", "player2": "214"},
                                  {"name": "First Serve", "player1": "40/62 (65%)", "player2": "38/60 (63%)"}]}}


def encrypt(obj, last_modified: int) -> dict:
    """An envelope as the Infosys hosts serve it (the acquisition tests' helper): JSON, PKCS#7, AES-128-CBC."""
    from Crypto.Cipher import AES
    key, iv = I.key_iv(last_modified)
    plain = json.dumps(obj).encode("utf-8")
    pad = 16 - len(plain) % 16
    cipher = AES.new(key, AES.MODE_CBC, iv).encrypt(plain + bytes([pad]) * pad)
    return {"lastModified": last_modified, "response": base64.b64encode(cipher).decode("ascii"), "data": None}


@pytest.mark.parametrize("ms, key", [
    # pinned to the public implementation (nipunagarwalla/courtside), as in test/serve_speed_acquisition
    (1749418445123, "#417kmljorn1m03$"),
    (1737936000000, "#40s2h3o0lc23i3$"),
    (1780000000999, "#42jkuxtl7d2hb7$"),
    (1704067199999, "#3ziv286t95gf34$"),
])
def test_pinned_keys(ms, key):
    k, iv = I.key_iv(ms)
    assert k == key.encode() and iv == key.upper().encode()


def test_round_trip_current_season():
    env = encrypt(KEYSTATS, 1791000000123)
    assert AD.decrypt_envelope(env, year=2026) == KEYSTATS
    assert AD.decrypt_envelope(env, year=2027) == KEYSTATS


@pytest.mark.parametrize("year", list(range(2015, 2022)))
def test_backfill_years_are_refused(year):
    env = encrypt(KEYSTATS, 1791000000123)
    with pytest.raises(AD.RefusedDecryption):
        AD.decrypt_envelope(env, year=year)


@pytest.mark.parametrize("year", [2022, 2023, 2024, 2025, None, "x"])
def test_years_outside_the_collector_are_refused(year):
    with pytest.raises(AD.RefusedDecryption):
        AD.guard(year)


def test_the_backfill_folder_is_refused_whatever_the_year():
    for p in (AD.BACKFILL_DIR / "2026" / "747" / "MS001.json.gz", AD.BACKFILL_DIR / "x.json.gz", AD.BACKFILL_DIR):
        with pytest.raises(AD.RefusedDecryption):
            AD.guard(2026, p)
    AD.guard(2026, AD.RAW_DIR / "2026" / "747" / "keystats-api" / "MS001.json.gz")       # the collector's own: allowed


def _write(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(payload))
    return path


def test_decrypt_and_stage(tmp_path):
    f = _write(tmp_path / "2026" / "747" / "keystats-api" / "MS001.json.gz",
               json.dumps(encrypt(KEYSTATS, 1791000000123)).encode())
    df = AD.decrypt_and_stage([f], collected_on="2026-10-08")
    assert len(df) == 1
    r = df.iloc[0]
    assert (r["year"], r["event_id"], r["match_code"], r["round"]) == (2026, "747", "MS001", "F")
    assert (r["p1_atp_id"], r["p1_spd1"], r["p2_spd1"], r["p1_first_in"], r["p1_first_total"]) == ("S0AG", 201.0, 196.0, 40, 62)
    assert r["source"] == "infosys_atp_daily" and r["collected_on"] == "2026-10-08" and bool(r["match_completed"])


def test_decrypt_and_stage_refuses_before_reading(tmp_path):
    """A 2019 file is refused before it is opened: its content (not even JSON here) is never read."""
    f = _write(tmp_path / "2019" / "747" / "keystats-api" / "MS001.json.gz", b"not json")
    with pytest.raises(AD.RefusedDecryption):
        AD.decrypt_and_stage([f], collected_on="2026-10-08")


def test_fetch_is_off_by_default(tmp_path):
    with pytest.raises(AD.NotEnabled):
        AD.fetch_daily("2026-10-08", [(2026, "5014", "MS064", "R128")], cfg=tmp_path / "absent.json")


def test_fetch_when_enabled_uses_the_routes_and_budget(tmp_path, monkeypatch):
    """With the switch on and a stand-in adapter and client (no network): the /prod/api/ keystats route of the current
    season, one request per planned code within the budget, files saved where decrypt_and_stage reads them."""
    from src.ingest.point_sources import common as P
    cfg = tmp_path / "collector.json"
    cfg.write_text(json.dumps({"atp_daily_enabled": True}), encoding="utf-8")
    asked = []

    class Client:
        requests = 0

        def get(self, url, headers=None):
            if self.requests >= 2:
                raise P.BudgetExhausted("budget")
            self.requests += 1
            asked.append((url, headers))
            body = json.dumps(encrypt(KEYSTATS, 1791000000123)).encode()
            return types.SimpleNamespace(status_code=200, headers={"content-type": "application/json"}, url=url,
                                         content=body)

        def stats(self):
            return {"requests": self.requests}

    fake = types.SimpleNamespace(make_client=lambda: Client(), site_headers=lambda: {"Origin": "https://www.atptour.com"})
    monkeypatch.setattr(AD, "_adapter", lambda: fake)
    monkeypatch.setattr(AD, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "receipts")
    plan = [(2026, "5014", "MS064", "R128"), (2026, "5014", "MS065", "R128"), (2026, "5014", "MS066", "R128")]
    with pytest.raises(P.BudgetExhausted):
        AD.fetch_daily("2026-10-08", plan, cfg=cfg)
    assert [u for u, _ in asked] == [
        "https://itp-atp-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2026/eventId/5014/matchId/MS064",
        "https://itp-atp-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2026/eventId/5014/matchId/MS065"]
    files = sorted((tmp_path / "raw").rglob("*.json.gz"))
    assert len(files) == 2
    df = AD.decrypt_and_stage(files, collected_on="2026-10-08")
    assert len(df) == 2 and set(df["round"]) == {"R128"}
    with pytest.raises(AD.RefusedDecryption):
        AD.fetch_daily("2026-10-08", [(2019, "5014", "MS064", "R128")], cfg=cfg)


def test_without_the_backfill_adapter_the_fetch_stays_off_unless_allowed(tmp_path, monkeypatch):
    """Enabled but the adapter missing: refused unless collector.json allows the shared client (no request either way
    here: the stand-in client raises if asked)."""
    cfg = tmp_path / "collector.json"
    cfg.write_text(json.dumps({"atp_daily_enabled": True}), encoding="utf-8")

    def missing():
        raise AD.NotEnabled("adapter missing")
    monkeypatch.setattr(AD, "_adapter", missing)
    with pytest.raises(AD.NotEnabled):
        AD.fetch_daily("2026-10-08", [(2026, "5014", "MS064", "R128")], cfg=cfg)
    cfg.write_text(json.dumps({"atp_daily_enabled": True, "require_backfill_adapter": False}), encoding="utf-8")
    from src.ingest.point_sources import feeds as FD

    class NoNet(FD.FeedClient):
        def get(self, url, headers=None):
            raise RuntimeError(f"would request {url}")
    monkeypatch.setattr(FD, "FeedClient", lambda **kw: NoNet(session=object(), **kw))
    from src.ingest.point_sources import common as P
    monkeypatch.setattr(AD, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "receipts")
    res = AD.fetch_daily("2026-10-08", [(2026, "5014", "MS064", "R128")], cfg=cfg)
    assert res["files"] == [] and res["planned"] == 1
