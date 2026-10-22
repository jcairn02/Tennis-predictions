"""Work package P11's probe (src/eda/gap_downloads/odds_probe.py): the seeded sample, the name rules and linker, and the
BetExplorer and TennisExplorer readers, on synthetic pages built like the sites' (structure observed 22 Oct 2026; every
price here is made up, no raw page is committed)."""
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import odds_probe as O  # noqa: E402


# --- the sample ---------------------------------------------------------------------------------------------------------
def fake_map(weeks):
    rows, uid = [], 0
    for year, monday, n_wch in weeks:
        d = pd.Timestamp(monday)
        for tour, level, n_ed in (("M", "CH", 3), ("W", "CH", n_wch), ("M", "ITF", 4), ("W", "ITF", 4)):
            for e in range(n_ed):
                for k in range(3):
                    rows.append({"uid": uid, "tour": tour, "level": level, "draw": "main", "year": year, "d": d,
                                 "name1": f"Ann Bee{uid}", "name2": f"Cid Dee{uid}", "tname": f"{level} {tour} {e}",
                                 "creator": "sackmann"})
                    uid += 1
        rows.append({"uid": uid, "tour": "M", "level": "ITFQ", "draw": "qual", "year": year,
                     "d": d - pd.Timedelta(days=1), "name1": "Eve Fox", "name2": "Gus Hil", "tname": "ITF M 0",
                     "creator": "tennislive_listed"})
        uid += 1
    return pd.DataFrame(rows)


def test_weekend_qualifying_belongs_to_the_next_monday():
    d = pd.Series(pd.to_datetime(["2025-07-12", "2025-07-13", "2025-07-14", "2025-07-20", "2025-07-13"]))
    draw = pd.Series(["qual", "qual", "qual", "main", "main"])
    assert [str(x.date()) for x in O.week_of(d, draw)] == ["2025-07-14", "2025-07-14", "2025-07-14", "2025-07-14",
                                                           "2025-07-07"]


def test_sample_takes_an_eligible_week_per_year_and_ranks_each_stratum():
    m = fake_map([(2019, "2019-03-04", 0), (2019, "2019-03-11", 1), (2022, "2022-05-09", 1)])
    s, info = O.draw_sample(m, seed=3, years=(2019, 2022))
    assert info["weeks"] == {"2019": "2019-03-11", "2022": "2022-05-09"}      # 4 Mar 2019 has no WTA 125
    assert set(s.level) == {"CH", "ITF", "ITFQ"}
    q = s[s.level.eq("ITFQ")]
    assert len(q) == 2 and set(q.wk.dt.date.astype(str)) == {"2019-03-11", "2022-05-09"}   # Sunday's qualifying moved
    for _, g in s.groupby(["year", "tour", "level"]):
        assert sorted(g["rank"]) == list(range(1, len(g) + 1))
    s2, _ = O.draw_sample(m, seed=3, years=(2019, 2022))
    assert s2["rank"].tolist() == s["rank"].tolist()                             # seeded


# --- names and the linker -----------------------------------------------------------------------------------------------
def test_site_names_and_initials():
    assert O.site_name("Alcala Gurri M.") == (frozenset({"alcala", "gurri"}), "m")
    assert O.site_name("Struff J-L.") == (frozenset({"struff"}), "j")
    assert O.site_name("Etcheverry T. M.") == (frozenset({"etcheverry"}), "t")
    assert O.site_name("Nadal") == (frozenset({"nadal"}), "")
    assert O.same_player("Botic van de Zandschulp", O.site_name("Van De Zandschulp B."))
    assert O.same_player("Hernandez Aguila Abel", O.site_name("Hernandez Aguila A."))   # surname-first order
    assert not O.same_player("Botic van de Zandschulp", O.site_name("Van De Zandschulp K."))
    assert not O.same_player("Ann Bee", O.site_name("Beeby A."))


def test_link_one_none_and_the_same_pair_twice():
    sample = pd.DataFrame([
        {"uid": 1, "tour": "M", "name1": "Ann Bee", "name2": "Cid Dee", "first_day": dt.date(2025, 7, 12),
         "last_day": dt.date(2025, 7, 20)},
        {"uid": 2, "tour": "M", "name1": "Eve Fox", "name2": "Gus Hil", "first_day": dt.date(2025, 7, 12),
         "last_day": dt.date(2025, 7, 20)},
        {"uid": 3, "tour": "W", "name1": "Ivy Jo", "name2": "Kay Lu", "first_day": dt.date(2025, 7, 12),
         "last_day": dt.date(2025, 7, 20)}])
    rows = pd.DataFrame([
        {"site_id": "a", "tour": "M", "day": dt.date(2025, 7, 15), "event": "M15 X", "p1": "Dee C.", "p2": "Bee A.",
         "priced": True},
        {"site_id": "b", "tour": "M", "day": dt.date(2025, 7, 13), "event": "M15 X", "p1": "Fox E.", "p2": "Hil G.",
         "priced": True},
        {"site_id": "c", "tour": "M", "day": dt.date(2025, 7, 16), "event": "M15 X", "p1": "Fox E.", "p2": "Hil G.",
         "priced": False},
        {"site_id": "d", "tour": "W", "day": dt.date(2025, 7, 25), "event": "W15 Y", "p1": "Jo I.", "p2": "Lu K.",
         "priced": True}])                                                       # outside the window
    out = O.link_rows(sample, rows).set_index("uid")
    assert (out.loc[1, "link"], out.loc[1, "site_id"], out.loc[1, "priced"]) == ("one", "a", True)
    assert out.loc[2, "link"] == "several" and out.loc[3, "link"] == "none"


def test_detail_pick_takes_the_first_ranked_priced_matches():
    rows = []
    for i in range(8):
        rows.append({"uid": i, "year": 2025, "tour": "M", "level": "ITF", "rank": 8 - i, "link": "one",
                     "priced": i != 7})
    for i in range(8, 12):
        rows.append({"uid": i, "year": 2025, "tour": "M", "level": "ITFQ", "rank": i, "link": "one", "priced": True})
    picked = O.detail_pick(pd.DataFrame(rows))
    assert picked[picked.level.eq("ITF")].uid.tolist() == [6, 5, 4, 3, 2]      # uid 7 (rank 1) has no price
    assert picked[picked.level.eq("ITFQ")].uid.tolist() == [8, 9]


# --- BetExplorer ------------------------------------------------------------------------------------------------------
BE_DAY = """<html><head><title>Latest Tennis Results | BetExplorer</title></head><body>
<table class="table-main"><tr class="js-tournament"><th><a href="/tennis/itf-men-singles/m15-hurghada/">ITF Men - Singles:
 M15 Hurghada, hard</a></th></tr>
<tr data-dt="7,1,2026,9,00" data-def="0"><td class="table-main__tt"><span>FIN</span><a class="table-main__teamsLink"
 href="/tennis/itf-men-singles/m15-hurghada/bee-ann-dee-cid/AbCd1234/"><span class="table-main__teamLine
 table-main__teamLine--home"><strong>Bee A.</strong></span><span class="table-main__teamLine table-main__teamLine--away">
Dee C.</span></a></td></tr>
<tr class="js-tournament"><th>ITF Men - Doubles: M15 Hurghada, hard</th></tr>
<tr data-dt="7,1,2026,10,00"><td><a class="table-main__teamsLink" href="/tennis/x/y/zz/EfGh5678/"><span
 class="table-main__teamLine--home">Bee A./Fox E.</span><span class="table-main__teamLine--away">Dee C./Hil G.</span>
</a></td></tr></table></body></html>"""


def test_betexplorer_day_rows_singles_only_in_utc():
    rows = O.be_day_rows(BE_DAY)
    assert len(rows) == 1
    r = rows[0]
    assert (r["site_id"], r["tour"], r["category"], r["event"]) == ("AbCd1234", "M", "ITF Men", "M15 Hurghada")
    assert (r["p1"], r["p2"], r["start_utc"]) == ("Bee A.", "Dee C.", "2026-01-07T08:00:00+00:00")


def be_cell(odd, created, archive=True, oid="o1"):
    cls = "archiveOddsMovement__odds table-main__detail-odds" + (" js-has-aodds" if archive else "")
    return (f'<td class="{cls}" data-odd="{odd}" data-created="{created}" data-oid="{oid}" data-bid="16" data-bt="3"'
            f' data-sc="2" data-hcp="E-3-2-0-0-0"></td>')


def test_betexplorer_odds_and_history():
    html = ('<table><tbody><tr data-bid="16"><td><span class="in-bookmaker-logo l16" title="bet365"></span></td><td></td>'
            '<td></td>' + be_cell("1.50", "7,1,2026,08,30") + be_cell("2.50", "7,1,2026,08,40", archive=False) +
            '</tr><tr data-bid="5"><td><span class="in-bookmaker-logo l5" title="Unibet"></span></td><td></td><td></td>'
            '<td data-odd="">-</td></tr></tbody></table>')
    books = O.be_odds({"odds": html})
    assert list(books) == ["bet365"]
    a, b = books["bet365"]["sides"]
    assert (a["odd"], a["set_utc"], b["set_utc"]) == (1.5, "2026-01-07T07:30:00+00:00", "2026-01-07T07:40:00+00:00")
    assert a["archive"] == "/archive-odds/o1/16/3/2/E-3-2-0-0-0/" and a["history"] and not b["history"]
    hist = O.be_history([{"date": "06.01. 20:08", "odd": "1.62", "change": "0"},
                         {"date": "31.12. 18:00", "odd": "1.70", "change": "0"}],
                        ref=dt.datetime(2026, 1, 7, 9, tzinfo=dt.timezone.utc))
    assert hist[0] == (dt.datetime(2025, 12, 31, 17, 0, tzinfo=dt.timezone.utc), 1.7)     # the year before the start
    assert hist[1] == (dt.datetime(2026, 1, 6, 19, 8, tzinfo=dt.timezone.utc), 1.62)
    m = O.book_measures(books, pd.Timestamp("2026-01-07T09:00:00Z"))
    assert (m["n_books"], m["pinnacle"], m["n_books_timed"]) == (1, False, 1)
    assert m["last_change_min_before_start_median"] == 80.0 and m["books_last_change_after_start"] == 0


# --- TennisExplorer -----------------------------------------------------------------------------------------------------
TE_DAY = """<html><head><title>Tennis Explorer: results</title></head><body><table class="result">
<tr class="head flags"><td class="t-name" colspan="2">Futures 2026</td><td class="course">H</td></tr>
<tr id="r1" class="one fRow bott"><td class="first time" rowspan="2">13:30</td><td class="t-name"><a href="/player/bee/">
Bee A.</a></td><td class="coursew" rowspan="2">1.25</td><td class="course" rowspan="2">3.50</td>
<td rowspan="2"><a href="/match-detail/?id=123">info</a></td></tr>
<tr id="r1b" class="one"><td class="t-name"><a href="/player/dee/">Dee C.</a></td></tr>
<tr class="head flags"><td class="t-name" colspan="2"><a href="/x-itf/2026/wta-women/">X ITF</a></td></tr>
<tr id="r2" class="two bott"><td class="first time" rowspan="2">10:00</td><td class="t-name"><a href="/player/fox/">
Fox E.</a></td><td class="coursew" rowspan="2">&nbsp;</td><td class="course" rowspan="2">&nbsp;</td>
<td rowspan="2"><a href="/match-detail/?id=124">info</a></td></tr>
<tr id="r2b" class="two"><td class="t-name"><a href="/player/hil/">Hil G.</a></td></tr></table></body></html>"""


def test_tennisexplorer_day_rows_and_prices():
    rows = O.te_day_rows(TE_DAY, dt.date(2026, 1, 7), "M")
    assert [(r["site_id"], r["event"], r["event_href"], r["p1"], r["p2"], r["priced"], r["time_berlin"]) for r in rows] \
        == [(123, "Futures 2026", None, "Bee A.", "Dee C.", True, "13:30"),
            (124, "X ITF", "/x-itf/2026/wta-women/", "Fox E.", "Hil G.", False, "10:00")]


def test_tennisexplorer_books_from_the_adapters_parser():
    sys.path.insert(0, str(PROJECT_ROOT / "test" / "pinnacle_gap"))
    from test_tennisexplorer import page
    from src.ingest import tennisexplorer as T
    parsed = T.parse_match(page())
    books = O.te_books(parsed)
    pin = books["Pinnacle"]["sides"][0]
    assert pin["odd"] == 2.15 and pin["set_utc"] == "2026-10-18T08:21:00+00:00"
    assert pin["opening_utc"] == "2026-10-17T18:23:00+00:00" and pin["n_moves"] == 2
    assert books["bet365"]["sides"][0]["set_utc"] is None                        # untimed
    m = O.book_measures(books, pd.Timestamp(parsed["start_utc"]))
    assert (m["n_books"], m["pinnacle"], m["pinnacle_timed"], m["n_books_timed"], m["n_books_opening"]) == \
        (2, True, True, 1, 1)
    assert m["pinnacle_last_min_before_start"] == 19.0


def test_evidence_holds_no_price(tmp_path, monkeypatch):
    monkeypatch.setattr(O, "STUDY", tmp_path)
    monkeypatch.setattr(O, "RAW", tmp_path)
    t = pd.DataFrame([{"uid": 1, "year": 2026, "tour": "M", "level": "ITF", "rank": 1, "link": "one", "priced": True,
                       "site_id": "a", "name1": "Ann Bee", "name2": "Cid Dee"}])
    site = O.Site("fake", "https://example.invalid", 0)
    out = O.finish("fake", site, t, pd.DataFrame(), t, t, {1: {"n_books": 3, "pinnacle": True}}, None)
    table = pd.read_csv(tmp_path / "odds_probe_fake.csv.gz")
    assert "name1" not in table and not any(c in table for c in ("odd", "price", "p_home"))
    assert json.loads((tmp_path / "odds_probe_fake.json").read_text())["by_stratum"]["2026 M ITF"]["pinnacle"] == 1
    assert out["site"] == "fake"
