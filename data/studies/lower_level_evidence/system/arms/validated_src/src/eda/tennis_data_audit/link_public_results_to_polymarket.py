"""Conservative candidate links; does not certify settlement or impose fuzzy joins.

Uses normalized full names and date distance at most one calendar day. Public results
are Open Tennis Data's pinned preview, not an independent market census. Run with
explicit research interpreter C:/Users/zerom/miniforge3/envs/ufc-ag/python.exe.
"""
import collections
import datetime as dt
import gzip
import json
from pathlib import Path
import re
import unicodedata
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/studies/tennis_data_audit/public"


def norm(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", name).split())


def main():
    results = pd.read_parquet(OUT / "raw/open_tennis_completed.parquet")
    by_pair = collections.defaultdict(list)
    for row in results.to_dict("records"):
        if len(row["player1_name"]) != 1 or len(row["player2_name"]) != 1:
            continue
        a,b = str(row["player1_name"][0]), str(row["player2_name"][0])
        key = tuple(sorted((norm(a),norm(b))))
        by_pair[key].append({"result_match_id":row["match_id"],"result_date":str(row["date"]),
                             "player1":a,"player2":b,"winner_id":list(row["winner_id"]),
                             "tournament":row["tournament_name"],"tour":row["tour"],"round":row["round"],
                             "score":row["score"],"status":row["status"],"source":list(row["source"])})
    events = [json.loads(line) for line in (ROOT / "data/studies/tennis_data_audit/polymarket/events.jsonl").read_text(encoding="utf-8").splitlines()]
    counters = collections.Counter()
    links = []
    misses = []
    for event in events:
        if not event["in_sport_window"]:
            continue
        counters["all_tagged_events_in_sport_window"] += 1
        if event["date_basis"] != "startTime":
            counters["excluded_non_startTime_date_basis"] += 1
            continue
        parts = re.split(r"\s+vs\.?\s+",event["title"])
        if len(parts) != 2:
            counters["excluded_title_not_two_part_vs"] += 1
            continue
        a,b = parts[0].rsplit(":",1)[-1].strip(), parts[1].strip()
        if any(symbol in a+b for symbol in ("/"," & ","?")):
            counters["excluded_doubles_or_question_title"] += 1
            continue
        counters["parsed_full_name_pair_candidates"] += 1
        key = tuple(sorted((norm(a),norm(b))))
        edate = dt.datetime.fromisoformat(event["sport_date"]).date()
        found = [r for r in by_pair.get(key, []) if abs((edate - dt.date.fromisoformat(r["result_date"])).days) <= 1]
        if len(found) == 1:
            r = found[0]
            gap = (edate-dt.date.fromisoformat(r["result_date"])).days
            links.append({"event_id":event["id"],"event_title":event["title"],"event_url":event["url"],
                          "market_sport_date":event["sport_date"],"calendar_day_difference":gap,
                          "volume":event["volume"],**r})
            counters["unique_full_name_date_candidates"] += 1
            counters["exact_calendar_date" if gap == 0 else "one_day_calendar_tolerance"] += 1
        elif len(found) > 1:
            counters["ambiguous_result_candidates"] += 1
            misses.append({"event_id":event["id"],"title":event["title"],"reason":"multiple candidates","count":len(found)})
        else:
            counters["no_exact_name_date_candidate"] += 1
            if key in by_pair:
                counters["same_pair_elsewhere_but_no_date_candidate"] += 1
            misses.append({"event_id":event["id"],"title":event["title"],"date":event["sport_date"],"reason":"no exact normalized full-name pair within one day"})
    linked = {r["event_id"]:r for r in links}
    for row in links:
        row["market_contracts"] = []
    with gzip.open(ROOT / "data/studies/tennis_data_audit/polymarket/markets.jsonl.gz","rt",encoding="utf-8") as handle:
        for line in handle:
            market = json.loads(line)
            if market["event_id"] in linked:
                linked[market["event_id"]]["market_contracts"].append({k:market.get(k) for k in ("id","question","sportsMarketType","outcomes","clobTokenIds","conditionId")})
    summary = {"method":"Exact normalized full player-name pair; event startTime UTC calendar date vs sporting result date, tolerance at most one day; unique results only. Candidates, not certified joins.",
               "warning":"Tag false positives, future dates, non-main-tour populations, dataset gaps, and aliases remain in unmatched denominator. This is not overall Polymarket coverage.",
               "results_release":"data-v3-20260905T083014Z", "counts":dict(counters),
               "candidate_tours":dict(collections.Counter(r["tour"] for r in links)),
               "candidate_status":dict(collections.Counter(r["status"] for r in links)),
               "candidate_market_contracts":sum(len(r["market_contracts"]) for r in links),
               "distinct_result_matches":len({r["result_match_id"] for r in links}),
               "result_rows_in_requested_window": int(((pd.to_datetime(results.date) >= "2025-09-10") & (pd.to_datetime(results.date) < "2026-09-11")).sum()),
               "candidate_date_range":[min((r["result_date"] for r in links),default=None),max((r["result_date"] for r in links),default=None)]}
    for name, data in (("polymarket_public_link_summary.json",summary),("polymarket_public_candidate_links.json",links),("polymarket_public_unmatched.json",misses)):
        (OUT / name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    main()
