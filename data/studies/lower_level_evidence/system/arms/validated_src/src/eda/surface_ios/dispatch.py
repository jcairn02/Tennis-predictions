"""Prepare the surface-IOS study's TabPFN uploads (the locked plan: plan.py); optionally quote or run them on the API.

    ./python.sh src/eda/surface_ios/dispatch.py --prepare             builds every slot's upload from the arm frames and
                                                                      writes uploads/manifest.json (free; tennis env).
                                                                      The study's fits read these uploads locally:
                                                                      run_local.py (no API)
    ./python_tabpfn.sh src/eda/surface_ios/dispatch.py --quote        the server's quotes and the remaining quota (free)
    ./python_tabpfn.sh src/eda/surface_ios/dispatch.py --run --spend-tokens [--slots a,b,...]
                                                                      PAID: ask the owner first (the owner has
                                                                      raised concern about API costs); one fit and one
                                                                      prediction per slot, through guard.execute_once

A slot is one arm with one seed in one expanding window: trained on every main-tour match with odds from 2013 to the
season before the test season, and queried on the test season's matches in both orientations (A and B swapped), as the
original study did. --run refuses if the quotes exceed the remaining daily or monthly quota.
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
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import plan as PL  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

UPLOADS = C.OUT / "uploads"


def flip(X: pd.DataFrame, antisymmetric: list[str]) -> pd.DataFrame:
    out = X.copy()
    cols = [c for c in X.columns if c in antisymmetric]
    out[cols] = -X[cols]
    return out


def slot_frames(arm: str, year: int) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame, pd.DataFrame]:
    f = pd.read_parquet(PL.arm_path(arm))
    names = PL.ARMS[arm]["columns"]
    train = (f["year"] < year).to_numpy()
    test = (f["year"] == year).to_numpy()            # every frame row has closing odds (train or test split alike)
    X = pd.DataFrame({n: f[f"in_{n}"].to_numpy(dtype="float64") for n in names})
    X_train = X[train].reset_index(drop=True)
    y = f.loc[train, "a_won"].astype("int64").to_numpy()
    X_test = X[test].reset_index(drop=True)
    X_query = pd.concat([X_test, flip(X_test, PL.antisymmetric(names))], ignore_index=True)
    n = len(X_test)
    ids = pd.DataFrame({"match_id": np.r_[f.loc[test, "match_id"].to_numpy(), f.loc[test, "match_id"].to_numpy()],
                        "orientation": np.r_[np.zeros(n), np.ones(n)].astype(int)})
    return X_train, y, X_query, ids


def prepare() -> dict:
    UPLOADS.mkdir(parents=True, exist_ok=True)
    manifest = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "plan_sha256": PL.plan_hash(),
                "slots": {}}
    for slot, spec in PL.slots().items():
        X_train, y, X_query, ids = slot_frames(spec["arm"], spec["year"])
        d = UPLOADS / slot
        d.mkdir(parents=True, exist_ok=True)
        X_train.to_parquet(d / "X_train.parquet", index=False)
        np.save(d / "y_train.npy", y)
        X_query.to_parquet(d / "X_query.parquet", index=False)
        ids.to_parquet(d / "query_ids.parquet", index=False)
        manifest["slots"][slot] = {**spec, "columns": list(X_train.columns), "train_rows": int(len(X_train)),
                                   "query_rows": int(len(X_query)),
                                   "input_fingerprint": T.fingerprint(X_train, y, X_query),
                                   "files_sha256": {p.name: C.sha256(p) for p in sorted(d.glob("*"))}}
        C.log(f"{slot}: train {X_train.shape}, query {X_query.shape}")
    C.jdump(manifest, UPLOADS / "manifest.json")
    return manifest


def load_slot(slot: str, manifest: dict):
    m = manifest["slots"][slot]
    d = UPLOADS / slot
    for name, sha in m["files_sha256"].items():
        if C.sha256(d / name) != sha:
            raise RuntimeError(f"{slot}/{name} differs from the manifest; rerun --prepare")
    X_train = pd.read_parquet(d / "X_train.parquet")
    y = np.load(d / "y_train.npy", allow_pickle=False)
    X_query = pd.read_parquet(d / "X_query.parquet")
    if T.fingerprint(X_train, y, X_query) != m["input_fingerprint"]:
        raise RuntimeError(f"{slot}: the value fingerprint differs from the manifest")
    return X_train, y, X_query, m


def quote_all(manifest: dict, slots: list[str]) -> dict:
    from src.eda.surface_ios import guard as G
    backend = G.LiveBackend(G.BASE_CONFIG)
    account = backend.preflight()
    out = {"quoted_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "usage": account["usage"],
           "slots": {}}
    total = 0
    for slot in slots:
        X_train, y, X_query, m = load_slot(slot, manifest)
        q = backend.quote(X_train, X_query)
        out["slots"][slot] = q["predict"]["estimated_cost"]
        total += q["predict"]["estimated_cost"]
    cap = G.validate_account(account, X_train, X_query)
    out.update({"total_quoted": total, "capacity": cap})
    C.jdump(out, C.OUT / "quotes.json")
    C.log(f"quoted {total:,} tokens for {len(slots)} slots; remaining today {cap['daily_tokens_remaining']:,}, "
          f"this month {cap['monthly_tokens_remaining']:,}")
    return out


def run(manifest: dict, slots: list[str]) -> None:
    from src.eda.surface_ios import guard as G
    q = quote_all(manifest, slots)
    room = min(q["capacity"]["monthly_tokens_remaining"], q["capacity"]["daily_tokens_remaining"])
    if q["total_quoted"] > room:
        raise RuntimeError(f"quoted {q['total_quoted']:,} tokens exceed the remaining quota {room:,}; nothing sent")
    registered = PL.registered_configs()
    backend = G.LiveBackend(G.BASE_CONFIG)
    log_path = C.OUT / "tabpfn_runs.jsonl"
    for slot in slots:
        X_train, y, X_query, m = load_slot(slot, manifest)
        before = backend.usage()
        t0 = time.monotonic()
        res = G.execute_once(slot, registered, X_train, y, X_query, expected_input_sha256=m["input_fingerprint"],
                             fingerprint=T.fingerprint, description=PL.description(slot), log=C.log)
        after = backend.usage()
        rec = {"slot": slot, "finished_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "wall_seconds": round(time.monotonic() - t0, 1), "reused": res["reused_saved_predictions"],
               "monthly_usage_before": before.get("monthly_usage"), "monthly_usage_after": after.get("monthly_usage"),
               "metadata": res["receipt"].get("metadata")}
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
        C.log(f"{slot}: done in {rec['wall_seconds']}s; monthly usage {before.get('monthly_usage')} -> "
              f"{after.get('monthly_usage')}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--quote", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--spend-tokens", action="store_true")
    ap.add_argument("--slots", default="")
    a = ap.parse_args()
    if a.prepare:
        prepare()
        return 0
    manifest = json.loads((UPLOADS / "manifest.json").read_text(encoding="utf-8"))
    if manifest["plan_sha256"] != PL.plan_hash():
        raise RuntimeError("the plan changed after the uploads were prepared")
    slots = [s for s in a.slots.split(",") if s] or list(manifest["slots"])
    unknown = [s for s in slots if s not in manifest["slots"]]
    if unknown:
        raise ValueError(f"unknown slots: {unknown}")
    if a.quote:
        quote_all(manifest, slots)
        return 0
    if a.run:
        if not a.spend_tokens:
            raise SystemExit("--run needs --spend-tokens")
        run(manifest, slots)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
