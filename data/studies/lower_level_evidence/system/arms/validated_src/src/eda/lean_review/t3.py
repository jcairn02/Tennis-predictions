"""The lean review's T3 (checklist item 8, as amended): the long-memory IOS profile pooled against per surface, on the
Pinnacle-first instance, carrying T2's decision on ios_points_short. It runs only if T2 keeps the profile
(docs/studies/lean_review/README.md, "The test plan").

The pooled profile is the leak-proof refit's 21 IOS inputs: ios_O_<s>|single, ios_D_<s>|single and prod_<s>|single of
data/studies/match_timing/leakproof_features.parquet, as the frozen reference holds it (tables_later/). They are
swapped into the instance's frame in place of the per-surface iosO_<s>, iosD_<s> and prod_<s>. Before 6 Oct 2026
these were the model's profile inputs (item 8: "how the pooled profile was built before 6 Oct (the leak-proof refit's
inputs)"). The table holds every frame match with the frame's sides: its ios_short equals the frame's
ios_points_short exactly, with the same missing pattern (checked by --build).

Arms. S, the per-surface build: T2's A0, or A2 if T2 proposed removing ios_points_short. P, the same inputs with the
pooled profile: P0 or P2. P's fits are made exactly as fits.py makes T2's (two predict calls), seeds 0-3, 2019-2024.

    --build             write P0's and P2's frames and input lists; check that only the 21 profile columns differ
    --run --arm P0|P2   the fits (start through src/eda/bet_timing/run_when_free.sh)
    --score --arm P0|P2 P against its S at (O), the primary, and (C); the pre-declared rule; t3_summary.json

The rule (fixed before T3 ran):
    * switch to pooled unless the per-surface build's B * est > 0.01 at (O), both tours, both stages (tau 0.05);
      est = per surface against pooled, + = per surface better;
    * split by tour only if one tour clears that bar and the other's per-surface reading is worse with
      P(better) <= 0.2;
    * veto (item 8's clause): stay per surface if pooled is worse at (C) by more than 0.1.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as K  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.lean_review import common as L  # noqa: E402
from src.eda.lean_review import fits as FT  # noqa: E402
from src.eda.lean_review import score as SC  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402

POOLED = (ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "tables_later" /
          "data" / "studies" / "match_timing" / "leakproof_features.parquet")
SWAP = {f"in_{q}_{s}": f"{p}_{s}|single" for s in L.STATS for q, p in (("iosO", "ios_O"), ("iosD", "ios_D"),
                                                                        ("prod", "prod"))}
T3 = {"P0": ("A0", []), "P2": ("A2", L.SHORT)}       # pooled arm -> (its per-surface twin, dropped inputs)
TAU, C_BAR, VETO_EST, SPLIT_P = 0.05, 0.01, -0.10, 0.20


def frame_path(arm: str) -> Path:
    return L.arm_dir(arm) / "model_frame.parquet"


def paths(arm: str) -> C.Paths:
    return L.paths(arm).with_(model_frame=frame_path(arm))


def build() -> dict:
    """The pooled frames and input lists. Reads no result: the frame is copied whole, a_won included, unread."""
    f = pd.read_parquet(L.FRAME)
    f["match_id"] = f["match_id"].astype(str)
    t = pd.read_parquet(POOLED, columns=["match_id", "ios_short"] + list(SWAP.values()))
    t["match_id"] = t["match_id"].astype(str)
    if t["match_id"].duplicated().any():
        raise RuntimeError("the pooled table has duplicate match ids")
    t = t.set_index("match_id")
    missing = int((~pd.Index(f["match_id"]).isin(t.index)).sum())
    if missing:
        raise RuntimeError(f"the pooled table lacks {missing} frame matches")
    t = t.reindex(f["match_id"].to_numpy())
    a, b = f["in_ios_points_short"].to_numpy(float), t["ios_short"].to_numpy(float)
    same = np.array_equal(np.isfinite(a), np.isfinite(b)) and np.allclose(a[np.isfinite(a)], b[np.isfinite(b)],
                                                                          rtol=0, atol=1e-12)
    if not same:
        raise RuntimeError("the pooled table's sides or values differ from the frame's (ios_short check)")
    g = f.copy()
    for col, src in SWAP.items():
        g[col] = t[src].to_numpy(float)
    changed = [c for c in g.columns if not g[c].equals(f[c])]
    if sorted(changed) != sorted(SWAP):
        raise RuntimeError(f"columns other than the profile changed: {sorted(set(changed) - set(SWAP))}")
    meta = json.loads(L.INPUTS.read_text(encoding="utf-8"))
    out = {"pooled_table": str(POOLED.relative_to(ROOT)), "pooled_sha256": C.sha256_file(POOLED),
           "instance_frame_sha256": C.sha256_file(L.FRAME), "swapped": SWAP, "arms": {}}
    for arm, (twin, drop) in T3.items():
        L.arm_dir(arm).mkdir(parents=True, exist_ok=True)
        g.to_parquet(frame_path(arm), index=False)
        m = dict(meta)
        m["inputs"] = [dict(d) for d in meta["inputs"] if d["name"] not in drop]
        for d in m["inputs"]:
            if f"in_{d['name']}" in SWAP:
                d["source"] = f"pooled (leak-proof refit's {SWAP['in_' + d['name']]}); lean review T3"
        m["lean_review"] = {"arm": arm, "twin": twin, "dropped": drop, "profile": "pooled"}
        L.inputs_path(arm).write_text(json.dumps(m, indent=1), encoding="utf-8")
        out["arms"][arm] = {"twin": twin, "inputs": len(m["inputs"]), "frame_sha256": C.sha256_file(frame_path(arm)),
                            "corr_with_surface": {c: round(float(np.corrcoef(f[c], g[c])[0, 1]), 4) for c in SWAP}}
    C.write_json(L.OUT / "t3_build.json", out)
    C.log(f"T3 build: pooled frames for {list(T3)}, only the 21 profile columns differ")
    return out


class PooledArm(FT.Arm):
    def __init__(self, arm: str):
        self.arm = arm
        self.P = paths(arm)
        self.cols = A.arm_inputs("model", self.P)
        if len(self.cols) != 58 - len(T3[arm][1]):
            raise RuntimeError(f"{arm}: {len(self.cols)} inputs")
        self.frame = A.load_frame([], self.P, labels=True)
        if not A.check_flip(self.frame, self.cols, self.P):
            raise RuntimeError(f"{arm}: flip is not an involution")
        op = L.opening_prices(self.frame)
        self.p_open = pd.Series(op["p_open"].to_numpy(float), index=op["match_id"].to_numpy())


def run(arm: str) -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    from src.eda.training_window.fits import wait_for_card
    if not (L.OUT / "t3_build.json").exists():
        raise SystemExit("run --build first")
    a = PooledArm(arm)
    frame_sha = C.sha256_file(frame_path(arm))
    L.fits_dir(arm).mkdir(parents=True, exist_ok=True)
    for season in L.SEASONS:
        todo = [k for k in L.SEEDS if not FT.fit_path(arm, season, k).exists()]
        if not todo:
            continue
        X_train, y_train, qs = a.job(season)
        for seed in todo:
            path = FT.fit_path(arm, season, seed)
            free_gb = wait_for_card(patience_s=12 * 3600, processes=False)
            clf = runtime.classifier(**C.CONFIG, random_state=seed)
            torch.cuda.reset_peak_memory_stats()
            t0 = time.monotonic()
            clf.fit(X_train, y_train)
            p_td = clf.predict_proba(qs["td"][0])
            t1 = time.monotonic()
            p_open = clf.predict_proba(qs["open"][0])
            t2 = time.monotonic()
            for p in (p_td, p_open):
                if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(p).all():
                    raise RuntimeError(f"{arm} {path.name}: invalid probabilities")
            meta = {"arm": "model", "lean_review_arm": arm, "dropped": T3[arm][1], "profile": "pooled",
                    "season": season, "seed": seed, "kind": "fit", "frame": "pooled-profile copy of the "
                    "Pinnacle-first instance (lean review T3)", "config": {**C.CONFIG, "random_state": seed},
                    "train_shape": list(X_train.shape), "train_seasons": [C.TRAIN_FROM, season - 1],
                    "query_rows": {n: int(len(q[0])) for n, q in qs.items()}, "columns": list(X_train.columns),
                    "fingerprint": C.fingerprint(X_train, y_train, qs["td"][0]),
                    "fingerprint_open": C.fingerprint(X_train, y_train, qs["open"][0]),
                    "model_frame_sha256": frame_sha, "seconds_fit_td": round(t1 - t0, 1),
                    "seconds_open": round(t2 - t1, 1), "gpu_free_gb_before": round(free_gb, 1),
                    "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                    "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, meta=np.asarray(json.dumps(meta)), p_td=p_td[:, 1], ids_td=qs["td"][1].astype(str),
                     p_open=p_open[:, 1], ids_open=qs["open"][1].astype(str))
            tmp.replace(path)
            C.log(f"{arm} {path.name}: fit+td {t1 - t0:.0f} s, open {t2 - t1:.0f} s, queries {meta['query_rows']}")
            del clf
            torch.cuda.empty_cache()
    return 0


def decide(rows: dict) -> dict:
    """rows: {(yardstick, population): {"estimate", "se", "p_better"}} for per surface against pooled (+ = per
    surface better). The pre-declared rule."""
    def clears(r):
        return TAU ** 2 / (TAU ** 2 + r["se"] ** 2) * r["estimate"] > C_BAR
    both = rows[("O", "both tours")]
    keep = clears(both)
    veto = rows[("C", "both tours")]["estimate"] > -VETO_EST        # pooled worse at (C) by more than 0.1
    men, women = rows[("O", "men")], rows[("O", "women")]
    split = None
    if clears(men) and women["p_better"] <= SPLIT_P:
        split = {"atp": "per surface", "wta": "pooled"}
    elif clears(women) and men["p_better"] <= SPLIT_P:
        split = {"atp": "pooled", "wta": "per surface"}
    if veto:
        proposal = "stay per surface (veto: pooled worse at the close by more than 0.1)"
    elif split:
        proposal = f"split: men {split['atp']}, women {split['wta']}"
    else:
        proposal = "stay per surface" if keep else "switch to pooled"
    return {"B_est_both": TAU ** 2 / (TAU ** 2 + both["se"] ** 2) * both["estimate"], "clears_both": keep,
            "clears_men": clears(men), "clears_women": clears(women), "veto": bool(veto), "split": split,
            "proposal": proposal}


def score(arm: str) -> int:
    twin = T3[arm][0]
    rp = L.OUT / "repro.json"
    if not rp.exists() or not C.read_json(rp).get("passed"):
        raise SystemExit("T2's reproduction check must pass first")
    P0 = L.paths("A0")
    frame = K.inputs_frame(P0)
    y = K.outcomes(P0, SC.THROUGH)
    info = K.scoring_info(frame, frame, y, y, SC.THROUGH)
    fx = F.FrameIndex(frame.reset_index()[["match_id", "season"]])
    op = L.opening_prices(frame.reset_index())
    p_open = pd.Series(op["p_open"].to_numpy(float), index=op["match_id"].astype(str).to_numpy())
    z = R.speed_column("reference")
    ids_O = info.index[np.isfinite(p_open.reindex(info.index).to_numpy())]
    infos = {"C": info, "O": info.loc[ids_O].assign(p_open=p_open.reindex(ids_O).to_numpy())}
    tables = {}
    for a in (twin, arm):
        P = paths(arm) if a == arm else L.paths(a)
        tables[a] = {"C": K.seed_table(P, frame, L.SEASONS).reindex(info.index),
                     "O": SC.open_table(a, fx).reindex(ids_O)}
        for yard in ("C", "O"):
            if tables[a][yard].isna().any().any():
                raise SystemExit(f"{a}: forecasts missing at ({yard})")
    out_rows, rule_rows = [], {}
    for yard, inf in infos.items():
        models = {}
        for a in (twin, arm):
            p = tables[a][yard]
            eta = pd.Series(C.lg(p.mean(axis=1).to_numpy()), index=p.index)
            models[a] = (p, K.walk_forward(eta, inf, z, L.TEST))
        for group, name, mask in K.populations(inf, L.TEST):
            ids = inf.index[mask]
            if len(ids) == 0:
                continue
            fc = {a: K.forecasts(p, inf, par, z, ids) for a, (p, par) in models.items()}
            r = K.paired(inf, ids, fc[arm], fc[twin])          # + = per surface (the twin) better than pooled
            out_rows.append({"yardstick": yard, "group": group, "population": name,
                             "comparison": f"per surface ({twin}) vs pooled ({arm})", **r})
            if group == "primary":
                rule_rows[(yard, name)] = {"estimate": float(r["estimate"]), "se": float(r["se"]),
                                           "p_better": float(r["p_better"])}
    scores = pd.DataFrame(out_rows)
    scores.to_csv(L.OUT / "t3_scores.csv", index=False)
    decision = decide(rule_rows)
    C.write_json(L.OUT / "t3_summary.json", {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "arms": [twin, arm],
        "unit": "mLL per match; positive = the per-surface build better than pooled; 95% intervals, seeds paired",
        "primary": {f"{k[0]} {k[1]}": v for k, v in rule_rows.items()}, "decision": decision})
    pd.set_option("display.width", 240)
    print(scores[scores["group"] == "primary"][["yardstick", "population", "comparison", "matches", "estimate", "lo",
                                                 "hi", "p_better", "reading"]].round(3).to_string(index=False))
    print(decision)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--build", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--score", action="store_true")
    ap.add_argument("--arm", choices=list(T3), default="P0")
    a = ap.parse_args()
    if a.build:
        build()
        return 0
    return run(a.arm) if a.run else score(a.arm)


if __name__ == "__main__":
    sys.exit(main())
