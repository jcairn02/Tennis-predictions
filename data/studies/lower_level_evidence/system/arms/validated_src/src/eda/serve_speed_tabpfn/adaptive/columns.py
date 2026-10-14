"""Serve-speed TabPFN study, adaptive memory (agent 2, the modeller): the two speed columns and the per-match mode.

Plan (fixed by the lead, 8 Oct 2026): data/studies/serve_speed_tabpfn/adaptive/plan.md. Reuses features.py, panel.py
and latency/features_latency.py by import (never edits them). Values only: no match result, outcome or price is read.

Per scenario S (A instant; B today's sources; D daily tour collector; E live Slam feeds), from the rows released by
each target's es under S (the latency variants' rule: history and as-of edition offsets alike; A is the build as run):
    spd_T_<S>   the 14-day filter (the study's constants), clip(df / s_f, -4, 4), s_f = 2.2240 km/h (the study's)
    spd_L_<S>   the 28-day filter (latency B-M1: the same constants, half-life 28 d), clip(df / 1.9496, -4, 4)
                (B-M1's own SD), men; both columns are 0 for women
    late_a/b_<S> a side is late at t = es when one of his own earlier matches (earlier event, or an earlier round of
                the same event) has a usable panel speed (use), finished at least a day before t (lf + 1 < t), lies in
                the last 14 days (obs >= t - 14) and is not in hand at t (release_S > t)
    mode_<S>    'T' when neither side is late, else 'L'; women are always 'T' (their columns are 0) and not flagged
Exact reproductions: spd_T_A == features/speed.parquet's spd_f; spd_L_B == latency/variants.parquet's spd_B_M1.

late_flags_live(frame_rows, speeds_in_hand, watermarks, now): the same rule live, with the sources' publication
watermarks instead of release days (the engineer's pending()).

Run: ./python.sh src/eda/serve_speed_tabpfn/adaptive/columns.py [--no-probes]
Writes data/studies/serve_speed_tabpfn/adaptive/columns.parquet and columns_meta.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import features_latency as FL  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "adaptive"
COLUMNS = OUT / "columns.parquet"
META = OUT / "columns_meta.json"
SCENARIOS = ("A", "B", "D", "E")
HL_T, HL_L = 14.0, 28.0
LATE_WINDOW = 14
# the two standardisers, read from the earlier builds (exact floats, so that the reproductions are exact)
S_F = float(json.loads(F.META.read_text(encoding="utf-8"))["s_f"])
SD_L = float(json.loads(FL.META.read_text(encoding="utf-8"))["standardisation_sd_km_h"]["B_M1"])
assert abs(S_F - 2.224) < 5e-4 and abs(SD_L - 1.9496) < 5e-4
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------ release days
def release_table(p: pd.DataFrame) -> pd.DataFrame:
    """Release day per panel row (aligned with p) for each scenario present in latency/availability.parquet."""
    have = _avail_columns()
    want = [f"release_{s}" for s in SCENARIOS if f"release_{s}" in have]
    a = pd.read_parquet(FL.AVAIL, columns=["match_id", "side", "lf"] + want)
    m = p[["match_id", "side"]].astype(str).merge(a.astype({"match_id": str, "side": str}), on=["match_id", "side"],
                                                  how="left", validate="one_to_one")
    assert (m["lf"].to_numpy(np.int64) == p["lf"].to_numpy(np.int64)).all()
    r = pd.DataFrame(index=p.index)
    for c in want:
        assert m[c].notna().all(), c
        r[c.replace("release_", "")] = m[c].to_numpy(np.int64)
    assert (r["A"].to_numpy() == p["lf"].to_numpy(np.int64) + 1).all()
    return r


def _avail_columns() -> list[str]:
    import pyarrow.parquet as pq
    return pq.ParquetFile(FL.AVAIL).schema.names


# ------------------------------------------------------------------------------------------------ the late flag
def late_flags(p: pd.DataFrame, t: pd.DataFrame, rel: np.ndarray, window: int = LATE_WINDOW) -> np.ndarray:
    """Backtest form. For each target side (tour, player_id, tdate, tournament_id, round_order, es): late when one of
    the player's own earlier panel rows (p holds the usable rows; earlier = an earlier tdate, or the same tournament
    at an earlier round) has lf + 1 < es, obs >= es - window and rel > es."""
    n = len(t)
    out = np.zeros(n, bool)
    if not len(p) or not n:
        return out
    tid_codes, _ = pd.factorize(pd.concat([p["tournament_id"].astype(str), t["tournament_id"].astype(str)]))
    p_tid, t_tid = tid_codes[:len(p)], tid_codes[len(p):]
    p_td, p_ro = p["tdate"].to_numpy(float), p["round_order"].to_numpy(float)
    p_lf, p_ob, rel = p["lf"].to_numpy(float), p["obs"].to_numpy(float), np.asarray(rel, float)
    t_td, t_ro, t_es = t["tdate"].to_numpy(float), t["round_order"].to_numpy(float), t["es"].to_numpy(float)
    groups = p.groupby("player_id", sort=False).indices
    valid = t["player_id"].notna().to_numpy() & np.isfinite(t_es) & np.isfinite(t_td)
    tg = pd.Series(np.arange(n))[valid].groupby(t["player_id"].to_numpy()[valid]).indices
    for pid, loc in tg.items():
        ti = np.arange(n)[valid][loc]
        r = groups.get(pid)
        if r is None:
            continue
        earlier = (p_td[r][None, :] < t_td[ti, None]) | ((p_tid[r][None, :] == t_tid[ti, None])
                                                          & (p_ro[r][None, :] < t_ro[ti, None]))
        es = t_es[ti, None]
        late = earlier & (p_lf[r][None, :] + 1.0 < es) & (p_ob[r][None, :] >= es - window) & (rel[r][None, :] > es)
        out[ti] = late.any(1)
    return out


# ------------------------------------------------------------------------------------------------ the columns
def scenario_sides(p: pd.DataFrame, tm: pd.DataFrame, name: str, rel: np.ndarray | None,
                   box_rel: np.ndarray) -> dict:
    """The men's side values of one scenario: the 14-day and 28-day filters on the released rows (A as built)."""
    S = FL.Scenario(name, p, None if name == "A" else rel, box_rel)
    hist = FL.histories_rel(p, tm, None if name == "A" else rel)
    sT = FL.side_values_v(S, tm, dict(FL.MEN, hl=HL_T), hist=hist)
    sL = FL.side_values_v(S, tm, dict(FL.MEN, hl=HL_L), hist=hist)
    return {"T": sT, "L": sL, "S": S}


def match_columns(keys: pd.DataFrame, tm: pd.DataFrame, sides: dict, late: np.ndarray, name: str) -> pd.DataFrame:
    """One row per frame match: spd_T_<S>, spd_L_<S>, late_a_<S>, late_b_<S>, mode_<S> (women 0 / not late / T)."""
    a = tm["side"].eq("A").to_numpy()
    assert (tm.loc[a, "match_id"].to_numpy() == tm.loc[~a, "match_id"].to_numpy()).all()
    mid = tm.loc[a, "match_id"].to_numpy()
    dT = sides["T"].loc[a, "f_hat"].to_numpy() - sides["T"].loc[~a, "f_hat"].to_numpy()
    dL = sides["L"].loc[a, "f_hat"].to_numpy() - sides["L"].loc[~a, "f_hat"].to_numpy()
    men = pd.DataFrame({f"spd_T_{name}": np.clip(dT / S_F, -F.CLIP, F.CLIP),
                        f"spd_L_{name}": np.clip(dL / SD_L, -F.CLIP, F.CLIP),
                        f"late_a_{name}": late[a], f"late_b_{name}": late[~a]}, index=mid)
    out = keys[["match_id"]].join(men, on="match_id")
    wom = keys["tour"].eq("wta").to_numpy()
    out.loc[wom, [f"spd_T_{name}", f"spd_L_{name}"]] = 0.0
    out.loc[wom, [f"late_a_{name}", f"late_b_{name}"]] = False
    out[f"late_a_{name}"] = out[f"late_a_{name}"].astype(bool)
    out[f"late_b_{name}"] = out[f"late_b_{name}"].astype(bool)
    out[f"mode_{name}"] = np.where(out[f"late_a_{name}"] | out[f"late_b_{name}"], "L", "T")
    return out.drop(columns="match_id")


def build_scenario(p: pd.DataFrame, keys: pd.DataFrame, tm: pd.DataFrame, rt: pd.DataFrame, name: str) -> dict:
    rel = rt[name].to_numpy(np.int64)
    sides = scenario_sides(p, tm, name, rel, p["lf"].to_numpy(np.int64) + 1)
    late = late_flags(p, tm, rel)
    cols = match_columns(keys, tm, sides, late, name)
    return {"cols": cols, "sides": sides, "late": late}


# ------------------------------------------------------------------------------------------------ Probe B
def probe_b_adaptive(p: pd.DataFrame, keys: pd.DataFrame, tm: pd.DataFrame, rt: pd.DataFrame, name: str,
                     days: list[float], seed: int = 20261011) -> dict:
    """On day D the rows with release_S > D get noise (y) in the filter and the snapshot inputs, and a new release
    day drawn in (D, D + 60] (still pending at D); no column or flag of any men's frame side with es <= D may move.
    Leaky controls: (i) the columns with rows admitted at lf + 1 in history and snapshots, under the same noise;
    (ii) a flag that peeks a week ahead (late when a row's release falls in (es, es + 7]): each must move something."""
    rng = np.random.default_rng(seed)
    rel = rt[name].to_numpy(np.int64)
    base = build_scenario(p, keys, tm, rt, name)
    a = tm["side"].eq("A").to_numpy()
    es_m = tm.loc[a, "es"].to_numpy(float)
    lk_rel = p["lf"].to_numpy(np.int64) + 1
    lk0 = FL.side_values_v(FL.Scenario("leaky", p, lk_rel, lk_rel), tm, dict(FL.MEN, hl=HL_T))
    es_s = tm["es"].to_numpy(float)

    def peek(relv):
        return late_flags_window(p, tm, relv)

    peek0 = peek(rel)
    recs, moved, lk_cols, lk_flag = [], 0, 0, 0
    cols = [f"spd_T_{name}", f"spd_L_{name}", f"late_a_{name}", f"late_b_{name}", f"mode_{name}"]
    for D in days:
        q = p.copy()
        late_rows = rel > D
        q.loc[late_rows, "y"] = rng.uniform(100.0, 250.0, int(late_rows.sum()))
        rq = rt.copy()
        rq.loc[late_rows, name] = (D + rng.integers(1, 61, int(late_rows.sum()))).astype(np.int64)
        got = build_scenario(q, keys, tm, rq, name)
        men_chk = np.flatnonzero(es_m <= D)
        idx_frame = keys.index[keys["match_id"].isin(tm.loc[a, "match_id"].to_numpy()[men_chk])]
        diff = np.zeros(len(idx_frame), bool)
        for c in cols:
            x0, x1 = base["cols"].loc[idx_frame, c].to_numpy(), got["cols"].loc[idx_frame, c].to_numpy()
            diff |= ~(x0 == x1)
        moved += int(diff.sum())
        # leaky control (i): columns from rows admitted at lf + 1, same noise, sides with es in [D - 28, D]
        near = np.flatnonzero((es_s <= D) & (es_s >= D - 28.0))
        l1 = FL.side_values_v(FL.Scenario("leaky", q, lk_rel, lk_rel), tm.iloc[near].reset_index(drop=True),
                              dict(FL.MEN, hl=HL_T))
        lm = ~np.isclose(lk0["f_hat"].to_numpy()[near], l1["f_hat"].to_numpy(), rtol=0.0, atol=1e-12)
        lk_cols += int(lm.sum())
        # leaky control (ii): a flag that peeks a week past es
        pk = peek(rq[name].to_numpy(np.int64))
        pm = (pk != peek0) & (es_s <= D)
        lk_flag += int(pm.sum())
        recs.append({"day": D, "date": str(pd.Timestamp("1970-01-01") + pd.Timedelta(days=D))[:10],
                     "matches_checked": int(len(idx_frame)), "moved": int(diff.sum()),
                     "leaky_columns_moved": int(lm.sum()), "leaky_flag_moved": int(pm.sum())})
        log(f"  probe B {name} {recs[-1]['date']}: checked {len(idx_frame)}, moved {int(diff.sum())}; leaky "
            f"columns {int(lm.sum())}, leaky flag {int(pm.sum())}")
    passed = moved == 0 and lk_cols > 0 and lk_flag > 0
    return {"scenario": name, "days": len(days), "values_checked": cols, "check_set": "men's frame matches with es <= D",
            "moved": moved, "leaky_columns_moved": lk_cols, "leaky_flag_moved": lk_flag, "pass": bool(passed),
            "per_day": recs}


def late_flags_window(p: pd.DataFrame, t: pd.DataFrame, rel: np.ndarray) -> np.ndarray:
    """A deliberately leaky flag for the probe's control: late when a row's release falls in (es, es + 7]."""
    n = len(t)
    out = np.zeros(n, bool)
    tid_codes, _ = pd.factorize(pd.concat([p["tournament_id"].astype(str), t["tournament_id"].astype(str)]))
    p_tid, t_tid = tid_codes[:len(p)], tid_codes[len(p):]
    p_td, p_ro, p_lf, p_ob = (p["tdate"].to_numpy(float), p["round_order"].to_numpy(float), p["lf"].to_numpy(float),
                              p["obs"].to_numpy(float))
    rel = np.asarray(rel, float)
    t_td, t_ro, t_es = t["tdate"].to_numpy(float), t["round_order"].to_numpy(float), t["es"].to_numpy(float)
    groups = p.groupby("player_id", sort=False).indices
    tg = pd.Series(np.arange(n)).groupby(t["player_id"].to_numpy()).indices
    for pid, ti in tg.items():
        r = groups.get(pid)
        if r is None:
            continue
        earlier = (p_td[r][None, :] < t_td[ti, None]) | ((p_tid[r][None, :] == t_tid[ti, None])
                                                          & (p_ro[r][None, :] < t_ro[ti, None]))
        es = t_es[ti, None]
        lk = earlier & (p_lf[r][None, :] + 1.0 < es) & (p_ob[r][None, :] >= es - LATE_WINDOW) \
            & (rel[r][None, :] > es) & (rel[r][None, :] <= es + 7)
        out[ti] = lk.any(1)
    return out


# ------------------------------------------------------------------------------------------------ live
def late_flags_live(frame_rows: pd.DataFrame, speeds_in_hand: pd.DataFrame, watermarks: dict, now) -> pd.Series:
    """The late flag at forecast time `now` (plan section 1, live form): the backtest rule with the sources'
    publication watermarks in place of release days, through the engineer's latency.availability.pending().

    frame_rows      the player-matches known at `now`, one row per (match, player):
                      player_id, match_id, tdate, tournament_id, round_order (own order), and
                      target  True for the sides to forecast (their other columns are not used),
                      lf, obs  the played match's latest possible finish and best-estimate day,
                      source   the speed source covering its event ('' or None when no source covers it, e.g.
                               Barcelona); a key of `watermarks`
    speeds_in_hand  the (match_id, player_id) pairs whose speed is in the panel at `now`
    watermarks      {source: the last match day the source has fully delivered} (day numbers or dates; a missing or
                    NaN watermark = nothing delivered yet), e.g. availability.mantd_watermark(latest commit),
                    daily_watermark(today), slam_feed_watermark(last collected day)
    now             the forecast day (a day number; es in the backtest)

    A target side is late when one of its player's own earlier matches (an earlier event, or an earlier round of the same
    event) is expected to carry a speed and is outstanding (covered, and pending(lf, watermark) is true), is not in
    hand, finished at least a day before now (lf + 1 < now) and lies in the last 14 days (obs >= now - 14).
    Returns a boolean Series on the target rows."""
    from src.eda.serve_speed_tabpfn.latency.availability import pending
    fr = frame_rows.reset_index(drop=True)
    tgt = fr["target"].astype(bool).to_numpy()
    h = fr[~tgt].reset_index(drop=True)
    src = h["source"].fillna("").astype(str)
    covered = src.ne("").to_numpy()
    wm = np.array([float(pd.Timestamp(watermarks[s]).value // 86_400_000_000_000)
                   if (s in watermarks and not isinstance(watermarks[s], (int, float, np.integer, np.floating)))
                   else float(watermarks.get(s, np.nan)) if s in watermarks else np.nan for s in src])
    outstanding = np.asarray(pending(h["lf"].to_numpy(float), wm, covered), bool)
    hand = set(zip(speeds_in_hand["match_id"].astype(str), speeds_in_hand["player_id"].astype(str)))
    in_hand = np.array([(m, p) in hand for m, p in zip(h["match_id"].astype(str), h["player_id"].astype(str))], bool)
    q = h[outstanding & ~in_hand].reset_index(drop=True)
    # an outstanding row is, in backtest terms, released after now
    rel = np.full(len(q), float(now) + 1.0)
    t = fr[tgt].assign(es=float(now)).reset_index(drop=True)
    flags = late_flags(q, t, rel)
    return pd.Series(flags, index=frame_rows.index[tgt], name="late")


# ------------------------------------------------------------------------------------------------ main
def build(probes: bool = True) -> dict:
    log("inputs")
    p = FL.load_panel()
    keys = P.load_frame_keys()
    t = F.side_targets(keys)
    tm = t[t["tour"].eq("atp")].reset_index(drop=True)
    rt = release_table(p)
    scen = [s for s in SCENARIOS if s in rt.columns]
    log(f"scenarios with release days: {scen}")
    out = keys[["match_id"]].copy()
    parts, late_by = {}, {}
    for s in scen:
        r = build_scenario(p, keys, tm, rt, s)
        parts[s] = r
        out = pd.concat([out, r["cols"]], axis=1)
        log(f"  {s}: L share men {float((r['cols'].loc[keys['tour'].eq('atp'), f'mode_{s}'] == 'L').mean()):.3f}")
    res = {"p": p, "keys": keys, "tm": tm, "rt": rt, "scen": scen, "out": out, "parts": parts, "probes": {}}
    if probes and "D" in scen:
        days = FL.probe_days(keys)
        res["probes"]["D"] = probe_b_adaptive(p, keys, tm, rt, "D", days)
    return res


def mode_shares(out: pd.DataFrame, keys: pd.DataFrame, scen: list[str]) -> list[dict]:
    rows = []
    k = keys[["tour", "season"]]
    for s in scen:
        for (tour, season), g in out.join(k).groupby(["tour", "season"]):
            rows.append({"scenario": s, "tour": tour, "season": int(season), "matches": int(len(g)),
                         "mode_L": int((g[f"mode_{s}"] == "L").sum()),
                         "share_L": float((g[f"mode_{s}"] == "L").mean()),
                         "late_a": int(g[f"late_a_{s}"].sum()), "late_b": int(g[f"late_b_{s}"].sum())})
    return rows


def write(res: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    out, keys, scen = res["out"], res["keys"], res["scen"]
    assert len(out) == 63737 and out["match_id"].is_unique
    for s in scen:
        for c in (f"spd_T_{s}", f"spd_L_{s}"):
            assert out[c].notna().all() and (out[c].abs() <= F.CLIP).all()
    out.to_parquet(COLUMNS, index=False)
    men = keys["tour"].eq("atp")
    late_season = keys["season"].between(2024, 2026)
    meta = {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "plan": "data/studies/serve_speed_tabpfn/adaptive/plan.md", "reads_results": False,
        "scenarios": scen,
        "constants": {"men": FL.MEN, "half_life_T": HL_T, "half_life_L": HL_L, "late_window_days": LATE_WINDOW,
                      "grace": "lf + 1 < es (a match that finished the day before es is never late)",
                      "clip": F.CLIP},
        "standardisers_km_h": {"spd_T": S_F, "spd_T_source": "features/speed_meta.json s_f",
                               "spd_L": SD_L, "spd_L_source": "latency/variants_meta.json standardisation_sd_km_h.B_M1"},
        "women": "spd_T = spd_L = 0, never flagged late, mode T",
        "inputs": {"panel_sha256": F.sha256(F.PANEL_FILE), "availability_sha256": F.sha256(FL.AVAIL),
                   "features_parquet_sha256": F.sha256(F.FEATURES), "variants_parquet_sha256": F.sha256(FL.VARIANTS)},
        "code_sha256": {"columns.py": F.sha256(Path(__file__)), "features_latency.py": F.sha256(Path(FL.__file__)),
                        "features.py": F.sha256(Path(F.__file__))},
        "columns_parquet_sha256": F.sha256(COLUMNS),
        "mode_shares": mode_shares(out, keys, scen),
        "mode_L_share_men_2024_26": {s: float((out.loc[men & late_season, f"mode_{s}"] == "L").mean()) for s in scen},
        "values_men_2024_26": {s: {"sd_spd_T": float(out.loc[men & late_season, f"spd_T_{s}"].std()),
                                   "sd_spd_L": float(out.loc[men & late_season, f"spd_L_{s}"].std())} for s in scen},
        "probes": res["probes"],
        "probes_pass": bool(res["probes"]) and all(v["pass"] for v in res["probes"].values()),
    }
    META.write_text(json.dumps(meta, indent=1, default=float) + "\n", encoding="utf-8")
    log(f"wrote {COLUMNS.name} ({len(out)} rows, scenarios {scen}) and {META.name}; probes pass {meta['probes_pass']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-probes", action="store_true")
    a = ap.parse_args()
    write(build(probes=not a.no_probes))


if __name__ == "__main__":
    main()
