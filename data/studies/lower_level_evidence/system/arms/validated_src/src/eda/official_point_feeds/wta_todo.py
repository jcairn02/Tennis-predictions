"""The WTA collection's to-do list: every endpoint of every played match, by batch of the collection plan, with what
is fetched, empty, absent, failed or still to fetch.

Inputs: the plan (BATCHES and NOT_SERVED in src/ingest/point_sources/wta.py), the calendars, match lists and receipts
under data/raw/point_sources/wta/. No request is made, and it can run while a batch is fetching. The matches of an
edition whose match list is not held yet are estimated: the mean of the held lists of its tier and year (of its tier
in any year when fewer than two are held), scaled by the share of that tier and year's held lists with a played match
(half of 2020's lists hold none: events cancelled for COVID).

A document is:
    fetched   saved, with data (a log with a point, a box score with a row; a one-point win-probability stub counts)
    empty     saved, but without a point or a row (an empty log, as for the Slams)
    absent    HTTP 404: final, not asked again
    error     failed; the next run asks again
    pending   never asked, or its file is missing
Documents of 4,000 bytes or more are taken as holding data (an empty event log, with its players and tournament,
reaches 2,126 bytes); smaller ones are opened and checked. Box scores need no opening: an empty one is "[]" and the
smallest with a row is 534 bytes (30 Sep 2026, 30,349 of them), so 100 bytes separates them.

Outputs:
    data/studies/official_point_feeds/wta_todo.csv          one row per batch and per population the API does not
                                                            serve: scope, status, progress, what remains, the command
    data/studies/official_point_feeds/wta_todo_detail.csv   per batch, year, endpoint and draw
    data/dump/points/wta/todo.parquet                       every (match, endpoint) of the batches with its status
                                                            (gitignored; rebuilt by this script)
Usage:
    ./python.sh src/eda/official_point_feeds/wta_todo.py
"""
from __future__ import annotations

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
SECONDS_PER_REQUEST = 2.56  # measured over the 942 requests of the 24 Sep 2026 sample (2 s + jitter + the answer)
SMALL_BYTES = 4000
SURE_BYTES = {"stats": 100}  # per endpoint, the size from which a document surely holds data (module docstring)
BUDGET_MARGIN = 1.15
STATES = ["fetched", "empty", "absent", "error", "pending"]
DRAWS = ["main_singles", "qual_singles", "main_doubles", "qual_doubles"]


# --------------------------------------------------------------------------------------
# pure functions (tested offline)
# --------------------------------------------------------------------------------------
def has_data(endpoint: str, payload) -> bool:
    if endpoint in ("events", "point-by-point"):
        return W.has_points(payload)
    if endpoint == "advanced-stats":
        return isinstance(payload, dict) and bool(payload.get("teamA") or payload.get("teamB"))
    return isinstance(payload, list) and bool(payload)  # stats, win-probability-momentum


def item_state(receipt: dict | None, path: Path, endpoint: str) -> str:
    """fetched, empty, absent, error or pending (module docstring)."""
    if not receipt:
        return "pending"
    if receipt.get("error"):
        return "error"
    if receipt.get("status") == 404:
        return "absent"
    if receipt.get("status") != 200 or not path.exists():
        return "pending"
    if (receipt.get("bytes") or 0) >= SURE_BYTES.get(endpoint, SMALL_BYTES):
        return "fetched"
    return "fetched" if has_data(endpoint, P.read_json(path)) else "empty"


def in_scope(batch: dict, edition: dict) -> bool:
    return (edition["year"] in W.parse_years(batch["years"])
            and (not batch["tiers"] or edition["tier"] in batch["tiers"])
            and (not batch["from_date"] or (edition["start_date"] or "") >= batch["from_date"]))


def wanted_draw(batch: dict, draw: str) -> bool:
    return not batch["draws"] or draw in batch["draws"]


def played_by_draw(matches: list[dict]) -> Counter:
    return Counter(W.draw_of(m) for m in matches if W.is_played(m))


def size_estimator(held: dict[tuple, Counter], editions: list[dict]):
    """A function edition -> expected played matches by draw, for editions whose match list is not held."""
    by_tier_year, by_tier, lists, with_play = defaultdict(list), defaultdict(list), Counter(), Counter()
    tiers = {(e["tournament_id"], e["year"]): e["tier"] for e in editions}
    for key, counts in held.items():
        tier = tiers.get(key)
        lists[(tier, key[1])] += 1
        if sum(counts.values()):
            with_play[(tier, key[1])] += 1
            by_tier_year[(tier, key[1])].append(counts)
            by_tier[tier].append(counts)

    def estimate(edition: dict) -> Counter:
        cell = (edition["tier"], edition["year"])
        pool = by_tier_year[cell] if len(by_tier_year[cell]) >= 2 else by_tier[edition["tier"]]
        if not pool:
            return Counter()
        share = with_play[cell] / lists[cell] if lists[cell] else 1.0
        return Counter({d: share * sum(c[d] for c in pool) / len(pool) for d in DRAWS})

    return estimate


# --------------------------------------------------------------------------------------
# the list
# --------------------------------------------------------------------------------------
def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    receipts = P.receipts_for(W.SOURCE)
    years = sorted(set(W.calendar_years()) | {y for b in W.BATCHES for y in W.parse_years(b["years"])})
    editions = W.load_editions(years)
    held = {}
    for e in editions:
        if W.listing_dest(e["tournament_id"], e["year"]).exists():
            held[(e["tournament_id"], e["year"])] = played_by_draw(W.load_listing(e["tournament_id"], e["year"]))
    estimate = size_estimator(held, editions)
    items, detail, plan = [], defaultdict(Counter), []
    for batch in W.BATCHES:
        counts = Counter()
        scope = [e for e in editions if in_scope(batch, e)]
        for e in scope:
            tid, year = e["tournament_id"], e["year"]
            unfinished = e.get("status") != "past"
            counts["editions"] += 1
            counts["editions_unfinished"] += unfinished
            if (tid, year) not in held:
                listing = receipts.get(f"tournaments/{tid}/{year}/matches") or {}
                if listing.get("status") == 404 and not listing.get("error"):
                    counts["editions_not_listed"] += 1  # the API has no match list for it (15 of 2019's 64): final
                    continue
                counts["editions_listing_pending"] += 1
                if not unfinished and (e["singles_draw_size"] or e["tier"] == "team"):
                    guess = estimate(e)
                    for draw in DRAWS:
                        if wanted_draw(batch, draw):
                            counts["matches_estimated"] += guess[draw]
                            for endpoint in batch["endpoints"]:
                                detail[(batch["id"], year, endpoint, draw)]["estimated"] += guess[draw]
                continue
            counts["editions_listed"] += 1
            for m in W.load_listing(tid, year):
                draw = W.draw_of(m)
                if not W.is_played(m) or not wanted_draw(batch, draw):
                    continue
                counts["matches_listed"] += 1
                for endpoint in batch["endpoints"]:
                    receipt = receipts.get(W.endpoint_name(tid, year, m["MatchID"], endpoint))
                    state = item_state(receipt, W.endpoint_dest(tid, year, m["MatchID"], endpoint), endpoint)
                    counts[state] += 1
                    detail[(batch["id"], year, endpoint, draw)][state] += 1
                    items.append({"batch": batch["id"], "year": year, "tournament_id": tid, "tier": e["tier"],
                                  "match_id": m["MatchID"], "draw": draw, "round": m.get("RoundID"),
                                  "endpoint": endpoint, "state": state,
                                  "bytes": (receipt or {}).get("bytes"), "retrieved_at": (receipt or {}).get("retrieved_at"),
                                  "error": (receipt or {}).get("error")})
        estimated_documents = counts["matches_estimated"] * len(batch["endpoints"])
        remaining = counts["pending"] + counts["error"] + counts["editions_listing_pending"] + estimated_documents
        documents = sum(counts[s] for s in STATES)
        plan.append({
            "batch": batch["id"], "status": batch["status"], "approved_on": batch["approved_on"],
            "endpoints": ";".join(batch["endpoints"]), "years": batch["years"],
            "tiers": ";".join(batch["tiers"]) if batch["tiers"] else "all", "draws": ";".join(batch["draws"] or []) or "all",
            "from_date": batch["from_date"], "note": batch["note"],
            "editions": counts["editions"], "editions_listed": counts["editions_listed"],
            "editions_not_listed": counts["editions_not_listed"],
            "editions_unfinished": counts["editions_unfinished"], "matches_listed": counts["matches_listed"],
            "matches_estimated_unlisted": round(counts["matches_estimated"]),
            "documents_listed": documents, **{s: counts[s] for s in STATES},
            "share_done": round((documents - counts["pending"] - counts["error"]) / documents, 3) if documents else None,
            "remaining_requests": round(remaining), "remaining_hours": round(remaining * SECONDS_PER_REQUEST / 3600, 1),
            "command": (f"./python.sh -m src.ingest.point_sources.wta --batch {batch['id']} "
                        f"--max-requests {max(100, round(remaining * BUDGET_MARGIN, -2)):.0f}"
                        + ("" if batch["status"] == "approved" else "  # after approval")),
        })
    for ns in W.NOT_SERVED:
        plan.append({"batch": "-", "status": "not_served", "endpoints": ";".join(ns["endpoints"]), "years": ns["years"],
                     "tiers": "", "draws": "", "note": f"{ns['what']}: {ns['why']}"})
    detail_rows = [{"batch": b, "year": y, "endpoint": ep, "draw": d, **{s: c[s] for s in STATES},
                    "estimated_unlisted": round(c["estimated"], 1)}
                   for (b, y, ep, d), c in sorted(detail.items())]
    plan = pd.DataFrame(plan)
    counts = ["editions", "editions_listed", "editions_not_listed", "editions_unfinished", "matches_listed",
              "matches_estimated_unlisted",
              "documents_listed", *STATES, "remaining_requests"]
    plan[counts] = plan[counts].astype("Int64")  # whole numbers, blank on the not-served rows
    return plan, pd.DataFrame(detail_rows), pd.DataFrame(items)


def run() -> dict:
    plan, detail, items = build()
    OUT.mkdir(parents=True, exist_ok=True)
    plan.to_csv(OUT / "wta_todo.csv", index=False)
    detail.to_csv(OUT / "wta_todo_detail.csv", index=False)
    dest = P.dump_path(W.SOURCE, "todo.parquet")
    dest.parent.mkdir(parents=True, exist_ok=True)
    items.astype({c: "string" for c in items.columns}).to_parquet(dest, index=False)
    return {"batches": plan, "items": len(items), "items_file": P.rel(dest)}


def main() -> int:
    P.configure_stdout()
    out = run()
    shown = out["batches"][["batch", "status", "endpoints", "years", "editions_listed", "editions", "matches_listed",
                            "fetched", "empty", "absent", "error", "pending", "remaining_requests", "remaining_hours"]]
    print(shown.to_string(index=False))
    print(f"{out['items']:,} items in {out['items_file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
