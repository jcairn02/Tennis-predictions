"""The leak-proof timeline: an earliest possible start (ES) and latest possible finish (LF) day for every match.

Inputs
    data/studies/predictability_diagnostic/stage0_matches.parquet   every match (872,704) with its tournament start date
    data/studies/match_timing/links/*.parquet                       exact days attached by source (common schema:
        match_id, source, source_key, date_local, start_utc, date_basis, link_method, score_agrees, round_agrees)
    data/studies/predictability_diagnostic/stage1_odds.parquet      tennis-data's days (used directly if the tennis_data
                                                                    link file is not there yet)

Rules (one principle throughout: where evidence disagrees, the window widens to cover every reading; it never picks one)
1. Exact days. Every linked day within [start - 10, start + 21] is a candidate. A 'local' day is that day; a UTC day
   whose venue time zone is unknown could be the local day before or after, so it counts as [d - 1, d + 1], and so do
   the days of the sources often a day off (LOOSE_CLOCK). A match's candidates form its exact interval when they overlap.
   Each source class's own clock error is then measured against the days of point logs (calibrate(): the extra days
   that bring 99.9% of the logs' days inside) and a dated match's own earliest start and latest finish are its
   claimed days widened by that error; the windows of rules 2-4 and the checks use the claimed days. When they disagree, a day shared by three or more sources
   against a single dissenter stands; otherwise the interval covers them all, and when they lie more than a week apart
   the match is not counted as dated (one of them is a mislink).
2. A dated day is not trusted alone when it falls after its event's dated final, or outside the days of the other dated
   matches of its round (sibling_outliers). Such a match keeps a window covering its claimed day AND the window rules 3-4
   give it.
3. Windows, where no source has the day. The dated matches of the same event and round, when they agree within
   SIBLING_SPAN days; otherwise per class (tour, level, phase, round, era) the spread of (match day - anchor) over the
   class's dated matches, trimmed of the outermost 0.2% at each end (mislinks), widened by one day each side, joined
   with the online research's rule (schedule_rules.csv); classes with fewer than MIN_CLASS dated matches take the level's
   default window (DEFAULTS). Where an event's own dated matches show it ran EVENT_SHIFT_MIN or more days off its
   classes' typical days, the class window is joined with the same window shifted by that much (event_shift).
4. The draw narrows windows: a player's match cannot start before their previous round of the same event could start,
   and cannot finish after their next round finished. Applied over each event's rounds until nothing moves. The draw
   order is a fact, so a window it would invert proves a dated day of that event wrong; every match of such an event
   then takes the union of its claimed day, its round's window and its class/rule window, and is narrowed again
   (narrow_with_guard). No window is ever inverted: an inverted window would let a match's own result into its own
   ratings.
5. Best-estimate day (the time decay's clock): the exact day, else the class's median offset, placed inside the window.

Writes data/studies/match_timing/timing.parquet (one row per match), timing_classes.csv (the windows), timing_summary.json
and undated_matches.parquet / .csv.gz (every match without a trusted exact day: its window and why).
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

LINK_COLUMNS = ["match_id", "source", "source_key", "date_local", "start_utc", "date_basis", "link_method",
                "score_agrees", "round_agrees"]
# most trusted first: local official/ provider days, then UTC-stamped feeds
SOURCE_RANK = ["tennis_data", "open_tennis_data", "slam_feeds", "wta_api", "match_charting", "sofascore",
               "flashscore", "api_tennis", "live_tennis_api", "infosys", "tdi", "pbp_copy", "sirgenkii", "tml_days"]
PLAUSIBLE = (-10, 21)          # days from the tournament start a linked day may fall
CONFLICT_HULL = 7              # disagreeing sources further apart than this: the match is not counted as dated
MAJORITY_MIN = 3               # sources that must share a day, against a single dissenter, for that day to stand
# sources whose day is outvoted, mostly by one day, where several sources date a match (ATP Infosys 380 of 37,203 links,
# Match Charting 348 of 9,164, TML days 105 of 2,448): their days count as [d - 1, d + 1], like a UTC day
LOOSE_CLOCK = ("infosys", "match_charting", "tml_days")
TRIM = 0.002                   # each tail of a class's offsets treated as mislinks
MIN_CLASS = 200                # dated matches a class needs for its own window
MARGIN = 1                     # days added on each side of an empirical window
# Default windows (offsets from the tournament start date): wide enough for every schedule the research found.
DEFAULTS = {
    ("main", "GS"): (-2, 16), ("qual", "GS"): (-10, 1),
    ("main", "T1000"): (-4, 15), ("qual", "T1000"): (-5, 3),
    ("main", "other"): (-3, 9), ("qual", "other"): (-5, 3),
    ("main", "TEAM"): (-4, 16), ("qual", "TEAM"): (-5, 3),
}


def level_group(level: pd.Series) -> pd.Series:
    return level.where(level.isin(["GS", "T1000", "TEAM"]), "other")


def load_links() -> pd.DataFrame:
    """The link file of every known source (links/<source>.parquet; other files in the folder are helpers' working
    tables and are never read), plus tennis-data's days from Stage 1 if its link file is absent."""
    frames, seen = [], set()
    for src in SOURCE_RANK:
        path = MT.LINKS / f"{src}.parquet"
        if not path.exists():
            continue
        try:
            cols = pd.read_parquet(path).columns
        except Exception as exc:
            MT.log(f"  skipped unreadable link file {path.name}: {exc}")
            continue
        if not set(LINK_COLUMNS).issubset(cols):
            MT.log(f"  skipped {path.name}: not the link schema")
            continue
        f = pd.read_parquet(path, columns=LINK_COLUMNS)
        frames.append(f)
        seen.update(f["source"].dropna().unique())
    if "tennis_data" not in seen:
        o = pd.read_parquet(C.OUT / "stage1_odds.parquet",
                            columns=["match_id", "td_date", "td_redated", "link", "same_set_scores", "round_agrees"])
        o = o[o["td_date"].notna()]
        frames.append(pd.DataFrame({
            "match_id": o["match_id"], "source": "tennis_data", "source_key": o["match_id"],
            "date_local": pd.to_datetime(o["td_date"]).dt.normalize(), "start_utc": pd.NaT, "date_basis": "local",
            "link_method": np.where(o["td_redated"].fillna(False), "stage1_redated", "stage1_" + o["link"].astype(str)),
            "score_agrees": o["same_set_scores"], "round_agrees": o["round_agrees"].eq("yes")}))
    links = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=LINK_COLUMNS)
    links["day"] = MT.to_day(links["date_local"])
    return links


CAL_COVER = 0.999           # each source class's interval is widened until it holds this share of the reference days
CAL_MIN = 200               # reference overlaps a class needs for its own calibration
CAL_DROP = 7                # differences beyond this many days are mislinks, not clock error, and are left out
DEFAULT_SLACK = (1, 1)      # a class with no calibration: one more day before and after


def reference_link(L: pd.DataFrame) -> pd.Series:
    """Links whose day is read off a point log, the gold standard: a WTA event log's or a Slam feed's first point,
    TDI's points."""
    m = L["link_method"].astype(str)
    return L["source"].eq("tdi") | (L["source"].isin(["wta_api", "slam_feeds"])
                                    & m.str.contains("first_point", regex=False))


def cal_class(L: pd.DataFrame) -> pd.Series:
    """A link's calibration class: source and clock, plus the WTA list's and the Slam feeds' time basis and
    tennis-data's UK-day tag."""
    m = L["link_method"].astype(str)
    basis = m.str.extract(r"(first_point|listing_schedule|listing_start|day_number|listing_2019_label_day|"
                          r"listed_local_date|draw_end_time)")[0].fillna("other")
    extra = np.where(L["source"].isin(["wta_api", "slam_feeds"]), ":" + basis, "")
    tag = np.select([m.str.contains("uk_day_venue_east", regex=False), m.str.contains("uk_day_venue_west", regex=False)],
                    [":east", ":west"], "")
    return L["source"].astype(str) + extra + ":" + L["date_basis"].astype(str) + tag


def _shortfall(X: pd.DataFrame, ref_day: pd.Series, tier: str) -> pd.DataFrame:
    """Per class, the extra days before and after its intervals needed for CAL_COVER of the reference days to fall
    inside, on the links whose match has a reference day."""
    X = X.assign(ref=X["match_id"].map(ref_day))
    X = X[X["ref"].notna() & ((X["day"] - X["ref"]).abs() <= CAL_DROP)]
    X = X.assign(need_before=X["lo"] - X["ref"], need_after=X["ref"] - X["hi"])
    rows = []
    for cls, g in X.groupby("cal_class"):
        if len(g) < CAL_MIN:
            continue
        before = max(0, int(np.ceil(np.quantile(g["need_before"], CAL_COVER))))
        after = max(0, int(np.ceil(np.quantile(g["need_after"], CAL_COVER))))
        inside = (g["need_before"] <= 0) & (g["need_after"] <= 0)
        inside_after = (g["need_before"] <= before) & (g["need_after"] <= after)
        rows.append({"cal_class": cls, "tier": tier, "overlaps": int(len(g)), "before": before, "after": after,
                     "share_inside_base": float(inside.mean()), "share_inside_calibrated": float(inside_after.mean())})
    return pd.DataFrame(rows)


def calibrate(L: pd.DataFrame) -> pd.DataFrame:
    """Each source class's extra days, measured against the gold days (point logs) where a class has CAL_MIN
    overlaps with them, else against silver days (Flashscore's local day and tennis-data's day agreeing), else
    DEFAULT_SLACK. Point-log links themselves take none."""
    ref = L[L["reference"]].groupby("match_id")["day"].agg(["min", "max"])
    gold = ref.loc[ref["min"] == ref["max"], "min"]
    X = L[~L["reference"]]
    cal = _shortfall(X, gold, "gold")
    fs = L[L["cal_class"].eq("flashscore:local")].groupby("match_id")["day"].agg(["min", "max"])
    td = L[L["cal_class"].eq("tennis_data:local")].groupby("match_id")["day"].agg(["min", "max"])
    both = fs.join(td, lsuffix="_fs", rsuffix="_td", how="inner")
    silver = both.loc[(both["min_fs"] == both["max_fs"]) & (both["min_fs"] == both["min_td"])
                      & (both["min_td"] == both["max_td"]), "min_fs"]
    rest = X[~X["cal_class"].isin(cal["cal_class"]) & ~X["cal_class"].isin(["flashscore:local", "tennis_data:local"])]
    return pd.concat([cal, _shortfall(rest, silver, "silver")], ignore_index=True)


def _majority(U: pd.DataFrame, index: pd.Index) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per match of ``index``: the interval shared by MAJORITY_MIN or more distinct sources when exactly one other
    source disagrees (NaN otherwise), and that source's name. U holds the usable candidates of the conflicting matches."""
    lo = pd.Series(np.nan, index=index)
    hi = pd.Series(np.nan, index=index)
    who = pd.Series("", index=index, dtype=object)
    for mid, r in U.groupby("match_id"):
        best_d, best = None, set()
        for d in np.arange(r["lo"].min(), r["hi"].max() + 1):
            covers = set(r.loc[(r["lo"] <= d) & (r["hi"] >= d), "source"])
            if len(covers) > len(best):
                best_d, best = d, covers
        rest = set(r["source"]) - best
        if len(best) >= MAJORITY_MIN and len(rest) == 1:
            sel = r[r["source"].isin(best) & (r["lo"] <= best_d) & (r["hi"] >= best_d)]
            lo[mid], hi[mid], who[mid] = sel["lo"].max(), sel["hi"].min(), rest.pop()
    return lo.to_numpy(), hi.to_numpy(), who.to_numpy()


def _combine(U: pd.DataFrame, lo: str, hi: str) -> pd.DataFrame:
    """Per match, its candidates' intervals (columns ``lo``, ``hi``) combined into one: their overlap when they
    agree; when they disagree, a day shared by MAJORITY_MIN or more sources against a single dissenter, else the
    interval covering them all."""
    U = U.assign(lo=U[lo], hi=U[hi])
    g = U.groupby("match_id")
    out = pd.DataFrame({"lo_all": g["lo"].min(), "hi_all": g["hi"].max(), "lo_max": g["lo"].max(),
                        "hi_min": g["hi"].min()})
    # candidates agree when every interval overlaps every other (max of lows <= min of highs)
    agree = out["lo_max"] <= out["hi_min"]
    # disagreeing sources: a day shared by MAJORITY_MIN or more sources against a single dissenter stands (open tennis
    # data alone gives Osaka-Muchova at Bad Homburg and Wimbledon 2026 each other's days, against three and five
    # sources). Otherwise the interval covering every candidate, which holds the true day whichever source is right;
    # choosing by source rank is not safe (tennis-data, ranked first, gives Haas-Fognini at Stuttgart and Hamburg 2013,
    # quarter-finals both, each other's days, against Flashscore and the point-by-point copy). Beyond a week apart one
    # of them is a mislink, and build() does not count the match as dated
    maj_lo, maj_hi, outvoted = _majority(U[U["match_id"].isin(out.index[~agree])], out.index)
    has_maj = ~agree & np.isfinite(maj_lo)
    out["exact_lo"] = np.where(agree, out["lo_max"], np.where(has_maj, maj_lo, out["lo_all"]))
    out["exact_hi"] = np.where(agree, out["hi_min"], np.where(has_maj, maj_hi, out["hi_all"]))
    out["conflict"] = ~agree
    out["outvoted_source"] = outvoted
    out["wide_conflict"] = ~agree & ~has_maj & ((out["hi_all"] - out["lo_all"]) > CONFLICT_HULL)
    out["conflict_span_days"] = np.where(agree, 0, out["hi_all"] - out["lo_all"])
    return out


def exact_days(matches: pd.DataFrame, links: pd.DataFrame, calibration: pd.DataFrame | None = None,
               default: tuple[int, int] = DEFAULT_SLACK) -> pd.DataFrame:
    """Per match, from its candidates: the claimed interval [exact_lo, exact_hi] (the sources' days under the clock
    rules: what the windows, the checks and the trusted flag use), the calibrated interval [cal_lo, cal_hi] (each
    candidate widened by its class's measured clock error: the dated match's own earliest start and latest finish),
    the sources behind it, and conflicts. The calibration is calibrate() on these links unless ``calibration`` is
    given (``default`` for a class it lacks); it is returned in L.attrs['calibration']."""
    start = pd.Series(MT.to_day(matches["tournament_date"]), index=matches["match_id"])
    L = links[links["match_id"].isin(start.index) & np.isfinite(links["day"])].copy()
    L["start"] = L["match_id"].map(start).to_numpy()
    L["offset"] = L["day"] - L["start"]
    L["plausible"] = L["offset"].between(*PLAUSIBLE)
    # redated tennis-data rows were moved by Stage 1's misdating rule: not an observed match day
    L["usable"] = L["plausible"] & ~L["link_method"].astype(str).str.contains("redated")
    utc = L["date_basis"].astype(str).ne("local") | L["source"].isin(LOOSE_CLOCK)
    method = L["link_method"].astype(str)
    # tennis-data dates by the UK calendar: at venues four or more hours east of London the local day can be one later,
    # at venues to the west one earlier (the point-feed linker's finding, tags uk_day_venue_east / _west)
    uk_east = method.str.contains("uk_day_venue_east", regex=False)
    uk_west = method.str.contains("uk_day_venue_west", regex=False)
    L["lo"] = L["day"] - np.where(utc | uk_west, 1, 0)
    L["hi"] = L["day"] + np.where(utc | uk_east, 1, 0)
    # a match suspended overnight finishes on its last point's day (the point-feed linker's 'last_point_day+N' tag);
    # tags beyond three days are clock faults, so the extension is capped
    extra = method.str.extract(r"last_point_day\+(\d+)")[0].astype(float).fillna(0).clip(upper=3).to_numpy()
    L["hi"] = L["hi"] + extra
    # each source's own clock error, measured against point-log days: a class whose days sometimes fall a day or two
    # after the first point (a late start dated by the next day, a zone guessed wrong) is widened by as much
    L["cal_class"], L["reference"] = cal_class(L), reference_link(L)
    cal = calibrate(L[L["usable"]]) if calibration is None else calibration
    slack = cal.set_index("cal_class") if len(cal) else pd.DataFrame({"before": [], "after": []})
    before = L["cal_class"].map(slack["before"]).fillna(default[0]).where(~L["reference"], 0).to_numpy()
    after = L["cal_class"].map(slack["after"]).fillna(default[1]).where(~L["reference"], 0).to_numpy()
    L["cal_lo"], L["cal_hi"] = L["lo"] - before, L["hi"] + after
    L.attrs["calibration"] = cal
    L["rank"] = L["source"].map({s: i for i, s in enumerate(SOURCE_RANK)}).fillna(len(SOURCE_RANK))
    U = L[L["usable"]]
    g = U.groupby("match_id")
    out = _combine(U, "lo", "hi")
    out["n_sources"] = g["source"].nunique()
    out["sources"] = g["source"].agg(lambda s: ";".join(sorted(set(s))))
    calibrated = _combine(U, "cal_lo", "cal_hi")
    out["cal_lo"], out["cal_hi"] = calibrated["exact_lo"], calibrated["exact_hi"]
    best = U.sort_values(["match_id", "rank", "lo"]).groupby("match_id").first()
    out["best_source"] = best["source"].reindex(out.index)
    rejected = L[~L["usable"]].groupby("match_id").size()
    out["rejected_links"] = rejected.reindex(out.index).fillna(0).astype(int)
    return out.reset_index(), L


ERAS = ((2010, 2018), (2019, 2020), (2021, 2026))     # before, during and after the ITF's 2019-20 restructuring
RULES = MT.OUT / "schedule_rules.csv"                  # the online research (docs/research/match-timing/README.md)
RULE_MARGIN = 2                                        # the research's margin where no day-level check exists
TIE_EVENTS = r"davis cup|fed cup|billie jean king|bjk"
AO21_QUALIFYING = "Australian Open 2021 qualifying (Doha; Dubai)"   # recorded on its own date, 2021-01-10
EVENT_SHIFT_MIN = 2         # days an event's dated matches sit off their classes' typical days before its undated
                            # matches' windows are widened by the same shift


def anchor_day(m: pd.DataFrame) -> np.ndarray:
    """The research's anchor: the recorded start moved to the nearest Monday (Tue -1, Wed -2, Thu -3, Fri +3, Sat +2,
    Sun +1), except team ties (Davis Cup, Fed/BJK Cup), which count from their own date, and the ATP London 2012
    Olympics (+7). Offsets and windows are measured from this day."""
    start = MT.to_day(m["tournament_date"])
    dow = (start.astype(np.int64) + 3) % 7                 # 1970-01-01 was a Thursday: Monday = 0
    shift = np.select([dow == 1, dow == 2, dow == 3, dow == 4, dow == 5, dow == 6], [-1, -2, -3, 3, 2, 1], 0)
    name = m["tournament_name"].astype(str).str.lower()
    ties = m["level"].eq("TEAM").to_numpy() & name.str.contains(TIE_EVENTS, regex=True).to_numpy()
    shift = np.where(ties, 0, shift)
    london = (m["tour"].eq("atp") & m["year"].eq(2012) & name.str.contains("olympic")).to_numpy()
    return start + shift + np.where(london, 7, 0)


def rule_label(m: pd.DataFrame) -> pd.Series:
    """The research rule a match falls under: a named event or edition where one applies, else its level's pattern."""
    name = m["tournament_name"].astype(str).str.lower()
    lab = pd.Series("", index=m.index, dtype=object)
    lv, yr, tour, q = m["level"], m["year"], m["tour"], m["qualifying"].astype(bool)
    # 'us open' as a whole phrase: the 2021 Australian Open qualifying events are named 'Doha/Dubai Aus Open Qualies'
    slam = {"australian open": "Australian Open", "roland garros": "Roland Garros", "french open": "Roland Garros",
            "wimbledon": "Wimbledon", r"\bus open\b": "US Open"}
    for k, v in slam.items():
        lab[(lv.eq("GS") & q & name.str.contains(k, regex=True)).to_numpy()] = v
    lab[(lv.eq("GS") & q & name.str.contains("aus open qualies")).to_numpy()] = AO21_QUALIFYING
    lab[(lv.eq("CH") & tour.eq("atp") & ~q).to_numpy()] = "ATP Challenger (all categories)"
    lab[(lv.eq("CH") & tour.eq("atp") & q).to_numpy()] = "ATP Challenger"
    lab[(lv.eq("CH") & tour.eq("wta")).to_numpy()] = "WTA 125"
    lab[lv.eq("ITF").to_numpy()] = "ITF (all prize levels)"
    team = lv.eq("TEAM")
    lab[(team & name.str.contains("davis cup")).to_numpy()] = "Davis Cup ties (offsets vs Sackmann tie date)"
    lab[(team & name.str.contains("fed cup|billie jean|bjk", regex=True)).to_numpy()] = \
        "Fed Cup / BJK Cup ties dated per tie (offsets vs Sackmann tie date)"
    lab[(team & name.str.contains("olympic")).to_numpy()] = "Olympics"
    lab[(team & name.str.contains("atp cup|united cup", regex=True)).to_numpy()] = "ATP Cup / United Cup"
    lab[(team & name.str.contains("laver cup")).to_numpy()] = "Laver Cup"
    lab[(team & name.str.contains("world team cup")).to_numpy()] = "World Team Cup (Dusseldorf)"
    jan21 = yr.eq(2021) & lv.isin(["T250", "T500"]) & name.str.contains("delray|antalya|abu dhabi", regex=True)
    lab[jan21.to_numpy()] = "January 2021 events (Delray Beach; Antalya; Abu Dhabi)"
    sun = (tour.eq("wta") & lv.eq("T1000") & (name.str.contains("doha|dubai", regex=True)
           | (name.str.contains("wuhan") & yr.le(2019)) | (name.str.contains("tokyo") & yr.le(2013))))
    lab[sun.to_numpy()] = "Sunday start, Saturday final (Doha; Dubai; Wuhan to 2019; Tokyo to 2013)"
    return lab


NAMED_OVERRIDE = {"Australian Open", "Roland Garros", "Wimbledon", "US Open", AO21_QUALIFYING,
                  "January 2021 events (Delray Beach; Antalya; Abu Dhabi)", "Olympics", "ATP Cup / United Cup",
                  "Laver Cup", "World Team Cup (Dusseldorf)", "Davis Cup ties (offsets vs Sackmann tie date)",
                  "Fed Cup / BJK Cup ties dated per tie (offsets vs Sackmann tie date)",
                  "Sunday start, Saturday final (Doha; Dubai; Wuhan to 2019; Tokyo to 2013)"}


def rule_windows(m: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per match, the research's window [earliest - margin, latest + margin] (offsets from the anchor) where a rule
    row matches its tour, label, year and round; NaN where none does. Also whether the row is a named override."""
    lo = np.full(len(m), np.nan)
    hi = np.full(len(m), np.nan)
    named = np.zeros(len(m), dtype=bool)
    if not RULES.exists():
        return lo, hi, named
    r = pd.read_csv(RULES)
    lab = rule_label(m).to_numpy()
    tour, yr, rnd = m["tour"].to_numpy(), m["year"].to_numpy(), m["round"].astype(str).to_numpy()
    for row in r.itertuples(index=False):
        if row.event_or_pattern not in set(lab):
            continue
        sel = (lab == row.event_or_pattern) & (yr >= row.era_from) & (yr <= row.era_to) & (rnd == str(row.round))
        if row.tour in ("atp", "wta"):
            sel &= tour == row.tour
        if not sel.any():
            continue
        lo[sel] = np.fmin(lo[sel], row.earliest_day_offset - RULE_MARGIN)
        hi[sel] = np.fmax(hi[sel], row.latest_day_offset + RULE_MARGIN)
        named[sel] |= row.event_or_pattern in NAMED_OVERRIDE
    return lo, hi, named


def era_of(year: pd.Series) -> pd.Series:
    out = pd.Series("", index=year.index, dtype=object)
    for a, b in ERAS:
        out[year.between(a, b)] = f"{a}-{b}"
    a, b = ERAS[-1]
    out[year > b] = f"{a}-{b}"          # a later season belongs to the last era (its label kept; since 10 Oct 2026)
    return out


def _window(d: np.ndarray) -> dict:
    lo, hi = np.quantile(d, [TRIM, 1 - TRIM])
    return {"lo": int(np.floor(lo)) - MARGIN, "hi": int(np.ceil(hi)) + MARGIN, "median": float(np.median(d)),
            "min_seen": float(d.min()), "max_seen": float(d.max())}


def class_windows(m: pd.DataFrame) -> pd.DataFrame:
    """Per class (tour, level, phase, round, era): the empirical offset window from exact-dated matches of the class;
    if it has fewer than MIN_CLASS, the class pooled over eras; if that is short too, the level's default window."""
    dated = m[m["exact"]].copy()
    dated["offset"] = (dated["exact_lo"] + dated["exact_hi"]) / 2 - dated["anchor"]
    fine = ["tour", "level", "phase", "round", "era"]
    coarse = ["tour", "level", "phase", "round"]
    pooled = {k: g["offset"].to_numpy() for k, g in dated.groupby(coarse, dropna=False)}
    by_fine = {k: g["offset"].to_numpy() for k, g in dated.groupby(fine, dropna=False)}
    rows = []
    for key, g in m.groupby(fine, dropna=False):
        lg = "GS" if key[1] == "GS" else ("T1000" if key[1] == "T1000" else ("TEAM" if key[1] == "TEAM" else "other"))
        default = DEFAULTS[(key[2], lg)]
        rec = dict(zip(fine, key), matches=len(g), default_lo=default[0], default_hi=default[1])
        d = by_fine.get(key, np.array([]))
        dp = pooled.get(key[:4], np.array([]))
        if len(d) >= MIN_CLASS:
            rec.update(_window(d), dated=len(d), basis="empirical_era")
        elif len(dp) >= MIN_CLASS:
            rec.update(_window(dp), dated=len(dp), basis="empirical_all_eras")
        else:
            rec.update(lo=default[0], hi=default[1], median=float(np.mean(default)), dated=len(d), basis="default",
                       min_seen=float(d.min()) if len(d) else np.nan, max_seen=float(d.max()) if len(d) else np.nan)
        rows.append(rec)
    return pd.DataFrame(rows)


SIBLING_SPAN = 4        # an event-round's dated days spread wider than this are not trusted alone


def sibling_windows(m: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per undated match: the window from the exactly dated matches of the same event and round (its siblings),
    [first day - margin, last day + margin], margin 1 with three or more dated siblings, else 2. An event's own days
    catch what a class window cannot: an edition that started on a Thursday, ran two weeks, or was held elsewhere.
    Returns (lo, hi, span) as days (NaN where no sibling is dated)."""
    d = m[m["exact"]]
    g = d.groupby(["ev", "round"]).agg(first=("exact_lo", "min"), last=("exact_hi", "max"), n=("exact_lo", "size"))
    key = pd.MultiIndex.from_arrays([m["ev"], m["round"]])
    first = g["first"].reindex(key).to_numpy()
    last = g["last"].reindex(key).to_numpy()
    n = g["n"].reindex(key).to_numpy()
    margin = np.where(n >= 3, 1, 2)
    return first - margin, last + margin, last - first


def _loo_min(v: np.ndarray, gid: np.ndarray) -> np.ndarray:
    """Per row: the minimum of v over the OTHER rows of its group (NaN in a group of one)."""
    order = np.lexsort((v, gid))
    gs, vs = gid[order], v[order]
    start = np.flatnonzero(np.r_[True, gs[1:] != gs[:-1]])
    size = np.diff(np.r_[start, len(gs)])
    at = np.repeat(start, size)
    second = np.repeat(np.where(size > 1, vs[np.minimum(start + 1, len(vs) - 1)], np.nan), size)
    out = np.empty(len(v))
    out[order] = np.where(np.arange(len(gs)) == at, second, vs[at])   # the row holding the minimum sees the next one
    return out


def sibling_outliers(m: pd.DataFrame) -> np.ndarray:
    """Exactly dated matches whose day lies outside the window the OTHER dated matches of their event and round give:
    [first - margin, last + margin], margin 1 with three or more others, else 2; rounds whose other days spread wider
    than SIBLING_SPAN are not judged. Such a day is a misdated source or a real rescheduling (rain); either way it is
    not trusted alone. Out of sample these windows miss 0.035% of dated matches (timing_check.py)."""
    out = np.zeros(len(m), dtype=bool)
    ex = np.flatnonzero(m["exact"].to_numpy(dtype=bool))
    if len(ex) == 0:
        return out
    d = m.iloc[ex]
    gid = d.groupby(["ev", "round"], sort=False).ngroup().to_numpy()
    lo, hi = d["exact_lo"].to_numpy(dtype=float), d["exact_hi"].to_numpy(dtype=float)
    others = np.bincount(gid)[gid] - 1
    first, last = _loo_min(lo, gid), -_loo_min(-hi, gid)
    margin = np.where(others >= 3, 1, 2)
    judged = (others >= 1) & ((last - first) <= SIBLING_SPAN)
    out[ex] = judged & ((hi < first - margin) | (lo > last + margin))
    return out


def event_shift(ev: np.ndarray, rnd: np.ndarray, resid: np.ndarray, exclude_own_round: bool = False) -> np.ndarray:
    """Per match: the median, over its event's exactly dated matches, of resid (dated day - the class's typical day);
    NaN for an event with none. An edition that started on a Thursday, or whose recorded start is a week off, shows
    here. With exclude_own_round each match reads only the other rounds of its event (the out-of-sample check)."""
    df = pd.DataFrame({"ev": ev, "rnd": rnd, "r": resid})
    if not exclude_own_round:
        return df["ev"].map(df.dropna(subset=["r"]).groupby("ev")["r"].median()).to_numpy(dtype=float)
    out = np.full(len(df), np.nan)
    dated_ev = set(df.loc[df["r"].notna(), "ev"])
    for _, g in df[df["ev"].isin(dated_ev)].groupby("ev", sort=False):
        for r_, gr in g.groupby("rnd", sort=False):
            other = g.loc[(g["rnd"] != r_) & g["r"].notna(), "r"]
            if len(other):
                out[gr.index.to_numpy()] = other.median()
    return out


def draw_narrowing(m: pd.DataFrame, max_pass: int = 8) -> tuple[pd.DataFrame, int]:
    """Within each event, a player's match starts no earlier than their previous round's start, and finishes no later
    than their next round's finish (the winner's next match). Only ever narrows windows; returns moved count. Sound
    only when every window holds its true day: narrow_with_guard handles the events where one does not."""
    m = m.copy()
    p = pd.concat([m[["match_id", "ev", "round_order", "player_a_id"]].rename(columns={"player_a_id": "pid"}),
                   m[["match_id", "ev", "round_order", "player_b_id"]].rename(columns={"player_b_id": "pid"})])
    p = p.sort_values(["ev", "pid", "round_order"], kind="mergesort")
    same = (p["ev"].to_numpy()[1:] == p["ev"].to_numpy()[:-1]) & (p["pid"].to_numpy()[1:] == p["pid"].to_numpy()[:-1])
    later_round = p["round_order"].to_numpy()[1:] > p["round_order"].to_numpy()[:-1]
    prev_mid = p["match_id"].to_numpy()[:-1][same & later_round]
    next_mid = p["match_id"].to_numpy()[1:][same & later_round]
    pos = pd.Series(np.arange(len(m)), index=m["match_id"])
    a, b = pos.reindex(prev_mid).to_numpy(), pos.reindex(next_mid).to_numpy()
    es, lf = m["es"].to_numpy(dtype=float), m["lf"].to_numpy(dtype=float)
    moved_total = 0
    for _ in range(max_pass):
        es_new = es.copy()
        np.maximum.at(es_new, b, es[a])           # the next round starts no earlier than the previous one started
        lf_new = lf.copy()
        np.minimum.at(lf_new, a, lf[b])           # the previous round finished no later than the next one finished
        moved = int((es_new != es).sum() + (lf_new != lf).sum())
        es, lf = es_new, lf_new
        moved_total += moved
        if moved == 0:
            break
    m["es"], m["lf"] = es, lf
    return m, moved_total


def narrow_with_guard(m: pd.DataFrame, union_lo: np.ndarray, union_hi: np.ndarray) -> tuple[pd.DataFrame, dict]:
    """draw_narrowing, guarded. If every window held its true day the draw order could never invert one, so an
    inverted window proves some dated day of that event wrong, and which one is unknown. Every match of such an event
    takes its union window (union_lo, union_hi: its claimed day, its round's window and its class/rule window together)
    and the event is narrowed again; an event still inverted after that keeps its union windows unnarrowed. Adds the
    column contradictory_event. Never returns an inverted window."""
    out, moved = draw_narrowing(m)
    inverted = out["lf"].to_numpy() < out["es"].to_numpy()
    contra = out["ev"].isin(np.unique(out["ev"].to_numpy()[inverted])).to_numpy()
    info = {"moved": moved, "contradictory_events": int(out.loc[contra, "ev"].nunique()),
            "contradictory_event_matches": int(contra.sum()), "events_left_unnarrowed": 0}
    if contra.any():
        sub = m.loc[contra].copy()
        sub["es"], sub["lf"] = union_lo[contra], union_hi[contra]
        sub2, _ = draw_narrowing(sub)
        inv2 = sub2["lf"].to_numpy() < sub2["es"].to_numpy()
        still = sub2["ev"].isin(np.unique(sub2["ev"].to_numpy()[inv2])).to_numpy()
        out.loc[contra, "es"] = np.where(still, sub["es"].to_numpy(), sub2["es"].to_numpy())
        out.loc[contra, "lf"] = np.where(still, sub["lf"].to_numpy(), sub2["lf"].to_numpy())
        info["events_left_unnarrowed"] = int(sub2.loc[still, "ev"].nunique())
    out["contradictory_event"] = contra
    if (out["lf"].to_numpy() < out["es"].to_numpy()).any():
        raise AssertionError("an inverted window survived the guard")
    return out, info


def build() -> dict:
    MT.OUT.mkdir(parents=True, exist_ok=True)
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "draw_size",
                        "tournament_id", "tournament_name", "tournament_date", "status", "player_a_id", "player_b_id"])
    m["start"] = MT.to_day(m["tournament_date"])
    m["anchor"] = anchor_day(m)
    m["ev"] = pd.factorize(m["tour"] + "|" + m["tournament_id"].astype(str) + "|" + m["tournament_date"].astype(str))[0]
    m["lgroup"] = level_group(m["level"]).to_numpy()
    m["phase"] = np.where(m["qualifying"].astype(bool), "qual", "main")
    m["era"] = era_of(m["year"]).to_numpy()
    links = load_links()
    MT.log(f"links: {len(links):,} rows from {links['source'].nunique()} sources: "
           f"{links['source'].value_counts().to_dict()}")
    ex, L = exact_days(m, links)
    cal = L.attrs["calibration"]
    cal.to_csv(MT.OUT / "source_calibration.csv", index=False)
    MT.log("source calibration (extra days before / after, tier):\n" + cal.to_string(index=False))
    m = m.merge(ex, on="match_id", how="left")
    m["rejected_links"] = m["match_id"].map(L[~L["usable"]].groupby("match_id").size()).fillna(0).astype(int).to_numpy()
    claimed = m["exact_lo"].notna().to_numpy()
    m["exact"] = claimed & ~m["wide_conflict"].fillna(False).to_numpy(dtype=bool)
    m["demoted"] = np.where(claimed & ~m["exact"].to_numpy(), "its sources disagree by more than a week", "")
    # an event's own final bounds its other matches: a day after the dated final (plus a day of slack) is a mislink, as
    # in Stage 1's swapped Stuttgart/Hamburg 2013 quarter-finals
    fin = m[m["exact"] & m["round"].eq("F")].groupby("ev")["exact_hi"].max()
    after_final = (m["exact"] & (m["exact_lo"] > m["ev"].map(fin) + 1)).to_numpy()
    m.loc[after_final, "demoted"] = "dated after its event's final"
    m.loc[after_final, "exact"] = False
    # a day far from every other dated match of its round is not trusted alone (a misdated source or a real rescheduling)
    outlier = sibling_outliers(m)
    m.loc[outlier, "demoted"] = "dated outside its round's other dated days"
    m.loc[outlier, "exact"] = False
    MT.log(f"dated days not trusted alone: {m.loc[m['demoted'].ne(''), 'demoted'].value_counts().to_dict()}")
    cls = class_windows(m)
    m = m.merge(cls[["tour", "level", "phase", "round", "era", "lo", "hi", "median", "basis"]],
                on=["tour", "level", "phase", "round", "era"], how="left")
    # an undated match's window: a named edition's researched rule where one applies; otherwise the union of the
    # empirical class window and the level's researched rule (the wider, safer of the two); otherwise the default
    rlo, rhi, named = rule_windows(m)
    has_rule = np.isfinite(rlo) & np.isfinite(rhi)
    emp = m["basis"].astype(str).str.startswith("empirical").to_numpy()
    lo = np.where(named & has_rule, rlo, np.where(emp, np.fmin(m["lo"], rlo), np.where(has_rule, rlo, m["lo"])))
    hi = np.where(named & has_rule, rhi, np.where(emp, np.fmax(m["hi"], rhi), np.where(has_rule, rhi, m["hi"])))
    basis = np.select([named & has_rule, emp & has_rule, emp, has_rule],
                      ["named_rule", "empirical+rule", "empirical", "rule"], "default")
    es_c, lf_c = m["anchor"].to_numpy() + lo, m["anchor"].to_numpy() + hi       # the class/rule window alone
    # dated siblings in the same event and round take precedence; if their days spread unusually wide, their window is
    # widened by the class/rule window instead of replacing it
    slo, shi, sspan = sibling_windows(m)
    sib = np.isfinite(slo)
    tight = sib & (sspan <= SIBLING_SPAN)
    es_w = np.where(tight, slo, np.where(sib, np.fmin(slo, es_c), es_c))
    lf_w = np.where(tight, shi, np.where(sib, np.fmax(shi, lf_c), lf_c))
    basis = np.where(tight, "event_round", np.where(sib, "event_round+" + basis, basis))
    exact = m["exact"].to_numpy(dtype=bool)
    claim_lo, claim_hi = m["exact_lo"].to_numpy(dtype=float), m["exact_hi"].to_numpy(dtype=float)
    # a dated match's own window: its claimed days widened by its sources' calibrated clock error (never narrower
    # than the claim)
    own_lo = np.fmin(claim_lo, m["cal_lo"].to_numpy(dtype=float))
    own_hi = np.fmax(claim_hi, m["cal_hi"].to_numpy(dtype=float))
    m["median"] = np.where(named & has_rule, (rlo + rhi) / 2, m["median"])
    # an event whose dated matches sit EVENT_SHIFT_MIN or more days off their classes' typical days ran off its class's
    # calendar (a Thursday start, a misrecorded week): its matches without dated siblings take the union of their
    # window and the same window shifted by that much
    typical = m["anchor"].to_numpy() + m["median"].to_numpy(dtype=float)
    shift = np.nan_to_num(event_shift(m["ev"].to_numpy(), m["round"].to_numpy(),
                                      np.where(exact, (claim_lo + claim_hi) / 2 - typical, np.nan)))
    shifted = ~exact & ~tight & (np.abs(np.round(shift)) >= EVENT_SHIFT_MIN)
    es_w = np.where(shifted, np.fmin(es_w, es_c + np.floor(shift)), es_w)
    lf_w = np.where(shifted, np.fmax(lf_w, lf_c + np.ceil(shift)), lf_w)
    basis = np.where(shifted, basis + "+event_shift", basis)
    MT.log(f"undated windows widened by their event's shift: {int(shifted.sum()):,}")
    # a dated match: its own (calibrated) window; a day not trusted alone: the window widened to cover the claimed
    # days as well (np.fmin and np.fmax ignore the NaN of a match no source dates)
    m["es"] = np.where(exact, own_lo, np.fmin(own_lo, es_w))
    m["lf"] = np.where(exact, own_hi, np.fmax(own_hi, lf_w))
    m["window_basis"] = np.where(exact, "exact", np.where(np.isfinite(claim_lo), "claimed_day+" + basis, basis))
    # the draw narrows every window; an event whose dated days contradict the draw order takes union windows instead
    union_lo = np.fmin.reduce(np.vstack([own_lo, slo, es_c, es_w]), axis=0)
    union_hi = np.fmax.reduce(np.vstack([own_hi, shi, lf_c, lf_w]), axis=0)
    es0, lf0 = m["es"].to_numpy().copy(), m["lf"].to_numpy().copy()
    m, guard = narrow_with_guard(m, union_lo, union_hi)
    contra = m["contradictory_event"].to_numpy(dtype=bool)
    m.loc[contra & m["exact"].to_numpy(dtype=bool), "demoted"] = "its event's dated days contradict the draw order"
    m.loc[contra, "exact"] = False
    m.loc[contra, "window_basis"] = "draw_contradiction_union"
    narrowed = ((m["es"].to_numpy() != es0) | (m["lf"].to_numpy() != lf0)) & ~contra
    m.loc[narrowed & ~m["exact"].to_numpy(dtype=bool), "window_basis"] = m["window_basis"] + "+draw"
    MT.log(f"draw guard: {guard}")
    centre = np.where(m["exact"].to_numpy(dtype=bool), (claim_lo + claim_hi) / 2,
                      m["anchor"].to_numpy() + m["median"].to_numpy(dtype=float))
    m["obs"] = np.clip(centre, m["es"].to_numpy(), m["lf"].to_numpy())
    m["width_days"] = m["lf"] - m["es"] + 1
    if not (np.isfinite(m[["es", "lf", "obs"]].to_numpy(dtype=float)).all() and (m["lf"] >= m["es"]).all()):
        raise AssertionError("every match needs a finite window that does not end before it starts")
    keep = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
            "tournament_name", "tournament_date", "start", "anchor", "es", "lf", "obs", "width_days", "exact",
            "window_basis",
            "best_source", "sources", "n_sources", "conflict", "outvoted_source", "wide_conflict", "conflict_span_days",
            "rejected_links", "demoted", "contradictory_event"]
    timing = m[keep].copy()
    timing.to_parquet(MT.TIMING, index=False, compression="zstd")
    cls.to_csv(MT.OUT / "timing_classes.csv", index=False)
    und = timing[~timing["exact"]].copy()
    und["es_date"], und["lf_date"] = MT.from_day(und["es"]).dt.date.to_numpy(), MT.from_day(und["lf"]).dt.date.to_numpy()
    und["why"] = np.select([und["demoted"].astype(str).ne(""), und["rejected_links"] > 0],
                           [und["demoted"].astype(str), "its only linked day was rejected (implausible or redated)"],
                           "no source holds the day")
    ucols = ["match_id", "tour", "year", "level", "qualifying", "round", "tournament_name", "tournament_date",
             "es_date", "lf_date", "width_days", "window_basis", "why"]
    und[ucols].to_parquet(MT.OUT / "undated_matches.parquet", index=False, compression="zstd")
    und[ucols].to_csv(MT.OUT / "undated_matches.csv.gz", index=False, compression="gzip")
    (und.assign(phase=np.where(und["qualifying"].astype(bool), "qualifying", "main draw"))
        .groupby(["tour", "level", "phase", "year"]).agg(undated=("match_id", "size"),
                                                         median_window_days=("width_days", "median"))
        .reset_index().merge(timing.assign(phase=np.where(timing["qualifying"].astype(bool), "qualifying", "main draw"))
                             .groupby(["tour", "level", "phase", "year"]).size().rename("matches").reset_index(),
                             on=["tour", "level", "phase", "year"], how="right")
        .fillna({"undated": 0}).to_csv(MT.OUT / "undated_summary.csv", index=False))
    summary = {
        "matches": len(timing), "exact": int(timing["exact"].sum()),
        "exact_share_by_tour_level": timing.groupby(["tour", "level", "qualifying"])["exact"].mean().round(4)
            .reset_index().to_dict("records"),
        "conflicts": int(timing["conflict"].sum()), "wide_conflicts": int(timing["wide_conflict"].fillna(False).sum()),
        "conflicts_settled_by_majority": int(timing["outvoted_source"].fillna("").ne("").sum()),
        "outvoted_sources": timing.loc[timing["outvoted_source"].fillna("").ne(""), "outvoted_source"]
            .value_counts().to_dict(),
        "dated_days_not_trusted_alone": timing.loc[timing["demoted"].ne(""), "demoted"].value_counts().to_dict(),
        "draw_narrowing_moves": guard["moved"], "draw_guard": guard,
        "source_calibration": cal.to_dict("records"), "default_slack": DEFAULT_SLACK,
        "links_rejected_implausible": int((~L["plausible"]).sum()),
        "width_days_undated": timing.loc[~timing["exact"], "width_days"].describe().round(2).to_dict(),
        "sources": links["source"].value_counts().to_dict(),
    }
    MT.jdump(summary, MT.OUT / "timing_summary.json")
    MT.log(f"timing: {summary['exact']:,} of {summary['matches']:,} matches have a trusted exact day; "
           f"{summary['conflicts']:,} conflicts; draw narrowing moved {guard['moved']:,} bounds; "
           f"{guard['contradictory_events']} events contradicted the draw order")
    return summary


if __name__ == "__main__":
    build()
