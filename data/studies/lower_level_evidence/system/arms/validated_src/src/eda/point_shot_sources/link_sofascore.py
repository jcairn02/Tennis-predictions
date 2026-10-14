"""Point/shot sources study, step 1: link the ten sampled players' SofaScore match lists to their official record.

Question: for the career-coverage sample (ten Challenger players, 4,055 official matches), which matches
does SofaScore list, and which of those carry a point-by-point record?

Input: data/studies/point_shot_sources/sofascore_raw/<code>.txt, one file per player: the player's SofaScore
match list (https://api.sofascore.com/api/v1/team/<id>/events/last/<page>), read page by page on
23 September 2026 through the WebFetch tool (plain HTTP clients receive HTTP 403; that was not worked
around) and transcribed as one line per event:
    id | startTimestamp | tournament | category | round | home | away | winnerCode | finalResultOnly |
    firstToServe | status | home sets | away sets
Page 0 holds the newest events and higher pages go back in time; within a page events run oldest to newest.
The reading tool cuts each 30-event page after 18-25 events, so the newest events of every page are unseen.
The unseen stretch is known (after the last event read on page p, before the first event read on page p-1),
and a match whose playing days touch it is reported as unobserved rather than absent.

Point-level marker: `firstToServe` is set on events for which SofaScore holds a point-by-point record; the
event's /point-by-point endpoint answers 404 otherwise. The marker is checked against that endpoint for a
stratified sample recorded in pbp_checks.csv (see check_pbp_sample.py).

Link rule (the career-coverage study's name rule, plus surnames written with or without spaces): a SofaScore
singles event links to an official match of the same player when the opponent's name agrees (opp_score >= 1)
and the event starts between 12 days before and 20 days after the official tournament date. Ties break on name
score, round, a shared place word in the tournament names, a finished (not cancelled) event, the distance to
the match's playing days and to the tournament start; each event links at most once.

Reads data/studies/career_coverage/reference_record.csv; writes sofascore_events.csv, sofascore_links.csv
and sofascore_summary.json to data/studies/point_shot_sources/.
Run: ./python.sh src/eda/point_shot_sources/link_sofascore.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "point_shot_sources"
RAW = OUT / "sofascore_raw"
REFERENCE = ROOT / "data" / "studies" / "career_coverage" / "reference_record.csv"
sys.path.insert(0, str(ROOT / "src" / "eda" / "career_coverage"))
sys.path.insert(0, str(ROOT / "src" / "eda" / "merge_feasibility"))
from build_coverage import LEVELS, name_score  # noqa: E402
from scan import norm  # noqa: E402

LINK_WINDOW = (-12, 20)  # days from the official tournament date, as for match-day sources in the career study
FIELDS = ["sofa_id", "ts", "tournament", "category", "sofa_round", "home", "away", "winner_code",
          "final_result_only", "first_to_serve", "status", "home_sets", "away_sets"]
ROUNDS = {"round of 128": "R128", "round of 64": "R64", "round of 32": "R32", "round of 16": "R16",
          "quarterfinals": "QF", "quarterfinal": "QF", "semifinals": "SF", "semifinal": "SF", "final": "F"}


def opp_score(first: str, last: str, other: str) -> int:
    """The career study's name score, plus one case it misses: a surname written with or without spaces
    ('Vandeweghe' / 'T. Van de Weghe') with the same first initial scores 1."""
    s = name_score(first, last, other)
    if s:
        return s
    squeezed, rest = norm(last).replace(" ", ""), norm(other).split()
    initial = norm(first)[:1]
    for k in range(len(rest)):  # drop leading given names or initials one by one
        if "".join(rest[k:]) == squeezed and squeezed and initial and any(t.startswith(initial) for t in rest[:k]):
            return 1
    return 0


GENERIC = {"singles", "qualifying", "challenger", "open", "cup", "men", "mens", "itf", "atp", "tour", "international",
           "championships", "tennis", "doubles", "main"}


def place_agrees(event_name: str, tournament: str) -> int:
    """1 when the official tournament name and SofaScore's share a place word ('Buenos Aires (Argentino)' /
    'Buenos Aires, Argentina'); codes such as M15, F9 or M-ITF-ARG-01A do not count."""
    words = lambda s: {t for t in norm(s).split() if len(t) >= 4 and t not in GENERIC and not any(c.isdigit() for c in t)}
    return int(bool(words(event_name) & words(tournament)))


def sofa_round(label: str) -> str:
    """SofaScore round label as an ATP-style round code; qualifying rounds keep their number when given."""
    s = str(label or "").strip().lower()
    if "qual" in s:
        m = re.search(r"(\d)", s)
        return f"Q{m.group(1)}" if m else "Q"
    return ROUNDS.get(s, s.upper())


def round_agrees(ref_round: str, sofa: str) -> int:
    """2 same round, 1 both qualifying without a number to compare, 0 otherwise."""
    if ref_round == sofa:
        return 2
    return 1 if ref_round.startswith("Q") and sofa.startswith("Q") and "QF" not in (ref_round, sofa) else 0


def play_window(event_type: str, level: str, rnd: str) -> tuple[int, int]:
    """Days, relative to the official tournament date, on which a match of this kind can be played.
    Grand Slam qualifying runs the week before the main draw; other qualifying the weekend before."""
    if event_type == "GS":
        return (-10, -1) if rnd.startswith("Q") and rnd != "QF" else (-1, 14)
    if level == "Davis Cup":
        return (-3, 3)
    if "qualifying" in level:
        return (-3, 2)
    return (-2, 13) if event_type == "1000" else (-2, 8)


def list_complete(pages: pd.DataFrame) -> bool:
    """Paging reached the end of the player's list: a page said hasNextPage false, or the last page asked for was
    missing (HTTP 404, recorded as a page line without events). Otherwise paging stopped at the 1 January 2012
    cut-off and anything older than the last event read is unseen."""
    if not len(pages):
        return False
    last = pages.sort_values("page").iloc[-1]
    return bool(pages["has_next"].eq("false").any()) or ("404" in last["note"] and last["count"] == "")


def parse_listing(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Events and per-page read spans of one player's transcribed SofaScore listing."""
    code = path.stem
    head, events, pages, page = {}, [], [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# player:"):
            head = dict(kv.split(":", 1) for kv in (x.strip() for x in line[2:].split("|")) if ":" in kv)
            head = {k.strip(): v.strip() for k, v in head.items()}
        elif line.startswith("# page"):
            m = re.match(r"# page (\d+)", line)
            page = int(m.group(1))
            pages.append({"code": code, "page": page, "count": _grab(line, "COUNT"),
                          "truncated": _grab(line, "TRUNCATED"), "has_next": _grab(line, "HASNEXT"),
                          "note": line.split("|", 1)[1].strip() if "|" in line else ""})
        elif line and not line.startswith("#") and page is not None:
            p = [x.strip() for x in line.split("|")]
            if len(p) >= 11 and p[0].isdigit() and p[1].isdigit():
                events.append({"code": code, "page": page, **dict(zip(FIELDS, p + [""] * (13 - len(p))))})
    ev = pd.DataFrame(events, columns=["code", "page"] + FIELDS)
    ev["ts"] = pd.to_numeric(ev["ts"], errors="coerce")
    ev = ev.drop_duplicates(subset=["sofa_id"])  # a page read twice after a retry
    return ev, pd.DataFrame(pages), head


def _grab(line: str, key: str) -> str:
    m = re.search(rf"{key}=(\S+)", line)
    return m.group(1) if m else ""


def suspect_timestamps(ev: pd.DataFrame, gap_days: int = 7) -> pd.Series:
    """Timestamps out of order within their page (events run oldest to newest). The transcription occasionally
    copies a timestamp wrongly (a 2025 match written as 2024); such a line breaks the order against both
    neighbours, or against its only neighbour at either end of the page."""
    flag = pd.Series(False, index=ev.index)
    g = gap_days * 86400
    for _, page in ev.groupby("page", sort=False):
        ts = page["ts"].tolist()
        for k, i in enumerate(page.index):
            prev = ts[k - 1] if k > 0 else None
            nxt = ts[k + 1] if k + 1 < len(ts) else None
            if prev is None and nxt is None:
                continue
            if prev is None:            # first line: only a date later than the next line is out of order
                flag[i] = ts[k] > nxt + g
            elif nxt is None:           # last line: only a date earlier than the previous line is out of order
                flag[i] = ts[k] < prev - g
            else:                       # a spike below or above both neighbours
                flag[i] = (ts[k] < prev - g and ts[k] < nxt - g) or (ts[k] > prev + g and ts[k] > nxt + g)
    return flag


def link_timestamps(ev: pd.DataFrame) -> pd.Series:
    """Timestamp used for linking: the transcribed one, or for a suspect line the mean of its page neighbours."""
    ts = ev["ts"].astype("float").copy()
    for _, page in ev.groupby("page", sort=False):
        idx = list(page.index)
        for k, i in enumerate(idx):
            if ev.at[i, "ts_suspect"]:
                near = [ev.at[j, "ts"] for j in (idx[k - 1] if k else None, idx[k + 1] if k + 1 < len(idx) else None)
                        if j is not None and not ev.at[j, "ts_suspect"]]
                ts[i] = sum(near) / len(near) if near else ts[i]
    return ts.astype("int64")


def unseen_spans(ev: pd.DataFrame, now_ts: int, list_complete: bool) -> list[tuple[int, int]]:
    """Open time intervals the listing did not show: the cut tail of each page, the tail after the newest
    event read, and, unless paging reached the end of the list, everything before the oldest event read.
    Suspect timestamps are left out of the page bounds."""
    spans = []
    ok = ev[~ev["ts_suspect"]] if "ts_suspect" in ev else ev
    by_page = ok.groupby("page")["ts"].agg(["min", "max"]).sort_index()
    pages = list(by_page.index)
    for p, q in zip(pages[1:], pages[:-1]):  # page p is older than page q = p - 1 (or the previous page read)
        spans.append((int(by_page.loc[p, "max"]), int(by_page.loc[q, "min"])))
    spans.append((int(by_page["max"].max()), now_ts))
    if not list_complete:
        spans.append((0, int(by_page["min"].min())))
    return [(a, b) for a, b in spans if b > a]


def is_doubles(row) -> bool:
    return "/" in f"{row['home']}{row['away']}" or "doubles" in str(row["tournament"]).lower()


def player_side(name: str, home: str, away: str) -> str:
    first, _, last = name.partition(" ")
    h, a = name_score(first, last, home), name_score(first, last, away)
    return "home" if h > a else "away" if a > h else ""


def link(ref: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """One row per official match: the SofaScore event linked to it, if any."""
    pairs = []
    for i, m in ref.iterrows():
        cand = ev[(ev["code"] == m["code"]) & (ev["days"] >= m["day0"] + LINK_WINDOW[0]) &
                  (ev["days"] <= m["day0"] + LINK_WINDOW[1])]
        for j, e in cand.iterrows():
            s = opp_score(m["opp_first"], m["opp_last"], e["opponent"])
            if s >= 1:
                lo, hi = m["day0"] + m["win_lo"], m["day0"] + m["win_hi"]
                dist = max(lo - e["days"], e["days"] - hi, 0)
                key = (s, round_agrees(m["round"], e["round_code"]), place_agrees(m["event_name"], e["tournament"]),
                       int(e["status"] == "finished"), -dist, -abs(e["days"] - m["day0"]))
                pairs.append((i, j, key))
    pairs.sort(key=lambda t: t[2], reverse=True)
    taken_ref, taken_ev, best = set(), set(), {}
    for i, j, key in pairs:
        if i not in taken_ref and j not in taken_ev:
            taken_ref.add(i)
            taken_ev.add(j)
            best[i] = (j, key)
    # an equally good second event that nothing else took leaves the choice open
    tied = {i for i, j, key in pairs if i in best and j != best[i][0] and key == best[i][1] and j not in taken_ev}
    rows = []
    for i, m in ref.iterrows():
        if i in best:
            j, (s, r, place, _, d, _) = best[i]
            status = "ambiguous" if i in tied else "linked"
            e = ev.loc[j]
            rows.append({"ref_id": m["ref_id"], "sofa_status": status, "sofa_id": e["sofa_id"], "sofa_ts": e["ts"],
                         "sofa_tournament": e["tournament"], "sofa_category": e["category"],
                         "sofa_round": e["sofa_round"], "sofa_opponent": e["opponent"], "name_score": s,
                         "round_agree": r, "place_agree": place, "days_outside_window": -d,
                         "first_to_serve": e["first_to_serve"],
                         "final_result_only": e["final_result_only"], "event_state": e["status"]})
        else:
            rows.append({"ref_id": m["ref_id"], "sofa_status": "absent" if m["seen"] else "unobserved"})
    return pd.DataFrame(rows)


def main():
    ref = pd.read_csv(REFERENCE, dtype=str, keep_default_na=False)
    ref = ref[ref["is_bye"] != "True"].copy()
    ref["event_date"] = pd.to_datetime(ref["event_date"])
    ref["year"] = ref["event_date"].dt.year
    ref["day0"] = (ref["event_date"] - pd.Timestamp("1970-01-01")).dt.days
    ref[["win_lo", "win_hi"]] = pd.DataFrame(
        [play_window(t, lv, r) for t, lv, r in zip(ref["event_type"], ref["level"], ref["round"])], index=ref.index)

    files = sorted(RAW.glob("*.txt"))
    evs, pages, heads = [], [], {}
    now_ts = int(pd.Timestamp("2026-09-23T23:59:59Z").timestamp())
    unseen = {}
    for f in files:
        ev, pg, head = parse_listing(f)
        heads[f.stem] = head
        pages.append(pg)
        if len(ev):
            ev["ts_suspect"] = suspect_timestamps(ev)
            ev["ts_link"] = link_timestamps(ev)
        unseen[f.stem] = unseen_spans(ev, now_ts, list_complete(pg)) if len(ev) else [(0, now_ts)]
        evs.append(ev)
    ev = pd.concat(evs, ignore_index=True)
    names = ref.drop_duplicates("code").set_index("code")["player"]
    ev["player"] = ev["code"].map(names)
    ev["doubles"] = ev.apply(is_doubles, axis=1)
    ev["side"] = [player_side(n, h, a) if not d else "" for n, h, a, d in
                  zip(ev["player"], ev["home"], ev["away"], ev["doubles"])]
    ev["opponent"] = ev.apply(lambda e: e["away"] if e["side"] == "home" else e["home"] if e["side"] == "away" else "",
                              axis=1)
    # a qualifying match sometimes has no round label; its tournament name still says "Qualifying"
    ev["round_code"] = [("Q" if "qualif" in str(t).lower() and not rc.startswith("Q") else rc)
                        for rc, t in zip(ev["sofa_round"].map(sofa_round), ev["tournament"])]
    ev["days"] = ev["ts_link"] // 86400
    ev["date"] = pd.to_datetime(ev["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d %H:%M")

    def observed(m) -> bool:
        spans = unseen.get(m["code"])
        if spans is None:
            return False
        lo = (m["day0"] + m["win_lo"] - 1) * 86400  # one day of slack for local time zones
        hi = (m["day0"] + m["win_hi"] + 2) * 86400
        return not any(a < hi and b > lo for a, b in spans)

    ref["seen"] = [observed(m) for _, m in ref.iterrows()]
    singles = ev[~ev["doubles"] & (ev["side"] != "")]
    links = link(ref[ref["code"].isin(unseen)], singles)
    out = ref.merge(links, on="ref_id", how="left")
    out["sofa_status"] = out["sofa_status"].fillna("no listing")
    out["pbp_marker"] = out["first_to_serve"].fillna("").isin(["1", "2"])

    OUT.mkdir(parents=True, exist_ok=True)
    ev.drop(columns=["days"]).to_csv(OUT / "sofascore_events.csv", index=False)
    keep = ["ref_id", "code", "player", "event_name", "event_type", "event_date", "round", "opp_first", "opp_last",
            "score", "level", "year", "sofa_status", "sofa_id", "sofa_ts", "sofa_tournament", "sofa_category",
            "sofa_round", "sofa_opponent", "name_score", "round_agree", "place_agree", "days_outside_window",
            "first_to_serve",
            "final_result_only", "event_state", "pbp_marker"]
    out[keep].assign(event_date=out["event_date"].dt.strftime("%Y-%m-%d")).to_csv(OUT / "sofascore_links.csv",
                                                                                   index=False)

    linked_ev = set(out["sofa_id"].dropna())
    unlinked = singles[~singles["sofa_id"].isin(linked_ev) & (singles["status"] == "finished")].copy()
    unlinked["draw"] = unlinked["round_code"].str.startswith("Q").map({True: "qualifying", False: "main"})
    unlinked["marker"] = unlinked["first_to_serve"].isin(["1", "2"])
    unlinked["year"] = pd.to_datetime(unlinked["ts"], unit="s").dt.year
    summary = {
        "players": {c: {"sofascore_id": heads[c].get("sofascore_id", ""), "pages": int(len(p)),
                        "list_complete": list_complete(p),
                        "events_read": int((ev["code"] == c).sum()),
                        "singles_read": int(((ev["code"] == c) & ~ev["doubles"]).sum()),
                        "oldest": ev.loc[ev["code"] == c, "date"].min(),
                        "newest": ev.loc[ev["code"] == c, "date"].max()}
                    for c, p in zip([f.stem for f in files], pages)},
        "suspect_timestamps": int(ev["ts_suspect"].sum()),
        "official_matches": int(len(out)),
        "by_status": out["sofa_status"].value_counts().to_dict(),
        "linked_with_point_marker": int((out["sofa_status"].eq("linked") & out["pbp_marker"]).sum()),
        "finished_singles_not_on_official_record": int(len(unlinked)),
        "not_on_official_record_by_kind": [
            {"category": c, "draw": d, "events": int(len(g)), "with_point_marker": int(g["marker"].sum()),
             "years": f"{g['year'].min()}-{g['year'].max()}"}
            for (c, d), g in unlinked.groupby(["category", "draw"])],
    }
    grid = []
    for (lv, y), g in out.groupby(["level", "year"]):
        lk = g["sofa_status"].eq("linked")
        grid.append({"level": lv, "year": int(y), "official": len(g),
                     "observed": int(g["sofa_status"].isin(["linked", "ambiguous", "absent"]).sum()),
                     "linked": int(lk.sum()), "absent": int(g["sofa_status"].eq("absent").sum()),
                     "unobserved": int(g["sofa_status"].eq("unobserved").sum()),
                     "linked_with_point_marker": int((lk & g["pbp_marker"]).sum())})
    summary["by_level_year"] = sorted(grid, key=lambda r: (LEVELS.index(r["level"]), r["year"]))
    (OUT / "sofascore_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "by_level_year"}, indent=1, default=str))
    t = pd.DataFrame(summary["by_level_year"]).groupby("level")[["official", "observed", "linked", "absent",
                                                                 "unobserved", "linked_with_point_marker"]].sum()
    print(t.loc[[lv for lv in LEVELS if lv in t.index]])


if __name__ == "__main__":
    main()
