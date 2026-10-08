"""Women's own-serve tempo and pressure pace: the pre-registered trait gate.

Pre-registration: data/studies/point_sequence/tempo_prereg.md (frozen by tempo_prereg.sha256; this script stops if
the file's hash differs). Run after trait_build.py:  ./python.sh src/eda/point_sequence/tempo_run.py

Writes tempo_player_matches.parquet, tempo_reliability.csv, tempo_results.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import trait_common as TC  # noqa: E402
from src.eda.point_sequence import trait_reliability as TR  # noqa: E402

PREREG = TC.OUT / "tempo_prereg.md"
HASH = TC.OUT / "tempo_prereg.sha256"
WTA_EVENTS_RAW = ROOT / "data" / "dump" / "points" / "wta" / "events"
MODEL_FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
JUNE_2019 = int(np.datetime64("2019-06-01", "D").astype("int64"))
SHUFFLES = 10
REL_SEED = 20261010
EXCLUDE_NAMES = {"Let", "Challenge", "MedicalTreatment", "PhysioCalled", "PhysioCallCancelled", "ToiletBreak",
                 "Suspension", "PlayResumed", "BallMarkInspection", "Overrule"}
EXCLUDE_STATE_REASONS = {"Correction", "ReWarmupAfterSuspensionStarted", "RestartedAfterSuspension"}
ACE, DF = 1, 2


def umpires(keys: set) -> pd.Series:
    out = []
    for f in sorted(WTA_EVENTS_RAW.glob("20*.parquet")):
        year = f.stem
        t = pq.ParquetFile(f).read(columns=["tournament_id", "match_id", "umpire_id"]).to_pandas()
        t["key"] = t["tournament_id"].astype(str) + "/" + year + "/" + t["match_id"].astype(str)
        t = t[t["key"].isin(keys) & t["umpire_id"].notna() & (t["umpire_id"] != "")]
        out.append(t.groupby("key")["umpire_id"].agg(lambda s: s.value_counts().index[0]))
    return pd.concat(out)


def fe_fit(y: np.ndarray, factors: dict, player: np.ndarray, iters: int = 500, tol: float = 1e-7) -> dict:
    """Least squares with fixed effects by alternating projections. Returns each factor's effects (non-player factors
    centred to weighted mean 0) and the player effects."""
    eff = {k: np.zeros(int(v.max()) + 1) for k, v in factors.items()}
    pe = np.zeros(int(player.max()) + 1)
    cnt = {k: np.bincount(v, minlength=len(eff[k])) for k, v in factors.items()}
    pcnt = np.bincount(player, minlength=len(pe))
    for it in range(iters):
        delta = 0.0
        fit_other = sum(eff[k][v] for k, v in factors.items())
        r = y - fit_other
        new = np.bincount(player, weights=r, minlength=len(pe)) / np.maximum(pcnt, 1)
        delta = max(delta, float(np.max(np.abs(new - pe))))
        pe = new
        for k, v in factors.items():
            r = y - pe[player] - (fit_other - eff[k][v])
            new = np.bincount(v, weights=r, minlength=len(eff[k])) / np.maximum(cnt[k], 1)
            delta = max(delta, float(np.max(np.abs(new - eff[k]))))
            fit_other = fit_other - eff[k][v] + new[v]
            eff[k] = new
        if delta < tol:
            break
    for k, v in factors.items():                        # centre each non-player factor; the player absorbs it
        c = float(np.average(eff[k], weights=cnt[k]))
        eff[k] = eff[k] - c
        pe = pe + c
    return {"effects": eff, "player": pe, "iterations": it + 1, "counts": cnt}


def group_median(values: np.ndarray, group: np.ndarray, n_groups: int) -> np.ndarray:
    s = pd.Series(values).groupby(group).median()
    out = np.full(n_groups, np.nan)
    out[s.index.to_numpy()] = s.to_numpy()
    return out


def stats(adj: np.ndarray, pm: np.ndarray, pressure: np.ndarray, n_pm: int) -> np.ndarray:
    """Per player-match (code pm): X/D of tempo level and of pressure pace. Columns X_T, D_T, X_P, D_P."""
    n = np.bincount(pm, minlength=n_pm).astype(float)
    med = group_median(adj, pm, n_pm)
    okt = n >= 5
    np_ = np.bincount(pm, weights=pressure, minlength=n_pm)
    no = n - np_
    mp = group_median(adj[pressure], pm[pressure], n_pm)
    mo = group_median(adj[~pressure], pm[~pressure], n_pm)
    okp = (np_ >= 2) & (no >= 2)
    w = np.where(okp, np_ * no / np.maximum(np_ + no, 1), 0.0)
    pace = np.where(okp, mp - mo, 0.0)
    return np.column_stack([np.where(okt, n * np.nan_to_num(med), 0.0), np.where(okt, n, 0.0), w * np.nan_to_num(pace), w])


def main() -> int:
    t0 = time.time()
    digest = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    if digest != HASH.read_text(encoding="utf-8").split()[0]:
        raise SystemExit("tempo_prereg.md changed after its hash was recorded: refusing to run")
    info: dict = {"prereg_sha256": digest, "deviations": []}
    pop = pd.read_parquet(TC.OUT / "trait_population.parquet")
    tp = pop[pop["tour"].eq("wta") & pop["source"].eq("wta") & (pop["obs"] >= JUNE_2019) & pop["year"].le(2024)].copy()
    tp = tp.reset_index(drop=True)
    tp["tcode"] = np.arange(len(tp))
    info["matches"] = int(len(tp))
    s = pd.read_parquet(TC.OUT / "sequences.parquet",
                        columns=["match_id", "key", "usable", "seq", "set_no", "game_idx", "pt_no", "is_tb", "server",
                                 "winner", "serve_no", "end", "t_utc"])
    s = s[s["usable"]]
    s["match_id"] = s["match_id"].astype(str)
    s = s[s["match_id"].isin(set(tp["match_id"]))]
    s["tcode"] = s["match_id"].map(pd.Series(tp["tcode"].to_numpy(), index=tp["match_id"].to_numpy()))
    s = s.sort_values(["tcode", "seq"], kind="mergesort").reset_index(drop=True)
    keys = s.groupby("tcode")["key"].first()
    tp["key"] = keys.reindex(tp["tcode"]).to_numpy()
    # interruptions between two points
    ev = pd.read_parquet(TC.OUT / "wta_events.parquet", columns=["key", "name", "reason", "next_point_seq"])
    ex = ev[ev["name"].isin(EXCLUDE_NAMES) | (ev["name"].eq("StateIndicator") & ev["reason"].isin(EXCLUDE_STATE_REASONS))]
    ex_pairs = set(zip(ex["key"], ex["next_point_seq"]))
    ump = umpires(set(tp["key"].dropna()))
    tp["umpire"] = tp["key"].map(ump)
    info["matches_with_umpire"] = int(tp["umpire"].notna().sum())
    # gaps
    tc = s["tcode"].to_numpy()
    same = np.r_[False, (tc[1:] == tc[:-1]) & (s["game_idx"].to_numpy()[1:] == s["game_idx"].to_numpy()[:-1])]
    t = s["t_utc"].to_numpy("float64")
    gap = np.r_[np.nan, np.diff(t)]
    srv = s["server"].to_numpy()
    won = (s["winner"].to_numpy() == srv).astype(np.int64)
    gid = np.cumsum(~same) - 1
    cs = np.cumsum(won) - won
    first = np.flatnonzero(~same)
    s_before = cs - cs[first][gid]
    r_before = (s["pt_no"].to_numpy().astype(np.int64) - 1) - s_before
    deu = (s_before >= 3) & (r_before >= 3)
    state = np.where(deu, 17 + np.sign(s_before - r_before), np.minimum(s_before, 3) * 4 + np.minimum(r_before, 3))
    pressure = ((s_before == 2) & (r_before == 2)) | (deu & (s_before <= r_before)) | ((r_before == 3) & (s_before < 3))
    end = s["end"].to_numpy()
    prev_end = np.r_[0, end[:-1]]
    prev_type = np.where(prev_end == ACE, 1, np.where(prev_end == DF, 2, 0))
    sn = s["serve_no"].to_numpy()
    cur_type = np.where(end == ACE, 0, np.where(end == DF, 1, np.where(sn == 1, 2, np.where(sn == 2, 3, 4))))
    interrupted = np.fromiter(((k, q) in ex_pairs for k, q in zip(s["key"].to_numpy(), s["seq"].to_numpy())), bool, len(s))
    elig = same & ~s["is_tb"].to_numpy().astype(bool) & np.isfinite(gap) & (gap >= 5) & (gap <= 120) & ~interrupted
    info["gaps"] = {"own_serve_within_game": int((same & ~s["is_tb"].to_numpy().astype(bool)).sum()),
                    "interrupted_excluded": int((same & interrupted).sum()), "eligible": int(elig.sum())}
    e = np.flatnonzero(elig)
    side = srv[e].astype(np.int64)
    mc = tc[e]
    player = np.where(side == 1, tp["player_a_id"].to_numpy()[mc], tp["player_b_id"].to_numpy()[mc])
    pcode, puniq = pd.factorize(pd.Series(player))
    ucode, _ = pd.factorize(tp["umpire"].fillna("unknown").to_numpy()[mc])
    eycode, _ = pd.factorize(pd.Series(tp["tournament_id"].to_numpy()[mc]).astype(str) + "|" + pd.Series(tp["year"].to_numpy()[mc]).astype(str))
    y = gap[e]
    fac_primary = {"umpire": ucode, "event_year": eycode, "state": state[e], "prev": prev_type[e], "cur": cur_type[e]}
    fac_spec = {k: v for k, v in fac_primary.items() if k != "cur"}
    pm = mc * 2 + (side - 1)                                    # player-match code
    n_pm = 2 * len(tp)
    worlds, fits = {}, {}
    rng = np.random.default_rng([20261006, 93])
    press = pressure[e]
    perms = []
    order0 = np.argsort(pm, kind="stable")
    pm_sorted = pm[order0]
    for j in range(SHUFFLES):
        r = np.random.default_rng([20261006, 93, j])
        o = np.lexsort((r.random(len(pm)), pm))
        lab = np.empty(len(pm), bool)
        lab[order0] = press[o]                                  # labels shuffled within each player-match
        perms.append(lab)
    assert (pm[o] == pm_sorted).all()
    for label, fac in (("primary", fac_primary), ("spec", fac_spec)):
        fit = fe_fit(y, fac, pcode)
        adj = y - sum(fit["effects"][k][v] for k, v in fac.items())
        fits[label] = {"iterations": fit["iterations"],
                       "effect_sd": {k: float(np.sqrt(np.average((v - np.average(v, weights=fit["counts"][k])) ** 2, weights=fit["counts"][k])))
                                     for k, v in fit["effects"].items()},
                       "cur_type_effects": fit["effects"]["cur"].tolist() if "cur" in fit["effects"] else None,
                       "prev_type_effects": fit["effects"]["prev"].tolist(),
                       "median_raw_gap": float(np.median(y)), "median_adjusted_gap": float(np.median(adj))}
        worlds[(label, "real")] = stats(adj, pm, press, n_pm)
        for j in range(SHUFFLES):
            worlds[(label, f"shuf_{j}")] = stats(adj, pm, perms[j], n_pm)
        TC.log(f"{label}: fitted in {fit['iterations']} iterations")
    # rows frame for the reliability machinery (2 rows per match, side 1 then 2 interleaved)
    rows = pd.DataFrame({"mcode": np.repeat(tp["tcode"].to_numpy(), 2), "side": np.tile([1, 2], len(tp))})
    mcx = rows["mcode"].to_numpy()
    rows["player"] = np.where(rows["side"] == 1, tp["player_a_id"].to_numpy()[mcx], tp["player_b_id"].to_numpy()[mcx])
    for c in ("tour", "year", "obs", "round_order", "source", "strict", "match_id", "bo", "surface"):
        rows[c] = tp[c].to_numpy()[mcx]
    frames = []
    for (label, w), a in worlds.items():
        f = pd.DataFrame(a.astype("float32"), columns=["X_T", "D_T", "X_P", "D_P"])
        f.insert(0, "side", rows["side"].to_numpy().astype("int8"))
        f.insert(0, "tcode", rows["mcode"].to_numpy())
        f.insert(0, "world", f"{label}|{w}")
        frames.append(f)
    pd.concat(frames, ignore_index=True).to_parquet(TC.OUT / "tempo_player_matches.parquet", index=False)
    rel_rows = []
    relr = np.random.default_rng(REL_SEED)
    wnames = ["real"] + [f"shuf_{j}" for j in range(SHUFFLES)]
    tempo_store = {}
    for label in ("primary", "spec"):
        Xw = {w: worlds[(label, w)][:, [0, 2]] for w in wnames}
        Dw = {w: worlds[(label, w)][:, [1, 3]] for w in wnames}
        for pname, hm in (("ge20", 20), ("ge50", 50)):
            res = TR.run_population(pname, "wta", np.ones(len(rows), bool), rows, {"X": Xw, "D": Dw}, wnames, hm, relr)
            rel, boot = res["rel"], res["boot"]
            d = rel[0, 1] - rel[1:, 1].mean()
            bd = boot[:, 0, 1] - boot[:, 1:, 1].mean(axis=1)
            bd = bd[np.isfinite(bd)]
            bt = boot[:, 0, 0]
            bt = bt[np.isfinite(bt)]
            rel_rows.append({"adjustment": label, "population": pname, "players": res["players"],
                             "player_matches": res["player_matches"], "matches_per_player_median": res["matches_per_player_median"],
                             "tempo_r": float(rel[0, 0]), "tempo_r_lo": float(np.percentile(bt, 2.5)),
                             "tempo_r_hi": float(np.percentile(bt, 97.5)),
                             "pace_real_r": float(rel[0, 1]), "pace_null_r": float(rel[1:, 1].mean()), "pace_delta": float(d),
                             "pace_lo": float(np.percentile(bd, 2.5)), "pace_hi": float(np.percentile(bd, 97.5)),
                             "pace_players_used": float(res["n_used"][0, 1])})
            if pname == "ge20":
                tempo_store[label] = res
            TC.log(f"{label} {pname}: {res['players']} players")
    rel = pd.DataFrame(rel_rows)
    rel.to_csv(TC.OUT / "tempo_reliability.csv", index=False)
    # population means of pressure pace
    means = {}
    for label in ("primary", "spec"):
        a = worlds[(label, "real")]
        nulls = [worlds[(label, f"shuf_{j}")] for j in range(SHUFFLES)]
        means[label] = {"pressure_pace_real_s": float(a[:, 2].sum() / a[:, 3].sum()),
                        "pressure_pace_null_s": float(np.mean([b[:, 2].sum() / b[:, 3].sum() for b in nulls])),
                        "tempo_level_mean_s": float(a[:, 0].sum() / a[:, 1].sum())}
    # R^2 of pre-match tempo with the 58 inputs
    r2 = {}
    mf = pd.read_parquet(MODEL_FRAME)
    inputs = [c for c in mf.columns if c.startswith("in_")]
    info["inputs_count"] = len(inputs)
    mf = mf[mf["tour"].eq("wta")]
    tim = pd.read_parquet(TC.TIMING, columns=["match_id", "obs"])
    s0m = pd.read_parquet(TC.S0 / "stage0_matches.parquet", columns=["match_id", "player_a_id", "player_b_id",
                                                                    "tournament_id", "round_order", "year"])
    mf = mf.merge(tim, on="match_id", how="left").merge(s0m, on="match_id", how="left")
    mf = mf[(mf["obs"] >= JUNE_2019) & (mf["year"] <= 2024)].reset_index(drop=True)
    for label in ("primary", "spec"):
        a = worlds[(label, "real")]
        hist = pd.DataFrame({"player": rows["player"].to_numpy(), "obs": rows["obs"].to_numpy(),
                             "tid": tp["tournament_id"].to_numpy()[rows["mcode"].to_numpy()],
                             "ro": rows["round_order"].to_numpy(), "X": a[:, 0], "D": a[:, 1]})
        hist = hist[hist["D"] > 0]
        pre = {}
        for sd in ("a", "b"):
            q = mf[["match_id", f"player_{sd}_id", "obs", "tournament_id", "round_order"]].rename(
                columns={f"player_{sd}_id": "player", "obs": "obs_t", "tournament_id": "tid_t", "round_order": "ro_t"})
            j = q.merge(hist, on="player", how="inner")
            ok = ((j["obs"] < j["obs_t"]) & (j["obs"] >= j["obs_t"] - 364)) | ((j["tid"] == j["tid_t"]) & (j["ro"] < j["ro_t"]) & (j["obs"] <= j["obs_t"]))
            j = j[ok]
            g = j.groupby("match_id").agg(X=("X", "sum"), D=("D", "sum"), k=("X", "size"))
            g = g[g["k"] >= 5]
            pre[sd] = (g["X"] / g["D"]).reindex(mf["match_id"]).to_numpy()
        ta, tb_ = pre["a"], pre["b"]
        ok = np.isfinite(ta) & np.isfinite(tb_)
        Xin = mf.loc[ok, inputs].copy()
        for c in ("in_surface", "in_level", "in_round"):
            Xin = pd.concat([Xin.drop(columns=c), pd.get_dummies(Xin[c].round(6).astype(str), prefix=c, drop_first=True, dtype=float)], axis=1)
        miss = Xin.isna()
        for c in Xin.columns[miss.any()]:
            Xin[c + "_missing"] = miss[c].astype(float)
            Xin[c] = Xin[c].fillna(Xin[c].mean())
        Xin = Xin.loc[:, Xin.std() > 0]
        Z = np.column_stack([np.ones(ok.sum()), Xin.to_numpy("float64")])
        out = {"matches": int(ok.sum()), "of_frame_matches": int(len(mf)), "regressors": int(Z.shape[1] - 1)}
        for tname, yv in (("diff", (ta - tb_)[ok]), ("side_a", ta[ok])):
            beta, *_ = np.linalg.lstsq(Z, yv, rcond=None)
            fit = Z @ beta
            r2_in = 1 - ((yv - fit) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
            from sklearn.model_selection import KFold
            pred = np.empty(len(yv))
            for tr, te in KFold(5, shuffle=True, random_state=7).split(Z):
                b, *_ = np.linalg.lstsq(Z[tr], yv[tr], rcond=None)
                pred[te] = Z[te] @ b
            r2_cv = 1 - ((yv - pred) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
            out[tname] = {"r2_in_sample": float(r2_in), "r2_cv": float(r2_cv)}
        r2[label] = out
    prim = rel[(rel["adjustment"] == "primary") & (rel["population"] == "ge20")].iloc[0]
    spec = rel[(rel["adjustment"] == "spec") & (rel["population"] == "ge20")].iloc[0]
    decision = {}
    for label, row in (("primary", prim), ("spec", spec)):
        decision[label] = {"pressure_pace_pass": bool(row["pace_delta"] >= 0.10 and row["pace_lo"] > 0),
                           "tempo_level_reliability_ge20": float(row["tempo_r"]),
                           "tempo_level_r2_diff_in_sample": r2[label]["diff"]["r2_in_sample"],
                           "tempo_level_new_information": bool(r2[label]["diff"]["r2_in_sample"] < 0.1)}
    info.update({"fits": fits, "reliability": json.loads(rel.to_json(orient="records")), "means": means, "r2": r2,
                 "decision": decision, "seconds": round(time.time() - t0, 1)})
    (TC.OUT / "tempo_results.json").write_text(json.dumps(info, indent=1, default=float) + "\n", encoding="utf-8")
    TC.log("wrote tempo_* outputs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
