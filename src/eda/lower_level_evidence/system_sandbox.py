"""Sandboxes of the lower-level-evidence system (role C1): set one up, patch its builders with the level layer (C1's
hooks and the joint-solve engineer's), pin the IOS constants, and check the patches. Never the repository.

    --setup [--n K]        MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_sys<K> run_chain.py --setup --candidate (K: the next
                           free number when omitted). The copy's tables are checked against the frozen reference first
                           (run_chain's history gate; check_tables() below re-hashes Stage 0, the odds and the timeline)
    --patch --sandbox D    copies level_layer.py (and common.py) into D, applies C1's patches (each anchor must be found
                           exactly once; a file already patched is left as it is), then C2's level_layer_ios.apply_patch(D)
                           when C2's module exists; writes the unified diffs against the repository's files to
                           data/studies/lower_level_evidence/system/arms/patches/ and D/LLE_SYSTEM.json (what was applied,
                           with hashes, and the pinned IOS_CONSTANTS_VERSION)
    --check --sandbox D    check_patch(D) for C1 and C2: every patch present once, the layer file the repository's
    --tables               check_tables(): the repository's live tables against the frozen reference's hashes
    --patch --sandbox D --stage0 F   phase 3: role F's candidate Stage 0 (its stage0_matches, stage0_match_players and
                           timing.parquet) copied over D's tables first, recorded with hashes; the build then runs lane 0
                           (Stage 1's odds link and the full leak-proof rebuild; the timeline step only when F brings no
                           timing.parquet) before lanes 1-3. Lane 0 is "not yet exercised" (run_chain.py:35-37)

C1's patches (each a few lines; the hooks do nothing unless LLE_LAYER is set):
    predictability_diagnostic/stage1_baselines.py   elo_pass: K x upd[i], count + upd[i] (booleans: the original pass);
                                                    tune: the frozen pass re-run with the layer's weights; main: the
                                                    probe's passes with the weights
    surface_elo_pieces/pieces.py                    elo_pass_ext as above; main: the final passes with the weights, the
                                                    offset's tuning on the unweighted flags (the reference's kd)
    predictability_diagnostic/stage4_features.py    history_sums: spw and rpw counts translated and weighted
                                                    (points_52w); weighted_elo_pass and elo_variants: elo_games
    predictability_diagnostic/stage3_ratings.py     main: the final pass's arrays translated and weighted (ratings_iid)
    ufc_ideas/stageB_adjperf.py                     build: the 17 forms' z recomputed with the layer, step 3 weighted;
                                                    main: the tuned constants pinned to the reference build's
Run: ./python.sh src/eda/lower_level_evidence/system_sandbox.py --setup | --patch --sandbox C:/Users/zerom/tnr_sys1 |
     --check --sandbox ... | --tables
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "data" / "studies" / "lower_level_evidence" / "system"
ARMS = SYSTEM / "arms"
PATCHES = ARMS / "patches"
PY_SHIM = ROOT / "python.sh"
SANDBOX_STEM = "C:/Users/zerom/tnr_sys"
IOS_VERSION = "2026-10-08_reference"
FIRST_RUN_SANDBOX = Path("C:/Users/zerom/tnr_lle")
COPIED = ("src/eda/lower_level_evidence/level_layer.py", "src/eda/lower_level_evidence/common.py")
# Since 10 Oct 2026 the repository's builders carry these edits themselves (docs/decisions/2026-10-10-level-evidence-
# layer.md): the same calls, under this tag. The study's sandboxes and its validated snapshot carry them under OLD_TAG;
# normalize() maps one onto the other, so the snapshot still checks the builders (system_arms.restore_validated_code).
TAG = "# level layer (LLE_LAYER)"
OLD_TAG = "# lower_level_evidence C1 (sandbox only)"
IMPORT = "from src.eda.lower_level_evidence import level_layer as _LLE  " + TAG.replace("# ", "# noqa: E402  ", 1) + "\n"

# file -> [(anchor, replacement)]; each anchor must be found exactly once in the repository's file
PATCH_SPECS: dict[str, list[tuple[str, str]]] = {
    "src/eda/predictability_diagnostic/stage1_baselines.py": [
        ("from src.eda.predictability_diagnostic import common as C  # noqa: E402\n",
         "from src.eda.predictability_diagnostic import common as C  # noqa: E402\n" + IMPORT),
        ("            xa[3] += k0 / (na + offset) ** shape * surprise\n"
         "            xb[3] -= k0 / (nb + offset) ** shape * surprise\n"
         "            xa[4] += 1\n"
         "            xb[4] += 1\n"
         "            if do_s:\n"
         "                surprise = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))\n"
         "                ya[3] += k0 / (nsa + offset) ** shape * surprise\n"
         "                yb[3] -= k0 / (nsb + offset) ** shape * surprise\n"
         "                ya[4] += 1\n"
         "                yb[4] += 1\n",
         "            xa[3] += upd[i] * k0 / (na + offset) ** shape * surprise   " + TAG + ": upd[i] True or w\n"
         "            xb[3] -= upd[i] * k0 / (nb + offset) ** shape * surprise\n"
         "            xa[4] += upd[i]\n"
         "            xb[4] += upd[i]\n"
         "            if do_s:\n"
         "                surprise = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))\n"
         "                ya[3] += upd[i] * k0 / (nsa + offset) ** shape * surprise\n"
         "                yb[3] -= upd[i] * k0 / (nsb + offset) ** shape * surprise\n"
         "                ya[4] += upd[i]\n"
         "                yb[4] += upd[i]\n"),
        ("            assert np.allclose(out[:len(early)], out_early, equal_nan=True)     # the tuning pass is its prefix\n",
         "            assert np.allclose(out[:len(early)], out_early, equal_nan=True)     # the tuning pass is its prefix\n"
         "            out = _LLE.elo_rerun(t, t[\"status\"].isin(UPDATES[rule]).tolist(), out, lambda u, h=h, k=k: elo_pass(\n"
         "                h[\"week\"], h[\"event\"], h[\"rnd\"], h[\"a\"], h[\"b\"], h[\"a_won\"], h[\"surf\"], u, h[\"n_players\"],\n"
         "                k[\"k0\"], k[\"offset\"], k[\"shape\"], surface=True))   " + TAG + "\n"),
        ("        upd, k = t[\"status\"].isin(UPDATES[rule]).tolist(), chosen[(tour, rule)]\n",
         "        upd, k = t[\"status\"].isin(UPDATES[rule]).tolist(), chosen[(tour, rule)]\n"
         "        upd = _LLE.elo_weights(t, upd)   " + TAG + "\n"),
    ],
    "src/eda/surface_elo_pieces/pieces.py": [
        ("from src.eda.surface_elo_pieces import common as C  # noqa: E402\n",
         "from src.eda.surface_elo_pieces import common as C  # noqa: E402\n" + IMPORT),
        ("            xa[3] += k0 / (na + offset) ** shape * surprise\n"
         "            xb[3] -= k0 / (nb + offset) ** shape * surprise\n"
         "            xa[4] += 1\n"
         "            xb[4] += 1\n"
         "            if do_s:\n"
         "                surprise_s = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))\n"
         "                ya[3] += k0 / (nsa + offset) ** shape * surprise_s\n"
         "                yb[3] -= k0 / (nsb + offset) ** shape * surprise_s\n"
         "                ya[4] += 1\n"
         "                yb[4] += 1\n"
         "                if mode == \"anchored\":\n"
         "                    surprise_x = res - 1.0 / (1.0 + 10.0 ** ((xb_s - xa_s) / 400.0))\n"
         "                    za[3] += k0 / (nsa + offset) ** shape * surprise_x\n"
         "                    zb[3] -= k0 / (nsb + offset) ** shape * surprise_x\n"
         "                elif mode == \"offset\":\n"
         "                    surprise_c = res - 1.0 / (1.0 + 10.0 ** (((rb + xb_s) - (ra + xa_s)) / 400.0))\n"
         "                    za[3] += kd0 / (nsa + kd_off) ** kd_shape * surprise_c\n"
         "                    zb[3] -= kd0 / (nsb + kd_off) ** kd_shape * surprise_c\n",
         "            xa[3] += upd[i] * k0 / (na + offset) ** shape * surprise   " + TAG + ": upd[i] True or w\n"
         "            xb[3] -= upd[i] * k0 / (nb + offset) ** shape * surprise\n"
         "            xa[4] += upd[i]\n"
         "            xb[4] += upd[i]\n"
         "            if do_s:\n"
         "                surprise_s = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))\n"
         "                ya[3] += upd[i] * k0 / (nsa + offset) ** shape * surprise_s\n"
         "                yb[3] -= upd[i] * k0 / (nsb + offset) ** shape * surprise_s\n"
         "                ya[4] += upd[i]\n"
         "                yb[4] += upd[i]\n"
         "                if mode == \"anchored\":\n"
         "                    surprise_x = res - 1.0 / (1.0 + 10.0 ** ((xb_s - xa_s) / 400.0))\n"
         "                    za[3] += upd[i] * k0 / (nsa + offset) ** shape * surprise_x\n"
         "                    zb[3] -= upd[i] * k0 / (nsb + offset) ** shape * surprise_x\n"
         "                elif mode == \"offset\":\n"
         "                    surprise_c = res - 1.0 / (1.0 + 10.0 ** (((rb + xb_s) - (ra + xa_s)) / 400.0))\n"
         "                    za[3] += upd[i] * kd0 / (nsa + kd_off) ** kd_shape * surprise_c\n"
         "                    zb[3] -= upd[i] * kd0 / (nsb + kd_off) ** kd_shape * surprise_c\n"),
        ("        upd = t[\"status\"].isin(B.UPDATES[\"ret\"]).tolist()\n",
         "        upd = t[\"status\"].isin(B.UPDATES[\"ret\"]).tolist()\n"
         "        upd0, upd = upd, _LLE.elo_weights(t, upd)   " + TAG + ": the passes read upd, the tuning upd0\n"),
        ("        kd, grid = tune_offset(t, h, upd, k)\n",
         "        kd, grid = tune_offset(t, h, upd0, k)   " + TAG + "\n"),
        ("        kd_gen, grid_gen = tune_offset(t, h_gen, upd, k)\n",
         "        kd_gen, grid_gen = tune_offset(t, h_gen, upd0, k)   " + TAG + "\n"),
    ],
    "src/eda/predictability_diagnostic/stage4_features.py": [
        ("from src.eda.predictability_diagnostic.scheduled_format import scheduled_format  # noqa: E402\n",
         "from src.eda.predictability_diagnostic.scheduled_format import scheduled_format  # noqa: E402\n" + IMPORT),
        ("    for s in HIST:\n        x, d, ok = xd[s]\n        mu = mu_of_rows(rows, ctx[\"means\"][s])\n",
         "    for s in HIST:\n        x, d, ok = xd[s]\n"
         "        x, d = _LLE.points_counts(rows, s, x, d, ok)   " + TAG + "\n"
         "        mu = mu_of_rows(rows, ctx[\"means\"][s])\n"),
        ("            wgt = weight[i]\n",
         "            wgt = upd[i] * weight[i]   " + TAG + ": upd[i] True or w\n"),
        ("            xa[3] += wgt * k0 / (na + offset) ** shape * surprise\n"
         "            xb[3] -= wgt * k0 / (nb + offset) ** shape * surprise\n"
         "            xa[4] += 1\n"
         "            xb[4] += 1\n",
         "            xa[3] += wgt * k0 / (na + offset) ** shape * surprise\n"
         "            xb[3] -= wgt * k0 / (nb + offset) ** shape * surprise\n"
         "            xa[4] += upd[i]   " + TAG + "\n"
         "            xb[4] += upd[i]\n"),
        ("                yb[3] -= wgt * k0 / (nsb + offset) ** shape * surprise\n"
         "                ya[4] += 1\n"
         "                yb[4] += 1\n",
         "                yb[3] -= wgt * k0 / (nsb + offset) ** shape * surprise\n"
         "                ya[4] += upd[i]   " + TAG + "\n"
         "                yb[4] += upd[i]\n"),
        ("                                           upd[idx].tolist(), wgt.tolist(), h[\"n_players\"], k[\"k0\"], k[\"offset\"], k[\"shape\"])\n",
         "                                           _LLE.elo_weights(t, upd[idx].tolist()), wgt.tolist(), h[\"n_players\"], k[\"k0\"], k[\"offset\"], k[\"shape\"])   " + TAG + "\n"),
    ],
    "src/eda/predictability_diagnostic/stage3_ratings.py": [
        ("from src.eda.predictability_diagnostic import common as C  # noqa: E402\n",
         "from src.eda.predictability_diagnostic import common as C  # noqa: E402\n" + IMPORT),
        ("        h = arrays(t, mu[idx])\n",
         "        h = arrays(t, mu[idx])\n"
         "        h = _LLE.ratings_arrays(t, h)   " + TAG + "\n"),
    ],
    "src/eda/ufc_ideas/stageB_adjperf.py": [
        ("from src.eda.ufc_ideas import stageB_common as B  # noqa: E402\n",
         "from src.eda.ufc_ideas import stageB_common as B  # noqa: E402\n" + IMPORT),
        ("        Z[(s, ch)] = z\n    del mom\n    feats = {}\n",
         "        Z[(s, ch)] = z\n"
         "    Z = _LLE.forms_z(ctx, chosen, Z)   " + TAG + "\n"
         "    del mom\n    feats = {}\n"),
        ("            sums = ctx.step3([Z[(s, ch)]], units, ok & (ctx.tour_box == t), c[\"tau\"], (c[\"h3\"],))\n",
         "            sums = _LLE.forms_step3(ctx, s, ch, [Z[(s, ch)]], units, ok & (ctx.tour_box == t), c[\"tau\"], (c[\"h3\"],))   " + TAG + "\n"),
        ("    grid, chosen, brief = tune(ctx)\n",
         "    grid, chosen, brief = tune(ctx)\n"
         "    chosen = _LLE.pin(\"stageB_adjperf\", chosen)   " + TAG + "\n"),
    ],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def is_sandbox(sb: Path) -> bool:
    sb = Path(sb)
    if not sb.exists() or sb.resolve() == ROOT.resolve() or sb.resolve() == FIRST_RUN_SANDBOX.resolve():
        return False
    return (sb / "src").is_dir() and (sb / "data" / "studies").is_dir()


def refuse(sb: Path) -> None:
    if Path(sb).resolve() == ROOT.resolve():
        raise SystemExit(f"{sb} is the repository: the system's patches are never applied to it")
    if Path(sb).resolve() == FIRST_RUN_SANDBOX.resolve():
        raise SystemExit(f"{sb} is the first run's sandbox: read-only for this run")
    if not is_sandbox(sb):
        raise SystemExit(f"{sb} is not a sandbox (no src/ and data/studies/)")


# ------------------------------------------------------------------------------------------------
# Applying and checking C1's patches

def normalize(text: str) -> str:
    """A builder's text with the study's sandbox tags (C1's and C2's) written as the integrated ones: the code is the
    same, only the comments differ."""
    from src.eda.lower_level_evidence import level_layer_ios as C2
    for old, new in ((OLD_TAG, TAG), (C2.OLD_TAG, C2.TAG)):
        text = text.replace(old[2:], new[2:])               # the tag also sits after "# noqa: E402  " on imports
    return text


# Edits made to hooked builders after G1 validated them, each moving no value on data to 2026: the 2027 fix of 10 Oct
# 2026 (docs/studies/daily_update_speed/): seasons after 2026 no longer fall out of Stage 1's per-season fits and
# Stage 4's pool.
POST_VALIDATION = {
    "src/eda/predictability_diagnostic/stage1_baselines.py": [(
        "    for tour in C.TOURS:\n        for year in C.EVAL_YEARS:\n",
        "    seasons = sorted(set(C.EVAL_YEARS) | set(m.loc[m[\"evaluation\"], \"year\"].astype(int)))   # and any later "
        "season held\n    for tour in C.TOURS:\n        for year in seasons:\n")],
    "src/eda/predictability_diagnostic/stage4_features.py": [(
        '    """Per match: an evaluation-level match of 2010-2026, completed or retired (the walk-forward fits\' pool)."""\n'
        "    a = rows.iloc[0::2]\n    return (a[\"level\"].isin(C.EVAL_LEVELS) & a[\"status\"].isin(C.EVAL_STATUSES)\n"
        "            & a[\"year\"].between(C.FIRST_YEAR, C.EVAL_YEARS[-1])).to_numpy()\n",
        '    """Per match: an evaluation-level match of 2010 on, completed or retired (the walk-forward fits\' pool). No last\n'
        '    season since 10 Oct 2026 (it was 2026)."""\n'
        "    a = rows.iloc[0::2]\n    return (a[\"level\"].isin(C.EVAL_LEVELS) & a[\"status\"].isin(C.EVAL_STATUSES)\n"
        "            & a[\"year\"].ge(C.FIRST_YEAR)).to_numpy()\n")],
}


def validated_now(text: str, rel: str) -> str:
    """The validated snapshot's text of a hooked builder as the repository should now hold it: the tags mapped
    (normalize) and the post-validation edits applied, each found exactly once."""
    out = normalize(text)
    for old, new in POST_VALIDATION.get(rel, []):
        if out.count(old) != 1:
            raise ValueError(f"{rel}: a post-validation edit's original text is not found exactly once")
        out = out.replace(old, new)
    return out


def integrated(text: str, rel: str) -> bool:
    """Whether a builder's text already carries every C1 edit exactly once (the repository's since 10 Oct 2026). A text
    carrying some edits but not all is refused: it is neither the decided builder nor the hooked one."""
    present = [text.count(repl) == 1 for _, repl in PATCH_SPECS[rel]]
    if all(present):
        return True
    if any(present):
        raise SystemExit(f"{rel}: carries {sum(present)} of {len(present)} of C1's edits")
    return False


def patched_text(original: str, rel: str) -> str:
    """The repository file with every C1 patch applied; refuses an anchor not found exactly once. A file that already
    carries every edit (the integrated builders) is returned as it is."""
    if integrated(original, rel):
        return original
    s = original
    for anchor, repl in PATCH_SPECS[rel]:
        n = s.count(anchor)
        if n != 1:
            raise SystemExit(f"{rel}: an anchor is found {n} times, not once; nothing patched\n{anchor[:200]}")
        s = s.replace(anchor, repl)
    return s


def unpatched_text(text: str, rel: str) -> str:
    """The decided builder without C1's edits: each edit undone, in reverse order (the tests compare the hooked passes
    with the originals this gives)."""
    s = normalize(text)
    if not integrated(s, rel):
        return s
    for anchor, repl in reversed(PATCH_SPECS[rel]):
        if s.count(repl) != 1:
            raise SystemExit(f"{rel}: an edit is found {s.count(repl)} times, not once")
        s = s.replace(repl, anchor)
    return s


def apply_patch(sandbox) -> dict:
    """C1's patches on a sandbox: the layer copied in, each builder patched from the REPOSITORY's text (so a file already
    patched by an earlier call is rewritten to the same content). Writes the diffs. Returns a record."""
    sb = Path(sandbox)
    refuse(sb)
    rec = {"copied": {}, "patched": {}}
    for rel in COPIED:
        shutil.copy2(ROOT / rel, sb / rel)
        rec["copied"][rel] = sha256(sb / rel)
    PATCHES.mkdir(parents=True, exist_ok=True)
    texts = {}
    for rel in PATCH_SPECS:                                   # check every file before writing any
        repo_text = (ROOT / rel).read_text(encoding="utf-8")
        sb_text = (sb / rel).read_text(encoding="utf-8")
        want = patched_text(repo_text, rel)
        if sb_text not in (repo_text, want):
            raise SystemExit(f"{rel}: the sandbox's copy is neither the repository's file nor C1's patched version "
                             "(edited since the setup?); nothing written")
        texts[rel] = (repo_text, sb_text, want)
    alldiff = []
    for rel, (repo_text, sb_text, want) in texts.items():
        if sb_text != want:
            (sb / rel).write_text(want, encoding="utf-8")
        diff = list(difflib.unified_diff(repo_text.splitlines(keepends=True), want.splitlines(keepends=True),
                                         fromfile=f"repository/{rel}", tofile=f"sandbox/{rel}"))
        if diff:                       # integrated builders: nothing to patch, and the study's diffs are kept as they are
            (PATCHES / (Path(rel).stem + ".diff")).write_text("".join(diff), encoding="utf-8")
        alldiff += diff
        rec["patched"][rel] = {"repository_sha256": hashlib.sha256(repo_text.encode("utf-8")).hexdigest(),
                               "sandbox_sha256": sha256(sb / rel), "integrated_in_repository": want == repo_text,
                               "lines_changed": sum(1 for x in diff if x[:1] in "+-" and not x.startswith(("+++", "---")))}
    if alldiff:
        (PATCHES / "c1_all.diff").write_text("".join(alldiff), encoding="utf-8")
    return rec


def check_patch(sandbox) -> dict:
    """Every C1 patch present exactly once in the sandbox, the rest of each file the repository's, and the layer file
    the repository's."""
    sb = Path(sandbox)
    out = {"files": {}, "copied_equal": {}}
    for rel in COPIED:
        out["copied_equal"][rel] = (sb / rel).exists() and sha256(sb / rel) == sha256(ROOT / rel)
    for rel in PATCH_SPECS:
        want = patched_text((ROOT / rel).read_text(encoding="utf-8"), rel)
        got = (sb / rel).read_text(encoding="utf-8")
        out["files"][rel] = {"equals_patched_repository_file": got == want,
                             "replacements_present_once": all(got.count(r) == 1 for _, r in PATCH_SPECS[rel])}
    out["pass"] = bool(all(out["copied_equal"].values())
                       and all(v["equals_patched_repository_file"] and v["replacements_present_once"]
                               for v in out["files"].values()))
    return out


# ------------------------------------------------------------------------------------------------
# C2's patches (level_layer_ios.apply_patch / check_patch), when they exist

def c2_module():
    """C2's module (the repository's), imported only once C2 has written READY_ios_hooks.txt."""
    p = ROOT / "src" / "eda" / "lower_level_evidence" / "level_layer_ios.py"
    if not p.exists() or not c2_ready():
        return None
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module("src.eda.lower_level_evidence.level_layer_ios")


def c2_ready() -> bool:
    return (ARMS / "READY_ios_hooks.txt").exists()


# ------------------------------------------------------------------------------------------------

def check_tables() -> dict:
    """The repository's live tables (which a new sandbox copies) against the frozen reference's hashes."""
    import pandas as pd
    files = pd.read_csv(ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" /
                        "files.csv.gz")
    t = files[files["role"].isin(["tables", "tables, later version"])]
    bad = []
    for r in t.itertuples(index=False):
        p = ROOT / r.source
        if not p.exists() or sha256(p) != r.sha256:
            bad.append(r.source)
    return {"checked": int(len(t)), "differing_or_missing": bad, "pass": not bad}


def next_free() -> int:
    k = 1
    while Path(f"{SANDBOX_STEM}{k}").exists():
        k += 1
    return k


def setup(n: int | None) -> Path:
    k = n if n is not None else next_free()
    sb = Path(f"{SANDBOX_STEM}{k}")
    if sb.exists():
        raise SystemExit(f"{sb} exists")
    tab = check_tables()
    if not tab["pass"]:
        raise SystemExit(f"the live tables differ from the frozen reference: {tab['differing_or_missing'][:5]}")
    env = {**os.environ, "MODEL_REBUILD_SANDBOX": str(sb)}
    done = subprocess.run(["bash", str(PY_SHIM), "src/eda/model_rebuild/run_chain.py", "--setup", "--candidate"],
                          cwd=ROOT, env=env)
    if done.returncode != 0:
        raise SystemExit(f"setup of {sb} failed ({done.returncode})")
    print(f"sandbox {sb} set up; tables {tab}")
    return sb


CANDIDATE_FILES = {   # role F's candidate Stage 0 (system/stage0/<name>/) -> the sandbox's table it replaces
    "stage0_matches.parquet": "data/studies/predictability_diagnostic/stage0_matches.parquet",
    "stage0_match_players.parquet": "data/studies/predictability_diagnostic/stage0_match_players.parquet",
    "timing.parquet": "data/studies/match_timing/timing.parquet",
}


def put_candidate_stage0(sb: Path, cand_dir: Path) -> dict:
    """A candidate Stage 0 (and its own timeline) copied over the sandbox's tables, before the patch and the lanes; the
    build then runs lane 0 (system_arms.lane_plan). Refuses a candidate whose READY.txt is missing. The repository's
    live tables are never touched."""
    cand_dir = Path(cand_dir)
    if not (cand_dir / "READY.txt").exists():
        raise SystemExit(f"{cand_dir}: no READY.txt; the candidate Stage 0 is not ready")
    rec = {"source": str(cand_dir), "files": {}, "timing": False}
    for name, rel in CANDIDATE_FILES.items():
        src = cand_dir / name
        if not src.exists():
            if name == "timing.parquet":
                continue
            raise SystemExit(f"{src} is missing")
        dst = sb / rel
        before = sha256(dst) if dst.exists() else None
        shutil.copy2(src, dst)
        rec["files"][rel] = {"source_sha256": sha256(src), "replaced_sha256": before, "sandbox_sha256": sha256(dst)}
        rec["timing"] |= name == "timing.parquet"
    for extra in ("manifest.json", "READY.txt"):
        if (cand_dir / extra).exists():
            rec[extra] = sha256(cand_dir / extra)
    return rec


def patch(sandbox, stage0: str | None = None) -> dict:
    sb = Path(sandbox)
    refuse(sb)
    reg = sb / "data" / "studies" / "ios_constants" / "versions" / f"{IOS_VERSION}.json"
    if not reg.exists():
        raise SystemExit(f"{reg} is missing: IOS_CONSTANTS_VERSION={IOS_VERSION} cannot be pinned")
    rec = {"sandbox": str(sb), "IOS_CONSTANTS_VERSION": IOS_VERSION, "ios_version_file_sha256": sha256(reg)}
    old = json.loads((sb / "LLE_SYSTEM.json").read_text(encoding="utf-8")) if (sb / "LLE_SYSTEM.json").exists() else {}
    if stage0:
        rec["candidate_stage0"] = put_candidate_stage0(sb, Path(stage0))
    elif old.get("candidate_stage0"):
        rec["candidate_stage0"] = old["candidate_stage0"]          # a re-patch keeps the candidate's tables
    rec["c1"] = apply_patch(sb)
    rec["c1_check"] = check_patch(sb)
    mod = c2_module()
    if mod is not None and hasattr(mod, "apply_patch"):
        rec["c2"] = {"module": "src/eda/lower_level_evidence/level_layer_ios.py",
                     "module_sha256": sha256(ROOT / "src/eda/lower_level_evidence/level_layer_ios.py"),
                     "ready_file": c2_ready()}
        res = mod.apply_patch(sb)
        rec["c2"]["apply"] = res if isinstance(res, (dict, list, str, bool, type(None))) else str(res)
        chk = mod.check_patch(sb) if hasattr(mod, "check_patch") else None
        rec["c2"]["check"] = chk if isinstance(chk, (dict, list, str, bool, type(None))) else str(chk)
        # C2's patches must leave C1's in place
        rec["c1_check_after_c2"] = check_patch(sb)
    else:
        rec["c2"] = None
    import datetime as _dt
    rec["patched_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    (sb / "LLE_SYSTEM.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--setup", action="store_true")
    g.add_argument("--patch", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--tables", action="store_true")
    ap.add_argument("--sandbox")
    ap.add_argument("--n", type=int)
    ap.add_argument("--stage0", help="with --patch: a candidate Stage 0 folder (role F's system/stage0/<name>/) copied "
                                     "over the sandbox's tables first (phase 3)")
    a = ap.parse_args()
    if a.tables:
        print(json.dumps(check_tables(), indent=1))
        return 0
    if a.setup:
        setup(a.n)
        return 0
    if not a.sandbox:
        raise SystemExit("--sandbox is required")
    if a.patch:
        rec = patch(a.sandbox, a.stage0)
        print(json.dumps({k: rec[k] for k in ("sandbox", "IOS_CONSTANTS_VERSION", "c1_check")}, indent=1, default=str))
        print("C2:", "applied" if rec.get("c2") else "not applied (READY_ios_hooks.txt absent)")
        if rec.get("candidate_stage0"):
            print("candidate Stage 0:", json.dumps(rec["candidate_stage0"], indent=1))
        return 0 if rec["c1_check"]["pass"] else 1
    res = {"c1": check_patch(a.sandbox)}
    mod = c2_module()
    if mod is not None and hasattr(mod, "check_patch"):
        res["c2"] = mod.check_patch(Path(a.sandbox))
    print(json.dumps(res, indent=1, default=str))
    return 0 if res["c1"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
