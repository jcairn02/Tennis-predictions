"""Career-coverage study, step 3: render the HTML report from coverage.json.

Fills report_template.html: `{{name}}` tokens take the numbers and sentences built here from the
measured results, and the `__REPORT_DATA__` placeholder takes a compact JSON copy of the per-match
table that the page's charts and match explorer are drawn from.

Reads data/studies/career_coverage/{coverage.json, atp_profile_totals.json};
writes docs/studies/career_coverage/report.html.
Run: ./python.sh src/eda/career_coverage/render_report.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "data" / "studies" / "career_coverage"
TEMPLATE = Path(__file__).with_name("report_template.html")
OUT = ROOT / "docs" / "studies" / "career_coverage" / "report.html"

DEPTH = ["Not in our data", "Listed only, no score", "Score only", "Score + serve stats", "Point by point", "Shot by shot"]
DEPTH_KEYS = ["Missing", "Listed only, no result", "Result, no statistics", "Result + serve/return totals",
              "Point-by-point sequence", "Shot-by-shot chart"]
LEVELS = ["ITF qualifying", "ITF main draw", "Challenger qualifying", "Challenger main draw", "Tour qualifying",
          "Tour main draw", "Davis Cup"]
REASONS = ["level never collected (ITF qualifying)", "after Sackmann ends (June 2026); no other source",
           "rest of the event is present", "whole event absent"]
SOURCES = ["sackmann", "tml", "tennis_data", "otd", "live_tennis_api", "charting", "slam_points", "polymarket"]
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def share(n, d) -> str:
    """Percent for prose: whole numbers, one decimal below 1% or above 99% so nothing rounds to 0 or 100."""
    if not d:
        return "0"
    v = 100 * n / d
    if 0 < v < 1 or 99 < v < 100:
        return f"{v:.1f}"
    return f"{round(v)}"


def fmt(n) -> str:
    return f"{n:,}"


def count_word(n) -> str:
    return WORDS.get(n, fmt(n))


def plural(n, one, many) -> str:
    return f"{fmt(n)} {one if n == 1 else many}"


def main():
    cov = json.loads((STUDY / "coverage.json").read_text(encoding="utf-8"))
    profile = json.loads((STUDY / "atp_profile_totals.json").read_text(encoding="utf-8"))["players"]
    players = sorted(cov["players"], key=lambda p: p["rank_2026_08_31"])
    index = {p["name"]: i for i, p in enumerate(players)}
    matches = cov["matches"]

    rows = []
    for m in matches:
        mask = sum(1 << k for k, s in enumerate(SOURCES) if s in (m["sources"] or "").split(","))
        rows.append([index[m["player"]], m["event_date"], m["event_name"], LEVELS.index(m["level"]), m["round"],
                     m["wl"], f"{m['opp_first']} {m['opp_last']}".strip(), m["score"] or "", int(m["depth"]), mask,
                     REASONS.index(m["why_missing"]) if m["why_missing"] else -1, 0 if m["ref_source"] == "atp" else 1,
                     int(bool(m["walkover"])), int(bool(m["has_stats_atp"])), int(m["year"])])

    wl_agree = 0
    for p in players:
        mine = [m for m in matches if m["player"] == p["name"]]
        tour = [m for m in mine if m["level"] in ("Tour main draw", "Davis Cup") and m["ref_source"] == "atp"]
        p["tour_wl_record"] = [sum(m["wl"] == "W" for m in tour), sum(m["wl"] == "L" for m in tour)]
        prof = profile[p["atp_code"]]
        p["tour_wl_profile"] = [prof["won"], prof["lost"]]
        wl_agree += p["tour_wl_record"] == p["tour_wl_profile"]
        p["wl"] = [sum(m["wl"] == "W" for m in mine), sum(m["wl"] == "L" for m in mine)]

    extras = [[x["player"], x["source"], x["date"], x["event_name"], x["round"], x["opp_name"], x["won"], x["score"],
               x["link"], x["id_matches"], x["name_matches"], x.get("elsewhere") or ""] for x in cov["local_not_in_reference"]]
    shown = {"Tour qualifying": "Tour-level qualifying", "Tour main draw": "Tour-level main draw"}
    data = {"depth": DEPTH, "levels": [shown.get(l, l) for l in LEVELS], "reasons": REASONS, "sources": SOURCES,
            "players": [{k: p.get(k) for k in ("atp_code", "name", "ioc", "rank_2026_08_31", "band", "birthdate",
                                                "first_year", "last_year", "reference_matches", "atp_matches",
                                                "tour_wl_record", "tour_wl_profile", "wl", "itf_id")} for p in players],
            "m": rows, "extras": extras}

    # ---------------------------------------------------------------- numbers
    n = len(rows)
    depth = [r[8] for r in rows]
    present, boxed, detail = (sum(d >= k for d in depth) for k in (1, 3, 4))
    missing = n - present
    by_reason = [sum(1 for r in rows if r[10] == k) for k in range(len(REASONS))]
    lvl = lambda names: [r for r in rows if LEVELS[r[3]] in names]
    itf_main = lvl({"ITF main draw"})
    itf_pre = [r for r in itf_main if r[1] < "2025-01-01"]
    itf_post = [r for r in itf_main if "2025-01-01" <= r[1] <= "2026-06-01"]
    upper = lvl({"Challenger qualifying", "Challenger main draw", "Tour qualifying", "Tour main draw"})
    after_june = [r for r in rows if r[1] > "2026-06-01"]
    per_player = []
    for i, p in enumerate(players):
        mine = [r for r in rows if r[0] == i]
        per_player.append({"name": p["name"], "n": len(mine), "present": 100 * sum(r[8] >= 1 for r in mine) / len(mine),
                           "box": 100 * sum(r[8] >= 3 for r in mine) / len(mine),
                           "itf_share": 100 * sum(LEVELS[r[3]].startswith("ITF") for r in mine) / len(mine)})
    lo_p, hi_p = min(per_player, key=lambda t: t["present"]), max(per_player, key=lambda t: t["present"])
    lo_b, hi_b = min(per_player, key=lambda t: t["box"]), max(per_player, key=lambda t: t["box"])
    sizes = sorted(per_player, key=lambda t: t["n"])
    detail_rows = [r for r in rows if r[8] >= 4]
    detail_sources = {s: sum(1 for r in detail_rows if r[9] & (1 << SOURCES.index(s))) for s in ("charting", "slam_points", "live_tennis_api")}

    itf = cov["itf_sample"]
    itf_levels = {r["level"]: r for r in itf["by_level_depth"]}
    itf_q = itf_levels.get("ITF qualifying", {})
    itf_q_n = itf_q.get("matches", 0)
    itf_q_listed = itf_q.get(DEPTH_KEYS[1], 0)
    itf_q_result = sum(itf_q.get(k, 0) for k in DEPTH_KEYS[2:])
    itf_main_extra = itf_levels.get("ITF main draw", {}).get("matches", 0)
    seasons_read = itf["seasons_read"]
    check = cov["itf_check"]

    # ---------------------------------------------------------------- sentences
    result = sum(d >= 2 for d in depth)
    verdict = (
        f"In short: <strong>{share(present, n)}% of the matches on these players' official record are somewhere in "
        f"our data</strong> ({share(result, n)}% with at least the final score), and nearly all of their Challenger "
        f"and tour-level matches come with serve and return statistics "
        f"({share(sum(r[8] >= 3 for r in upper), len(upper))}%). The thin part is the bottom of the pyramid. ITF "
        f"main-draw matches make up {share(len(itf_main), n)}% of these careers, and before 2025 only "
        f"{share(sum(r[8] >= 3 for r in itf_pre), len(itf_pre))}% of them have more than the score. Below the "
        f"Challenger main draw, no source has results after early June 2026. Deeper detail, point by point or shot "
        f"by shot, exists for {share(detail, n)}% of matches. And one kind of professional match is missing from "
        f"both the official ATP record and our data: qualifying at ITF events.")
    xs = cov["local_not_in_reference"]
    unread = [x for x in xs if x["link"] == "official record unread"]
    mism = [p for p in players if p["tour_wl_record"] != p["tour_wl_profile"]]
    explained = []
    for p in mism:  # a gap is explained when it equals the tour-level results in weeks we could not read
        tour_unread = [x for x in unread if x["player"] == p["name"] and x["source"] == "tennis_data"]
        gap = [a - b for a, b in zip(p["tour_wl_profile"], p["tour_wl_record"])]
        if gap == [sum(x["won"] is True for x in tour_unread), sum(x["won"] is False for x in tour_unread)]:
            explained.append(p)
    if not mism:
        wl_note = "They agree for every player, so the transcription reproduces the ATP's own headline figures."
    elif len(explained) == len(mism):
        who = "; ".join(f"{html.escape(p['name'])} ({'–'.join(map(str, p['tour_wl_profile']))} on the profile, "
                        f"{'–'.join(map(str, p['tour_wl_record']))} transcribed)" for p in mism)
        wl_note = (f"They agree for {count_word(wl_agree)} of {count_word(len(players))} players. The difference for "
                   f"{who} is exactly the tour-level matches in the weeks of the record the reading tool could not see "
                   f"(January 2024, see How we checked).")
    else:
        wl_note = f"They agree for {count_word(wl_agree)} of {count_word(len(players))} players; the table under A shows both figures."
    b_text = (
        f"In total the ATP record lists {fmt(n)} matches for the {count_word(len(players))} players, from "
        f"{fmt(sizes[0]['n'])} ({html.escape(sizes[0]['name'])}) to {fmt(sizes[-1]['n'])} "
        f"({html.escape(sizes[-1]['name'])}). As a check on our transcription we compared each player's tour-level "
        f"win–loss record in it with the headline figure on their ATP profile. {wl_note} The list below holds every "
        f"match, with where in our data it was found.")
    reasons_bits = []
    if by_reason[1]:
        reasons_bits.append(f"{plural(by_reason[1], 'is', 'are')} lower-level matches played after early June 2026, "
                            f"when our only source for those levels stops")
    if by_reason[2]:
        reasons_bits.append(f"{fmt(by_reason[2])} single {'match is' if by_reason[2] == 1 else 'matches are'} "
                            f"missing from tournaments we otherwise hold")
    if by_reason[3]:
        reasons_bits.append(f"{fmt(by_reason[3])} belong{'s' if by_reason[3] == 1 else ''} to tournaments absent "
                            f"from every source")
    c_text = (
        f"{share(present, n)}% of the {fmt(n)} matches are in at least one of our sources, and {fmt(missing)} are not. "
        f"The share hardly varies by player, from {share(lo_p['present'], 100)}% ({html.escape(lo_p['name'])}) to "
        f"{share(hi_p['present'], 100)}% ({html.escape(hi_p['name'])}); what decides it is the level and the date. "
        f"Of the {fmt(missing)} missing matches, " + "; ".join(reasons_bits) + ". "
        f"The same charts also show how deep the data goes for each match, which question D takes up.")
    newer = [x for x in xs if x not in unread and (x["date"] or "") >= "2026-09-21"]
    dup = [x for x in xs if x["link"] == "duplicate"]
    errors = [x for x in xs if x not in unread and x not in newer and x not in dup]
    clash = [x for x in errors if x.get("elsewhere")]
    err_players = sorted({x["player"] for x in errors})
    err_years = sorted({(x["date"] or "")[:4] for x in errors})
    dup_players = sorted({x["player"] for x in dup})
    parts = [f"{fmt(len(unread))} come from Walton's January 2024, the weeks of the official record we could not read"] if unread else []
    if newer:
        parts.append(f"{fmt(len(newer))} {'is' if len(newer) == 1 else 'are'} from tournaments still being played this week, "
                     f"not yet posted on the official record")
    if errors:
        who = html.escape(err_players[0]) if len(err_players) == 1 else f"{len(err_players)} players"
        span = err_years[0] if len(err_years) == 1 else f"{err_years[0]}–{err_years[-1]}"
        parts.append(f"{fmt(len(errors))} are ITF results the Sackmann archive credits to {who} in {span} that the "
                     f"official record does not have. In {fmt(len(clash))} of those weeks the official record places the "
                     f"player at a different tournament, so at least those results belong to someone else" if clash else
                     f"{fmt(len(errors))} are results the Sackmann archive credits to {who} in {span} that the official "
                     f"record does not have")
    if dup:
        parts.append(f"{fmt(len(dup))} repeat, under another tournament name and date, matches the same source already "
                     f"holds ({', '.join(html.escape(p) for p in dup_players)})")
    week = sum(cov["linked_rows_dated_to_another_week"].values())
    other_opp = cov["linked_rows_naming_another_opponent"]
    second = cov["linked_rows_under_a_second_player_record"]
    detail_bits = []
    if week:
        detail_bits.append(f"{fmt(week)} Tennis My Life rows are filed under the wrong week, some by as much as ten "
                           f"months")
    if other_opp:
        names = {"sackmann": "Sackmann", "tml": "Tennis My Life"}
        srcs = sorted({names.get(o["source"], o["source"]) for o in other_opp})
        detail_bits.append(f"{fmt(len(other_opp))} {' and '.join(srcs)} rows name a different opponent from the "
                           f"official record (identical scores, so the same match)")
    for name, k in second.items():
        detail_bits.append(f"{fmt(k)} of {html.escape(name)}'s matches sit under a second player record in the Sackmann "
                           f"archive")
    extras_text = (
        f"<p>We also checked the opposite direction: rows in our data for these players that match no official match. "
        f"Our sources hold {fmt(cov['totals']['local_rows'])} rows for the ten players (each source counted "
        f"separately), and {share(cov['totals']['local_rows_linked'], cov['totals']['local_rows'])}% of them match an "
        f"official match. Of the {fmt(len(xs))} rows with a result that do not:</p><ul class=\"findings\">"
        + "".join(f"<li>{p[0].upper() + p[1:]}.</li>" for p in parts) + "</ul>"
        + (f"<p>Some rows that do match an official match disagree with it on a detail. These still count as present "
           f"in the figures above:</p><ul class=\"findings\">" + "".join(f"<li>{b[0].upper() + b[1:]}.</li>" for b in detail_bits)
           + "</ul>" if detail_bits else ""))
    d_text = (
        f"The pattern is set by level and date more than by the player. For Challenger and tour-level matches, "
        f"{share(sum(r[8] >= 3 for r in upper), len(upper))}% come with serve and return statistics. ITF main-draw "
        f"matches are the opposite: before 2025 only {share(sum(r[8] >= 3 for r in itf_pre), len(itf_pre))}% have "
        f"them, because our sources kept only the score at that level. For January 2025 to June 2026 the Sackmann "
        f"archive has statistics for {share(sum(r[8] >= 3 for r in itf_post), len(itf_post))}% of ITF main-draw "
        f"matches. So the early part of a career, usually spent at ITF level, is known by results only, and the "
        f"Challenger part has the standard scoreboard totals. Across the ten careers the share with serve statistics "
        f"runs from {share(lo_b['box'], 100)}% ({html.escape(lo_b['name'])}, {share(lo_b['itf_share'], 100)}% of whose "
        f"career is ITF matches) to {share(hi_b['box'], 100)}% ({html.escape(hi_b['name'])}, "
        f"{share(hi_b['itf_share'], 100)}%).")
    src_bits = [f"{fmt(v)} {label}" for v, label in (
        (detail_sources["live_tennis_api"], "have live score states from the Live Tennis API sample, which covers a "
                                            "single month (June 2026)"),
        (detail_sources["slam_points"], "appear in the Grand Slam point files (to 2024)"),
        (detail_sources["charting"], "were charted shot by shot by volunteers")) if v]
    d_text_2 = (
        f"Deeper layers are rare at this level: {fmt(detail)} of {fmt(n)} matches ({share(detail, n)}%) have a "
        f"point-by-point or shot-by-shot record. Of those, " + "; ".join(src_bits) + " (a match can have more than "
        f"one). Everything else is the score, or the score plus scoreboard totals.")
    if itf["complete_for_all_players"]:
        itf_text = (
            f"The ATP record leaves out qualifying rounds at ITF events, and so does every source in our download. "
            f"The ITF's own record lists {fmt(itf_q_n)} such matches for these players, which the totals above include; "
            f"{fmt(itf_q_result)} of them are in our data with a result.")
        method_itf = "The ITF record was read for every player."
    else:
        read = ", ".join(s.rsplit(" ", 1)[0] + "'s " + s.rsplit(" ", 1)[1] + " season" for s in seasons_read) or "no season"
        listed_part = (", and none appears even as a schedule entry" if not itf_q_listed else
                       f"; {fmt(itf_q_listed)} appear only as schedule entries")
        itf_text = (
            f"The ATP record leaves out qualifying rounds at ITF events, and so does every source in our download, so "
            f"these matches are not in the totals above. We could read the ITF's own record only for {read} before its "
            f"website began refusing automated requests. That season alone has {fmt(itf_q_n)} ITF qualifying matches, "
            f"next to {fmt(itf['same_seasons_atp_matches'])} matches on the ATP record for the same season. "
            f"{'None' if not itf_q_result else fmt(itf_q_result)} of them {'is' if itf_q_result == 1 else 'are'} in our "
            f"data with a result{listed_part}. For a player who still enters ITF qualifying, the whole career is "
            f"noticeably longer than the ATP record shows, and that extra part is invisible to us.")
        method_itf = (
            f"The ITF website began refusing automated requests while it was being read, so its record covers only "
            f"{read}; we did not try to get around the block. The headline figures therefore use the ATP record, "
            f"and ITF qualifying is reported separately.")
    caveat = ("A second, shorter read of every season listed only its tournaments, and every tournament missing from "
              "the first transcription was fetched again.")

    tok = {
        "n_ref": fmt(n), "n_atp": fmt(n), "pct_present": share(present, n), "pct_box": share(boxed, n),
        "pct_detail": share(detail, n), "n_detail": fmt(detail), "n_missing": fmt(missing), "n_extras": fmt(len(extras)),
        "generated": cov["generated_at"][:10], "n_after_june": fmt(len(after_june)),
        "VERDICT": verdict, "B_TEXT": b_text, "C_TEXT": c_text, "EXTRAS_TEXT": extras_text, "D_TEXT": d_text,
        "D_TEXT_2": d_text_2, "ITF_TEXT": itf_text, "METHOD_ITF": method_itf, "CAVEAT_TRANSCRIPTION": caveat,
    }
    page = TEMPLATE.read_text(encoding="utf-8")
    unknown = set(re.findall(r"{{(\w+)}}", page)) - set(tok)
    if unknown:
        raise KeyError(f"template tokens without a value: {sorted(unknown)}")
    for k, v in tok.items():
        page = page.replace("{{" + k + "}}", v)
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    page = page.replace("__REPORT_DATA__", blob)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    for k in ("VERDICT", "B_TEXT", "C_TEXT", "EXTRAS_TEXT", "D_TEXT", "D_TEXT_2", "ITF_TEXT", "METHOD_ITF"):
        print(f"--- {k}\n{tok[k]}")
    print(f"tour-level W-L agrees with the ATP profile for {wl_agree}/{len(players)} players:",
          [(p["name"], p["tour_wl_record"], p["tour_wl_profile"]) for p in players if p["tour_wl_record"] != p["tour_wl_profile"]])
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
