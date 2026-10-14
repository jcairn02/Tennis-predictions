"""Check tennis-data.co.uk's Court against a second source, event by event, on every model match; and the rule's values.

    women   the WTA's own calendar (its inOutdoor per edition, matched to each event as status.py matches it)
    men     Stage 0's flag (Tennis My Life's event field, the model's men's input)
Then the rule (status.py) against the model's input as built before 9 Oct 2026 (the Pinnacle-first instance's frame,
on the tables of 8 Oct 2026): every value it adds or changes.

No result is read. Writes, in data/studies/indoor_fill/:
    crosscheck_events.csv   one row per model event: tennis-data's Court, the second source, the rule's value and source
    crosscheck.json         agreement by tour and season (events and matches), every disagreement, the events without a
                            second source, and the rule's values against the old input
Run: ./python.sh src/eda/indoor_fill/crosscheck.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.indoor_fill import status as ST  # noqa: E402

OUT = ROOT / "data" / "studies" / "indoor_fill"
FRAME = ROOT / "data" / "studies" / "current_best_model" / "pinnacle_first_2026-10-09" / "model_frame.parquet"


def one(x: pd.Series):
    """An event's single value (NaN when its rows disagree or none is known)."""
    v = x.dropna().unique()
    return v[0] if len(v) == 1 else np.nan


def events(t: pd.DataFrame) -> pd.DataFrame:
    m = ST.stage0_rows(t["match_id"])[["match_id", "tournament_name"]]
    t = t.merge(m, on="match_id", how="left")
    g = t.groupby(["tour", "year", "tournament_id"], sort=True)
    ev = g.agg(tournament_name=("tournament_name", "first"), matches=("match_id", "size"),
               court=("own", one), wta_calendar=("calendar", one), stage0=("stage0", one),
               stage0_known=("stage0", lambda x: int(x.notna().sum())), value=("indoor", one),
               source=("source", lambda x: "/".join(sorted(set(x)))), old=("old", one),
               old_known=("old", lambda x: int(x.notna().sum())), wta_id=("wta_id", "first"),
               wta_title=("wta_title", "first"), wta_how=("wta_how", "first")).reset_index()
    ev["second"] = np.where(ev["tour"].eq("wta"), ev["wta_calendar"], ev["stage0"])
    both = ev["court"].notna() & ev["second"].notna()
    ev["agree"] = np.where(both, ev["court"] == ev["second"], np.nan)
    return ev


def main() -> int:
    f = pd.read_parquet(FRAME, columns=["match_id", "tour", "season", "in_indoor"])
    f["match_id"] = f["match_id"].astype(str)
    t = ST.table(f["match_id"])
    if len(t) != len(f):
        raise SystemExit(f"the rule covers {len(t)} of the frame's {len(f)} matches")
    t = t.merge(f[["match_id", "in_indoor"]].rename(columns={"in_indoor": "old"}), on="match_id")
    ev = events(t)
    OUT.mkdir(parents=True, exist_ok=True)
    ev.to_csv(OUT / "crosscheck_events.csv", index=False)
    both = ev[ev["agree"].notna()].assign(agree=lambda d: d["agree"].astype(bool))
    by = both.assign(agree_matches=np.where(both["agree"], both["matches"], 0)).groupby(["tour", "year"]).agg(
        events=("agree", "size"), events_agree=("agree", "sum"), matches=("matches", "sum"),
        matches_agree=("agree_matches", "sum")).reset_index()
    tot = by.groupby("tour")[["events", "events_agree", "matches", "matches_agree"]].sum()
    keep = ["tour", "year", "tournament_id", "tournament_name", "matches", "court", "second", "value", "source",
            "wta_title"]
    dis = ev[ev["agree"].eq(False)]
    no_second = ev[ev["second"].isna()]
    # the rule against the old input
    changed = t["indoor"].ne(t["old"]) & ~(t["indoor"].isna() & t["old"].isna())
    chg = t[changed].groupby(["tour", "year", "source"]).agg(matches=("match_id", "size"),
                                                             filled=("old", lambda x: int(x.isna().sum()))).reset_index()
    sources = t.groupby(["tour", "source"]).size().rename("matches").reset_index()
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "frame": FRAME.relative_to(ROOT).as_posix(), "matches": int(len(t)), "events": int(len(ev)),
               "events_with_mixed_court": int(((t.groupby(["tour", "tournament_id"])["own"].nunique()) > 1).sum()),
               "agreement_totals": tot.reset_index().to_dict("records"),
               "agreement_by_tour_season": by.to_dict("records"),
               "disagreements": dis[keep].to_dict("records"),
               "events_without_second_source": no_second[keep].to_dict("records"),
               "rule_sources": sources.to_dict("records"),
               "rule_missing": int(t["indoor"].isna().sum()),
               "rule_vs_old_input": {"changed_or_filled": int(changed.sum()),
                                     "filled": int((changed & t["old"].isna()).sum()),
                                     "changed_known_value": int((changed & t["old"].notna()).sum()),
                                     "by_tour_season_source": chg.to_dict("records")}}
    (OUT / "crosscheck.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(tot.assign(event_share=lambda d: (d["events_agree"] / d["events"]).round(4),
                     match_share=lambda d: (d["matches_agree"] / d["matches"]).round(4)).to_string())
    print(f"events: {len(ev)}; mixed Court: {summary['events_with_mixed_court']}; without a second source: "
          f"{len(no_second)}; the rule leaves {summary['rule_missing']} matches unknown")
    print(dis[keep].to_string(index=False))
    print(no_second[keep].to_string(index=False))
    print(sources.to_string(index=False))
    print(json.dumps(summary["rule_vs_old_input"], indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
