"""Point/shot sources study, step 2: check SofaScore's point-level marker against its point-by-point endpoint.

`link_sofascore.py` treats an event's `firstToServe` field as the sign that SofaScore holds its
point-by-point record. This step tests that on a stratified sample of linked official matches:
level x era x marker, two events per cell with the marker and one without, where available (seeded).
The eras follow the breaks seen in the marker itself (Challenger 2022-23 and ITF 2025-26 mostly lack it).

  --sample   writes pbp_check_sample.csv: the events to read. Each was then read on 23 September 2026 at
             https://api.sofascore.com/api/v1/event/<id>/point-by-point through the WebFetch tool and the
             answer transcribed into pbp_checks.csv (http status; each set's highest game number and the
             score after it). Where listing and record disagreed, /api/v1/event/<id> was read for the marker.
  --sample-itf-recent
             writes pbp_check_itf_recent_sample.csv: 20 random linked ITF main-draw matches of 2025-26, read
             the same way into pbp_checks_itf_recent.csv, because the marker failed there.
  --sample-tennislive
             writes tennislive_sample.csv: 20 matches in SofaScore's two holes whose TennisLive.net page was
             read into tennislive_checks.csv (page found; point-by-point shown).
  (default)  compares the checks with the marker and with the official score: a record is complete
             when every set has as many games as the official score says (tiebreaks count as one game).

Writes pbp_check_sample.csv or pbp_check_summary.json to data/studies/point_shot_sources/.
Run: ./python.sh src/eda/point_shot_sources/pbp_checks.py [--sample]
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "point_shot_sources"
SEED = 20260923
ERAS = [(2012, 2018, "2012-18"), (2019, 2021, "2019-21"), (2022, 2023, "2022-23"), (2024, 2024, "2024"),
        (2025, 2026, "2025-26")]
LEVELS = ["ITF main draw", "Challenger qualifying", "Challenger main draw", "Tour qualifying", "Tour main draw"]


def era(year: int) -> str:
    return next(label for lo, hi, label in ERAS if lo <= year <= hi)


def official_games(score: str) -> list[int]:
    """Games per set in an official score such as '6-3 6-7(4) 7-5'; a match tiebreak '[10-8]' or '1-0(8)' is one game."""
    sets = re.findall(r"(\d+)-(\d+)", re.sub(r"\(\d+\)", "", str(score or "")))
    return [int(a) + int(b) for a, b in sets]


def sample():
    links = pd.read_csv(OUT / "sofascore_links.csv", dtype=str, keep_default_na=False)
    links = links[(links["sofa_status"] == "linked") & ~links["score"].str.contains("RET|W/O|DEF|ABD", case=False)]
    links["era"] = links["year"].astype(int).map(era)
    links["marker"] = links["pbp_marker"].map({"True": "marker", "False": "no marker"})
    picks = []
    for (lv, er, mk), g in links[links["level"].isin(LEVELS)].groupby(["level", "era", "marker"]):
        picks.append(g.sample(min(2 if mk == "marker" else 1, len(g)), random_state=SEED))
    out = pd.concat(picks)[["ref_id", "player", "event_name", "event_date", "round", "opp_last", "score", "level",
                            "era", "marker", "sofa_id", "first_to_serve", "final_result_only"]]
    out.to_csv(OUT / "pbp_check_sample.csv", index=False)
    print(len(out), "events to read")
    print(out.groupby(["level", "era", "marker"]).size().unstack(fill_value=0))


def sample_itf_recent(n: int = 20):
    """ITF main draws of 2025-26, where the marker and the record disagreed: a plain random sample of linked
    matches, marker ignored, to measure how many have a point record."""
    links = pd.read_csv(OUT / "sofascore_links.csv", dtype=str, keep_default_na=False)
    pool = links[(links["sofa_status"] == "linked") & (links["level"] == "ITF main draw") &
                 (links["year"].astype(int) >= 2025) & (links["score"] != "") &
                 ~links["score"].str.contains("RET|W/O|DEF|ABD", case=False)]
    out = pool.sample(min(n, len(pool)), random_state=SEED)[
        ["ref_id", "player", "event_name", "event_date", "round", "opp_last", "score", "level", "sofa_id",
         "first_to_serve", "pbp_marker"]]
    out.to_csv(OUT / "pbp_check_itf_recent_sample.csv", index=False)
    print(len(pool), "linked ITF main-draw matches of 2025-26;", len(out), "drawn")


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def sample_tennislive():
    """TennisLive.net for SofaScore's two holes (Challenger 2022-23, ITF 2025): 8 Challenger main-draw,
    4 Challenger qualifying and 8 ITF main-draw matches, drawn from tournaments held once per city and year so
    the match page's address can be built: /atp/match/<winner>-VS-<loser>/<tournament>-<year>/. Each page was
    then read on 23 September 2026 through WebFetch and the answer transcribed into tennislive_checks.csv."""
    r = pd.read_csv(ROOT / "data/studies/career_coverage/reference_record.csv", dtype=str, keep_default_na=False)
    r = r[(r["is_bye"] != "True") & (r["walkover"] != "True") & (r["score"] != "") &
          ~r["score"].str.contains("RET|W/O|DEF", case=False)]
    r["y"] = r["event_date"].str[:4].astype(int)
    repeated_itf = r"Antalya|Monastir|Sharm|Heraklion|Santa Margherita|Kursumlijska|Cancun|Hurghada|Tabarka|Sintra|Porto|Lima"
    picks = []
    for lv, (a, b), n in (("Challenger main draw", (2022, 2023), 8), ("Challenger qualifying", (2022, 2023), 4),
                          ("ITF main draw", (2025, 2025), 8)):
        pool = r[(r["level"] == lv) & r["y"].between(a, b)]
        drop = repeated_itf if lv.startswith("ITF") else r"\d|\(|/"   # numbered or bracketed Challenger names
        pool = pool[~pool["event_name"].str.contains(drop, regex=True)]
        picks.append(pool.sample(min(n, len(pool)), random_state=SEED))
    rows = []
    for _, m in pd.concat(picks).iterrows():
        me, opp = slug(m["player"]), slug(f"{m['opp_first']} {m['opp_last']}")
        pair = f"{me}-VS-{opp}" if m["wl"] == "W" else f"{opp}-VS-{me}"
        event = f"{slug(m['event_name'])}-{m['y']}" if m["level"].startswith("ITF") else \
            f"{slug(m['event_name'])}-challenger-{m['y']}"
        rows.append({"ref_id": m["ref_id"], "player": m["player"], "event": m["event_name"], "date": m["event_date"],
                     "round": m["round"], "wl": m["wl"], "opp": f"{m['opp_first']} {m['opp_last']}",
                     "score": m["score"], "level": m["level"],
                     "url": f"https://www.tennislive.net/atp/match/{pair}/{event}/"})
    pd.DataFrame(rows).to_csv(OUT / "tennislive_sample.csv", index=False)
    print(len(rows), "TennisLive pages to read")


def evaluate_tennislive() -> dict:
    path = OUT / "tennislive_checks.csv"
    if not path.exists():
        return {}
    c = pd.read_csv(path, dtype=str, keep_default_na=False)
    found = c[c["page"] == "found"]
    out = {}
    for lv, g in c.groupby("level"):
        f = g[g["page"] == "found"]
        k = int((f["point_by_point"] == "yes").sum())
        lo, hi = wilson(k, len(f))
        out[lv] = {"sampled": int(len(g)), "pages_found": int(len(f)), "with_point_by_point": k,
                   "wilson_95": [round(lo, 3), round(hi, 3)]}
    k = int((found["point_by_point"] == "yes").sum())
    lo, hi = wilson(k, len(found))
    out["all"] = {"sampled": int(len(c)), "pages_found": int(len(found)), "with_point_by_point": k,
                  "wilson_95": [round(lo, 3), round(hi, 3)]}
    return out


def evaluate_itf_recent() -> dict:
    path = OUT / "pbp_checks_itf_recent.csv"
    if not path.exists():
        return {}
    c = pd.read_csv(path, dtype=str, keep_default_na=False)
    c = c[c["http"].isin(["200", "404"])]
    has = c["http"] == "200"
    rec = c["games_per_set"].map(lambda s: [int(x) for x in re.findall(r"\d+", s)] if s else [])
    complete = has & (rec == c["score"].map(official_games))
    k, n = int(has.sum()), len(c)
    lo, hi = wilson(k, n)
    return {"read": n, "records": k, "records_complete": int(complete.sum()),
            "share_with_record": round(k / n, 3) if n else None, "wilson_95": [round(lo, 3), round(hi, 3)],
            "by_year": {y: {"read": int(len(g)), "records": int((g["http"] == "200").sum())}
                        for y, g in c.groupby(c["event_date"].str[:4])},
            "listed_marker_vs_record": pd.crosstab(c["pbp_marker"], has).to_dict()}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    p = k / n
    centre, half = p + z * z / (2 * n), z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((centre - half) / (1 + z * z / n), (centre + half) / (1 + z * z / n))


def evaluate():
    """pbp_checks.csv columns added to the sample: http (200, 404, or 'event not found' when the listed id itself
    does not exist), games_per_set and set_final_scores of the record (set order; each set's highest game number
    and the score after it), event_marker (firstToServe as read from /api/v1/event/<id>, filled where the listing
    and the record disagreed) and note."""
    checks = pd.read_csv(OUT / "pbp_checks.csv", dtype=str, keep_default_na=False)
    excluded = checks[~checks["http"].isin(["200", "404"])]
    checks = checks[checks["http"].isin(["200", "404"])].copy()
    checks["has_record"] = checks["http"] == "200"
    checks["official_games"] = checks["score"].map(official_games)
    checks["record_games"] = checks["games_per_set"].map(
        lambda s: [int(x) for x in re.findall(r"\d+", s)] if s else [])
    checks["complete"] = checks["has_record"] & (checks["record_games"] == checks["official_games"])
    checks["listed_marker"] = checks["marker"] == "marker"
    # the marker as the event's own record gives it, where that was read; otherwise as listed
    checks["true_marker"] = checks.apply(lambda r: r["event_marker"] in ("1", "2") if r["event_marker"]
                                         else r["listed_marker"], axis=1)
    checks["listed_agrees"] = checks["listed_marker"] == checks["has_record"]
    checks["true_agrees"] = checks["true_marker"] == checks["has_record"]
    itf_recent = (checks["level"] == "ITF main draw") & (checks["era"] == "2025-26")

    def cross(df, col):
        t = pd.crosstab(df[col], df["has_record"])
        return {("marker" if m else "no marker"): {("record" if k else "no record"): int(v) for k, v in row.items()}
                for m, row in t.iterrows()}

    summary = {
        "events_read": int(len(checks) + len(excluded)),
        "excluded": excluded[["sofa_id", "http", "note"]].to_dict(orient="records"),
        "records_found": int(checks["has_record"].sum()),
        "records_complete": int(checks["complete"].sum()),
        "listed_marker_vs_record": cross(checks, "listed_marker"),
        "listed_marker_agrees": int(checks["listed_agrees"].sum()),
        "listing_copy_errors": int((checks["listed_marker"] != checks["true_marker"]).sum()),
        "true_marker_vs_record_outside_itf_2025_26": cross(checks[~itf_recent], "true_marker"),
        "true_marker_vs_record_itf_2025_26": cross(checks[itf_recent], "true_marker"),
        "by_level_era": checks.groupby(["level", "era", "marker"]).agg(
            read=("sofa_id", "size"), records=("has_record", "sum"), complete=("complete", "sum"),
            listed_agrees=("listed_agrees", "sum"), true_agrees=("true_agrees", "sum")).reset_index()
            .to_dict(orient="records"),
        "incomplete_records": checks[checks["has_record"] & ~checks["complete"]][
            ["sofa_id", "player", "event_name", "event_date", "round", "score", "games_per_set"]]
            .to_dict(orient="records"),
        "itf_2025_26_direct_sample": evaluate_itf_recent(),
        "tennislive_sample": evaluate_tennislive(),
    }
    (OUT / "pbp_check_summary.json").write_text(json.dumps(summary, indent=1, default=int), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "by_level_era"}, indent=1, default=int))


if __name__ == "__main__":
    if "--sample" in sys.argv:
        sample()
    elif "--sample-itf-recent" in sys.argv:
        sample_itf_recent()
    elif "--sample-tennislive" in sys.argv:
        sample_tennislive()
    else:
        evaluate()
