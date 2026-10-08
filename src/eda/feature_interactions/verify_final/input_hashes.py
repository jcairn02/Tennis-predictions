"""Final-test verifier: do the files final_test.py reads still match the frozen inputs manifest (hypotheses/prepare.json)?
File hashes only, no content read.

    ./python.sh src/eda/feature_interactions/verify_final/input_hashes.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import final_test as FT  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402


def flatten(d, out):
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v):
                out[k] = v
            else:
                flatten(v, out)
    elif isinstance(d, list):
        for v in d:
            flatten(v, out)


def main() -> int:
    man = {}
    flatten(json.loads((C.OUT / "hypotheses" / "prepare.json").read_text(encoding="utf-8")), man)
    rel = lambda p: str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")  # noqa: E731
    want = [C.MODEL_FRAME, C.EARLY, S.PRE_REBUILD_STAGE0, FT.X_FILE]
    want += [d / f"model__{s}__seed{k}.npz" for s in range(2014, 2027) for k in range(16)
             for d in (C.LOCAL, C.RACE_LOCAL) if (d / f"model__{s}__seed{k}.npz").exists()]
    res = {"in_manifest_and_equal": 0, "in_manifest_and_DIFFERENT": [], "not_in_manifest": []}
    for p in want:
        key = rel(p)
        if key not in man:
            res["not_in_manifest"].append(key)
        elif C.sha256_file(p) == man[key]:
            res["in_manifest_and_equal"] += 1
        else:
            res["in_manifest_and_DIFFERENT"].append(key)
    res["forecast_files_checked"] = len(want) - 4
    (C.OUT / "verify_final" / "input_hashes.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
