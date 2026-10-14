"""Role 04 of the lower_level_evidence team: the incoming lower-level data, and how much of it touches the players the
current best model forecasts.

The question (docs/studies/lower_level_evidence/team/04_incoming.md): what lower-level data is coming, in what grain,
how much of it touches the model's players, and what must happen before it can reach a model input.

What it computes, all on the frozen reference's Stage 0 (common.STAGE0_DIR; --stage0-dir for a candidate):
    census       tour x bucket x year, 2018-2026: matches, with a box score, results only; and how many are "relevant":
                   main365    a player also played a MAIN match within +-365 days (the brief's definition)
                   frame365   a player plays a model-frame match in the 365 days after it (long-memory inputs)
                   frame28    a player plays a model-frame match in the 28 days after it (two-week form inputs)
                 (the 28/365-day windows are the input-data audit's, docs/studies/input_data_audit/README.md:229)
    targets      the gap downloads' frozen target lists (data/studies/gap_downloads/*_matches.csv[.gz]) plus the P7
                 gaps not yet frozen (itf_detail, itf_points_2025_2026), derived from the data map's match table with
                 the gap select of src/ingest/point_sources/sofascore_editions.py:235; each target linked to Stage 0 by
                 tour, surname pair and nearest tournament date (<= 10 days; <= 45 days for TML's misdated rows), the
                 surname rule of src/eda/data_map/measure.py:96
    cells        the data map's coverage cells (data/studies/data_map/coverage.json) against Stage 0, matched on
                 (tour, level, year): what the map holds that Stage 0 does not read
    newresults   the map's matches with no Stage 0 counterpart at the lower levels (TennisLive listings, WTA site,
                 API-Tennis), with their players matched to Stage 0 ids by full name where the name is unique
    dose         model-frame rows (2013-2026) by tour and season: how much of each player's previous-365-day (and
                 28-day) box-score history the ITF box scores of P7 would add
    translation  player-seasons with three or more matches at two levels (ITF and MAIN, ITF and CH, CH and MAIN),
                 today and once P7 lands: the anchors a same-player level translation could be estimated on
    progress     the running collectors' state, read from their receipts and run logs (no HTTP)

No outcome is read: no winner, score or box-score value; `has_box` (coverage) and dates only. Walkovers are counted
as matches (their status is not read). Holdout matches (2025-2026) are counted, never their outcomes.

Writes data/studies/lower_level_evidence/incoming/: census.csv, targets.csv, cells.csv, newresults.csv, dose.csv,
translation_sample.csv, clock.csv, packages_2026-10-09.csv (a dated snapshot written by hand), progress.json, summary.json.

Run: ./python.sh src/eda/lower_level_evidence/incoming.py [--stage0-dir <folder>] [--out <folder>] [--skip-progress]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as C  # noqa: E402

OUT = C.OUT / "incoming"
GAPDL = ROOT / "data" / "studies" / "gap_downloads"
MAP_MATCHES = ROOT / "data" / "studies" / "data_map" / "matches.parquet"
MAP_COVERAGE = ROOT / "data" / "studies" / "data_map" / "coverage.json"
YEARS = range(2018, 2027)
DEV = range(2018, 2025)                       # development seasons: outcomes allowed, but none is read here anyway
LOWER4 = ("ITF", "ITFQ", "CH", "CHQ")         # the brief's lower levels
TOUR_MAP = {"atp": "M", "wta": "W"}
GRAIN_RANK = {"result": 1, "stats": 2, "point": 3, "shot": 4}

# The gaps, their frozen target lists and the package that fills them (docs/studies/gap_downloads/collection-plan.md).
GAPS = [  # (gap, source, package, file or None = derive from the map with `select`, select, what it adds)
    ("challenger_points_2025", "sofascore", "P6", "sofascore_challenger_points_2025_matches.csv", None, "point"),
    ("wta125_points_2019_2026", "sofascore", "P6", "sofascore_wta125_points_2019_2026_matches.csv", None, "point"),
    ("challenger_points_2022_2024", "sofascore", "P6", "sofascore_challenger_points_2022_2024_matches.csv", None, "point"),
    ("wta_2018_points", "sofascore", "P6", "sofascore_wta_2018_points_matches.csv", None, "point"),
    ("challenger_points_2018_2021", "sofascore", "P6", "sofascore_challenger_points_2018_2021_matches.csv", None, "point"),
    ("challenger_points_2018_2021", "tennislive", "P5", "tennislive_challenger_points_2018_2021_matches.csv.gz", None,
     "point (partial)"),
    ("challenger_points_2022_2024", "tennislive", "P5", "tennislive_challenger_points_2022_2024_matches.csv.gz", None,
     "point (partial)"),
    ("wta_2018_points", "tennislive", "P5", "tennislive_wta_2018_points_matches.csv.gz", None, "point (partial)"),
    ("qualifying_points_2018_2026", "tennislive", "P5", "tennislive_qualifying_points_2018_2026_matches.csv.gz", None,
     "point (partial)"),
    ("itf_detail", "sofascore", "P7", None,
     {"tours": ["M", "W"], "levels": ["ITF"], "years": list(range(2018, 2025)), "below": "stats"}, "stats + point"),
    ("itf_points_2025_2026", "sofascore", "P7", None,
     {"tours": ["M", "W"], "levels": ["ITF"], "years": [2025, 2026], "below": "point"}, "point (+ stats after June 2026)"),
]

# Yields measured on samples by the gap-sources research and the downloads (shares of targets, with their evidence).
YIELDS = {
    ("itf_detail", "sofascore"): {"stats": (82, 84), "point_complete": (78, 84),
                                  "evidence": "docs/research/gap-sources/README.md:76 (84 sampled ITF 2018-24 matches)"},
    ("challenger_points_2025", "sofascore"): {"stats": (60, 60), "point_complete": (58, 60),
                                              "evidence": "docs/studies/gap_downloads/README.md:116-121 (trial, 60 targets)"},
    ("challenger_points_2018_2021", "tennislive"): {"point_any": (11, 14), "stats": (12, 14),
                                                   "evidence": "tennislive_gaps_summary.json (14 career pages held)"},
}

_PARTICLES = {"jr", "sr", "ii", "iii", "iv", "de", "da", "van", "von", "del", "der", "la", "le", "di", "dos"}


# ------------------------------------------------------------------------------------------------ names and keys
def _words(name) -> list[str]:
    """Lower-case ASCII words of two letters or more, particles dropped (src/eda/data_map/measure.py:96-115)."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return []
    text = "".join(ch for ch in unicodedata.normalize("NFKD", str(name)) if not unicodedata.combining(ch)).lower()
    words = [w for w in re.split(r"[^a-z]+", text) if len(w) >= 2]
    return [w for w in words if w not in _PARTICLES] or words


def surname(name) -> str:
    w = _words(name)
    return w[-1] if w else ""


def fullkey(name) -> str:
    """Order-free full-name key: 'Carlos Alcaraz' and 'Alcaraz Carlos' agree."""
    return " ".join(sorted(_words(name)))


def pair(a: pd.Series, b: pd.Series) -> pd.Series:
    a, b = a.fillna("").astype(str), b.fillna("").astype(str)
    lo = pd.Series(np.where(a <= b, a, b), index=a.index)
    hi = pd.Series(np.where(a <= b, b, a), index=a.index)
    return (lo + "|" + hi).where((a != "") & (b != ""), None)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ Stage 0
def load_stage0(stage0_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 0's matches (no outcome column) and the player rows: two per match, with names."""
    m = C.load_matches(stage0_dir, columns=["match_id", "tour", "year", "map_level", "tournament_date", "has_box",
                                            "player_a_id", "player_b_id"])
    m["T"] = m["tour"].map(TOUR_MAP)
    m["d"] = pd.to_datetime(m["tournament_date"]).astype("datetime64[ns]")
    p = C.load_players(stage0_dir, columns=["match_id", "player_id", "player_name"])
    p = p.drop_duplicates(["match_id", "player_id"])
    names = p.set_index(["match_id", "player_id"])["player_name"]
    m["name_a"] = names.reindex(list(zip(m["match_id"], m["player_a_id"]))).to_numpy()
    m["name_b"] = names.reindex(list(zip(m["match_id"], m["player_b_id"]))).to_numpy()
    rows = pd.concat([
        m[["match_id", "player_a_id", "d", "bucket", "T", "year", "has_box"]].rename(columns={"player_a_id": "player_id"}),
        m[["match_id", "player_b_id", "d", "bucket", "T", "year", "has_box"]].rename(columns={"player_b_id": "player_id"}),
    ], ignore_index=True)
    return m, rows


def frame_rows(m: pd.DataFrame) -> pd.DataFrame:
    """The model frame's matches (no outcome, no price), as player rows with Stage 0's player ids."""
    f = C.load_frame(columns=["match_id", "tour", "season", "tournament_date"])
    f = f.merge(m[["match_id", "player_a_id", "player_b_id"]], on="match_id", how="left")
    missing = int(f["player_a_id"].isna().sum())
    if missing:
        raise SystemExit(f"{missing} frame matches have no Stage 0 row")
    f["d"] = pd.to_datetime(f["tournament_date"]).astype("datetime64[ns]")
    f["T"] = f["tour"].map(lambda t: TOUR_MAP.get(str(t).lower(), str(t)))
    return pd.concat([
        f[["match_id", "player_a_id", "d", "season", "T"]].rename(columns={"player_a_id": "player_id"}).assign(side="a"),
        f[["match_id", "player_b_id", "d", "season", "T"]].rename(columns={"player_b_id": "player_id"}).assign(side="b"),
    ], ignore_index=True)


def relevance(rows: pd.DataFrame, frows: pd.DataFrame) -> pd.DataFrame:
    """Per player row of the lower levels: main365, frame365, frame28 (see the module's docstring)."""
    low = rows[rows["bucket"].isin(C.LOWER)].copy()
    low["_i"] = np.arange(len(low))
    main = rows.loc[rows["bucket"].eq("MAIN"), ["player_id", "d"]].rename(columns={"d": "d_main"})
    fr = frows[["player_id", "d"]].rename(columns={"d": "d_frame"})
    out = low.sort_values("d")
    near = pd.merge_asof(out[["_i", "player_id", "d"]], main.sort_values("d_main"), left_on="d", right_on="d_main",
                         by="player_id", direction="nearest", tolerance=pd.Timedelta(days=365))
    fwd = pd.merge_asof(out[["_i", "player_id", "d"]], fr.sort_values("d_frame"), left_on="d", right_on="d_frame",
                        by="player_id", direction="forward", tolerance=pd.Timedelta(days=365))
    near = near.set_index("_i")["d_main"]
    fwd = fwd.set_index("_i")["d_frame"]
    low["main365"] = near.reindex(low["_i"]).notna().to_numpy()
    nxt = pd.to_datetime(pd.Series(fwd.reindex(low["_i"]).to_numpy()))
    days = (nxt - low["d"].reset_index(drop=True)).dt.days
    low["frame365"] = nxt.notna().to_numpy()
    low["frame28"] = days.le(28).to_numpy()            # NaT -> NaN -> False
    return low.drop(columns="_i")


def check_relevance(low: pd.DataFrame, rows: pd.DataFrame, frows: pd.DataFrame, n: int = 300, seed: int = 20261009) -> dict:
    """Recount the three flags by brute force on a seeded sample of lower-level player rows."""
    rng = np.random.default_rng(seed)
    sample = low.iloc[rng.choice(len(low), size=min(n, len(low)), replace=False)]
    main = rows[rows["bucket"].eq("MAIN")].groupby("player_id")["d"].apply(lambda s: s.to_numpy())
    fr = frows.groupby("player_id")["d"].apply(lambda s: s.to_numpy())
    wrong = 0
    for _, r in sample.iterrows():
        dm = main.get(r["player_id"], np.array([], dtype="datetime64[ns]"))
        df = fr.get(r["player_id"], np.array([], dtype="datetime64[ns]"))
        d = np.datetime64(r["d"], "ns")
        main365 = bool(len(dm)) and bool((np.abs((dm - d).astype("timedelta64[D]").astype(int)) <= 365).any())
        ahead = (df - d).astype("timedelta64[D]").astype(int) if len(df) else np.array([], dtype=int)
        frame365 = bool(((ahead >= 0) & (ahead <= 365)).any())
        frame28 = bool(((ahead >= 0) & (ahead <= 28)).any())
        wrong += int((main365, frame365, frame28) != (bool(r["main365"]), bool(r["frame365"]), bool(r["frame28"])))
    if wrong:
        raise SystemExit(f"relevance check: {wrong} of {len(sample)} sampled player rows recount differently")
    return {"sampled": len(sample), "wrong": wrong, "seed": seed}


def census(m: pd.DataFrame, low: pd.DataFrame) -> pd.DataFrame:
    """Tour x bucket x year (2018-2026): matches, box scores, and relevant matches and player rows."""
    sub = m[m["year"].isin(YEARS) & m["bucket"].isin(C.LOWER)]
    base = sub.groupby(["T", "bucket", "year"]).agg(matches=("match_id", "size"), with_box=("has_box", "sum"))
    base["results_only"] = base["matches"] - base["with_box"]
    lw = low[low["year"].isin(YEARS)]
    per_match = lw.groupby("match_id").agg(main365=("main365", "sum"), frame365=("frame365", "sum"),
                                           frame28=("frame28", "sum"))
    sub = sub.join(per_match, on="match_id")
    for flag in ("main365", "frame365", "frame28"):
        sub[f"{flag}_any"] = sub[flag].gt(0)
        sub[f"{flag}_both"] = sub[flag].ge(2)
    grp = sub.groupby(["T", "bucket", "year"])
    for flag in ("main365", "frame365", "frame28"):
        base[f"m_{flag}"] = grp[f"{flag}_any"].sum()
        base[f"m_{flag}_both"] = grp[f"{flag}_both"].sum()
        base[f"pr_{flag}"] = grp[flag].sum()
        ro = sub[~sub["has_box"]].groupby(["T", "bucket", "year"])
        base[f"ro_m_{flag}"] = ro[f"{flag}_any"].sum()
        base[f"ro_pr_{flag}"] = ro[flag].sum()
    return base.fillna(0).astype("int64").reset_index()


# ------------------------------------------------------------------------------------------------ targets
def load_target_lists() -> pd.DataFrame:
    """Every gap's targets: frozen lists as written by the collectors, the P7 gaps derived from the map."""
    parts = []
    mapm = None
    for gap, source, pkg, fname, select, adds in GAPS:
        if fname:
            t = pd.read_csv(GAPDL / fname, usecols=["gap", "uid", "tour", "level", "draw", "year", "d", "tname",
                                                     "name1", "name2", "creator", "best", "sources"],
                            parse_dates=["d"], low_memory=False)
            frozen = f"frozen: {fname}"
        else:
            if mapm is None:
                mapm = pd.read_parquet(MAP_MATCHES)
                mapm["d"] = pd.to_datetime(mapm["d"]).astype("datetime64[ns]")
            sel = (mapm["tour"].isin(select["tours"]) & mapm["level"].isin(select["levels"])
                   & mapm["year"].isin(select["years"])
                   & (mapm["best"].map(GRAIN_RANK) < GRAIN_RANK[select["below"]]))
            t = mapm.loc[sel, ["uid", "tour", "level", "draw", "year", "d", "tname", "name1", "name2", "creator",
                               "best", "sources"]].copy()
            t.insert(0, "gap", gap)
            frozen = "derived from the map's match table (not frozen yet)"
        t["source"], t["package"], t["adds"], t["target_list"] = source, pkg, adds, frozen
        # Stage 0 is built from Sackmann's and Tennis My Life's files only (stage0_build.py:91-103): a match whose
        # map record names either of them is in Stage 0, by the map's own linker
        t["s0_by_sources"] = t["sources"].fillna("").str.contains(r"(?:^|;)(?:sackmann|tml)(?:;|$)")
        parts.append(t)
    return pd.concat(parts, ignore_index=True)


def link_to_stage0(t: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Each target's Stage 0 match: same tour and surname pair, nearest tournament date within 10 days (any level:
    API-Tennis files some Challenger qualifying as main draw); else within 45 days (TML files Irving 2018 under
    Dallas's date: src/ingest/point_sources/tennislive_gaps.py:26)."""
    mm = m[m["year"].ge(2017)].copy()
    mm["pair"] = pair(mm["name_a"].map(surname), mm["name_b"].map(surname))
    t = t.copy()
    t["_i"] = np.arange(len(t))
    t["pair"] = pair(t["name1"].map(surname), t["name2"].map(surname))
    j = t[["_i", "tour", "pair", "d"]].merge(
        mm[["match_id", "T", "pair", "d", "bucket", "has_box"]].rename(columns={"T": "tour", "d": "d0"}),
        on=["tour", "pair"], how="inner")
    j["dd"] = (j["d"] - j["d0"]).dt.days.abs()
    j = j[j["dd"].le(45)].sort_values(["_i", "dd"]).drop_duplicates("_i")
    t = t.merge(j[["_i", "match_id", "dd", "bucket", "has_box"]], on="_i", how="left")
    t["link"] = np.select([t["match_id"].isna(), t["dd"].le(10)], ["not in Stage 0", "linked"], "linked, date off")
    return t.drop(columns=["_i"])


def targets_table(t: pd.DataFrame, low: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """Gap x source x tour x level x year: targets, Stage 0 matches they reach, and how many of those are relevant."""
    flags = rows[["match_id"]].drop_duplicates().merge(
        low.groupby("match_id")[["main365", "frame365", "frame28"]].sum().reset_index(), on="match_id",
        how="left").fillna(0)
    t = t.merge(flags, on="match_id", how="left")
    out = []
    for key, g in t.groupby(["package", "gap", "source", "adds", "target_list", "tour", "level", "year"]):
        s0 = g.dropna(subset=["match_id"]).drop_duplicates("match_id")
        out.append(dict(zip(["package", "gap", "source", "adds", "target_list", "tour", "level", "year"], key),
                        targets=len(g), linked=int(g["link"].eq("linked").sum()),
                        linked_date_off=int(g["link"].eq("linked, date off").sum()),
                        not_in_stage0=int(g["link"].eq("not in Stage 0").sum()),
                        in_stage0_by_sources=int(g["s0_by_sources"].sum()),
                        not_in_stage0_by_sources=int((~g["s0_by_sources"]).sum()),
                        unlinked_but_in_stage0=int((g["link"].eq("not in Stage 0") & g["s0_by_sources"]).sum()),
                        stage0_matches=len(s0), stage0_with_box=int(s0["has_box"].fillna(False).astype(bool).sum()),
                        rel_main365=int(s0["main365"].gt(0).sum()), rel_frame365=int(s0["frame365"].gt(0).sum()),
                        rel_frame28=int(s0["frame28"].gt(0).sum()),
                        pr_main365=int(s0["main365"].sum()), pr_frame365=int(s0["frame365"].sum())))
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ the map's cells
def cells_table(m: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The map's coverage cells against Stage 0, on (tour, level, year), lower levels 2018-2026."""
    cov = json.loads(MAP_COVERAGE.read_text(encoding="utf-8"))
    c = pd.DataFrame(cov["cells"])
    c = c[c["level"].isin(["ITF", "ITFQ", "CH", "CHQ", "TQ", "GSQ"]) & c["year"].isin(list(YEARS))].copy()
    c["map_stats_plus"] = c["disk_stats"] + c["disk_point"] + c["disk_shot"]
    c["map_point_plus"] = c["disk_point"] + c["disk_shot"]
    c["public_point_plus"] = c["best_point"] + c["best_shot"]
    s0 = (m[m["year"].isin(YEARS)].groupby(["T", "map_level", "year"])
          .agg(stage0_matches=("match_id", "size"), stage0_with_box=("has_box", "sum")).reset_index()
          .rename(columns={"T": "tour", "map_level": "level"}))
    out = c[["tour", "level", "year", "matches", "map_stats_plus", "map_point_plus", "public_point_plus",
             "status_downloading", "missing_estimate"]].rename(columns={"matches": "map_matches"})
    out = out.merge(s0, on=["tour", "level", "year"], how="outer").fillna(0)
    for col in out.columns[3:]:
        out[col] = out[col].astype("int64")
    out["map_minus_stage0_matches"] = out["map_matches"] - out["stage0_matches"]
    out["map_minus_stage0_box"] = out["map_stats_plus"] - out["stage0_with_box"]
    # what each source adds, per cell (the map's per_source list)
    ps = pd.DataFrame(cov["per_source"])
    ps = ps[ps["level"].isin(["ITF", "ITFQ", "CH", "CHQ"]) & ps["year"].isin(list(YEARS))]
    src = (ps.groupby(["src", "grain", "status"])["matches"].sum().reset_index()
           .sort_values("matches", ascending=False))
    meta = {"generated_at": cov.get("generated_at"), "window": cov.get("window"),
            "per_source_lower_levels": src.to_dict(orient="records")}
    return out.sort_values(["tour", "level", "year"]), meta


# ------------------------------------------------------------------------------------------------ new results
def new_results(m: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """The map's lower-level matches with no Stage 0 counterpart (by tour, surname pair, date within 10 days), and
    whether a player is a Stage 0 player who also plays MAIN within 365 days (name -> id where the name is unique)."""
    mapm = pd.read_parquet(MAP_MATCHES, columns=["uid", "tour", "level", "year", "d", "name1", "name2", "creator",
                                                 "sources"])
    mapm["d"] = pd.to_datetime(mapm["d"]).astype("datetime64[ns]")
    mapm = mapm[mapm["level"].isin(C.LOWER) & mapm["year"].isin(list(YEARS))].copy()
    mapm["s0_by_sources"] = mapm["sources"].fillna("").str.contains(r"(?:^|;)(?:sackmann|tml)(?:;|$)")
    mm = m[m["year"].ge(2017) & m["bucket"].isin(C.LOWER)].copy()
    mm["pair"] = pair(mm["name_a"].map(surname), mm["name_b"].map(surname))
    mapm["pair"] = pair(mapm["name1"].map(surname), mapm["name2"].map(surname))
    mapm["_i"] = np.arange(len(mapm))
    j = mapm[["_i", "tour", "pair", "d"]].merge(mm[["T", "pair", "d"]].rename(columns={"T": "tour", "d": "d0"}),
                                                on=["tour", "pair"], how="inner")
    dd = (j["d"] - j["d0"]).dt.days.abs()
    mapm["in_stage0"] = mapm["_i"].isin(j.loc[dd.le(10), "_i"])
    # a pair Stage 0 holds 11-45 days away: most likely the same match misdated by one file (TML's Irving 2018 under
    # Dallas's date), not a new one
    mapm["near_dup"] = ~mapm["in_stage0"] & mapm["_i"].isin(j.loc[dd.le(45), "_i"])
    new = mapm[~mapm["in_stage0"]].copy()
    # names -> Stage 0 ids, unique names only
    names = pd.concat([m[["name_a", "player_a_id", "T"]].set_axis(["name", "player_id", "tour"], axis=1),
                       m[["name_b", "player_b_id", "T"]].set_axis(["name", "player_id", "tour"], axis=1)])
    names = names.dropna().drop_duplicates()
    names["key"] = names["name"].map(fullkey)
    ids = names.drop_duplicates(["tour", "key", "player_id"]).groupby(["tour", "key"])["player_id"]
    unique = ids.first()[ids.nunique().eq(1)]
    main = rows.loc[rows["bucket"].eq("MAIN"), ["player_id", "d"]].rename(columns={"d": "d_main"}).sort_values("d_main")
    for side, col in (("1", "name1"), ("2", "name2")):
        new[f"pid{side}"] = unique.reindex(list(zip(new["tour"], new[col].map(fullkey)))).to_numpy()
        q = new[[f"pid{side}", "d"]].rename(columns={f"pid{side}": "player_id"}).reset_index()
        q = q.dropna(subset=["player_id"]).sort_values("d")
        near = pd.merge_asof(q, main, left_on="d", right_on="d_main", by="player_id", direction="nearest",
                             tolerance=pd.Timedelta(days=365)).set_index("index")["d_main"]
        new[f"main365_{side}"] = near.reindex(new.index).notna()
    new["known_player"] = new["pid1"].notna() | new["pid2"].notna()
    new["main365_any"] = new["main365_1"] | new["main365_2"]
    new["new_by_sources"] = ~new["s0_by_sources"]
    # the WTA API's box scores already on disk (dataset wta_api, measured as wta_box) for a match Stage 0 lacks
    new["wta_box_on_disk"] = new["new_by_sources"] & new["sources"].fillna("").str.contains(r"(?:^|;)wta_box(?:;|$)")
    out = (new.groupby(["tour", "level", "year", "creator"])
           .agg(unlinked=("uid", "size"), new_by_sources=("new_by_sources", "sum"), near_duplicates=("near_dup", "sum"),
                with_a_stage0_player=("known_player", "sum"), rel_main365=("main365_any", "sum"),
                wta_box_on_disk=("wta_box_on_disk", "sum")).reset_index())
    new_src = new[new["new_by_sources"]]
    rel = (new_src.groupby(["tour", "level", "year", "creator"])
           .agg(new_known_player=("known_player", "sum"), new_rel_main365=("main365_any", "sum")).reset_index())
    out = out.merge(rel, on=["tour", "level", "year", "creator"], how="left").fillna(0)
    tot = mapm.groupby(["tour", "level", "year"]).agg(map_matches=("uid", "size"), in_stage0=("in_stage0", "sum"),
                                                      in_stage0_by_sources=("s0_by_sources", "sum"))
    return out.merge(tot.reset_index(), on=["tour", "level", "year"], how="left")


# ------------------------------------------------------------------------------------------------ the dose
def dose(m: pd.DataFrame, rows: pd.DataFrame, frows: pd.DataFrame, t_linked: pd.DataFrame) -> pd.DataFrame:
    """Model-frame player rows: the previous 365 (and 28) days' history, by what the incoming data would change."""
    point_gap = set(t_linked.loc[t_linked["adds"].str.startswith("point") & t_linked["match_id"].notna()
                                 & t_linked["package"].isin(["P5", "P6"]), "match_id"])
    r = rows.copy()
    cats = {
        "box_any": r["has_box"],
        "p7_box": r["bucket"].eq("ITF") & r["year"].between(2018, 2024) & ~r["has_box"],
        "itf_ro_pre2018": r["bucket"].eq("ITF") & r["year"].lt(2018) & ~r["has_box"],
        "itfq_ro": r["bucket"].eq("ITFQ") & ~r["has_box"],
        "ch_chq_ro": r["bucket"].isin(["CH", "CHQ"]) & ~r["has_box"],
        "lower_any": r["bucket"].isin(C.LOWER),
        "ch_point_gap": r["match_id"].isin(point_gap) & r["bucket"].isin(["CH", "CHQ"]),
    }
    codes, uniq = pd.factorize(pd.concat([r["player_id"], frows["player_id"]], ignore_index=True))
    rc, fc = codes[:len(r)], codes[len(r):]
    rday = (r["d"] - pd.Timestamp("1970-01-01")).dt.days.to_numpy()
    fday = (frows["d"] - pd.Timestamp("1970-01-01")).dt.days.to_numpy()
    big = np.int64(100000)
    f = frows.copy()
    for name, mask in cats.items():
        keys = np.sort(rc[mask.to_numpy()].astype(np.int64) * big + rday[mask.to_numpy()])
        for w in (365, 28):
            hi = np.searchsorted(keys, fc.astype(np.int64) * big + fday, side="left")
            lo = np.searchsorted(keys, fc.astype(np.int64) * big + (fday - w), side="left")
            f[f"{name}_{w}"] = hi - lo
    f["p7_share_365"] = f["p7_box_365"] / (f["box_any_365"] + f["p7_box_365"]).replace(0, np.nan)
    for col in ("p7_box_365", "p7_box_28", "itf_ro_pre2018_365", "itfq_ro_365", "ch_point_gap_365", "ch_point_gap_28"):
        f[f"{col}_pos"] = f[col].gt(0)
    per_match = f.groupby("match_id").agg(
        T=("T", "first"), season=("season", "first"),
        p7_any_365=("p7_box_365_pos", "max"), p7_any_28=("p7_box_28_pos", "max"),
        itf_pre_any_365=("itf_ro_pre2018_365_pos", "max"), itfq_any_365=("itfq_ro_365_pos", "max"),
        chgap_any_365=("ch_point_gap_365_pos", "max"), chgap_any_28=("ch_point_gap_28_pos", "max"))
    g = per_match.groupby(["T", "season"])
    out = g.agg(frame_matches=("p7_any_365", "size"), rows_p7_365=("p7_any_365", "sum"), rows_p7_28=("p7_any_28", "sum"),
                rows_itf_pre2018_365=("itf_pre_any_365", "sum"), rows_itfq_365=("itfq_any_365", "sum"),
                rows_ch_point_gap_365=("chgap_any_365", "sum"), rows_ch_point_gap_28=("chgap_any_28", "sum"))
    pg = f.groupby(["T", "season"])
    out["player_rows"] = pg.size()
    out["mean_p7_share_365"] = pg["p7_share_365"].mean().round(4)
    out["players_p7_share_ge_25pct"] = pg["p7_share_365"].apply(lambda s: int((s >= 0.25).sum()))
    out["mean_box_365"] = pg["box_any_365"].mean().round(2)
    out["mean_p7_box_365"] = pg["p7_box_365"].mean().round(2)
    out["mean_lower_365"] = pg["lower_any_365"].mean().round(2)
    return out.reset_index()


# ------------------------------------------------------------------------------------------------ the clock
def clock_table(m: pd.DataFrame, timing: Path = C.TIMING) -> pd.DataFrame:
    """The timeline's dating of each level, 2018-2024 (default: the frozen reference's; a candidate passes its own with
    --timing): exact days, window widths and the best source."""
    t = pd.read_parquet(timing, columns=["match_id", "exact", "width_days", "best_source"])
    t = t.merge(m[["match_id", "T", "bucket", "year"]], on="match_id")
    t = t[t["year"].isin(list(DEV))]
    out = t.groupby(["T", "bucket"]).agg(matches=("match_id", "size"), exact_share=("exact", "mean"),
                                         width_median=("width_days", "median"), width_mean=("width_days", "mean"))
    top = (t.groupby(["T", "bucket"])["best_source"].agg(lambda s: "; ".join(
        f"{k} {v}" for k, v in s.value_counts().head(3).items())))
    out["best_sources_top3"] = top
    return out.round(3).reset_index()


# ------------------------------------------------------------------------------------------------ translation sample
def translation_sample(rows: pd.DataFrame) -> pd.DataFrame:
    """Player-seasons that could anchor a same-player, same-season level translation (the design of
    docs/studies/event_levels/README.md:107, at least three matches at each level): today (box scores held) and once
    P7 gives the ITF matches of 2018-2024 their box scores (counting matches; no box-score value is read)."""
    r = rows[rows["year"].between(2013, 2026)].copy()
    r["itf_box"] = r["bucket"].eq("ITF") & r["has_box"]
    r["itf_p7"] = r["bucket"].eq("ITF") & r["year"].between(2018, 2024) & ~r["has_box"]
    r["ch_box"] = r["bucket"].eq("CH") & r["has_box"]
    r["main_box"] = r["bucket"].eq("MAIN") & r["has_box"]
    ps = r.groupby(["T", "year", "player_id"])[["itf_box", "itf_p7", "ch_box", "main_box"]].sum()
    out = []
    for (tour, year), g in ps.groupby(level=["T", "year"]):
        itf_now, itf_after = g["itf_box"], g["itf_box"] + g["itf_p7"]
        out.append({"tour": tour, "year": year,
                    "itf_main_now": int(((itf_now >= 3) & (g["main_box"] >= 3)).sum()),
                    "itf_main_after_p7": int(((itf_after >= 3) & (g["main_box"] >= 3)).sum()),
                    "itf_ch_now": int(((itf_now >= 3) & (g["ch_box"] >= 3)).sum()),
                    "itf_ch_after_p7": int(((itf_after >= 3) & (g["ch_box"] >= 3)).sum()),
                    "ch_main_now": int(((g["ch_box"] >= 3) & (g["main_box"] >= 3)).sum())})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ progress
def progress() -> dict:
    """The collectors' state from their receipts and run logs (read only, no HTTP)."""
    res: dict = {"read_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    rec = ROOT / "data" / "raw" / "point_sources" / "sofascore_editions" / "_receipts.jsonl"
    if rec.exists():
        start = dt.datetime.fromisoformat("2026-10-08T19:42:00+00:00")       # P6's bulk run
        kinds: dict = {}
        last = None
        times = []
        for line in rec.open(encoding="utf-8"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = dt.datetime.fromisoformat(d["retrieved_at"])
            if t < start:
                continue
            name = d.get("name", "")
            k = name.split("/")[0] + ("/" + name.split("/")[-1] if name.startswith("events/") else "")
            kinds[f"{k}:{d.get('status')}"] = kinds.get(f"{k}:{d.get('status')}", 0) + 1
            times.append(t)
            last = t
        times.sort()
        hour = sum(1 for t in times if last and t >= last - dt.timedelta(hours=2)) / 2 if times else None
        res["p6_sofascore_since_bulk_start"] = {"by_kind_status": kinds, "requests": len(times),
                                                "last": last.isoformat() if last else None,
                                                "requests_per_hour_last_2h": hour}
    for name, path in (("gap_downloads_runs", GAPDL / "runs.jsonl"),
                       ("official_point_feeds_runs", ROOT / "data" / "studies" / "official_point_feeds" / "runs.jsonl")):
        if path.exists():
            lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
            res[name] = [{k: x.get(k) for k in ("source", "started_at", "finished_at", "stopped", "matches_selected")}
                         for x in lines[-4:]]
    tl = GAPDL / "tennislive_gaps_summary.json"
    if tl.exists():
        s = json.loads(tl.read_text(encoding="utf-8"))
        res["p5_tennislive"] = {"finished_at": s.get("finished_at"), "link_only": s.get("args", {}).get("link_only"),
                                "all": s.get("all"), "pages": s.get("pages")}
    return res


# ------------------------------------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0-dir", type=Path, default=C.STAGE0_DIR)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--skip-progress", action="store_true")
    ap.add_argument("--timing", type=Path, default=C.TIMING,
                    help="the match timeline that goes with the Stage 0 (default: the frozen reference's)")
    a = ap.parse_args()
    t0 = time.time()
    a.out.mkdir(parents=True, exist_ok=True)

    m, rows = load_stage0(a.stage0_dir)
    frows = frame_rows(m)
    low = relevance(rows, frows)
    check = check_relevance(low, rows, frows)
    print(f"relevance flags recounted by brute force: {check}", flush=True)
    cen = census(m, low)
    cen.to_csv(a.out / "census.csv", index=False)
    print(f"census: {len(cen)} rows ({time.time() - t0:.0f}s)", flush=True)

    t = link_to_stage0(load_target_lists(), m)
    tt = targets_table(t, low, rows)
    tt.to_csv(a.out / "targets.csv", index=False)
    print(f"targets: {len(t)} targets in {tt['gap'].nunique()} gaps ({time.time() - t0:.0f}s)", flush=True)

    cells, cmeta = cells_table(m)
    cells.to_csv(a.out / "cells.csv", index=False)
    nr = new_results(m, rows)
    nr.to_csv(a.out / "newresults.csv", index=False)
    print(f"cells and new results ({time.time() - t0:.0f}s)", flush=True)

    ds = dose(m, rows, frows, t)
    ds.to_csv(a.out / "dose.csv", index=False)
    ts = translation_sample(rows)
    ts.to_csv(a.out / "translation_sample.csv", index=False)
    clock_table(m, a.timing).to_csv(a.out / "clock.csv", index=False)
    print(f"dose and translation sample ({time.time() - t0:.0f}s)", flush=True)

    prog = {} if a.skip_progress else progress()
    if prog:
        (a.out / "progress.json").write_text(json.dumps(prog, indent=1, default=str), encoding="utf-8")

    dev = cen[cen["year"].isin(list(DEV)) & cen["bucket"].isin(LOWER4)]
    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "stage0_dir": str(Path(a.stage0_dir).resolve().relative_to(ROOT)) if str(a.stage0_dir).startswith(str(ROOT))
        else str(a.stage0_dir),
        "inputs": {"map_matches": {"path": str(MAP_MATCHES.relative_to(ROOT)), "sha256": sha256(MAP_MATCHES)},
                   "map_coverage": {"path": str(MAP_COVERAGE.relative_to(ROOT)), "sha256": sha256(MAP_COVERAGE),
                                    "generated_at": cmeta["generated_at"], "window": cmeta["window"]},
                   "target_lists": {f: sha256(GAPDL / f) for _, _, _, f, _, _ in GAPS if f}},
        "dev_2018_2024_lower4": {
            "by_tour_bucket": dev.groupby(["T", "bucket"])[["matches", "with_box", "results_only", "m_main365",
                                                             "ro_m_main365", "m_frame365", "ro_m_frame365",
                                                             "m_frame28", "ro_m_frame28"]].sum()
            .reset_index().to_dict(orient="records")},
        "targets_by_gap": tt.groupby(["package", "gap", "source"])[
            ["targets", "linked", "linked_date_off", "not_in_stage0", "in_stage0_by_sources",
             "not_in_stage0_by_sources", "unlinked_but_in_stage0", "stage0_matches", "stage0_with_box",
             "rel_main365", "rel_frame365", "rel_frame28"]].sum().reset_index().to_dict(orient="records"),
        "map_per_source_lower_levels": cmeta["per_source_lower_levels"],
        "yields_measured": {f"{k[0]}|{k[1]}": v for k, v in YIELDS.items()},
        "relevance_check": check,
        "seconds": round(time.time() - t0, 1),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f}s -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
