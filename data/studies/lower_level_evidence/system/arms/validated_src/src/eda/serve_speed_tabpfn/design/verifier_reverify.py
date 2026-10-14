"""R4 test verifier, re-verification of the strategist's fixes (V2, V5, V7, V8 and the new LinAlgError fallback).

Everything that runs --run does so on the strategist's stand-in world (test_ssp_harness.make_world: a fake frame with
FAKE labels, fake fits written here, all in a temporary folder). The real study tree is used once, for V5's refusal,
with a spy proving that no fit file at all (so no speed-arm forecast) is opened before the refusal.

    V2   --run refuses missing fits BEFORE labels(): one P2 fit missing; every A2 fit missing (labels booby-trapped)
    V7   a recorded FORECASTS_SHA256 that differs from the fits refuses before labels(); the matching one runs
    V8   score.hash_prereg and verify_prereg use the same CRLF-normalised hash: an LF and a CRLF copy of the same text
         hash alike, a checkout to CRLF still verifies, and a raw (un-normalised) hash of a CRLF file is refused
    V5   synthetic(arms="real") refuses before the hash (real tree: no preregistration.sha256; stand-in world: no hash),
         reading no fit; after a valid hash on the stand-in world it runs
    fallback  a LinAlgError (or ValueError) in S6, S9, S12 or a paired secondary marks that secondary unavailable and
         --run completes; the same error in P2, S0, S10, S13 or S14 aborts --run before results.json is written

Writes data/studies/serve_speed_tabpfn/design/verifier_reverify.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_reverify.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.serve_speed_tabpfn.design import verifier_prereg as VP  # noqa: E402

OUT = C.OUT / "design" / "verifier_reverify.json"


def write_prereg(P: C.Paths, extra: dict | None = None, crlf: bool = False) -> None:
    """A stand-in pre-registration holding the six current hashes (plus extra lines), hashed with score.hash_prereg."""
    lines = [f"{k}: {v}" for k, v in {**S.hashes(P), **(extra or {})}.items()]
    text = "# stand-in pre-registration\n\n```\n" + "\n".join(lines) + "\n```\n"
    P.prereg.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    S.hash_prereg(P)


def attempt(fn, *, labels_allowed: bool) -> dict:
    """Run fn() with score.labels wrapped: record whether it was reached (and raise if it must not be)."""
    real = S.labels
    state = {"labels_reached": False}

    def spy(*a, **k):
        state["labels_reached"] = True
        if not labels_allowed:
            raise AssertionError("labels() reached")
        return real(*a, **k)
    S.labels = spy
    try:
        fn()
        return {"outcome": "ran", **state}
    except Exception as e:                                   # noqa: BLE001 (reported, not swallowed)
        return {"outcome": f"refused: {type(e).__name__}: {str(e)[:150]}", **state}
    finally:
        S.labels = real


class Worlds:
    def __init__(self):
        self.H = VP.harness_tests()
        self.root = Path(tempfile.mkdtemp(prefix="ssp_verifier_reverify_"))
        (self.root / "world").mkdir()
        self.P0 = self.H.make_world(self.root / "world")
        self.n = 0

    def fresh(self, name: str, complete: bool = True, **kw) -> C.Paths:
        self.n += 1
        d = self.root / f"{self.n:02d}_{name}"
        shutil.copytree(self.P0.out, d / "out")
        shutil.copytree(self.P0.race_local, d / "race_local")
        P = self.P0.with_(out=d / "out", local=d / "out" / "local", checks=d / "out" / "checks",
                          features=d / "out" / "features", prereg=d / "prereg.md", race_local=d / "race_local")
        C.write_json(P.checks / "repro_check.json", {"passed": True})
        C.write_json(P.checks / "fingerprint_check.json", {"all_ok": True})
        if complete:
            VP.complete_world(P, **kw)
        return P


def results(P: C.Paths) -> dict:
    p = P.out / "results.json"
    return C.read_json(p) if p.exists() else {}


def v2(Wd: Worlds) -> list[dict]:
    out = []
    for name, kw in (("one P2 fit missing (spd 2026 seed 15)", {"skip_fits": {("spd", 2026, 15)}}),
                     ("every A2 fit missing", {"skip_arms": ("spd_raw",)}),
                     ("one model_noodds race seed missing (2019 seed 0)", {"skip_fits": {("model_noodds", 2019, 0)}})):
        P = Wd.fresh("v2", **kw)
        write_prereg(P)
        r = attempt(lambda: S.run(P), labels_allowed=False)
        out.append({"case": name, **r, "results_written": (P.out / "results.json").exists(),
                    "pass": r["outcome"].startswith("refused: RuntimeError") and "missing" in r["outcome"]
                    and not r["labels_reached"] and not (P.out / "results.json").exists()})
    P = Wd.fresh("v2_control")
    write_prereg(P)
    r = attempt(lambda: S.run(P), labels_allowed=True)
    res = results(P)
    out.append({"case": "control: every fit present", **r, "K": res.get("multiplicity", {}).get("secondary_intervals"),
                "pass": r["outcome"] == "ran" and r["labels_reached"]})
    return out


def v7(Wd: Worlds) -> list[dict]:
    out = []
    P = Wd.fresh("v7_match")
    write_prereg(P, {"FORECASTS_SHA256": S.forecasts_hash(P)["FORECASTS_SHA256"]})
    r = attempt(lambda: S.run(P), labels_allowed=True)
    out.append({"case": "recorded FORECASTS_SHA256 equals the fits", **r, "pass": r["outcome"] == "ran"})
    P = Wd.fresh("v7_changed")
    write_prereg(P, {"FORECASTS_SHA256": S.forecasts_hash(P)["FORECASTS_SHA256"]})
    VP.write_fit(P, "spd_raw", 2024, 3, P.local, C.sha256_file(P.feature_file), np.random.default_rng(99), set())
    r = attempt(lambda: S.run(P), labels_allowed=False)
    out.append({"case": "one fit refitted after the hash (spd_raw 2024 seed 3)", **r,
                "pass": r["outcome"].startswith("refused") and "FORECASTS_SHA256" in r["outcome"]
                and not r["labels_reached"]})
    P = Wd.fresh("v7_zero")
    write_prereg(P, {"FORECASTS_SHA256": "0" * 64})
    r = attempt(lambda: S.run(P), labels_allowed=False)
    out.append({"case": "recorded FORECASTS_SHA256 = 0...0", **r,
                "pass": r["outcome"].startswith("refused") and not r["labels_reached"]})
    P = Wd.fresh("v7_placeholder")
    write_prereg(P, {"FORECASTS_SHA256": "[lead, if the fits exist at the freeze]"})
    r = attempt(lambda: S.run(P), labels_allowed=True)
    out.append({"case": "FORECASTS_SHA256 line without a hex (fits not pinned): not checked", **r,
                "pass": r["outcome"] == "ran"})
    return out


def v8(Wd: Worlds) -> list[dict]:
    out = []
    P = Wd.fresh("v8", complete=False)
    write_prereg(P)
    lf_bytes = P.prereg.read_bytes()
    h_file = P.prereg_sha.read_text(encoding="utf-8").split()[0]
    out.append({"case": "hash_prereg on LF text = SHA-256 of the raw LF bytes = prereg_sha256",
                "hash": h_file, "pass": h_file == C.sha256_file(P.prereg) == S.prereg_sha256(P)})
    P.prereg.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))              # a checkout under core.autocrlf
    try:
        S.verify_prereg(P, S.hashes(P))
        ok = True
    except RuntimeError as e:
        ok = str(e)
    out.append({"case": "the same file converted to CRLF after hashing still verifies (and its keys parse)",
                "crlf_bytes": b"\r\n" in P.prereg.read_bytes(), "verify": ok, "pass": ok is True})
    S.hash_prereg(P)
    h_crlf = P.prereg_sha.read_text(encoding="utf-8").split()[0]
    out.append({"case": "hash_prereg on the CRLF file gives the LF hash", "pass": h_crlf == h_file})
    P.prereg_sha.write_text(C.sha256_file(P.prereg) + "  preregistration.md\n", encoding="utf-8")
    try:
        S.verify_prereg(P, S.hashes(P))
        ok = "verified"
    except RuntimeError as e:
        ok = f"refused: {e}"
    out.append({"case": "a raw (un-normalised) sha256sum of the CRLF file is refused: use --hash-prereg",
                "verify": ok, "pass": ok.startswith("refused")})
    Pr = Wd.fresh("v8_run", complete=True)
    write_prereg(Pr)
    Pr.prereg.write_bytes(Pr.prereg.read_bytes().replace(b"\n", b"\r\n"))
    r = attempt(lambda: S.run(Pr), labels_allowed=True)
    out.append({"case": "--run on a CRLF checkout of a hashed pre-registration", **r, "pass": r["outcome"] == "ran"})
    return out


class LoadSpy:
    def __init__(self):
        self.files = []
        self._lf, self._nl = F.load_fit, np.load

    def __enter__(self):
        spy = self

        def load_fit(arm, season, seed, *a, **k):
            spy.files.append(f"load_fit {arm} {season} {seed}")
            return spy._lf(arm, season, seed, *a, **k)

        def load(file, *a, **k):
            spy.files.append(f"np.load {Path(str(file)).name}")
            return spy._nl(file, *a, **k)
        F.load_fit, np.load = load_fit, load
        return self

    def __exit__(self, *exc):
        F.load_fit, np.load = self._lf, self._nl


def v5(Wd: Worlds) -> list[dict]:
    out = []
    scratch = Path(tempfile.mkdtemp(prefix="ssp_verifier_v5_"))
    with LoadSpy() as spy:
        r = attempt(lambda: S.synthetic(C.DEFAULT.with_(out=scratch), reps=1, arms="real"), labels_allowed=False)
    out.append({"case": "real tree (no preregistration.sha256): synthetic(arms='real')", **r,
                "fit_files_opened": spy.files, "pass": r["outcome"].startswith("refused") and not spy.files
                and not r["labels_reached"]})
    P = Wd.fresh("v5_standin")
    with LoadSpy() as spy:
        r = attempt(lambda: S.synthetic(P, reps=1, arms="real"), labels_allowed=False)
    out.append({"case": "stand-in world, no hash", **r, "fit_files_opened": len(spy.files),
                "pass": r["outcome"].startswith("refused") and not spy.files})
    write_prereg(P)
    r = attempt(lambda: S.synthetic(P, reps=2, arms="real", tag="v5_after_hash"), labels_allowed=False)
    out.append({"case": "stand-in world after a valid hash (fake spd fits)", **r, "pass": r["outcome"] == "ran"})
    r = attempt(lambda: S.synthetic(P, reps=1, arms="synthetic", tag="v5_synthetic"), labels_allowed=False)
    out.append({"case": "arms='synthetic' needs no hash (the verifier's mode)", **r, "pass": r["outcome"] == "ran"})
    return out


def fallback(Wd: Worlds) -> list[dict]:
    LinAlg = np.linalg.LinAlgError
    out = []
    real_paired, real_info = S.Scorer.paired, S.information

    def paired_failing(cid, exc):
        def f(self, cmp, ids=None):
            if cmp.cid == cid:
                raise exc("synthetic failure")
            return real_paired(self, cmp, ids)
        return f

    def info_failing(z_col, exc):
        def f(sc, col, seasons):
            if col == z_col:
                raise exc("synthetic failure")
            return real_info(sc, col, seasons)
        return f

    def raiser(exc):
        def f(*a, **k):
            raise exc("synthetic failure")
        return f

    cases = [  # (name, target attribute owner, attribute, replacement, expected: "fallback" | "abort", where to look)
        ("S6 moves LinAlgError", S, "moves", raiser(LinAlg), "fallback", "S6_moves"),
        ("S9 nudge LinAlgError", S, "nudge", raiser(LinAlg), "fallback", "S9"),
        ("S12 (information on spd_raw) LinAlgError", S, "information", info_failing("spd_raw", LinAlg), "fallback",
         "S12"),
        ("S8_A2 (a paired secondary) LinAlgError", S.Scorer, "paired", paired_failing("S8_A2", LinAlg), "fallback",
         "paired_secondaries"),
        ("S12 ValueError", S, "information", info_failing("spd_raw", ValueError), "fallback", "S12"),
        ("P2 LinAlgError", S.Scorer, "paired", paired_failing("P2", LinAlg), "abort", None),
        ("P2 ValueError", S.Scorer, "paired", paired_failing("P2", ValueError), "abort", None),
        ("S0 (information on spd_f) LinAlgError", S, "information", info_failing("spd_f", LinAlg), "abort", None),
        ("S10 capture LinAlgError", S, "capture", raiser(LinAlg), "abort", None),
        ("S13 close_edge LinAlgError", S, "close_edge", raiser(LinAlg), "abort", None),
        ("S14 LinAlgError", S.Scorer, "paired", paired_failing("S14", LinAlg), "abort", None),
    ]
    for name, owner, attr, repl, expect, where in cases:
        P = Wd.fresh("fallback")
        write_prereg(P)
        saved = getattr(owner, attr)
        setattr(owner, attr, repl)
        try:
            r = attempt(lambda: S.run(P), labels_allowed=True)
        finally:
            setattr(owner, attr, saved)
        res = results(P)
        row = {"case": name, "expected": expect, **r, "results_written": bool(res)}
        if expect == "fallback":
            part = res.get(where)
            if isinstance(part, list):
                unavailable = [x["cid"] for x in part if not x.get("available", True)]
            else:
                unavailable = [part["cid"]] if part and not part.get("available", True) else []
            row.update({"unavailable": unavailable, "P2_present": "estimate" in res.get("P2", {}),
                        "S0_present": "estimate" in res.get("S0", {}),
                        "K": res.get("multiplicity", {}).get("secondary_intervals")})
            row["pass"] = r["outcome"] == "ran" and bool(unavailable) and row["P2_present"] and row["S0_present"]
        else:
            row["pass"] = r["outcome"].startswith("refused") and not res
        out.append(row)
    return out


def main() -> int:
    Wd = Worlds()
    report = {"what": "re-verification of V2, V5, V7, V8 and the LinAlgError fallback (stand-in world with fake "
                      "labels; the real tree only for V5's refusal)", "scorer_code_sha256": C.code_hash(),
              "stand_in_root": str(Wd.root),
              "linalgerror_is_valueerror": issubclass(np.linalg.LinAlgError, ValueError)}
    for name, fn in (("V2", v2), ("V7", v7), ("V8", v8), ("V5", v5), ("fallback", fallback)):
        report[name] = fn(Wd)
    report["passed"] = all(c["pass"] for k in ("V2", "V7", "V8", "V5", "fallback") for c in report[k])
    C.write_json(OUT, report)
    for k in ("V2", "V7", "V8", "V5", "fallback"):
        print(f"== {k}")
        for c in report[k]:
            extra = {x: c[x] for x in ("labels_reached", "unavailable", "K", "results_written") if x in c}
            print(f"   {'ok ' if c['pass'] else 'NO '} {c['case']}: {c.get('outcome', c.get('verify', ''))} {extra}")
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
