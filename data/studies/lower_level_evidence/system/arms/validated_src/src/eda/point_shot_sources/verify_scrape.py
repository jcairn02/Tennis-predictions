"""Check the study's SofaScore and TennisLive appraisal against the records actually downloaded.

Inputs: the ten players' official match list (career-coverage reference record), the SofaScore tables staged
by src/ingest/point_sources/sofascore.py and the TennisLive tables staged by src/ingest/point_sources/tennislive.py.

For every official match the script links the downloaded listings with the study's own rules (link_sofascore.link),
then records whether the linked event has a point-by-point record and whether that record is complete, meaning
each set has as many games as the official score. The study's claims are compared with the direct
measurement by level and period.

Outputs (data/studies/point_shot_sources/scrape/):
    verification_matches.csv    one row per official match: what each source holds for it
    verification_summary.json   coverage by level and period for each source and their union, next to the study's
                                claims; extra SofaScore records not on the official list
Usage:
    ./python.sh src/eda/point_shot_sources/verify_scrape.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PROJECT_ROOT = HERE.parents[2]

import link_sofascore as L  # noqa: E402
from pbp_checks import official_games  # noqa: E402

REFERENCE = PROJECT_ROOT / "data" / "studies" / "career_coverage" / "reference_record.csv"
STUDY = PROJECT_ROOT / "data" / "studies" / "point_shot_sources"
DUMP = PROJECT_ROOT / "data" / "dump" / "points"
OUT = STUDY / "scrape"
LEVELS = ["ITF main draw", "ITF qualifying", "Challenger main draw", "Challenger qualifying", "Tour qualifying",
          "Tour main draw", "Davis Cup"]
STUDY_SLUGS = {"CH12": "jan-choinski", "G0BY": "daniil-glinka", "H09P": "brandon-holt", "H0A4": "nick-hardt",
               "O0A2": "gauthier-onclin", "P0HY": "samuele-pieri", "P0I6": "gabriele-piraino",
               "S0GZ": "nikolas-sanchez-izquierdo", "V0F6": "nicolas-villalon", "W09E": "adam-walton"}
# The study's SofaScore point-marker shares (README table), per level and period, as "with/of".
STUDY_SOFASCORE = {
    "ITF main draw": {"2012-18": "91% of 238", "2019-21": "96% of 297", "2022-23": "98% of 310", "2024": "97% of 145",
                      "2025": "0 of 15 (read directly)", "2026": "7 of 8 (read directly)"},
    "Challenger main draw": {"2012-18": "35% of 26", "2019-21": "79% of 70", "2022-23": "1% of 213", "2024": "99% of 168",
                             "2025-26": "98% of 295"},
    "Challenger qualifying": {"2012-18": "4% of 27", "2019-21": "29% of 17", "2022-23": "0% of 88", "2024": "100% of 33",
                              "2025-26": "100% of 57"},
    "Tour qualifying": {"2012-18": "1 of 9", "2019-21": "1 of 2", "2022-23": "37% of 35", "2024": "100% of 30",
                        "2025-26": "98% of 59"},
    "Tour main draw": {"2022-23": "4 of 5", "2024": "100% of 11", "2025-26": "100% of 43"},
}
STUDY_TOTALS = {"official_matches": 4055, "with_point_or_shot_data_in_dump": 85, "need_points": 3959,
                "sofascore_linked_with_marker": 1746, "sofascore_expected_total": "about 2,930 (74% of 3,959)",
                "tennislive_in_sofascore_holes": "about 700 (at least 557), Challenger 2022-23 and ITF from March 2025",
                "free_plus_tennislive_expected": "about 92%"}


def period(level: str, year: int) -> str:
    if level == "ITF main draw" and year >= 2025:
        return str(year)
    if year <= 2018:
        return "2012-18"
    if year <= 2021:
        return "2019-21"
    if year <= 2023:
        return "2022-23"
    if year == 2024:
        return "2024"
    return "2025-26"


def reference() -> pd.DataFrame:
    ref = pd.read_csv(REFERENCE, dtype=str, keep_default_na=False)
    ref = ref[ref["is_bye"] != "True"].copy()
    ref["event_date"] = pd.to_datetime(ref["event_date"])
    ref["year"] = ref["event_date"].dt.year
    ref["day0"] = (ref["event_date"] - pd.Timestamp("1970-01-01")).dt.days
    ref[["win_lo", "win_hi"]] = pd.DataFrame(
        [L.play_window(t, lv, r) for t, lv, r in zip(ref["event_type"], ref["level"], ref["round"])], index=ref.index)
    ref["seen"] = True
    ref["period"] = [period(lv, y) for lv, y in zip(ref["level"], ref["year"])]
    ref["walkover"] = ref["score"].str.contains(r"W/O|DEF", case=False, regex=True) | ref["walkover"].eq("True")
    fill = STUDY / "fill_matrix.csv"
    if fill.exists():
        fm = pd.read_csv(fill, dtype=str, keep_default_na=False)
        if "needs_points" in fm.columns:
            ref = ref.merge(fm[["ref_id", "needs_points"]], on="ref_id", how="left")
            ref["needs_points"] = ref["needs_points"].eq("True")
    if "needs_points" not in ref.columns:
        ref["needs_points"] = ~ref["walkover"]
    return ref


def official_sets(score: str) -> list[int]:
    return official_games(score)


def _round_from_stage(stage_code: str) -> str:
    s = (stage_code or "").lower()
    if s.startswith("qualif"):
        return "Q"
    if "semifinal" in s:
        return "SF"
    if "quarterfinal" in s:
        return "QF"
    if s == "final" or s.endswith("_final") and "qualif" not in s:
        return "F"
    return ""


def sofascore_candidates(ref: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Downloaded SofaScore singles events in the linker's shape (one row per listing team), plus games per set."""
    path = DUMP / "sofascore" / "events.parquet"
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame()
    ev = pd.read_parquet(path)
    ev = ev[ev["doubles"] != "TRUE"].copy()
    summary = json.loads((STUDY / "sofascore_summary.json").read_text(encoding="utf-8"))
    code_of = {str(info["sofascore_id"]): code for code, info in summary["players"].items()}
    names = ref.drop_duplicates("code").set_index("code")["player"]
    rows = []
    for _, e in ev.iterrows():
        for team in str(e["listed_for_teams"] or "").split(";"):
            code = code_of.get(team)
            if not code:
                continue
            side = L.player_side(names[code], e["home_name"], e["away_name"])
            if not side:
                continue
            opponent = e["away_name"] if side == "home" else e["home_name"]
            tournament = e["tournament_name"] or ""
            rc = L.sofa_round(e["round_name"] or "")
            rows.append({"code": code, "sofa_id": e["event_id"], "ts": int(e["start_timestamp"] or 0),
                         "tournament": tournament, "category": e["category_name"], "sofa_round": e["round_name"],
                         "round_code": "Q" if "qualif" in tournament.lower() and not rc.startswith("Q") else rc,
                         "opponent": opponent, "status": e["status_type"], "first_to_serve": e["first_to_serve"],
                         "final_result_only": e["final_result_only"], "pbp_status": e["pbp_status"],
                         "stats_status": e["stats_status"], "pbp_games": e["pbp_games"], "pbp_points": e["pbp_points"]})
    cand = pd.DataFrame(rows)
    if len(cand):
        cand["days"] = cand["ts"] // 86400
    games = pd.DataFrame()
    points_path = DUMP / "sofascore" / "points.parquet"
    if points_path.exists():
        pts = pd.read_parquet(points_path, columns=["event_id", "set", "game"])
        pts["set"] = pd.to_numeric(pts["set"], errors="coerce")
        pts["game"] = pd.to_numeric(pts["game"], errors="coerce")
        games = pts.groupby(["event_id", "set"])["game"].max().reset_index().sort_values(["event_id", "set"])
        games = games.groupby("event_id")["game"].apply(lambda s: [int(x) for x in s]).rename("record_games")
    return cand, games


def tennislive_candidates(ref: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path = DUMP / "tennislive" / "index.parquet"
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    idx = pd.read_parquet(path)
    idx = idx[(idx["doubles"] != "TRUE") & idx["url"].notna()].copy()
    code_of = {slug: code for code, slug in STUDY_SLUGS.items()}
    names = ref.drop_duplicates("code").set_index("code")["player"]
    rows = []
    for _, e in idx.drop_duplicates(["slug", "url"]).iterrows():
        code = code_of.get(e["slug"])
        if not code:
            continue
        side = L.player_side(names[code], e["player1_name"] or "", e["player2_name"] or "")
        if not side:
            continue
        opponent = e["player2_name"] if side == "home" else e["player1_name"]
        rows.append({"code": code, "sofa_id": e["url"], "ts": int(e["start_timestamp"] or 0),
                     "tournament": e["tournament_name"] or "", "category": e["info"], "sofa_round": e["stage"],
                     "round_code": _round_from_stage(e["stage_code"]), "opponent": opponent, "status": e["state"],
                     "first_to_serve": "", "final_result_only": ""})
    cand = pd.DataFrame(rows)
    if len(cand):
        cand["days"] = cand["ts"] // 86400
    matches = pd.DataFrame()
    mpath = DUMP / "tennislive" / "matches.parquet"
    if mpath.exists():
        columns = ["url", "page_status", "pbp_available", "stats_available", "games_listed", "points_listed", "score"]
        import pyarrow.parquet as pq

        if "games_without_points" in pq.read_schema(mpath).names:
            columns.append("games_without_points")
        matches = pd.read_parquet(mpath, columns=columns).set_index("url")
        if "games_without_points" not in matches.columns:
            matches["games_without_points"] = None
    games = pd.DataFrame()
    gpath = DUMP / "tennislive" / "games.parquet"
    if gpath.exists():
        g = pd.read_parquet(gpath, columns=["url", "set", "game", "after"])
        g["set"] = pd.to_numeric(g["set"], errors="coerce")
        g["game"] = pd.to_numeric(g["game"], errors="coerce")
        g = g.sort_values(["url", "set", "game"])
        last = g.groupby(["url", "set"]).tail(1).copy()
        last["after_sum"] = last["after"].map(_score_sum)
        per = last.sort_values(["url", "set"])
        games = per.groupby("url").apply(lambda d: {"record_games": [int(x) for x in d["game"]],
                                                    "last_after": [x for x in d["after_sum"]]}, include_groups=False)
    return cand, matches, games


def _score_sum(text) -> int | None:
    m = re.fullmatch(r"(\d+)-(\d+)", str(text or "").strip())
    return int(m.group(1)) + int(m.group(2)) if m else None


def short_kind(official: list[int], record: list[int], last_after: list) -> str | None:
    """For a short TennisLive record: are the missing games only the games that closed a set?

    The site's pages often stop a set's game list one game early: the listed games run to the state before
    the set's last game (its "after" score sums to one game fewer than the official set). "set closers only"
    means every deficit is of that kind; "other" means games are missing elsewhere as well."""
    if not isinstance(record, list) or not official or not last_after:
        return None
    closers_only = True
    for i, official_games_in_set in enumerate(official):
        listed = record[i] if i < len(record) else 0
        after = last_after[i] if i < len(last_after) else None
        deficit = official_games_in_set - listed
        if deficit <= 0:
            continue
        if not (deficit == 1 and after == official_games_in_set - 1):
            closers_only = False
    return "set closers only" if closers_only else "other"


def link_source(ref: pd.DataFrame, cand: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if not len(cand):
        return pd.DataFrame({"ref_id": ref["ref_id"], f"{prefix}_status": "no download"})
    links = L.link(ref, cand)
    keep = {"sofa_status": f"{prefix}_status", "sofa_id": f"{prefix}_id", "sofa_ts": f"{prefix}_ts",
            "sofa_tournament": f"{prefix}_tournament", "sofa_round": f"{prefix}_round", "sofa_opponent": f"{prefix}_opponent",
            "name_score": f"{prefix}_name_score", "round_agree": f"{prefix}_round_agree", "place_agree": f"{prefix}_place_agree",
            "days_outside_window": f"{prefix}_days_outside", "first_to_serve": f"{prefix}_first_to_serve",
            "event_state": f"{prefix}_state"}
    return links.rename(columns=keep)[["ref_id"] + [v for k, v in keep.items() if k in links.columns]]


COMPLETE = {"exact", "unfinished game listed", "match tiebreak as one game"}


def completeness(official: list[int], record) -> str | None:
    """How a record's games per set compare with the official score.

    "exact": the same games in every set. "unfinished game listed": a retirement whose record also lists the
    game in progress (one more game in the last set, or a new set with one game). "match tiebreak as one
    game": the official score writes the deciding tiebreak as a set score such as 6-10, the record as one
    game. "short": the record stops early. "long": the record has games the official score does not."""
    if not isinstance(record, list) or not official:
        return None
    if record == official:
        return "exact"
    if record == official[:-1] + [official[-1] + 1] or record == official + [1]:
        return "unfinished game listed"
    if official[-1] >= 16 and record == official[:-1] + [1]:
        return "match tiebreak as one game"
    if len(record) < len(official) or any(r < o for r, o in zip(record, official)):
        return "short"
    return "long"


def complete(official: list[int], record) -> bool | None:
    kind = completeness(official, record)
    return None if kind is None else kind in COMPLETE


def share_table(df: pd.DataFrame, flag: str, group: list[str]) -> list[dict]:
    rows = []
    for keys, g in df.groupby(group, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        rows.append({**dict(zip(group, keys)), "official": int(len(g)), "need_points": int(g["needs_points"].sum()),
                     flag: int(g[flag].sum()), f"{flag}_share": round(float(g[flag].mean()), 3) if len(g) else None})
    return rows


def main():
    ref = reference()
    sofa_cand, sofa_games = sofascore_candidates(ref)
    tl_cand, tl_matches, tl_games = tennislive_candidates(ref)
    out = ref.merge(link_source(ref, sofa_cand, "sofa"), on="ref_id", how="left")
    out = out.merge(link_source(ref, tl_cand, "tl"), on="ref_id", how="left")
    out["official_games"] = out["score"].map(official_sets)

    # SofaScore: does the linked event have a record, is it complete, does it have a box score
    if len(sofa_cand):
        ev = sofa_cand.drop_duplicates("sofa_id").set_index("sofa_id")
        out["sofa_pbp_status"] = out["sofa_id"].map(ev["pbp_status"])
        out["sofa_stats_status"] = out["sofa_id"].map(ev["stats_status"])
        out["sofa_record_games"] = out["sofa_id"].map(sofa_games) if len(sofa_games) else None
    else:
        out["sofa_pbp_status"] = out["sofa_stats_status"] = out["sofa_record_games"] = None
    out["sofa_linked"] = out["sofa_status"].isin(["linked", "ambiguous"])
    out["sofa_pbp"] = out["sofa_linked"] & out["sofa_pbp_status"].eq("200")
    out["sofa_stats"] = out["sofa_linked"] & out["sofa_stats_status"].eq("200")
    out["sofa_completeness"] = [completeness(o, r) if p else None for o, r, p in
                                zip(out["official_games"], out["sofa_record_games"], out["sofa_pbp"])]
    out["sofa_complete"] = [None if k is None else k in COMPLETE for k in out["sofa_completeness"]]
    # TennisLive
    if len(tl_matches):
        out["tl_page_status"] = out["tl_id"].map(tl_matches["page_status"])
        out["tl_pbp_available"] = out["tl_id"].map(tl_matches["pbp_available"])
        out["tl_stats_available"] = out["tl_id"].map(tl_matches["stats_available"])
        out["tl_games_without_points"] = pd.to_numeric(out["tl_id"].map(tl_matches["games_without_points"]), errors="coerce")
        shapes = out["tl_id"].map(tl_games) if len(tl_games) else pd.Series([None] * len(out), index=out.index)
        out["tl_record_games"] = [s_["record_games"] if isinstance(s_, dict) else None for s_ in shapes]
        out["tl_last_after"] = [s_["last_after"] if isinstance(s_, dict) else None for s_ in shapes]
    else:
        out["tl_page_status"] = out["tl_pbp_available"] = out["tl_stats_available"] = out["tl_record_games"] = None
        out["tl_games_without_points"] = out["tl_last_after"] = None
    out["tl_linked"] = out["tl_status"].isin(["linked", "ambiguous"]) if "tl_status" in out else False
    out["tl_fetched"] = out["tl_linked"] & out["tl_page_status"].eq("200")
    out["tl_pbp"] = out["tl_linked"] & out["tl_pbp_available"].eq("TRUE")
    out["tl_stats"] = out["tl_linked"] & out["tl_stats_available"].eq("TRUE")
    # games complete: every set has as many games as the official score; complete: that, and no game lacks points
    out["tl_games_completeness"] = [completeness(o, r) if p else None for o, r, p in
                                    zip(out["official_games"], out["tl_record_games"], out["tl_pbp"])]
    out["tl_games_complete"] = [None if k is None else k in COMPLETE for k in out["tl_games_completeness"]]
    out["tl_short_kind"] = [short_kind(o, r, a) if k == "short" else None for o, r, a, k in
                            zip(out["official_games"], out["tl_record_games"], out["tl_last_after"], out["tl_games_completeness"])]
    out["tl_complete"] = [None if gc is None else bool(gc and (missing == 0)) for gc, missing in
                          zip(out["tl_games_complete"], out["tl_games_without_points"].fillna(0))]
    out["any_pbp"] = out["sofa_pbp"] | out["tl_pbp"]
    out["any_complete"] = out["sofa_complete"].eq(True) | out["tl_complete"].eq(True)
    out["tl_fills_sofa_hole"] = out["tl_pbp"] & ~out["sofa_pbp"]

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["ref_id", "code", "player", "level", "year", "period", "event_name", "event_type", "event_date", "round",
            "opp_first", "opp_last", "score", "walkover", "needs_points", "official_games",
            "sofa_status", "sofa_id", "sofa_tournament", "sofa_round", "sofa_opponent", "sofa_name_score", "sofa_state",
            "sofa_first_to_serve", "sofa_pbp_status", "sofa_pbp", "sofa_record_games", "sofa_completeness", "sofa_complete",
            "sofa_stats", "tl_status", "tl_id", "tl_tournament", "tl_round", "tl_opponent", "tl_name_score", "tl_state",
            "tl_page_status", "tl_pbp", "tl_record_games", "tl_games_without_points", "tl_games_completeness",
            "tl_short_kind", "tl_games_complete", "tl_complete", "tl_stats", "any_pbp", "any_complete", "tl_fills_sofa_hole"]
    cols = [c for c in cols if c in out.columns]
    table = out[cols].copy()
    table["event_date"] = table["event_date"].dt.strftime("%Y-%m-%d")
    for c in ("official_games", "sofa_record_games", "tl_record_games"):
        if c in table:
            table[c] = table[c].map(lambda v: " ".join(str(x) for x in v) if isinstance(v, list) else "")
    table.to_csv(OUT / "verification_matches.csv", index=False)

    need = out[out["needs_points"]]
    played = out[~out["walkover"]]
    summary = {
        "generated_at": pd.Timestamp.now("UTC").isoformat(timespec="seconds"),
        "inputs": {"reference_matches": int(len(out)), "sofascore_singles_candidates": int(len(sofa_cand)),
                   "sofascore_events_with_record": int(sofa_cand.drop_duplicates("sofa_id")["pbp_status"].eq("200").sum()) if len(sofa_cand) else 0,
                   "tennislive_index_candidates": int(len(tl_cand)),
                   "tennislive_pages_fetched": int((tl_matches["page_status"] == "200").sum()) if len(tl_matches) else 0},
        "study_claims": STUDY_TOTALS,
        "totals": {
            "official_matches": int(len(out)), "walkovers": int(out["walkover"].sum()), "need_points": int(len(need)),
            "sofascore": {"linked": int(out["sofa_linked"].sum()), "linked_played": int(played["sofa_linked"].sum()),
                          "with_record": int(out["sofa_pbp"].sum()), "with_record_need_points": int(need["sofa_pbp"].sum()),
                          "share_of_need_points": round(float(need["sofa_pbp"].mean()), 3) if len(need) else None,
                          "record_complete": int(out["sofa_complete"].eq(True).sum()),
                          "record_incomplete": int(out["sofa_complete"].eq(False).sum()),
                          "completeness": out["sofa_completeness"].value_counts().to_dict(),
                          "with_box_score": int(out["sofa_stats"].sum()),
                          "linked_with_marker": int((out["sofa_linked"] & out["sofa_first_to_serve"].isin(["1", "2"])).sum()) if "sofa_first_to_serve" in out else None,
                          "by_status": out["sofa_status"].value_counts().to_dict()},
            "tennislive": {"linked": int(out["tl_linked"].sum()), "pages_fetched": int(out["tl_fetched"].sum()),
                           "with_record": int(out["tl_pbp"].sum()), "with_record_need_points": int(need["tl_pbp"].sum()),
                           "share_of_need_points": round(float(need["tl_pbp"].mean()), 3) if len(need) else None,
                           "record_games_complete": int(out["tl_games_complete"].eq(True).sum()),
                           "record_games_incomplete": int(out["tl_games_complete"].eq(False).sum()),
                           "completeness": out["tl_games_completeness"].value_counts().to_dict(),
                           "short_records_by_kind": out["tl_short_kind"].value_counts().to_dict(),
                           "short_by_missing_games": {str(k): int(v) for k, v in
                                                      pd.Series([sum(o) - sum(r) for o, r, k in zip(out["official_games"], out["tl_record_games"], out["tl_games_completeness"]) if k == "short"]).value_counts().sort_index().items()},
                           "record_complete_every_game_with_points": int(out["tl_complete"].eq(True).sum()),
                           "records_with_games_lacking_points": int((out["tl_pbp"] & out["tl_games_without_points"].gt(0)).sum()),
                           "games_lacking_points_total": int(out.loc[out["tl_pbp"], "tl_games_without_points"].fillna(0).sum()),
                           "with_statistics": int(out["tl_stats"].sum()),
                           "fills_sofascore_hole": int(out["tl_fills_sofa_hole"].sum()),
                           "fills_sofascore_hole_need_points": int(need["tl_fills_sofa_hole"].sum()),
                           "by_status": out["tl_status"].value_counts().to_dict() if "tl_status" in out else {}},
            "union": {"with_record": int(out["any_pbp"].sum()), "with_record_need_points": int(need["any_pbp"].sum()),
                      "share_of_need_points": round(float(need["any_pbp"].mean()), 3) if len(need) else None,
                      "complete_from_either": int(out["any_complete"].sum())},
        },
        "sofascore_by_level_period": share_table(out, "sofa_pbp", ["level", "period"]),
        "sofascore_by_level_period_study_claim": STUDY_SOFASCORE,
        "tennislive_by_level_period": share_table(out, "tl_pbp", ["level", "period"]),
        "tennislive_fills_by_level_period": share_table(out, "tl_fills_sofa_hole", ["level", "period"]),
        "union_by_level_period": share_table(out, "any_pbp", ["level", "period"]),
        "union_by_player": share_table(out, "any_pbp", ["code", "player"]),
        "sofascore_by_player": share_table(out, "sofa_pbp", ["code", "player"]),
        "tennislive_by_player": share_table(out, "tl_pbp", ["code", "player"]),
    }
    for key in ("sofascore_by_level_period", "tennislive_by_level_period", "tennislive_fills_by_level_period",
                "union_by_level_period"):
        summary[key] = sorted(summary[key], key=lambda r: (LEVELS.index(r["level"]) if r["level"] in LEVELS else 99, r["period"]))
    # completeness detail: where a record's games disagree with the official score
    incomplete = out[out["sofa_complete"].eq(False) | out["tl_games_complete"].eq(False)]
    summary["incomplete_records"] = [
        {"ref_id": r["ref_id"], "score": r["score"], "official_games": r["official_games"],
         "sofa": r["sofa_record_games"] if r["sofa_complete"] is False else None,
         "tennislive": r["tl_record_games"] if r["tl_games_complete"] is False else None}
        for _, r in incomplete.head(200).iterrows()]
    summary["incomplete_records_total"] = int(len(incomplete))
    # SofaScore records of these players that the official list does not carry
    if len(sofa_cand):
        linked_ids = set(out["sofa_id"].dropna())
        extra = sofa_cand[~sofa_cand["sofa_id"].isin(linked_ids) & sofa_cand["pbp_status"].eq("200")].drop_duplicates("sofa_id")
        extra_years = pd.to_datetime(extra["ts"], unit="s").dt.year
        summary["sofascore_records_not_on_official_list"] = {
            "events": int(len(extra)),
            "by_category": extra["category"].value_counts().to_dict(),
            "by_year": {str(k): int(v) for k, v in extra_years.value_counts().sort_index().items()},
            "qualifying": int(extra["round_code"].str.startswith("Q").sum()),
        }
    (OUT / "verification_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    t = summary["totals"]
    print(json.dumps({"need_points": t["need_points"], "sofascore": t["sofascore"], "tennislive": t["tennislive"],
                      "union": t["union"]}, indent=1, default=str))
    grid = pd.DataFrame(summary["sofascore_by_level_period"])
    if len(grid):
        print(grid.to_string(index=False))
    return summary


if __name__ == "__main__":
    main()
