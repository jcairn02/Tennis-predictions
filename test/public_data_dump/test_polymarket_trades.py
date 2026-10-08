"""Offline tests for the Polymarket trade-fill page merge (no network)."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import polymarket_trades as T  # noqa: E402


def fill(ts, wallet="0xa", side="BUY", size=10.0, price=0.5, tx="0x1"):
    return {"proxyWallet": wallet, "side": side, "asset": "1", "size": size, "price": price, "timestamp": ts,
            "transactionHash": tx, "outcomeIndex": 0}


def test_single_page_is_returned_unchanged():
    rows = [fill(30), fill(20), fill(10)]
    assert T.merge_pages([(None, rows)]) == rows


def test_boundary_second_repeats_are_removed():
    # page 1 ends inside second 20; page 2 (end=20, inclusive) repeats both second-20 rows and adds the rest
    page1 = [fill(30, tx="0x3"), fill(20, tx="0x2a"), fill(20, tx="0x2b")]
    page2 = [fill(20, tx="0x2a"), fill(20, tx="0x2b"), fill(20, tx="0x2c"), fill(10, tx="0x1")]
    merged = T.merge_pages([(None, page1), (20, page2)])
    assert [r["transactionHash"] for r in merged] == ["0x3", "0x2a", "0x2b", "0x2c", "0x1"]


def test_identical_twins_are_counted_not_collapsed():
    # two genuinely identical records in one second: page 1 holds one copy, page 2 returns both
    twin = fill(20, wallet="0xm", size=5.0, tx="0xt")
    merged = T.merge_pages([(None, [fill(30), dict(twin)]), (20, [dict(twin), dict(twin), fill(10)])])
    assert sum(1 for r in merged if r["transactionHash"] == "0xt") == 2
    assert len(merged) == 4


def test_rows_older_than_the_boundary_are_never_dropped():
    # a row identical to a boundary row except for its (older) timestamp is a different fill
    merged = T.merge_pages([(None, [fill(20)]), (20, [fill(20), fill(19)])])
    assert [r["timestamp"] for r in merged] == [20, 19]


def test_three_pages_chain_their_boundaries():
    page1 = [fill(50), fill(40)]
    page2 = [fill(40), fill(30)]
    page3 = [fill(30), fill(20)]
    merged = T.merge_pages([(None, page1), (40, page2), (30, page3)])
    assert [r["timestamp"] for r in merged] == [50, 40, 30, 20]


def test_markets_fetched_before_they_closed_are_fetched_again():
    import pandas as pd
    markets = pd.DataFrame({"conditionId": ["done_after_close", "done_while_open", "still_open", "never_fetched", "no_close_time"],
                            "closed": ["True", "True", "False", "True", "True"],
                            "closedTime": ["2026-09-23 20:05:13+00", "2026-10-05 23:00:00+00", None, "2026-09-23 20:00:00+00", None]})
    done = {c: {"retrieved_at": "2026-10-05T20:30:00+00:00"} for c in markets.conditionId if c != "never_fetched"}
    assert T.fetched_before_close(markets, done).tolist() == [False, True, True, False, False]
