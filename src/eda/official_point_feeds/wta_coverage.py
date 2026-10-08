"""Coverage of the WTA API by year, tier, draw and endpoint, from the seeded sample, and the size of bulk scopes.

Inputs: the calendar pages, the sampled editions' match lists and the per-match receipts written by
src/ingest/point_sources/wta.py --sample (receipts carry "sampled": true). A document counts as present when it
was answered with HTTP 200 and holds data: at least one point (point-by-point), one scoring record (events), one
row (stats), a team block (advanced-stats) or any content (win-probability-momentum).

Scope sizes: for every edition of 2020-2026 that is past and has a singles draw, the played matches by draw are
taken from its match list when it was fetched, else estimated as the mean of the sampled editions of the same
tier (and year when the year has two or more sampled editions of the tier). The request count of a scope is one
match list per edition plus one request per match and endpoint, keeping only the endpoints the sample found for
that year and draw: coverage follows the year, not the tier, so presence is pooled over the non-Slam tiers (each
tier cell holds one to four sampled matches), and the Slams are judged on their own. The run time assumes the
sample's measured seconds per request.

Outputs (data/studies/official_point_feeds/):
    wta_coverage.csv     one row per (year, tier, draw, endpoint) cell of the sample: asked, present, empty, absent
    wta_coverage.json    the same as nested tables, the sampled editions, and the scope options with their sizes
Usage:
    ./python.sh src/eda/official_point_feeds/wta_coverage.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import wta as W  # noqa: E402

OUT = PROJECT_ROOT / "data" / "studies" / "official_point_feeds"
YEARS = list(range(2020, 2027))
# point-by-point begins between Indian Wells 2022 (from 9 March: absent at both sampled matches of its 2022 edition)
# and Charleston 2022 (from 4 April: present); editions starting before this date are not asked for it
POINT_BY_POINT_FROM = "2022-03-14"
TIERS = ["1000", "500", "250", "125", "finals", "slam", "team"]
DRAWS = ["main_singles", "qual_singles", "main_doubles", "qual_doubles"]
# the owner's four endpoints plus the umpire's event log, found during the probes
SCOPES = {
    "A": {"label": "the umpire's event log, main singles", "draws": ["main_singles"], "endpoints": ["events"]},
    "B": {"label": "the umpire's event log, every draw (main and qualifying, singles and doubles)",
          "draws": DRAWS, "endpoints": ["events"]},
    "C": {"label": "scope B plus point-by-point where it exists (from April 2022), as a second record",
          "draws": DRAWS, "endpoints": ["events", "point-by-point"]},
    "D": {"label": "the four endpoints named in the request (no event log), every draw",
          "draws": DRAWS, "endpoints": ["point-by-point", "win-probability-momentum", "advanced-stats", "stats"]},
    "E": {"label": "every endpoint where it exists, every draw", "draws": DRAWS, "endpoints": list(W.ENDPOINTS)},
}
EXTENSION_YEAR = 2019  # the event log answered for both 2019 finals asked (1045, 1052); 2018's (804) was empty


def document_state(receipt: dict | None, path: Path, endpoint: str) -> str:
    """"present", "empty" (200 without data), "absent" (404), "error" or "not asked"."""
    if not receipt:
        return "not asked"
    if receipt.get("error"):
        return "error"
    if receipt.get("status") == 404:
        return "absent"
    if receipt.get("status") != 200 or not path.exists():
        return "error"
    payload = P.read_json(path)
    if endpoint in ("point-by-point", "events"):
        return "present" if W.has_points(payload) else "empty"
    if endpoint == "stats":
        return "present" if isinstance(payload, list) and payload else "empty"
    if endpoint == "advanced-stats":
        return "present" if isinstance(payload, dict) and (payload.get("teamA") or payload.get("teamB")) else "empty"
    return "present" if payload else "empty"


def sample_rows(receipts, starts: dict) -> list[dict]:
    """One row per sampled document (receipts marked "sampled"; the step-1 probes are not)."""
    rows = []
    for name, r in receipts.all().items():
        if not name.startswith("matches/") or not r.get("sampled"):
            continue
        tid, year, mid, endpoint = r["tournament_id"], int(r["year"]), r["match_id"], r["endpoint"]
        state = document_state(r, W.endpoint_dest(tid, year, mid, endpoint), endpoint)
        rows.append({"year": year, "tier": r.get("tier"), "draw": r.get("draw"), "endpoint": endpoint,
                     "tournament_id": tid, "start_date": starts.get((tid, year)), "match_id": mid,
                     "round": r.get("round"), "state": state})
    return rows


def coverage_table(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    counts = (frame.groupby(["year", "tier", "draw", "endpoint", "state"]).size().unstack("state", fill_value=0)
              .reindex(columns=["present", "empty", "absent", "error"], fill_value=0))
    counts["asked"] = counts.sum(axis=1)
    counts["editions"] = frame.groupby(["year", "tier", "draw", "endpoint"])["tournament_id"].nunique()
    counts["share_present"] = (counts["present"] / counts["asked"]).round(3)
    return counts.reset_index()


def played_by_draw(matches: list[dict]) -> Counter:
    return Counter(W.draw_of(m) for m in matches if W.is_played(m))


def edition_sizes(editions: list[dict], sampled_keys: set) -> pd.DataFrame:
    """Played matches by draw for every past edition with a singles draw (or a team event): counted from its match
    list when held, else the mean of the sampled editions of its tier (and year, when two or more were sampled)."""
    held = {}
    for e in editions:
        path = W.listing_dest(e["tournament_id"], e["year"])
        if path.exists():
            held[(e["tournament_id"], e["year"])] = played_by_draw(W.load_listing(e["tournament_id"], e["year"]))
    by_tier_year, by_tier = defaultdict(list), defaultdict(list)
    tried = defaultdict(lambda: [0, 0])  # (tier, year) -> [match lists held, of which with a played match]
    for e in editions:
        counts = held.get((e["tournament_id"], e["year"]))
        if counts is None:
            continue
        tried[(e["tier"], e["year"])][0] += 1
        tried[(e["tier"], e["year"])][1] += bool(sum(counts.values()))
        if sum(counts.values()) and (e["tournament_id"], e["year"]) in sampled_keys:
            by_tier_year[(e["tier"], e["year"])].append(counts)
            by_tier[e["tier"]].append(counts)
    rows = []
    for e in editions:
        if e["year"] not in YEARS or e.get("status") != "past" or not (e["singles_draw_size"] or e["tier"] == "team"):
            continue
        counts = held.get((e["tournament_id"], e["year"]))
        source = "listing"
        if counts is None:
            pool = by_tier_year.get((e["tier"], e["year"]), [])
            pool, source = (pool, "tier-year mean") if len(pool) >= 2 else (by_tier.get(e["tier"], []), "tier mean")
            # scaled by the share of this year's and tier's fetched match lists that held a played match: the
            # calendar keeps some cancelled editions with their draw sizes (8 of the 16 tried for 2020)
            held_n, played_n = tried.get((e["tier"], e["year"]), (0, 0))
            played_share = played_n / held_n if held_n else 1.0
            counts = Counter({d: played_share * sum(c[d] for c in pool) / len(pool) for d in DRAWS}) if pool else Counter()
        rows.append({"year": e["year"], "tier": e["tier"], "tournament_id": e["tournament_id"], "title": e["title"],
                     "start_date": e["start_date"], "size_source": source, **{d: float(counts.get(d, 0)) for d in DRAWS}})
    return pd.DataFrame(rows)


def pooled_presence(rows: list[dict]) -> dict:
    """Share of sampled documents present by (year, "slam" or "other", draw, endpoint); point-by-point asked of
    editions that started before POINT_BY_POINT_FROM is left out, since no scope asks for it there."""
    frame = pd.DataFrame(rows)
    if frame.empty:
        return {}
    early = (frame["endpoint"] == "point-by-point") & (frame["start_date"].fillna("") < POINT_BY_POINT_FROM)
    frame = frame[~early].assign(group=frame["tier"].where(frame["tier"] == "slam", "other"),
                                 present=lambda f: f["state"] == "present")
    pooled = frame.groupby(["year", "group", "draw", "endpoint"])["present"].agg(["sum", "count"])
    return {(int(y), g, d, e): r["sum"] / r["count"] for (y, g, d, e), r in pooled.iterrows() if r["count"]}


def scope_sizes(sizes: pd.DataFrame, present: dict, seconds_per_request: float) -> dict:
    """Requests and hours for each scope, keeping only the endpoints the sample found for the year and draw."""
    out = {}
    for key, scope in SCOPES.items():
        requests, matches, docs, editions = 0.0, 0.0, 0.0, 0
        by_year = defaultdict(float)
        for r in sizes.itertuples():
            group = "slam" if r.tier == "slam" else "other"
            edition_requests, wanted_any = 1.0, False  # the match list
            for draw in scope["draws"]:
                n = getattr(r, draw)
                wanted = [e for e in scope["endpoints"] if present.get((int(r.year), group, draw, e), 0) > 0
                          and not (e == "point-by-point" and (r.start_date or "") < POINT_BY_POINT_FROM)]
                if n and wanted:
                    wanted_any = True
                    matches += n
                    edition_requests += n * len(wanted)
                    docs += sum(n * present[(int(r.year), group, draw, e)] for e in wanted)
            if wanted_any:
                editions += 1
                requests += edition_requests
                by_year[int(r.year)] += edition_requests
        out[key] = {**scope, "editions": editions, "matches": round(matches), "requests": round(requests),
                    "documents_expected": round(docs), "hours": round(requests * seconds_per_request / 3600, 1),
                    "requests_by_year": {y: round(v) for y, v in sorted(by_year.items())}}
    return out


def extension_2019(sizes: pd.DataFrame, seconds_per_request: float) -> dict:
    """2019, the event log only, every draw: its editions from the calendar, their sizes from 2021's sampled
    editions of the same tier (2020 was cut short by the pandemic). An estimate from two checked finals."""
    editions = [e for e in W.load_editions([EXTENSION_YEAR]) if e.get("status") == "past" and e["singles_draw_size"]]
    means = sizes[sizes["year"] == 2021].groupby("tier")[DRAWS].mean() if len(sizes) else pd.DataFrame()
    matches = sum(float(means.loc[e["tier"]].sum()) for e in editions if e["tier"] in means.index)
    requests = len(editions) + matches
    return {"year": EXTENSION_YEAR, "editions": len(editions), "matches": round(matches), "requests": round(requests),
            "hours": round(requests * seconds_per_request / 3600, 1),
            "basis": "event log present for both 2019 finals asked (1045/2019, 1052/2019); sizes from 2021's tiers"}


def run() -> dict:
    receipts = P.receipts_for(W.SOURCE)
    editions = W.load_editions(YEARS)
    rows = sample_rows(receipts, {(e["tournament_id"], e["year"]): e["start_date"] for e in editions})
    coverage = coverage_table(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(OUT / "wta_coverage.csv", index=False)
    sampled_keys = {(r["tournament_id"], r["year"]) for r in rows}
    sizes = edition_sizes(editions, sampled_keys)
    summary_path = OUT / "wta_sample_summary.json"
    run_summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    client = run_summary.get("client") or {}
    seconds = (run_summary.get("seconds") or 0) / client["requests"] if client.get("requests") else 2.6
    tables = {}
    for endpoint in W.ENDPOINTS:
        sub = coverage[coverage["endpoint"] == endpoint] if len(coverage) else coverage
        tables[endpoint] = {f"{r.year}|{r.tier}|{r.draw}": f"{r.present}/{r.asked}" for r in sub.itertuples()}
    out = {
        "sampled_matches": len({(r["tournament_id"], r["year"], r["match_id"]) for r in rows}),
        "sampled_editions": len(sampled_keys),
        "requests_sampled": len(rows),
        "seconds_per_request": round(seconds, 2),
        "present_over_asked": tables,
        "sizes": {"editions": len(sizes), "by_source": dict(Counter(sizes["size_source"])) if len(sizes) else {},
                  "played_matches_by_draw": {d: round(float(sizes[d].sum())) for d in DRAWS} if len(sizes) else {},
                  "by_year_tier": {f"{y}|{t}": {"editions": len(g), **{d: round(float(g[d].sum())) for d in DRAWS}}
                                   for (y, t), g in sizes.groupby(["year", "tier"])} if len(sizes) else {}},
        "point_by_point_from": POINT_BY_POINT_FROM,
        "scopes": scope_sizes(sizes, pooled_presence(rows), seconds) if len(coverage) else {},
        "extension_2019_events": extension_2019(sizes, seconds),
    }
    (OUT / "wta_coverage.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


def main() -> int:
    P.configure_stdout()
    out = run()
    print(json.dumps({k: out[k] for k in ("sampled_matches", "sampled_editions", "requests_sampled",
                                          "seconds_per_request", "scopes")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
