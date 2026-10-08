"""Real match start times from the Flashscore files of the ATP pipeline handoff, linked to Stage 0's match
table, so a leak-proof timeline can use exact days instead of tournament weeks.

Source: data/raw/public_dump/atp_pipeline_handoff/flashscore_{full,gql_stats,daily,data,bruteforce}/ (Hugging Face
dataset atlas-polybot/atp-pipeline-handoff at commit ea3d94d7, downloaded 25 Sep 2026; no licence, no dataset card).
What the files hold, and why player ids come from the head-to-head feeds: flashscore_parse.py.
Targets: data/studies/predictability_diagnostic/stage0_matches.parquet and stage0_match_players.parquet.

Method
    1. Parse (flashscore_parse.py). Every file is streamed; match pages (year, statistics and head-to-head files),
       daily-board rows and the entries of every page's head-to-head feed become one table keyed by Flashscore
       match id, from 2009-12-01 on: flashscore_records.parquet. Rows without a match id or start time (layer-3
       "recovered" rows, flashscore_data, flashscore_bruteforce) are counted, not linked. Doubles, juniors and
       exhibitions are kept in the table and left out of the link.
    2. Link, identity first (flashscore_names.py for the name keys). Candidates share both players' name keys
       (an unordered pair, so either side may be home), the same tour where Flashscore's gender is known, and a
       start date from 10 days before to 21 days after Stage 0's tournament date. A candidate must be confirmed:
       identical set scores (read for Stage 0's player A, or as written from the winner's side; a trailing 0-0
       set of a retirement ignored), or, where Flashscore gives no set scores, the same sets won and winner, or a
       walkover on both sides, or the same round. Candidates rank by that confirmation, then winner, round and
       country agreement, strict name keys before loose ones, days outside the round's expected dates and the
       distance from the round's usual day. The expected dates of each level x qualifying x round are learned from
       the candidates confirmed by identical scores that are their match's only candidate (0.5th to 99.5th
       percentile, a day either side). A candidate whose given names conflict with Stage 0's (two sisters,
       "Pliskova Ka." against Kristyna Pliskova) or whose country disagrees must fall inside those dates.
       Equal best candidates leave the match ambiguous, except when they share one start time (the same match
       under two Flashscore ids: the better source is kept, the others listed). Each Flashscore match takes at
       most one Stage 0 match (the better-ranked; the other tries its next candidate). A second pass links the
       rest on one identical player on the same side with identical set scores (two sets or more, or one with
       the round agreeing), inside the round's expected dates, the other player's first initial agreeing (a
       married or changed surname keeps the given name), unique both ways.
    3. Local dates (flashscore_tz.py). The event's country comes from Stage 4's hand-made table
       (stage4_event_country.csv: main tour and Challengers), else the ITF tournament id (its three-letter code),
       else Flashscore's own country field; its time zone from the country, or, where the country spans several
       zones, from the city or the US state / Canadian province code in the tournament name; a few one-venue
       events (Olympics, Laver Cup, the 2021-22 ATP Cup) by season. start_utc in that zone gives date_local
       (date_basis 'local'); without a zone (Davis Cup and other team ties, unknown cities, Stage 0 and Flashscore
       naming different countries) date_local is the UTC date (date_basis 'utc_date'). link_method ends with how
       the zone was found (country_zone, mainland_zone, city_zone, state_zone, territory_zone, event_zone, utc).
    Daily-board rows (6 May - 2 Jun 2026) have a board date but no start time and an unverified day boundary;
    their links go to flashscore_daily_board.parquet, not flashscore.parquet.

Writes data/studies/match_timing/links/:
    flashscore_records.parquet     the parsed, deduplicated Flashscore matches from 2009-12-01 on
    flashscore.parquet             one row per linked Stage 0 match: match_id, source, source_key, date_local,
                                   start_utc, date_basis, link_method, score_agrees, round_agrees
    flashscore_daily_board.parquet Stage 0 matches linked to a daily board only: match_id, source, source_key,
                                   board_date, link_method, score_agrees, round_agrees
    flashscore_ambiguous.parquet   the tied candidates of ambiguous Stage 0 matches, and duplicate Flashscore ids
    flashscore_unlinked.parquet    every Stage 0 match without a start-time link, with the reason
    flashscore_link_counts.csv     links and coverage by tour x level x qualifying x year
    flashscore_summary.json        counts, coverage, agreement with tennis-data.co.uk's match days, flags

Run: ./python.sh src/eda/match_timing/link_flashscore.py [--workers 4] [--work-dir DIR] [--reparse] [--rebuild-records]
The parse writes shards to --work-dir (default: <system temp>/flashscore_link_work), reused by later runs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.match_timing import flashscore_names as N  # noqa: E402
from src.eda.match_timing import flashscore_parse as P  # noqa: E402
from src.eda.match_timing import flashscore_tz as Z  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.predictability_diagnostic import stage4_country as SC  # noqa: E402

OUT = ROOT / "data" / "studies" / "match_timing" / "links"
RECORDS = OUT / "flashscore_records.parquet"
LINKS = OUT / "flashscore.parquet"
AMBIGUOUS = OUT / "flashscore_ambiguous.parquet"
UNLINKED = OUT / "flashscore_unlinked.parquet"
COUNTS = OUT / "flashscore_link_counts.csv"
SUMMARY = OUT / "flashscore_summary.json"
BOARD = OUT / "flashscore_daily_board.parquet"
BOARD_ONLY = "linked to a daily board only (a date, no start time)"
ZONE_TOKEN = {"country": "country_zone", "country (mainland)": "mainland_zone", "city": "city_zone",
              "city (state code)": "state_zone", "city (province code)": "province_zone",
              "city (outlying territory)": "territory_zone", "event venue (fixed)": "event_zone"}
ODDS = C.OUT / "stage1_odds.parquet"
WINDOW = (-10, 21)                 # Flashscore start date minus Stage 0's tournament date, in days
MAX_WORKERS = 4
FINISHED = ("finished", "retired", "walkover", "awarded")
TOUR_GENDER = {"atp": "men", "wta": "women"}
# the dates a round is expected on, from the tournament date (days): used to rank candidates, not to filter
EXPECTED_MAIN = {"GS": (-1, 14), "T1000": (-2, 13), "FIN": (-2, 7), "TEAM": (-3, 14)}
EXPECTED_MAIN_DEFAULT = (-2, 7)
EXPECTED_QUAL = (-9, 1)
# flags: a date this many days before the tournament date, or after it (the plausible end), by level
EARLY_MAIN, EARLY_QUAL = 1, 10
PLAUSIBLE_END = {"GS": 15, "T1000": 13, "FIN": 8, "TEAM": 14}
PLAUSIBLE_END_DEFAULT = 8
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records", date_format="iso", default_handler=str))


# ------------------------------------------------------------------------------------------------
# Step 1: the Flashscore table

def load_records(work: Path, workers: int, reparse: bool, rebuild: bool) -> tuple[pd.DataFrame, list, dict]:
    results = P.load_or_parse(work, workers, reparse, log)
    index, stats_path = work / "parse_results.json", work / "records_stats.json"
    fresh = (RECORDS.exists() and stats_path.exists() and not (rebuild or reparse)
             and RECORDS.stat().st_mtime > index.stat().st_mtime)
    if fresh:
        log(f"reusing {RECORDS.name}")
        return pd.read_parquet(RECORDS), results, json.loads(stats_path.read_text(encoding="utf-8"))
    rec, stats = P.build_records(results, log)
    OUT.mkdir(parents=True, exist_ok=True)
    rec.to_parquet(RECORDS, index=False)
    stats_path.write_text(json.dumps(stats, indent=1, default=str), encoding="utf-8")
    log(f"wrote {RECORDS.name}: {len(rec):,} Flashscore matches from {P.SCOPE_FROM}")
    return rec, results, stats


def noid_coverage(results: list, f: pd.DataFrame) -> dict:
    """Rows of flashscore_data and flashscore_bruteforce (no match id, no start time; a date as displayed) from
    SCOPE_FROM on: how many name a match that a timestamped Flashscore row also holds (both players' surname and
    initial, dates at most two days apart), so leaving them out loses little."""
    noid = P.read_shards([r["noid_shard"] for r in results if r.get("noid_shard")])
    if noid.empty:
        return {"rows": 0}
    noid = noid[noid["home_name"].fillna("").ne("") & noid["away_name"].fillna("").ne("")
                & ~(noid["home_name"] + noid["away_name"]).str.contains("/", regex=False)].drop_duplicates(
        ["match_date", "home_name", "away_name"])
    noid["day"] = pd.to_datetime(noid["match_date"], format="%Y%m%d", errors="coerce")

    def key(name):
        sur, ini = N.fs_parts(name)
        return " ".join(sur) + " " + ini

    def pair(a, b):
        return pd.Series(np.where(a < b, a + "|" + b, b + "|" + a), index=a.index)

    noid["pair"] = pair(noid["home_name"].map(key), noid["away_name"].map(key))
    ft = f[f["has_start"]]
    right = pd.DataFrame({"pair": pair(ft["home_name"].map(key), ft["away_name"].map(key)).to_numpy(),
                          "fday": ft["fs_day"].to_numpy()})
    j = noid[["pair", "day"]].reset_index().merge(right, on="pair")
    near = j[(j["fday"] - j["day"]).dt.days.abs() <= 2]["index"].unique()
    found = noid.index.isin(near)
    by = noid.assign(found=found, year=noid["day"].dt.year).groupby(["kind", "year"])["found"].agg(["size", "sum"])
    return {"rows_from_scope_start_singles_distinct": int(len(noid)), "also_in_timestamped_rows": int(found.sum()),
            "share_pct": round(100 * float(found.mean()), 2),
            "by_kind_year": records(by.rename(columns={"size": "rows", "sum": "also_timestamped"}).reset_index())}


def parse_summary(results: list) -> dict:
    by_kind = {}
    for r in results:
        k = by_kind.setdefault(r["kind"], {"files": 0, "bytes_on_disk": 0})
        k["files"] += 1
        k["bytes_on_disk"] += r["bytes_on_disk"]
        for key, v in r["counts"].items():
            if key != "distinct_feed_ids":
                k[key] = k.get(key, 0) + v
        k["pages_in_scope"] = k.get("pages_in_scope", 0) + r["pages_in_scope"]
    rounds, statuses = {}, {}
    for r in results:
        for k, v in r["rounds"].items():
            rounds[k] = rounds.get(k, 0) + v
        for k, v in r["statuses"].items():
            statuses[f"{r['kind']}|{k}"] = statuses.get(f"{r['kind']}|{k}", 0) + v
    total = {"files": len(results), "records": sum(r["counts"].get("records", 0) for r in results)}
    return {"total": total, "by_kind": by_kind, "round_labels_on_pages": dict(sorted(rounds.items(), key=lambda x: -x[1])),
            "status_codes_by_kind": statuses}


def set_tuple(text_: str | None) -> tuple:
    if not isinstance(text_, str) or not text_:
        return ()
    return trim(tuple((int(a), int(b)) for a, b in re.findall(r"(\d+)-(\d+)", text_)))


def trim(sets: tuple) -> tuple:
    """Set scores without trailing 0-0 sets: a retirement at the start of a set is written "6-2 0-0" by one source
    and "6-2" by the other."""
    sets = tuple(sets)
    while sets and tuple(sets[-1][:2]) == (0, 0):
        sets = sets[:-1]
    return sets


def flashscore_side(rec: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The Flashscore matches the link may use: singles, not juniors, finished (retired, walkover, awarded),
    with a start time or a daily-board date from SCOPE_FROM on."""
    day = rec["start_utc"].dt.tz_convert(None).dt.normalize()
    day = day.fillna(rec["board_date"])
    status_ok = rec["status"].isin(FINISHED) | (rec["origin"].eq("daily_board") & rec["status"].isna())
    keep = (~rec["is_doubles"] & ~rec["is_junior"] & ~rec["is_exhibition"] & status_ok & day.notna()
            & (day >= pd.Timestamp(P.SCOPE_FROM)) & rec["home_name"].fillna("").ne("") & rec["away_name"].fillna("").ne(""))
    out = {"records": int(len(rec)), "doubles": int(rec["is_doubles"].sum()), "juniors": int(rec["is_junior"].sum()),
           "exhibitions": int(rec["is_exhibition"].sum()),
           "not_finished": int((~status_ok).sum()), "no_date": int(day.isna().sum()),
           "in_scope": int(keep.sum())}
    f = rec[keep].copy()
    f["fs_day"] = day[keep]
    f["has_start"] = f["start_utc"].notna()
    f["sets_home"] = f["set_scores"].map(set_tuple)
    f["pref"] = f["origin"].map({"year_file": 0, "stats_file": 1, "h2h_page": 2, "feed_entry": 3, "daily_board": 4})
    f["ioc"] = f["country"].map(Z.ioc_of_fs_country)
    f = f.reset_index(drop=True)
    out["in_scope_by_origin"] = f["origin"].value_counts().to_dict()
    out["in_scope_by_gender"] = f["gender"].fillna("unknown").value_counts().to_dict()
    out["in_scope_by_category_guess"] = f["category_guess"].fillna("other").value_counts().to_dict()
    out["in_scope_by_year"] = f["fs_day"].dt.year.value_counts().sort_index().to_dict()
    return f, out


# ------------------------------------------------------------------------------------------------
# Step 2: linking

def stage0_side() -> pd.DataFrame:
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
                        "tournament_name", "tournament_date", "status", "score", "player_a_id", "player_b_id", "a_won"])
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "side", "player_name"])
    names = mp.pivot(index="match_id", columns="side", values="player_name")
    m["name_a"] = m["match_id"].map(names["A"]).fillna("")
    m["name_b"] = m["match_id"].map(names["B"]).fillna("")
    winner_sets = m["score"].fillna("").map(lambda s: trim(tuple((a, b) for a, b, _br in B.set_scores(s))))
    a_won = m["a_won"].to_numpy(dtype=bool)
    m["sets_a"] = [w if aw else tuple((b, a) for a, b in w) for w, aw in zip(winner_sets, a_won)]
    m["sets_w"] = winner_sets

    def won_counts(s: str) -> tuple[int, int]:
        toks = B.tokens_of(s)[0]
        c = B.score_counts(s, B.short_like(toks))
        return c[0], c[1]

    counts = {s: won_counts(s) for s in m["score"].fillna("").unique()}
    wl = m["score"].fillna("").map(counts)
    sw, sl = np.array([x[0] for x in wl]), np.array([x[1] for x in wl])
    m["setwon_a"], m["setwon_b"] = np.where(a_won, sw, sl), np.where(a_won, sl, sw)
    lo, hi = expected_interval(m)
    m["exp_lo"], m["exp_hi"], m["exp_mid"] = lo, hi, (lo + hi) / 2
    m["ioc"], m["ioc_basis"] = event_country(m)
    return m


def event_country(m: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Stage 0's event country and its basis: Stage 4's hand-made table (main tour and Challengers), else the ITF
    tournament id. Looked up once per event (tour, season, tournament id and name)."""
    keys = ["tour", "year", "tournament_id", "tournament_name"]
    ev = m[keys].drop_duplicates().reset_index(drop=True)
    table = SC.event_country(ev)
    ev["ioc"] = pd.Series(table.astype(object).where(table.notna(), None), dtype=object)
    ev["basis"] = np.where(ev["ioc"].notna(), "stage4_event_country", None)
    itf = ev["tournament_id"].map(Z.itf_country)
    use = ev["ioc"].isna() & itf.notna()
    ev.loc[use, "ioc"], ev.loc[use, "basis"] = itf[use], "itf_tournament_id"
    j = m[keys].merge(ev, on=keys, how="left")
    return (pd.Series(j["ioc"].to_numpy(dtype=object), index=m.index),
            pd.Series(j["basis"].to_numpy(dtype=object), index=m.index))


def expected_interval(m: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    lo = np.full(len(m), EXPECTED_MAIN_DEFAULT[0])
    hi = np.full(len(m), EXPECTED_MAIN_DEFAULT[1])
    for level, (a, b) in EXPECTED_MAIN.items():
        hit = m["level"].eq(level).to_numpy()
        lo[hit], hi[hit] = a, b
    q = m["qualifying"].to_numpy(dtype=bool)
    lo[q], hi[q] = EXPECTED_QUAL
    return lo, hi


class Vocab:
    """Name key -> integer id, shared by both sides."""

    def __init__(self):
        self.ids: dict[str, int] = {}

    def of(self, keys) -> list[int]:
        out = []
        for k in keys:
            if k not in self.ids:
                self.ids[k] = len(self.ids)
            out.append(self.ids[k])
        return out


def pairs_frame(idx: np.ndarray, keys_a: list, keys_b: list, extra: dict | None = None) -> pd.DataFrame:
    """Cross product of the two players' key ids per row: pair id (unordered), whether the first player's key is
    the lower id (orientation) and whether the two keys are equal (orientation unknown)."""
    ia, ib, ka, kb, ex = [], [], [], [], {k: [] for k in (extra or {})}
    for j, (a_list, b_list) in enumerate(zip(keys_a, keys_b)):
        for a in a_list:
            for b in b_list:
                ia.append(idx[j])
                ka.append(a)
                kb.append(b)
                for k, v in (extra or {}).items():
                    ex[k].append(v[j][(a, b)] if isinstance(v[j], dict) else v[j])
    ka_, kb_ = np.asarray(ka, dtype=np.int64), np.asarray(kb, dtype=np.int64)
    out = pd.DataFrame({"row": np.asarray(ia, dtype=np.int64),
                        "pair": np.minimum(ka_, kb_) * (1 << 32) + np.maximum(ka_, kb_),
                        "first_lo": ka_ < kb_, "eq": ka_ == kb_})
    for k, v in ex.items():
        out[k] = v
    return out


def stage0_pairs(m: pd.DataFrame, vocab: Vocab) -> tuple[pd.DataFrame, dict]:
    names = pd.unique(pd.concat([m["name_a"], m["name_b"]]))
    ids = {n: vocab.of(sorted(N.stage0_keys(n))) for n in names}
    ka = [ids[n] for n in m["name_a"]]
    kb = [ids[n] for n in m["name_b"]]
    p = pairs_frame(m.index.to_numpy(), ka, kb).rename(columns={"row": "li", "first_lo": "a_lo", "eq": "a_eq"})
    return p.drop_duplicates(["li", "pair"]), ids


def flashscore_pairs(f: pd.DataFrame, vocab: Vocab) -> tuple[pd.DataFrame, list, list]:
    strict_h = [vocab.of(sorted(N.fs_strict_keys(n, s or ""))) for n, s in zip(f["home_name"], f["home_slug"].fillna(""))]
    strict_a = [vocab.of(sorted(N.fs_strict_keys(n, s or ""))) for n, s in zip(f["away_name"], f["away_slug"].fillna(""))]
    loose_h = [vocab.of(sorted(N.fs_loose_keys(n))) for n in f["home_name"]]
    loose_a = [vocab.of(sorted(N.fs_loose_keys(n))) for n in f["away_name"]]
    all_h = [s + [k for k in lz if k not in s] for s, lz in zip(strict_h, loose_h)]
    all_a = [s + [k for k in lz if k not in s] for s, lz in zip(strict_a, loose_a)]
    strict_flags = [{(a, b): (a in set(sh) and b in set(sa)) for a in ah for b in aa}
                    for sh, sa, ah, aa in zip(strict_h, strict_a, all_h, all_a)]
    p = pairs_frame(f.index.to_numpy(), all_h, all_a, extra={"strict": strict_flags})
    p = p.rename(columns={"row": "ri", "first_lo": "h_lo", "eq": "h_eq"})
    p = p.sort_values("strict", ascending=False).drop_duplicates(["ri", "pair"])
    return p, strict_h, strict_a


def candidates(m: pd.DataFrame, f: pd.DataFrame, sp: pd.DataFrame, fp: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Every (Stage 0 match, Flashscore match) sharing a name-key pair, with the date gap; and per Stage 0 match
    whether any pair exists at all, and inside the window."""
    c = sp.merge(fp, on="pair")
    tdate = m["tournament_date"].to_numpy(dtype="datetime64[D]")
    fday = f["fs_day"].to_numpy(dtype="datetime64[D]")
    c["gap"] = (fday[c["ri"].to_numpy()] - tdate[c["li"].to_numpy()]).astype("int64")
    stats = {"pair_rows": int(len(c)), "stage0_with_any_pair": int(c["li"].nunique())}
    any_pair = set(c["li"].unique())
    c = c[(c["gap"] >= WINDOW[0]) & (c["gap"] <= WINDOW[1])]
    stats["stage0_with_pair_in_window"] = int(c["li"].nunique())
    unknown = c["a_eq"] | c["h_eq"]
    same = ~unknown & (c["a_lo"] == c["h_lo"])
    swap = ~unknown & (c["a_lo"] != c["h_lo"])
    c = c.assign(same=same, swap=swap)
    g = c.groupby(["li", "ri"], sort=False).agg(gap=("gap", "first"), same=("same", "any"), swap=("swap", "any"),
                                                 strict=("strict", "any")).reset_index()
    return g, {**stats, "_any_pair": any_pair}


def a_side_options(g: pd.DataFrame) -> pd.DataFrame:
    """One row per candidate and possible orientation: a_home True (Stage 0's A is Flashscore's home), False, or
    both rows when the keys cannot tell."""
    both = ~g["same"] & ~g["swap"] | (g["same"] & g["swap"])
    rows = [g[g["same"] & ~g["swap"]].assign(a_home=True), g[g["swap"] & ~g["same"]].assign(a_home=False),
            g[both].assign(a_home=True), g[both].assign(a_home=False)]
    return pd.concat(rows, ignore_index=True)


def score_candidates(g: pd.DataFrame, m: pd.DataFrame, f: pd.DataFrame) -> pd.DataFrame:
    """Confirmation tier and agreement flags per candidate orientation; the best orientation per candidate."""
    c = a_side_options(g)
    li, ri = c["li"].to_numpy(), c["ri"].to_numpy()
    a_home = c["a_home"].to_numpy(dtype=bool)
    tour = m["tour"].to_numpy()[li]
    fg = f["gender"].to_numpy(dtype=object)[ri]
    c["gender_ok"] = [(g_ is None or (isinstance(g_, float) and np.isnan(g_)) or TOUR_GENDER[t] == g_)
                      for t, g_ in zip(tour, fg)]
    win = f["winner"].to_numpy(dtype=object)[ri]
    a_won = m["a_won"].to_numpy(dtype=bool)[li]
    fs_a_won = np.where(pd.isna(win), None, np.where(a_home, win == "home", win == "away"))
    c["winner_agrees"] = pd.array([None if w is None else bool(w == aw) for w, aw in zip(fs_a_won, a_won)],
                                  dtype="boolean")
    sets_home = f["sets_home"].to_numpy(dtype=object)[ri]
    sets_a0 = m["sets_a"].to_numpy(dtype=object)[li]
    sets_w0 = m["sets_w"].to_numpy(dtype=object)[li]
    sc, sc_w = [], []
    for sh, ah, s0a, s0w in zip(sets_home, a_home, sets_a0, sets_w0):
        if not sh or not s0a:
            sc.append(None)
            sc_w.append(False)
            continue
        fa = sh if ah else tuple((b, a) for a, b in sh)
        ok = fa == s0a
        sc.append(bool(ok or sh == s0w))
        sc_w.append(bool(not ok and sh == s0w))
    c["score_agrees"] = pd.array(sc, dtype="boolean")
    c["score_from_winner_side"] = sc_w
    hs, as_ = f["home_sets"].to_numpy(dtype="float64", na_value=np.nan)[ri], f["away_sets"].to_numpy(dtype="float64", na_value=np.nan)[ri]
    fa_sets = np.where(a_home, hs, as_)
    fb_sets = np.where(a_home, as_, hs)
    count_ok = (fa_sets == m["setwon_a"].to_numpy()[li]) & (fb_sets == m["setwon_b"].to_numpy()[li])
    c["count_agrees"] = count_ok & ~np.isnan(fa_sets)
    s0_wo = m["status"].to_numpy(dtype=object)[li] == "walkover"
    fs_wo = f["status"].to_numpy(dtype=object)[ri] == "walkover"
    c["walkover_both"] = s0_wo & fs_wo
    c["round_agrees"] = rounds_agree(f["round"].to_numpy(dtype=object)[ri], m["round"].to_numpy(dtype=object)[li])
    wa = c["winner_agrees"].fillna(True).to_numpy(dtype=bool)
    tier = np.where(c["score_agrees"].fillna(False).to_numpy(dtype=bool), 3,
                    np.where(c["score_agrees"].isna().to_numpy() & (c["count_agrees"].to_numpy() | c["walkover_both"].to_numpy())
                             & wa & c["winner_agrees"].notna().to_numpy(), 2,
                             np.where(c["round_agrees"].fillna(False).to_numpy(dtype=bool) & wa, 1, 0)))
    tier = np.where(c["strict"].to_numpy(dtype=bool) | (tier == 3), tier, 0)   # loose name keys need identical set scores
    c["tier_raw"] = np.where(c["gender_ok"].to_numpy(dtype=bool), tier, 0)
    c["tier"] = c["tier_raw"]
    c["wa"] = c["winner_agrees"].map({True: 2, False: 0}).fillna(1).astype("int8")
    c["ra"] = c["round_agrees"].map({True: 2, False: 0}).fillna(1).astype("int8")
    names_a, names_b = m["name_a"].to_numpy()[li], m["name_b"].to_numpy()[li]
    hn, an = f["home_name"].to_numpy(dtype=object)[ri], f["away_name"].to_numpy(dtype=object)[ri]
    hs = f["home_slug"].fillna("").to_numpy(dtype=object)[ri]
    as_ = f["away_slug"].fillna("").to_numpy(dtype=object)[ri]
    conflict = []
    for na, nb, h, a, sh, sa, ah in zip(names_a, names_b, hn, an, hs, as_, a_home):
        fa, sfa, fb, sfb = (h, sh, a, sa) if ah else (a, sa, h, sh)
        conflict.append(bool(N.given_names_conflict(fa, sfa, na)) or bool(N.given_names_conflict(fb, sfb, nb)))
    c["name_conflict"] = conflict
    same = [Z.same_country(x, y) for x, y in zip(m["ioc"].to_numpy(dtype=object)[li], f["ioc"].to_numpy(dtype=object)[ri])]
    c["ca"] = np.array([1 if v is None else 2 if v else 0 for v in same], dtype="int8")
    c["pref"] = f["pref"].to_numpy()[ri]
    st = f["start_utc"].to_numpy(dtype="datetime64[s]")[ri].astype("int64")
    st = np.where(f["has_start"].to_numpy()[ri], st, f["fs_day"].to_numpy(dtype="datetime64[s]")[ri].astype("int64"))
    c["start_key"] = st
    c = place_in_window(c, m)
    c = c.sort_values(["li", "ri"] + RANK, ascending=[True, True] + RANK_ASC, kind="mergesort")
    return c.drop_duplicates(["li", "ri"]).reset_index(drop=True)


def rounds_agree(fs_round: np.ndarray, s0_round: np.ndarray) -> pd.array:
    """Flashscore's round against Stage 0's; missing where it cannot be told. Flashscore's match pages label a
    qualifying match by its place in the qualifying bracket ("Semi-finals" for Q1 of a four-player bracket, "Final"
    for its last round) and never say "qualification", and label Tour Finals group matches oddly, so Stage 0's
    qualifying and round-robin matches are not compared."""
    out = []
    for r, s in zip(fs_round, s0_round):
        if not isinstance(r, str) or not isinstance(s, str) or (s.startswith("Q") and not r.startswith("Q")) or s == "RR":
            out.append(None)
        else:
            out.append(r == s)
    return pd.array(out, dtype="boolean")


RANK = ["tier", "wa", "ra", "ca", "strict", "outside", "dev"]
RANK_ASC = [False, False, False, False, False, True, True]


def place_in_window(c: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Days outside the round's expected dates (outside) and distance from its usual day (dev), from Stage 0's
    exp_lo / exp_hi / exp_mid. A candidate whose given names conflict, or whose country disagrees, must fall
    inside the expected dates (so a sibling's exhibition match nine days early cannot take a Shenzhen match)."""
    li = c["li"].to_numpy()
    lo, hi, mid = m["exp_lo"].to_numpy()[li], m["exp_hi"].to_numpy()[li], m["exp_mid"].to_numpy()[li]
    gap = c["gap"].to_numpy()
    c["outside"] = np.maximum(lo - gap, 0) + np.maximum(gap - hi, 0)
    c["dev"] = np.abs(gap - mid)
    doubtful = (c["name_conflict"].to_numpy(dtype=bool) | (c["ca"].to_numpy() == 0)) & (c["outside"].to_numpy() > 0)
    c["tier"] = np.where(doubtful, 0, c["tier_raw"] if "tier_raw" in c else c["tier"])
    return c


def learn_windows(c: pd.DataFrame, m: pd.DataFrame, min_n: int = 40) -> dict:
    """Each (level, qualifying, round)'s expected dates, learned from candidates confirmed by identical set scores
    that are the only candidate of their Stage 0 match: 0.5th to 99.5th percentile of the days from the tournament
    date, widened by a day; the median is the usual day. Groups with fewer than ``min_n`` such links keep the
    level's default interval."""
    u = c[(c["tier"] == 3) & (c.groupby("li")["ri"].transform("nunique") == 1)].drop_duplicates("li")
    key = m["level"] + "|" + m["qualifying"].map({True: "Q", False: "M"}) + "|" + m["round"].fillna("")
    u = u.assign(key=key.to_numpy()[u["li"].to_numpy()])
    q = u.groupby("key")["gap"].quantile([0.005, 0.5, 0.995]).unstack()
    n = u.groupby("key").size()
    q = q[n.reindex(q.index) >= min_n]
    k = key.to_numpy()
    lo = pd.Series(k).map(np.floor(q[0.005]) - 1).to_numpy()
    hi = pd.Series(k).map(np.ceil(q[0.995]) + 1).to_numpy()
    mid = pd.Series(k).map(q[0.5]).to_numpy()
    use = ~np.isnan(lo)
    m.loc[use, "exp_lo"] = lo[use]
    m.loc[use, "exp_hi"] = hi[use]
    m.loc[use, "exp_mid"] = mid[use]
    return {"groups_learned": int(len(q)), "stage0_matches_with_learned_window": int(use.sum()),
            "windows": {g: {"lo": float(np.floor(r[0.005]) - 1), "median": float(r[0.5]),
                            "hi": float(np.ceil(r[0.995]) + 1), "links": int(n[g])} for g, r in q.iterrows()}}


def choose(c: pd.DataFrame, max_rounds: int = 4) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, set]:
    """One Flashscore match per Stage 0 match and vice versa, from confirmed candidates (tier >= 1).

    Returns kept links, tied candidates of ambiguous matches, duplicate-id candidates (tied, same start: the page
    kept), and the Stage 0 matches whose every candidate went to better-ranked matches."""
    c = c[c["tier"] >= 1]
    kept_all, amb_all, dup_all = [], [], []
    taken: set = set()
    lost_all: set = set()
    settled: set = set()
    todo = c
    for _ in range(max_rounds):
        todo = todo[~todo["ri"].isin(taken)]
        if todo.empty:
            break
        s = todo.sort_values(["li"] + RANK + ["pref", "ri"], ascending=[True] + RANK_ASC + [True, True], kind="mergesort")
        top = s.drop_duplicates("li")
        tied = s.merge(top[["li"] + RANK], on=["li"] + RANK)
        ntie = tied.groupby("li")["ri"].nunique()
        multi = ntie.index[ntie > 1]
        same_start = tied[tied["li"].isin(multi)].groupby("li")["start_key"].nunique()
        dup_li = same_start.index[same_start == 1]
        amb_li = multi.difference(dup_li)
        amb_all.append(tied[tied["li"].isin(amb_li)])
        dup_all.append(tied[tied["li"].isin(dup_li)].merge(top[["li", "ri"]].rename(columns={"ri": "kept_ri"}), on="li"))
        top = top[~top["li"].isin(amb_li)]
        top = top.sort_values(["ri"] + RANK + ["li"], ascending=[True] + RANK_ASC + [True], kind="mergesort")
        kept = top.drop_duplicates("ri")
        kept_all.append(kept)
        taken |= set(kept["ri"])
        lost = set(top.loc[~top.index.isin(kept.index), "li"])
        lost_all |= lost
        settled |= set(kept["li"]) | set(amb_li)
        todo = todo[todo["li"].isin(lost) & ~todo["li"].isin(settled)]
    cat = lambda xs: pd.concat(xs, ignore_index=True) if xs else pd.DataFrame()  # noqa: E731
    return cat(kept_all), cat(amb_all), cat(dup_all), lost_all - settled


def anchor_pass(m: pd.DataFrame, f: pd.DataFrame, free_li: np.ndarray, free_ri: np.ndarray,
                s0_ids: dict, fs_h: list, fs_a: list) -> tuple[pd.DataFrame, dict]:
    """One identical player key on the same side (winner with winner, loser with loser), identical set scores read
    from the winner's side (two sets or more, or one set with the round agreeing), same tour where known, inside
    the round's expected dates, the other player's first initial agreeing (a married or changed surname keeps the
    given name), no conflicting given names for the anchored player and no disagreeing country; unique both ways."""
    mm = m.loc[free_li]
    mm = mm[mm["sets_w"].map(len) > 0]
    s0_w = np.where(mm["a_won"], mm["name_a"], mm["name_b"])
    s0_l = np.where(mm["a_won"], mm["name_b"], mm["name_a"])
    score0 = mm["sets_w"].map(lambda s: " ".join(f"{a}-{b}" for a, b in s)).to_numpy()
    rows = []
    for role, names in (("w", s0_w), ("l", s0_l)):
        for li, n, sc in zip(mm.index, names, score0):
            for k in s0_ids[n]:
                rows.append((li, role, k, sc))
    left = pd.DataFrame(rows, columns=["li", "role", "key", "score"])
    ff = f.loc[free_ri]
    ff = ff[ff["winner"].isin(["home", "away"]) & (ff["sets_home"].map(len) > 0)]
    rows = []
    for ri, w, sh in zip(ff.index, ff["winner"], ff["sets_home"]):
        hw = w == "home"
        sw = sh if hw else tuple((b, a) for a, b in sh)
        sc = " ".join(f"{a}-{b}" for a, b in sw)
        for k in fs_h[ri]:
            rows.append((ri, "w" if hw else "l", k, sc))
        for k in fs_a[ri]:
            rows.append((ri, "l" if hw else "w", k, sc))
    right = pd.DataFrame(rows, columns=["ri", "role", "key", "score"])
    c = left.merge(right, on=["role", "key", "score"]).drop_duplicates(["li", "ri"])
    if c.empty:
        return c.assign(gap=pd.Series(dtype="int64")), {}
    tdate = m["tournament_date"].to_numpy(dtype="datetime64[D]")
    fday = f["fs_day"].to_numpy(dtype="datetime64[D]")
    c["gap"] = (fday[c["ri"].to_numpy()] - tdate[c["li"].to_numpy()]).astype("int64")
    c = c[(c["gap"] >= WINDOW[0]) & (c["gap"] <= WINDOW[1])].copy()
    tour = m["tour"].to_numpy()[c["li"].to_numpy()]
    fg = f["gender"].to_numpy(dtype=object)[c["ri"].to_numpy()]
    c = c[[g_ is None or (isinstance(g_, float) and np.isnan(g_)) or TOUR_GENDER[t] == g_ for t, g_ in zip(tour, fg)]]
    nsets = c["score"].str.count("-")
    c["round_agrees"] = rounds_agree(f["round"].to_numpy(dtype=object)[c["ri"].to_numpy()],
                                     m["round"].to_numpy(dtype=object)[c["li"].to_numpy()])
    stats = {"candidates_with_identical_scores_in_the_window": int(len(c))}
    c = c[((nsets >= 2) | c["round_agrees"].fillna(False).to_numpy(dtype=bool)) & c["round_agrees"].fillna(True).to_numpy(dtype=bool)]
    # inside the round's expected dates, the other player's first initial agrees, the anchored player's given
    # names do not conflict, and the countries do not disagree
    li, ri = c["li"].to_numpy(), c["ri"].to_numpy()
    gap = c["gap"].to_numpy()
    inside = (gap >= m["exp_lo"].to_numpy()[li]) & (gap <= m["exp_hi"].to_numpy()[li])
    a_won = m["a_won"].to_numpy(dtype=bool)[li]
    s0w = np.where(a_won, m["name_a"].to_numpy()[li], m["name_b"].to_numpy()[li])
    s0l = np.where(a_won, m["name_b"].to_numpy()[li], m["name_a"].to_numpy()[li])
    hw = f["winner"].to_numpy(dtype=object)[ri] == "home"
    fw = np.where(hw, f["home_name"].to_numpy(dtype=object)[ri], f["away_name"].to_numpy(dtype=object)[ri])
    fl = np.where(hw, f["away_name"].to_numpy(dtype=object)[ri], f["home_name"].to_numpy(dtype=object)[ri])
    sw = np.where(hw, f["home_slug"].fillna("").to_numpy(dtype=object)[ri], f["away_slug"].fillna("").to_numpy(dtype=object)[ri])
    sl = np.where(hw, f["away_slug"].fillna("").to_numpy(dtype=object)[ri], f["home_slug"].fillna("").to_numpy(dtype=object)[ri])
    role = c["role"].to_numpy()
    ok_names = []
    for r_, a1, b1, a2, b2, s1, s2 in zip(role, s0w, fw, s0l, fl, sw, sl):
        if r_ == "w":     # the winners share a key: the losers must share an initial
            ok_names.append(N.initial_agrees(b2, a2) and not N.given_names_conflict(b1, s1, a1))
        else:
            ok_names.append(N.initial_agrees(b1, a1) and not N.given_names_conflict(b2, s2, a2))
    same = np.array([Z.same_country(x, y) is not False for x, y in
                     zip(m["ioc"].to_numpy(dtype=object)[li], f["ioc"].to_numpy(dtype=object)[ri])])
    ok = inside & np.array(ok_names, dtype=bool) & same
    stats.update({"outside_the_expected_dates": int((~inside).sum()),
                  "other_player_initial_or_given_names_disagree": int((inside & ~np.array(ok_names, dtype=bool)).sum()),
                  "countries_disagree": int((inside & np.array(ok_names, dtype=bool) & ~same).sum())})
    c = c[ok]
    one = c.groupby("li")["ri"].transform("nunique").eq(1) & c.groupby("ri")["li"].transform("nunique").eq(1)
    stats["not_unique"] = int((~one).sum())
    return c[one].reset_index(drop=True), stats


def link_all(m: pd.DataFrame, f: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, dict]:
    vocab = Vocab()
    sp, s0_ids = stage0_pairs(m, vocab)
    log(f"Stage 0 key pairs: {len(sp):,} rows")
    fp, fs_h, fs_a = flashscore_pairs(f, vocab)
    log(f"Flashscore key pairs: {len(fp):,} rows; vocabulary {len(vocab.ids):,} keys")
    g, cstats = candidates(m, f, sp, fp)
    any_pair = cstats.pop("_any_pair")
    del sp, fp
    log(f"candidates in the window: {len(g):,} for {g['li'].nunique():,} Stage 0 matches")
    c = score_candidates(g, m, f)
    windows = learn_windows(c, m)
    c = place_in_window(c, m)
    log(f"expected dates learned for {windows['groups_learned']} level x qualifying x round groups")
    kept, amb, dup, lost = choose(c)
    log(f"pass 1 (name pair): {len(kept):,} linked, {amb['li'].nunique() if len(amb) else 0:,} ambiguous, "
        f"{len(lost):,} lost to better-ranked matches")
    kept = kept.assign(pass_="name_pair")
    amb_li = set(amb["li"]) if len(amb) else set()
    free_li = m.index[~m.index.isin(list(set(kept["li"]) | amb_li))].to_numpy()
    free_ri = f.index[~f.index.isin(list(set(kept["ri"])))].to_numpy()
    a, anchor_stats = anchor_pass(m, f, free_li, free_ri, s0_ids, fs_h, fs_a)
    log(f"pass 2 (one-player anchor): {len(a):,} linked")
    # reason per Stage 0 match (later lines override earlier ones)
    reason = pd.Series("no Flashscore match with either player in the window", index=m.index, dtype=object)
    in_window = set(g["li"])
    confirmed = set(c.loc[c["tier"] >= 1, "li"])
    linked_li = set(kept["li"]) | set(a["li"])
    no_pair = m.index[~m.index.isin(list(any_pair | linked_li | amb_li))].to_numpy()
    one_player = one_player_in_window(m, f, s0_ids, fs_h, fs_a, no_pair)
    reason[m.index.isin(list(one_player))] = "one player in Flashscore in the window, not the pair"
    reason[m.index.isin(list(any_pair))] = "player pair in Flashscore, but not in the date window"
    reason[m.index.isin(list(in_window))] = "pair in the window, but no confirmation (set scores, sets won, round)"
    gender_bad = set(c.loc[~c["gender_ok"], "li"]) - confirmed
    reason[m.index.isin(list(gender_bad))] = "pair in the window, but Flashscore's gender disagrees"
    reason[m.index.isin(list(lost))] = "its Flashscore match was taken by a better-ranked Stage 0 match"
    reason[m.index.isin(list(amb_li))] = "ambiguous: equally good Flashscore matches with different start times"
    reason[m.index.isin(list(linked_li))] = "linked"
    links = pd.concat([kept[["li", "ri", "gap", "tier", "score_agrees", "round_agrees", "winner_agrees", "strict",
                             "score_from_winner_side", "pass_"]],
                       a.assign(pass_="one_player_anchor", tier=3, score_agrees=True, winner_agrees=True, strict=True,
                                score_from_winner_side=False)[["li", "ri", "gap", "tier", "score_agrees", "round_agrees",
                                                               "winner_agrees", "strict", "score_from_winner_side", "pass_"]]],
                      ignore_index=True)
    stats = {**cstats, "candidates_in_window": int(len(g)), "candidate_orientations_scored": int(len(c)),
             "confirmed_candidates": int((c["tier"] >= 1).sum()),
             "pass_name_pair": {"linked": int(len(kept)), "ambiguous_matches": int(len(amb_li)),
                                "duplicate_fs_ids_resolved": int(dup["li"].nunique()) if len(dup) else 0,
                                "lost_to_better_ranked": int(len(lost)),
                                "by_tier": kept["tier"].value_counts().sort_index().to_dict(),
                                "loose_name_keys": int((~kept["strict"].astype(bool)).sum()),
                                "score_read_from_winner_side": int(kept["score_from_winner_side"].astype(bool).sum())},
             "pass_one_player_anchor": {"linked": int(len(a)), **anchor_stats},
             "candidates_set_aside_for_conflicting_names_or_country_outside_the_expected_dates":
                 int(((c["tier"] == 0) & (c["tier_raw"] > 0)).sum()),
             "expected_dates": windows}
    amb_out = amb.assign(kind="ambiguous") if len(amb) else pd.DataFrame()
    dup_out = dup.assign(kind="duplicate_fs_id_same_start") if len(dup) else pd.DataFrame()
    return links, amb_out, dup_out, reason, stats


def one_player_in_window(m, f, s0_ids, fs_h, fs_a, which: np.ndarray) -> set:
    """Of the Stage 0 matches ``which``, those with at least one player's name key on a Flashscore match near the
    window (weekly buckets from two weeks before to three after the tournament week)."""
    epoch = np.datetime64("1970-01-05", "D")                                  # a Monday
    fweek = ((f["fs_day"].to_numpy(dtype="datetime64[D]") - epoch).astype("int64")) // 7
    rows_k, rows_w = [], []
    for ri in range(len(f)):
        for k in fs_h[ri] + fs_a[ri]:
            rows_k.append(k)
            rows_w.append(fweek[ri])
    present = set(zip(rows_k, rows_w))
    mm = m.loc[which]
    tweek = ((mm["tournament_date"].to_numpy(dtype="datetime64[D]") - epoch).astype("int64")) // 7
    out = set()
    for li, na, nb, w in zip(mm.index, mm["name_a"], mm["name_b"], tweek):
        keys = set(s0_ids[na]) | set(s0_ids[nb])
        if any((k, w + d) in present for k in keys for d in (-2, -1, 0, 1, 2, 3)):
            out.add(li)
    return out


# ------------------------------------------------------------------------------------------------
# Step 3: local dates

def local_dates(lk: pd.DataFrame, m: pd.DataFrame, f: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Country (IOC) and time zone per linked match, and the local calendar date of its start."""
    mm = m.loc[lk["li"].to_numpy()].reset_index(drop=True)
    ff = f.loc[lk["ri"].to_numpy()].reset_index(drop=True)
    fsc = ff["ioc"]
    country = pd.Series(mm["ioc"].to_numpy(dtype=object), dtype=object)
    basis = pd.Series(mm["ioc_basis"].to_numpy(dtype=object), dtype=object)
    use = country.isna() & fsc.notna()
    country[use], basis[use] = fsc[use], "flashscore_country"
    # Stage 0's country against Flashscore's: when they name different countries the zone is not knowable (each
    # source is right in some such cases: Stage 4 places the 2010 Tournament of Champions in Sofia, not Bali;
    # Flashscore files the 2021 Australian Open qualifying, played in Dubai and Doha, under Australia)
    clash = [Z.same_country(a, b) is False for a, b in zip(country, fsc)]
    zones = []
    for c, a, b, yr, cl in zip(country, ff["tournament_name"].fillna(""), mm["tournament_name"].fillna(""), mm["year"], clash):
        fixed = Z.fixed_venue(b, yr)
        if fixed:
            zones.append((fixed, "event venue (fixed)"))
        elif cl:
            zones.append((None, "countries disagree (Stage 0 and Flashscore)"))
        else:
            zones.append(Z.zone_of(c, [a, b]))
    zone = pd.Series([z for z, _ in zones], dtype=object)
    zbasis = pd.Series([b for _, b in zones], dtype=object)
    start = ff["start_utc"]
    local = pd.Series(pd.NaT, index=start.index, dtype="datetime64[s]")
    has = start.notna() & zone.notna()
    for z, idx in zone[has].groupby(zone[has]).groups.items():
        local.loc[idx] = start.loc[idx].dt.tz_convert(z).dt.tz_localize(None).dt.normalize().astype("datetime64[s]")
    utc_day = start.dt.tz_convert(None).dt.normalize().astype("datetime64[s]")
    board = ff["board_date"].astype("datetime64[s]")
    date_local = local.where(has, utc_day.where(start.notna(), board))
    date_basis = pd.Series(np.where(has, "local", "utc_date"), dtype=object)
    out = pd.DataFrame({"country": country, "country_basis": basis, "fs_country_ioc": fsc, "zone": zone,
                        "zone_basis": zbasis, "date_local": date_local.dt.date, "date_basis": date_basis,
                        "utc_day": utc_day.dt.date})
    both = country.notna() & fsc.notna() & basis.ne("flashscore_country")
    agree = pd.Series([bool(Z.same_country(a, b)) for a, b in zip(country, fsc)], index=country.index)
    stats = {"country_basis": basis.fillna("unknown").value_counts().to_dict(),
             "zone_basis": zbasis.fillna("unknown").value_counts().to_dict(),
             "date_basis": date_basis.value_counts().to_dict(),
             "stage0_country_vs_flashscore_country": {"both_known": int(both.sum()),
                                                      "agree": int((both & agree).sum()),
                                                      "disagree_examples": records(pd.DataFrame({
                                                          "tournament": mm.loc[both & ~agree, "tournament_name"],
                                                          "year": mm.loc[both & ~agree, "year"],
                                                          "stage0_country": country[both & ~agree],
                                                          "flashscore_country": ff.loc[both & ~agree, "country"],
                                                          "flashscore_tournament": ff.loc[both & ~agree, "tournament_name"]})
                                                          .drop_duplicates(["tournament", "stage0_country"]).head(40))},
             "local_date_differs_from_utc_date": int((has & (local != utc_day)).sum()),
             "utc_date_reasons": zbasis[~has].fillna("no start time").value_counts().to_dict()}
    return out, stats


# ------------------------------------------------------------------------------------------------
# Checks and tables

def tennis_data_agreement(out: pd.DataFrame, m: pd.DataFrame) -> dict:
    o = pd.read_parquet(ODDS, columns=["match_id", "link", "td_date", "td_redated", "td_tournament", "td_round",
                                        "td_winner", "td_loser"])
    o = o[o["link"].ne("none") & o["td_date"].notna() & ~o["td_redated"].astype(bool)]
    j = out.merge(o, on="match_id", how="inner")
    j = j.merge(m[["match_id", "tournament_name", "tournament_date", "round", "level", "tour", "year"]], on="match_id")
    j["diff"] = (pd.to_datetime(j["date_local"]) - pd.to_datetime(j["td_date"])).dt.days
    j["diff_utc"] = (pd.to_datetime(j["utc_day"]) - pd.to_datetime(j["td_date"])).dt.days
    uk_day = pd.to_datetime(j["start_utc"], utc=True).dt.tz_convert("Europe/London").dt.tz_localize(None).dt.normalize()
    j["diff_uk"] = (uk_day - pd.to_datetime(j["td_date"])).dt.days

    def shares(d: pd.Series) -> dict:
        n = len(d)
        if not n:
            return {"matches": 0}
        return {"matches": int(n), "same_day": int((d == 0).sum()), "same_day_pct": round(100 * float((d == 0).mean()), 2),
                "plus_minus_1": int((d.abs() == 1).sum()), "plus_minus_1_pct": round(100 * float((d.abs() == 1).mean()), 2),
                "larger": int((d.abs() > 1).sum()), "larger_pct": round(100 * float((d.abs() > 1).mean()), 3),
                "flashscore_later_by_1": int((d == 1).sum()), "flashscore_earlier_by_1": int((d == -1).sum())}

    worst = j.assign(absdiff=j["diff"].abs()).sort_values(["absdiff", "match_id"], ascending=[False, True]).head(20)
    return {"overlap_rule": "Stage 1's linked tennis-data rows (td_date not re-dated) against this link's date_local",
            "all": shares(j["diff"]),
            "by_date_basis": {b: shares(g["diff"]) for b, g in j.groupby("date_basis")},
            "utc_date_instead_of_local": shares(j["diff_utc"]),
            "uk_date_instead_of_local": shares(j["diff_uk"]),
            "by_tour": {t: shares(g["diff"]) for t, g in j.groupby("tour")},
            "by_level": {lv: shares(g["diff"]) for lv, g in j.groupby("level")},
            "worst_20": records(worst[["match_id", "tour", "level", "year", "tournament_name", "round", "tournament_date",
                                       "td_tournament", "td_round", "td_winner", "td_loser", "td_date", "date_local",
                                       "date_basis", "start_utc", "zone", "diff", "link_method", "source_key"]])}


def date_flags(out: pd.DataFrame, m: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    j = out.merge(m[["match_id", "tour", "level", "qualifying", "year", "round", "tournament_name", "tournament_date"]],
                  on="match_id")
    d = (pd.to_datetime(j["date_local"]) - j["tournament_date"]).dt.days
    early = np.where(j["qualifying"], d < -EARLY_QUAL, d < -EARLY_MAIN)
    end = j["level"].map(PLAUSIBLE_END).fillna(PLAUSIBLE_END_DEFAULT)
    late = d > end
    j = j.assign(days_from_tournament_date=d, early=early, late=late)
    flagged = j[j["early"] | j["late"]]
    stats = {"rule": f"main draw more than {EARLY_MAIN} day before the tournament date, qualifying more than {EARLY_QUAL} "
                     f"days before; after the plausible end: tournament date + {PLAUSIBLE_END} days by level "
                     f"(others {PLAUSIBLE_END_DEFAULT})",
             "early": int(j["early"].sum()), "late": int(j["late"].sum()),
             "early_by_level_qualifying": records(j[j["early"]].groupby(["tour", "level", "qualifying"]).size()
                                                  .rename("matches").reset_index()),
             "late_by_level_qualifying": records(j[j["late"]].groupby(["tour", "level", "qualifying"]).size()
                                                 .rename("matches").reset_index()),
             "days_from_tournament_date_by_level": records(
                 j.groupby(["level", "qualifying"])["days_from_tournament_date"].describe(percentiles=[.001, .01, .5, .99, .999])
                 .round(1).reset_index()),
             "examples": records(flagged.sort_values("days_from_tournament_date").iloc[
                 list(range(min(10, len(flagged)))) + list(range(max(len(flagged) - 10, 0), len(flagged)))]
                 [["match_id", "tournament_name", "round", "tournament_date", "date_local", "date_basis",
                   "days_from_tournament_date", "link_method", "source_key"]].drop_duplicates("match_id"))}
    return j[["match_id", "early", "late"]], stats


def coverage(m: pd.DataFrame, reason: pd.Series) -> pd.DataFrame:
    """Per tour x level x qualifying x year: matches, linked with a start time, linked to a daily board only,
    ambiguous, unlinked, and the share linked with a start time."""
    t = m[["tour", "level", "qualifying", "year"]].assign(
        linked=reason.eq("linked").to_numpy(), board=reason.eq(BOARD_ONLY).to_numpy(),
        ambiguous=reason.str.startswith("ambiguous").to_numpy())
    g = t.groupby(["tour", "level", "qualifying", "year"]).agg(
        matches=("linked", "size"), linked=("linked", "sum"), linked_daily_board_only=("board", "sum"),
        ambiguous=("ambiguous", "sum")).reset_index()
    g["unlinked"] = g["matches"] - g["linked"] - g["linked_daily_board_only"] - g["ambiguous"]
    g["linked_pct"] = (100 * g["linked"] / g["matches"]).round(1)
    return g


def local_hour_check(tz: pd.DataFrame, ff: pd.DataFrame) -> dict:
    """Start hours in the assigned zone: play rarely starts before 07:00 or after 23:00 local, so a venue whose
    starts cluster there points to a wrong zone (or to start times that are not playing times)."""
    start = ff["start_utc"]
    hour = pd.Series(np.nan, index=tz.index)
    zones = tz["zone"].dropna()
    for z, idx in zones.groupby(zones).groups.items():
        loc = start.loc[idx].dt.tz_convert(z)
        hour.loc[idx] = (loc.dt.hour + loc.dt.minute / 60).to_numpy()
    city = ff["tournament_name"].map(Z.city_key)
    t = pd.DataFrame({"country": tz["country"], "zone": tz["zone"], "city": city, "hour": hour,
                      "utc_hour": start.dt.hour + start.dt.minute / 60, "basis": tz["date_basis"]})
    loc = t[t["hour"].notna()]
    odd = loc["hour"].lt(7) | loc["hour"].ge(23)
    g = loc.assign(odd=odd).groupby(["country", "zone", "city"]).agg(
        matches=("hour", "size"), median_local_hour=("hour", "median"), share_before_7_or_from_23=("odd", "mean"))
    g = g[g["matches"] >= 20].reset_index()
    sus = g[(g["share_before_7_or_from_23"] > 0.2) | ~g["median_local_hour"].between(9, 20)]
    utc = t[t["basis"].eq("utc_date")]
    return {"local_rows": int(len(loc)), "local_start_before_7_or_from_23": int(odd.sum()),
            "local_start_before_7_or_from_23_pct": round(100 * float(odd.mean()), 2) if len(loc) else None,
            "local_hour_quantiles": {str(k): round(float(v), 2) for k, v in loc["hour"].quantile([.01, .05, .5, .95, .99]).items()},
            "venues_with_20_plus_matches": int(len(g)),
            "suspicious_venues": records(sus.sort_values("matches", ascending=False).round(3).head(40)),
            "utc_date_rows_by_country": utc["country"].fillna("unknown").value_counts().head(25).to_dict(),
            "utc_date_rows_utc_hour_quantiles": ({str(k): round(float(v), 2) for k, v in
                                                  utc["utc_hour"].quantile([.05, .5, .95]).items()} if len(utc) else {})}


# ------------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    ap.add_argument("--work-dir", type=Path, default=Path(tempfile.gettempdir()) / "flashscore_link_work")
    ap.add_argument("--reparse", action="store_true", help="parse the raw files again even if shards exist")
    ap.add_argument("--rebuild-records", action="store_true", help="rebuild flashscore_records.parquet from the shards")
    args = ap.parse_args()
    workers = max(1, min(args.workers, MAX_WORKERS))
    rec, results, rstats = load_records(args.work_dir, workers, args.reparse, args.rebuild_records)
    f, fstats = flashscore_side(rec)
    del rec
    log(f"Flashscore matches in scope: {len(f):,}")
    noid = noid_coverage(results, f)
    m = stage0_side()
    log(f"Stage 0 matches: {len(m):,}")
    links, amb, dup, reason, lstats = link_all(m, f)
    method = links["pass_"] + ";" + links["tier"].map({3: "set_scores", 2: "sets_won", 1: "round"})
    method = method + np.where(links["strict"].astype(bool), "", ";loose_names")
    links["link_method"] = method + np.where(links["score_from_winner_side"].astype(bool), ";scores_from_winner_side", "")
    timed = f["has_start"].to_numpy()[links["ri"].to_numpy()]
    board = links[~timed].reset_index(drop=True)
    links = links[timed].reset_index(drop=True)
    reason[board["li"].to_numpy()] = BOARD_ONLY
    tz, zstats = local_dates(links, m, f)
    links["link_method"] = links["link_method"] + ";" + tz["zone_basis"].map(ZONE_TOKEN).fillna("utc").to_numpy()
    ff = f.loc[links["ri"].to_numpy()].reset_index(drop=True)
    out = pd.DataFrame({
        "match_id": m.loc[links["li"].to_numpy(), "match_id"].to_numpy(),
        "source": "flashscore",
        "source_key": ff["fs_match_id"].to_numpy(),
        "date_local": tz["date_local"].to_numpy(),
        "start_utc": ff["start_utc"].to_numpy(),
        "date_basis": tz["date_basis"].to_numpy(),
        "link_method": links["link_method"].to_numpy(),
        "score_agrees": links["score_agrees"].astype("boolean").to_numpy(),
        "round_agrees": links["round_agrees"].astype("boolean").to_numpy(),
    })
    out["date_local"] = pd.to_datetime(out["date_local"]).dt.date
    out["start_utc"] = pd.to_datetime(out["start_utc"], utc=True)
    assert out["match_id"].is_unique and out["source_key"].is_unique
    extra = pd.concat([out[["match_id", "source_key", "date_local", "start_utc", "date_basis", "link_method"]],
                       tz[["utc_day", "zone"]]], axis=1)
    agreement = tennis_data_agreement(extra, m)
    flags, fl_stats = date_flags(out, m)
    hours = local_hour_check(tz, ff)
    out = out.sort_values("match_id").reset_index(drop=True)
    out.to_parquet(LINKS, index=False)
    fb = f.loc[board["ri"].to_numpy()].reset_index(drop=True)
    pd.DataFrame({"match_id": m.loc[board["li"].to_numpy(), "match_id"].to_numpy(), "source": "flashscore_daily_board",
                  "source_key": fb["fs_match_id"].to_numpy(), "board_date": fb["board_date"].dt.date.to_numpy(),
                  "link_method": board["link_method"].to_numpy(),
                  "score_agrees": board["score_agrees"].astype("boolean").to_numpy(),
                  "round_agrees": board["round_agrees"].astype("boolean").to_numpy()}
                 ).sort_values("match_id").to_parquet(BOARD, index=False)
    # ambiguous candidates and duplicate ids
    side = []
    for frame in (amb, dup):
        if len(frame):
            side.append(pd.DataFrame({
                "match_id": m.loc[frame["li"].to_numpy(), "match_id"].to_numpy(), "kind": frame["kind"].to_numpy(),
                "fs_match_id": f.loc[frame["ri"].to_numpy(), "fs_match_id"].to_numpy(),
                "start_utc": f.loc[frame["ri"].to_numpy(), "start_utc"].to_numpy(),
                "fs_tournament": f.loc[frame["ri"].to_numpy(), "tournament_name"].to_numpy(),
                "fs_home": f.loc[frame["ri"].to_numpy(), "home_name"].to_numpy(),
                "fs_away": f.loc[frame["ri"].to_numpy(), "away_name"].to_numpy(),
                "gap_days": frame["gap"].to_numpy(), "tier": frame["tier"].to_numpy(),
                "kept_fs_match_id": (f.loc[frame["kept_ri"].to_numpy(), "fs_match_id"].to_numpy()
                                     if "kept_ri" in frame else None)}))
    side = pd.concat(side, ignore_index=True) if side else pd.DataFrame(columns=["match_id", "kind"])
    side.to_parquet(AMBIGUOUS, index=False)
    un = m.loc[reason.ne("linked").to_numpy(), ["match_id", "tour", "level", "qualifying", "year", "tournament_date"]]
    un = un.assign(reason=reason[reason.ne("linked")].to_numpy())
    un.to_parquet(UNLINKED, index=False)
    cov = coverage(m, reason)
    cov.to_csv(COUNTS, index=False)
    linked_f = f.loc[links["ri"].to_numpy()]
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "generated_by": "src/eda/match_timing/link_flashscore.py",
        "source": {"dataset": "atlas-polybot/atp-pipeline-handoff", "revision": "ea3d94d79f5d9e9b4bead031e2c6262f91a86c35",
                   "downloaded": "2026-09-25",
                   "folders": [f"data/raw/public_dump/atp_pipeline_handoff/{x}/" for x in P.FOLDERS],
                   "licence": "none published (no dataset card)"},
        "targets": {"stage0_matches": "data/studies/predictability_diagnostic/stage0_matches.parquet",
                    "stage0_matches_rows": int(len(m))},
        "parameters": {"scope_from": P.SCOPE_FROM, "window_days": list(WINDOW), "expected_main": EXPECTED_MAIN,
                       "expected_main_default": list(EXPECTED_MAIN_DEFAULT), "expected_qualifying": list(EXPECTED_QUAL)},
        "files_and_records_read": parse_summary(results),
        "rows_without_id_or_start_time_against_timestamped_rows": noid,
        "records_table": rstats,
        "flashscore_in_scope": fstats,
        "linking": lstats,
        "stage0_outcome": reason.value_counts().to_dict(),
        "stage0_linked_with_start_time": int(reason.eq("linked").sum()),
        "stage0_linked_to_daily_board_only": int(reason.eq(BOARD_ONLY).sum()),
        "stage0_ambiguous": int(reason.str.startswith("ambiguous").sum()),
        "stage0_unlinked": int((~reason.isin(["linked", BOARD_ONLY]) & ~reason.str.startswith("ambiguous")).sum()),
        "flashscore_matches_linked": int(len(links) + len(board)),
        "linked_by_origin_of_flashscore_match": linked_f["origin"].value_counts().to_dict(),
        "link_method_counts": out["link_method"].value_counts().to_dict(),
        "daily_board_link_method_counts": board["link_method"].value_counts().to_dict(),
        "score_agrees": out["score_agrees"].astype("object").fillna("null").astype(str).value_counts().to_dict(),
        "round_agrees": out["round_agrees"].astype("object").fillna("null").astype(str).value_counts().to_dict(),
        "flashscore_status_against_stage0_status": records(pd.crosstab(
            linked_f["status"].fillna("none").to_numpy(),
            m.loc[links["li"].to_numpy(), "status"].to_numpy(), rownames=["flashscore"], colnames=["stage0"]).reset_index()),
        "local_dates": zstats,
        "local_start_hours": hours,
        "agreement_with_tennis_data": agreement,
        "date_flags": fl_stats,
        "link_counts_by_tour_level_qualifying_year": records(cov),
        "unlinked_reasons_by_tour_level": records(
            pd.crosstab([un["tour"], un["level"]], un["reason"]).reset_index()),
        "runtime_seconds": round(time.time() - T0, 1),
    }
    SUMMARY.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log(f"wrote {LINKS.name} ({len(out):,} links), {BOARD.name} ({len(board):,}), {AMBIGUOUS.name}, {UNLINKED.name}, "
        f"{COUNTS.name}, {SUMMARY.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
