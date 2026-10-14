"""Box scores first: the gaps a prediction run finds after downloading Tennis My Life, and the fills from the official
feed (docs/decisions/2026-10-08-prediction-run-box-scores.md, point 1).

gaps() reads a Stage 0 built on the fresh download (run.py --refresh builds one into the run's folder): every completed
match of an event that began within LOOKBACK_DAYS with a result but no box score. Each is classed:
    held        the frozen reference holds it: TML's own numbers only, when TML publishes them (the owner's choice)
    fillable    a WTA tour or WTA qualifying match after the freeze: the WTA API serves its box score
    unserved    everything else for now. ATP: the Stats Centre's keystats carry the box score, but the daily job keeps
                only speeds (not yet wired). The Slams: their feeds' live mode waits for the betting pipeline. ITF,
                team events and the WTA 125s TML lacks
fill_wta() fetches, through the WTA adapter's own client (about 2 s between requests, a receipt for every answer, a
stop on any block), each fillable match's edition list (refetched while the edition runs) and its box score (once). A
gap is linked to the API's match within the edition by the two players' name keys and the draw (main or
qualifying), and kept only when every set's games agree with TML's score. The API's counts become Stage 0's nine as
data_continuity/sources.py reads them: break points are recorded on the returner's side.

The fills take the override table's columns (stage0_build.apply_box_overrides: TML's tour, normalised tournament id,
round and the two players' name keys), so the sandbox's Stage 0 applies them with the decided Slam overrides. They are
rebuilt at every run, so a match TML has since completed takes TML's numbers, and they never reach the repository's
Stage 0 or a template build.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.prediction_run import common as P
from src.eda.prediction_run import live_rows as LR
from src.eda.predictability_diagnostic import common as C
from src.eda.predictability_diagnostic import stage0_build as B

COUNTS = list(C.BOX_SOURCE_NAMES)                  # Stage 0's nine counts, in the override table's order
SET = re.compile(r"(\d+)-(\d+)")


def reference_ids() -> set[str]:
    from src.eda.current_best_model import history as H

    return set(pd.read_parquet(H.REF_STAGE0 / "stage0_matches.parquet", columns=["match_id"])["match_id"].astype(str))


def gaps(stage0: Path, today: pd.Timestamp, held: set[str]) -> pd.DataFrame:
    """Completed matches of events that began within LOOKBACK_DAYS, without a box score, with their class."""
    m = pd.read_parquet(stage0 / "stage0_matches.parquet")
    m["match_id"] = m["match_id"].astype(str)
    recent = m["tournament_date"] >= today - pd.Timedelta(days=P.LOOKBACK_DAYS)
    g = m[recent & m["status"].eq("completed") & ~m["has_box"].astype(bool)].copy()
    g["held"] = g["match_id"].isin(held)
    wta_tour = g["tour"].eq("wta") & g["level"].isin(["GS", "FIN", "T1000", "T500", "T250"]) & g["source"].eq("tml")
    g["class"] = np.select([g["held"], wta_tour & ~g["level"].eq("GS")], ["held", "fillable"], "unserved")
    return g


def tml_keys(rows: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """The override table's key of each Stage 0 match: its TML row's tour, normalised id, round and name keys."""
    own = LR.raw_of(rows, raw)
    return pd.DataFrame({"tour": rows["tour"].to_numpy(),
                         "tid": own["tourney_id"].astype(str).str.replace(r"-0+(\d)", r"-\1", regex=True).to_numpy(),
                         "round": own["round"].astype(str).str.upper().to_numpy(),
                         "winner_key": B.S.keys_for(own["winner_name"]).to_numpy(),
                         "loser_key": B.S.keys_for(own["loser_name"]).to_numpy(),
                         "winner_name": own["winner_name"].to_numpy(), "loser_name": own["loser_name"].to_numpy(),
                         "tml_score": own["score"].to_numpy(), "stage0_match_id": rows["match_id"].to_numpy()},
                        index=rows.index)


def games(score: str) -> list[tuple[int, int]]:
    return [(int(a), int(b)) for a, b in SET.findall(str(score or ""))]


def api_games(m: dict, winner_side: str) -> list[tuple[int, int]]:
    out = []
    for n in range(1, 6):
        a, b = str(m.get(f"ScoreSet{n}A") or "").strip(), str(m.get(f"ScoreSet{n}B") or "").strip()
        if not (a.isdigit() and b.isdigit()):
            break
        out.append((int(a), int(b)) if winner_side == "A" else (int(b), int(a)))
    return out


def api_counts(total: dict, side: str) -> dict:
    """Stage 0's nine counts of one side of a WTA API box score (setnum 0), as data_continuity/sources.py reads them."""
    other = "b" if side == "a" else "a"

    def n(name: str, s: str = side) -> float:
        v = total.get(f"{name}{s}")
        try:
            return float(v)
        except (TypeError, ValueError):
            return float("nan")

    return {"ace": n("aces"), "df": n("dblflt"), "svpt": n("totservplayed"), "first_in": n("ptsplayed1stserv"),
            "first_won": n("ptswon1stserv"), "second_won": n("ptstotwonserv") - n("ptswon1stserv"),
            "sv_gms": n("servgamesplayed"), "bp_saved": n("breakptsplayed", other) - n("breakptsconv", other),
            "bp_faced": n("breakptsplayed", other)}


def fill_wta(fillable: pd.DataFrame, keys: pd.DataFrame, max_requests: int) -> tuple[pd.DataFrame, list[dict]]:
    """The WTA API's box score of each fillable gap, as override rows; and what happened to every gap."""
    from src.ingest.point_sources import common as PS
    from src.ingest.point_sources import feeds as F
    from src.ingest.point_sources import wta as W

    notes: list[dict] = []
    if fillable.empty:
        return pd.DataFrame(), notes
    client = W.make_client(min_interval=2.0, jitter=1.0, max_requests=max_requests)
    receipts = PS.receipts_for(W.SOURCE)
    fills = []
    try:
        years = sorted(set(int(y) for y in fillable["year"]))
        for y in years:
            W.fetch_calendar(client, receipts, y, refresh=True)
        editions = {(e["tournament_id"], int(e["year"])): e for e in W.load_editions(years)}
        fillable = fillable.assign(api_tid=keys.loc[fillable.index, "tid"].str.split("-").str[1])
        for (api_tid, year), group in fillable.groupby(["api_tid", "year"]):
            edition = editions.get((str(api_tid), int(year)))
            if edition is None:
                notes += [{"match_id": mid, "outcome": "edition not in the WTA calendar"} for mid in group["match_id"]]
                continue
            W.fetch_listing(client, receipts, edition, refresh=True)
            played = [m for m in W.load_listing(str(api_tid), int(year)) if m.get("DrawMatchType") == "S"
                      and W.is_played(m)]
            for i, gap in group.iterrows():
                k = keys.loc[i]
                level = "Q" if bool(gap["qualifying"]) else "M"
                want = {k["winner_key"], k["loser_key"]}
                cands = []
                for m in played:
                    a = B.S.name_key(f"{m.get('PlayerNameFirstA') or ''} {m.get('PlayerNameLastA') or ''}")
                    b = B.S.name_key(f"{m.get('PlayerNameFirstB') or ''} {m.get('PlayerNameLastB') or ''}")
                    if m.get("DrawLevelType") == level and {a, b} == want:
                        cands.append((m, "A" if a == k["winner_key"] else "B"))
                cands = [(m, w) for m, w in cands if api_games(m, w) == games(k["tml_score"])]
                if len(cands) != 1:
                    notes.append({"match_id": gap["match_id"], "outcome": f"{len(cands)} WTA API matches agree"})
                    continue
                m, w = cands[0]
                receipt = W.fetch_endpoint(client, receipts, str(api_tid), int(year), m["MatchID"], "stats",
                                           refresh=False, extra={"tier": edition["tier"], "draw": W.draw_of(m),
                                                                 "round": m.get("RoundID"), "prediction_run": True})
                if receipt.get("status") != 200:
                    notes.append({"match_id": gap["match_id"], "outcome": f"stats {receipt.get('error') or receipt.get('status')}"})
                    continue
                rows = W.stats_rows(str(api_tid), int(year), m["MatchID"],
                                    PS.read_json(W.endpoint_dest(str(api_tid), int(year), m["MatchID"], "stats")))
                total = next((r for r in rows if str(r.get("setnum")) == "0"), None)
                if total is None:
                    notes.append({"match_id": gap["match_id"], "outcome": "stats without the match's totals"})
                    continue
                win, lose = api_counts(total, w.lower()), api_counts(total, "b" if w == "A" else "a")
                row = {"box_source": "wta_api_live", "feed_key": f"wta:{api_tid}/{year}/{m['MatchID']}",
                       **k.to_dict(), "score": "", "minutes": "", "feed_sha256": receipt.get("sha256"),
                       "feed_retrieved_at": receipt.get("retrieved_at")}
                for c, src in C.BOX_SOURCE_NAMES.items():
                    row[f"w_{src}"], row[f"l_{src}"] = win[c], lose[c]
                if any(np.isnan(v) for v in list(win.values()) + list(lose.values())):
                    notes.append({"match_id": gap["match_id"], "outcome": "stats incomplete"})
                    continue
                fills.append(row)
                notes.append({"match_id": gap["match_id"], "outcome": "filled", "feed_key": row["feed_key"]})
    except (PS.Blocked, PS.BudgetExhausted, F.Stopped) as stop:     # a block stops the fills, as the decision asks
        notes.append({"match_id": None, "outcome": f"stopped: {type(stop).__name__}: {stop}"})
    return pd.DataFrame(fills), notes


def override_table(fills: pd.DataFrame) -> pd.DataFrame:
    """The decided Slam overrides and the run's fills, in the override table's columns."""
    decided = pd.read_csv(B.DECIDED_OVERRIDES, dtype=str, keep_default_na=False)
    if fills.empty:
        return decided
    f = fills.reindex(columns=decided.columns).astype(object).where(fills.reindex(columns=decided.columns).notna(), "")
    for col in [c for c in decided.columns if c.startswith(("w_", "l_"))]:
        f[col] = pd.to_numeric(fills[col]).astype(int).astype(str)
    return pd.concat([decided, f], ignore_index=True)


def agreement(found: pd.DataFrame, raw: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """For matches TML already scored: the share of player rows where the WTA API's count (as a fill would give it)
    equals TML's, count by count. Both sides are in TML's orientation (its winner and loser)."""
    own = LR.raw_of(matches, raw).assign(match_id=matches["match_id"].to_numpy()).set_index("match_id")
    f = found.set_index("stage0_match_id")
    rows = []
    for c, src in C.BOX_SOURCE_NAMES.items():
        api = pd.concat([pd.to_numeric(f[f"w_{src}"]), pd.to_numeric(f[f"l_{src}"])])
        tml = pd.concat([pd.to_numeric(own.loc[f.index, f"w_{src}"], errors="coerce"),
                         pd.to_numeric(own.loc[f.index, f"l_{src}"], errors="coerce")])
        rows.append({"count": c, "player_rows": int(len(api)), "equal": int((api.to_numpy() == tml.to_numpy()).sum()),
                     "share_equal": round(float((api.to_numpy() == tml.to_numpy()).mean()), 4) if len(api) else None,
                     "mean_api_minus_tml": round(float((api.to_numpy() - tml.to_numpy()).mean()), 3) if len(api) else None})
    return pd.DataFrame(rows)


def main() -> int:
    """Check the fill against TML where TML has the box score: the agreement the fills would bring."""
    import argparse
    import json

    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("--stage0", default=str(C.OUT), help="the Stage 0 folder (default: the repository's)")
    ap.add_argument("--events", required=True, help="comma list of Stage 0 tournament ids (WTA)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-requests", type=int, default=200)
    a = ap.parse_args()
    m = pd.read_parquet(Path(a.stage0) / "stage0_matches.parquet")
    m["match_id"] = m["match_id"].astype(str)
    scored = m[m["tournament_id"].isin(a.events.split(",")) & m["tour"].eq("wta") & m["status"].eq("completed")
               & m["has_box"].astype(bool) & m["source"].eq("tml")]
    raw = LR.staged_tml(sorted({int(y) for y in scored["year"]}))
    keys = tml_keys(scored, raw)
    found, notes = fill_wta(scored, keys, a.max_requests)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    table = agreement(found, raw, scored[scored["match_id"].isin(set(found.get("stage0_match_id", [])))]) \
        if len(found) else pd.DataFrame()
    table.to_csv(out / "fill_agreement.csv", index=False)
    summary = {"matches": int(len(scored)), "fetched": int(len(found)),
               "outcomes": pd.Series([n["outcome"] for n in notes]).value_counts().to_dict(),
               "agreement": table.to_dict("records")}
    (out / "fill_agreement.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
