"""How far one missing box score moves the forecast: a past day replayed through the daily engine, then replayed again
with chosen box scores removed (docs/studies/box_score_gate_review/).

The engine's own steps (src/eda/daily_prediction/dp.py, its CLI), in this study's own work tree and run folders, with
the active instance (src/pipeline/train.dp_env). One work tree serves every scenario: init, worktree, matchups, prices
and tables once; the tree's Stage 0 is then kept, and each scenario restores it, removes its box scores the way Stage 0
drops a box score (repair_data.repair_tables: the nine counts and their rates blank, has_box False), resolves the level
layer on it again (as the tables step does), and runs states and fit in its own run folder (a copy of the base folder as
it stood after the tables step); `finish` then sets each scenario's Stage 0 again and runs the patterns step and the
predict step, the forecast the bet sheet shows. The states step resumes each feature family from the checkpoint and
recomputes the parts whose history changed, so every input sees the removal; the run's states.json says which parts
were recomputed.

The removals, chosen per live match by the gate's own rule (same event and earlier round, or a latest possible finish
in the 14 days before the match's day), among earlier matches that have a box score:
    same_event     the most recent earlier round at the event, of side A's player (side B's if A has none)
    other_event    the most recent match at another event in the window, of side A's player (side B's if none); a live
                   match with none removes nothing and serves as a control for the spill-over (IOS is solved jointly)
    all_window     every earlier match in the window, both players (the worst case for that match)
Each removal also changes the history of the other player of the removed match, as a real gap would.

Run: ./python.sh src/eda/box_score_gate_review/replay_gaps.py setup|run|finish|compare|cleanup
     [--week 2026-07-13 --round R16 --seeds 0-15]
Outputs in data/studies/box_score_gate_review/replay/: the run folders, removals.csv, layer_resolves.jsonl, compare.csv,
compare.json.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "box_score_gate_review" / "replay"
DP = ROOT / "src" / "eda" / "daily_prediction" / "dp.py"
TREE = Path("C:/Users/zerom/tnr_gate_review")              # this study's own work tree
SCENARIOS = ("base", "same_event", "other_event", "all_window", "same_event_b")
# same_event_b, an extension added after the interim reading of same_event (process log, 22:41-22:45): the most recent
# earlier round at the event of side B's player (none when B has none), for a second single-gap reading per match.
# Its removals are in removals_ext.csv (choose_ext), so removals.csv stays as the four pre-registered scenarios read it.
PD = Path("data") / "studies" / "predictability_diagnostic"
MT = Path("data") / "studies" / "match_timing"


def env() -> dict:
    """The active instance and its build tree (the notebook's dp_env), this study's work tree, and no stray DP_*,
    LLE_* or MODEL_REBUILD* variable from the caller (as src/pipeline/runner scrubs them)."""
    from src.pipeline import train as T
    e = {k: v for k, v in os.environ.items() if not k.startswith(("DP_", "LLE_", "MODEL_REBUILD"))}
    e.update(T.dp_env())
    e.update({"DP_WORK_TREE": str(TREE), "PYTHONIOENCODING": "utf-8"})
    return e


def dp(step: str, run: Path, *extra: str) -> None:
    py = Path(os.environ.get("TENNIS_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis/python.exe"))
    cmd = [str(py), str(DP), step, "--run", str(run), *extra]
    print(">>>", " ".join(cmd[1:]), flush=True)
    done = subprocess.run(cmd, cwd=ROOT, env=env(), text=True, encoding="utf-8", errors="replace",
                          stdout=sys.stdout, stderr=subprocess.STDOUT)
    if done.returncode:
        raise SystemExit(f"{step} failed for {run} (exit {done.returncode})")


def setup(week: str, rnd: str, seeds: str) -> None:
    base = OUT / "base"
    if base.exists():
        raise SystemExit(f"{base} exists")
    OUT.mkdir(parents=True, exist_ok=True)
    dp("init", base, "--replay-week", week, "--replay-round", rnd, "--seeds", seeds)
    for step in ("worktree", "matchups", "prices", "tables"):
        dp(step, base)
    keep = OUT / "_stage0_after_tables"
    keep.mkdir(exist_ok=True)
    for f in ("stage0_matches.parquet", "stage0_match_players.parquet"):
        shutil.copy2(TREE / PD / f, keep / f)
    for s in SCENARIOS[1:]:
        shutil.copytree(base, OUT / s)                 # each scenario starts from the base folder after the tables step
    choose()


def retry_tables(seeds: str) -> None:
    """The tables step again, after it failed at `additions` ("the merge made duplicate ... timeline rows").
    Since the shared rebuild of 13 Oct 21:13-21:16, the shared timeline (copied into every work tree) holds rows for
    matches of today's Tennis My Life that a replay's frozen dump lacks; the lower-level feed adds 43 of them, and their
    timeline rows collide. The tree's timeline is trimmed to the matches of the tree's own Stage 0 (the frozen build the
    failed attempt left), the state the 20:51 replay ran in; the replay then holds the instance's timeline after the
    steps (dp_tables.hold_timeline), so the trimmed copy feeds only the steps between. The failed attempt's scratch
    folder is kept as `run_failed_1`, not deleted."""
    base = OUT / "base"
    ids = set(pd.read_parquet(TREE / PD / "stage0_matches.parquet", columns=["match_id"])["match_id"].astype(str))
    t = pd.read_parquet(TREE / MT / "timing.parquet")
    shutil.copy2(TREE / MT / "timing.parquet", OUT / "_tree_timing_before_trim.parquet")
    keep = t["match_id"].astype(str).isin(ids)
    t[keep].to_parquet(TREE / MT / "timing.parquet", index=False, compression="zstd")
    print(f"tree timeline trimmed: {len(t)} -> {int(keep.sum())} rows ({len(ids)} Stage 0 matches)")
    (TREE / "run").rename(TREE / "run_failed_1")
    dp("tables", base)
    keep_dir = OUT / "_stage0_after_tables"
    keep_dir.mkdir(exist_ok=True)
    for f in ("stage0_matches.parquet", "stage0_match_players.parquet"):
        shutil.copy2(TREE / PD / f, keep_dir / f)
    for s in SCENARIOS[1:]:
        if not (OUT / s).exists():
            shutil.copytree(base, OUT / s)
    choose()


def _tables():
    m = pd.read_parquet(OUT / "_stage0_after_tables" / "stage0_matches.parquet")
    p = pd.read_parquet(OUT / "_stage0_after_tables" / "stage0_match_players.parquet")
    t = pd.read_parquet(TREE / MT / "timing.parquet", columns=["match_id", "lf"]).astype({"match_id": str})
    return m.astype({"match_id": str}), p.astype({"match_id": str}), t.set_index("match_id")["lf"]


def choose() -> pd.DataFrame:
    """Per live match and scenario, the earlier matches whose box scores are removed (the gate's window)."""
    from src.eda.prediction_run import common as P
    m, p, lf = _tables()
    meta = pd.read_parquet(OUT / "base" / "live_meta.parquet").astype({"match_id": str})
    live = set(meta["match_id"])
    h = p[["match_id", "player_id", "side"]].merge(m[["match_id", "tournament_id", "round_order", "status", "has_box"]],
                                                   on="match_id")
    h["lf"] = h["match_id"].map(lf)
    rows = []
    for _, lm in meta.iterrows():
        me = m[m["match_id"].eq(lm["match_id"])].iloc[0]
        day = P.day_of(lm["day"])
        sides = p[p["match_id"].eq(lm["match_id"])].set_index("side")["player_id"].to_dict()
        win = {}
        for side in ("A", "B"):
            hh = h[h["player_id"].eq(sides[side]) & ~h["match_id"].isin(live) & h["status"].eq("completed")
                   & h["has_box"].astype(bool)]
            same = hh["tournament_id"].eq(me["tournament_id"]) & (hh["round_order"] < me["round_order"])
            recent = hh["lf"].notna() & (hh["lf"] >= day - P.WINDOW_DAYS) & (hh["lf"] < day)
            win[side] = (hh[same], hh[recent & ~same], hh[same | recent])
        for scen, pick in (("same_event", 0), ("other_event", 1)):
            for side in ("A", "B"):
                cand = win[side][pick]
                if len(cand):
                    g = cand.sort_values(["round_order", "lf"] if pick == 0 else ["lf", "round_order"]).iloc[-1]
                    rows.append({"live_match_id": lm["match_id"], "scenario": scen, "side": side,
                                 "removed_match_id": g["match_id"]})
                    break
        for side in ("A", "B"):
            for mid in win[side][2]["match_id"]:
                rows.append({"live_match_id": lm["match_id"], "scenario": "all_window", "side": side,
                             "removed_match_id": mid})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "removals.csv", index=False)
    print(r.groupby("scenario")["removed_match_id"].nunique().to_string())
    return r


def choose_ext() -> pd.DataFrame:
    """same_event_b's removals: per live match, side B's most recent earlier round at the event (as choose picks A's)."""
    from src.eda.prediction_run import common as P
    m, p, lf = _tables()
    meta = pd.read_parquet(OUT / "base" / "live_meta.parquet").astype({"match_id": str})
    live = set(meta["match_id"])
    h = p[["match_id", "player_id"]].merge(m[["match_id", "tournament_id", "round_order", "status", "has_box"]],
                                           on="match_id")
    h["lf"] = h["match_id"].map(lf)
    rows = []
    for _, lm in meta.iterrows():
        me = m[m["match_id"].eq(lm["match_id"])].iloc[0]
        b = p[p["match_id"].eq(lm["match_id"]) & p["side"].eq("B")]["player_id"].iloc[0]
        hh = h[h["player_id"].eq(b) & ~h["match_id"].isin(live) & h["status"].eq("completed") & h["has_box"].astype(bool)
               & h["tournament_id"].eq(me["tournament_id"]) & (h["round_order"] < me["round_order"])]
        if len(hh):
            g = hh.sort_values(["round_order", "lf"]).iloc[-1]
            rows.append({"live_match_id": lm["match_id"], "scenario": "same_event_b", "side": "B",
                         "removed_match_id": g["match_id"]})
    r = pd.DataFrame(rows)
    # where side A had no earlier round at the event (a bye), same_event removed side B's already: not a new reading
    a = pd.read_csv(OUT / "removals.csv").astype(str)
    a = a[a["scenario"].eq("same_event")].set_index("live_match_id")["removed_match_id"]
    dup = r["removed_match_id"].astype(str).eq(r["live_match_id"].map(a))
    r = r[~dup].reset_index(drop=True)
    r.to_csv(OUT / "removals_ext.csv", index=False)
    print(f"same_event_b: {len(r)} live matches, {r['removed_match_id'].nunique()} removed matches "
          f"({int(dup.sum())} left out: the same removal as same_event's)")
    return r


def removals() -> pd.DataFrame:
    """The pre-registered scenarios' removals and the extension's."""
    r = [pd.read_csv(OUT / "removals.csv")]
    if (OUT / "removals_ext.csv").exists():
        r.append(pd.read_csv(OUT / "removals_ext.csv"))
    return pd.concat(r, ignore_index=True).astype({"live_match_id": str, "removed_match_id": str})


def perturb(scenario: str) -> dict:
    """The tree's Stage 0 restored to its state after the tables step, then the scenario's box scores removed."""
    from src.eda.predictability_diagnostic import common as C
    if scenario == "base":                             # the tables step's own files, byte for byte
        for f in ("stage0_matches.parquet", "stage0_match_players.parquet"):
            shutil.copy2(OUT / "_stage0_after_tables" / f, TREE / PD / f)
        return {"scenario": scenario, "removed": 0}
    m, p, _ = _tables()
    if scenario != "base":
        r = removals()
        ids = set(r.loc[r["scenario"].eq(scenario), "removed_match_id"].astype(str))
        if not ids:
            raise SystemExit(f"no removals for {scenario}")
        raw = [c for c in C.BOX if c in p]
        rates = [f"{s}_{v}" for s in C.RATES if s not in {"tb_won", "sets_won", "games_won"} for v in ("n", "d")
                 if f"{s}_{v}" in p]
        rows = p["match_id"].isin(ids)
        p.loc[rows, raw + rates] = np.nan
        if "has_box" in p:
            p.loc[rows, "has_box"] = False
        mm = m["match_id"].isin(ids)
        m.loc[mm, "has_box"] = False
        m.loc[mm, "box_status"] = "blank"
        if "sv_gms_incl_tb" in m:
            m.loc[mm, "sv_gms_incl_tb"] = pd.NA
        assert int(mm.sum()) == len(ids), "a removed match is not in Stage 0"
    m.to_parquet(TREE / PD / "stage0_matches.parquet", index=False)
    p.to_parquet(TREE / PD / "stage0_match_players.parquet", index=False)
    return {"scenario": scenario, "removed": 0 if scenario == "base" else len(ids)}


def resolve_layer(scenario: str) -> dict:
    """The level layer resolved again on the tree's Stage 0, as the tables step's lle_layer step resolves it (the states
    step refuses a build config resolved on another Stage 0). Its strength is the plain Elo of Stage 0's results, which a
    box score does not enter: the strength file's hash must not change, and is recorded to show it."""
    from src.eda.current_best_model import layer_config as LCF
    folder = TREE / LCF.REL_BUILD
    before = LCF.sha256(folder / "strength_elo.parquet")
    py = Path(os.environ.get("TENNIS_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis/python.exe"))
    cmd = [str(py), str(TREE / "src" / "eda" / "current_best_model" / "layer_config.py"), "--resolve",
           "--official", str(LCF.OFFICIAL)]
    print(">>>", " ".join(cmd[1:]), flush=True)
    done = subprocess.run(cmd, cwd=TREE, env=env(), text=True, encoding="utf-8", errors="replace",
                          stdout=sys.stdout, stderr=subprocess.STDOUT)
    if done.returncode:
        raise SystemExit(f"the layer's resolve failed for {scenario} (exit {done.returncode})")
    after = LCF.sha256(folder / "strength_elo.parquet")
    rec = {"scenario": scenario, "strength_sha256_before": before, "strength_sha256_after": after,
           "strength_unchanged": before == after,
           "stage0_sha256": LCF.sha256(TREE / LCF.STAGE0)}
    with (OUT / "layer_resolves.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    if before != after:
        raise SystemExit(f"the layer's strength changed with {scenario}'s removals: {rec}")
    return rec


def run(seeds: str, only: list[str] | None = None) -> None:
    """states and fit per scenario. The predict step is not run: since 13 Oct 21:06 it needs the combined-pattern
    adjustment's step, which only run_day calls; this study reads the fit's own output instead (fit/season*_seed*.npz:
    each seed's symmetrised forecast at the match's own price), which is stage 1, the TabPFN seed mean."""
    for s in only or SCENARIOS:
        if len(list((OUT / s / "fit").glob("season*_seed*.npz"))) >= 16:
            print(f"{s}: done already")
            continue
        print(json.dumps(perturb(s)))
        print(json.dumps(resolve_layer(s)))
        for step in ("states", "fit"):
            dp(step, OUT / s, *(["--seeds", seeds] if step == "fit" else []))
    perturb("base")                                   # leave the tree as the tables step made it
    resolve_layer("base")


def patterns(scenario: str) -> None:
    """The engine's patterns step (dp_steps.step_patterns, which only run_day calls) for a scenario's run folder, on the
    tree's Stage 0 as the scenario left it: the combined-pattern adjustment (on since 13 Oct 21:09) reads the tree's
    tables and the run's live frame, so a removed box score can move its z too."""
    py = Path(os.environ.get("TENNIS_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis/python.exe"))
    code = ("import sys, json; from pathlib import Path; sys.path.insert(0, r'%s'); import dp_steps as S; "
            "print(json.dumps(S.step_patterns(Path(r'%s')), default=str)[:2000])"
            % (DP.parent, OUT / scenario))
    print(f">>> patterns step for {scenario}", flush=True)
    done = subprocess.run([str(py), "-c", code], cwd=ROOT, env=env(), text=True, encoding="utf-8", errors="replace",
                          stdout=sys.stdout, stderr=subprocess.STDOUT)
    if done.returncode:
        raise SystemExit(f"patterns failed for {scenario} (exit {done.returncode})")


def finish(seeds: str, only: list[str] | None = None) -> None:
    """The forecast the bet sheet would show, per scenario: the tree's Stage 0 set to the scenario's again (the layer
    resolved on it), the patterns step, then the engine's predict step (stage 2 with its speed and pattern terms) on
    the scenario's fit. Run after `run`."""
    for s in only or SCENARIOS:
        if (OUT / s / "predictions.csv").exists():
            print(f"{s}: predicted already")
            continue
        if len(list((OUT / s / "fit").glob("season*_seed*.npz"))) < 16:
            raise SystemExit(f"{s}: no complete fit (run `run` first)")
        print(json.dumps(perturb(s)))
        print(json.dumps(resolve_layer(s)))
        patterns(s)
        dp("predict", OUT / s, "--seeds", seeds)
    perturb("base")
    resolve_layer("base")


def final(scenario: str) -> pd.DataFrame | None:
    """The predict step's forecasts at the match's own price (predictions.csv), if it ran."""
    f = OUT / scenario / "predictions.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f).astype({"match_id": str}).set_index("match_id")
    return d[["q_a", "q_a_patterns_off", "p_base_a", "pattern_z", "pattern_shift", "spd_L"]]


def stage1(scenario: str) -> pd.DataFrame:
    """Per live match: the 16-seed mean of the symmetrised own-price forecasts (dp_predict's p_base and eta), and the
    seeds' spread."""
    own = {}
    for f in sorted((OUT / scenario / "fit").glob("season*_seed*.npz")):
        with np.load(f, allow_pickle=False) as z:
            for mid, p in zip(z["match_id"].astype(str), z["own"]):
                own.setdefault(mid, []).append(float(p))
    d = pd.DataFrame({"p_base": {m: np.mean(v) for m, v in own.items()},
                      "seeds": {m: len(v) for m, v in own.items()},
                      "seed_sd": {m: np.std(v, ddof=1) for m, v in own.items()}})
    d["eta"] = np.log(d["p_base"] / (1 - d["p_base"]))
    return d


def compare() -> dict:
    """Each scenario against the base, per live match: stage 1's change (the TabPFN seed mean, in percentage points),
    stage 2's (logit q = s_tour * eta + b * spd_L, with spd_L untouched by a box score: s_tour times eta's change; the
    2026 slopes of the active instance's stage 2), and the 57 inputs' changes (the states step's live_frame)."""
    base = stage1("base")
    fin0 = final("base")
    fb = pd.read_parquet(OUT / "base" / "live_frame.parquet").astype({"match_id": str}).set_index("match_id")
    meta = pd.read_parquet(OUT / "base" / "live_meta.parquet").astype({"match_id": str}).set_index("match_id")
    inputs = [c for c in fb.columns if c.startswith("in_")]
    slope = slopes()
    r = removals()
    out, rows = {"slopes": slope}, []
    for s in SCENARIOS[1:]:
        if len(list((OUT / s / "fit").glob("season*_seed*.npz"))) < 16:
            continue
        pr = stage1(s)
        fin1 = final(s)
        fr = pd.read_parquet(OUT / s / "live_frame.parquet").astype({"match_id": str}).set_index("match_id")
        st = json.loads((OUT / s / "states.json").read_text(encoding="utf-8"))
        hit = set(r.loc[r["scenario"].eq(s), "live_match_id"])
        for mid in base.index:
            d_in = (fr.loc[mid, inputs].astype(float) - fb.loc[mid, inputs].astype(float)).abs()
            k = slope.get(str(meta.loc[mid, "tour"]), 1.0)
            p0 = float(base.loc[mid, "p_base"])
            q0 = 1 / (1 + np.exp(-k * base.loc[mid, "eta"]))       # stage 2 without its speed term (unchanged here)
            q1 = 1 / (1 + np.exp(-k * pr.loc[mid, "eta"]))
            row = {"scenario": s, "match_id": mid, "tour": meta.loc[mid, "tour"], "removal": mid in hit,
                   "n_removed": int((r["scenario"].eq(s) & r["live_match_id"].eq(mid)).sum()),
                   "d_stage1_pts": 100 * (float(pr.loc[mid, "p_base"]) - p0), "d_q_pts": 100 * (q1 - q0),
                   "seed_sd_pts": 100 * float(base.loc[mid, "seed_sd"]),
                   "inputs_changed": int((d_in > 1e-12).sum()), "max_input_change": float(d_in.max()),
                   "p_base": p0}
            if fin0 is not None and fin1 is not None:           # the predict step's own forecast (speed, patterns)
                row.update({"q_final": float(fin0.loc[mid, "q_a"]),
                            "d_q_final_pts": 100 * (float(fin1.loc[mid, "q_a"]) - float(fin0.loc[mid, "q_a"])),
                            "d_q_off_pts": 100 * (float(fin1.loc[mid, "q_a_patterns_off"])
                                                  - float(fin0.loc[mid, "q_a_patterns_off"])),
                            "d_pattern_z": float(fin1.loc[mid, "pattern_z"]) - float(fin0.loc[mid, "pattern_z"])
                            if pd.notna(fin0.loc[mid, "pattern_z"]) and pd.notna(fin1.loc[mid, "pattern_z"])
                            else np.nan,
                            "d_stage1_check_pts": 100 * (float(fin1.loc[mid, "p_base_a"])
                                                         - float(fin0.loc[mid, "p_base_a"]))})
            rows.append(row)
        out[s] = {"parts": st.get("parts_summary")}
    c = pd.DataFrame(rows)
    c.to_csv(OUT / "compare.csv", index=False)
    for s, g in c.groupby("scenario", sort=False):
        hit, ctl = g[g["removal"]], g[~g["removal"]]
        col = "d_q_final_pts" if "d_q_final_pts" in g and g["d_q_final_pts"].notna().all() else "d_q_pts"
        out[s]["reading"] = col
        a = hit[col].abs()
        out[s].update({"matches_with_removal": int(len(hit)), "controls": int(len(ctl)),
                       "abs_dq_pts_median": float(a.median()) if len(hit) else None,
                       "abs_dq_pts_mean": float(a.mean()) if len(hit) else None,
                       "abs_dq_pts_p90": float(a.quantile(0.9)) if len(hit) else None,
                       "abs_dq_pts_max": float(a.max()) if len(hit) else None,
                       "share_over_1pt": float((a > 1).mean()) if len(hit) else None,
                       "mean_dq_pts_signed": float(hit[col].mean()) if len(hit) else None,
                       "control_abs_dq_pts_max": float(ctl[col].abs().max()) if len(ctl) else None,
                       "seed_sd_pts_median": float(g["seed_sd_pts"].median())})
    (OUT / "compare.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(c.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(json.dumps(out, indent=1, default=str))
    return out


def slopes() -> dict:
    """Stage 2's 2026 tour slopes for the active instance, from the newest live run's provenance that names it."""
    from src.pipeline import train as T
    inst = T.dp_env()["DP_INSTANCE"]
    runs = sorted((ROOT / "data" / "studies" / "daily_prediction" / "runs").glob("live_*"), reverse=True)
    for run in runs:
        prov = run / "provenance.json"
        if not prov.exists():
            continue
        js = json.loads(prov.read_text(encoding="utf-8"))
        coef = ((js.get("stage2") or {}).get("coefficients") or {}).get("2026") or {}
        if inst in str((coef.get("keys") or {}).get("instance", "")):
            return {"atp": float(coef["s_atp"]), "wta": float(coef["s_wta"]), "from": run.name}
    return {"atp": 0.90, "wta": 0.92, "from": "the 11 Oct run's (template_2026-10-10): no run of this instance"}


def cleanup() -> None:
    dp_py = Path(os.environ.get("TENNIS_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis/python.exe"))
    subprocess.run([str(dp_py), str(DP), "cleanup", "--work-tree", str(TREE)], cwd=ROOT, env=env(), check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("setup", "retry_tables", "choose", "choose_ext", "run", "finish", "compare",
                                    "cleanup"))
    ap.add_argument("--week", default="2026-07-13")
    ap.add_argument("--round", default="R16")
    ap.add_argument("--seeds", default="0-15")
    ap.add_argument("--only", default=None, help="run, finish: comma-separated scenarios")
    a = ap.parse_args()
    if a.cmd == "setup":
        setup(a.week, a.round, a.seeds)
    elif a.cmd == "retry_tables":
        retry_tables(a.seeds)
    elif a.cmd == "choose":
        choose()
    elif a.cmd == "choose_ext":
        choose_ext()
    elif a.cmd == "run":
        run(a.seeds, a.only.split(",") if a.only else None)
    elif a.cmd == "finish":
        finish(a.seeds, a.only.split(",") if a.only else None)
    elif a.cmd == "compare":
        compare()
    else:
        cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
