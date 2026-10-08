"""The link check's verdicts: a SofaScore event against Tennis My Life's winner and score (offline, synthetic)."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import verify_links as V  # noqa: E402


def event(home, away, home_sets, away_sets, winner=1):
    hs = {f"period{n}": g for n, g in enumerate(home_sets, 1)}
    aw = {f"period{n}": g for n, g in enumerate(away_sets, 1)}
    return {"homeTeam": {"name": home}, "awayTeam": {"name": away}, "homeScore": hs, "awayScore": aw,
            "winnerCode": winner}


def test_scores_are_read_winner_first():
    assert V.tml_sets("6-7(2) 7-6(3) 7-5 RET") == [(6, 7), (7, 6), (7, 5)]
    assert V.ss_sets(event("Ann Bee", "Cid Dee", [4, 6], [6, 3], winner=2)) == [(6, 4), (3, 6)]


def test_verdicts():
    basel = event("Reilly Opelka", "Botic Van de Zandschulp", [6, 6], [4, 4])
    assert V.compare(basel, "Reilly Opelka", "6-4 6-4") == "agrees"
    assert V.compare(basel, "Botic van de Zandschulp", "6-4 6-4") == "winner differs"
    retired = event("Ann Bee", "Cid Dee", [6, 0], [3, 0])   # SofaScore adds the set never started
    assert V.compare(retired, "Ann Bee", "6-3 RET") == "agrees"
    assert V.compare(event("Ann Bee", "Cid Dee", [], [], winner=2), "Cid Dee", "4-3 RET") == \
        "winner agrees, SofaScore lists no score"
    assert V.compare(event("Ann Bee", "Cid Dee", [7, 5], [6, 4]), "Ann Bee", "7-6(3) 5-7 6-3") == \
        "winner agrees, score differs"
