"""Part 3 (the owner's request of 22 Oct 2026, 13:04; process_log.md Part 3): the five-pattern adjustment on qualifying.

Does the adjustment, as the daily engine applies it, help or harm the live model's qualifying forecasts? For the study's
scored qualifying matches (Part 1's primary population: 2020-2026, debut seasons out, priced), on the active instance's
build tree (the tables the study's forecasts were built on):
    members   the registered members of each match, by the tree's own copy of unpriced_leads/live_members.py (identical
              to the repository's), run inside the tree as the engine runs it inside a work tree; its not-built members
              missing, as live. Its outputs go outside the tree; the tree's own extracts are read, never written.
    z         the live gate by each match's month (patterns_live.live_gates, the tree's tables) and the frozen
              parameters (check_now/now/params.json, its SHA-256 checked by patterns_live), capped at +-3.5, as
              patterns_live.build_for_run computes it for a run
    on, off   the live model's forecast (Part 2: today's fits, the instance's stage 2 fitted on main draws, seeds 0-3)
              without and with logit q += b z (b: adjustment.json's size_per_unit_z)
    scores    the primary: paired log loss, on against off (compare.paired, matched seeds; positive = on better); each
              against the calibrated close; betting at BetOnline's and Pinnacle's closes (top_edges' rules); slices
    parity    the 16 Almaty and Brussels round-1 matches the master pipeline replayed (17 Oct 2026): their z here
              against the replay's own live z (data/studies/daily_prediction/runs/replay_2026-10-19_Q1_qualifying_
              maindate/live_patterns.parquet)
Writes data/studies/qualifying_targets/patterns/ (members.parquet and .json, z.parquet, patterns.json, rows.csv).
Run: ./python.sh src/eda/qualifying_targets/patterns_check.py --members      (about the tree's own build of the members)
     ./python.sh src/eda/qualifying_targets/patterns_check.py --score
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.qualifying_targets import score as S  # noqa: E402
from src.eda.qualifying_targets import top_edges as TE  # noqa: E402

OUT = C.OUT / "patterns"
SCRATCH = Path(os.environ.get("QT_SCRATCH", str(OUT / "scratch")))      # the members' copy of the IOS table (large)
PY = Path(os.environ.get("TENNIS_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis/python.exe"))
REPLAY = ROOT / "data" / "studies" / "daily_prediction" / "runs" / "replay_2026-10-19_Q1_qualifying_maindate"


def population() -> tuple[pd.DataFrame, pd.Index, pd.Series]:
    """Part 1's scored qualifying matches: (info, ids, the speed column) as score.qual_info gives them."""
    info, spd = S.qual_info()
    keep = ~info["debut"].to_numpy() & info["season"].isin(S.TEST).to_numpy()
    return info, info.index[keep], spd


def members() -> dict:
    """The tree's live_members.py in the tree, for the scored ids; its ace gap checked against the study frame."""
    _, ids, _ = population()
    OUT.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    id_file = OUT / "ids.txt"
    id_file.write_text("\n".join(map(str, ids)) + "\n", encoding="utf-8")
    script = C.TREE / "src" / "eda" / "unpriced_leads" / "live_members.py"
    mine = ROOT / "src" / "eda" / "unpriced_leads" / "live_members.py"
    if script.read_bytes() != mine.read_bytes():
        raise SystemExit(f"{script} differs from the repository's copy")
    cmd = [str(PY), str(script), "--ids", str(id_file), "--out", str(OUT / "members.parquet"),
           "--ios-table", str(C.TREE / "data" / "studies" / "surface_ios" / "surface_features.parquet"),
           "--ios-out", str(SCRATCH / "ios_table.parquet"), "--frame", str(C.FRAME)]
    C.log("members: " + " ".join(cmd))
    with open(OUT / "members.log", "w", encoding="utf-8") as fh:
        code = subprocess.run(cmd, cwd=C.TREE, stdout=fh, stderr=subprocess.STDOUT,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"}).returncode
    if code:
        raise SystemExit(f"live_members failed ({code}): {OUT / 'members.log'}")
    rec = json.loads((OUT / "members.json").read_text(encoding="utf-8"))
    C.log(f"members of {rec['matches']:,} matches; frame check {rec.get('frame_check')}")
    return rec


def zscores(ids: pd.Index) -> tuple[pd.DataFrame, dict]:
    """z of the ids as patterns_live.build_for_run computes a run's: the members, the study frame's inputs, each
    match's month (its observed day in the tree's timeline), the live gate on the tree, the frozen parameters."""
    from src.eda.unpriced_leads import check_now as CN
    from src.eda.unpriced_leads import live_members as LM
    from src.eda.unpriced_leads import patterns_live as PL
    from src.eda.unpriced_leads import screen as H
    cfg = PL.config()
    if not PL.is_on(cfg):
        raise SystemExit("the adjustment is off: nothing to test")
    P = PL._params(cfg)                                           # SHA-256 checked against adjustment.json
    groups = json.loads(CN.REGISTRY.read_text(encoding="utf-8"))["groups"]
    vals = pd.read_parquet(OUT / "members.parquet").astype({"match_id": str}).drop_duplicates("match_id")
    frame = pd.read_parquet(C.FRAME).astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id")
    frame = frame.reindex(pd.Index(ids).astype(str)).reset_index()
    t = pd.read_parquet(C.TREE_TIMING, columns=["match_id", "obs"]).astype({"match_id": str}).set_index("match_id")
    obs = t["obs"].reindex(frame["match_id"]).to_numpy(float)
    if np.isnan(obs).any():
        raise SystemExit(f"{int(np.isnan(obs).sum())} matches have no observed day in the tree's timeline")
    frame["day"] = pd.to_datetime(obs, unit="D")
    for k, (a, b) in H.PAIRS.items():
        frame[f"in_{k}"] = frame[f"in_{a}"] - frame[f"in_{b}"]
    frame["month"] = frame["day"].dt.to_period("M").astype(str)
    gates, gate_report = PL.live_gates(groups, frame["tour"].to_numpy(), frame["month"].to_numpy(), C.TREE)
    values = {c: vals.set_index("match_id")[c] for c in vals.columns if c != "match_id"}
    z = CN.score_from_params(groups, frame, P, gates, values=values)
    out = pd.DataFrame({"match_id": frame["match_id"], "z": z, "month": frame["month"]})
    for c in vals.columns:
        if c != "match_id":
            out[c] = values[c].reindex(frame["match_id"]).to_numpy(float)
            if c in gates:
                out[f"gate_{c}"] = gates[c]
    off_months = {c: len(v) for c, v in gate_report.items()}
    rec = {"matches": int(len(out)), "z_finite": int(np.isfinite(z).sum()), "z_sd": float(np.nanstd(z)),
           "z_at_cap": int((np.abs(z) >= P["cap"] - 1e-12).sum()), "b": float(cfg["size_per_unit_z"]),
           "params_sha256": cfg["params_sha256"], "gate_months_off": off_months,
           "not_built": LM.NOT_BUILT,
           "members_present": {c: int(np.isfinite(out[c]).sum()) for c in vals.columns if c != "match_id"}}
    return out, rec


def parity(z: pd.DataFrame) -> dict:
    """The replayed round-1 matches' z here against the replay's own (the engine's patterns step in a work tree)."""
    f = REPLAY / "live_patterns.parquet"
    if not f.exists():
        return {"checked": False, "why": f"{f} missing"}
    live = pd.read_parquet(f).astype({"match_id": str}).set_index("match_id")["z"]
    here = z.set_index("match_id")["z"].reindex(live.index)
    d = (here - live).abs()
    return {"checked": True, "matches": int(len(live)), "in_population": int(here.notna().sum()),
            "max_abs_diff": float(d.max()) if d.notna().any() else None, "equal": int((d <= 1e-12).sum())}


def with_patterns(fc: tuple, shift: np.ndarray) -> tuple:
    """logit q += b z, on the seed mean's forecast and on each seed's (patterns_live.shift)."""
    from src.eda.unpriced_leads import patterns_live as PL
    mean, seeds = fc
    return PL.shift(mean, shift), PL.shift(seeds, shift[:, None])


def score() -> dict:
    info, ids, spd = population()
    z, zrec = zscores(ids)
    z.to_parquet(OUT / "z.parquet", index=False)
    par = parity(z)
    C.log(f"z: {zrec['z_finite']:,} of {zrec['matches']:,}, sd {zrec['z_sd']:.3f}; parity {par}")
    m0 = S.model(S.seed_table("M0", "qual"), info, spd)
    minfo, mz = S.main_info()
    mm = S.model(S.seed_table("M0", "main"), minfo, mz)
    off = CMP.forecasts(m0["p"], info, mm["s2"], spd, ids)         # the live model's qualifying forecast (Part 2)
    zz = z.set_index("match_id")["z"].reindex(ids.astype(str)).to_numpy(float)
    shift = zrec["b"] * np.where(np.isfinite(zz), zz, 0.0)         # a match without z gets no shift, as live
    on = with_patterns(off, shift)
    close = CMP.close_forecast(info, "p_close", S.TEST, ids)
    rows = [S.row(info, ids, off, on, True, comparison="patterns on vs off", population="all"),
            S.row(info, ids, close, off, False, comparison="off vs calibrated close", population="all"),
            S.row(info, ids, close, on, False, comparison="on vs calibrated close", population="all")]
    inf = info.loc[ids]
    slices = {"men": inf["tour"].eq("atp"), "women": inf["tour"].eq("wta"), "tour qualifying": inf["kind"].eq("TQ"),
              "Slam qualifying": inf["kind"].eq("GSQ"), "2020-2024": inf["season"].between(2020, 2024),
              "2025-2026": inf["season"].between(2025, 2026)}
    for name, mask in slices.items():
        sub = ids[mask.to_numpy()]
        pos = np.flatnonzero(mask.to_numpy())
        rows.append(S.row(info, sub, (off[0][pos], off[1][pos]), (on[0][pos], on[1][pos]), True,
                          comparison="patterns on vs off", population=name))
    acc = pd.DataFrame(rows)
    bets = []
    for venue in TE.VENUES:
        for name, q in (("off", off[0]), ("on", on[0])):
            df = TE.candidates(info, ids, q, venue)
            bets += TE.readings(df, venue, f"patterns {name}", full=False)
    bet = pd.DataFrame(bets)
    out = {"population": {"matches": int(len(ids)), "by_tour": inf["tour"].value_counts().to_dict()},
           "z": zrec, "parity": par, "shift_log_odds": {"mean_abs": float(np.abs(shift).mean()),
                                                         "max_abs": float(np.abs(shift).max()),
                                                         "share_zero": float((shift == 0).mean())},
           "accuracy": acc.to_dict("records"), "betting": bet.to_dict("records"),
           "decision_rule": "turn the patterns off for qualifying if on is worse than off by more than 0.10 mLL with "
                            "the whole 95% interval below 0; otherwise keep them on (fixed in process_log.md P3.2 "
                            "before any score)"}
    prim = acc.iloc[0]
    out["harm_check_fails"] = bool(prim["hi"] < 0 and prim["estimate"] < -0.10)
    pd.concat([acc.assign(kind="accuracy"), bet.assign(kind="betting")], ignore_index=True).to_csv(
        OUT / "rows.csv", index=False)
    C.write_json(OUT / "patterns.json", out)
    pd.set_option("display.width", 250)
    print(acc[["comparison", "population", "matches", "estimate", "lo", "hi", "p_better", "reading"]].to_string(index=False))
    bet["roi_ci"] = bet.apply(lambda r: f"{100 * r['roi']:+.1f}% [{100 * r['roi_lo']:+.1f}, {100 * r['roi_hi']:+.1f}] "
                                        f"n={int(r['bets'])}" if r.get("bets") else "", axis=1)
    print(bet.pivot_table(index=["rule", "forecast"], columns="venue", values="roi_ci", aggfunc="first").to_string())
    print(json.dumps({k: out[k] for k in ("z", "parity", "shift_log_odds", "harm_check_fails")}, indent=1, default=str))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--members", action="store_true")
    which.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.members:
        members()
    else:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
