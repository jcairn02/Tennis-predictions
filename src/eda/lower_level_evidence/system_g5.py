"""G5 of the lower-level-evidence system (role C1), the real-date probe for the layer's cross-player changes: the
translation by the opponent's strength and the opponents' re-referenced norms.

The design is match_timing/probe.py's: on a slice of history (every level, 2023-2024, history inside the slice), for each
cut day D (probe.py's: the second Wednesday of US Open 2023, Australian Open 2024 and Wimbledon 2024, and Cincinnati 2024's
third day), every match that surely started after D (earliest possible start es > D) has its result reversed and the
two players' box-score counts exchanged; the strength the layer reads (Stage 1's pre-match Elo, retirements counted, the
reference's constants) is recomputed on the flipped history; points_52w and the 17 one-step forms are rebuilt with the
layer on; and no input of a pool match that surely finished by D (latest possible finish lf <= D) may move (atol 1e-9).

The configs (not arms): DROP (men, w = 0: the norms and forms lose their lower-level rows), REWEIGHT (both tours, w = 0.5,
ITF excluded), TRANSLATE (both tours, A's classes, gamma from A's class table per statistic, delta 0.1 at every level A
allows, w = 0.7, strength_ref 1700: synthetic parameters in SPEC 6.2's schema, written to a scratch folder, because B's
are not frozen yet). The positive control: TRANSLATE with a leaky strength, each player's rating at the END of the slice
for every match (it contains the flipped results): protected inputs must move.

Run inside a built sandbox's code and tables (its src first on sys.path; nothing is written into the sandbox):
    ./python.sh src/eda/lower_level_evidence/system_g5.py --tree C:/Users/zerom/tnr_sys1 [--cuts 2024-07-10,...]
Writes data/studies/lower_level_evidence/system/arms/g5/real_date_probe.json and its configs/params.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "data" / "studies" / "lower_level_evidence" / "system" / "arms" / "g5"
CLASSES = REPO / "data" / "studies" / "lower_level_evidence" / "system" / "classes" / "classes.csv"
PIN = REPO / "data" / "studies" / "lower_level_evidence" / "system" / "arms" / "constants" / "stageB_adj_summary_reference.json"
SLICE = ("2023-01-01", "2024-12-31")
CUTS = ("2023-09-06", "2024-01-24", "2024-07-10", "2024-08-14")
ATOL = 1e-9
STATS = ("spw", "rpw", "tpw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg",
         "brk", "bp_conv", "rpw_first", "rpw_second", "def_ace", "def_df", "def_first_in", "def_bp_faced_pg")
LEVELS = ("TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ")
FAMILIES_OFF = {"points_52w": False, "forms": False, "ios": False, "ios_points_short": False, "ratings_iid": False,
                "elo": False}


def log(msg: str) -> None:
    print(f"[g5 {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def synthetic_params(path: Path, seasons=(2023, 2024, 2025)) -> str:
    # 2025: the slice's last events start on 27-30 Dec 2024, which Stage 0 counts as season 2025
    """SPEC 6.2's schema; gamma = A's analysis gamma of each statistic (classes.csv, kind stat), delta 0.1, w 0.7."""
    c = pd.read_csv(CLASSES, keep_default_na=False, dtype=str)
    c = c[c["kind"] == "stat"]
    recs = []
    for y in seasons:
        for t in ("atp", "wta"):
            for s in STATS:
                r = c[(c["name"] == s) & (c["tour"] == t)]
                g = float(r["gamma"].iloc[0]) if len(r) and r["gamma"].iloc[0] not in ("", "nan") else 0.0
                for lv in LEVELS:
                    recs.append({"season_used": y, "tour": t, "stat": s, "level": lv, "gamma": g, "delta": 0.1, "w": 0.7,
                                 "w_lo": 0.6, "w_hi": 0.8, "delta_lo": 0.0, "delta_hi": 0.2, "n_players": 0,
                                 "strength_ref": 1700.0, "prior_mu": 0.0, "prior_k": 0.0,
                                 "fit_through": f"{y - 1}-12-31", "method_version": "G5 synthetic"})
            for lv in LEVELS:
                recs.append({"season_used": y, "tour": t, "stat": "results", "level": lv, "gamma": 0.0, "delta": 0.0,
                             "w": 0.7, "w_lo": 0.6, "w_hi": 0.8, "delta_lo": 0.0, "delta_hi": 0.0, "n_players": 0,
                             "strength_ref": 1700.0, "prior_mu": 0.0, "prior_k": 0.0, "fit_through": f"{y - 1}-12-31",
                             "method_version": "G5 synthetic"})
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(recs).to_parquet(path, index=False)
    return sha(path)


def configs(params: Path, params_sha: str) -> dict:
    base = {"params": None, "params_sha256": None, "classes": None, "prior": "pool", "elo_count": "weighted",
            "pins": {}, "record_dir": None}
    fam = {**FAMILIES_OFF, "points_52w": True, "forms": True}
    return {
        "DROP": {**base, "name": "G5_DROP", "tours": ["atp"], "translate": False, "weight": 0.0, "weight_results": 1.0,
                 "itf_box": "exclude", "families": fam},
        "REWEIGHT": {**base, "name": "G5_REWEIGHT", "tours": ["atp", "wta"], "translate": False, "weight": 0.5,
                     "weight_results": 1.0, "itf_box": "exclude", "families": fam},
        "TRANSLATE": {**base, "name": "G5_TRANSLATE", "tours": ["atp", "wta"], "translate": True, "weight": "fitted",
                      "weight_results": 1.0, "itf_box": "exclude", "families": fam, "params": str(params),
                      "params_sha256": params_sha, "classes": str(CLASSES)},
    }


def flip_rows(rows: pd.DataFrame, later_ids: set) -> pd.DataFrame:
    """probe.flip on the player-match table: for the later matches, the result reversed and every count exchanged
    between the two rows of the match (rows come in A, B pairs)."""
    r = rows.copy()
    sel = r["match_id"].isin(later_ids).to_numpy()
    a = np.flatnonzero(sel & (np.arange(len(r)) % 2 == 0))
    cols = [c for c in r.columns if c.endswith("_n") or c.endswith("_d")] + ["won"]
    for c in cols:
        v = r[c].to_numpy().copy()
        va, vb = v[a].copy(), v[a + 1].copy()
        v[a], v[a + 1] = vb, va
        r[c] = v
    return r


def slice_elo(E, rows: pd.DataFrame, k: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 1's pass (the reference's constants, retirements counted) on the slice: (pre-match ratings per match,
    the end-of-slice ratings per match: the leaky control)."""
    a = rows.iloc[0::2].reset_index(drop=True)
    out, leak = [], []
    for tour in ("atp", "wta"):
        t = a[a["tour"].eq(tour)].reset_index(drop=True)
        m = pd.DataFrame({"tournament_date": t["tournament_date"], "tournament_id": t["tournament_id"],
                          "round_order": t["round_order"], "player_a_id": t["player_id"],
                          "player_b_id": t["opponent_id"], "a_won": t["won"], "surface": t["surface"]})
        h = E.history_arrays(m)
        upd = t["status"].isin(E.UPDATES["ret"]).tolist()
        kk = k[tour]
        o = E.elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, h["n_players"],
                       kk["k0"], kk["offset"], kk["shape"], surface=False)
        out.append(pd.DataFrame({"match_id": t["match_id"].to_numpy(), "elo_a_ret": o[:, 0], "elo_b_ret": o[:, 1]}))
        # the end-of-slice rating of each player: the last pre-match rating plus nothing (a leak by construction is
        # enough: the latest rating reflects every result, the flipped ones included)
        last = {}
        for i in range(len(t)):
            last[h["a"][i]] = o[i, 0]
            last[h["b"][i]] = o[i, 1]
        leak.append(pd.DataFrame({"match_id": t["match_id"].to_numpy(),
                                  "elo_a_ret": [last[x] for x in h["a"]], "elo_b_ret": [last[x] for x in h["b"]]}))
    return pd.concat(out, ignore_index=True), pd.concat(leak, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--cuts", default=",".join(CUTS))
    ap.add_argument("--only", default=None, help="comma list of configs")
    a = ap.parse_args()
    tree = Path(a.tree)
    sys.path.insert(0, str(tree))
    for k in [k for k in sys.modules if k == "src" or k.startswith("src.")]:
        del sys.modules[k]
    from src.eda.lower_level_evidence import level_layer as L
    from src.eda.match_timing import common as MT
    from src.eda.predictability_diagnostic import stage1_baselines as E
    from src.eda.predictability_diagnostic import stage4_features as F4
    from src.eda.ufc_ideas import stageB_adjperf as AP
    from src.eda.ufc_ideas import stageB_common as B
    assert Path(L.__file__).resolve().is_relative_to(tree.resolve()), L.__file__
    OUT.mkdir(parents=True, exist_ok=True)
    params = OUT / "synthetic_params.parquet"
    psha = synthetic_params(params)
    cfgs = configs(params, psha)
    if a.only:
        cfgs = {k: v for k, v in cfgs.items() if k in a.only.split(",")}
    k1 = {c["tour"]: c for c in json.loads((tree / "data/studies/predictability_diagnostic/"
                                                    "stage1_baselines_summary.json").read_text())["chosen"]
          if c["rule"] == "ret"}
    t0 = time.time()
    rows_full, typical = F4.load_rows()
    xd_full = F4.stat_xd(rows_full)
    pbp = F4.pbp_history(rows_full)
    ctx4, _ = F4.constants(rows_full, xd_full, typical, pbp)
    log(f"rows and Stage 4 constants: {time.time() - t0:.0f} s")
    chosen, typ, madpop = AP.load_frozen(Path(json.loads(PIN.read_text())["source"]))
    means = B.surface_means()
    sl = rows_full["tournament_date"].between(pd.Timestamp(SLICE[0]), pd.Timestamp(SLICE[1])).to_numpy()
    base_rows = F4.prepare(rows_full[sl].reset_index(drop=True).drop(columns=["day", "pcode"]))
    del rows_full, xd_full
    timing = pd.read_parquet(tree / "data/studies/match_timing/timing.parquet", columns=["match_id", "es", "lf"])
    timing = timing.set_index("match_id")
    pool = F4.pool_mask(base_rows)
    A = np.flatnonzero(pool) * 2
    pool_ids = base_rows["match_id"].to_numpy()[A]
    lf_pool = timing["lf"].reindex(pool_ids).to_numpy(float)
    m_ids = base_rows["match_id"].to_numpy()[0::2]
    es_m = timing["es"].reindex(m_ids).to_numpy(float)
    work = OUT / "work"
    work.mkdir(exist_ok=True)

    def build(rows: pd.DataFrame, strength: pd.DataFrame, cfg: dict, tag: str) -> pd.DataFrame:
        sp = work / f"strength_{tag}.parquet"
        strength.to_parquet(sp, index=False)
        c = dict(cfg)
        c["strength"] = {"path": str(sp), "sha256": sha(sp)}
        cp = work / f"config_{tag}.json"
        cp.write_text(json.dumps(c), encoding="utf-8")
        os.environ["LLE_LAYER"] = str(cp)
        for cache in (L._CFG, L._TABLES, L._BOX):
            cache.clear()
        xd = F4.stat_xd(rows)
        ctx = dict(ctx4)
        ctx["adjusted_x"] = F4.adjusted_x(rows, xd, ctx4)
        S = {"hist": F4.history_sums(rows, xd, ctx), "bo5": F4.best_of_five(rows, "scheduled"),
             "rule": F4.deciding_rules(rows), "format": F4.scheduled_format(rows)["format"].to_numpy()}
        Ai = np.flatnonzero(F4.pool_mask(rows)) * 2
        out = pd.DataFrame({"match_id": rows["match_id"].to_numpy()[Ai]})
        out["points_52w"] = F4.matchup(rows, S, ctx, "mu_points", "52 weeks", Ai, Ai + 1)
        actx = AP.Ctx(rows, means, typ=typ, madpop=madpop)
        feats = AP.build(actx, chosen, stats=tuple(dict.fromkeys(s for s, _ in L.FORM_SPECS)))["features"]
        for s, ch in L.FORM_SPECS:
            out[L.input_name(s, ch)] = np.asarray(feats[f"{ch}_{s}|decayed"], float)
        os.environ.pop("LLE_LAYER", None)
        return out

    res = {"what": "G5 real-date probe of the layer's cross-player changes (probe.py's design)", "slice": SLICE,
           "cuts": a.cuts.split(","), "atol": ATOL, "params": str(params), "params_sha256": psha, "configs": {},
           "control": {}, "tree": str(tree)}
    prev = OUT / "real_date_probe.json"
    if prev.exists() and a.only:                             # a partial rerun keeps the other configs' results
        old = json.loads(prev.read_text(encoding="utf-8"))
        res["configs"] = {k: v for k, v in old.get("configs", {}).items() if k not in cfgs}
        res["control"] = old.get("control", {})
    elo_base, elo_leak_base = slice_elo(E, base_rows, k1)
    flips = {}
    for cut in res["cuts"]:
        D = float(MT.to_day([cut])[0])
        later = set(m_ids[es_m > D])
        fr = flip_rows(base_rows, later)
        e_f, e_leak_f = slice_elo(E, fr, k1)
        flips[cut] = (fr, e_f, e_leak_f, lf_pool <= D, len(later))
    log(f"flipped histories ready: {time.time() - t0:.0f} s")
    cols = ["points_52w"] + [L.input_name(s, ch) for s, ch in L.FORM_SPECS]
    for name, cfg in cfgs.items():
        base = build(base_rows, elo_base, cfg, f"{name}_base")
        rec = {"cuts": []}
        for cut, (fr, e_f, _, prot, n_later) in flips.items():
            got = build(fr, e_f, cfg, f"{name}_{cut}")
            x, y = base[cols].to_numpy(float), got[cols].to_numpy(float)
            moved = ~np.isclose(x, y, rtol=0, atol=ATOL, equal_nan=True)
            rec["cuts"].append({"cut": cut, "later_matches_flipped": n_later, "protected_pool_matches": int(prot.sum()),
                                "protected_moved": int(moved[prot].any(axis=1).sum()),
                                "protected_moved_by_input": {c: int(moved[prot, j].sum()) for j, c in enumerate(cols)
                                                             if moved[prot, j].any()},
                                "unprotected_moved": int(moved[~prot].any(axis=1).sum())})
            log(f"{name} cut {cut}: protected moved {rec['cuts'][-1]['protected_moved']} of {int(prot.sum())}; later "
                f"moved {rec['cuts'][-1]['unprotected_moved']}")
        rec["pass"] = all(c["protected_moved"] == 0 for c in rec["cuts"])
        res["configs"][name] = rec
        (OUT / "real_date_probe.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    if "TRANSLATE" in cfgs:
        cfg = cfgs["TRANSLATE"]
        base = build(base_rows, elo_leak_base, cfg, "CONTROL_base")
        cut = res["cuts"][-1]
        fr, _, e_leak_f, prot, n_later = flips[cut]
        got = build(fr, e_leak_f, cfg, "CONTROL_flip")
        x, y = base[cols].to_numpy(float), got[cols].to_numpy(float)
        moved = ~np.isclose(x, y, rtol=0, atol=ATOL, equal_nan=True)
        res["control"] = {"what": "TRANSLATE with each player's end-of-slice rating (a leak by construction): protected "
                                  "inputs must move", "cut": cut, "protected_moved": int(moved[prot].any(axis=1).sum()),
                          "caught": bool(moved[prot].any())}
        log(f"control: protected moved {res['control']['protected_moved']}")
    res["pass"] = bool(all(v["pass"] for v in res["configs"].values()) and res["control"].get("caught", True))
    res["seconds"] = round(time.time() - t0, 1)
    (OUT / "real_date_probe.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    log(f"pass {res['pass']}; written {OUT / 'real_date_probe.json'}")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
