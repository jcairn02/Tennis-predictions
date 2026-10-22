"""The lower-level feed's "player in two main draws of one week" flags, compared with the last advanced snapshot's
(owner, 14 Oct 2026: docs/decisions/2026-10-14-p6-data-issues.md, point 4).

Why. The builder's duplicate check counts the player-weeks in which a player of a new match sits in the main draws of
two tournaments with the same Monday (candidate_stage0.duplicates: an identity merge or a misdated event). It never
stops a snapshot, and it should not: the history holds such cases that are known and harmless (team events and ITF
weeks listed under two names, the W15 Luque 2026 edition the WTA website copy lists twice). But a new case is the
signature of a source gone wrong: 25 of the 13 Oct candidate's flags were the WTA website copy's misfiled week of
7-14 Sep 2026 (docs/studies/p6_data_issues/README.md, section 4). So the feed alerts on a flag that the last advanced
snapshot did not hold, and never blocks on it.

A flag is a player-week: the player's id, the Monday (Stage 0's tournament date) and the tournament ids, as the builder
counts it (round robins and qualifying left out; a week counts when one of its matches is new). Flags are read from a
candidate folder (stage0_matches.parquet and additions.parquet: the feed's derived candidate, <label>_gaps) and kept
per run in data/studies/data_gaps_2026/feed/two_draws/<label>.csv. The baseline is the newest file of an advanced
snapshot's label; the first time, the 13 Oct snapshot's own candidate folder (BASELINE_FOLDER).

Run: ./python.sh src/eda/data_gaps_2026/two_draws.py --candidate <folder> --label <label>   (prints the comparison)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "data_gaps_2026" / "feed" / "two_draws"
BASELINE_LABEL = "F20261013c"
BASELINE_FOLDER = ROOT / "data" / "studies" / "data_gaps_2026" / "feed" / "candidates" / "F20261013c_gaps"
KEY = ["player_id", "tournament_date", "tournaments"]


def flags(folder: Path) -> pd.DataFrame:
    """The player-weeks with a new match in two main draws (the builder's duplicates check, listed)."""
    folder = Path(folder)
    m = pd.read_parquet(folder / "stage0_matches.parquet",
                        columns=["match_id", "tournament_id", "tournament_name", "tournament_date", "round",
                                 "qualifying", "player_a_id", "player_b_id"])
    new = set(pd.read_parquet(folder / "additions.parquet", columns=["match_id"])["match_id"]) \
        if (folder / "additions.parquet").exists() else set()
    m["new"] = m["match_id"].isin(new)
    pl = pd.concat([m.assign(player_id=m["player_a_id"]), m.assign(player_id=m["player_b_id"])], ignore_index=True)
    pl = pl[pl["round"].ne("RR") & ~pl["qualifying"].astype(bool)]
    g = pl.groupby(["player_id", "tournament_date"])
    pw = g.agg(events=("tournament_id", "nunique"), new=("new", "any"),
               tournaments=("tournament_id", lambda s: "|".join(sorted(set(map(str, s))))),
               names=("tournament_name", lambda s: " | ".join(sorted(set(map(str, s)))))).reset_index()
    out = pw[(pw["events"] > 1) & pw["new"]].drop(columns=["events", "new"])
    out["tournament_date"] = pd.to_datetime(out["tournament_date"]).dt.strftime("%Y-%m-%d")
    return out.sort_values(KEY).reset_index(drop=True)


def baseline(advanced_labels: list[str]) -> tuple[str, pd.DataFrame]:
    """The flags of the newest advanced snapshot whose file is kept; else the 13 Oct snapshot's, from its folder."""
    for label in reversed(advanced_labels):
        p = OUT / f"{label}.csv"
        if p.exists():
            return label, pd.read_csv(p, dtype=str)
    f = flags(BASELINE_FOLDER)
    OUT.mkdir(parents=True, exist_ok=True)
    f.to_csv(OUT / f"{BASELINE_LABEL}.csv", index=False)
    return BASELINE_LABEL, f.astype(str)


def compare(current: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """The current flags the baseline did not hold (by player, week and the tournaments)."""
    seen = set(map(tuple, base[KEY].astype(str).to_numpy()))
    keys = [tuple(r) for r in current[KEY].astype(str).to_numpy()]
    return current[[k not in seen for k in keys]].reset_index(drop=True)


def check(candidate: Path, label: str, advanced_labels: list[str]) -> dict:
    """Flags of this run, kept as <label>.csv, against the baseline; the new ones in <label>_new.csv."""
    cur = flags(candidate)
    OUT.mkdir(parents=True, exist_ok=True)
    cur.to_csv(OUT / f"{label}.csv", index=False)
    base_label, base = baseline([x for x in advanced_labels if x != label])
    new = compare(cur, base)
    new.to_csv(OUT / f"{label}_new.csv", index=False)
    return {"flags": int(len(cur)), "baseline": base_label, "baseline_flags": int(len(base)), "new": int(len(new)),
            "new_examples": [f"{r.player_id} {r.tournament_date}: {r.names}" for r in new.head(5).itertuples()],
            "file": str((OUT / f"{label}_new.csv").relative_to(ROOT))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--label", required=True)
    a = ap.parse_args()
    print(json.dumps(check(Path(a.candidate), a.label, []), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
