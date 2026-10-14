"""Final-test verifier, step 3: final_test's two modes, with no real 2025-2026 result.

  A. --check reads no result: check() run with a_won never loaded (NaN) and again with a_won random noise; both
     outputs must equal each other and the study's existing check.json (written there with the real frame).
     build_x is trapped (X_FILE exists, so check() must not rebuild it); output goes to verify_final/, not final/.
  B. --run refuses without the pre-registration's POPULATION_SHA256 line (line absent, wrong hash, file absent), and
     with the right line it passes the gate (the first fit is trapped). The population is synthetic throughout.
  C. One end-to-end synthetic run() (beta for 0.2 mLL), output to verify_final/final_results_synthetic.json: every
     branch (primary, effect, subsets, Polymarket, the JSON write) must complete.

    ./python.sh src/eda/feature_interactions/verify_final/modes.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.verify_final import harness as HN  # noqa: E402

FT, TT, C = HN.FT, HN.TT, HN.C


class Trap(Exception):
    pass


def trap(name):
    def f(*a, **k):
        raise Trap(name)
    return f


def check_mode(out: dict) -> None:
    real_out = FT.OUT
    FT.OUT = HN.OUT / "check_result_free"
    build_x = FT.build_x
    FT.build_x = trap("build_x")
    res = []
    rng = np.random.default_rng(5)
    for label, fill in (("a_won NaN", None), ("a_won noise", "noise")):
        def frame(seasons, with_players=True, _fill=fill):
            f = HN.frame_free(seasons, with_players)
            if _fill == "noise":
                f["a_won"] = (rng.random(len(f)) < 0.5).astype(float)
            return f
        TT.frame = frame
        FT.check()
        res.append(json.loads((FT.OUT / "check.json").read_text(encoding="utf-8")))
    study = json.loads((real_out / "check.json").read_text(encoding="utf-8"))
    out["check_nan_equals_noise"] = res[0] == res[1]
    out["check_equals_study_check_json"] = res[0] == study
    out["check_diff_keys_vs_study"] = [k for k in study if study[k] != res[0].get(k)]
    FT.OUT, FT.build_x, TT.frame = real_out, build_x, HN.frame_free


def run_gate(out: dict, syn: HN.Synth) -> None:
    real_docs, real_params = C.DOCS, FT.parameters
    FT.population = lambda: syn.f.copy()
    FT.parameters = trap("parameters")
    reg = (real_docs / "preregistration.md").read_text(encoding="utf-8")
    d = Path(os.environ["VERIFY_TMP"]) / "prereg_variants"          # outside the study folders (scratch copies)
    d.mkdir(parents=True, exist_ok=True)
    cases = {"no hash line": "\n".join(ln for ln in reg.splitlines() if not ln.startswith("POPULATION_SHA256:")),
             "wrong hash": reg.replace("POPULATION_SHA256: b76b", "POPULATION_SHA256: 0000"),
             "hash line indented": reg.replace("POPULATION_SHA256:", "  POPULATION_SHA256:"),
             "file absent": None, "real pre-registration": reg}
    for name, text in cases.items():
        sub = d / name.replace(" ", "_")
        sub.mkdir(exist_ok=True)
        p = sub / "preregistration.md"
        if text is None:
            if p.exists():
                p.rename(sub / "preregistration.absent")
        else:
            p.write_text(text, encoding="utf-8")
        C.DOCS = sub
        try:
            FT.run()
            outcome = "ran to the end (no gate)"
        except SystemExit as e:
            outcome = f"refused: {e}"
        except Trap as e:
            outcome = f"passed the gate (reached {e})"
        except FileNotFoundError as e:
            outcome = f"refused: FileNotFoundError {Path(str(e.filename)).name}"
        out[f"run_gate[{name}]"] = outcome
    C.DOCS, FT.parameters = real_docs, real_params


def end_to_end(out: dict, syn: HN.Synth, beta: float) -> None:
    real_out = FT.OUT
    FT.OUT = HN.OUT / "SYNTHETIC_end_to_end"            # synthetic outcomes: not the final test's results
    syn.draw(beta, np.random.default_rng(77))
    FT.population = lambda: syn.f.copy()
    FT.run()
    r = json.loads((FT.OUT / "final_results.json").read_text(encoding="utf-8"))
    out["end_to_end_keys"] = sorted(r)
    out["end_to_end_primary"] = {k: r["primary"][k] for k in ("b", "lo", "hi", "df", "blocks", "n")}
    out["end_to_end_effect"] = {k: r["effect"][k] for k in ("gain", "lo", "hi", "n")}
    out["end_to_end_subsets"] = [[s["subset"], s["matches"], round(s["primary"]["b"], 3), s["primary"]["df"],
                                  round(s["effect"]["gain"], 3)] for s in r["subsets"]]
    out["end_to_end_polymarket"] = [[p["population"], p["comparison"], p["matches"], round(p["gain"], 4)]
                                    for p in r["polymarket"]]
    out["end_to_end_column_arm"] = [[c["tour"], c["matches"], round(c["gain"], 4), round(c["lo"], 3), round(c["hi"], 3)]
                                    for c in r.get("column_arm", [])]
    FT.OUT = real_out


def main() -> int:
    warnings.simplefilter("ignore")
    out = {}
    check_mode(out)
    syn = HN.Synth()
    syn.draw(0.0, np.random.default_rng(3))
    run_gate(out, syn)
    end_to_end(out, syn, 0.042955620639999706)
    (HN.OUT / "modes.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, default=float)[:3500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
