"""Final-test verifier, round 2 (checkpoint 2, R-B, R-C): run()'s input gate and --check, no real result.

A. Positive control: the pre-registration with FINAL_TEST_CODE_SHA256 filled with today's code_hash() (scratch copy)
   passes every file check and reaches population() (trapped).
B. One input changed (C.sha256_file returns another digest for that file): run() must refuse, naming the input,
   without reaching population(). Every hashed file: model frame, Stage 0, x, early frame, the 10 code files, one
   forecast file per folder and arm.
C. Real modified copies (one byte appended, no patching): x file, early frame, one code file (FT.ROOT redirected).
D. Each hash line removed. E. After the gate: population minus one match; one NaN a_won.
F. End to end on synthetic outcomes: final_primary.json first (with the text's SHA-256), then final_results.json;
   a failing polymarket(); a failing tml_exposed().  G. --check with a_won NaN vs noise.

    VERIFY_TMP=<scratch dir> ./python.sh src/eda/feature_interactions/verify_final/gate_round2.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.verify_final import harness as HN  # noqa: E402

FT, TT, C = HN.FT, HN.TT, HN.C
TMP = Path(os.environ["VERIFY_TMP"]) / "gate_round2"
REAL = {"sha": C.sha256_file, "pop": FT.population, "params": FT.parameters, "docs": C.DOCS, "x": FT.X_FILE,
        "early": C.EARLY, "root": FT.ROOT, "out": FT.OUT, "poly": FT.polymarket, "tml": FT.tml_exposed}


class Trap(Exception):
    pass


def trap(name):
    def f(*a, **k):
        raise Trap(name)
    return f


def restore():
    C.sha256_file, FT.population, FT.parameters, C.DOCS = REAL["sha"], trap("population"), REAL["params"], REAL["docs"]
    FT.X_FILE, C.EARLY, FT.ROOT, FT.OUT = REAL["x"], REAL["early"], REAL["root"], REAL["out"]
    FT.polymarket, FT.tml_exposed = REAL["poly"], REAL["tml"]


def use_text(text: str, name: str) -> Path:
    d = TMP / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "preregistration.md").write_text(text, encoding="utf-8")
    C.DOCS = d
    return d / "preregistration.md"


def attempt() -> str:
    try:
        FT.run()
        return "ran to the end"
    except SystemExit as e:
        return f"refused: {e}"
    except Trap as e:
        return f"passed the gate (reached {e})"


def main() -> int:
    warnings.simplefilter("ignore")
    out = {}
    syn = HN.Synth()                                     # TT.frame is result-free from here on
    reg = (REAL["docs"] / "preregistration.md").read_text(encoding="utf-8")
    good = re.sub(r"^FINAL_TEST_CODE_SHA256:.*$", f"FINAL_TEST_CODE_SHA256: {FT.code_hash()}", reg, flags=re.M)
    restore()
    use_text(good, "good")
    out["A positive control"] = attempt()
    targets = {"model frame": C.MODEL_FRAME, "stage0": HN.S.PRE_REBUILD_STAGE0, "x file": FT.X_FILE, "early": C.EARLY}
    for n in ("final_test.py", "tabpfn_tests.py", "screen.py", "common.py", "panel.py", "history.py", "g5_build.py",
              "screen_batch.py"):
        targets[f"code {n}"] = ROOT / "src" / "eda" / "feature_interactions" / n
    targets["code tabpfn_thinking/common.py"] = ROOT / "src/eda/tabpfn_thinking/common.py"
    targets["code early_price_score.py"] = ROOT / "src/eda/surface_elo_pieces/early_price_score.py"
    for folder in (C.LOCAL, C.RACE_LOCAL):
        for arm in ("model", "binj"):
            hit = sorted(folder.glob(f"{arm}__2026__seed*.npz"))
            if hit:
                targets[f"forecast {folder.parent.name}/{hit[-1].name}"] = hit[-1]
    for name, path in targets.items():
        restore()
        use_text(good, "good")
        C.sha256_file = lambda p, *a, _t=Path(path).resolve(), **k: "f" * 64 if Path(p).resolve() == _t \
            else REAL["sha"](p, *a, **k)
        out[f"B changed: {name}"] = attempt()
    for name, src in (("x file", REAL["x"]), ("early", REAL["early"])):
        restore()
        use_text(good, "good")
        cp = TMP / f"copy_{src.name}"
        shutil.copyfile(src, cp)
        with open(cp, "ab") as fh:
            fh.write(b"\0")
        if name == "x file":
            FT.X_FILE = cp
        else:
            C.EARLY = cp
        out[f"C real copy changed: {name}"] = attempt()
    restore()
    use_text(good, "good")
    tree = TMP / "tree"
    for rel in [f"src/eda/feature_interactions/{n}" for n in ("final_test.py", "tabpfn_tests.py", "screen.py",
                "common.py", "panel.py", "history.py", "g5_build.py", "screen_batch.py")] + \
            ["src/eda/tabpfn_thinking/common.py", "src/eda/surface_elo_pieces/early_price_score.py"]:
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, tree / rel)
    FT.ROOT = tree
    out["C copied tree unchanged"] = attempt()
    with open(tree / "src/eda/feature_interactions/screen.py", "a", encoding="utf-8") as fh:
        fh.write("\n# changed\n")
    out["C copied tree, screen.py changed"] = attempt()
    for key in ("MODEL_FRAME_SHA256", "STAGE0_MATCHES_SHA256", "BINJ_X_SHA256", "EARLY_SHA256",
                "FINAL_TEST_CODE_SHA256", "FORECASTS_SHA256"):
        restore()
        use_text(re.sub(rf"^{key}:.*\n", "", good, flags=re.M), f"no_{key}")
        out[f"D line removed: {key}"] = attempt()
    syn.draw(0.042955620639999706, np.random.default_rng(77))
    for name, fr in (("full synthetic population", syn.f.copy()), ("one match dropped", syn.f.iloc[1:].copy()),
                     ("one NaN a_won", syn.f.assign(a_won=np.r_[np.nan, syn.f["a_won"].to_numpy()[1:]]))):
        restore()
        use_text(good, "good")
        FT.population, FT.parameters = (lambda _f=fr: _f.copy()), trap("parameters")
        out[f"E {name}"] = attempt()
    restore()
    reg_file = use_text(good, "good")
    FT.population, FT.OUT = (lambda: syn.f.copy()), HN.OUT / "SYNTHETIC_end_to_end_round2"
    out["F end to end"] = attempt()
    p = json.loads((FT.OUT / "final_primary.json").read_text(encoding="utf-8"))
    r = json.loads((FT.OUT / "final_results.json").read_text(encoding="utf-8"))
    out["F primary file keys"] = sorted(p)
    out["F primary file records the text's SHA-256"] = p["preregistration_sha256"] == REAL["sha"](reg_file)
    out["F effect keys"] = sorted(p["effect"])
    out["F b14 in parameters"] = all("b14" in v for v in p["parameters"].values())
    out["F subsets"] = [[s["subset"], "error" in s, sorted(s.get("effect", {}))] for s in r["subsets"]]
    out["F secondaries ok"] = [isinstance(r["polymarket"], list), isinstance(r["column_arm"], list)]
    (FT.OUT / "final_results.json").rename(FT.OUT / "final_results_ok.json")
    FT.polymarket = trap("polymarket failure")
    out["F2 failing polymarket"] = attempt()
    r2 = json.loads((FT.OUT / "final_results.json").read_text(encoding="utf-8"))
    out["F2 recorded"] = [str(r2["polymarket"])[:60], isinstance(r2["column_arm"], list)]
    (FT.OUT / "final_results.json").rename(FT.OUT / "final_results_poly_fail.json")
    def tml_fail(*a, **k):
        raise RuntimeError("tml_exposed failure")
    FT.polymarket, FT.tml_exposed = REAL["poly"], tml_fail
    try:
        out["F3 failing tml_exposed"] = attempt()
    except RuntimeError as e:
        out["F3 failing tml_exposed"] = f"run() crashed: {e}"
    out["F3 final_results.json written"] = (FT.OUT / "final_results.json").exists()
    restore()
    (HN.OUT / "gate_round2.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for k, v in out.items():
        print(k, "->", str(v)[:150])
    return 0


if __name__ == "__main__":
    sys.exit(main())
