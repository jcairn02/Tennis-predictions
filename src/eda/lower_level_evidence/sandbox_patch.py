"""Patch a candidate sandbox (run_chain.py --setup --candidate) with the role-08 translation hooks; never the repository.

Copies translate_hooks.py and offsets.py into the sandbox's src/eda/lower_level_evidence/ (the setup may predate their
last edit), inserts two lines in each of the sandbox's copies of stageB_adjperf.py (build: after the per-match z, before
the decay-and-shrink step) and stage4_features.py (history_sums: before the sums), and writes the unified diff against
the repository's files to data/studies/lower_level_evidence/candidates/sandbox_patch.diff. The hooks do nothing unless
LLE_TRANSLATE is set (translate_hooks.py). Refuses to patch the repository itself or a file whose anchor is not found
exactly once; a file already patched is left as it is.
Run: ./python.sh src/eda/lower_level_evidence/sandbox_patch.py --sandbox C:/Users/zerom/tnr_lle
"""
from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "lower_level_evidence" / "candidates" / "sandbox_patch.diff"
COPIED = ("src/eda/lower_level_evidence/translate_hooks.py", "src/eda/lower_level_evidence/offsets.py")
PATCHES = {
    "src/eda/ufc_ideas/stageB_adjperf.py": (
        "        Z[(s, ch)] = z\n    del mom\n    feats = {}\n",
        "        Z[(s, ch)] = z\n    del mom\n"
        "    from src.eda.lower_level_evidence import translate_hooks as _LLE   # lower_level_evidence role 08 (sandbox only)\n"
        "    Z = _LLE.translate_forms(ctx.rows, ctx.box_idx, Z)                   # off unless LLE_TRANSLATE is set\n"
        "    feats = {}\n"),
    "src/eda/predictability_diagnostic/stage4_features.py": (
        "    for s in HIST:\n        x, d, ok = xd[s]\n        mu = mu_of_rows(rows, ctx[\"means\"][s])\n",
        "    from src.eda.lower_level_evidence import translate_hooks as _LLE   # lower_level_evidence role 08 (sandbox only)\n"
        "    for s in HIST:\n        x, d, ok = xd[s]\n"
        "        x = _LLE.translate_counts(rows, s, x, d, ok)                     # off unless LLE_TRANSLATE is set\n"
        "        mu = mu_of_rows(rows, ctx[\"means\"][s])\n"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sandbox", required=True)
    a = ap.parse_args()
    sb = Path(a.sandbox)
    if sb.resolve() == ROOT.resolve() or not (sb / "src").is_dir():
        raise SystemExit(f"{sb} is not a sandbox (or is the repository)")
    for rel in COPIED:
        shutil.copy2(ROOT / rel, sb / rel)
        print(f"copied {rel}")
    diffs = []
    for rel, (old, new) in PATCHES.items():
        p = sb / rel
        s = p.read_text(encoding="utf-8")
        if s.count(new) == 1:
            print(f"already patched: {rel}")
        else:
            if s.count(old) != 1:
                raise SystemExit(f"{rel}: the anchor is found {s.count(old)} times, not once; nothing patched")
            p.write_text(s.replace(old, new), encoding="utf-8")
            print(f"patched {rel}")
        orig = (ROOT / rel).read_text(encoding="utf-8").splitlines(keepends=True)
        mod = p.read_text(encoding="utf-8").splitlines(keepends=True)
        diffs += difflib.unified_diff(orig, mod, fromfile=f"repository/{rel}", tofile=f"sandbox/{rel}")
    OUT.write_text("".join(diffs), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
