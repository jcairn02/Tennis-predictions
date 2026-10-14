"""The NEW arms of pre-registration addition 1 (role C1), as the lead's addition 3 (section 4) builds them, on role F's
candidate Stage 0s (system/stage0/C0_now, C0_pre). New code only: the frozen layer (level_layer.py), C2's module and C1's
SYS-family patches (system_sandbox.py) keep addition 3's hashes.

    NEW_ASIS      the identity config on C0_now, every tuned constant pinned to the reference's: Stage 1's Elo K and
                  surface weight, the offset Elo's kd (both kinds), Stage 3's constants (level_pins.py), Stage B's
                  (the layer's pin), IOS_CONSTANTS_VERSION=2026-10-08_reference (the environment)
    NEW_ASIS_PRE  the same on C0_pre
    NEW_SYS_BOTH  SYS_BOTH's config on C0_now (B's frozen parameters, ITF box rows excluded, the caps), the constants
                  pinned likewise, the opponent strength from the unweighted pre-match Elo on C0_now under the reference
                  K (written by --strength from NEW_ASIS's Stage 1, in strength_elo.parquet's format, hashed)

    --patch --sandbox D --stage0 F   system_sandbox.patch(D, F) (F's tables over D's, C1's and C2's patches), then the
                  pins: level_pins.py copied in and three anchored edits on top of C1's (PIN_SPECS); LLE_SYSTEM.json
                  gains "pins"
    --check --sandbox D              C1's patches with the pins, C2's, the copied modules
    --lane0-check --sandbox D        after lane 0's stage1_odds, before lane 1 (F's notes): the odds table against the
                  frozen file, and the 67,226 frame matches unchanged in the candidate's Stage 0
    --strength --from D --name N     the strength file arms/strength/<N>.parquet (+ .sha256) from D's Stage 1
Run: ./python.sh src/eda/lower_level_evidence/system_new_arms.py --patch --sandbox C:/Users/zerom/tnr_sysK --stage0 <F>
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.lower_level_evidence import system_sandbox as SB  # noqa: E402

SYSTEM = LC.OUT / "system"
ARMS = SYSTEM / "arms"
PINS_MODULE = "src/eda/lower_level_evidence/level_pins.py"
PIN_TAG = "# lower_level_evidence C1 pins (sandbox only)"
PIN_IMPORT = ("from src.eda.lower_level_evidence import level_pins as _LLEPIN  "
              + PIN_TAG.replace("# ", "# noqa: E402  ", 1) + "\n")
REF_CONSTANTS = ARMS / "constants" / "reference_constants.json"
FROZEN = LC.REF                                         # the frozen reference (files.csv.gz, tables/, instance/)

# file -> [(anchor in C1's patched text, replacement)]; each anchor found exactly once
PIN_SPECS: dict[str, list[tuple[str, str]]] = {
    "src/eda/predictability_diagnostic/stage1_baselines.py": [
        (SB.IMPORT, SB.IMPORT + PIN_IMPORT),
        ("            k = {c: float(best[c]) for c in (\"k0\", \"offset\", \"shape\")}\n",
         "            k = {c: float(best[c]) for c in (\"k0\", \"offset\", \"shape\")}\n"
         "            k = _LLEPIN.stage1_k(tour, rule, k)   " + PIN_TAG + "\n"),
        ("            w = float(wg.loc[wg[\"log_loss_2013_2018\"].idxmin(), \"w\"])\n",
         "            w = float(wg.loc[wg[\"log_loss_2013_2018\"].idxmin(), \"w\"])\n"
         "            w = _LLEPIN.stage1_w(tour, rule, w)   " + PIN_TAG + "\n"),
    ],
    "src/eda/surface_elo_pieces/pieces.py": [
        (SB.IMPORT, SB.IMPORT + PIN_IMPORT),
        ("        kd, grid = tune_offset(t, h, upd0, k)   " + SB.TAG + "\n",
         "        kd, grid = tune_offset(t, h, upd0, k)   " + SB.TAG + "\n"
         "        kd = _LLEPIN.offset_kd(\"offset\", tour, kd)   " + PIN_TAG + "\n"),
        ("        kd_gen, grid_gen = tune_offset(t, h_gen, upd0, k)   " + SB.TAG + "\n",
         "        kd_gen, grid_gen = tune_offset(t, h_gen, upd0, k)   " + SB.TAG + "\n"
         "        kd_gen = _LLEPIN.offset_kd(\"offset_surface_blind\", tour, kd_gen)   " + PIN_TAG + "\n"),
    ],
    "src/eda/predictability_diagnostic/stage3_ratings.py": [
        (SB.IMPORT, SB.IMPORT + PIN_IMPORT),
        ("    chosen, grid = tune(m, mu)\n",
         "    chosen, grid = tune(m, mu)\n"
         "    chosen = _LLEPIN.stage3(chosen)   " + PIN_TAG + "\n"),
    ],
}


def sha256(path: Path) -> str:
    return SB.sha256(Path(path))


def c1_text(rel: str) -> str:
    """The repository's builder with C1's SYS-family patches (system_sandbox.PATCH_SPECS), as every sandbox holds it."""
    return SB.patched_text((ROOT / rel).read_text(encoding="utf-8"), rel)


def pinned_text(rel: str) -> str:
    """C1's patched builder with the pins on top; refuses an anchor not found exactly once."""
    s = c1_text(rel)
    for anchor, repl in PIN_SPECS[rel]:
        n = s.count(anchor)
        if n != 1:
            raise SystemExit(f"{rel}: a pin anchor is found {n} times, not once; nothing patched\n{anchor[:200]}")
        s = s.replace(anchor, repl)
    return s


def unpin(sandbox: Path) -> None:
    """A pinned builder back to C1's text, so that system_sandbox.patch (which accepts only the repository's text or
    C1's) can re-patch the sandbox; the pins are applied again right after."""
    for rel in PIN_SPECS:
        p = Path(sandbox) / rel
        if p.read_text(encoding="utf-8") == pinned_text(rel):
            p.write_text(c1_text(rel), encoding="utf-8")


def apply_pins(sandbox: Path) -> dict:
    sb = Path(sandbox)
    SB.refuse(sb)
    rec = {"module": PINS_MODULE, "patched": {}}
    shutil.copy2(ROOT / PINS_MODULE, sb / PINS_MODULE)
    rec["module_sha256"] = sha256(sb / PINS_MODULE)
    alldiff = []
    for rel in PIN_SPECS:
        cur = (sb / rel).read_text(encoding="utf-8")
        want = pinned_text(rel)
        if cur not in (c1_text(rel), want):
            raise SystemExit(f"{sb / rel}: neither C1's patched text nor the pinned one; nothing written")
        if cur != want:
            (sb / rel).write_text(want, encoding="utf-8")
        diff = list(difflib.unified_diff(c1_text(rel).splitlines(keepends=True), want.splitlines(keepends=True),
                                         fromfile=f"c1/{rel}", tofile=f"pinned/{rel}"))
        alldiff += diff
        rec["patched"][rel] = sha256(sb / rel)
    SB.PATCHES.mkdir(parents=True, exist_ok=True)
    (SB.PATCHES / "pins_all.diff").write_text("".join(alldiff), encoding="utf-8")
    return rec


def check_patch(sandbox) -> dict:
    """C1's patches with the pins: system_sandbox.check_patch for the builders without pins, the pinned text for the
    three with them, and the pin module the repository's."""
    sb = Path(sandbox)
    out = SB.check_patch(sb)
    for rel in PIN_SPECS:
        got = (sb / rel).read_text(encoding="utf-8")
        out["files"][rel] = {"equals_pinned_c1_text": got == pinned_text(rel),
                             "pins_present_once": all(got.count(r) == 1 for _, r in PIN_SPECS[rel])}
    out["copied_equal"][PINS_MODULE] = (sb / PINS_MODULE).exists() and sha256(sb / PINS_MODULE) == sha256(
        ROOT / PINS_MODULE)
    out["pass"] = bool(all(out["copied_equal"].values()) and all(all(v.values()) for v in out["files"].values()))
    return out


def patch(sandbox, stage0: str) -> dict:
    sb = Path(sandbox)
    SB.refuse(sb)
    if (sb / PINS_MODULE).exists():
        unpin(sb)
    rec = SB.patch(sb, stage0)
    rec["pins"] = apply_pins(sb)
    rec["pins_check"] = check_patch(sb)
    (sb / "LLE_SYSTEM.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    return rec


# ------------------------------------------------------------------------------------------------
# F's lane-0 notes: before lane 1

def lane0_check(sandbox) -> dict:
    """After lane 0's stage1_odds (the timeline step skipped: F brings timing.parquet): Stage 1's odds table against
    the frozen file, and the frame's 67,226 matches unchanged in the candidate's Stage 0 (every column)."""
    sb = Path(sandbox)
    pd_ = "data/studies/predictability_diagnostic/"
    out = {}
    files = pd.read_csv(FROZEN / "files.csv.gz")
    row = files.loc[files["source"].eq(pd_ + "stage1_odds.parquet")].iloc[0]
    odds_sb, odds_fr, want = sb / (pd_ + "stage1_odds.parquet"), FROZEN / row["frozen"], row["sha256"]
    got = sha256(odds_sb)
    out["stage1_odds"] = {"sandbox_sha256": got, "frozen_sha256": want, "bytes_equal": got == want}
    if got != want:
        # the content on the frozen rows (a new match has no odds row, by F's design)
        fr = pd.read_parquet(odds_fr) if odds_fr.exists() else None
        if fr is not None:
            s = pd.read_parquet(odds_sb)
            keys = [c for c in ("match_id",) if c in fr.columns]
            same = (len(s) == len(fr) and s.reset_index(drop=True).equals(fr.reset_index(drop=True)))
            out["stage1_odds"].update({"rows_sandbox": int(len(s)), "rows_frozen": int(len(fr)), "content_equal": same,
                                       "key": keys})
    m_sb = pd.read_parquet(sb / (pd_ + "stage0_matches.parquet"))
    m_fr = pd.read_parquet(FROZEN / files.loc[files["source"].eq(pd_ + "stage0_matches.parquet"), "frozen"].iloc[0])
    frame_ids = pd.read_parquet(LC.FRAME, columns=["match_id"])["match_id"].astype(str)
    a = m_fr[m_fr["match_id"].astype(str).isin(frame_ids)].set_index("match_id").sort_index()
    b = m_sb[m_sb["match_id"].astype(str).isin(frame_ids)].set_index("match_id").sort_index()
    cols = [c for c in a.columns if c in b.columns]
    out["frame_matches"] = {"frame_ids": int(len(frame_ids)), "in_frozen": int(len(a)), "in_candidate": int(len(b)),
                            "columns_compared": len(cols), "columns_only_frozen": sorted(set(a.columns) - set(b.columns)),
                            "columns_only_candidate": sorted(set(b.columns) - set(a.columns))}
    same_ids = a.index.equals(b.index)
    # "order" is Stage 0's global chronological index: the candidate's new matches interleave, so its values shift;
    # what must hold is the frame matches' relative order
    diff_cols = [] if not same_ids else [c for c in cols if c != "order" and not a[c].equals(b[c])]
    if same_ids and "order" in cols:
        out["frame_matches"]["order"] = {"values_equal": bool(a["order"].equals(b["order"])),
                                         "relative_order_equal": bool((a["order"].rank(method="first").to_numpy()
                                                                       == b["order"].rank(method="first").to_numpy()
                                                                       ).all())}
        if not out["frame_matches"]["order"]["relative_order_equal"]:
            diff_cols.append("order (relative)")
    out["frame_matches"].update({"same_ids": bool(same_ids), "columns_differing": diff_cols})
    out["pass"] = bool((out["stage1_odds"]["bytes_equal"] or out["stage1_odds"].get("content_equal"))
                       and same_ids and len(a) == len(frame_ids) and not diff_cols)
    return out


# ------------------------------------------------------------------------------------------------
# NEW_SYS_BOTH's strength

def strength(source_sandbox, name: str) -> dict:
    """arms/strength/<name>.parquet from a sandbox's Stage 1 (stage1_baselines.parquet: the pre-match overall Elo,
    retirements counted), in strength_elo.parquet's columns, with its sha256 beside it. Checked against the reference
    strength on every match dated before the candidate's first new match (those ratings cannot have moved)."""
    src = Path(source_sandbox) / "data" / "studies" / "predictability_diagnostic" / "stage1_baselines.parquet"
    ref = pd.read_parquet(SYSTEM / "classes" / "strength_elo.parquet")
    cols = list(ref.columns)
    b = pd.read_parquet(src, columns=cols)
    dst = ARMS / "strength" / f"{name}.parquet"
    if dst.exists():
        raise SystemExit(f"{dst} exists")
    m = pd.read_parquet(Path(source_sandbox) / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet",
                        columns=["match_id", "tournament_date"])
    new = ~m["match_id"].isin(ref["match_id"])
    first_new = pd.to_datetime(m.loc[new, "tournament_date"]).min()
    j = ref.merge(b, on="match_id", suffixes=("_ref", ""))
    j = j.merge(m, on="match_id")
    early = (pd.to_datetime(j["tournament_date"]) < first_new) if pd.notna(first_new) else pd.Series(True, index=j.index)
    gap = np.nanmax(np.abs(j.loc[early, ["elo_a_ret", "elo_b_ret"]].to_numpy("float64")
                           - j.loc[early, ["elo_a_ret_ref", "elo_b_ret_ref"]].to_numpy("float64"))) if early.any() else 0.0
    chk = {"rows": int(len(b)), "new_matches": int(new.sum()), "reference_matches_found": int(len(j)),
           "first_new_match_date": str(first_new.date()) if pd.notna(first_new) else None,
           "matches_before_it": int(early.sum()), "largest_difference_before_it": float(gap),
           "missing_ratings": int(b[["elo_a_ret", "elo_b_ret"]].isna().to_numpy().sum())}
    if gap != 0.0 or len(j) != len(ref) or chk["missing_ratings"]:
        raise SystemExit(f"the strength from {src} fails its checks: {chk}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    b.to_parquet(dst, index=False, compression="zstd")
    h = sha256(dst)
    dst.with_suffix(".parquet.sha256").write_text(f"{h} *{dst.name}\n", encoding="utf-8")
    rec = {"path": str(dst), "sha256": h, "source": str(src), "source_sha256": sha256(src), "checks": chk}
    (dst.with_suffix(".json")).write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    return rec


def strength_centred(name: str, out_name: str, keep_reference: bool = False) -> dict:
    """The strength file <name> moved to the reference's Elo scale (offered to the lead at 10:1x UTC: C0_now's added
    matches move the plain Elo's scale, +75 to +92 for women in every season, up to +85 for men by 2024, while B's
    strength_ref is on the reference's): per tour and season, the mean over the reference's main-tour matches of the
    new pre-match rating minus the reference's (both players) is subtracted from every match of that tour and season.
    keep_reference: the reference strength itself for every match it covers, the re-centred value for the new ones."""
    ref = pd.read_parquet(SYSTEM / "classes" / "strength_elo.parquet")
    src = ARMS / "strength" / f"{name}.parquet"
    side = src.with_suffix(".parquet.sha256").read_text(encoding="utf-8").split()[0]
    if sha256(src) != side:
        raise SystemExit(f"{src}: sha256 differs from its .sha256 file")
    new = pd.read_parquet(src)
    m = LC.load_matches(columns=["match_id", "tour", "year", "map_level"])
    cand = pd.read_parquet(Path(json.loads(src.with_suffix(".json").read_text(encoding="utf-8"))["source"]).parents[0]
                           / "stage0_matches.parquet", columns=["match_id", "tour", "year"])
    j = ref.merge(new, on="match_id", suffixes=("_ref", "")).merge(m, on="match_id")
    j = j[j["bucket"] == "MAIN"]
    j["d"] = ((j["elo_a_ret"] - j["elo_a_ret_ref"]) + (j["elo_b_ret"] - j["elo_b_ret_ref"])) / 2.0
    shift = j.groupby(["tour", "year"])["d"].mean()
    out = new.merge(cand, on="match_id", how="left")
    if out[["tour", "year"]].isna().any().any():
        raise SystemExit("matches of the strength file are missing from the candidate's Stage 0")
    s = shift.reindex(pd.MultiIndex.from_frame(out[["tour", "year"]])).to_numpy(dtype="float64")
    if np.isnan(s).any():                                  # a season without main-tour matches: the nearest season's
        filled = shift.groupby(level=0).apply(lambda x: x.droplevel(0).reindex(range(int(out["year"].min()),
                                                                                     int(out["year"].max()) + 1))
                                              .interpolate(limit_direction="both"))
        s = filled.reindex(pd.MultiIndex.from_frame(out[["tour", "year"]])).to_numpy(dtype="float64")
    for c in ("elo_a_ret", "elo_b_ret"):
        out[c] = (out[c].to_numpy(dtype="float64") - s).astype(new[c].dtype)
    out = out[list(new.columns)]
    if keep_reference:
        r = ref.set_index("match_id")
        hit = out["match_id"].isin(r.index)
        for c in ("elo_a_ret", "elo_b_ret", "n_a_ret", "n_b_ret"):
            if c in r.columns:
                out.loc[hit, c] = r[c].reindex(out.loc[hit, "match_id"]).to_numpy()
    dst = ARMS / "strength" / f"{out_name}.parquet"
    if dst.exists():
        raise SystemExit(f"{dst} exists")
    out.to_parquet(dst, index=False, compression="zstd")
    h = sha256(dst)
    dst.with_suffix(".parquet.sha256").write_text(f"{h} *{dst.name}\n", encoding="utf-8")
    rec = {"path": str(dst), "sha256": h, "from": str(src), "from_sha256": side, "keep_reference": keep_reference,
           "shift_by_tour_season": {f"{t}|{y}": round(float(v), 3) for (t, y), v in shift.items()}}
    dst.with_suffix(".json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--patch", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--lane0-check", action="store_true")
    g.add_argument("--strength", action="store_true")
    ap.add_argument("--sandbox")
    ap.add_argument("--stage0")
    ap.add_argument("--from", dest="source")
    ap.add_argument("--name")
    a = ap.parse_args()
    if a.strength:
        print(json.dumps(strength(a.source, a.name), indent=1, default=str))
        return 0
    if a.patch:
        if not a.stage0:
            raise SystemExit("--stage0 is required: the NEW arms are built on a candidate Stage 0")
        rec = patch(a.sandbox, a.stage0)
        print(json.dumps({"c1_check": rec["c1_check"]["pass"], "c2": bool(rec.get("c2")),
                          "pins_check": rec["pins_check"]["pass"],
                          "candidate_stage0": rec.get("candidate_stage0", {}).get("source")}, indent=1))
        return 0 if rec["pins_check"]["pass"] else 1
    if a.check:
        res = check_patch(a.sandbox)
        print(json.dumps(res, indent=1, default=str))
        return 0 if res["pass"] else 1
    res = lane0_check(a.sandbox)
    print(json.dumps(res, indent=1, default=str))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
