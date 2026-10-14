"""Role E (red team), CP1: a leak probe of the layer's cross-player changes with role B's REAL parameters and the FINAL
level_layer.py (C1's G5 used synthetic parameters, constant across seasons, and ran an earlier copy of the layer).

The design is C1's system_g5.py (itself match_timing/probe.py's): a slice of history at every level, for each cut day D
every match that surely started after D (es > D) has its result reversed and the two players' box-score counts
exchanged; the strength the layer reads (Stage 1's pre-match Elo on the slice, the reference's constants) is recomputed
on the flipped history; points_52w and the 17 one-step forms are rebuilt with the layer on; no input of a pool match
that surely finished by D (lf <= D) may move (atol 1e-9).

Differences from C1's run:
  * the parameters are role B's params.parquet, seasons <= 2024 only (the sealed 2025-2026 rows are not read);
  * the slice ends on 26 Dec 2024, so no match of a 2025-season event (27-29 Dec 2024) is read or flipped;
  * the layer module is the repository's final level_layer.py (sha256 printed), injected in place of the sandbox copy;
    the sandbox (read only) supplies the patched builders and the frozen tables;
  * the config is SYS's family settings for points_52w and the forms (translate, fitted w, A's classes), both tours.
Writes only under data/studies/lower_level_evidence/system/audit/g5_realparams/.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"C:\Users\zerom\Documents\Tennis-predictions")
TREE = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\zerom\tnr_sys2")
OUTD = REPO / "data/studies/lower_level_evidence/system/audit/g5_realparams"
LAYER = REPO / "src/eda/lower_level_evidence/level_layer.py"
PARAMS = REPO / "data/studies/lower_level_evidence/system/relationship/params.parquet"
CLASSES = REPO / "data/studies/lower_level_evidence/system/classes/classes.csv"
PIN = REPO / "data/studies/lower_level_evidence/system/arms/constants/stageB_adj_summary_reference.json"
SLICE = ("2023-01-01", "2024-12-26")
CUTS = ("2023-09-06", "2024-01-24", "2024-07-10", "2024-08-14")
ATOL = 1e-9


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def log(m):
    print(f"[e-g5 {time.strftime('%H:%M:%S')}] {m}", flush=True)


def main() -> int:
    OUTD.mkdir(parents=True, exist_ok=True)
    work = OUTD / "work"
    work.mkdir(exist_ok=True)
    # B's real parameters, dev seasons only
    p = pd.read_parquet(PARAMS)
    p = p[p["season_used"] <= 2024].reset_index(drop=True)
    pp = OUTD / "params_dev_only.parquet"
    p.to_parquet(pp, index=False)
    psha = sha(pp)
    # the tree's builders, the repository's final layer
    sys.path.insert(0, str(TREE))
    for k in [k for k in sys.modules if k == "src" or k.startswith("src.")]:
        del sys.modules[k]
    import src.eda.lower_level_evidence as pkg  # noqa: F401  (the tree's package)
    spec = importlib.util.spec_from_file_location("src.eda.lower_level_evidence.level_layer", LAYER)
    L = importlib.util.module_from_spec(spec)
    sys.modules["src.eda.lower_level_evidence.level_layer"] = L
    spec.loader.exec_module(L)
    sys.modules["src.eda.lower_level_evidence"].level_layer = L
    # the layer puts its own ROOT (the repository) first on sys.path: put the tree back in front, so the builders
    # (namespace packages resolve by sys.path order) come from the tree
    while str(REPO) in sys.path:
        sys.path.remove(str(REPO))
    sys.path.insert(0, str(TREE))
    for k in [k for k in sys.modules if k.startswith("src.eda.predictability_diagnostic") or
              k.startswith("src.eda.ufc_ideas") or k.startswith("src.eda.match_timing")]:
        del sys.modules[k]
    from src.eda.match_timing import common as MT
    from src.eda.predictability_diagnostic import stage1_baselines as E
    from src.eda.predictability_diagnostic import stage4_features as F4
    from src.eda.ufc_ideas import stageB_adjperf as AP
    from src.eda.ufc_ideas import stageB_common as B
    gspec = importlib.util.spec_from_file_location("e_system_g5", REPO / "src/eda/lower_level_evidence/system_g5.py")
    G = importlib.util.module_from_spec(gspec)       # flip_rows, slice_elo (no src import at module level)
    gspec.loader.exec_module(G)
    assert Path(F4.__file__).resolve().is_relative_to(TREE.resolve()), F4.__file__
    assert Path(AP.__file__).resolve().is_relative_to(TREE.resolve()), AP.__file__
    log(f"layer {L.__file__} sha256 {sha(L.__file__)}; builders from {TREE}")
    stage0m = TREE / "data/studies/predictability_diagnostic/stage0_matches.parquet"
    cfg0 = {"name": "E_SYSREAL", "tours": ["atp", "wta"], "params": str(pp), "params_sha256": psha,
            "classes": str(CLASSES), "classes_sha256": sha(CLASSES), "translate": True, "weight": "fitted",
            "weight_results": 1.0, "prior": "pool", "itf_box": "exclude", "elo_count": "weighted", "pins": {},
            "record_dir": None, "params_season_floor": 2013, "missing_params": "error", "stage0_matches": str(stage0m),
            "families": {"points_52w": True, "forms": True, "ios": False, "ios_points_short": False,
                         "ratings_iid": False, "elo": False}}
    k1 = {c["tour"]: c for c in json.loads((TREE / "data/studies/predictability_diagnostic/"
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
    assert (base_rows["year"] <= 2024).all(), "a 2025-season row is in the slice"
    del rows_full, xd_full
    timing = pd.read_parquet(TREE / "data/studies/match_timing/timing.parquet", columns=["match_id", "es", "lf"])
    timing = timing.set_index("match_id")
    pool = F4.pool_mask(base_rows)
    A = np.flatnonzero(pool) * 2
    pool_ids = base_rows["match_id"].to_numpy()[A]
    lf_pool = timing["lf"].reindex(pool_ids).to_numpy(float)
    m_ids = base_rows["match_id"].to_numpy()[0::2]
    es_m = timing["es"].reindex(m_ids).to_numpy(float)

    def build(rows, strength, tag):
        sp = work / f"strength_{tag}.parquet"
        strength.to_parquet(sp, index=False)
        c = dict(cfg0)
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

    res = {"what": "E's real-parameter leak probe (C1's G5 design, B's params <= 2024, final layer)", "slice": SLICE,
           "cuts": list(CUTS), "atol": ATOL, "params": str(pp), "params_sha256": psha, "layer": str(LAYER),
           "layer_sha256": sha(LAYER), "tree": str(TREE), "cuts_result": []}
    elo_base, _ = G.slice_elo(E, base_rows, k1)
    base = build(base_rows, elo_base, "base")
    cols = ["points_52w"] + [L.input_name(s, ch) for s, ch in L.FORM_SPECS]
    # sanity: the layer did translate (compare with the layer off on the same rows)
    os.environ.pop("LLE_LAYER", None)
    for cache in (L._CFG, L._TABLES, L._BOX):
        cache.clear()
    off_cfg = dict(cfg0)
    off_cfg["families"] = {k: False for k in cfg0["families"]}
    sp = work / "strength_off.parquet"
    elo_base.to_parquet(sp, index=False)
    off_cfg["strength"] = {"path": str(sp), "sha256": sha(sp)}
    off_cp = work / "config_off.json"
    off_cp.write_text(json.dumps(off_cfg), encoding="utf-8")
    saved = cfg0["families"]
    cfg0["families"] = off_cfg["families"]
    off = build(base_rows, elo_base, "off")
    cfg0["families"] = saved
    diff = ~np.isclose(base[cols].to_numpy(float), off[cols].to_numpy(float), rtol=0, atol=ATOL, equal_nan=True)
    res["layer_moved_vs_off"] = {c: int(diff[:, j].sum()) for j, c in enumerate(cols)}
    log(f"layer on vs off: pool matches moved per input {res['layer_moved_vs_off']}")
    for cut in CUTS:
        D = float(MT.to_day([cut])[0])
        later = set(m_ids[es_m > D])
        fr = G.flip_rows(base_rows, later)
        e_f, _ = G.slice_elo(E, fr, k1)
        got = build(fr, e_f, f"cut_{cut}")
        prot = lf_pool <= D
        x, y = base[cols].to_numpy(float), got[cols].to_numpy(float)
        moved = ~np.isclose(x, y, rtol=0, atol=ATOL, equal_nan=True)
        rec = {"cut": cut, "later_matches_flipped": len(later), "protected_pool_matches": int(prot.sum()),
               "protected_moved": int(moved[prot].any(axis=1).sum()),
               "protected_moved_by_input": {c: int(moved[prot, j].sum()) for j, c in enumerate(cols)
                                            if moved[prot, j].any()},
               "unprotected_moved": int(moved[~prot].any(axis=1).sum())}
        res["cuts_result"].append(rec)
        log(f"cut {cut}: protected moved {rec['protected_moved']} of {rec['protected_pool_matches']}; later moved "
            f"{rec['unprotected_moved']}")
        (OUTD / "real_params_probe.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    res["pass"] = all(r["protected_moved"] == 0 for r in res["cuts_result"])
    res["seconds"] = round(time.time() - t0, 1)
    (OUTD / "real_params_probe.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    log(f"pass {res['pass']}")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
