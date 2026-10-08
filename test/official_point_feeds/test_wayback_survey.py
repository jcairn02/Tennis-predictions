"""The Wayback survey's pure parts: reading a CDX answer, naming a capture's edition, spotting point-data URLs."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "official_point_feeds"))

import wayback_survey as W  # noqa: E402

HEADER = ["timestamp", "original", "statuscode", "mimetype", "length", "digest"]


def test_a_cdx_answer_with_and_without_a_resume_key():
    row = ["20240128132209", "https://prod-scores-api.ausopen.com/match-centre/MS701", "200", "application/json", "9", "A"]
    rows, resume = W.parse_answer([HEADER, row, [], ["next-page-key"]])
    assert resume == "next-page-key" and rows[0]["original"].endswith("MS701") and len(rows) == 1
    assert W.parse_answer([HEADER, row]) == ([dict(zip(HEADER, row))], None) and W.parse_answer([]) == ([], None)
    url = W.cdx_url(W.QUERIES["ao_api"], "k")
    assert "matchType=host" in url and "filter=statuscode%3A200" in url and url.endswith("resumeKey=k")


def test_edition_years():
    def row(ts, original):
        return {"timestamp": ts, "original": original}
    assert W.edition_year(row("20220711142713", "https://www.usopen.org/en_US/scores/2018/feeds/slamtracker/history/4601C.json"), "uso") == 2018
    assert W.edition_year(row("20180303050536", "http://2016.usopen.org/en_US/xml/gen/slamtracker/history/1701C.json"), "uso") == 2016
    # no year in the URL: a capture made before that year's event holds the previous edition
    assert W.edition_year(row("20180303095903", "http://www.usopen.org:80/en_US/xml/gen/slamtracker/history/1701C.json"), "uso") == 2017
    assert W.edition_year(row("20240128132209", "https://prod-scores-api.ausopen.com/match-centre/MS701"), "ao") == 2024
    assert W.edition_year(row("20240105000000", "https://prod-scores-api.ausopen.com/match-centre/MS701"), "ao") == 2023
    assert W.edition_year(row("20240105000000", "https://prod-scores-api.ausopen.com/match-centre/MS701")) is None


def test_point_data_urls():
    yes = ["https://prod-scores-api.ausopen.com/match-centre/MS701",
           "https://prod-manhattan-api.ausopen.com/year/2019/match/GS201",
           "http://www.ausopen.com/en_AU/xml/gen/slamtracker/history/1315C.json",
           "https://www.usopen.org/en_US/scores/feeds/2019/slamtracker/history/2701U.json",
           "https://api.wtatennis.com/tennis/tournaments/901/2022/matches/LS001/point-by-point"]
    no = ["https://prod-scores-api.ausopen.com/event/257391/draws",
          "https://www.wimbledon.com/assets/images/scores/slamtracker/key.png",
          "https://ausopen.com/match/2023-stefanos-tsitsipas-vs-novak-djokovic-ms701"]
    assert all(W.POINT_DATA.search(u) for u in yes) and not any(W.POINT_DATA.search(u) for u in no)
    assert W.url_family("ao_api", "https://prod-scores-api.ausopen.com/year/2023/period/MD/day/3/results") == "results"
    assert W.url_family("uso_slamtracker", "https://www.usopen.org/en_US/scores/feeds/2019/slamtracker/history/1701C.json") \
        == "slamtracker/history"
