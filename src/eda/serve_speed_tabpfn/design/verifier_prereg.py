"""R4 test verifier, part 8: the pre-registration's machine-checkable claims against score.py.

Two parts.

  real inputs (no outcome)   the populations and counts the draft states (men 7,068 = 2,674 / 2,620 / 1,774; women
                             6,586; both 13,654; 33 blocks; early-price men 1,442 = 232 + 1,210, clean 582 = 117 + 465),
                             the recency and id_conflict counts the lead must fill, the SD of spd_f, the code-hash file
                             list and the six keys --run verifies. Read through score.population (no a_won).
  --run's refusals           on the strategist's stand-in world (test_ssp_harness.make_world: a fake frame with fake
                             labels, in a temporary folder; the real study tree is never written), with score.labels
                             patched to raise unless a case is meant to reach it:
                               results.json present; no pre-registration; no .sha256; a .sha256 that does not match;
                               the draft's [lead] placeholders; one recorded hash wrong; a stand-in feature meta; reuse
                               checks not passed; a stale speed fit;
                             and two completion cases with every needed fit written as a file: all present (must run),
                             and every A2 (spd_raw) fit missing (does --run refuse, or consume its one run?).

Writes data/studies/serve_speed_tabpfn/design/verifier_prereg.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_prereg.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

OUT = C.OUT / "design" / "verifier_prereg.json"


def harness_tests():
    spec = importlib.util.spec_from_file_location("ssp_harness_tests",
                                                  ROOT / "test" / "serve_speed_tabpfn" / "test_ssp_harness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------------------------
# Real inputs: counts only

def real_counts() -> dict:
    info = S.population(C.DEFAULT)
    out = {}
    for pop, seasons in (("men", S.TEST), ("women", S.TEST), ("both", S.TEST), ("men", (2025, 2026)),
                         ("men_early_all", (2025, 2026)), ("men_early_clean", (2025, 2026)),
                         ("men_recency_both", S.TEST), ("men_recency_one", S.TEST), ("men_recency_neither", S.TEST),
                         ("women_no_conflict", S.TEST)):
        ids = S.population_ids(info, pop, seasons)
        inf = info.loc[ids]
        out[f"{pop} {seasons[0]}-{seasons[-1]}"] = {
            "matches": int(len(ids)), "by_season": {str(k): int(v) for k, v in inf["season"].value_counts().sort_index().items()},
            "blocks": int(inf["block"].nunique())}
    men = info.loc[S.population_ids(info, "men", S.TEST)]
    out["spd_f_sd_men_2024_2026"] = float(men["spd_f"].std())
    out["spd_f_sd_men_2022_2023"] = float(info.loc[S.population_ids(info, "men", (2022, 2023)), "spd_f"].std())
    out["spd_f_nonzero_men_2024_2026"] = int((men["spd_f"] != 0).sum())
    out["player_ids_missing_men_2024_2026"] = int(men["player_a_id"].isna().sum() + men["player_b_id"].isna().sum())
    out["women_id_conflict_2024_2026"] = int(info.loc[S.population_ids(info, "women", S.TEST), "id_conflict"].sum())
    out["population_sha256"] = S.ids_hash(S.population_ids(info, "men", S.TEST))
    out["code_files"] = list(C.CODE_FILES)
    out["prereg_keys_verified_by_run"] = list(S.PREREG_KEYS)
    draft = C.DEFAULT.prereg.read_text(encoding="utf-8")
    out["draft_recorded_hashes"] = S.recorded(draft)
    return out


# ------------------------------------------------------------------------------------------------
# The stand-in world: every fit the scorer needs, as files

def write_fit(P: C.Paths, arm: str, season: int, seed: int, folder: Path, fsha: str | None, rng, priced: set) -> None:
    f = pd.read_parquet(P.model_frame, columns=["match_id", "season"])
    ids = f.loc[f["season"] == season, "match_id"].to_numpy().astype(str)
    n_train = int(f["season"].between(C.TRAIN_FROM, season - 1).sum())
    cols = A.arm_inputs(arm, P)
    meta = {"arm": arm, "season": season, "seed": seed, "columns": cols, "train_shape": [n_train, len(cols)],
            "train_seasons": [C.TRAIN_FROM, season - 1], "feature_sha256": fsha}
    p = rng.uniform(0.2, 0.8, len(ids))
    payload = {"p_td": np.r_[p, 1 - p], "ids_td": ids}
    if A.has_odds(arm) and season in C.PRICE_SEASONS:
        e = np.array([i for i in ids if i in priced])
        pe = rng.uniform(0.2, 0.8, len(e))
        payload.update({"p_early": np.r_[pe, 1 - pe], "ids_early": e, "p_late": np.r_[pe, 1 - pe], "ids_late": e})
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(folder / f"{arm}__{season}__seed{seed}.npz", meta=np.asarray(json.dumps(meta)), **payload)


def complete_world(P: C.Paths, skip_arms=(), skip_fits=()) -> None:
    """Every fit the scorer needs, as files (fake forecasts); none written for skip_arms or (arm, season, seed) in
    skip_fits (no file is ever deleted)."""
    rng = np.random.default_rng(5)
    fsha = C.sha256_file(P.feature_file)
    priced = set(pd.read_parquet(P.early, columns=["match_id"])["match_id"].astype(str))
    for arm, need in S.needed_fits().items():
        if arm == "model" or arm in skip_arms:
            continue                                   # the stand-in already holds model 2019-2026 seeds 0-15
        for season, seed in sorted(need):
            if (arm, season, seed) in skip_fits:
                continue
            folder = P.race_local if (arm == "model_noodds" and seed < 3) else P.local
            write_fit(P, arm, season, seed, folder, None if arm == "model_noodds" else fsha, rng, priced)


def hashed_prereg(P: C.Paths, hashes: dict, tamper: dict | None = None, placeholders: bool = False,
                  write_sha: bool = True) -> None:
    lines = [f"{k}: {'[lead]' if placeholders else (tamper or {}).get(k, v)}" for k, v in hashes.items()]
    P.prereg.write_text("# stand-in pre-registration\n\n```\n" + "\n".join(lines) + "\n```\n", encoding="utf-8")
    if write_sha:
        P.prereg_sha.write_text(C.sha256_file(P.prereg) + "  preregistration.md\n", encoding="utf-8")


def attempt(P: C.Paths, allow_labels: bool = False) -> str:
    real = S.labels
    if not allow_labels:
        S.labels = lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() reached"))
    try:
        S.run(P)
        return "RAN (results.json written)"
    except AssertionError as e:
        return f"REACHED LABELS: {e}"
    except (RuntimeError, FileNotFoundError) as e:
        return f"refused: {str(e)[:160]}"
    finally:
        S.labels = real


def refusal_cases() -> list[dict]:
    H = harness_tests()
    root = Path(tempfile.mkdtemp(prefix="ssp_verifier_prereg_"))
    (root / "world").mkdir()
    P0 = H.make_world(root / "world")
    out = []

    def fresh(name: str) -> C.Paths:
        d = root / name
        shutil.copytree(P0.out, d / "out")
        shutil.copytree(P0.race_local, d / "race_local")
        P = P0.with_(out=d / "out", local=d / "out" / "local", checks=d / "out" / "checks",
                     features=d / "out" / "features", prereg=d / "prereg.md", race_local=d / "race_local")
        C.write_json(P.checks / "repro_check.json", {"passed": True})
        C.write_json(P.checks / "fingerprint_check.json", {"all_ok": True})
        return P

    def case(name, P, expect, allow_labels=False):
        r = attempt(P, allow_labels)
        ok = r.startswith(expect)
        out.append({"case": name, "result": r, "expected": expect, "pass": ok})

    P = fresh("results_exist")
    (P.out / "results.json").write_text("{}", encoding="utf-8")
    case("results.json already present", P, "refused")
    P = fresh("no_prereg")
    case("no pre-registration", P, "refused")
    P = fresh("no_sha")
    hashed_prereg(P, S.hashes(P), write_sha=False)
    case("pre-registration without its .sha256", P, "refused")
    P = fresh("sha_mismatch")
    hashed_prereg(P, S.hashes(P))
    P.prereg.write_text(P.prereg.read_text(encoding="utf-8") + "edited after the hash\n", encoding="utf-8")
    case(".sha256 does not match (edited after hashing)", P, "refused")
    P = fresh("placeholders")
    hashed_prereg(P, S.hashes(P), placeholders=True)
    case("the draft's [lead] placeholders", P, "refused")
    P = fresh("real_draft")
    shutil.copy(C.DEFAULT.prereg, P.prereg)
    P.prereg_sha.write_text(C.sha256_file(P.prereg) + "\n", encoding="utf-8")
    case("the real draft text, hashed", P, "refused")
    for key in S.PREREG_KEYS:
        P = fresh(f"wrong_{key}")
        hashed_prereg(P, S.hashes(P), tamper={key: "0" * 64})
        case(f"recorded {key} differs", P, "refused")
    P = fresh("standin_meta")
    hashed_prereg(P, S.hashes(P))
    meta = C.read_json(P.feature_meta)
    C.write_json(P.feature_meta, {**meta, "standin_panel": True})
    case("feature meta says stand-in panel", P, "refused")
    P = fresh("checks_not_passed")
    hashed_prereg(P, S.hashes(P))
    C.write_json(P.checks / "repro_check.json", {"passed": False})
    case("reproduction check not passed", P, "refused")
    P = fresh("stale")
    complete_world(P)
    write_fit(P, "spd", 2024, 0, P.local, "f" * 64, np.random.default_rng(1), set())
    hashed_prereg(P, S.hashes(P))
    case("a stale speed fit (another feature file)", P, "refused")
    P = fresh("p2_fit_missing")
    complete_world(P, skip_fits={("spd", 2026, 15)})
    hashed_prereg(P, S.hashes(P))
    case("a P2 fit missing (spd 2026 seed 15)", P, "refused", allow_labels=True)
    P = fresh("complete")
    complete_world(P)
    hashed_prereg(P, S.hashes(P))
    case("everything present (synthetic stand-in labels)", P, "RAN", allow_labels=True)
    res = C.read_json(P.out / "results.json") if (P.out / "results.json").exists() else {}
    out[-1]["unavailable_rows"] = [r["cid"] for r in res.get("paired_secondaries", []) if not r.get("available", True)]
    P = fresh("a2_missing")
    complete_world(P, skip_arms=("spd_raw",))
    hashed_prereg(P, S.hashes(P))
    r = attempt(P, allow_labels=True)
    res = C.read_json(P.out / "results.json") if (P.out / "results.json").exists() else {}
    out.append({"case": "every A2 (spd_raw) fit missing", "result": r,
                "unavailable_rows": [x["cid"] for x in res.get("paired_secondaries", []) if not x.get("available", True)],
                "expected": "refused (proposed)", "pass": r.startswith("refused"),
                "note": "if RAN: --run consumed its one run with secondaries marked unavailable"})
    return out, str(root)


def main() -> int:
    report = {"what": "pre-registration claims against score.py: counts (no outcome) and --run's refusals on a "
                      "stand-in world with fake labels"}
    report["real_counts"] = real_counts()
    cases, root = refusal_cases()
    report["run_cases"] = cases
    report["stand_in_root"] = root
    C.write_json(OUT, report)
    print(json.dumps(report["real_counts"], indent=1, default=str)[:3500])
    for c in cases:
        print(f"{'ok ' if c['pass'] else 'NO '} {c['case']}: {c['result']}"
              + (f"  unavailable {c['unavailable_rows']}" if c.get("unavailable_rows") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
