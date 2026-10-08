"""Source 3, sofascore: SofaScore events of the three collections the earlier studies downloaded, staged under
data/dump/points/: sofascore/ (the ten sampled careers, 2012-2026, every level and ITF), sofascore_editions/ (ATP tour
level, 2025 to June 2026, qualifying included) and sofascore_tournaments/ (Australian Open and Roland Garros 2022-26 with
qualifying, men and women, and a few US Open and Wimbledon seasons). Each staged events table lists every event the
collection listed, fetched or not, so the listed-but-unlinked events (AO/RG qualifying, ...) are linked here too.

Day and time: startTimestamp (UTC seconds), SofaScore's listed start. The venue zone comes from the event's own
tournament name ("Valencia, Spain"; "Manacor, Singles M-ITF-ESP-02A"; "Spain F30, Singles"), else from the linked
Stage 0 event's country and city (srcc_tz: one-zone countries, or a city in a multi-zone country); else the UTC day.

Linking: identity (srcc_common.link) against Stage 0 of the event's tour (ATP, Challenger, ITF Men, Davis Cup -> atp;
WTA, ITF Women -> wta; exhibitions and juniors are out of scope), with SofaScore's team ids for the id pass. The earlier
studies' links are then translated to Stage 0 by exact names and tournament week (their keys are the data map's uid or
the career study's ref_id, not Stage 0 match ids) and compared with the identity links:
    data/studies/gap_downloads/sofascore_atp_points_2025_matches.csv   (editions; map uid -> event_id)
    data/studies/ao_rg_points/sofascore_links.csv                        (AO/RG main draws; map uid -> event_id)
    data/studies/point_shot_sources/sofascore_links.csv                  (careers; ref_id -> sofa_id)
An event the identity pass leaves unlinked but a prior link places on a free Stage 0 match whose set scores or round
agree is added with link_method 'prior_link'.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.eda.match_timing import srcc_common as K
from src.eda.match_timing import srcc_tz as TZ

SOURCE = "sofascore"
COLLECTIONS = ("sofascore", "sofascore_editions", "sofascore_tournaments")
STUDIES = K.ROOT / "data" / "studies"
PRIOR = {
    "gap_downloads": STUDIES / "gap_downloads" / "sofascore_atp_points_2025_matches.csv",
    "ao_rg_points": STUDIES / "ao_rg_points" / "sofascore_links.csv",
    "point_shot_sources": STUDIES / "point_shot_sources" / "sofascore_links.csv",
}
COLS = (["event_id", "start_timestamp", "tournament_name", "unique_tournament_name", "category_name", "season_year",
         "round_name", "status_type", "status_description", "doubles", "winner_code", "home_id", "home_name",
         "away_id", "away_name"] + [f"{s}_set{k}" for k in range(1, 6) for s in ("home", "away")])
TOUR = {"ATP": "atp", "Challenger": "atp", "ITF Men": "atp", "Davis Cup": "atp", "WTA": "wta", "ITF Women": "wta",
        "WTA 125": "wta", "Billie Jean King Cup": "wta"}
FINISHED = {"Ended", "Retired", "Walkover"}


END_COLS = ["change_timestamp"]     # for a finished match, within a minute of its last point (sofascore.py)


def load() -> pd.DataFrame:
    frames = []
    for c in COLLECTIONS:
        path = K.DUMP / "points" / c / "events.parquet"
        have = set(pq.read_schema(path).names)          # END_COLS staged from 5 Oct 2026 (sofascore.py); older files lack them
        t = pq.read_table(path, columns=COLS + [x for x in END_COLS if x in have]).to_pandas()
        frames.append(t.assign(collection=c))
    t = pd.concat(frames, ignore_index=True)
    coll = t.groupby("event_id")["collection"].agg(lambda s: ";".join(sorted(set(s))))
    t = t.drop_duplicates("event_id").copy()
    t["collections"] = t["event_id"].map(coll)
    return t.reset_index(drop=True)


SKIP_PART = re.compile(r"^(singles|doubles|qualifying|main|men|women|boys|girls|mens|womens)\b", re.I)


def place(name) -> tuple[str | None, str | None]:
    """(IOC country, city) read from a SofaScore tournament name; either may be None."""
    s = str(name or "")
    m = re.search(r"\b[MW]-ITF-([A-Z]{3})-", s)
    country = m.group(1) if m else None
    parts = [p.strip() for p in s.split(",") if p.strip()]
    keep = [p for p in parts if not SKIP_PART.match(p) and not re.search(r"[MW]-ITF-", p)]
    cpart = None
    if country is None:
        for p in reversed(keep):
            q = re.sub(r"\b(19|20)\d{2}\b|\bF\d+\b", " ", p)
            c = TZ.country_code(q)
            if c:
                country, cpart = c, p
                break
    city = None
    # the city is the part just before the country ("Australian Open, Melbourne, Australia"), else the first part
    if cpart in keep and keep.index(cpart) > 0:
        cand = keep[keep.index(cpart) - 1]
    else:
        cand = keep[0] if keep and keep[0] != cpart else None
    if cand:
        city = re.sub(r"\b(itf|[mw]\d{2,3}|men|women)\b", " ", TZ.norm_place(cand))
        city = re.sub(r"\b\d+\b", " ", city)
        city = " ".join(city.split()) or None
    return country, city


def is_qual(tname, rnd) -> object:
    if "qualif" in str(tname or "").lower() or (isinstance(rnd, str) and rnd.startswith("Q") and rnd != "QF"):
        return True
    if isinstance(rnd, str) and rnd in ("R128", "R64", "R32", "R16", "QF", "SF", "F"):
        return False
    return None


def prior_links(s0: pd.DataFrame) -> pd.DataFrame:
    """The earlier studies' event links, each translated to a Stage 0 match by exact full names (either order) and a
    tournament date within 7 days of the study's date. Returns (event_id, prior, prior_key, prior_mid)."""
    rows = []
    g = pd.read_csv(PRIOR["gap_downloads"], dtype=str)
    g = g[g["event_id"].notna()]
    rows.append(pd.DataFrame({"event_id": g["event_id"], "prior": "gap_downloads", "prior_key": "uid:" + g["uid"],
                              "tour": g["tour"].map({"M": "atp", "W": "wta"}), "d": g["d"], "n1": g["name1"],
                              "n2": g["name2"], "rnd": g["ss_round"].map(K.round_code)}))
    a = pd.read_csv(PRIOR["ao_rg_points"], dtype=str)
    a = a[a["event_id"].notna()]
    rows.append(pd.DataFrame({"event_id": a["event_id"], "prior": "ao_rg_points", "prior_key": "uid:" + a["map_uid"],
                              "tour": a["tour"].map({"M": "atp", "W": "wta"}), "d": a["d"], "n1": a["name1"],
                              "n2": a["name2"], "rnd": a["ss_round"].map(K.round_code)}))
    c = pd.read_csv(PRIOR["point_shot_sources"], dtype=str)
    c = c[c["sofa_id"].notna() & c["sofa_status"].eq("linked")]
    rows.append(pd.DataFrame({"event_id": c["sofa_id"], "prior": "point_shot_sources", "prior_key": c["ref_id"],
                              "tour": "atp", "d": c["event_date"], "n1": c["player"],
                              "n2": (c["opp_first"].fillna("") + " " + c["opp_last"].fillna("")).str.strip(),
                              "rnd": c["round"].map(K.round_code)}))
    p = pd.concat(rows, ignore_index=True)
    p["event_id"] = pd.to_numeric(p["event_id"], errors="coerce").astype("Int64").astype(str)
    p["d"] = pd.to_datetime(p["d"], errors="coerce")
    p["k"] = [pair_key(x, y) for x, y in zip(p["n1"], p["n2"])]
    s = s0[s0["tdate"] >= "2011-12-01"][["match_id", "tour", "tdate", "name_a", "name_b", "round"]].copy()
    s["k"] = [pair_key(x, y) for x, y in zip(s["name_a"], s["name_b"])]
    j = p.merge(s, on=["tour", "k"])
    # the study's date is a tournament week (2026 rows of the map: a match day), so +-14 days, and where the pair met
    # twice in that span, the candidate in the round SofaScore gives
    j = j[(j["tdate"] - j["d"]).dt.days.abs() <= 14]
    j["rd_ok"] = j["rnd"].isna() | j["rnd"].eq(j["round"])
    best = j.groupby(["prior", "prior_key"])["rd_ok"].transform("max")
    j = j[j["rd_ok"] | ~best]
    n = j.groupby(["prior", "prior_key"])["match_id"].nunique()
    j = j[j.set_index(["prior", "prior_key"]).index.isin(n.index[n == 1])]
    out = p.merge(j[["prior", "prior_key", "match_id"]].drop_duplicates(), on=["prior", "prior_key"], how="left")
    return out.rename(columns={"match_id": "prior_mid"})[["event_id", "prior", "prior_key", "prior_mid"]]


def pair_key(a, b) -> str:
    ka, kb = K.name_info(a)[0], K.name_info(b)[0]
    return "|".join(sorted([ka, kb])) if ka and kb else ""


def run() -> dict:
    s0 = K.stage0()
    ev = load()
    ev["tour"] = ev["category_name"].map(TOUR)
    ev["single"] = ev["doubles"].astype(str).str.upper().eq("FALSE") & ~ev["home_name"].astype(str).str.contains("/") \
        & ~ev["away_name"].astype(str).str.contains("/")
    ev["finished"] = ev["status_description"].isin(FINISHED)
    ev["ts"] = pd.to_datetime(pd.to_numeric(ev["start_timestamp"], errors="coerce"), unit="s", utc=True)
    scope = ev[ev["tour"].notna() & ev["single"] & ev["finished"] & ev["ts"].notna()].copy().reset_index(drop=True)
    scope["rnd"] = scope["round_name"].map(K.round_code)
    scope["qual"] = [is_qual(t, r) for t, r in zip(scope["tournament_name"], scope["rnd"])]
    pl = scope["tournament_name"].map(place)
    scope["country"] = pl.str[0]
    scope["city"] = pl.str[1]
    scope["sid"] = "sofascore:" + scope["event_id"].astype(str)
    walk = scope["status_description"].eq("Walkover")
    src = pd.DataFrame({
        "sid": scope["sid"], "tour": scope["tour"], "day": K.utc_day(scope["ts"]),
        "p1": scope["home_name"], "p2": scope["away_name"],
        "sets": [() if w else K.sets_from_pairs([(r[f"home_set{k}"], r[f"away_set{k}"]) for k in range(1, 6)])
                 for w, (_, r) in zip(walk, scope.iterrows())],
        "rnd": scope["rnd"], "qual": scope["qual"], "tid": None,
        "id1": scope["home_id"].astype(str), "id2": scope["away_id"].astype(str)})
    lo, hi = src["day"].min() - pd.Timedelta(days=30), src["day"].max() + pd.Timedelta(days=30)
    sl = s0[s0["tour"].isin(src["tour"].unique()) & (s0["tdate"] >= lo) & (s0["tdate"] <= hi)]
    K.log(f"[sofascore] {len(src):,} singles events to link against {len(sl):,} Stage 0 matches")
    res = K.link(src, sl)
    links = res["links"].copy()
    links["method"] = "identity_" + links["pass"]
    # the earlier studies' links, translated, against the identity links
    pr = prior_links(s0)
    pr["sid"] = "sofascore:" + pr["event_id"]
    mine = links.set_index("sid")["match_id"]
    pr["mine"] = pr["sid"].map(mine)
    pr["verdict"] = np.select(
        [pr["prior_mid"].isna(), pr["mine"].isna(), pr["mine"] == pr["prior_mid"]],
        ["prior row not translatable to Stage 0", "identity found no link", "same Stage 0 match"],
        "different Stage 0 match")
    agree = set(pr.loc[pr["verdict"].eq("same Stage 0 match"), "sid"])
    differ = set(pr.loc[pr["verdict"].eq("different Stage 0 match"), "sid"])
    links.loc[links["sid"].isin(agree), "method"] += ";prior_link_agrees"
    links.loc[links["sid"].isin(differ), "method"] += ";prior_link_differs"
    # prior links where identity found none: kept when the Stage 0 match is free and scores or round agree
    add = pr[pr["verdict"].eq("identity found no link") & pr["sid"].isin(set(src["sid"]))]
    add = add.drop_duplicates("sid")
    add = add[~add["prior_mid"].isin(set(links["match_id"]))].drop_duplicates("prior_mid")
    added = 0
    if len(add):
        si = src.set_index("sid")
        sm = s0.set_index("match_id")
        rows = []
        for sid, mid in zip(add["sid"], add["prior_mid"]):
            r, m = si.loc[sid], sm.loc[mid]
            g1a = K.name_grade(r["p1"], m["name_a"]) + K.name_grade(r["p2"], m["name_b"])
            g1b = K.name_grade(r["p1"], m["name_b"]) + K.name_grade(r["p2"], m["name_a"])
            p1_side = "A" if g1a >= g1b else "B"
            p1_won = bool(m["a_won"]) == (p1_side == "A")
            s = r["sets"]
            sc = bool(s) and K.sets_equal(s if p1_won else tuple((b, a) for a, b in s), m["sets_w"])
            rd = K.round_grade(r["rnd"], m["round"], m["round_no"], bool(m["qualifying"]), m["qmax"])
            if sc or rd == 2:
                rows.append({"sid": sid, "match_id": mid, "sc": sc, "rd": rd, "pass": "prior_link",
                             "method": "prior_link", "p1_side": p1_side})
        if rows:
            links = pd.concat([links, pd.DataFrame(rows)], ignore_index=True)
            added = len(rows)
    for s in links["sid"]:
        res["reason"].loc[s] = "linked"
    # local days: the event's own place, else the Stage 0 event's country and city
    lk = links.merge(scope, on="sid", how="left")
    sm = s0.set_index("match_id")
    lk["s0_country"] = lk["match_id"].map(sm["country"])
    lk["s0_city"] = lk["match_id"].map(sm["tournament_name"]).map(K.s0_city)
    z_src = [TZ.zone_for(c, ci) if isinstance(c, str) else None for c, ci in zip(lk["country"], lk["city"])]
    z_s0 = [TZ.zone_for(c, ci) if isinstance(c, str) else None for c, ci in zip(lk["s0_country"], lk["s0_city"])]
    lk["zone"] = [a or b for a, b in zip(z_src, z_s0)]
    lk["zone_basis"] = np.where([a is not None for a in z_src], "event_place_zone",
                                np.where([b is not None for b in z_s0], "stage0_event_zone", "utc"))
    lk["day_local"] = K.local_day(lk["ts"], lk["zone"])
    lk["date_basis"] = np.where(lk["day_local"].notna(), "local", "utc_date")
    walk_l = lk["status_description"].eq("Walkover")
    # the finish: the record's last change (staged from 5 Oct 2026), on the same local clock; a finish on a later day
    # than the start is tagged as the point-feed linker tags a last point's day (timing.py caps it at three days)
    end_ts = pd.to_datetime(pd.to_numeric(lk.get("change_timestamp"), errors="coerce"), unit="s", utc=True)         if "change_timestamp" in lk else pd.Series(pd.NaT, index=lk.index, dtype="datetime64[ns, UTC]")
    end_day = K.local_day(end_ts, lk["zone"]).fillna(K.utc_day(end_ts))
    late = ((end_day - lk["day_local"].fillna(K.utc_day(lk["ts"]))).dt.days).where(~walk_l)
    end_tag = np.where(late.fillna(0) > 0, ";last_point_day+" + late.fillna(0).clip(lower=0).astype(int).astype(str), "")
    out = pd.DataFrame({
        "match_id": lk["match_id"], "source_key": lk["sid"],
        "date_local": lk["day_local"].fillna(K.utc_day(lk["ts"])),
        "start_utc": lk["ts"].where(~walk_l), "date_basis": lk["date_basis"],
        "link_method": lk["method"] + ";listed_start;" + lk["zone_basis"] + np.where(walk_l, ";walkover", "") + end_tag,
        "score_agrees": lk["sc"].astype("boolean"), "round_agrees": lk["rd"].map(K.rd_bool)})
    path = K.write_links(out, SOURCE)
    reason = res["reason"]
    diag = src.assign(reason=src["sid"].map(reason))
    diag = diag[diag["reason"] != "linked"].copy()
    diag["candidates"] = diag["sid"].map(lambda s: ";".join(res["ambiguous"].get(s, [])))
    diag["sets"] = diag["sets"].map(lambda t: " ".join(f"{a}-{b}" for a, b in t))
    diag = diag.merge(scope[["sid", "collections", "category_name", "tournament_name", "round_name"]], on="sid",
                      how="left").drop(columns=["id1", "id2"])
    K.write_diagnostics(diag, SOURCE)
    unresolved = lk[lk["zone_basis"].eq("utc")]
    return {
        "source": SOURCE, "file": str(path.relative_to(K.ROOT)),
        "method": "identity (srcc_common.link; SofaScore team ids for the id pass) against Stage 0 of the event's tour "
                  "within 30 days of the collections' span; earlier studies' links translated by exact names and "
                  "week and compared; startTimestamp (listed start, UTC) to the venue's day",
        "rows_read": int(len(ev)), "rows_by_collection": ev["collections"].value_counts().to_dict(),
        "out_of_scope": {"doubles": int((~ev["single"]).sum()),
                         "exhibition_junior_or_unknown_tour": int((ev["single"] & ev["tour"].isna()).sum()),
                         "not_finished": int((ev["single"] & ev["tour"].notna() & ~ev["finished"]).sum())},
        "singles_in_scope": int(len(src)),
        "in_scope_by_collection": scope["collections"].value_counts().to_dict(),
        "linked": int(len(out)),
        "ambiguous": int(reason.str.startswith("ambiguous").sum()),
        "unlinked": int(len(src) - len(out) - reason.str.startswith("ambiguous").sum()),
        "outcomes": K.outcome_counts(reason),
        "linked_by_pass": links["pass"].value_counts().to_dict(),
        "linked_by_collection": lk["collections"].value_counts().to_dict(),
        "unlinked_by_collection_category": diag.groupby(["collections", "category_name", "reason"]).size()
                                               .rename("rows").reset_index().to_dict("records"),
        "player_id_crosswalk_size": len(res["crosswalk"]),
        "prior_links": {"rows": int(len(pr)), "by_study_and_verdict": pr.groupby(["prior", "verdict"]).size()
                        .rename("rows").reset_index().to_dict("records"),
                        "added_where_identity_found_none": int(added),
                        "different_examples": pr[pr["verdict"].eq("different Stage 0 match")]
                        [["prior", "prior_key", "event_id", "prior_mid", "mine"]].head(20).to_dict("records")},
        "date_basis": out["date_basis"].value_counts().to_dict(),
        "zone_basis": lk["zone_basis"].value_counts().to_dict(),
        "utc_day_kept_for": unresolved.groupby(["country", "city"], dropna=False).size().rename("links")
                                      .reset_index().sort_values("links", ascending=False).head(30)
                                      .astype(str).to_dict("records"),
        "utc_day_kept_for_stage0_place": unresolved.groupby(["s0_country", "s0_city"], dropna=False).size()
                                                   .rename("links").reset_index().sort_values("links", ascending=False)
                                                   .head(30).astype(str).to_dict("records"),
        "with_start_utc": int(out["start_utc"].notna().sum()),
        "score_agrees": out["score_agrees"].value_counts(dropna=False).rename(str).to_dict(),
        "round_agrees": out["round_agrees"].value_counts(dropna=False).rename(str).to_dict(),
    }
