"""The TennisExplorer adapter's parsers (src/ingest/tennisexplorer.py), on synthetic pages built like the site's
(structure observed 21-22 Oct 2026; the prices here are made up, no raw page is committed)."""
import datetime as dt

from src.ingest import tennisexplorer as T

ROW = ('<tr class="one"><td class="first tl"><a href="#"><span class="i eLink">&nbsp;</span><span class="t">{book}</span>'
       '</a></td><td class="k1">{k1}</td><td class="k2">{k2}</td></tr>')
MOVES = ('<div class="odds-in odown">{last}<div class="odds-change-div"><table cellspacing="0">{rows}'
         '<tr><td colspan="3" class="title">Opening odds</td></tr><tr><td>{open_t}</td><td class="bold">{open}</td>'
         '<td class="diff-down">&nbsp</td></tr></table></div></div>')
MOVE = '<tr><td>{t}</td><td class="bold">{v}</td><td class="diff-down">-0.03</td></tr>'


def page(day="18.10.2026", hhmm="10:40", k1_moves=(("18.10. 10:21", "2.15"), ("17.10. 22:00", "2.18")),
         open_t="17.10. 20:23", extra_tab=True):
    k1 = MOVES.format(last=k1_moves[0][1], rows="".join(MOVE.format(t=t, v=v) for t, v in k1_moves),
                      open_t=open_t, open="2.19")
    k2 = MOVES.format(last="1.79", rows=MOVE.format(t="18.10. 10:21", v="1.79"), open_t=open_t, open="1.75")
    rows = ROW.format(book="Pinnacle", k1=k1, k2=k2) + ROW.format(book="bet365", k1='<div class="odds-in">2.10</div>',
                                                                   k2='<div class="odds-in">1.72</div>')
    over = ('<div id="oddsMenu-2-data" style="display:none"><table class="result"><tr><td class="first tl">'
            '<span class="t">Pinnacle</span></td><td class="k1">9.99</td><td class="k2">9.99</td></tr></table></div>'
            if extra_tab else "")
    return (f'<html><head><title>Tennis Explorer - Match detail</title></head><body><div id="hdr">22.10. 03:07, '
            f'<span class="timezone" title="Timezone: Berlin, Prague, Vienna">GMT+1</span></div>'
            f'<div id="center"><h1 class="bg">Davidovich Fokina - Jodar</h1>'
            f'<div class="box boxBasic lGray"><span class="upper">{day}</span>, {hhmm}, <a href="/shanghai/2026/atp-men/">'
            f'Shanghai</a>, final, hard</div><div class="box boxBasic lGray"><table class="result gDetail noMgB"><thead><tr>'
            f'<th class="plName" colspan="2"><a href="/player/davidovich-fokina">Davidovich Fokina Alejandro</a></th>'
            f'<td class="gScore">2 : 1</td><th class="plName" colspan="2"><a href="/player/jodar">Jodar Rafael</a></th>'
            f'</tr></thead></table></div><div>head-to-head tables</div><h2 class="bg">Betting odds</h2>'
            f'<div class="box lGray"><div class="inner"><div class="content"><ul class="tabs">'
            f'<li id="oddsMenu-1" class="set"><a onclick="x">Home/Away (2)</a></li>'
            f'<li id="oddsMenu-2"><a onclick="x">Over/Under (1)</a></li></ul>'
            f'<div id="oddsMenu-1-data"><table class="result " cellspacing="0"><tbody><tr class="head"><td class="tl"> </td>'
            f'<td class="k1">Davidovich Fokina Alejandro</td><td class="k2">Jodar Rafael</td></tr>{rows}</tbody></table>'
            f'</div>{over}</div></div></div></div></body></html>')


def test_match_page_summer_time_and_books():
    m = T.parse_match(page())
    assert (m["date"], m["time_berlin"], m["start_utc"]) == ("2026-10-18", "10:40", "2026-10-18T08:40:00+00:00")
    assert (m["p1"], m["p2"], m["round"], m["surface"]) == ("Davidovich Fokina Alejandro", "Jodar Rafael", "final", "hard")
    assert m["ha_tab"] == "Home/Away (2)" and set(m["books"]) == {"Pinnacle", "bet365"}
    assert (m["tz_label"], m["clock"]) == ("Timezone: Berlin, Prague, Vienna", "22.10. 03:07")
    p = m["books"]["Pinnacle"]["k1"]
    assert p["last"] == 2.15 and p["open"] == (dt.datetime(2026, 10, 17, 18, 23, tzinfo=dt.timezone.utc), 2.19)
    assert p["moves"][0] == (dt.datetime(2026, 10, 18, 8, 21, tzinfo=dt.timezone.utc), 2.15)
    assert m["books"]["bet365"]["k2"] == {"last": 1.72, "moves": [], "open": None}


def test_match_page_winter_time_new_year_and_no_later_tab():
    m = T.parse_match(page(day="02.01.2026", hhmm="13:00", k1_moves=(("02.01. 12:10", "2.15"),),
                           open_t="30.12. 18:00", extra_tab=False))
    assert m["start_utc"] == "2026-01-02T12:00:00+00:00"                     # CET: one hour
    p = m["books"]["Pinnacle"]["k1"]
    assert p["open"][0] == dt.datetime(2025, 12, 30, 17, 0, tzinfo=dt.timezone.utc)   # opened in the year before
    assert p["moves"] == [(dt.datetime(2026, 1, 2, 11, 10, tzinfo=dt.timezone.utc), 2.15)]


def test_over_under_tab_not_read_as_home_away():
    m = T.parse_match(page())
    assert m["books"]["Pinnacle"]["k1"]["last"] == 2.15 and len(m["books"]) == 2


def test_event_year_straddles_new_year():
    assert T._year_for(2, 1, dt.date(2025, 12, 29)) == 2026
    assert T._year_for(30, 12, dt.date(2025, 12, 29)) == 2025
    assert T._year_for(18, 10, dt.date(2026, 10, 7)) == 2026


def test_calendar_and_event_pages():
    cal = ('<table><tr class="two" data-type="main"><td class="first shortdate " rowspan="2">01.10.<br>2025</td>'
           '<th class="t-name" rowspan="2"><a href="/shanghai/2025/atp-men/"><strong>Shanghai</strong></a></th>'
           '<td class="s-color" rowspan="2"><span title="Hard">&nbsp;</span></td><td class="draw">96</td></tr>'
           '<tr class="one" data-type="lower"><td class="first shortdate">29.09.<br>2025</td><th class="t-name">'
           '<a href="/olbia-challenger/2025/atp-men/">Olbia chall.</a></th><td class="draw">32</td></tr></table>')
    rows = T.parse_calendar(cal, "atp", 2025)
    assert [(r["slug"], r["type"], r["start"], r["draw"]) for r in rows] == [
        ("shanghai", "main", "2025-10-01", 96), ("olbia-challenger", "lower", "2025-09-29", 32)]
    ev = ('<div id="tournamentTabs-1-data"><table class="result"><tbody>'
          '<tr id="r0" class="one"><td class="first time" rowspan="2">18.10.<br />10:40</td>'
          '<td title="final" rowspan="2">F</td><td class="t-name"><a href="/player/davidovich-fokina/">Davidovich Fokina</a>'
          '</td><td class="result">2</td><td class="course" rowspan="2">2.12</td><td class="course" rowspan="2">1.72</td>'
          '<td><a href="/match-detail/?id=3351563">info</a></td></tr><tr id="r0b" class="one"><td class="t-name">'
          '<a href="/player/jodar/">Jodar</a></td><td class="result">1</td></tr></tbody></table></div>')
    (m,) = T.parse_event(ev, "atp", dt.date(2026, 10, 7))
    assert (m["te_id"], m["day"], m["time_berlin"], m["round"], m["p1"], m["p2"], m["sets1"], m["h"], m["a"]) == (
        3351563, "2026-10-18", "10:40", "final", "Davidovich Fokina", "Jodar", "2", 2.12, 1.72)


def test_same_round_splits_a_finals_rematch():
    assert T._same_round("F", "final") and not T._same_round("F", "round robin")
    assert T._same_round("RR", "round robin") and not T._same_round("RR", "final")
    assert T._same_round("R32", "1. round")


def test_close_names_inside_one_event():
    t = T.name_tokens
    assert T._close_tokens(t("Starodubtseva Yulia"), t("Yuliia Starodubtseva"))
    assert T._close_tokens(t("Kasatkina Darya"), t("Daria Kasatkina"))
    assert T._close_tokens(t("Shelbayh Abedallah"), t("Abdullah Shelbayh"))
    assert T._close_tokens(t("Wolf Jeffrey John"), t("J.J. Wolf"))
    assert T._close_tokens(t("Ku Yeon Woo"), t("Yeonwoo Ku"))          # the same letters, split differently
    assert T._close_tokens(t("Ma Yexin"), t("Ye Xin Ma"))
    assert not T._close_tokens(t("Cerundolo Francisco"), t("Juan Manuel Cerundolo"))
    assert not T._close_tokens(t("Ma Yexin"), t("Ma Shuyue"))
    # Accepted by the loose test (shared surname, same initial). Only the second pass uses it, inside one event and
    # with both players required, so a namesake would also need the same opponent at the same event.
    assert T._close_tokens(t("Pliskova Kristyna"), t("Karolina Pliskova"))
    assert T._close_tokens(t("Wang Xiyu"), t("Wang Xinyu"))


EV_ROW = ('<tr id="r{i}" class="one"><td class="first time" rowspan="2">{day}<br />14:10</td>{rnd}'
       '<td class="t-name"><a href="/player/{a}/">{a}</a></td><td class="result">2</td>'
       '<td class="course" rowspan="2">1.20</td><td class="course" rowspan="2">4.63</td>'
       '<td><a href="/match-detail/?id={id}">info</a></td></tr><tr id="r{i}b" class="one"><td class="t-name">'
       '<a href="/player/{b}/">{b}</a></td><td class="result">0</td></tr>')


def test_event_pages_under_way_and_without_a_draw_tab():
    # under way: "Next matches" in the first tab (no "r<n>" rows), the results in a box of their own below
    live = ('<div id="center"><ul class="tabs"><li id="tournamentTabs-1">Next matches</li></ul>'
            '<div id="tournamentTabs-1-data"><table class="result"><tbody><tr class="one"><td class="first time">today</td>'
            '<td class="t-name"><a href="/player/x/">X</a></td><td><a href="/match-detail/?id=9">info</a></td></tr>'
            '</tbody></table></div><table class="result moneydetails"><tbody></tbody></table>'
            '<ul class="tabs"><li class="set"><span class="tab">Results</span></li></ul><table class="result"><tbody>'
            + EV_ROW.format(i=0, day="21.10.", rnd='<td title="1. round" rowspan="2">1R</td>', a="sinner", b="ruud", id=5)
            + '</tbody></table></div><div id="right"><table class="result"><tbody>'
            + EV_ROW.format(i=0, day="21.10.", rnd="", a="other", b="event", id=7) + '</tbody></table></div>')
    (m,) = T.parse_event(live, "atp", dt.date(2026, 10, 19))
    assert (m["te_id"], m["round"], m["p1"], m["day"]) == (5, "1. round", "sinner", "2026-10-21")
    # the Finals: no draw tab, round-robin rows without a round title
    finals = ('<div id="center"><table class="result"><tbody>'
              + EV_ROW.format(i=0, day="16.11.", rnd='<td title="final" rowspan="2">F</td>', a="sinner", b="alcaraz", id=1)
              + EV_ROW.format(i=1, day="09.11.", rnd='<td rowspan="2" style="0:round">-</td>', a="alcaraz", b="deminaur",
                           id=2) + '</tbody></table></div>')
    a, b = T.parse_event(finals, "atp", dt.date(2025, 11, 9))
    assert (a["te_id"], a["round"], b["te_id"], b["round"], b["day"]) == (1, "final", 2, None, "2025-11-09")
    assert T._same_round("RR", b["round"]) and not T._same_round("RR", a["round"])


def test_same_player():
    assert T._same_player("Davidovich Fokina Alejandro", "Alejandro Davidovich Fokina")
    assert T._same_player("Damm Martin (2003)", "Martin Damm")
    assert T._same_player("Auger-Aliassime Felix", "Felix Auger Aliassime")
    assert not T._same_player("Wang Xiyu", "Wang Xinyu")
    assert not T._same_player("Cerundolo Francisco", "Juan Manuel Cerundolo")
