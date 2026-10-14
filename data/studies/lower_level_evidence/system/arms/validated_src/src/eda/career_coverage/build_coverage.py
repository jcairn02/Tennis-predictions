"""Career-coverage study, step 2: link each sampled player's official record to the staged public dump.

Question: what share of each sampled Challenger player's career is in the staged dump (data/dump,
public sources of 22 Sep 2026), in which sources, by level and year, and with how much in-match data?

Reference record (the "truth" side), fetched 2026-09-23 through the WebFetch tool and transcribed
line by line into data/studies/career_coverage/:
* atp_activity_raw/: the ATP Tour website's per-season singles activity
  (https://www.atptour.com/en/-/www/activity/sgl/<code>/<year>?v=1). It lists ITF World Tennis Tour
  (Futures) main draws, Challenger and tour-level main draws and qualifying, and Davis Cup ties.
* itf_activity_raw/: the ITF website's per-season singles activity
  (https://www.itftennis.com/tennis/api/PlayerApi/GetPlayerActivity?circuitCode=MT&matchTypeCode=S&playerId=<id>&year=<year>).
  It adds ITF qualifying draws, which the ATP does not list, and confirms ITF main draws.
The reference record is the ATP record plus the ITF matches it lacks. College, exhibition and
junior matches are outside it.

Link rule: a local row links to a reference match of the same player when the opponent agrees (ATP
code for Tennis My Life rows; otherwise normalised name equal, one name's tokens contained in the
other's, or same surname plus first initial) and the row's date falls inside a window around the
event week. Round agreement and the smaller date gap break ties; remaining ties are ambiguous.

Depth ladder per reference match (highest layer reached): missing; listed without a result (Live
Tennis API schedule or a Polymarket market only); result without statistics; result with
serve/return totals (Sackmann or Tennis My Life); point-by-point score sequence (Grand Slam point
files, Live Tennis API score states); shot-by-shot chart (Match Charting Project).

Reads data/dump read-only; writes reference_record.csv, local_rows.csv and coverage.json to
data/studies/career_coverage/.
Run: ./python.sh src/eda/career_coverage/build_coverage.py
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
DUMP = ROOT / "data" / "dump"
OUT = ROOT / "data" / "studies" / "career_coverage"
ATP_RAW, ITF_RAW = OUT / "atp_activity_raw", OUT / "itf_activity_raw"
sys.path.insert(0, str(ROOT / "src" / "eda" / "merge_feasibility"))
from scan import file_year, keys_for, name_key, norm, parse_list, td_key, td_variants  # noqa: E402

SACKMANN_LOWER_TIER_END = "2026-06-01"  # last Futures and qualifying/Challenger tournament week in Sackmann
# Parts of the official record the reading tool could not see. The ATP page for Walton's 2024 season is
# longer than the tool reads (about 100,000 characters), so tournaments before Burnie 2 (week of
# 5 Feb 2024) never reached it and every read of them was invented; only the part before the cut is kept.
UNREAD = {"W09E": ("2024-01-01", "2024-02-04")}
RESULT_SOURCES = ("sackmann", "tml", "tennis_data", "otd")
DEPTH = ["Missing", "Listed only, no result", "Result, no statistics", "Result + serve/return totals",
         "Point-by-point sequence", "Shot-by-shot chart"]
LEVELS = ["ITF qualifying", "ITF main draw", "Challenger qualifying", "Challenger main draw", "Tour qualifying",
          "Tour main draw", "Davis Cup"]
STAT_FIELDS = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
MARK = re.compile(r"RET|W/O|WO\b|DEF|ABD|ABN|WALKOVER", re.I)
WINDOW_WEEK = (-10, 10)    # source dated by tournament week: gap to the reference event week, days
WINDOW_DAY = (-12, 20)     # source dated by match day or scheduled time
ITF_ROUNDS = {"1st Round": "R32", "2nd Round": "R16", "Quarter-final": "QF", "Semi-final": "SF", "Final": "F"}


def tokens(name) -> set:
    return set(norm(name).split())


def name_score(first, last, other) -> int:
    """3 same tokens, 2 one name's tokens inside the other's, 1 same surname and first initial or
    another shared token of four letters or more (transliterations: Nikita/Mykyta Mashtakov,
    Mukund Sasikumar/Sasi Kumar Mukund). Callers already hold player and tournament week fixed."""
    a, b = tokens(f"{first} {last}"), tokens(other)
    if not a or not b:
        return 0
    if a == b:
        return 3
    if a <= b or b <= a:
        return 2
    surname, initial = tokens(last), norm(first)[:1]
    if surname & b and initial and any(t.startswith(initial) for t in b - surname):
        return 1
    if any(len(t) >= 4 for t in a & b):
        return 1
    if SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio() >= 0.75:  # Dimitris Azoidis / Demetris Azoides
        return 1
    return 0


def games(score, flip=False) -> tuple:
    """Set scores as (games, games) pairs, tiebreak points dropped; flip turns a loser-first score winner-first."""
    sets = re.findall(r"(\d+)-(\d+)", re.sub(r"\(\d+\)", "", str(score or "")))
    return tuple((int(b), int(a)) if flip else (int(a), int(b)) for a, b in sets)


def round_code(r) -> str:
    r = str(r or "").strip().upper()
    return {"W": "F", "3RD/4TH": "BR"}.get(r, r)


def level_of(event_type: str, rnd: str) -> str:
    qual = re.fullmatch(r"Q\d", rnd) is not None  # Q1-Q4; QF is a main-draw quarter-final
    if event_type == "FU":
        return "ITF qualifying" if qual else "ITF main draw"
    if event_type == "CH":
        return "Challenger qualifying" if qual else "Challenger main draw"
    if event_type == "DC":
        return "Davis Cup"
    return "Tour qualifying" if qual else "Tour main draw"


def season_files(folder: Path, code: str) -> dict:
    """Season files per year. Split or paged versions (_a/_b, _p0...) replace a single-file version of
    the same year; targeted re-fetches of tournaments a transcription dropped (_fix1...) are added to it."""
    by_year = {}
    for f in sorted(folder.glob(f"{code}_*.txt")):
        m = re.fullmatch(rf"{code}_(\d{{4}})(?:_([a-z]+\d*))?\.txt", f.name)
        if m:
            by_year.setdefault(int(m.group(1)), []).append((m.group(2) or "", f))
    out = {}
    for y, fs in sorted(by_year.items()):
        fixes = [f for part, f in fs if part.startswith("fix")]
        parts = [f for part, f in fs if part and not part.startswith("fix")]
        out[y] = (parts or [f for part, f in fs if not part]) + fixes
    return out


# ---------------------------------------------------------------- reference record: ATP

def parse_atp(codes) -> tuple[pd.DataFrame, int, list]:
    matches, n_events, issues = [], 0, []
    for code in codes:
        for year, files in season_files(ATP_RAW, code).items():
            matches += season_matches(code, year, files, issues)
    ma = pd.DataFrame(matches)
    before = len(ma)
    # Davis Cup rubbers of one tie share a stats URL (…/ms000), so a repeated line is one whose match fields all agree
    ma = ma.drop_duplicates(subset=["code", "url", "round", "wl", "opp_code", "opp_first", "opp_last"])
    if len(ma) < before:
        issues.append(f"ATP: {before - len(ma)} repeated match lines dropped (overlapping split files or repeated output)")
    ma = ma[~ma["is_bye"]].reset_index(drop=True)
    n_events = len(ma[["code", "year", "event_id"]].drop_duplicates())
    ma["event_date"] = pd.to_datetime(ma["event_date"], errors="coerce")
    ma["level"] = [level_of(t, r) for t, r in zip(ma["event_type"], ma["round"])]
    ma["ref_id"] = (ma["code"] + ":atp:" + ma["url"].str.extract(r"archive/(.+)$", expand=False).fillna("")
                    + ":" + ma["opp_code"].where(ma["opp_code"] != "", ma["opp_last"].map(norm)))
    ma["ref_source"] = "atp"
    return ma, n_events, issues


def season_matches(code, year, files, issues) -> list:
    """Match lines of one season. A targeted re-fetch (_fix file) replaces the lines of every tournament
    it names, either with its own T/M lines or, for a `NONE|<EventId>` line, with nothing."""
    season, fixed = [], set()
    for f in files:
        _, ms = parse_atp_file(code, year, f, issues)
        if "_fix" in f.name:
            text = f.read_text(encoding="utf-8").splitlines()
            fixed |= {ln.split("|")[1].strip() for ln in text if ln.startswith(("T|", "NONE|")) and ln.count("|") >= 1}
        season += ms
    return [m for m in season if "_fix" in m["file"] or m["event_id"] not in fixed]


def parse_atp_file(code, year, f, issues):
    events, matches, cur = [], [], None
    for line in f.read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in line.strip().split("|")]
        if p[0] == "T" and len(p) >= 11:
            cur = {"event_id": p[1], "event_name": p[2], "event_type": p[3], "event_date": p[4], "n_listed": p[-1]}
            events.append(cur)
        elif p[0] == "M" and len(p) >= 12 and cur is not None:
            um = re.search(r"archive/(\d{4})/(\w+)/(\w+)", p[1])
            rest = p[11:-1]
            matches.append({"code": code, "year": year, "url": p[1], "url_event": um.group(2) if um else "",
                            **{k: cur[k] for k in ("event_id", "event_name", "event_type", "event_date")},
                            "round": round_code(p[2]), "wl": p[4], "opp_code": p[5].upper(),
                            "opp_first": p[6], "opp_last": p[7], "score": p[10],
                            "reason": next((x for x in [p[10]] + rest if MARK.search(x)), ""),
                            # a bye has no opponent; an IsBye flag alone is not trusted (one played 1-6 0-6
                            # match was transcribed with IsBye=true), so it also needs a score without games
                            "is_bye": (p[6] == "" and p[7] == "") or (any(x.lower() == "true" for x in rest)
                                                                      and not re.search(r"\d", p[10])),
                            "has_stats_atp": p[-1].lower() == "true", "file": f.name})
    ids = {e["event_id"]: e for e in events}
    for m in matches:  # a line placed under the wrong tournament keeps the event named by its stats URL
        if m["url_event"] and m["url_event"] != m["event_id"]:
            if m["url_event"] in ids:
                m.update({k: ids[m["url_event"]][k] for k in ("event_id", "event_name", "event_type", "event_date")})
                issues.append(f"{f.name}: {m['url']} re-attached to event {m['event_id']}")
            else:
                issues.append(f"{f.name}: {m['url']} sits under event {m['event_id']}, its URL names another")
    for e in events:
        listed = sum(1 for m in matches if m["event_id"] == e["event_id"])
        if str(listed) != e["n_listed"]:
            issues.append(f"{f.name}: event {e['event_id']} says {e['n_listed']} matches, {listed} transcribed")
    return events, matches


# ---------------------------------------------------------------- reference record: ITF

def itf_start(dates: str):
    """'18 Dec to 24 Dec 2023' -> 2023-12-18; '30 Dec to 05 Jan 2025' -> 2024-12-30."""
    m = re.match(r"(\d{1,2}) (\w{3}) to (\d{1,2}) (\w{3}) (\d{4})", str(dates))
    if not m:
        return pd.NaT
    start = pd.to_datetime(f"{m.group(1)} {m.group(2)} {m.group(5)}", format="%d %b %Y", errors="coerce")
    end = pd.to_datetime(f"{m.group(3)} {m.group(4)} {m.group(5)}", format="%d %b %Y", errors="coerce")
    return start - pd.DateOffset(years=1) if pd.notna(start) and pd.notna(end) and start > end else start


def parse_itf(codes) -> tuple[pd.DataFrame, list]:
    rows, issues = [], []
    for code in codes:
        for year, files in season_files(ITF_RAW, code).items():
            for f in files:
                cur, seen = None, 0
                for line in f.read_text(encoding="utf-8").splitlines():
                    p = [x.strip() for x in line.strip().split("|")]
                    if p[0] == "E" and len(p) >= 10:
                        if cur is not None and str(seen) != cur["n"]:
                            issues.append(f"{f.name}: {cur['name']} {cur['draw']} says {cur['n']} matches, {seen} transcribed")
                        key = re.search(r"/([a-z]-[^/]+)/?$", p[4])
                        cur = {"name": p[1], "tour": p[2], "type": p[3], "key": key.group(1) if key else p[4],
                               "date": itf_start(p[5]), "draw": p[7], "n": p[-1]}
                        seen = 0
                    elif p[0] == "X" and len(p) >= 9 and cur is not None:
                        seen += 1
                        score = next((x for x in reversed(p[9:]) if re.search(r"\d+-\d+", x)), "")
                        if p[3] == "B" or (p[5] == "" and p[6] == ""):
                            continue  # bye
                        qual = cur["draw"].lower().startswith("qual")
                        rows.append({"code": code, "year": year, "itf_match_id": p[1], "event_name": cur["name"],
                                     "itf_tour": cur["tour"], "itf_type": cur["type"], "itf_key": cur["key"],
                                     "event_date": cur["date"], "draw": cur["draw"],
                                     "round": ("Q" + p[2][0]) if qual and p[2][:1].isdigit() else ITF_ROUNDS.get(p[2], p[2]),
                                     "wl": p[3], "reason": p[4], "opp_first": p[5], "opp_last": p[6],
                                     "opp_itf_id": p[8], "score": score, "file": f.name})
                if cur is not None and str(seen) != cur["n"]:
                    issues.append(f"{f.name}: {cur['name']} {cur['draw']} says {cur['n']} matches, {seen} transcribed")
    itf = pd.DataFrame(rows)
    if itf.empty:
        return itf, issues
    before = len(itf)
    itf = itf.drop_duplicates(subset=["code", "itf_match_id"]).reset_index(drop=True)
    if len(itf) < before:
        issues.append(f"ITF: {before - len(itf)} duplicated match lines dropped")
    davis = itf["itf_type"].str.contains("Davis", case=False) | itf["itf_tour"].eq("DC")
    itf["event_type"] = np.where(davis, "DC", "FU")
    itf["level"] = [level_of(t, r) for t, r in zip(itf["event_type"], itf["round"])]
    return itf, issues


def unify(atp: pd.DataFrame, itf: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """ATP record plus the ITF matches it lacks; ITF main draws that the ATP also lists confirm them."""
    atp = atp.assign(itf_confirmed=False)
    if itf.empty:
        return atp, {}
    itf = itf.assign(atp_ref_id="")
    for code, rows in itf.groupby("code"):
        cand = atp[(atp["code"] == code) & atp["event_type"].isin(["FU", "DC"])]
        for i, r in rows.iterrows():
            gap = (r["event_date"] - cand["event_date"]).dt.days.abs()
            # same draw (a qualifying match never confirms a main-draw one, even against the same opponent a week apart)
            c = cand[(gap <= 10) & (cand["event_type"] == r["event_type"]) & (cand["level"] == r["level"])]
            c = c[c.apply(lambda a: name_score(a["opp_first"], a["opp_last"], f"{r['opp_first']} {r['opp_last']}") > 0, axis=1)]
            if len(c):
                itf.at[i, "atp_ref_id"] = c.assign(g=gap[c.index]).sort_values("g").iloc[0]["ref_id"]
    atp.loc[atp["ref_id"].isin(set(itf["atp_ref_id"])), "itf_confirmed"] = True
    extra = itf[itf["atp_ref_id"] == ""].copy()
    extra["ref_id"] = extra["code"] + ":itf:" + extra["itf_match_id"]
    extra["ref_source"] = "itf"
    extra["event_id"] = extra["itf_key"]
    extra["has_stats_atp"] = False
    ref = pd.concat([atp, extra[[c for c in extra.columns if c in atp.columns or c in ("itf_key", "draw")]]],
                    ignore_index=True)
    ref["itf_confirmed"] = ref["itf_confirmed"].fillna(False).astype(bool)
    itf_years = itf.groupby("code")["year"].agg(["min", "max"])
    fu = atp["event_type"].eq("FU") & atp["code"].isin(itf_years.index)
    in_itf_span = fu & atp.apply(lambda a: a["code"] in itf_years.index and
                                 itf_years.loc[a["code"], "min"] <= a["year"] <= itf_years.loc[a["code"], "max"], axis=1)
    check = {"itf_matches_transcribed": len(itf),
             "itf_main_draw_matches": int((~itf["level"].eq("ITF qualifying") & itf["event_type"].eq("FU")).sum()),
             "itf_main_draw_also_in_atp_record": int(((itf["atp_ref_id"] != "") & itf["event_type"].eq("FU")).sum()),
             "itf_qualifying_matches": int(itf["level"].eq("ITF qualifying").sum()),
             "itf_davis_cup_matches": int(itf["event_type"].eq("DC").sum()),
             "atp_itf_matches_in_seasons_fetched_from_itf": int(in_itf_span.sum()),
             "atp_itf_matches_confirmed_by_itf": int((in_itf_span & atp["itf_confirmed"]).sum()),
             "itf_only_main_draw_added": int((extra["level"] == "ITF main draw").sum()),
             "itf_only_davis_cup_added": int((extra["level"] == "Davis Cup").sum())}
    return ref, check


# ---------------------------------------------------------------- local rows from every source

def box(df, side) -> pd.Series:
    return pd.to_numeric(df[f"{side}_svpt"], errors="coerce").fillna(0) > 0


def stat_fields_filled(df) -> pd.Series:
    cols = [f"{s}_{f}" for s in ("w", "l") for f in STAT_FIELDS]
    return df[cols].apply(pd.to_numeric, errors="coerce").notna().sum(axis=1)


def from_winner_loser(df, players, source) -> pd.DataFrame:
    """Rows of a winner/loser file that carry a sampled player's id or name on either side."""
    out = []
    for side in ("winner", "loser"):
        df[f"{side}_key"] = keys_for(df[f"{side}_name"])
        df[f"{side}_id"] = df[f"{side}_id"].fillna("").str.upper()
    for pl in players:
        pid = pl["sackmann_id"] if source == "sackmann" else pl["atp_code"]
        alt = set(pl["sackmann_alt_ids"]) if source == "sackmann" else set()
        key = name_key(pl["name"])
        for side, other in (("winner", "loser"), ("loser", "winner")):
            by_id = df[f"{side}_id"] == pid.upper()
            by_alt = df[f"{side}_id"].isin(alt)
            by_name = df[f"{side}_key"] == key
            hit = df[by_id | by_alt | by_name]
            if hit.empty:
                continue
            out.append(pd.DataFrame({
                "code": pl["atp_code"], "source": source, "source_file": hit["_source_file"].str.split("/").str[-1],
                "source_row": hit["_row"], "date": pd.to_datetime(hit["tourney_date"], format="%Y%m%d", errors="coerce"),
                "date_kind": "tournament week", "event_name": hit["tourney_name"], "tourney_id": hit["tourney_id"],
                "tourney_level": hit["tourney_level"], "round": hit["round"].map(round_code),
                "opp_name": hit[f"{other}_name"], "opp_id": hit[f"{other}_id"],
                "won": side == "winner", "score": hit["score"].fillna(""),
                "id_matches": by_id[hit.index] | by_alt[hit.index], "name_matches": by_name[hit.index],
                "second_record": by_alt[hit.index],
                "has_box": box(hit, "w") & box(hit, "l"), "stat_fields": stat_fields_filled(hit),
                "has_minutes": pd.to_numeric(hit["minutes"], errors="coerce").fillna(0) > 0,
                "svpt_w": hit["w_svpt"], "svpt_l": hit["l_svpt"]}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def load_sackmann(players) -> pd.DataFrame:
    frames = [pd.read_parquet(f) for pattern in ("atp_matches_[0-9]*.parquet", "atp_matches_qual_chall_*.parquet",
                                                 "atp_matches_futures_*.parquet")
              for f in sorted((DUMP / "matches/sackmann_archive/atp").glob(pattern))]
    return from_winner_loser(pd.concat(frames, ignore_index=True), players, "sackmann")


def load_tml(players) -> pd.DataFrame:
    base = DUMP / "matches/tennis_my_life"
    files = (sorted((base / "atp_main").glob("[0-9]*.parquet")) + sorted((base / "atp_challenger").glob("*.parquet"))
             + sorted((base / "atp_qualifying").glob("*.parquet"))
             + [base / "ongoing/ongoing_tourneys.parquet", base / "ongoing/challenger_ongoing_tourneys.parquet"])
    frames = [pd.read_parquet(f) for f in files if (file_year(f) or 9999) >= 2010]
    return from_winner_loser(pd.concat(frames, ignore_index=True), players, "tml")


def load_tennis_data(players) -> pd.DataFrame:
    frames = [pd.read_parquet(f) for f in sorted(DUMP.glob("odds/tennis_data_couk/atp/*/*.parquet")) if int(f.stem) >= 2010]
    td = pd.concat(frames, ignore_index=True)
    td["wk"], td["lk"] = td["Winner"].map(td_key), td["Loser"].map(td_key)
    odds = [c for c in td.columns if re.fullmatch(r"(B365|PS|Max|Avg|BFE)W", c)]
    td["has_odds"] = td[odds].apply(pd.to_numeric, errors="coerce").gt(1.0).any(axis=1)
    out = []
    for pl in players:
        forms = set(td_variants(pl["name"]))
        for side, other in (("wk", "Loser"), ("lk", "Winner")):
            hit = td[td[side].isin(forms)]
            sets = [(f"W{k}", f"L{k}") for k in range(1, 6)]
            score = [" ".join(f"{r[w]}-{r[l]}" for w, l in sets if pd.notna(r[w]) and str(r[w]) != "")
                     for _, r in hit.iterrows()]
            out.append(pd.DataFrame({
                "code": pl["atp_code"], "source": "tennis_data", "source_file": hit["_source_file"].str.split("/").str[-1],
                "source_row": hit["_row"], "date": pd.to_datetime(hit["Date"], errors="coerce"), "date_kind": "match day",
                "event_name": hit["Tournament"], "tourney_level": hit["Series"], "round": "", "opp_name": hit[other],
                "won": side == "wk", "score": score, "has_odds": hit["has_odds"]}))
    return pd.concat(out, ignore_index=True)


def load_otd(players) -> pd.DataFrame:
    otd = pd.read_parquet(DUMP / "matches/open_tennis_data/completed.parquet")
    otd = otd[otd["tour"] == "atp"]
    out = []
    for pl in players:
        pid = f"atp:{pl['sackmann_id']}"
        for me, other in (("player1", "player2"), ("player2", "player1")):
            hit = otd[otd[f"{me}_id"].map(lambda s: pid in parse_list(s))]
            out.append(pd.DataFrame({
                "code": pl["atp_code"], "source": "otd", "source_file": "completed.parquet", "source_row": hit["_row"],
                "date": pd.to_datetime(hit["date"], errors="coerce"), "date_kind": "match day",
                "event_name": hit["tournament_name"], "round": hit["round"].map(round_code),
                "opp_name": hit[f"{other}_name"].map(lambda s: (parse_list(s) or [""])[0]),
                "won": hit["winner_id"].map(lambda s: pid in parse_list(s)), "score": hit["score"].fillna("")}))
    return pd.concat(out, ignore_index=True)


def load_live_tennis_api(players) -> pd.DataFrame:
    lp = pd.read_parquet(DUMP / "players/live_tennis_api_zenodo/players.parquet", columns=["player_id", "name", "tour"])
    names = dict(zip(lp["player_id"], lp["name"]))
    lm = pd.read_parquet(DUMP / "matches/live_tennis_api_zenodo/matches.parquet")
    states = pq.read_table(DUMP / "points/live_tennis_api_zenodo/points_sample_2026-06.parquet",
                           columns=["match_id"]).column("match_id").to_pandas().value_counts()
    out = []
    for pl in players:
        ids = set(lp.loc[(lp["tour"] == "atp") & lp["name"].map(lambda s: tokens(s) == tokens(pl["name"])), "player_id"])
        for me, other in (("player1_id", "player2_id"), ("player2_id", "player1_id")):
            hit = lm[lm[me].isin(ids)]
            out.append(pd.DataFrame({
                "code": pl["atp_code"], "source": "live_tennis_api", "source_file": "matches.parquet",
                "source_row": hit["_row"], "date": pd.to_datetime(hit["scheduled_time_utc"], errors="coerce"),
                "date_kind": "scheduled time", "event_name": hit["tournament"], "tourney_level": hit["tier_key"],
                "round": np.where(hit["is_qualifying"].eq("True"), "Q", ""),
                "opp_name": hit[other].map(names).fillna(""), "won": np.nan, "score": hit["event_status"].fillna(""),
                "lta_match_id": hit["match_id"], "score_states": hit["match_id"].map(states).fillna(0).astype(int)}))
    return pd.concat(out, ignore_index=True)


def load_charting(players) -> pd.DataFrame:
    mcp = pd.read_parquet(DUMP / "points/match_charting_project/metadata/charting-m-matches.parquet")
    out = []
    for pl in players:
        for me, other in (("Player 1", "Player 2"), ("Player 2", "Player 1")):
            hit = mcp[mcp[me].map(lambda s: tokens(s) == tokens(pl["name"]))]
            out.append(pd.DataFrame({
                "code": pl["atp_code"], "source": "charting", "source_file": "charting-m-matches.parquet",
                "source_row": hit["_row"], "date": pd.to_datetime(hit["Date"], format="%Y%m%d", errors="coerce"),
                "date_kind": "match day", "event_name": hit["Tournament"], "round": hit["Round"].map(round_code),
                "opp_name": hit[other], "won": np.nan, "score": "", "chart_id": hit["match_id"]}))
    return pd.concat(out, ignore_index=True)


def load_slam_points(players) -> pd.DataFrame:
    out = []
    for f in sorted(DUMP.glob("points/sackmann_archive/slam_pointbypoint/*-matches.parquet")):
        sm = pd.read_parquet(f)
        pts = f.with_name(f.name.replace("-matches", "-points"))
        with_points = set(pq.read_table(pts, columns=["match_id"]).column("match_id").to_pandas()) if pts.exists() else set()
        for pl in players:
            first, last = pl["name"].split(" ", 1)
            short = {norm(f"{first[0]} {last}")}
            for me, other in (("player1", "player2"), ("player2", "player1")):
                hit = sm[sm[me].map(lambda s: tokens(s) == tokens(pl["name"]) or norm(s) in short)]
                if hit.empty:
                    continue
                out.append(pd.DataFrame({
                    "code": pl["atp_code"], "source": "slam_points", "source_file": f.name, "source_row": hit["_row"],
                    "date": pd.to_datetime(hit["year"] + "-01-01", errors="coerce"), "date_kind": "year",
                    "event_name": hit["slam"], "round": "", "opp_name": hit[other], "won": np.nan, "score": "",
                    "slam": hit["slam"], "has_points": hit["match_id"].isin(with_points)}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def load_polymarket(players) -> pd.DataFrame:
    mi = pd.read_parquet(DUMP / "odds/polymarket/market_index.parquet",
                         columns=["id", "question", "sportsMarketType", "gameStartTime", "outcomePrices", "event_id", "_row"])
    ev = pd.read_parquet(DUMP / "odds/polymarket/event_index.parquet", columns=["id", "bucket", "sport_date"])
    ml = mi[mi["sportsMarketType"] == "moneyline"].merge(ev.rename(columns={"id": "event_id"}), on="event_id", how="left")
    q = ml["question"].fillna("")
    ml = ml[~q.str.contains("/", regex=False) & ~q.str.contains(" & ", regex=False)].copy()
    parts = ml["question"].str.split(r"\s+vs\.?\s+", regex=True)
    keep = parts.str.len() == 2
    ml, parts = ml[keep].copy(), parts[keep]
    ml["a"] = parts.str[0].str.rsplit(":", n=1).str[-1].str.strip()
    ml["b"] = parts.str[1].str.strip()
    start = pd.to_datetime(ml["gameStartTime"], utc=True, errors="coerce")
    ml["start"] = start.fillna(pd.to_datetime(ml["sport_date"], utc=True, errors="coerce")).dt.tz_convert(None)
    out = []
    for pl in players:
        for me, other in (("a", "b"), ("b", "a")):
            hit = ml[ml[me].map(lambda s: tokens(s) == tokens(pl["name"]))]
            out.append(pd.DataFrame({
                "code": pl["atp_code"], "source": "polymarket", "source_file": "market_index.parquet",
                "source_row": hit["_row"], "date": hit["start"], "date_kind": "scheduled time",
                "event_name": hit["bucket"], "round": "", "opp_name": hit[other], "won": np.nan,
                "score": hit["outcomePrices"].fillna(""), "market_id": hit["id"]}))
    pm = pd.concat(out, ignore_index=True)
    ids, priced = set(pm["market_id"]), set()
    for f in sorted(DUMP.glob("odds/polymarket/price_history/*/*.parquet")):
        col = pq.read_table(f, columns=["market_id"]).column("market_id").to_pandas()
        priced |= set(col[col.isin(ids)].unique())
    pm["has_prices"] = pm["market_id"].isin(priced)
    return pm


# ---------------------------------------------------------------- linking

def slam_word(slam) -> str:
    return {"ausopen": "australian", "frenchopen": "roland", "usopen": "us open", "wimbledon": "wimbledon"}.get(slam, slam)


def link_rows(ref: pd.DataFrame, local: pd.DataFrame) -> pd.DataFrame:
    """Best reference match for every local row of the same player; ties are ambiguous."""
    local = local.copy()
    local["ref_id"], local["link"], local["gap_days"] = "", "unlinked", np.nan
    local["date_disagrees"], local["opp_disagrees"] = False, False
    for code, rows in local.groupby("code"):
        cand = ref[ref["code"] == code]
        for i, r in rows.iterrows():
            if pd.isna(r["date"]):
                continue
            if r["date_kind"] == "year":
                ok = cand["event_date"].dt.year == r["date"].year
            else:
                window = WINDOW_WEEK if r["date_kind"] == "tournament week" else WINDOW_DAY
                ok = (r["date"].normalize() - cand["event_date"]).dt.days.between(*window)
            c = cand[ok]
            if c.empty:
                continue
            gap = (r["date"].normalize() - c["event_date"]).dt.days
            if r["source"] == "tennis_data":  # "Surname I." names
                opp = c.apply(lambda a: 2 if td_key(r["opp_name"]) in td_variants(f"{a['opp_first']} {a['opp_last']}") else 0, axis=1)
            else:
                opp = c.apply(lambda a: 3 if r["source"] == "tml" and r["opp_id"] and r["opp_id"] == a["opp_code"]
                              else name_score(a["opp_first"], a["opp_last"], r["opp_name"]), axis=1)
            if r["source"] == "slam_points":
                opp = opp.where(c["event_name"].map(norm).str.contains(slam_word(r["slam"])), 0)
            c = c.assign(opp=opp, rnd=(c["round"] == r["round"]).astype(int), dist=gap.abs()).query("opp > 0")
            if c.empty:
                continue
            c = c.sort_values(["opp", "rnd", "dist"], ascending=[False, False, True])
            top = c.iloc[0]
            tied = c[(c["opp"] == top["opp"]) & (c["rnd"] == top["rnd"]) & (c["dist"] == top["dist"])]
            local.at[i, "link"] = "ambiguous" if tied["ref_id"].nunique() > 1 else "linked"
            local.at[i, "ref_id"] = top["ref_id"]
            local.at[i, "gap_days"] = gap[top.name]
    taken = set(local.loc[local["link"] == "linked", ["source", "ref_id"]].itertuples(index=False, name=None))
    # Second pass, rows a source files under the wrong week (Tennis My Life dates some tournaments to
    # another tournament's week, up to ten months away): same round, same opponent, a shared word in
    # the tournament name, within a year, one candidate the source has not already matched.
    # Third pass, rows naming a different opponent (the Sackmann archive files Milan Welte's matches
    # under Alexandre Aubriot): same round and week, identical set scores, one candidate.
    for code, rows in local[(local["link"] == "unlinked") & local["date"].notna()].groupby("code"):
        cand = ref[ref["code"] == code]
        for i, r in rows.iterrows():
            if r["source"] not in ("sackmann", "tml") or not r["round"]:
                continue
            gap = (r["date"].normalize() - cand["event_date"]).dt.days
            free = ~cand["ref_id"].map(lambda x: (r["source"], x) in taken)
            same = cand["round"].eq(r["round"]) & free
            words = {t for t in tokens(r["event_name"]) if len(t) >= 4}
            c = cand[same & gap.abs().le(366) & cand["event_name"].map(lambda e: bool(words & tokens(e)))]
            c = c[c.apply(lambda a: (r["opp_id"] and r["opp_id"] == a["opp_code"])
                          or name_score(a["opp_first"], a["opp_last"], r["opp_name"]) >= 2, axis=1)]
            flag = "date_disagrees"
            if len(c) != 1:
                sets = games(r["score"])
                c = cand[same & gap.between(*WINDOW_WEEK)]
                c = c[c.apply(lambda a: len(sets) >= 2 and games(a["score"], flip=a["wl"] == "L") == sets, axis=1)]
                flag = "opp_disagrees"
            if len(c) == 1:
                local.at[i, "link"], local.at[i, "ref_id"] = "linked", c.iloc[0]["ref_id"]
                local.at[i, "gap_days"], local.at[i, flag] = gap[c.index[0]], True
                taken.add((r["source"], c.iloc[0]["ref_id"]))
    # A row left over that repeats a matched row of the same source (same round, opponent and set
    # scores; the Sackmann archive files Choinski's Germany F3 run a second time as Germany F4) is a copy.
    done = local[local["link"] == "linked"]
    seen = {(r.source, r.code, r.round, name_key(r.opp_name), games(r.score)): r.ref_id for r in done.itertuples()}
    for i, r in local[local["link"] == "unlinked"].iterrows():
        key = (r["source"], r["code"], r["round"], name_key(r["opp_name"]), games(r["score"]))
        if len(key[4]) >= 2 and key in seen:
            local.at[i, "link"], local.at[i, "ref_id"] = "duplicate", seen[key]
    for code, (start, end) in UNREAD.items():
        inside = (local["code"] == code) & local["date"].between(start, end) & (local["link"] == "unlinked")
        local.loc[inside, "link"] = "official record unread"
    # An unmatched tournament-week row in a week the official record has the player at a different
    # tournament cannot be that player's match (the Sackmann archive credits Onclin with ITF wins in
    # Jakarta and Singapore in weeks the ATP has Onclin in Belgium and Egypt): name the official tournament.
    local["elsewhere"] = ""
    for i, r in local[(local["link"] == "unlinked") & local["date_kind"].eq("tournament week")].iterrows():
        cand = ref[(ref["code"] == r["code"]) & (ref["event_date"] - r["date"].normalize()).dt.days.abs().le(3)]
        words = {t for t in tokens(r["event_name"]) if len(t) >= 4}
        other = cand[~cand["event_name"].map(lambda e: bool(words & tokens(e)))]
        if len(other) and len(other) == len(cand):
            local.at[i, "elsewhere"] = other.iloc[0]["event_name"]
    return local


# ---------------------------------------------------------------- coverage measures

def grade(ref: pd.DataFrame, local: pd.DataFrame) -> pd.DataFrame:
    lk = local[local["link"] == "linked"]
    ref = ref.copy()
    ref["sources"] = ref["ref_id"].map(lk.groupby("ref_id")["source"].agg(lambda s: ",".join(sorted(set(s))))).fillna("")

    def has(src, flag=None):
        rows = lk[lk["source"] == src]
        if flag:
            rows = rows[rows[flag].fillna(False).astype(bool)]
        return ref["ref_id"].isin(set(rows["ref_id"]))

    for src in ("sackmann", "tml", "tennis_data", "otd", "live_tennis_api", "charting", "slam_points", "polymarket"):
        ref[f"in_{src}"] = has(src)
    ref["box_sackmann"], ref["box_tml"] = has("sackmann", "has_box"), has("tml", "has_box")
    ref["slam_point_rows"] = has("slam_points", "has_points")
    lta = lk[(lk["source"] == "live_tennis_api") & (lk["score_states"].fillna(0) > 0)]
    ref["score_states"] = ref["ref_id"].isin(set(lta["ref_id"]))
    ref["closing_odds"] = has("tennis_data", "has_odds")
    ref["market_prices"] = has("polymarket", "has_prices")
    result = ref[[f"in_{s}" for s in RESULT_SOURCES]].any(axis=1)
    listed = ref["in_live_tennis_api"] | ref["in_polymarket"]
    boxed = ref["box_sackmann"] | ref["box_tml"]
    ref["depth"] = np.select([ref["in_charting"], ref["slam_point_rows"] | ref["score_states"], boxed, result, listed],
                             [5, 4, 3, 2, 1], 0)
    ref["depth_label"] = ref["depth"].map(dict(enumerate(DEPTH)))
    # a walkover has no games played; transcriptions put "W/O" in the Reason field or the score field
    ref["walkover"] = (ref["reason"].fillna("").str.contains(r"W/O|WO\b|WALKOVER", case=False)
                       & ~ref["score"].fillna("").str.contains(r"\d"))
    miss = ref["depth"] == 0
    after = ref["event_date"] > pd.Timestamp(SACKMANN_LOWER_TIER_END)
    partial = ref.groupby(["code", "event_date", "event_name"])["depth"].transform("max") > 0
    ref["why_missing"] = np.select(
        [~miss, ref["level"].eq("ITF qualifying"),
         ref["level"].isin(["ITF main draw", "Challenger qualifying"]) & after, partial],
        ["", "level never collected (ITF qualifying)", "after Sackmann ends (June 2026); no other source",
         "rest of the event is present"], "whole event absent")
    return ref


def crosstab(df, by, col="depth_label", order=DEPTH):
    t = pd.crosstab([df[b] for b in by], df[col]).reindex(columns=order, fill_value=0)
    t["matches"] = t.sum(axis=1)
    return json.loads(t.reset_index().to_json(orient="records"))


def records(df) -> list:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def main():
    sample = json.loads((OUT / "sample.json").read_text(encoding="utf-8"))
    players = [d for d in sample["draws"] if d["role"] == "pick"]
    sp = pd.read_parquet(DUMP / "players/sackmann_archive/atp/atp_players.parquet",
                         columns=["player_id", "name_first", "name_last", "dob", "ioc"])
    sp["k"] = keys_for(sp["name_first"].fillna("") + " " + sp["name_last"].fillna(""))
    for pl in players:
        pl["sackmann_id"] = sp.loc[(sp["dob"] == pl["birthdate"]) & (sp["k"] == name_key(pl["name"])), "player_id"].iloc[0]
        # a second Sackmann record for the same person: same country, every name word, birth date equal or
        # blank (Nicolas Villalon's later ITF matches sit under "Nicolas Villalon Valdes", id 211477)
        words = tokens(pl["name"])
        same = (sp["ioc"] == pl["ioc"]) & sp["dob"].fillna("").isin(["", pl["birthdate"]]) & (sp["player_id"] != pl["sackmann_id"])
        pl["sackmann_alt_ids"] = sorted(sp.loc[same & sp["k"].map(lambda k: words <= set(k.split())), "player_id"])
        idf = ITF_RAW / f"{pl['atp_code']}_id.txt"
        pl["itf_id"] = idf.read_text(encoding="utf-8").strip().split("|")[1] if idf.exists() else None

    codes = [p["atp_code"] for p in players]
    atp, n_events, issues = parse_atp(codes)
    itf, itf_issues = parse_itf(codes)
    ref, itf_check = unify(atp, itf)
    print(f"ATP record {len(atp):,} matches ({n_events:,} tournament entries); ITF record {len(itf):,} matches; "
          f"reference record {len(ref):,}; {len(issues) + len(itf_issues)} transcription notes")
    loaders = [load_sackmann, load_tml, load_tennis_data, load_otd, load_live_tennis_api, load_charting,
               load_slam_points, load_polymarket]
    local = pd.concat([f(players) for f in loaders], ignore_index=True)
    local = link_rows(ref, local)
    print(pd.crosstab(local["source"], local["link"]))
    ref = grade(ref, local)

    names = {p["atp_code"]: p["name"] for p in players}
    ref["player"], local["player"] = ref["code"].map(names), local["code"].map(names)
    ref.sort_values(["code", "event_date", "ref_id"]).to_csv(OUT / "reference_record.csv", index=False)
    local.to_csv(OUT / "local_rows.csv", index=False)

    # The headline reference is the ATP record, complete for every player. ITF-only matches join it
    # only when the ITF record was read for every player; otherwise they are reported as a sample.
    itf_seasons = sorted({(r.code, int(r.year)) for r in itf.itertuples()}) if not itf.empty else []
    itf_complete = bool(itf_seasons) and {c for c, _ in itf_seasons} == set(codes)
    itf_only = ref[ref["ref_source"] == "itf"]
    itf_sample = {
        "complete_for_all_players": itf_complete,
        "seasons_read": [f"{names[c]} {y}" for c, y in itf_seasons],
        "itf_only_matches": len(itf_only),
        "by_level_depth": crosstab(itf_only, ["level"]) if len(itf_only) else [],
        "by_player_year_level": records(itf_only.groupby(["player", "year", "level"]).size().rename("matches").reset_index())
        if len(itf_only) else [],
        "same_seasons_atp_matches": int(sum(((atp["code"] == c) & (atp["year"] == y)).sum() for c, y in itf_seasons)),
    }
    if not itf_complete:
        ref = ref[ref["ref_source"] == "atp"]

    linked = local[local["link"] == "linked"]
    box_rows = linked[linked["source"].isin(["sackmann", "tml"]) & linked["has_box"].fillna(False).astype(bool)]
    sv = [box_rows[box_rows["source"] == s].drop_duplicates("ref_id").set_index("ref_id")[["svpt_w", "svpt_l"]]
          .apply(pd.to_numeric, errors="coerce") for s in ("sackmann", "tml")]
    b = sv[0].join(sv[1], lsuffix="_s", rsuffix="_t", how="inner")
    unlinked = local[(local["link"] != "linked") & local["source"].isin(RESULT_SOURCES)]
    played = ref[~ref["walkover"]]
    matches_cols = ["ref_id", "player", "year", "event_date", "event_name", "event_type", "level", "round", "wl",
                    "opp_first", "opp_last", "score", "ref_source", "itf_confirmed", "has_stats_atp", "sources",
                    "depth", "depth_label", "why_missing", "walkover", "closing_odds", "market_prices"]
    result = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "reference_fetched": "2026-09-23",
        "players": [{**p, "reference_matches": int((ref["code"] == p["atp_code"]).sum()),
                     "atp_matches": int((atp["code"] == p["atp_code"]).sum()),
                     "first_year": ref.loc[ref["code"] == p["atp_code"], "year"].min(),
                     "last_year": ref.loc[ref["code"] == p["atp_code"], "year"].max()} for p in players],
        "transcription_notes": issues + itf_issues,
        "itf_check": itf_check,
        "itf_sample": itf_sample,
        "totals": {"reference_matches": len(ref), "atp_record_matches": len(atp), "itf_only_matches": int((ref["ref_source"] == "itf").sum()),
                   "walkovers": int(ref["walkover"].sum()), "local_rows": len(local),
                   "local_rows_linked": int((local["link"] == "linked").sum())},
        "depth_overall": crosstab(ref.assign(all="all"), ["all"]),
        "depth_by_player": crosstab(ref, ["player"]),
        "depth_by_level": crosstab(ref, ["level"]),
        "depth_by_year": crosstab(ref, ["year"]),
        "depth_by_player_level": crosstab(ref, ["player", "level"]),
        "depth_by_level_year": crosstab(ref, ["level", "year"]),
        "depth_played_only_by_level": crosstab(played, ["level"]),
        "layers_by_level": records(ref.groupby("level")[[c for c in ref.columns if c.startswith("in_")] +
                                                         ["box_sackmann", "box_tml", "slam_point_rows", "score_states",
                                                          "closing_odds", "market_prices", "has_stats_atp"]]
                                   .sum().reset_index()),
        "missing_by_reason": crosstab(ref[ref["depth"] == 0], ["level"], col="why_missing",
                                      order=sorted(set(ref["why_missing"]) - {""})),
        "local_not_in_reference": records(unlinked[["player", "source", "source_file", "source_row", "date", "event_name",
                                                    "round", "opp_name", "won", "score", "link", "id_matches",
                                                    "name_matches", "elsewhere"]].assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d"))),
        "linked_rows_dated_to_another_week": {s: int(n) for s, n in
                                              linked[linked["date_disagrees"]].groupby("source").size().items()},
        "linked_rows_under_a_second_player_record": {p: int(n) for p, n in
                                                     linked[linked["second_record"].fillna(False).astype(bool)]
                                                     .groupby("player").size().items()},
        "linked_rows_naming_another_opponent": records(linked[linked["opp_disagrees"]][
            ["player", "source", "date", "event_name", "round", "opp_name", "score"]]
            .assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d"))),
        "box_score_rows": {"rows": len(box_rows), "all_18_fields": int((box_rows["stat_fields"] == 18).sum()),
                           "with_minutes": int(box_rows["has_minutes"].fillna(False).astype(bool).sum())},
        "sackmann_vs_tml_serve_points": {"matches_with_box_in_both": int(len(b)),
                                         "identical": int(((b["svpt_w_s"] == b["svpt_w_t"]) & (b["svpt_l_s"] == b["svpt_l_t"])).sum())},
        "matches": records(ref[matches_cols].assign(event_date=lambda d: d["event_date"].dt.strftime("%Y-%m-%d"))),
    }
    (OUT / "coverage.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print(pd.DataFrame(result["depth_by_player"]).to_string(index=False))
    print(pd.DataFrame(result["depth_by_level"]).to_string(index=False))
    print(json.dumps(itf_check, indent=1))
    print(f"wrote {OUT / 'coverage.json'}")


if __name__ == "__main__":
    main()
