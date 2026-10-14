"""Write the level layer's hooks into the repository's 11 builders (10 Oct 2026): the study's C1 and C2 edits, under the
integrated tags. Checks, before writing anything: every builder is the decided one (no edit yet), and each result equals
the study's validated snapshot (system/arms/validated_src/) once the snapshot's sandbox tags are mapped to the integrated
ones. Writes nothing unless all 11 pass. Run from the repository root: ./python.sh <this file> [--write]"""
import hashlib
import json
import py_compile
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import level_layer_ios as C2  # noqa: E402
from src.eda.lower_level_evidence import system_sandbox as SB  # noqa: E402

VALIDATED = ROOT / "data/studies/lower_level_evidence/system/arms/validated_src"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


plan, problems = {}, []
for rel in SB.PATCH_SPECS:
    text = (ROOT / rel).read_text(encoding="utf-8")
    if SB.integrated(text, rel):
        problems.append(f"{rel}: already integrated")
        continue
    new = SB.patched_text(text, rel)
    plan[rel] = (text, new)
for rel, edits in C2.PATCHES.items():
    text = (ROOT / rel).read_text(encoding="utf-8")
    if C2.integrated(text, rel):
        problems.append(f"{rel}: already integrated")
        continue
    s = text
    for old, new in edits:
        if s.count(old) != 1:
            problems.append(f"{rel}: anchor found {s.count(old)} times")
        s = s.replace(old, new, 1)
    plan[rel] = (text, s)

report = {}
for rel, (old, new) in plan.items():
    snap = SB.normalize((VALIDATED / rel).read_text(encoding="utf-8"))
    eq = new == snap
    back = (SB.unpatched_text(new, rel) if rel in SB.PATCH_SPECS else C2.unpatched_text(new, rel)) == old
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(new)
    try:
        py_compile.compile(fh.name, doraise=True)
        compiles = True
    except py_compile.PyCompileError as e:
        compiles = False
        problems.append(f"{rel}: {e}")
    report[rel] = {"equals_normalized_snapshot": eq, "unpatches_to_the_decided_builder": back, "compiles": compiles,
                   "before_sha256": sha((ROOT / rel).read_bytes())}
    if not (eq and back and compiles):
        problems.append(f"{rel}: snapshot {eq}, unpatch {back}, compiles {compiles}")

print(json.dumps(report, indent=1))
print("problems:", problems)
if "--write" in sys.argv:
    if problems or len(plan) != 11:
        raise SystemExit("not written")
    for rel, (old, new) in plan.items():
        (ROOT / rel).write_text(new, encoding="utf-8")
        report[rel]["after_sha256"] = sha((ROOT / rel).read_bytes())
    out = Path(sys.argv[sys.argv.index("--write") + 1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("written; record", out)
