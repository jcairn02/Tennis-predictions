"""P9 point details, the harness's population (brief: docs/studies/p9_point_details/briefs/03_harness.md).

One row per men's Stage 0 match whose day (the match clock's `obs`, floored) falls in 2025-01-01 .. 2026-10-18:
    tour level    the Slams, the Finals, the 1000s, 500s and 250s: main draws and qualifying
    Challengers   main draws and qualifying
Completed and retired matches are kept (`finished` = completed; the project's checks score both and report completed
matches only as a sensitivity). Walkovers, the 'other' statuses and the Next Gen Finals (a nonstandard format, outside
the model's frame) are left out and counted.

Prices (`price_logit`, A's margin-free log-odds; the margin is removed proportionally, p_A = (1/d_A) / (1/d_A + 1/d_B),
book by book):
    tour main draw   the Pinnacle-first close under the current default rule (odds_input.RULE, 2026-10-21), built in
                     memory exactly as src/eda/pinnacle_gap/dry_run.py builds it: the live instance's per-source table,
                     TennisExplorer's tour staging linked to its frame (tennisexplorer.link_frame, read-only), then
                     odds_input.construct. The instance's own input (rule 2026-10-09) is kept as price_logit_instance.
    tour qualifying  OddsTrader's lines as the qualifying-targets study kept them (data/studies/qualifying_targets/
                     prices.parquet): Pinnacle's last line where kept (OddsTrader's Pinnacle ends in September 2025),
                     else BetOnline's last line. TennisExplorer has no tour-level qualifying (its tour staging holds main
                     draws only; the lower-level collector leaves tour events out).
    Challengers      TennisExplorer's lower-level pages (data/dump/odds/tennisexplorer_lower/), linked here to Stage 0
                     (link_challengers): Pinnacle's last price where the site shows it with times, on time (its last
                     change no later than 30 minutes after the listed start) and not grossly apart from the site's other
                     books (the production rule's test); else the median of the other books' margin-free log-odds (each
                     coherent and on time). A link whose winner disagrees with Stage 0's is refused.

Model forecasts (tour level; stored fits only: no TabPFN fit, no GPU):
    main draw        the live instance's backtest fits (season Y trained on 2013..Y-1, checked against the expanding
                     window), 16 seeds averaged; the per-tour slope and stage 2 (b * spd_L_B, b shrunk with tau 0.05)
                     fitted walk-forward on 2019..Y-1 from seeds 0-3 (compare.walk_forward), as
                     unpriced_leads/build_forecasts.py builds them. model_logit_s1: the slope alone.
    qualifying       the qualifying-targets study's arm M0, the instance's own model (its main-draw block equals the
                     instance's fits exactly), seeds 0-3, on its qualifying block, with the main-draw slope and stage 2
                     (qualifying_targets/top_edges.py's "main-draw stage 2"). model_seeds says 16 or 4.

Results read: Stage 0's a_won for the population (stored); the instance frame's a_won of 2019-2026 for the walk-forward
fits. No P9 table and no rally statistic is read (guard: _check_path).

Writes data/studies/p9_point_details/harness/: population.parquet, model_inputs.parquet (the model's 48 non-price
inputs as A - B for the tour-level rows, outcome-free), challenger_link.parquet, population_facts.json.
Run: ./python.sh src/eda/p9_point_details/harness_population.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import odds_input as O  # noqa: E402
from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.ingest import tennisexplorer as TEI  # noqa: E402

STUDIES = ROOT / "data" / "studies"
STAGE0 = STUDIES / "predictability_diagnostic" / "stage0_matches.parquet"
PLAYERS = STUDIES / "predictability_diagnostic" / "stage0_match_players.parquet"
TIMING = STUDIES / "match_timing" / "timing.parquet"
SELECTED = STUDIES / "master_pipeline" / "selected_instance.json"
INSTANCES = STUDIES / "current_best_model"
EXPECTED_INSTANCE = "template_2026-10-21b"          # the brief's live instance (selected_instance.json, 28 Oct 2026)
QT = STUDIES / "qualifying_targets"
TE_LOWER = ROOT / "data" / "dump" / "odds" / "tennisexplorer_lower"
OUT = STUDIES / "p9_point_details" / "harness"
FORBIDDEN = (ROOT / "data" / "dump" / "points" / "infosys_atp_recent", STUDIES / "p9_point_details" / "build")

FIRST_DAY, LAST_DAY = "2025-01-01", "2026-10-18"
TOUR_LEVELS = ("GS", "FIN", "T1000", "T500", "T250")
CH_LEVELS = ("CH",)
SEASONS_FIT = tuple(range(2019, 2027))             # 2019-2024 calibrate only
TEST = (2025, 2026)
SEEDS16, SEEDS4 = tuple(range(16)), (0, 1, 2, 3)
LATE_MIN = Q.LATE_MIN                               # 30 minutes after the listed start
CHALLENGER = re.compile(r"(?:challenger|-chall$)")
EVENT_HREF = re.compile(r"^/([^/]+)/(\d{4})/atp-men/$")
SETS = re.compile(r"^\s*(\d+)\s*:\s*(\d+)")
CONTEXT = ("tour", "surface", "level", "indoor", "best_of", "round")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def _check_path(p: Path) -> Path:
    """The brief's blinding: no table under the P9 dump or the study's build folder is ever opened here."""
    rp = Path(p).resolve()
    for bad in FORBIDDEN:
        if rp == bad.resolve() or bad.resolve() in rp.parents:
            raise RuntimeError(f"{p}: a P9 table or the study's build folder; the harness never opens it")
    return Path(p)


def read_parquet(p: Path, **kw) -> pd.DataFrame:
    return pd.read_parquet(_check_path(p), **kw)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(_check_path(p), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (pd.Timestamp, dt.date)):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o)
        raise TypeError(type(o))
    path.write_text(json.dumps(value, indent=1, default=default), encoding="utf-8")


def instance_folder() -> Path:
    sel = json.loads(SELECTED.read_text(encoding="utf-8"))
    if sel.get("instance") != EXPECTED_INSTANCE:
        raise SystemExit(f"the live model is now {sel.get('instance')}, not the brief's {EXPECTED_INSTANCE}: ask the lead")
    return INSTANCES / sel["instance"]


# ------------------------------------------------------------------------------------------------
# The matches

def window_matches() -> tuple[pd.DataFrame, dict]:
    """Men's tour-level and Challenger matches of the window with their day, players' names and flags."""
    cols = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "surface", "indoor", "best_of",
            "tournament_id", "tournament_name", "tournament_date", "status", "status_detail", "nonstandard_format",
            "player_a_id", "player_b_id", "a_won", "score"]
    s = read_parquet(STAGE0, columns=cols, filters=[("tour", "==", "atp")])
    s = s[s["level"].isin(TOUR_LEVELS + CH_LEVELS)].copy()
    t = read_parquet(TIMING, columns=["match_id", "obs", "es", "lf", "exact"])
    s = s.merge(t, on="match_id", how="left", validate="one_to_one")
    if s["obs"].isna().any():
        raise RuntimeError(f"{int(s['obs'].isna().sum())} matches without a clock row")
    s["date"] = pd.to_datetime(np.floor(s["obs"].to_numpy(float)).astype("int64"), unit="D")
    s = s[(s["date"] >= FIRST_DAY) & (s["date"] <= LAST_DAY)].copy()
    s["level_group"] = np.where(s["level"].isin(TOUR_LEVELS), "tour", "challenger")
    s["draw"] = np.where(s["qualifying"].astype(bool), "qualifying", "main")
    counts = {"window_rows": int(len(s)),
              "status": {f"{g}|{d}|{k}": int(v) for (g, d, k), v in
                         s.groupby(["level_group", "draw", "status"]).size().items()},
              "nonstandard_format": {str(k): int(v) for k, v in
                                     s[s["nonstandard_format"].astype(bool)]["tournament_name"].value_counts().items()}}
    keep = s["status"].isin(["completed", "retired"]) & ~s["nonstandard_format"].astype(bool)
    counts["left_out"] = {"walkover": int((s["status"] == "walkover").sum()),
                          "other_status": int((s["status"] == "other").sum()),
                          "nonstandard_format_played": int((s["nonstandard_format"].astype(bool)
                                                            & s["status"].isin(["completed", "retired"])).sum())}
    s = s[keep].copy()
    s["finished"] = s["status"].eq("completed")
    s["a_won"] = s["a_won"].astype(bool)
    pl = read_parquet(PLAYERS, columns=["match_id", "side", "player_name"])
    pl = pl[pl["match_id"].isin(s["match_id"])].pivot(index="match_id", columns="side", values="player_name")
    s = s.join(pl.rename(columns={"A": "name_a", "B": "name_b"}), on="match_id")
    s["week"] = SC.blocks(s["tournament_date"].to_numpy(), 7)
    s["block"] = SC.blocks(s["tournament_date"].to_numpy(), 28)
    s["half"] = s["date"].dt.year.astype(str) + np.where(s["date"].dt.month <= 6, "-H1", "-H2")
    return s.reset_index(drop=True), counts


# ------------------------------------------------------------------------------------------------
# Tour level: the main draw's close (rule 2026-10-21) and the instance's own input

def tour_main_prices(inst: Path) -> tuple[pd.DataFrame, dict]:
    sources = read_parquet(inst / "odds_sources.parquet")
    link, how = TEI.link_frame(inst / "model_frame.parquet", dt.date.fromisoformat(O.TE_LINK_SINCE))
    te = O.te_columns(link)
    s = sources.drop(columns=[c for c in sources.columns if c.startswith("tex_")]).merge(te, on="match_id", how="left")
    now = O.construct(s, O.RULE)
    before = O.construct(sources, O.RULE_BEFORE)
    stored = read_parquet(inst / "book_prices.parquet", columns=["match_id", "p_input", "odds_input"])
    chk = stored.merge(before[["match_id", "p_input", "odds_input"]], on="match_id", suffixes=("_stored", "_rebuilt"))
    facts = {"te_link": how, "rule": O.RULE,
             "rule_before_reproduces_instance": {
                 "matches": int(len(chk)),
                 "max_abs_diff": float(np.max(np.abs(chk["p_input_stored"] - chk["p_input_rebuilt"]))),
                 "same_source": int((chk["odds_input_stored"] == chk["odds_input_rebuilt"]).sum())}}
    out = now[["match_id", "p_input", "odds_input", "pin_source"]].rename(
        columns={"p_input": "p_close", "odds_input": "close_source"})
    out = out.merge(stored.rename(columns={"p_input": "p_instance", "odds_input": "instance_source"}), on="match_id",
                    how="left")
    # TennisExplorer's score against the frame's result, on the matches priced by the site (a check of the link only)
    if len(link):
        tm = read_parquet(TEI.DUMP / "matches.parquet", columns=["te_id", "score"])
        lk = link[["match_id", "te_id", "a_is_p2"]].merge(tm, on="te_id", how="left")
        facts["te_link_winner_check"] = _winner_check(lk, sources[["match_id", "a_won"]])
    return out, facts


def _te_winner_is_p1(score: pd.Series) -> np.ndarray:
    """+1 when the site's first player won (more sets), 0 when the second did, NaN when the sets do not say."""
    m = score.astype("string").str.extract(SETS)
    a, b = pd.to_numeric(m[0], errors="coerce").to_numpy(float), pd.to_numeric(m[1], errors="coerce").to_numpy(float)
    return np.where(a > b, 1.0, np.where(b > a, 0.0, np.nan))


def _winner_check(lk: pd.DataFrame, res: pd.DataFrame) -> dict:
    j = lk.merge(res, on="match_id", how="left")
    p1 = _te_winner_is_p1(j["score"])
    a_won_site = np.where(j["a_is_p2"].astype(bool), 1.0 - p1, p1)
    ok = np.isfinite(a_won_site) & j["a_won"].notna().to_numpy()
    agree = ok & (a_won_site == j["a_won"].astype(float).to_numpy())
    return {"linked": int(len(j)), "checked": int(ok.sum()), "agree": int(agree.sum()),
            "disagree": int((ok & ~agree).sum())}


def tour_qual_prices() -> pd.DataFrame:
    p = read_parquet(QT / "prices.parquet", columns=["match_id", "p_close", "close_source", "after_pin_min",
                                                      "after_bol_min"])
    p["close_source"] = p["close_source"].map({"pinnacle": "pinnacle (oddstrader)", "betonline": "betonline (oddstrader)",
                                               "none": "none"})
    return p


# ------------------------------------------------------------------------------------------------
# Challengers: TennisExplorer's lower-level pages, their prices and the link to Stage 0

def _months(first: str, last: str) -> list[str]:
    out, d = [], pd.Timestamp(first + "-01")
    while d.strftime("%Y-%m") <= last:
        out.append(d.strftime("%Y-%m"))
        d = d + pd.offsets.MonthBegin(1)
    return out


def te_lower_pages(first: str = "2024-12", last: str = "2026-10") -> tuple[pd.DataFrame, dict]:
    """Men's Challenger match pages (main draws and qualifying) with the staging's provenance."""
    parts, files = [], {}
    for m in _months(first, last):
        p = TE_LOWER / "matches" / f"{m}.parquet"
        if p.exists():
            parts.append(read_parquet(p))
            files[m] = {"rows": int(len(parts[-1])), "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat()}
    m = pd.concat(parts, ignore_index=True)
    m = m.astype({c: "object" for c in m.columns})
    key = m["event_href"].astype(str).str.extract(EVENT_HREF)
    m["slug"], m["event_year"] = key[0], pd.to_numeric(key[1], errors="coerce")
    men_ch = m["slug"].notna() & m["slug"].astype(str).str.contains(CHALLENGER)
    m = m[men_ch].copy()
    m["te_id"] = m["te_id"].astype("int64")
    m["date"] = pd.to_datetime(m["date"])
    m["start_utc"] = pd.to_datetime(m["start_utc"], utc=True, errors="coerce")
    m["te_qual"] = m["round"].astype(str).str.startswith("Qualification")
    m["n_books"] = pd.to_numeric(m["n_books"], errors="coerce")
    m = m.drop_duplicates("te_id")
    return m.reset_index(drop=True), files


def te_lower_odds(te_ids: set, first: str = "2024-12", last: str = "2026-10") -> pd.DataFrame:
    parts = []
    for m in _months(first, last):
        p = TE_LOWER / "odds" / f"{m}.parquet"
        if p.exists():
            o = read_parquet(p)
            o = o[o["te_id"].astype("int64").isin(te_ids)]
            parts.append(o)
    o = pd.concat(parts, ignore_index=True)
    o["te_id"] = o["te_id"].astype("int64")
    for c in ("k1_last", "k2_last", "k1_open", "k2_open", "k1_n_moves", "k2_n_moves"):
        o[c] = pd.to_numeric(o[c], errors="coerce")
    for c in ("k1_last_t", "k2_last_t", "k1_open_t", "k2_open_t"):
        o[c] = pd.to_datetime(o[c], utc=True, errors="coerce")
    return o.drop_duplicates(["te_id", "book"], keep="last")


def te_lower_prices(pages: pd.DataFrame, odds: pd.DataFrame) -> pd.DataFrame:
    """Per page: the price of the site's first player (p1) and its source.
    te_pinnacle   Pinnacle's last price, shown with times (an opening time or a change), coherent, its last change no
                  later than LATE_MIN after the listed start, and not grossly apart from the median of the other books
                  (at least Q.MIN_REF of them agreeing within Q.AGREE: over Q.GROSS in log-odds and Q.GROSS_PP in chance)
    te_consensus  else the median of the other books' margin-free log-odds (each coherent and on time)"""
    o = odds.merge(pages[["te_id", "start_utc"]], on="te_id", how="inner")
    d1, d2 = o["k1_last"].to_numpy(float), o["k2_last"].to_numpy(float)
    coh = OC.coherent(d1, d2)
    last_t = o[["k1_last_t", "k2_last_t"]].max(axis=1)
    # hours from the book's last recorded change to the listed start (NaN: no time shown); late = in-play risk
    lead = (o["start_utc"] - last_t).dt.total_seconds().to_numpy(float) / 3600.0
    late = lead < -LATE_MIN / 60.0
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.log(d2 / d1)                                   # p1's margin-free log-odds (proportional)
    o = o.assign(z=z, ok=coh & ~late, late=late, lead=lead,
                 timed=o["k1_open_t"].notna() | ((o["k1_n_moves"].fillna(0) + o["k2_n_moves"].fillna(0)) > 0))
    oth = o[(o["book"] != "Pinnacle") & o["ok"]]
    g = oth.groupby("te_id")
    ref = pd.DataFrame({"z_books": g["z"].median(), "n_books_ok": g.size(),
                        "iqr_books": g["z"].quantile(0.75) - g["z"].quantile(0.25),
                        "lead_books": g["lead"].median()})
    pin = o[o["book"] == "Pinnacle"].set_index("te_id")[["z", "ok", "timed", "late", "lead"]].add_prefix("pin_")
    out = pages[["te_id", "start_utc"]].set_index("te_id").join(ref).join(pin)
    zb, zp = out["z_books"].to_numpy(float), out["pin_z"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        off = (out["n_books_ok"].fillna(0).to_numpy() >= Q.MIN_REF) & (out["iqr_books"].to_numpy(float) < Q.AGREE) \
            & (np.abs(zp - zb) > Q.GROSS) & (np.abs(expit(zp) - expit(zb)) > Q.GROSS_PP)
    pin_ok = out["pin_ok"].fillna(False).astype(bool).to_numpy() & out["pin_timed"].fillna(False).astype(bool).to_numpy()
    use_pin = pin_ok & ~off & np.isfinite(zp)
    use_books = ~use_pin & np.isfinite(zb)
    out["p1_logit"] = np.where(use_pin, zp, np.where(use_books, zb, np.nan))
    out["te_source"] = np.where(use_pin, "te_pinnacle", np.where(use_books, "te_consensus", "none"))
    out["pin_shown"] = out["pin_z"].notna()
    out["pin_untimed"] = out["pin_shown"] & ~out["pin_timed"].fillna(False).astype(bool)
    out["pin_off_books"] = off
    out["price_lead_hours"] = np.where(use_pin, out["pin_lead"].to_numpy(float), out["lead_books"].to_numpy(float))
    return out.reset_index()


def _hits(tA: frozenset, tB: frozenset, cands: pd.DataFrame, test) -> list[tuple[int, bool]]:
    hits = []
    for t in cands.itertuples():
        if test(t.t1, tA) and test(t.t2, tB):
            hits.append((t.Index, False))
        elif test(t.t1, tB) and test(t.t2, tA):
            hits.append((t.Index, True))
    return hits


def link_challengers(s: pd.DataFrame, pages: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Stage 0's Challenger matches to the site's pages. Pass 1: the site's day within one day of the match clock's
    day and both players' word sets the same (tennisexplorer._same_tokens); pass 2: the site's day within
    [tournament date - 7, + 10]; pass 3: inside the site's event that the tournament's other links name, the looser
    name test (tennisexplorer._close_tokens). Several candidates: the one of the same draw (qualifying or main) if
    exactly one, else none. A page claimed by two matches links neither. A link whose sets name the other winner than
    Stage 0 is refused (never guessed)."""
    pg = pages.copy()
    pg["t1"], pg["t2"] = pg["p1"].map(TEI.name_tokens), pg["p2"].map(TEI.name_tokens)
    by_day = {d: g for d, g in pg.groupby(pg["date"].dt.normalize())}
    days = sorted(by_day)
    tok = {}
    for i, (a, b) in enumerate(zip(pg["t1"], pg["t2"])):
        for t in a | b:
            tok.setdefault(t, set()).add(i)

    def cands_for(tA, tB, lo, hi) -> pd.DataFrame:
        ia = set().union(*[tok.get(t, set()) for t in tA]) if tA else set()
        ib = set().union(*[tok.get(t, set()) for t in tB]) if tB else set()
        ix = sorted(ia & ib)
        c = pg.iloc[ix]
        return c[(c["date"] >= lo) & (c["date"] <= hi)]

    rows, how = [], {"pass1_day_names": 0, "pass2_window_names": 0, "pass3_event_close_names": 0,
                     "several": 0, "none": 0}
    left = []
    s = s.copy()
    s["tA"], s["tB"] = s["name_a"].map(TEI.name_tokens), s["name_b"].map(TEI.name_tokens)
    for r in s.itertuples():
        found = None
        for kind, lo, hi in (("pass1_day_names", r.date - pd.Timedelta(days=1), r.date + pd.Timedelta(days=1)),
                             ("pass2_window_names", r.tournament_date - pd.Timedelta(days=7),
                              r.tournament_date + pd.Timedelta(days=10))):
            c = cands_for(r.tA, r.tB, lo, hi)
            hits = _hits(r.tA, r.tB, c, TEI._same_tokens)
            if len(hits) > 1:
                same = [h for h in hits if bool(pg.at[h[0], "te_qual"]) == (r.draw == "qualifying")]
                hits = same if len(same) == 1 else hits
            if len(hits) == 1:
                found = (hits[0], kind)
                break
        if found is None:
            left.append(r)
        else:
            rows.append((r.match_id, found[0][0], found[0][1], found[1]))
    ev = {}
    if rows:
        lk = pd.DataFrame(rows, columns=["match_id", "ix", "a_is_p2", "how"])
        lk["tid"] = s.set_index("match_id").loc[lk["match_id"], "tournament_id"].to_numpy()
        lk["href"] = pg.loc[lk["ix"], "event_href"].to_numpy()
        ev = lk.groupby("tid")["href"].agg(lambda x: x.value_counts().index[0]).to_dict()
    by_href = {h: g for h, g in pg.groupby("event_href")}
    for r in left:
        g = by_href.get(ev.get(r.tournament_id))
        if g is None:
            how["none"] += 1
            continue
        hits = _hits(r.tA, r.tB, g, TEI._close_tokens)
        if len(hits) > 1:
            same = [h for h in hits if bool(pg.at[h[0], "te_qual"]) == (r.draw == "qualifying")]
            hits = same if len(same) == 1 else hits
        if len(hits) == 1:
            rows.append((r.match_id, hits[0][0], hits[0][1], "pass3_event_close_names"))
        else:
            how["none" if not hits else "several"] += 1
    lk = pd.DataFrame(rows, columns=["match_id", "ix", "a_is_p2", "how"])
    for k in ("pass1_day_names", "pass2_window_names", "pass3_event_close_names"):
        how[k] = int((lk["how"] == k).sum())
    twice = lk["ix"].duplicated(keep=False)
    how["page_claimed_twice"] = int(twice.sum())
    lk = lk[~twice].copy()
    lk["te_id"] = pg.loc[lk["ix"], "te_id"].to_numpy()
    lk["te_date"] = pg.loc[lk["ix"], "date"].to_numpy()
    lk["te_round"] = pg.loc[lk["ix"], "round"].to_numpy()
    lk["te_qual"] = pg.loc[lk["ix"], "te_qual"].to_numpy()
    lk["te_score"] = pg.loc[lk["ix"], "score"].to_numpy()
    lk["te_event_href"] = pg.loc[lk["ix"], "event_href"].to_numpy()
    j = lk.merge(s[["match_id", "a_won", "draw", "date"]], on="match_id", how="left")
    p1 = _te_winner_is_p1(j["te_score"])
    a_site = np.where(j["a_is_p2"].astype(bool), 1.0 - p1, p1)
    j["winner_check"] = np.where(~np.isfinite(a_site), "unchecked",
                                 np.where(a_site == j["a_won"].astype(float), "agree", "disagree"))
    j["draw_check"] = np.where(j["te_qual"].astype(bool) == (j["draw"] == "qualifying"), "agree", "disagree")
    j["day_gap"] = (pd.to_datetime(j["te_date"]) - j["date"]).dt.days
    how["winner_check"] = {k: int(v) for k, v in j["winner_check"].value_counts().items()}
    how["draw_check"] = {k: int(v) for k, v in j["draw_check"].value_counts().items()}
    how["refused_winner_disagrees"] = int((j["winner_check"] == "disagree").sum())
    j["linked"] = j["winner_check"] != "disagree"
    return j.drop(columns=["ix", "a_won", "draw", "date"]), how


# ------------------------------------------------------------------------------------------------
# The model's forecasts

def _speed(path: Path, ids: pd.Index, tour: pd.Series) -> tuple[pd.Series, pd.Index]:
    sp = read_parquet(path, columns=["match_id", "spd_L_B"]).astype({"match_id": str})
    z = sp.drop_duplicates("match_id").set_index("match_id")["spd_L_B"].reindex(ids).astype(float)
    men = tour.reindex(ids).to_numpy() == "atp"
    filled = ids[men & ~np.isfinite(z.to_numpy())]
    z = pd.Series(np.where(men, np.nan_to_num(z.to_numpy(), nan=0.0), 0.0), index=ids)
    return z, filled


def model_main(inst: Path) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    _, P, _ = CMP.candidate(str(inst))
    frame = CMP.inputs_frame(P)
    seasons = frame["season"].to_numpy()
    fx = F.FrameIndex(frame.reset_index()[["match_id", "season"]])
    p16, _ = F.seed_table("model", SEASONS_FIT, SEEDS16, fx, P, "td", require_checks=True)
    ids = frame.index[(seasons >= SEASONS_FIT[0]) & (seasons <= SEASONS_FIT[-1])]
    p16 = p16.reindex(ids)
    if p16.isna().any().any():
        raise RuntimeError("forecasts are missing for some frame matches")
    y = read_parquet(P.model_frame, columns=["match_id", "season", "a_won"],
                     filters=[("season", ">=", SEASONS_FIT[0])])
    y = pd.Series(y["a_won"].astype(float).to_numpy(), index=y["match_id"].astype(str).to_numpy())
    info = frame.loc[ids, ["tour", "season", "tournament_date", "debut_season"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = y.reindex(ids).to_numpy(float)
    z, filled = _speed(inst / "stage2_speed_columns.parquet", ids, info["tour"])
    eta4 = pd.Series(SC.lg(p16[list(SEEDS4)].mean(axis=1).to_numpy()), index=ids)
    par_both = CMP.walk_forward(eta4, info, z, TEST)
    par_s1 = CMP.walk_forward(eta4, info, None, TEST)
    test = info.index[info["season"].isin(TEST).to_numpy()]
    q_full, _ = CMP.forecasts(p16, info, par_both, z, test)
    q_s1, _ = CMP.forecasts(p16, info, par_s1, None, test)
    out = pd.DataFrame({"model_logit_full": SC.lg(q_full), "model_logit_s1": SC.lg(q_s1),
                        "model_eta16": SC.lg(p16.loc[test].mean(axis=1).to_numpy()),
                        "spd": z.reindex(test).to_numpy(float), "spd_filled": test.isin(filled),
                        "model_seeds": 16, "model_source": "instance fits"}, index=test)
    # the qualifying study's stored main-draw stage 2 (the same instance, seeds 0-3): a reproduction check
    te = json.loads((QT / "top_edges.json").read_text(encoding="utf-8"))["stage2_params"]["main draw"]
    diff = max(abs(a - b) for Y in TEST for a, b in zip(par_both[Y], te[str(Y)]))
    facts = {"fits": f"{inst.name}/fits, seasons {SEASONS_FIT[0]}-{SEASONS_FIT[-1]}, seeds 0-15 (checked: training "
                     "shape = the expanding window 2013..Y-1, td ids = the season's frame ids in order)",
             "params_both_stages": {str(k): v for k, v in par_both.items()},
             "params_stage1": {str(k): v for k, v in par_s1.items()},
             "params_reproduce_qualifying_study_main_draw": {"max_abs_diff": float(diff)},
             "speed_column": str((inst / "stage2_speed_columns.parquet").relative_to(ROOT)),
             "speed_filled_with_0_men_test": int(len(filled.intersection(test))),
             "results_read": "the instance frame's a_won of 2019-2026 (2019..Y-1 for the fits; 2025-2026 scored)"}
    inputs = frame.loc[test]
    return out, facts, inputs


def _m0_table(block: str, seasons, inst_sha: str, fx_n_train: dict) -> pd.DataFrame:
    parts = []
    for s in seasons:
        per = {}
        for k in SEEDS4:
            path = QT / "local" / f"M0__{s}__seed{k}.npz"
            with np.load(_check_path(path), allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
                if meta.get("instance_frame_sha256") != inst_sha:
                    raise RuntimeError(f"{path.name}: fitted on another instance frame")
                if list(meta.get("train_shape", [])) != [fx_n_train[s], 57] or meta.get("train_rows_qualifying"):
                    raise RuntimeError(f"{path.name}: training shape {meta.get('train_shape')} is not 2013..{s - 1}")
                p, ids = z[f"p_{block}"], z[f"ids_{block}"].astype(str)
            n = len(ids)
            if len(p) != 2 * n:
                raise RuntimeError(f"{path.name}: block {block} is not stored + swapped")
            per[k] = pd.Series(SC.symmetrize(p[:n], p[n:]), index=ids)
        parts.append(pd.DataFrame(per))
    t = pd.concat(parts)
    if t.index.duplicated().any() or t.isna().any().any():
        raise RuntimeError(f"M0 {block}: duplicate or missing forecasts")
    return t


def model_qual(inst: Path, par_both: dict, par_s1: dict) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    frame_q = read_parquet(QT / "frame.parquet")
    frame_q["match_id"] = frame_q["match_id"].astype(str)
    frame_q = frame_q.set_index("match_id")
    main = read_parquet(inst / "model_frame.parquet", columns=["match_id", "season"])
    fx = F.FrameIndex(main.astype({"match_id": str}))
    p4 = _m0_table("qual", TEST, SC.sha256_file(inst / "model_frame.parquet"), fx.n_train)
    ids = p4.index
    info = frame_q.loc[ids, ["tour", "season", "tournament_date"]].copy()
    z, filled = _speed(QT / "speed.parquet", ids, info["tour"])
    q_full, _ = CMP.forecasts(p4, info, {int(k): v for k, v in par_both.items()}, z, ids)
    q_s1, _ = CMP.forecasts(p4, info, {int(k): v for k, v in par_s1.items()}, None, ids)
    out = pd.DataFrame({"model_logit_full": SC.lg(q_full), "model_logit_s1": SC.lg(q_s1),
                        "model_eta16": SC.lg(p4.mean(axis=1).to_numpy()), "spd": z.to_numpy(float),
                        "spd_filled": ids.isin(filled), "model_seeds": 4,
                        "model_source": "qualifying_targets M0 fits"}, index=ids)
    facts = {"fits": "data/studies/qualifying_targets/local/M0__<Y>__seed<k>.npz, block qual, seasons 2025-2026, seeds "
                     "0-3 (checked: the instance frame's SHA-256 and the training shape 2013..Y-1 of main draws only)",
             "calibration": "the instance's main-draw slope and stage 2 (the same parameters as the main draw)",
             "speed_column": "data/studies/qualifying_targets/speed.parquet (spd_L_B)",
             "matches": int(len(ids)), "speed_filled_with_0_men": int(len(filled))}
    return out, facts, frame_q.loc[ids]


def diff_inputs(inst: Path) -> list[str]:
    """The model's 48 non-price, non-context inputs (pairs as A - B), as unpriced_leads/screen.py's diff_input_names
    lists them, read from the live instance's input list."""
    d = json.loads((inst / "model_inputs.json").read_text(encoding="utf-8"))["inputs"]
    out = []
    for x in d:
        n = x["name"]
        if n == "odds_logit" or x["kind"] == "context":
            continue
        stem = n[:-2] if x["kind"] == "pair" else n
        if stem not in out:
            out.append(stem)
    return out


def inputs_table(names: list[str], frames: list[pd.DataFrame]) -> pd.DataFrame:
    parts = []
    for f in frames:
        g = pd.DataFrame(index=f.index)
        for n in names:
            if f"in_{n}" in f.columns:
                g[n] = f[f"in_{n}"].to_numpy(float)
            else:
                g[n] = f[f"in_{n}_a"].to_numpy(float) - f[f"in_{n}_b"].to_numpy(float)
        parts.append(g)
    out = pd.concat(parts)
    out.index.name = "match_id"
    return out


# ------------------------------------------------------------------------------------------------

def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    inst = instance_folder()
    facts: dict = {"generated_at": dt.datetime.now().isoformat(timespec="seconds"), "instance": inst.name,
                   "window": [FIRST_DAY, LAST_DAY], "window_day": "the match clock's obs, floored (timing.parquet)",
                   "inputs": {"stage0": str(STAGE0.relative_to(ROOT)), "stage0_sha256": sha256_file(STAGE0),
                              "timing_sha256": sha256_file(TIMING),
                              "instance_frame_sha256": sha256_file(inst / "model_frame.parquet")}}
    log("matches")
    s, counts = window_matches()
    facts["matches"] = counts
    log(f"  {len(s):,} matches kept")

    log("tour level: the main draw's close (rule 2026-10-21) and the instance's input")
    tm, fm = tour_main_prices(inst)
    facts["tour_main_prices"] = fm
    tq = tour_qual_prices()

    log("Challengers: TennisExplorer's lower-level pages")
    pages, files = te_lower_pages()
    ch = s[s["level_group"] == "challenger"]
    lk, how = link_challengers(ch, pages)
    lk.to_parquet(OUT / "challenger_link.parquet", index=False)
    odds = te_lower_odds(set(lk["te_id"]))
    pr = te_lower_prices(pages[pages["te_id"].isin(lk["te_id"])], odds)
    facts["challenger_link"] = {"stage0_matches": int(len(ch)), "te_pages_men_challenger": int(len(pages)),
                                "te_files": files, **how,
                                "linked_after_checks": int(lk["linked"].sum())}
    log(f"  linked {int(lk['linked'].sum()):,} of {len(ch):,}")

    # prices into the population
    s["price_logit"], s["price_source"] = np.nan, "none"
    s["price_logit_instance"], s["price_n_books"], s["price_lead_hours"] = np.nan, np.nan, np.nan
    s["te_pin_shown"], s["te_pin_untimed"] = False, False
    m = s.merge(tm, on="match_id", how="left", validate="one_to_one")
    is_tm = (s["level_group"].eq("tour") & s["draw"].eq("main")).to_numpy() & m["p_close"].notna().to_numpy()
    s.loc[is_tm, "price_logit"] = SC.lg(m.loc[is_tm, "p_close"].to_numpy(float))
    s.loc[is_tm, "price_source"] = m.loc[is_tm, "close_source"].to_numpy()
    s.loc[is_tm, "price_logit_instance"] = SC.lg(m.loc[is_tm, "p_instance"].to_numpy(float))
    s["in_frame"] = m["p_instance"].notna().to_numpy()
    m = s.merge(tq, on="match_id", how="left", validate="one_to_one")
    is_tq = (s["level_group"].eq("tour") & s["draw"].eq("qualifying")).to_numpy() & \
        np.isfinite(m["p_close"].to_numpy(float))
    s.loc[is_tq, "price_logit"] = SC.lg(m.loc[is_tq, "p_close"].to_numpy(float))
    s.loc[is_tq, "price_source"] = m.loc[is_tq, "close_source"].to_numpy()
    s["in_qual_prices"] = m["close_source"].notna().to_numpy()
    j = s[["match_id"]].merge(lk[lk["linked"]][["match_id", "te_id", "a_is_p2", "how"]], on="match_id", how="left") \
        .merge(pr, on="te_id", how="left")
    is_ch = s["level_group"].eq("challenger").to_numpy() & np.isfinite(j["p1_logit"].to_numpy(float))
    sign = np.where(j["a_is_p2"].fillna(False).astype(bool).to_numpy(), -1.0, 1.0)
    s.loc[is_ch, "price_logit"] = (sign * j["p1_logit"].to_numpy(float))[is_ch]
    s.loc[is_ch, "price_source"] = j.loc[is_ch, "te_source"].to_numpy()
    s.loc[is_ch, "price_n_books"] = j.loc[is_ch, "n_books_ok"].to_numpy(float)
    s.loc[is_ch, "price_lead_hours"] = j.loc[is_ch, "price_lead_hours"].to_numpy(float)
    s.loc[is_ch, "te_pin_shown"] = j.loc[is_ch, "pin_shown"].fillna(False).astype(bool).to_numpy()
    s.loc[is_ch, "te_pin_untimed"] = j.loc[is_ch, "pin_untimed"].fillna(False).astype(bool).to_numpy()
    s["te_link"] = j["how"].fillna("").to_numpy()
    s["priced"] = np.isfinite(s["price_logit"].to_numpy(float))

    log("the model: main draw (the instance's fits)")
    mm, fmm, frame_main = model_main(inst)
    facts["model_main"] = fmm
    log("the model: qualifying (the qualifying study's M0 fits)")
    pb = {int(k): v for k, v in fmm["params_both_stages"].items()}
    ps = {int(k): v for k, v in fmm["params_stage1"].items()}
    mq, fmq, frame_q = model_qual(inst, pb, ps)
    facts["model_qual"] = fmq
    mod = pd.concat([mm, mq])
    if mod.index.duplicated().any():
        raise RuntimeError("a match has two model forecasts")
    j = s[["match_id"]].join(mod, on="match_id")
    for c in ("model_logit_full", "model_logit_s1", "model_eta16", "spd"):
        s[c] = j[c].to_numpy(float)
    s["spd_filled"] = j["spd_filled"].fillna(False).astype(bool).to_numpy()
    s["model_seeds"] = j["model_seeds"].fillna(0).astype(int).to_numpy()
    s["model_source"] = j["model_source"].fillna("").to_numpy()
    s["has_model"] = np.isfinite(s["model_logit_full"].to_numpy(float))
    # the frame's result equals Stage 0's (both orientations are Stage 0's side A)
    fy = read_parquet(inst / "model_frame.parquet", columns=["match_id", "a_won"]).astype({"match_id": str})
    qy = frame_q["a_won"] if "a_won" in frame_q.columns else pd.Series(dtype=float)
    yy = pd.concat([fy.set_index("match_id")["a_won"], qy]).astype(float)
    jj = s[["match_id", "a_won"]].join(yy.rename("a_won_frame"), on="match_id")
    both = jj["a_won_frame"].notna()
    facts["result_check_frame_vs_stage0"] = {"matches": int(both.sum()),
                                             "equal": int((jj.loc[both, "a_won"].astype(float)
                                                           == jj.loc[both, "a_won_frame"]).sum())}

    log("the model's non-price inputs (outcome-free)")
    names = diff_inputs(inst)
    it = inputs_table(names, [frame_main, frame_q])
    it = it[it.index.isin(s["match_id"])]
    it.reset_index().to_parquet(OUT / "model_inputs.parquet", index=False)
    facts["model_inputs"] = {"names": names, "count": len(names), "rows": int(len(it)),
                             "rule": "unpriced_leads/screen.py's 48 non-price, non-context inputs, pairs as A - B"}

    s["season"] = s["year"].astype(int)
    keep = ["match_id", "date", "tournament_date", "season", "half", "week", "block", "tournament_id", "tournament_name",
            "level", "level_group", "draw", "round", "round_order", "surface", "indoor", "best_of", "player_a_id",
            "player_b_id", "a_won", "finished", "status", "status_detail", "priced", "price_logit", "price_source",
            "price_logit_instance", "price_n_books", "price_lead_hours", "te_pin_shown", "te_pin_untimed", "te_link",
            "in_frame", "in_qual_prices", "has_model", "model_logit_full", "model_logit_s1", "model_eta16",
            "model_seeds", "model_source", "spd", "spd_filled", "exact"]
    pop = s[keep].sort_values(["date", "match_id"]).reset_index(drop=True)
    pop.to_parquet(OUT / "population.parquet", index=False)
    facts["counts"] = counts_table(pop)
    facts["population_sha256"] = sha256_file(OUT / "population.parquet")
    write_json(OUT / "population_facts.json", facts)
    log(f"written {OUT.relative_to(ROOT)}: {len(pop):,} rows")
    return facts


def counts_table(pop: pd.DataFrame) -> dict:
    """Matches, finished and retired, priced, with the model: by level group, draw and half-year."""
    g = pop.groupby(["level_group", "draw", "half"])
    t = pd.DataFrame({"matches": g.size(), "finished": g["finished"].sum(),
                      "retired": g["finished"].apply(lambda x: int((~x).sum())), "priced": g["priced"].sum(),
                      "priced_and_model": g.apply(lambda d: int((d["priced"] & d["has_model"]).sum()))})
    by = {f"{a}|{b}|{c}": {k: int(v) for k, v in r.items()} for (a, b, c), r in t.iterrows()}
    src = pop[pop["priced"]].groupby(["level_group", "draw", "price_source"]).size()
    return {"by_group_draw_half": by,
            "price_source": {f"{a}|{b}|{c}": int(v) for (a, b, c), v in src.items()}}


def main() -> int:
    facts = build()
    print(json.dumps({"matches": facts["matches"]["left_out"], "challenger_link": {
        k: v for k, v in facts["challenger_link"].items() if k != "te_files"}}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
