"""The prediction run's proof that live inputs are the training inputs: played matches replayed as live rows must get
exactly the inputs the template's frame gave them (docs/decisions/2026-10-08-prediction-run-box-scores.md, point 4).

A replay is a prediction run on the morning of a past day. For one round of a week's main-tour events (Tennis My Life's
era, so every row is a TML row; not the two Slams whose box scores the official feeds override):
    the round's matches of its first day become live rows: their own TML rows, their outcome removed (no score's games,
    no minutes, no box score) and a placeholder result, won by Stage 0's player A (a hash of the match id, so the
    placeholder is the real result in about half the matches and the reverse in the rest);
    the round's later days and the events' later rounds are left out, as they had not been played that morning (Stage 0
    would otherwise restore the real result from who played on);
    each match is priced and dated as the frame's own were: Stage 1's margin-free closing price and tennis-data's day.
The sandbox then builds the whole chain (run.py --build). compare() sets the replayed matches' 58 inputs against the
template's frame of 8 Oct (data/studies/model_rebuild/model_frame.parquet). Equal inputs prove that the live path is the
training path: the placeholder result, the missing box score and the score never reach a match's own inputs, and the
live row's price and day are read as tennis-data's are.

One day only, because what a replay changes spreads to every later match: a match without its box score leaves the
jointly solved IOS ratings of the days after it, the ratings of a dropped match's players reach their later opponents,
and the timeline's class windows pool every event's dated matches. The first replay (9 Oct 2026, two weeks of round-of-16
matches) found exactly that: its 23 first-day matches equal the frame on all 58 inputs, while its later matches, replayed
or not, moved with those changes. The first day's matches can reach none of them.

Two datings. "training" keeps the played matches' own days (their point logs and other sources still link them):
the code path alone. "live" dates them as upcoming matches are dated (inject.py: no source's link, the tour's usual
window around the day): what live dating changes. The price is the frame's in both.

The template compared with (since 10 Oct 2026): --template <folder> names a built instance (its model_frame.parquet and
model_inputs.json), so a replay built with the level layer (run.py --build, the default) is compared with the template
built with it; without --template, the frame of 8 Oct, built without the layer (a replay built with --no-layer).

Run: ./python.sh src/eda/prediction_run/replay.py --prepare --out data/studies/prediction_run/replay_<stamp>
         [--week 2026-07-13] [--round R16] [--winner A] [--dating live|training]
     ./python.sh src/eda/prediction_run/run.py --setup; ./python.sh src/eda/prediction_run/run.py --build <out>
     ./python.sh src/eda/prediction_run/replay.py --compare --out <out> [--template <instance folder>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import common as P  # noqa: E402
from src.eda.prediction_run import live_rows as LR  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

TEMPLATE_FRAME = ROOT / "data" / "studies" / "model_rebuild" / "model_frame.parquet"
TEMPLATE_INPUTS = ROOT / "data" / "studies" / "model_rebuild" / "model_inputs.json"
OVERRIDDEN = ("Wimbledon", "US Open")              # their 2026 box scores come from the feeds (decision 2026-10-06)
LEVELS = ("T1000", "T500", "T250")
TOL = 1e-9


def select(week: str, rnd: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The targets (the round's matches of its first day across the week's events, in the template's frame, with a box
    score) and what that morning had not seen: the round's later days and the events' later rounds."""
    m = pd.read_parquet(C.MATCHES)
    m["match_id"] = m["match_id"].astype(str)
    frame = set(pd.read_parquet(TEMPLATE_FRAME, columns=["match_id"])["match_id"].astype(str))
    obs = pd.read_parquet(ROOT / P.MT / "timing.parquet", columns=["match_id", "obs"]).astype({"match_id": str})
    start = pd.Timestamp(week)
    ev = m[m["tournament_date"].between(start, start + pd.Timedelta(days=6)) & m["source"].eq("tml")
           & m["level"].isin(LEVELS) & ~m["qualifying"] & ~m["tournament_name"].isin(OVERRIDDEN)]
    ev = ev.merge(obs, on="match_id", how="left")
    in_round = ev[ev["round"].eq(rnd)]
    first = in_round["obs"].min()
    targets = in_round[in_round["obs"].eq(first) & in_round["match_id"].isin(frame) & in_round["has_box"].astype(bool)]
    later = ev[(ev["round_order"] > C.ROUND_ORDER[rnd]) | (ev["round"].eq(rnd) & ~ev["match_id"].isin(set(targets["match_id"])))]
    return targets.drop(columns="obs"), later.drop(columns="obs")


def meta_for(targets: pd.DataFrame) -> pd.DataFrame:
    """Each target's price, day and venue as the frame had them: Stage 1's margin-free close (A's), tennis-data's day,
    and the city of its tennis-data row."""
    o = pd.read_parquet(C.OUT / "stage1_odds.parquet",
                        columns=["match_id", "p_avg_a", "td_date", "td_file", "td_row"]).astype({"match_id": str})
    o = o.set_index("match_id").reindex(targets["match_id"])
    if o["p_avg_a"].isna().any() or o["td_date"].isna().any():
        raise SystemExit("replay: a target lacks Stage 1's price or day")
    from src.eda.match_timing import srcc_tennis_data as TD

    venue = TD.locations(o.reset_index().rename(columns={"index": "match_id"}))
    return pd.DataFrame({"match_id": targets["match_id"].to_numpy(), "day": pd.to_datetime(o["td_date"]).dt.normalize()
                         .to_numpy(), "p_a": o["p_avg_a"].to_numpy(), "venue": venue.to_numpy(),
                         "tour": targets["tour"].to_numpy(), "tournament_name": targets["tournament_name"].to_numpy(),
                         "round": targets["round"].to_numpy()})


def prepare(out: Path, week: str, rnd: str, winner: str, dating: str) -> dict:
    targets, later = select(week, rnd)
    players = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "player_id", "player_name"]).astype({"match_id": str})
    raw = LR.staged_tml([int(week[:4])])
    rows = LR.replay_rows(targets, later, raw, players, placeholder_winner=winner)
    meta = meta_for(targets)
    meta["dating"] = dating
    real_a_won = targets["a_won"].astype(bool).to_numpy()
    meta["placeholder_is_real_result"] = real_a_won if winner == "A" else ~real_a_won
    out.mkdir(parents=True, exist_ok=True)
    rows.to_parquet(out / "live_rows.parquet", index=False)
    meta.to_parquet(out / "live_meta.parquet", index=False)
    summary = {"kind": "replay", "prepared_at": P.stamp(), "week": week, "round": rnd, "placeholder_winner": winner,
               "dating": dating,
               "targets": int(len(targets)), "left_out_later": int(len(later)),
               "placeholder_reverses_result": int((~meta["placeholder_is_real_result"]).sum()),
               "by_event": targets.groupby(["tour", "tournament_name"]).size().rename("matches").reset_index()
               .to_dict("records"),
               "template_frame": str(TEMPLATE_FRAME.relative_to(ROOT))}
    P.write_json(out / "replay.json", summary)
    return summary


def compare(out: Path, template: Path | None = None, frame: str = "model_frame.parquet") -> dict:
    """The replayed matches' inputs against the template frame's, input by input. Equal within TOL counts as equal.
    template: a built instance's folder (default the frame of 8 Oct); frame: which of its frames. A replay prices its
    matches with Stage 1's close (the books' average, meta_for), so an instance with the Pinnacle-first odds input is
    compared on its chain frame (model_frame_chain.parquet: the same inputs, the books' average odds input)."""
    frame_path = TEMPLATE_FRAME if template is None else Path(template) / frame
    inputs_path = TEMPLATE_INPUTS if template is None else Path(template) / "model_inputs.json"
    names = [i["name"] for i in json.loads(inputs_path.read_text(encoding="utf-8"))["inputs"]]
    cols = ["match_id"] + [f"in_{n}" for n in names]
    live = pd.read_parquet(out / "live_frame.parquet", columns=cols).astype({"match_id": str}).set_index("match_id")
    meta = pd.read_parquet(out / "live_meta.parquet").astype({"match_id": str}).set_index("match_id")
    tmpl = pd.read_parquet(frame_path, columns=cols).astype({"match_id": str}).set_index("match_id")
    ids = meta.index
    missing = sorted(set(ids) - set(live.index))
    ids = ids[ids.isin(live.index)]
    rows = []
    for n in names:
        a = pd.to_numeric(live.loc[ids, f"in_{n}"], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(tmpl.loc[ids, f"in_{n}"], errors="coerce").to_numpy(dtype=float)
        both_nan = np.isnan(a) & np.isnan(b)
        diff = np.where(both_nan, 0.0, np.abs(a - b))
        diff = np.where(np.isnan(diff), np.inf, diff)
        reversed_ = ~meta.loc[ids, "placeholder_is_real_result"].to_numpy(dtype=bool)
        rows.append({"input": n, "matches": int(len(ids)), "equal": int((diff <= TOL).sum()),
                     "max_abs_diff": float(diff.max()) if len(diff) else 0.0,
                     "differ_where_placeholder_reverses": int(((diff > TOL) & reversed_).sum())})
    table = pd.DataFrame(rows)
    table.to_csv(out / "replay_compare.csv", index=False)
    per_match = []
    for mid in ids:
        a = pd.to_numeric(live.loc[mid], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(tmpl.loc[mid], errors="coerce").to_numpy(dtype=float)
        d = np.where(np.isnan(a) & np.isnan(b), 0.0, np.abs(a - b))
        bad = [names[i] for i in np.flatnonzero(~(d <= TOL))]
        per_match.append({"match_id": mid, "inputs_differing": len(bad), "which": ";".join(bad)})
    pd.DataFrame(per_match).to_csv(out / "replay_compare_matches.csv", index=False)
    summary = {"compared_at": P.stamp(), "template_frame": str(frame_path), "matches": int(len(ids)),
               "missing_from_live_frame": missing,
               "inputs": len(names), "inputs_equal_on_every_match": int((table["equal"] == table["matches"]).sum()),
               "matches_equal_on_every_input": int(sum(r["inputs_differing"] == 0 for r in per_match)),
               "differing_inputs": table[table["equal"] < table["matches"]].to_dict("records")}
    P.write_json(out / "replay_compare.json", summary)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--prepare", action="store_true")
    which.add_argument("--compare", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--week", default="2026-07-13", help="the Monday of the week replayed")
    ap.add_argument("--round", default="R16")
    ap.add_argument("--winner", default="A", choices=["A", "B"])
    ap.add_argument("--dating", default="live", choices=["live", "training"],
                    help="live: dated as an upcoming match is (inject.py's links and pin); training: the played "
                         "matches keep their sources' days, which checks the code path alone")
    ap.add_argument("--template", default=None, help="--compare: a built instance's folder (model_frame.parquet, "
                                                     "model_inputs.json); default the frame of 8 Oct")
    ap.add_argument("--frame", default="model_frame.parquet", help="--compare: the instance's frame to compare with "
                                                                   "(model_frame_chain.parquet: the books' average odds)")
    a = ap.parse_args()
    out = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    tmpl = None if a.template is None else (Path(a.template) if Path(a.template).is_absolute() else ROOT / a.template)
    res = prepare(out, a.week, a.round, a.winner, a.dating) if a.prepare else compare(out, tmpl, a.frame)
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
