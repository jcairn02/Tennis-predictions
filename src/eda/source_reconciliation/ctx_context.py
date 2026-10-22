"""Part D of the source-reconciliation study: the context fields. Stage 0's surface, indoor flag, level, round,
best-of, draw size, tournament and match dates and seeds against every other source that holds them for the same
matches (the ctx_results gather tables carry each source's raw context fields per linked match; the match-timing link
files the dates). Run ctx_results.py --stage gather first.

Stages (--part): surface, indoor, level, rbd (round, best-of, draw size), dates, seeds, or all.
Outputs in data/studies/source_reconciliation/context/ (aggregates and event lists only; per-match rows in work/):
    surface_by_source.csv, surface_events.csv            match agreement by source; every event where a source's
                                                         modal surface differs from Stage 0's, the values by source
    indoor_events.csv, indoor_summary.json               the model's indoor rule's two sources (men: Stage 0's flag
                                                         against tennis-data's Court; women: the WTA's calendar against
                                                         Court) and third sources, every disagreeing event resolved
    level_by_source.csv, level_events.csv                as for the surface
    round_by_source.csv, bestof_by_source.csv, draw_events.csv
    dates_by_source.csv, dates_pairwise.csv, dates_clock.csv, dates_summary.json, work/dates_links.parquet
    seeds_by_source.csv
No result is read; values of the same match are compared.

Run: ./python.sh src/eda/source_reconciliation/ctx_context.py [--part all]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import ctx_common as X  # noqa: E402

RESULT_SOURCES = ["tennis_data", "open_tennis_data", "api_tennis", "flashscore", "slam_feeds", "wta_api", "tdi",
                  "sofascore", "live_tennis_api", "infosys", "tennislive", "wta_site", "tml"]
COLS = ["match_id", "source", "family", "surface_raw", "indoor_raw", "level_raw", "round_raw", "best_of_raw",
        "draw_raw", "tournament_raw", "seed_a_src", "seed_b_src", "entry_a_src", "entry_b_src", "source_key"]
MAIN_LEVELS = ("GS", "FIN", "T1000", "T500", "T250", "TEAM")


def load(sources=RESULT_SOURCES, cols=COLS) -> pd.DataFrame:
    frames = []
    for s in sources:
        p = X.WORK / f"results_{s}.parquet"
        if p.exists():
            frames.append(pd.read_parquet(p, columns=cols))
    return pd.concat(frames, ignore_index=True)


def s0() -> pd.DataFrame:
    return X.stage0_matches().set_index("match_id")


def event_key(m: pd.DataFrame) -> pd.Series:
    return m["tour"].astype(str) + "|" + m["tournament_id"].astype(str) + "|" + \
        pd.to_datetime(m["tournament_date"]).dt.strftime("%Y-%m-%d")


def modal(s: pd.Series):
    s = s.dropna()
    if s.empty:
        return None
    vc = s.value_counts()
    return vc.index[0]


# ------------------------------------------------------------------------------------------------ surface

def norm_surface(v) -> str | None:
    if X.blank(v):
        return None
    s = str(v).strip().lower()
    if "clay" in s or "antuka" in s or "terre" in s:
        return "Clay"
    if "grass" in s or "tráva" in s or "trava" in s or "tr�va" in s:
        return "Grass"
    if "carpet" in s or "koberec" in s:
        return "Carpet"
    if "hard" in s or "greenset" in s:
        return "Hard"
    return None


def surface(r: pd.DataFrame, m: pd.DataFrame) -> None:
    x = r[["match_id", "source", "family", "surface_raw"]].copy()
    x["src"] = x["surface_raw"].map(norm_surface)
    # the WTA API's matches carry no surface: its editions do (tournament id and year from the source key)
    w = r[r["source"].eq("wta_api")][["match_id", "source_key"]].copy()
    k = w["source_key"].str.extract(r"^wta:(?P<tid>[^/]+)/(?P<year>\d{4})/")
    ed = pd.read_parquet(C.DUMP / "points" / "wta" / "editions.parquet",
                         columns=["tournament_id", "year", "surface", "in_outdoor", "tier", "singles_draw_size", "title",
                                  "city"])
    ed["year"] = ed["year"].astype(int).astype(str)
    ed = ed.drop_duplicates(["tournament_id", "year"]).set_index(["tournament_id", "year"])
    edk = ed.reindex(pd.MultiIndex.from_arrays([k["tid"].astype(str), k["year"].astype(str)]))
    w["src"] = edk["surface"].map(norm_surface).to_numpy()
    x = pd.concat([x[~x["source"].eq("wta_api")], w.assign(source="wta_api_editions", family="wta_official")[
        ["match_id", "source", "family", "src"]]], ignore_index=True)
    x = x[x["src"].notna()]
    x = x.join(m[["surface", "tour", "level", "qualifying", "tournament_id", "tournament_date", "tournament_name",
                  "year"]], on="match_id")
    x["s0"] = x["surface"]
    x["agree"] = x["src"] == x["s0"]
    x["carpet_vs_hard"] = x["s0"].isin(["Carpet", "Hard"]) & x["src"].isin(["Carpet", "Hard"]) & ~x["agree"]
    bs = x.groupby(["source", "family", "tour"]).agg(matches=("match_id", "size"), agree=("agree", "sum"),
                                                    carpet_vs_hard=("carpet_vs_hard", "sum"),
                                                    s0_blank=("s0", lambda s: int(s.isna().sum()))).reset_index()
    bs["disagree_pct"] = (100 * (1 - bs["agree"] / bs["matches"])).round(3)
    bs.to_csv(X.OUT / "surface_by_source.csv", index=False)
    # events: each source's modal surface against Stage 0's
    x["ev"] = event_key(x)
    ev = x.groupby(["ev", "source"]).agg(src=("src", modal), n=("match_id", "size")).reset_index()
    s0ev = x.groupby("ev").agg(s0=("s0", modal), tour=("tour", "first"), level=("level", "first"),
                               name=("tournament_name", "first"), year=("year", "first"))
    ev = ev.join(s0ev, on="ev")
    dis_ev = ev[ev["src"] != ev["s0"]]["ev"].unique()
    t = ev[ev["ev"].isin(dis_ev)]
    wide = t.pivot_table(index="ev", columns="source", values="src", aggfunc="first")
    fam = x.drop_duplicates(["ev", "source"])[["ev", "source", "family"]]
    t2 = t.merge(fam, on=["ev", "source"])
    indep = t2[~t2["family"].isin(["derived_otd", "sackmann_tml"])]
    # per event: independent families' modal surfaces: how many differ from Stage 0
    fv = indep.groupby(["ev", "family"])["src"].agg(modal).reset_index().join(s0ev["s0"], on="ev")
    agg = fv.assign(against=fv["src"] != fv["s0"]).groupby("ev").agg(families=("family", "nunique"),
                                                                       families_against=("against", "sum"))
    out = s0ev.loc[dis_ev].join(agg).join(wide)
    out["matches"] = x.groupby("ev")["match_id"].nunique().reindex(out.index)
    out["s0_carpet"] = out["s0"].eq("Carpet")
    # the majority of the independent families' modal surfaces, the Live Tennis API left out (its surface disagrees
    # with Stage 0 on 8-20% of matches, ten times any other source: surface_by_source.csv), and the WTA's own value
    fv2 = fv[fv["family"].ne("live_tennis_api")]
    def maj(g):
        vc = g["src"].value_counts()
        if vc.empty or (len(vc) > 1 and vc.iloc[0] == vc.iloc[1]):
            return None
        return vc.index[0]
    out["majority_without_lta"] = fv2.groupby("ev").apply(maj, include_groups=False).reindex(out.index)
    off = fv[fv["family"].eq("wta_official")].set_index("ev")["src"]
    out["wta_official"] = off[~off.index.duplicated()].reindex(out.index)
    out["stage0_is_majority"] = out["majority_without_lta"].eq(out["s0"])
    out["frame_matches"] = x[x["match_id"].isin(set(X.model_frame_ids()))].groupby("ev")["match_id"].nunique()         .reindex(out.index).fillna(0).astype(int)
    out = out.reset_index().sort_values(["families_against", "matches"], ascending=False)
    out.to_csv(X.OUT / "surface_events.csv", index=False)
    X.log(f"surface: {len(out):,} events with a disagreement; by source {bs.groupby('source')['disagree_pct'].mean().round(3).to_dict()}")


# ------------------------------------------------------------------------------------------------ indoor

def norm_indoor(source: str, v) -> float:
    if X.blank(v):
        return np.nan
    s = str(v).strip().lower()
    if source == "tennis_data":
        return {"indoor": 1.0, "outdoor": 0.0}.get(s, np.nan)
    if source == "sofascore":
        return 1.0 if "indoor" in s else (0.0 if "outdoor" in s else np.nan)
    if source == "live_tennis_api":
        return {"true": 1.0, "false": 0.0}.get(s, np.nan)
    if source == "tml":
        return {"i": 1.0, "o": 0.0}.get(s, np.nan)
    if source == "wta_site":
        return {"true": 1.0, "false": 0.0}.get(s, np.nan)
    if source == "tennislive":
        return 1.0 if "indoor" in s else (0.0 if s in ("hard",) else np.nan)
    return np.nan


# Venues whose roof status is plain (general knowledge, not checked online: no network in this study). Keys are words
# of Stage 0's tournament name; values: 1.0 indoor, 0.0 outdoor, with the venue.
VENUES = {
    "rotterdam": (1.0, "Rotterdam Ahoy, indoor hard"), "paris masters": (1.0, "Paris Bercy (Accor Arena), indoor hard"),
    "linz": (1.0, "Linz: TipsArena / Design Center, indoor"), "stuttgart": (None, "WTA Stuttgart: Porsche Arena, "
                                                                             "indoor clay; ATP Stuttgart: outdoor grass/clay"),
    "indian wells": (0.0, "Indian Wells Tennis Garden, outdoor hard"), "basel": (1.0, "St. Jakobshalle, indoor hard"),
    "vienna": (1.0, "Wiener Stadthalle, indoor hard"), "marseille": (1.0, "Palais des Sports, indoor hard"),
    "montpellier": (1.0, "Sud de France Arena, indoor hard"), "metz": (1.0, "Arenes de Metz, indoor hard"),
    "stockholm": (1.0, "Kungliga tennishallen, indoor hard"), "antwerp": (1.0, "Lotto Arena, indoor hard"),
    "sofia": (1.0, "Arena Sofia, indoor hard"), "st. petersburg": (1.0, "Sibur Arena, indoor hard"),
    "st petersburg": (1.0, "Sibur Arena, indoor hard"), "moscow": (1.0, "Kremlin Cup, indoor hard"),
    "zagreb": (1.0, "Dom Sportova, indoor"), "memphis": (1.0, "Racquet Club of Memphis, indoor hard"),
    "san jose": (1.0, "SAP Center (to 2013), indoor hard"), "quebec": (1.0, "PEPS, indoor carpet/hard"),
    "ostrava": (1.0, "Ostravar Arena, indoor hard"), "luxembourg": (1.0, "CK Sportcenter Kockelscheuer, indoor hard"),
    "tour finals": (1.0, "O2 Arena / Pala Alpitour, indoor hard"), "atp finals": (1.0, "O2 Arena / Pala Alpitour, indoor"),
    "miami": (0.0, "outdoor hard"), "monte carlo": (0.0, "outdoor clay"), "wimbledon": (0.0, "outdoor grass"),
    "us open": (0.0, "outdoor hard"), "australian open": (0.0, "outdoor hard"), "roland garros": (0.0, "outdoor clay"),
    "dubai": (0.0, "outdoor hard"), "doha": (0.0, "outdoor hard"), "santiago": (0.0, "outdoor clay"),
    "sao paulo": (None, "Brasil Open: indoor clay at Ibirapuera (2012-2015), outdoor at Pinheiros (2016-2019)"),
    "zhuhai": (0.0, "Hengqin, outdoor hard"), "guadalajara": (0.0, "Panamerican Tennis Center, outdoor hard"),
    "taipei": (1.0, "Taipei Arena / Heping Gymnasium, indoor hard"), "tallinn": (1.0, "Forus Tennis Center, indoor hard"),
    "lyon": (None, "WTA Lyon: Palais des Sports, indoor; ATP Lyon: Parc de la Tete d'Or, outdoor clay"),
}


# (words of the name, season, tour) -> (value, venue): editions whose venue differs from the event's usual one
VENUE_EDITIONS = {
    ("wta championships", 2010, "wta"): (0.0, "WTA Championships 2010, Doha: Khalifa International Tennis Complex, "
                                              "outdoor hard"),
    ("tournament of champions", 2011, "wta"): (0.0, "Tournament of Champions 2009-2011, Bali (Nusa Dua): outdoor hard"),
    ("tokyo", 2018, "wta"): (1.0, "Pan Pacific Open 2018: Arena Tachikawa Tachihi, indoor hard (Ariake rebuilt)"),
}


def venue(name: str, tour: str, year) -> tuple[float, str]:
    s = str(name or "").lower()
    y = int(year) if not X.blank(year) else 0
    for (k, yy, tt), (v, note) in VENUE_EDITIONS.items():
        if k in s and y == yy and tour == tt:
            return v, note
    for k, (v, note) in VENUES.items():
        if k in s:
            if k == "stuttgart":
                return (1.0 if tour == "wta" else 0.0), note
            if k == "lyon":
                return (1.0 if tour == "wta" else 0.0), note
            if k == "sao paulo":
                y = int(year) if not X.blank(year) else 0
                return (1.0 if y <= 2015 else 0.0) if y else np.nan, note
            return (np.nan if v is None else v), note
    return np.nan, ""


def indoor(r: pd.DataFrame, m: pd.DataFrame) -> None:
    from src.eda.indoor_fill import status as ST
    from src.eda.source_reconciliation import ctx_readers as R
    rows = m.reset_index()
    rows = rows[rows["level"].isin(ST.LEVELS)][ST.MATCH_COLS].copy()
    rows["match_id"] = rows["match_id"].astype(str)
    td = r[r["source"].eq("tennis_data")][["match_id", "indoor_raw", "source_key"]]
    loc = R.tennis_data(td["source_key"])["location"]
    court = pd.Series(ST.court_flag(td["indoor_raw"].to_numpy()).to_numpy(), index=td["match_id"].to_numpy())
    location = pd.Series(loc.reindex(td["source_key"]).to_numpy(), index=td["match_id"].to_numpy())
    rule = ST.rule(rows, court, location, ST.wta_editions)
    rule = rule.set_index("match_id")
    # the model's frame: the rule's value against the frame's input (a check that the rule ran as the chain runs it)
    fr = pd.read_parquet(C.STUDIES / "current_best_model" / "template_2026-10-14" / "model_frame.parquet",
                         columns=["match_id", "in_indoor"]).set_index("match_id")
    chk = fr.join(rule[["indoor"]], how="left")
    check = {"frame_matches": int(len(chk)), "rule_equals_frame": int((chk["in_indoor"] == chk["indoor"]).sum()),
             "rule_missing": int(chk["indoor"].isna().sum()),
             "differ": int(((chk["in_indoor"] != chk["indoor"]) & chk["indoor"].notna() & chk["in_indoor"].notna()).sum())}
    # third sources per match
    third = []
    for s in ("sofascore", "live_tennis_api", "wta_site", "tennislive", "tml"):
        q = r[r["source"].eq(s)][["match_id", "indoor_raw", "surface_raw"]].copy()
        raw = q["surface_raw"] if s == "tennislive" else q["indoor_raw"]
        q["v"] = [norm_indoor(s, v) for v in raw]
        third.append(q[["match_id", "v"]].assign(source=s))
    th = pd.concat(third, ignore_index=True)
    th = th[th["match_id"].isin(rule.index) & th["v"].notna()]
    tw = th.groupby(["match_id", "source"])["v"].first().unstack()
    rule = rule.join(tw)
    rule = rule.join(m[["tournament_name", "tournament_date", "level"]])
    rule["second"] = np.where(rule["tour"].eq("wta"), rule["calendar"], rule["stage0"])
    rule["ev"] = rule["tour"].astype(str) + "|" + rule["tournament_id"].astype(str)
    frame_ids = set(fr.index)
    rule["frame"] = rule.index.isin(frame_ids)

    def one(x):
        v = x.dropna().unique()
        return v[0] if len(v) == 1 else (np.nan if len(v) == 0 else -1.0)
    agg = {c: (c, one) for c in ["own", "second", "stage0", "calendar", "indoor", "sofascore", "live_tennis_api",
                                 "wta_site", "tennislive", "tml"] if c in rule}
    ev = rule.groupby("ev").agg(tour=("tour", "first"), year=("year", "first"), tournament_id=("tournament_id", "first"),
                                name=("tournament_name", "first"), level=("level", "first"),
                                matches=("indoor", "size"), frame_matches=("frame", "sum"), **agg).reset_index()
    both = ev["own"].isin([0.0, 1.0]) & ev["second"].isin([0.0, 1.0])
    ev["disagree"] = both & (ev["own"] != ev["second"])
    dis = ev[ev["disagree"]].copy()
    vv = [venue(n, t, y) for n, t, y in zip(dis["name"], dis["tour"], dis["year"])]
    dis["venue_value"] = [v[0] for v in vv]
    dis["venue_note"] = [v[1] for v in vv]
    thirds = [c for c in ("sofascore", "live_tennis_api", "tennislive", "wta_site", "tml") if c in dis]
    # third sources independent of both sides: for men, TML IS Stage 0's flag; for women, the WTA website is the WTA's
    # calendar's family. SofaScore, the Live Tennis API and TennisLive are independent of both.
    indep = ["sofascore", "live_tennis_api", "tennislive"]
    dis["third_for_court"] = sum((dis[c] == dis["own"]).astype(int) for c in indep if c in dis)
    dis["third_for_second"] = sum((dis[c] == dis["second"]).astype(int) for c in indep if c in dis)
    right = []
    for _, e in dis.iterrows():
        if not np.isnan(e["venue_value"]) if isinstance(e["venue_value"], float) else False:
            right.append(("court" if e["venue_value"] == e["own"] else "second", "venue"))
        elif e["third_for_court"] > e["third_for_second"]:
            right.append(("court", "third_sources"))
        elif e["third_for_second"] > e["third_for_court"]:
            right.append(("second", "third_sources"))
        else:
            right.append(("unresolved", "none"))
    dis["right"] = [x[0] for x in right]
    dis["resolved_by"] = [x[1] for x in right]
    dis["second_source"] = np.where(dis["tour"].eq("wta"), "wta_calendar", "stage0_flag(TML)")
    keep = ["tour", "year", "tournament_id", "name", "level", "matches", "frame_matches", "own", "second",
            "second_source", "indoor"] + thirds + ["third_for_court", "third_for_second", "venue_value", "venue_note",
                                                   "right", "resolved_by"]
    dis = dis.rename(columns={"own": "own"})[keep].rename(columns={"own": "td_court", "indoor": "model_value"})
    dis.sort_values(["tour", "year", "name"]).to_csv(X.OUT / "indoor_events.csv", index=False)
    summ = {"rule_check_on_frame": check,
            "events_with_both": {t: int(both[ev["tour"].eq(t)].sum()) for t in ("atp", "wta")},
            "events_disagreeing": dis["tour"].value_counts().to_dict(),
            "disagreeing_frame_matches": dis.groupby("tour")["frame_matches"].sum().to_dict(),
            "who_is_right": dis.groupby(["tour", "right", "resolved_by"]).size().rename("events").reset_index()
                               .to_dict("records"),
            "matches_with_both": {t: int((rule["tour"].eq(t) & rule["own"].notna() & rule["second"].notna()).sum())
                                  for t in ("atp", "wta")},
            "matches_disagreeing": {t: int((rule["tour"].eq(t) & rule["own"].notna() & rule["second"].notna()
                                            & (rule["own"] != rule["second"])).sum()) for t in ("atp", "wta")}}
    # third sources against each of the two, match by match (independent families only)
    for t in ("atp", "wta"):
        g = rule[rule["tour"].eq(t) & rule["own"].notna() & rule["second"].notna() & (rule["own"] != rule["second"])]
        d = {}
        for c in indep:
            if c in g:
                h = g[g[c].notna()]
                d[c] = {"matches": int(len(h)), "with_court": int((h[c] == h["own"]).sum()),
                        "with_second": int((h[c] == h["second"]).sum())}
        summ[f"third_sources_on_disagreeing_matches_{t}"] = d
        a = rule[rule["tour"].eq(t) & rule["own"].notna() & rule["second"].notna()]
        d2 = {}
        for c in indep:
            if c in a:
                h = a[a[c].notna()]
                d2[c] = {"matches": int(len(h)), "agrees_with_court": int((h[c] == h["own"]).sum()),
                         "agrees_with_second": int((h[c] == h["second"]).sum())}
        summ[f"third_sources_all_matches_{t}"] = d2
    X.write_json(X.OUT / "indoor_summary.json", summ)
    X.log(f"indoor: {summ['events_disagreeing']} disagreeing events; check {check}")


# ------------------------------------------------------------------------------------------------ level

TD_LEVEL = {"ATP250": "T250", "ATP500": "T500", "Masters 1000": "T1000", "Grand Slam": "GS", "Masters Cup": "FIN",
            "International": "T250", "International Gold": "T500", "Masters": "T1000", "Premier": "T500|T1000",
            "Tier 1": "T1000", "Tier 2": "T500", "Tier 3": "T250", "Tier 4": "T250", "WTA1000": "T1000",
            "WTA500": "T500", "WTA250": "T250", "Tour Championships": "FIN"}
WTA_TIER = {"250": "T250", "500": "T500", "1000": "T1000", "125": "CH", "slam": "GS", "finals": "FIN", "team": "TEAM"}
TML_LEVEL = {"G": "GS", "M": "T1000", "1000": "T1000", "500": "T500", "250": "T250", "A": "T250", "F": "FIN",
             "D": "TEAM", "O": "TEAM", "C": "CH", "I": "T250", "P": "T500", "PM": "T1000", "P5": "T1000",
             "T1": "T1000", "T2": "T500", "T3": "T250", "T4": "T250", "T5": "T250", "W": "T250"}
COARSE = {"GS": "tour", "FIN": "tour", "T1000": "tour", "T500": "tour", "T250": "tour", "CH": "CH", "ITF": "ITF",
          "TEAM": "TEAM"}


def norm_level(source: str, v):
    """(level or alternatives 'T500|T1000', how fine: 'fine' or 'coarse' (tour / CH / ITF only))."""
    if X.blank(v):
        return None, None
    s = str(v).strip()
    if source == "tennis_data":
        if re.fullmatch(r"WTA2[5-7]\d", s) and s != "WTA250":
            return "T250", "garbled"            # WTA251 ... WTA276: one row each, a fill-down artefact (inference)
        return TD_LEVEL.get(s), "fine"
    if source == "wta_api":
        return WTA_TIER.get(s.lower()), "fine"
    if source == "wta_site":
        return (s if s in COARSE else None), "fine"
    if source == "tml":
        return TML_LEVEL.get(s), "fine"
    if source == "tennislive":
        kind, _, rank = s.partition("|")
        if kind == "itf":
            return "ITF", "coarse"
        if kind in ("challenger", "wta125"):
            return "CH", "coarse"
        if kind == "slam":
            return "GS", "fine"
        if kind == "finals":
            return "FIN", "fine"
        if kind == "team":
            return "TEAM", "coarse"
        if kind == "tour":
            return ("T1000" if rank == "3" else "T250|T500"), "fine"
        return None, None
    if source in ("sofascore", "flashscore", "api_tennis"):
        t = s.lower()
        if "itf" in t:
            return "ITF", "coarse"
        if "challenger" in t or "125" in t:
            return "CH", "coarse"
        if "davis" in t or "billie" in t or "united cup" in t or "fed cup" in t:
            return "TEAM", "coarse"
        if t.startswith("atp") or t.startswith("wta"):
            return "tour", "coarse"
        return None, None
    return None, None


def level_agrees(s0lvl: str, src: str, how: str) -> bool:
    if how == "coarse":
        return (src == "tour" and COARSE.get(s0lvl) == "tour") or src == s0lvl or COARSE.get(s0lvl) == src
    return s0lvl in str(src).split("|")


def level(r: pd.DataFrame, m: pd.DataFrame) -> None:
    x = r[["match_id", "source", "family", "level_raw"]].copy()
    nl = [norm_level(s, v) for s, v in zip(x["source"], x["level_raw"])]
    x["src"], x["how"] = [a for a, _ in nl], [b for _, b in nl]
    x = x[x["src"].notna()]
    x = x.join(m[["level", "tour", "qualifying", "tournament_id", "tournament_date", "tournament_name", "year"]],
               on="match_id")
    x["agree"] = [level_agrees(a, b, h) for a, b, h in zip(x["level"], x["src"], x["how"])]
    bs = x.groupby(["source", "family", "how", "tour"]).agg(matches=("match_id", "size"),
                                                          agree=("agree", "sum")).reset_index()
    bs["disagree_pct"] = (100 * (1 - bs["agree"] / bs["matches"])).round(3)
    bs.to_csv(X.OUT / "level_by_source.csv", index=False)
    x["ev"] = event_key(x)
    d = x[~x["agree"]]
    ev = d.groupby(["ev", "source"]).agg(src=("src", modal), n=("match_id", "size")).reset_index()
    tot = x.groupby(["ev", "source"])["match_id"].size().rename("linked").reset_index()
    ev = ev.merge(tot, on=["ev", "source"])
    ev["share"] = (ev["n"] / ev["linked"]).round(3)
    info = x.groupby("ev").agg(tour=("tour", "first"), year=("year", "first"), name=("tournament_name", "first"),
                               stage0_level=("level", "first"), qualifying=("qualifying", "max"))
    ev = ev.join(info, on="ev")
    ev["value"] = ev["src"] + " (" + ev["n"].astype(str) + "/" + ev["linked"].astype(str) + ")"
    wide = ev.pivot_table(index="ev", columns="source", values="value", aggfunc="first")
    out = info.join(wide, how="inner")
    out["sources_disagreeing"] = ev[ev["share"] >= 0.5].groupby("ev")["source"].nunique().reindex(out.index).fillna(0)
    out = out.reset_index().sort_values(["sources_disagreeing", "year"], ascending=[False, True])
    out.to_csv(X.OUT / "level_events.csv", index=False)
    lv = level_verdicts(x)
    lv.to_csv(X.OUT / "level_main_tour_verdicts.csv", index=False)
    X.log(f"level: {len(out):,} events with some disagreement; {int((out['sources_disagreeing'] >= 2).sum())} with "
          f"two or more sources disagreeing on most of the event; main-tour verdicts "
          f"{lv['verdict'].value_counts().to_dict()}")


# Men's levels where tennis-data and Stage 0 disagree and no official ATP level is on disk: general knowledge of the
# ATP calendar (not checked online: no network in this study), with how sure.
ATP_LEVEL_KNOWLEDGE = {
    ("valencia", 2014): ("T500", "Valencia Open 500 was an ATP 500 from 2009 to 2014 (a 250 from 2015)", "confident"),
    ("vienna", 2014): ("T250", "Vienna became an ATP 500 in 2015, swapping with Valencia", "confident"),
    ("valencia", 2015): ("T250", "Valencia was an ATP 250 from 2015", "confident"),
    ("vienna", 2015): ("T500", "Vienna an ATP 500 from 2015", "confident"),
    ("nottingham", 2015): ("T250", "Nottingham (Aegon Open) 2015-2016 was an ATP 250", "confident"),
    ("nottingham", 2016): ("T250", "Nottingham (Aegon Open) 2015-2016 was an ATP 250", "confident"),
    ("hamburg", None): ("T500", "Hamburg (German Open) has been an ATP 500 since 2009", "confident"),
    ("st petersburg", 2020): ("T500", "St. Petersburg Open was a 500 in 2020 (a one-season upgrade)", "moderate"),
}


def level_verdicts(x: pd.DataFrame) -> pd.DataFrame:
    """Main-tour events where a fine source (tennis-data, the WTA's API or website, TML) gives another level than
    Stage 0 on most of the event's matches: every fine source's modal level, and a verdict: the WTA's own record where
    it has the event (women), else the general knowledge above (men), else 'unresolved'; season finales filed as
    250s (tennis-data's Tournament of Champions, TML's Next Gen Finals and WTA Finals codes) are definitional."""
    fine = x[x["how"].isin(["fine", "garbled"]) & x["level"].isin(["GS", "FIN", "T1000", "T500", "T250"])]
    mv = fine.groupby(["ev", "source"]).agg(val=("src", modal), n=("match_id", "size"),
                                            agree=("agree", "mean")).reset_index()
    flagged = mv[mv["agree"] < 0.5]["ev"].unique()
    mv = mv[mv["ev"].isin(flagged)]
    wide = mv.pivot_table(index="ev", columns="source", values="val", aggfunc="first")
    info = fine.groupby("ev").agg(tour=("tour", "first"), year=("year", "first"), name=("tournament_name", "first"),
                                  stage0_level=("level", "first"))
    out = info.loc[flagged].join(wide)
    frame = set(X.model_frame_ids())
    out["frame_matches"] = fine[fine["match_id"].isin(frame)].groupby("ev")["match_id"].nunique()         .reindex(out.index).fillna(0).astype(int)
    verdicts = []
    for ev, r in out.iterrows():
        off = None
        for c in ("wta_site", "wta_api"):
            if c in r and isinstance(r[c], str):
                off = r[c]
                break
        name = str(r["name"]).lower().replace(".", "")
        finale = ("champions" in name or "next gen" in name or "nextgen" in name or "finals" in name)
        if off is not None:
            v = ("stage0_right" if off == r["stage0_level"] else "stage0_wrong", off, "the WTA's own record")
        elif finale:
            v = ("definitional", r["stage0_level"], "a season finale filed under a 250 code by the other source")
        else:
            hit = None
            for (k, y), val in ATP_LEVEL_KNOWLEDGE.items():
                if k in name and (y is None or int(r["year"]) == y) and r["tour"] == "atp":
                    hit = val
            if hit:
                v = ("stage0_right" if hit[0] == r["stage0_level"] else "stage0_wrong", hit[0],
                     f"general knowledge ({hit[2]}): {hit[1]}")
            else:
                v = ("unresolved", None, "no official record held; not judged")
        verdicts.append(v)
    out["verdict"] = [v[0] for v in verdicts]
    out["right_level"] = [v[1] for v in verdicts]
    out["basis"] = [v[2] for v in verdicts]
    return out.reset_index().sort_values(["tour", "year", "name"])


# ------------------------------------------------------------------------------------------------ round, best-of, draw

def rbd(r: pd.DataFrame, m: pd.DataFrame) -> None:
    # round: the link files' own round agreement flag (the linker's grading), and the self-linked sources' rd
    rows = []
    for s in ["tennis_data", "open_tennis_data", "api_tennis", "flashscore", "slam_feeds", "wta_api", "tdi",
              "sofascore", "live_tennis_api", "infosys", "match_charting", "pbp_copy", "tml_days"]:
        lk = C.links(s, ["match_id", "round_agrees"])
        lk = lk.join(m[["tour", "level", "qualifying"]], on="match_id")
        g = lk.groupby(["tour", "qualifying"])["round_agrees"].agg(
            links="size", agree=lambda v: int(v.eq(True).sum()), differ=lambda v: int(v.eq(False).sum()))
        rows.append(g.reset_index().assign(source=s))
    for s in ("tennislive", "wta_site"):
        lk = pd.read_parquet(X.WORK / f"selflink_{s}.parquet", columns=["match_id", "rd"])
        lk = lk.join(m[["tour", "qualifying"]], on="match_id")
        g = lk.groupby(["tour", "qualifying"])["rd"].agg(links="size", agree=lambda v: int(v.eq(2).sum()),
                                                         differ=lambda v: int(v.eq(0).sum()))
        rows.append(g.reset_index().assign(source=s))
    rt = pd.concat(rows, ignore_index=True)
    rt["differ_pct_of_compared"] = (100 * rt["differ"] / (rt["agree"] + rt["differ"]).where(lambda v: v > 0)).round(3)
    rt.to_csv(X.OUT / "round_by_source.csv", index=False)
    # best-of
    x = r[r["source"].isin(["tennis_data", "live_tennis_api", "tml", "open_tennis_data"])][
        ["match_id", "source", "best_of_raw"]].copy()
    x["src"] = x["best_of_raw"].map(lambda v: X.int_or_none(re.sub(r"[^0-9]", "", str(v))) if not X.blank(v) else None)
    x = x[x["src"].isin([3, 5])].join(m[["best_of", "tour", "level"]], on="match_id")
    x["agree"] = x["src"] == x["best_of"]
    bo = x.groupby(["source", "tour", "level"]).agg(matches=("match_id", "size"), agree=("agree", "sum")).reset_index()
    bo.to_csv(X.OUT / "bestof_by_source.csv", index=False)
    dis = x[~x["agree"]].join(m[["tournament_name", "year", "score"]], on="match_id", rsuffix="_s0")
    dis.groupby(["source", "tour", "year", "tournament_name", "best_of", "src"]).size().rename("matches") \
        .reset_index().sort_values("matches", ascending=False).to_csv(X.OUT / "bestof_disagreements.csv", index=False)
    # draw size: TML's per match, the WTA's editions per main draw
    d = r[r["source"].eq("tml")][["match_id", "draw_raw"]].copy()
    d["src"] = d["draw_raw"].map(X.int_or_none)
    d = d.join(m[["draw_size", "tour", "tournament_id", "tournament_date", "tournament_name", "year", "qualifying"]],
               on="match_id")
    d["ev"] = event_key(d)
    de = d.groupby("ev").agg(tour=("tour", "first"), name=("tournament_name", "first"), year=("year", "first"),
                             stage0=("draw_size", modal), tml=("src", modal), matches=("match_id", "size"),
                             qualifying=("qualifying", "max"))
    w = r[r["source"].eq("wta_api")][["match_id", "source_key"]].copy()
    k = w["source_key"].str.extract(r"^wta:(?P<tid>[^/]+)/(?P<year>\d{4})/")
    ed = pd.read_parquet(C.DUMP / "points" / "wta" / "editions.parquet", columns=["tournament_id", "year",
                                                                                  "singles_draw_size"])
    ed["year"] = ed["year"].astype(int).astype(str)
    ed = ed.drop_duplicates(["tournament_id", "year"]).set_index(["tournament_id", "year"])
    w["src"] = ed.reindex(pd.MultiIndex.from_arrays([k["tid"].astype(str), k["year"].astype(str)]))[
        "singles_draw_size"].map(X.int_or_none).to_numpy()
    w = w.join(m[["draw_size", "tour", "tournament_id", "tournament_date", "tournament_name", "year", "qualifying"]],
               on="match_id")
    w = w[~w["qualifying"]]
    w["ev"] = event_key(w)
    we = w.groupby("ev").agg(tour=("tour", "first"), name=("tournament_name", "first"), year=("year", "first"),
                             stage0=("draw_size", modal), wta_editions=("src", modal), matches=("match_id", "size"))
    out = pd.concat([de.assign(kind="tml"), we.assign(kind="wta_editions")])
    out["other"] = out["tml"].where(out["kind"].eq("tml"), out.get("wta_editions"))
    out = out[out["other"].notna() & out["stage0"].notna()]
    out["agree"] = out["stage0"].astype(float) == out["other"].astype(float)
    out.groupby("kind")["agree"].agg(events="size", agree="sum").reset_index().to_csv(X.OUT / "draw_by_source.csv",
                                                                                     index=False)
    out[~out["agree"]].reset_index().to_csv(X.OUT / "draw_events.csv", index=False)
    X.log(f"round/best-of/draw written; draw events agreeing {out.groupby('kind')['agree'].mean().round(4).to_dict()}")


# ------------------------------------------------------------------------------------------------ dates

DATE_SOURCES = ["tennis_data", "open_tennis_data", "api_tennis", "flashscore", "slam_feeds", "wta_api", "tdi",
                "sofascore", "live_tennis_api", "infosys", "match_charting", "pbp_copy", "tml_days"]


def dates(m: pd.DataFrame) -> None:
    frames = []
    for s in DATE_SOURCES:
        lk = C.links(s, ["match_id", "date_local", "start_utc", "date_basis", "link_method"])
        frames.append(lk.assign(source=s))
    L = pd.concat(frames, ignore_index=True)
    L = L[L["date_local"].notna()].copy()
    L["day"] = pd.to_datetime(L["date_local"]).astype("datetime64[ns]")
    L["loose"] = L["date_basis"].ne("local")
    L = L.join(m[["tour", "level", "qualifying", "year", "tdate"]], on="match_id")
    L["off_tdate"] = (L["day"] - L["tdate"]).dt.days
    # leave-one-out: each link's day against the median day of the match's other sources (independent of it)
    g = L.groupby("match_id")["day"]
    n = g.transform("size")
    L["n_sources"] = n
    multi = L[n >= 2].copy()
    med = []
    days = multi.groupby("match_id")["day"].apply(list)
    for mid, d, src in zip(multi["match_id"], multi["day"], multi["source"]):
        others = [x for x in days[mid]]
        others.remove(d)
        med.append(pd.Series(others).median())
    multi["others_median"] = med
    multi["diff_vs_others"] = (multi["day"] - pd.to_datetime(multi["others_median"])).dt.days
    tol = np.where(multi["loose"], 2, 1)
    multi["off_more_than_a_day"] = multi["diff_vs_others"].abs() > tol
    bs = multi.groupby(["source", "date_basis"]).agg(links=("match_id", "size"),
                                                     off=("off_more_than_a_day", "sum"),
                                                     mean_diff=("diff_vs_others", "mean")).reset_index()
    bs["off_pct"] = (100 * bs["off"] / bs["links"]).round(3)
    bs.to_csv(X.OUT / "dates_by_source.csv", index=False)
    # pairwise
    piv = L.pivot_table(index="match_id", columns="source", values="day", aggfunc="first")
    pr = []
    for i, a in enumerate(DATE_SOURCES):
        for b in DATE_SOURCES[i + 1:]:
            if a not in piv or b not in piv:
                continue
            x = piv[[a, b]].dropna()
            if x.empty:
                continue
            dd = (x[a] - x[b]).dt.days.abs()
            pr.append({"a": a, "b": b, "matches": int(len(x)), "same_day": int((dd == 0).sum()),
                       "one_day": int((dd == 1).sum()), "more_than_one_day": int((dd > 1).sum()),
                       "more_than_one_day_pct": round(100 * float((dd > 1).mean()), 3)})
    pd.DataFrame(pr).to_csv(X.OUT / "dates_pairwise.csv", index=False)
    # the leak-proof clock: every source's day inside [es, lf] (a UTC-basis day: inside [es - 1, lf + 1])
    tp = C.STUDIES / "match_timing" / "timing.parquet"
    t = pd.read_parquet(tp, columns=["match_id", "es", "lf", "exact", "rejected_links", "demoted", "conflict", "sources",
                                     "outvoted_source", "window_basis"])
    t = t.set_index("match_id")
    L = L.join(t, on="match_id")
    # es and lf are days since 1970-01-01 (match_timing.common.to_day)
    es, lf = pd.to_datetime(L["es"], unit="D"), pd.to_datetime(L["lf"], unit="D")
    L["es"], L["lf"] = es, lf
    # a day the timeline itself reads as +-1 (match_timing.timing: a UTC day; LOOSE_CLOCK sources), and tennis-data's
    # UK calendar day where its link says the venue is four or more hours from the UK (uk_day_venue_west: an evening
    # start in the Americas carries the next day; _east: a morning start in Asia-Pacific the previous day)
    lm = L["link_method"].astype(str)
    lo_slack = np.where(L["loose"] | L["source"].isin(["infosys", "match_charting", "tml_days"])
                        | lm.str.contains("uk_day_venue_east", regex=False), 1, 0)
    hi_slack = np.where(L["loose"] | L["source"].isin(["infosys", "match_charting", "tml_days"])
                        | lm.str.contains("uk_day_venue_west", regex=False), 1, 0)
    lo_t, hi_t = pd.to_timedelta(lo_slack, unit="D"), pd.to_timedelta(hi_slack, unit="D")
    L["inside_strict"] = (L["day"] >= es) & (L["day"] <= lf)
    L["inside_clock"] = (L["day"] >= es - lo_t) & (L["day"] <= lf + hi_t)
    L["outside_by"] = np.where(L["day"] < es - lo_t, (L["day"] - (es - lo_t)).dt.days,
                               np.where(L["day"] > lf + hi_t, (L["day"] - (lf + hi_t)).dt.days, 0))
    ck = L.groupby(["source", "date_basis"]).agg(links=("match_id", "size"),
                                                 outside_strict=("inside_strict", lambda s: int((~s).sum())),
                                                 outside=("inside_clock", lambda s: int((~s).sum())),
                                                 before_es=("outside_by", lambda s: int((s < 0).sum())),
                                                 after_lf=("outside_by", lambda s: int((s > 0).sum()))).reset_index()
    ck.to_csv(X.OUT / "dates_clock.csv", index=False)
    out_rows = L[~L["inside_clock"]].copy()
    out_rows["outvoted_by_timeline"] = [isinstance(v, str) and src in v.split(";")
                                        for v, src in zip(out_rows["outvoted_source"], out_rows["source"])]
    out_rows["direction"] = np.where(out_rows["outside_by"] < 0, "before_es", "after_lf")
    counted = out_rows[~out_rows["outvoted_by_timeline"]]
    counted[["match_id", "source", "day", "es", "lf", "outside_by", "direction", "date_basis", "window_basis",
             "sources", "link_method"]].assign(day=lambda d: d["day"].dt.strftime("%Y-%m-%d"),
                                               es=lambda d: d["es"].dt.strftime("%Y-%m-%d"),
                                               lf=lambda d: d["lf"].dt.strftime("%Y-%m-%d"))         .sort_values(["direction", "source", "match_id"]).to_csv(X.OUT / "dates_outside_clock.csv", index=False)
    X.WORK.mkdir(parents=True, exist_ok=True)
    L[["match_id", "source", "day", "date_basis", "link_method", "off_tdate", "es", "lf", "inside_clock",
       "outside_by"]].to_parquet(X.WORK / "dates_links.parquet", index=False)
    # Stage 0's tournament date against the match days: the day's offset from it, by level and phase
    off = L.groupby(["tour", "level", "qualifying"])["off_tdate"].describe(percentiles=[0.005, 0.5, 0.995])
    summ = {"links_with_a_day": int(len(L)), "matches_with_a_day": int(L["match_id"].nunique()),
            "matches_with_two_or_more_days": int(multi["match_id"].nunique()),
            "links_outside_clock": int(len(out_rows)),
            "links_outside_clock_by_source": out_rows["source"].value_counts().to_dict(),
            "links_outside_clock_outvoted_by_the_timeline": int(out_rows["outvoted_by_timeline"].sum()),
            "links_outside_clock_counted_by_the_timeline": int(len(counted)),
            "counted_outside_by_direction_source": counted.groupby(["direction", "source"]).size().rename("links")
                                                   .reset_index().to_dict("records"),
            "links_outside_clock_examples": out_rows.sort_values("outside_by").head(15)[
                ["match_id", "source", "day", "es", "lf", "date_basis", "link_method"]].astype(str).to_dict("records"),
            "matches_outside_clock_with_rejected_or_demoted_link": int(
                out_rows.drop_duplicates("match_id").pipe(lambda d: (d["rejected_links"].fillna(0).astype(float) > 0)
                                                          | d["demoted"].notna()).sum()),
            "matches_outside_clock": int(out_rows["match_id"].nunique()),
            "outside_by_days": out_rows["outside_by"].clip(-30, 30).value_counts().sort_index().to_dict(),
            "day_minus_tournament_date": off.round(2).reset_index().to_dict("records"),
            "links_outside_minus10_plus21": int(((L["off_tdate"] < -10) | (L["off_tdate"] > 21)).sum()),
            "links_flagged_outside_plausible_days": int(L["link_method"].astype(str).str.contains(
                "outside_plausible_days").sum()),
            "timing_file": str(tp.relative_to(C.ROOT)).replace("\\", "/"),
            "timing_sha256": C.sha256(tp)}
    X.write_json(X.OUT / "dates_summary.json", summ)
    X.log(f"dates: {summ['links_outside_clock']:,} links outside the clock; by source "
          f"{summ['links_outside_clock_by_source']}")


# ------------------------------------------------------------------------------------------------ seeds

def seeds(r: pd.DataFrame, m: pd.DataFrame) -> None:
    x = r[r["source"].isin(["wta_api", "slam_feeds", "tdi", "infosys", "sofascore", "open_tennis_data", "tennislive",
                            "tml"])][["match_id", "source", "family", "seed_a_src", "seed_b_src"]]
    x = x.join(m[["seed_a", "seed_b", "tour", "level", "qualifying"]], on="match_id")
    long = pd.concat([x[["match_id", "source", "family", "tour", "level", "qualifying", "seed_a", "seed_a_src"]]
                      .set_axis(["match_id", "source", "family", "tour", "level", "qualifying", "s0", "src"], axis=1),
                      x[["match_id", "source", "family", "tour", "level", "qualifying", "seed_b", "seed_b_src"]]
                      .set_axis(["match_id", "source", "family", "tour", "level", "qualifying", "s0", "src"], axis=1)])
    long["cls"] = np.select([long["s0"].isna() & long["src"].isna(), long["s0"].notna() & long["src"].notna()
                             & (long["s0"] == long["src"]), long["s0"].notna() & long["src"].notna(),
                             long["s0"].notna(), long["src"].notna()],
                            ["neither", "both_equal", "both_differ", "stage0_only", "source_only"], "?")
    t = long.groupby(["source", "tour", "qualifying", "cls"]).size().unstack(fill_value=0).reset_index()
    for c in ("neither", "both_equal", "both_differ", "stage0_only", "source_only"):
        if c not in t:
            t[c] = 0
    t["both_seeded"] = t["both_equal"] + t["both_differ"]
    t["differ_pct_of_both"] = (100 * t["both_differ"] / t["both_seeded"].where(t["both_seeded"] > 0)).round(3)
    t.to_csv(X.OUT / "seeds_by_source.csv", index=False)
    ex = long[long["cls"].eq("both_differ")].join(m[["tournament_name", "year", "round"]], on="match_id")
    ex.groupby(["source", "tour", "year", "tournament_name"]).size().rename("player_rows").reset_index() \
        .sort_values("player_rows", ascending=False).to_csv(X.OUT / "seeds_differ_events.csv", index=False)
    X.log("seeds written")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all")
    args = ap.parse_args()
    parts = ["surface", "indoor", "level", "rbd", "dates", "seeds"] if args.part == "all" else args.part.split(",")
    m = s0()
    r = load() if set(parts) - {"dates"} else None
    for p in parts:
        X.log(f"part {p}")
        if p == "dates":
            dates(m)
        else:
            globals()[p](r, m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
