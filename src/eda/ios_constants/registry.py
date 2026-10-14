"""The IOS constants registry: every constant the IOS inputs are built with, kept in versions that are hashed and never
edited, and a pointer to the version in use. A later change is a new version; reverting it is activating the old one.

Why (8 Oct 2026). The constants were spread over two study outputs and a line of code:
    Stage B's h, kappa, tau and the typical units   data/studies/ufc_ideas/stageB_ios_summary.json, which stageB_ios.py
                                                    rewrites whenever it runs (the template's build chain runs it in
                                                    lane 1 while lane 2 reads the file)
    the surface IOS's penalties                     data/studies/surface_ios/tuning_choice.json (summarise_tuning.py)
    the short memory, 4 weeks (men) and 13 (women)  hard-coded in match_timing/rebuild.py
So re-running a tuning study could change the model's inputs without anyone deciding it, and no build recorded which
constants it used. The model's IOS builders now read the version in effect here, and record it. The tuning studies still
write their own outputs; those reach the model only when added as a version and activated.

A version (data/studies/ios_constants/versions/<id>.json), keyed "tour|stat" over both tours and the eight statistics:
    base            Stage B's tuning (2013-2018): the half-life h in weeks ("inf": no decay), the ridge kappa in typical
                    matches and the units weight tau (0 or 1). The pooled and the surface IOS both use them
    typical_units   the mean units of a box-score match, 2010-2018: the units weights' reference
    short_memory_h  per tour: the half-life of the short-memory IOS points matchup (ios_points_short), which takes spw's
                    kappa and tau
    surface         the surface IOS: its variant (shared, return_only or pooled), the half-life multiplier, and the surface
                    penalties as multiples of kappa, kE on the serve side and kF on the return side ("inf": no surface term)
    sources         where each block came from, with the file's SHA-256 then. Also the fingerprint of the surface averages
                    the IOS is centred on: Stage 3's, which the builders read from stage4_constants.csv themselves (every
                    family shares them), so they are recorded here, not served; check() compares them
    sha256          of the four blocks as canonical JSON. Every load recomputes it and refuses a mismatch. The pointer holds
                    it too, so a version edited after its activation is refused even with its own hash redone
active.json holds the version in use and every activation with its reason. IOS_CONSTANTS_VERSION, when set, overrides the
pointer for a process and its children: pin() sets it at a build's start so every worker reads one version, and a
candidate build can set it to try a version without moving the pointer.

Readers: match_timing/rebuild.py (the leak-proof IOS profile and the short-memory points matchup) and the surface IOS
(surface_ios/common.ios_constants, build_features.py). Closed studies keep their own copies, the record of what they ran
(ufc_ideas/stageB_rundown.py, feature_alpha_audit/repair_features.py, feature_interactions/features/f28_state.py).

Commands:
    --show [ID]                  a version's constants (default: the one in effect)
    --list                       every version, the active one marked
    --verify                     every version's hash and the pointer's; exit 1 on a mismatch
    --check                      the version in effect against the tuning outputs on disk now (Stage B's summary, the
                                 surface tuning's choice) and the surface averages: what adding them as a version would
                                 change. Informational: exit 0
    --add ID --note TEXT         a new version: the active one (or --from ID) with the blocks given replaced
          [--base-from FILE]         base and typical_units from a Stage B summary (stageB_ios_summary.json's format)
          [--surface-from FILE]      surface from a surface tuning choice (tuning_choice.json's format)
          [--short-h atp=W wta=W]    short_memory_h, in weeks
    --activate ID --reason TEXT  the builders' version from now on; reverting is activating an earlier one
Run: ./python.sh src/eda/ios_constants/registry.py --show
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REG = ROOT / "data" / "studies" / "ios_constants"
STAGEB_SUMMARY = ROOT / "data" / "studies" / "ufc_ideas" / "stageB_ios_summary.json"
SURFACE_CHOICE = ROOT / "data" / "studies" / "surface_ios" / "tuning_choice.json"
ENV = "IOS_CONSTANTS_VERSION"
TOURS = ("atp", "wta")
STATS = ("spw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
CELLS = tuple(f"{t}|{s}" for t in TOURS for s in STATS)
BLOCKS = ("base", "typical_units", "short_memory_h", "surface")
VARIANTS = ("shared", "return_only", "pooled")
ID_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]{0,79}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(constants: dict) -> str:
    """SHA-256 of the four blocks as canonical JSON (sorted keys, no spaces, floats written exactly)."""
    text = json.dumps({b: constants[b] for b in BLOCKS}, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def enc(v) -> float | str:
    """A constant as the registry writes it: a float, or "inf". The tuning outputs write infinity as "inf" (Stage B) or
    None (the surface choice's multipliers), and rebuild.py read None as infinity too."""
    if v is None or (isinstance(v, str) and v.lower() in ("inf", "infinity")):
        return "inf"
    v = float(v)
    return "inf" if v == math.inf else v


def dec(v) -> float:
    return math.inf if v == "inf" else float(v)


# ------------------------------------------------------------------------------------------------
# Blocks from the tuning outputs, and their checks

def base_from(summary: Path) -> tuple[dict, dict]:
    """base and typical_units from a Stage B summary (stageB_ios.py's chosen and typical_units)."""
    s = json.loads(Path(summary).read_text(encoding="utf-8"))
    base = {f"{r['tour']}|{r['stat']}": {"h": enc(r["h"]), "kappa": float(r["kappa"]), "tau": int(r["tau"])}
            for r in s["chosen"]}
    typ = {f"{r['tour']}|{r['stat']}": float(r["units"]) for r in s["typical_units"]}
    return base, typ


def surface_from(choice: Path) -> dict:
    """surface from a surface tuning choice (summarise_tuning.py's tuning_choice.json): the variant, the half-life
    multiplier and the penalties' multiples. Its gains are the study's evidence and stay there."""
    c = json.loads(Path(choice).read_text(encoding="utf-8"))
    return {k: {"variant": x["variant"], "h_mult": float(x["h_mult"]), "kE_mult": enc(x["kE_mult"]),
                "kF_mult": enc(x["kF_mult"])} for k, x in c.items()}


def surface_means_fingerprint() -> str:
    """SHA-256 of the surface averages the eight IOS statistics are centred on (stageB_common.surface_means: Stage 3's,
    read from stage4_constants.csv), as canonical JSON."""
    from src.eda.ufc_ideas import stageB_common as B
    means = B.surface_means()
    flat = {f"{s}|{t}|{surface}": float(v) for s in STATS for (t, surface), v in means[s].items()}
    return hashlib.sha256(json.dumps(flat, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate(constants: dict) -> None:
    """Raise ValueError unless every block has exactly its cells and fields, with usable values."""
    def num(v, what: str, inf_ok: bool = False) -> None:
        if inf_ok and v == "inf":
            return
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError(f"{what}: {v!r} is not a positive number" + (' or "inf"' if inf_ok else ""))

    def fields(block: str, cell: str, x, want: set) -> None:
        if not isinstance(x, dict) or set(x) != want:
            raise ValueError(f"{block} {cell}: needs exactly the fields {sorted(want)}")

    if set(constants) != set(BLOCKS):
        raise ValueError(f"a version holds exactly the blocks {BLOCKS}, not {sorted(constants)}")
    for b in ("base", "typical_units", "surface"):
        if set(constants[b]) != set(CELLS):
            raise ValueError(f"{b}: cells missing or unknown: {sorted(set(CELLS) ^ set(constants[b]))}")
    if set(constants["short_memory_h"]) != set(TOURS):
        raise ValueError(f"short_memory_h: needs exactly the tours {TOURS}")
    for k, x in constants["base"].items():
        fields("base", k, x, {"h", "kappa", "tau"})
        num(x["h"], f"base {k} h", inf_ok=True)
        num(x["kappa"], f"base {k} kappa")
        if isinstance(x["tau"], bool) or x["tau"] not in (0, 1) or not isinstance(x["tau"], int):
            raise ValueError(f"base {k} tau: {x['tau']!r} is not 0 or 1")
    for k, x in constants["typical_units"].items():
        num(x, f"typical_units {k}")
    for k, x in constants["short_memory_h"].items():
        num(x, f"short_memory_h {k}")
    for k, x in constants["surface"].items():
        fields("surface", k, x, {"variant", "h_mult", "kE_mult", "kF_mult"})
        if x["variant"] not in VARIANTS:
            raise ValueError(f"surface {k}: variant {x['variant']!r} is not one of {VARIANTS}")
        num(x["h_mult"], f"surface {k} h_mult")
        num(x["kE_mult"], f"surface {k} kE_mult", inf_ok=True)
        num(x["kF_mult"], f"surface {k} kF_mult", inf_ok=True)
        no_term = x["kE_mult"] == "inf" and x["kF_mult"] == "inf"
        if (x["variant"] == "pooled") != no_term or (x["variant"] == "shared" and x["kE_mult"] != x["kF_mult"]):
            raise ValueError(f"surface {k}: variant {x['variant']} does not fit kE {x['kE_mult']} and kF {x['kF_mult']}")


def ordered(constants: dict) -> dict:
    """The blocks in their reading order: cells by tour, then statistic."""
    return {"base": {k: constants["base"][k] for k in CELLS},
            "typical_units": {k: constants["typical_units"][k] for k in CELLS},
            "short_memory_h": {t: constants["short_memory_h"][t] for t in TOURS},
            "surface": {k: constants["surface"][k] for k in CELLS}}


# ------------------------------------------------------------------------------------------------
# Versions and the pointer

def load(vid: str, reg: Path = REG) -> dict:
    """A version, its hash checked against its constants."""
    if not ID_RE.fullmatch(vid or ""):
        raise ValueError(f"not a version id: {vid!r}")
    path = reg / "versions" / f"{vid}.json"
    if not path.exists():
        raise FileNotFoundError(f"no IOS constants version {vid!r} in {rel(path.parent)}")
    v = json.loads(path.read_text(encoding="utf-8"))
    if v.get("id") != vid:
        raise ValueError(f"{rel(path)} holds version {v.get('id')!r}, not {vid!r}")
    validate(v["constants"])
    got = digest(v["constants"])
    if got != v.get("sha256"):
        raise ValueError(f"{rel(path)} was edited: its constants hash to {got[:12]}, not the recorded "
                         f"{str(v.get('sha256'))[:12]}. A version is never changed; add a new one")
    return v


def versions(reg: Path = REG) -> list[dict]:
    """Every version, oldest first; one that fails its check raises."""
    return sorted((load(p.stem, reg) for p in (reg / "versions").glob("*.json")),
                  key=lambda v: (v["created_at"], v["id"]))


def pointer(reg: Path = REG) -> dict:
    path = reg / "active.json"
    if not path.exists():
        raise FileNotFoundError(f"no active IOS constants version: {rel(path)} is missing (registry.py --activate)")
    return json.loads(path.read_text(encoding="utf-8"))


def active(reg: Path = REG) -> dict:
    """The pointer's version. The hash the pointer recorded at activation must still be the version's."""
    p = pointer(reg)
    v = load(p["version"], reg)
    if v["sha256"] != p.get("sha256"):
        raise ValueError(f"active.json names {p['version']} with hash {str(p.get('sha256'))[:12]}, but the version now "
                         f"hashes to {v['sha256'][:12]}: it was changed after its activation")
    return v


def current(reg: Path = REG) -> dict:
    """The version in effect: IOS_CONSTANTS_VERSION's if set (a pinned build, or a candidate's), else the active one."""
    pinned = os.environ.get(ENV)
    v = load(pinned, reg) if pinned else active(reg)
    v["selected_by"] = ENV if pinned else "active.json"
    return v


def pin(reg: Path = REG) -> dict:
    """current(), with IOS_CONSTANTS_VERSION set to it: this process and every worker it starts read this version,
    whatever the pointer does meanwhile. A build calls it once, at its start."""
    v = current(reg)
    os.environ[ENV] = v["id"]
    return v


def record(v: dict) -> dict:
    """What a build writes into its summary: the version it read, the version's hash and how it was selected."""
    return {"version": v["id"], "sha256": v["sha256"], "selected_by": v.get("selected_by")}


def add(vid: str, note: str, base_file: Path | None = None, surface_file: Path | None = None,
        short: dict | None = None, from_id: str | None = None, reg: Path = REG) -> dict:
    """A new version: version from_id (default: the active one) with the given blocks replaced. The first version must be
    given all three. It is not activated."""
    if not ID_RE.fullmatch(vid or ""):
        raise ValueError(f"not a version id: {vid!r} (letters, digits, '.', '_', '-')")
    if not (note or "").strip():
        raise ValueError("a version needs a note: what it is and why")
    path = reg / "versions" / f"{vid}.json"
    if path.exists():
        raise FileExistsError(f"version {vid} exists; a version is never changed")
    if from_id:
        start = load(from_id, reg)
    elif (reg / "active.json").exists():
        start = active(reg)
    else:
        start = None
    if start is None and not (base_file and surface_file and short):
        raise ValueError("the first version needs --base-from, --surface-from and --short-h")
    constants = dict(start["constants"]) if start else {}
    sources = dict(start["sources"]) if start else {}
    if base_file:
        constants["base"], constants["typical_units"] = base_from(base_file)
        made = json.loads(Path(base_file).read_text(encoding="utf-8")).get("generated_at")
        sources["base"] = sources["typical_units"] = {"path": rel(base_file), "sha256": file_sha256(base_file),
                                                      "generated_at": made}
    if surface_file:
        constants["surface"] = surface_from(surface_file)
        sources["surface"] = {"path": rel(surface_file), "sha256": file_sha256(surface_file)}
    if short:
        if set(short) != set(TOURS):
            raise ValueError(f"--short-h needs exactly the tours {TOURS}")
        constants["short_memory_h"] = {t: float(short[t]) for t in TOURS}
        sources["short_memory_h"] = {"given": "--short-h, by whoever added the version (see its note)"}
    validate(constants)
    constants = ordered(constants)
    h = digest(constants)
    for other in versions(reg):
        if other["sha256"] == h:
            raise ValueError(f"these constants are version {other['id']}'s exactly: activate it instead")
    sources["surface_means_sha256"] = surface_means_fingerprint()
    v = {"id": vid, "created_at": now(), "note": note.strip(), "based_on": start["id"] if start else None,
         "sources": sources, "constants": constants, "sha256": h}
    write_json(path, v)
    return v


def activate(vid: str, reason: str, reg: Path = REG) -> dict:
    """Point the builders at a version, with the reason; the history keeps every activation."""
    if not (reason or "").strip():
        raise ValueError("an activation needs a reason")
    v = load(vid, reg)
    path = reg / "active.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"history": []}
    if old.get("version") == vid and old.get("sha256") == v["sha256"]:
        raise ValueError(f"{vid} is already the active version")
    entry = {"version": vid, "sha256": v["sha256"], "activated_at": now(), "reason": reason.strip()}
    new = {"version": vid, "sha256": v["sha256"], "history": old.get("history", []) + [entry]}
    write_json(path, new)
    return new


def verify(reg: Path = REG) -> dict:
    """Every version's hash and the pointer's: what --verify prints."""
    out = {"registry": rel(reg), "versions": [], "ok": True}
    for p in sorted((reg / "versions").glob("*.json")):
        try:
            v = load(p.stem, reg)
            out["versions"].append({"id": v["id"], "sha256": v["sha256"], "ok": True})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            out["versions"].append({"id": p.stem, "ok": False, "error": str(e)})
            out["ok"] = False
    try:
        a = active(reg)
        out["active"] = {"version": a["id"], "sha256": a["sha256"], "ok": True}
    except (FileNotFoundError, ValueError, KeyError) as e:
        out["active"] = {"ok": False, "error": str(e)}
        out["ok"] = False
    if os.environ.get(ENV):
        out["pinned_by_environment"] = os.environ[ENV]
    return out


# ------------------------------------------------------------------------------------------------
# What the builders take

def ios_constants(v: dict | None = None) -> tuple[dict, dict]:
    """(chosen, typ) as the IOS builders take them (the keys' orders are theirs): chosen[(tour, stat)] = {"h": weeks or
    inf, "kappa", "tau"}, typ[(stat, tour)] = the typical units."""
    c = (v or current())["constants"]
    chosen = {tuple(k.split("|")): {"h": dec(x["h"]), "kappa": float(x["kappa"]), "tau": int(x["tau"])}
              for k, x in c["base"].items()}
    typ = {tuple(reversed(k.split("|"))): float(x) for k, x in c["typical_units"].items()}
    return chosen, typ


def short_h(v: dict | None = None) -> dict:
    """The short-memory IOS points matchup's half-life in weeks, per tour."""
    return {t: float(h) for t, h in (v or current())["constants"]["short_memory_h"].items()}


def surface_choice(v: dict | None = None) -> dict:
    """The surface IOS's choice per "tour|stat" as surface_ios/build_features.py takes it (tuning_choice.json's fields):
    variant, h_mult, and the multiples ks_mult (the shared penalty's), kE_mult and kF_mult, None for no surface term."""
    out = {}
    for k, x in (v or current())["constants"]["surface"].items():
        kE = None if x["kE_mult"] == "inf" else float(x["kE_mult"])
        kF = None if x["kF_mult"] == "inf" else float(x["kF_mult"])
        out[k] = {"variant": x["variant"], "h_mult": float(x["h_mult"]),
                  "ks_mult": kE if x["variant"] == "shared" else None, "kE_mult": kE, "kF_mult": kF}
    return out


# ------------------------------------------------------------------------------------------------
# The drift check and the printouts

def check(v: dict | None = None, stageb: Path = STAGEB_SUMMARY, choice: Path = SURFACE_CHOICE) -> dict:
    """The version in effect against the tuning outputs on disk now and the surface averages: every constant that
    adding those outputs as a version would change."""
    v = v or current()
    c = v["constants"]
    out = {"version": v["id"], "sha256": v["sha256"]}
    if Path(stageb).exists():
        base, typ = base_from(stageb)
        out["stage_b_summary"] = {
            "path": rel(stageb), "is_the_version_source": file_sha256(stageb) == v["sources"]["base"].get("sha256"),
            "base_differs": [{"cell": k, "version": c["base"][k], "summary": base.get(k)}
                             for k in CELLS if base.get(k) != c["base"][k]],
            "typical_units_differ": [{"cell": k, "version": c["typical_units"][k], "summary": typ.get(k),
                                      "relative": (typ[k] / c["typical_units"][k] - 1) if k in typ else None}
                                     for k in CELLS if typ.get(k) != c["typical_units"][k]]}
    else:
        out["stage_b_summary"] = {"path": rel(stageb), "missing": True}
    if Path(choice).exists():
        sc = surface_from(choice)
        out["surface_choice"] = {
            "path": rel(choice), "is_the_version_source": file_sha256(choice) == v["sources"]["surface"].get("sha256"),
            "surface_differs": [{"cell": k, "version": c["surface"][k], "choice": sc.get(k)}
                                for k in CELLS if sc.get(k) != c["surface"][k]]}
    else:
        out["surface_choice"] = {"path": rel(choice), "missing": True}
    out["surface_means_unchanged"] = surface_means_fingerprint() == v["sources"].get("surface_means_sha256")
    s, sc_ = out["stage_b_summary"], out["surface_choice"]
    out["drift"] = bool(s.get("missing") or s.get("base_differs") or s.get("typical_units_differ")
                        or sc_.get("missing") or sc_.get("surface_differs") or not out["surface_means_unchanged"])
    return out


def check_line(res: dict) -> str:
    s, sc = res["stage_b_summary"], res["surface_choice"]
    if not res["drift"]:
        return f"IOS constants {res['version']}: the tuning outputs on disk and the surface averages match it"
    parts = []
    if s.get("missing") or sc.get("missing"):
        parts.append("a tuning output is missing")
    if s.get("base_differs"):
        parts.append(f"Stage B's h/kappa/tau differ in {len(s['base_differs'])} cells")
    if s.get("typical_units_differ"):
        worst = max(abs(d["relative"]) for d in s["typical_units_differ"] if d["relative"] is not None)
        parts.append(f"typical units differ in {len(s['typical_units_differ'])} cells (at most {100 * worst:.3f}%)")
    if sc.get("surface_differs"):
        parts.append(f"the surface choice differs in {len(sc['surface_differs'])} cells")
    if not res["surface_means_unchanged"]:
        parts.append("the surface averages changed")
    return (f"IOS constants {res['version']}: " + "; ".join(parts) + ". Nothing changes until a version is added and "
            "activated")


def show(v: dict) -> str:
    c = v["constants"]
    lines = [f"IOS constants {v['id']} (sha256 {v['sha256'][:16]}), selected by {v.get('selected_by', '-')}",
             f"created {v['created_at']}, based on {v.get('based_on') or 'nothing'}", f"note: {v['note']}", "",
             f"{'tour':<5}{'stat':<12}{'h (wk)':>8}{'kappa':>7}{'tau':>5}{'typical':>10}   "
             f"{'surface':<12}{'h_mult':>7}{'kE':>6}{'kF':>6}"]
    for k in CELLS:
        t, s = k.split("|")
        b, sf = c["base"][k], c["surface"][k]
        lines.append(f"{t:<5}{s:<12}{b['h'] if b['h'] == 'inf' else format(b['h'], 'g'):>8}{b['kappa']:>7g}"
                     f"{b['tau']:>5}{c['typical_units'][k]:>10.3f}   {sf['variant']:<12}{sf['h_mult']:>7g}"
                     f"{str(sf['kE_mult']) if sf['kE_mult'] == 'inf' else format(sf['kE_mult'], 'g'):>6}"
                     f"{str(sf['kF_mult']) if sf['kF_mult'] == 'inf' else format(sf['kF_mult'], 'g'):>6}")
    lines.append("")
    lines.append("short-memory points matchup: half-life " +
                 ", ".join(f"{t} {h:g} weeks" for t, h in c["short_memory_h"].items()) + " (spw's kappa and tau)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--show", nargs="?", const="", metavar="ID")
    g.add_argument("--list", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--add", metavar="ID")
    g.add_argument("--activate", metavar="ID")
    ap.add_argument("--note")
    ap.add_argument("--reason")
    ap.add_argument("--from", dest="from_id", metavar="ID")
    ap.add_argument("--base-from", type=Path, metavar="FILE")
    ap.add_argument("--surface-from", type=Path, metavar="FILE")
    ap.add_argument("--short-h", nargs="+", metavar="TOUR=WEEKS")
    a = ap.parse_args()
    try:
        return run(a)
    except (ValueError, FileExistsError, FileNotFoundError) as e:     # a refusal, not a crash
        print(f"refused: {e}", file=sys.stderr)
        return 1


def run(a: argparse.Namespace) -> int:
    if a.show is not None:
        print(show(load(a.show) if a.show else current()))
    elif a.list:
        act = pointer().get("version") if (REG / "active.json").exists() else None
        for v in versions():
            print(f"{'*' if v['id'] == act else ' '} {v['id']:<28}{v['sha256'][:12]}  {v['created_at']}  "
                  f"based on {v.get('based_on') or '-'}: {v['note'][:90]}")
        if os.environ.get(ENV):
            print(f"{ENV} pins {os.environ[ENV]} in this shell")
    elif a.verify:
        res = verify()
        print(json.dumps(res, indent=1))
        return 0 if res["ok"] else 1
    elif a.check:
        res = check()
        print(json.dumps(res, indent=1))
        print(check_line(res))
    elif a.add:
        short = None
        if a.short_h:
            pairs = [x.split("=", 1) for x in a.short_h]
            if any(len(p) != 2 for p in pairs):
                raise SystemExit("--short-h takes TOUR=WEEKS pairs, e.g. atp=4 wta=13")
            short = {t.strip(): float(w) for t, w in pairs}
        v = add(a.add, a.note, a.base_from, a.surface_from, short, a.from_id)
        print(show(v))
        print(f"\nadded {v['id']}; not active. To use it: registry.py --activate {v['id']} --reason '...'")
    else:
        p = activate(a.activate, a.reason)
        print(f"active: {p['version']} ({p['sha256'][:12]}); {len(p['history'])} activations in active.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
