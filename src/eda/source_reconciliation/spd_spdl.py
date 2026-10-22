"""Source reconciliation, Part G (serve speed), step 3b: how far each consensus history moves spd_L. Data level only:
no match result, no coefficient refit, nothing scored.

The project's own column builder (serve_speed_tabpfn/adaptive/columns.py, build; through features.py, panel.py's
EditionOffsets and latency/features_latency.py) runs in memory on each history of speed/histories/, exactly as
infosys_atp_backfill/columns.py runs it on the live feed's history: the same 63,737 frame matches, release days
(latency/availability.parquet), constants and standardisers. Check first: the "current" history must reproduce
data/studies/infosys_atp_backfill/speed_columns_augmented.parquet (the columns stage 2's coefficients are fitted on)
exactly, every column.

Moves are counted as the input-data audit's propagation table did (|delta spd_L| >= 0.25, 0.5, 1 unit; one unit =
1.9496 km/h of form difference), on the men's frame matches of 2024-26 (the audit's 7,070) and of 2019-23 (the seasons
the coefficients are fitted on), for scenario A (instant), B (the weekly feed: the history of every replay before
8 Oct 2026, the L_weekly coefficients) and D (the daily feed, L_daily).

Live form (the same rule on today's live panel): live_panel.load()'s frozen rows take each history's values, the daily
rows are kept, and serve_speed_tabpfn/live/form.py's form_as_of gives each man's f_hat on --day (default 2026-10-16);
moves in units of spd_L per player.

Writes speed/spdl/<rule>.parquet (match_id and every spd_* column; git-ignored), speed/t3_spdl_moves.csv,
speed/t3_live_form.csv, speed/spdl_summary.json.
Run: ./python.sh src/eda/source_reconciliation/spd_spdl.py [--rules a,b] [--day 2026-10-16]   (about 5 minutes a rule)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402

OUT = C.OUT / "speed"
HIST = OUT / "histories"
SPDL = OUT / "spdl"
REF = C.STUDIES / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
RULES = ["points_first", "median", "ks_within5", "ks_within3", "ks_within5_audit", "ks_within5_literal"]
SCEN = ("A", "B", "D")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def build_on(history: pd.DataFrame) -> pd.DataFrame:
    """adaptive/columns.py's build with `history` in place of the panel (as infosys_atp_backfill/columns.py)."""
    from src.eda.serve_speed_tabpfn import panel as P
    from src.eda.serve_speed_tabpfn.adaptive import columns as CO
    frozen_load = P.load_panel
    P.load_panel = lambda use_only=True: (history[history["use"].astype(bool)].reset_index(drop=True)
                                          if use_only else history)
    try:
        return CO.build(probes=False)["out"]
    finally:
        P.load_panel = frozen_load


def moves(base: pd.DataFrame, new: pd.DataFrame, keys: pd.DataFrame, rule: str) -> list[dict]:
    k = keys.set_index("match_id").reindex(base["match_id"])
    men = k["tour"].eq("atp").to_numpy()
    rows = []
    for s in SCEN:
        d = (new[f"spd_L_{s}"].to_numpy(float) - base[f"spd_L_{s}"].to_numpy(float))
        for label, sel in (("2024-26", men & k["season"].between(2024, 2026).to_numpy()),
                           ("2019-23", men & k["season"].between(2019, 2023).to_numpy()),
                           *((str(y), men & k["season"].eq(y).to_numpy()) for y in range(2019, 2027))):
            a = np.abs(d[sel])
            if not len(a):
                continue
            rows.append({"rule": rule, "scenario": s, "seasons": label, "men_matches": int(len(a)),
                         "moved_ge_0.05": int((a >= 0.05).sum()), "moved_ge_0.25": int((a >= 0.25).sum()),
                         "moved_ge_0.5": int((a >= 0.5).sum()), "moved_ge_1": int((a >= 1).sum()),
                         "mean_abs_units": float(a.mean()), "max_abs_units": float(a.max()),
                         "sum_signed_units": float(d[sel].sum())})
    return rows


def live_form(rules: list[str], day: int) -> pd.DataFrame:
    from src.eda.serve_speed_tabpfn.live import form as SF
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    live = LP.load()
    fr = live["live_source"].eq("frozen").to_numpy()
    base = SF.form_as_of(day, live).set_index("player_id")
    rows = []
    for rule in rules:
        h = pd.read_parquet(HIST / f"{rule}.parquet", columns=["match_id", "side", "y", "use"]).set_index(
            ["match_id", "side"])
        alt = live.copy()
        idx = pd.MultiIndex.from_frame(alt.loc[fr, ["match_id", "side"]])
        alt.loc[fr, "y"] = h["y"].reindex(idx).to_numpy()
        alt.loc[fr, "use"] = (alt.loc[fr, "use"].astype(bool).to_numpy()
                              & h["use"].reindex(idx).fillna(False).astype(bool).to_numpy())
        f = SF.form_as_of(day, alt).set_index("player_id").reindex(base.index)
        du = (f["f_hat"] - base["f_hat"]).abs() / SF.SD_L
        active = base["k28"] > 0
        for label, sel in (("all players with a row in 364 days", base["hist"] > 0),
                           ("a reading in the last 28 days", active)):
            a = du[sel]
            rows.append({"rule": rule, "day": str(pd.Timestamp("1970-01-01") + pd.Timedelta(days=day))[:10],
                         "players": label, "n": int(len(a)), "moved_ge_0.1_units": int((a >= 0.1).sum()),
                         "moved_ge_0.25_units": int((a >= 0.25).sum()), "moved_ge_0.5_units": int((a >= 0.5).sum()),
                         "max_units": float(a.max()) if len(a) else np.nan})
    return pd.DataFrame(rows)


def merged(path: Path, new: pd.DataFrame, rules: list[str]) -> pd.DataFrame:
    """The rules re-run replace their own rows of an existing table; the other rules' rows are kept."""
    if not path.exists():
        return new
    old = pd.read_csv(path)
    return pd.concat([old[~old["rule"].isin(rules)], new], ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default=",".join(RULES))
    ap.add_argument("--day", default="2026-10-16")
    a = ap.parse_args()
    rules = [r for r in a.rules.split(",") if r]
    from src.eda.serve_speed_tabpfn import panel as P
    keys = P.load_frame_keys()[["match_id", "tour", "season"]]
    SPDL.mkdir(parents=True, exist_ok=True)
    log("base: the current history")
    cur = pd.read_parquet(HIST / "current.parquet")
    base = build_on(cur)
    ref = pd.read_parquet(REF)
    pd.testing.assert_frame_equal(base.reset_index(drop=True), ref[base.columns].reset_index(drop=True),
                                  check_dtype=False)
    log("the current history reproduces speed_columns_augmented.parquet exactly (every column)")
    base.to_parquet(SPDL / "current.parquet", index=False)
    out = []
    for rule in rules:
        log(f"rule {rule}")
        new = build_on(pd.read_parquet(HIST / f"{rule}.parquet"))
        assert (new["match_id"].to_numpy() == base["match_id"].to_numpy()).all()
        new.to_parquet(SPDL / f"{rule}.parquet", index=False)
        out.extend(moves(base, new, keys, rule))
        m = [r for r in out if r["rule"] == rule and r["seasons"] == "2024-26"]
        log("  " + "; ".join(f"{r['scenario']}: >=0.25 {r['moved_ge_0.25']}, >=0.5 {r['moved_ge_0.5']}, >=1 "
                             f"{r['moved_ge_1']}, max {r['max_abs_units']:.2f}" for r in m))
    mv = merged(OUT / "t3_spdl_moves.csv", pd.DataFrame(out), rules)
    mv.to_csv(OUT / "t3_spdl_moves.csv", index=False, float_format="%.4f")
    day = (pd.Timestamp(a.day) - pd.Timestamp("1970-01-01")).days
    log(f"live form on {a.day}")
    lf = merged(OUT / "t3_live_form.csv", live_form(rules, day), rules)
    lf.to_csv(OUT / "t3_live_form.csv", index=False, float_format="%.4f")
    C.write_json(OUT / "spdl_summary.json", {
        "reads_results": False, "reproduced": REF.relative_to(ROOT).as_posix(),
        "moves": mv[mv["seasons"].isin(["2024-26", "2019-23"])].to_dict(orient="records"),
        "live_form": lf.to_dict(orient="records")})
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
