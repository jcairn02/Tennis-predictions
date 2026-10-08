"""One-off edit of docs/studies/feature_interactions/round2/hypothesis_family.md for the meta-auditor's checkpoint 1
(R-1, R-5, R-6, R-7, F-1, F-4; B4 dropped by its members' gates). Text only: no weight or test changes.
Adds the column `multipliers` (the members' applied signs and the tested sign, checkpoint 1 section 1.2).

    ./python.sh src/eda/feature_interactions/round1/math_audit/apply_checkpoint1.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DOC = ROOT / "docs" / "studies" / "feature_interactions" / "round2" / "hypothesis_family.md"
OLD = ["hid", "members", "primary_columns", "test", "sign", "weight", "trait", "controls", "deployment", "module", "notes"]

MULT = {  # checkpoint 1, section 1.2 (read from the module code); "x as is" = the column is not negated
    "I-008": "x as is; tested +", "I-036": "x as is; tested +", "I-042": "x as is; tested +",
    "I-049": "x as is; tested +", "I-053": "x as is; tested −", "I-082": "x as is; tested +",
    "I-084": "x as is; tested +", "LIT-2": "x as is; tested +", "S2": "n/a (TabPFN arm)",
    "B-LEVER": "n/a (Wald)", "B3": "n/a (Wald)", "B-SWITCH": "n/a (Wald)", "B-RECAL": "n/a (Wald)",
    "B-HOME": "n/a (Wald)",
    "B-FLB": "+1, +1; tested +", "B2": "+1, +1; tested +",
    "B6": "+1, +1, +1 (each an uncertainty measure); tested −",
    "B7": "+1, +1, +1, −1, −1 (I-023, I-031, I-032, I-048 E, F); tested +",
    "B9a": "−1, −1, +1, −1 (I-024 h·Fat, h·age, I-058, I-061); tested +",
    "B9b": "−1, +1, −1 (I-063 oriented like ΔFat, I-065, I-066); tested +",
    "B10": "−1, −1, −1, −1; tested +", "B11": "+1, +1, +1; tested +", "B-CLUTCH": "+1 (I-026); tested +",
    "B-ANCHOR": "−1, +1; tested +", "B-INJ": "−1, −1, −1 (ΔRust, inj·e_pre, ΔDec); tested +",
    "B-VENUE": "+1 (I-072); tested +", "B-AGE": "+1 (I-070); tested +",
    "B-REPUTE": "+1, +1, +1; tested −", "B-INFO": "+1, +1, +1; tested +",
    "B-OVERREACT": "−1, +1, −1, −1; tested +", "B-MOTIV": "+1, +1; tested −", "B-PREV": "−1, −1; tested +",
    "B-STATE": "+1 (BOD-C1); tested +", "B-LOAD": "−1, −1; tested +",
}
EDITS = {
    "B-STATE": {"members": "BOD-C1", "primary_columns": "ΔPastFat (mean Fat over the player's own matches in the 14 days before)",
                "controls": "ΔFat, sets_14d; nearest inputs recomputed by the module's rule (F-1); Std",
                "notes": "INFO-1 dropped by checkpoint 1 R-1 (its premise is false: the IOS state already counts the player's own matches); INFO-1 runs only as a descriptive sensitivity"},
    "B-INJ": {"primary_columns": "ΔRust (−); Δ(inj·1[L ≥ 56]·1[m ≤ 2]·e_pre) (−); ΔDec = −ΔTr (within-event serve decay) (−)",
              "notes": "I-045 is ΔDec = −ΔTr, the mechanism's direction (checkpoint 1 R-5); the serve-speed variant is infeasible"},
    "B7": {"trait": "slow (× 1.25 gates; height P2 a diagnostic only)",
           "notes": "gates on the slow-trait widening × 1.25; P2 on height is computed and reported, never folded into p (checkpoint 1 R-6); CV(r) 0.584, CV(r̄) 0.176, height-ace 0.40 passed; a P3 sdev pass is read beside I-048"},
    "B9a": {"trait": "slow (× 1.25 gates; height P2 a diagnostic only)",
            "notes": "gates on the slow-trait widening × 1.25; P2 on height reported only (checkpoint 1 R-6); I-058 passed its split-half gate"},
    "S2": {"trait": "slow (× 1.25)",
           "notes": "fixed 6 Oct 2026; t₁ and t₂ divided by √1.25 before the joint z, the filter and the replication (checkpoint 1 R-7); spans the spw sums (98%)"},
    "B-CLUTCH": {"members": "I-026 (I-009, I-027 dropped by their gates)",
                 "notes": "gate drops recorded at checkpoint 1 §1.4 (I-009 split-half 0.160 / 0.270 < 0.3; I-027 −0.072 / −0.011 ≤ 0.1)"},
    "B-VENUE": {"members": "I-072 (+ I-077); I-073 dropped by its gate",
                "notes": "I-073's split-season carry-over failed (≤ 0.124 < 0.15, checkpoint 1 §1.4); field solve needs clock and probe; I-072 carry-over 0.661 / 0.566 ≥ 0.3"},
}
DROP = {"B4"}


def main() -> int:
    lines = DOC.read_text(encoding="utf-8").splitlines()
    out, inside, n = [], False, 0
    for line in lines:
        if line.startswith("| hid |"):
            inside = True
            out.append("| hid | members | primary column(s) | test | sign | multipliers | weight | trait | controls | deployment | module | notes |")
            continue
        if inside and line.startswith("|---"):
            out.append("|" + "---|" * 12)
            continue
        if inside and line.startswith("| "):
            cells = [c.strip() for c in line.strip()[1:-1].split(" | ")]
            assert len(cells) == len(OLD), cells[0]
            row = dict(zip(OLD, cells))
            if row["hid"] in DROP:
                continue
            row.update(EDITS.get(row["hid"], {}))
            row["multipliers"] = MULT[row["hid"]]
            cols = OLD[:5] + ["multipliers"] + OLD[5:]
            out.append("| " + " | ".join(row[c] for c in cols) + " |")
            n += 1
            continue
        if inside and not line.startswith("|"):
            inside = False
        out.append(line)
    DOC.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"rewrote the table: {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
