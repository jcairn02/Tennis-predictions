"""R2-skeptic (round 2, extension): add the extension's ruling to verdict.json (groups.extension and top-level
extension, identical) and update scope_totals from my files.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/verdict_extension.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"


def main() -> int:
    v = json.loads((OUT / "verdict.json").read_text(encoding="utf-8"))
    e = pd.read_csv(OUT / "extension_check.csv")
    summ = json.loads((OUT / "extension_summary.json").read_text(encoding="utf-8"))
    mine = pd.read_csv(OUT / "overrides_scope.csv", dtype=str, keep_default_na=False)
    v2 = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    m = mine.merge(v2[list(mine.columns)], on=list(mine.columns), how="left", indicator=True)
    equal = int(m["_merge"].eq("both").sum())
    how = summ["sv_gms_how"]
    n_conf = int(e["confirmed"].sum())
    entry = {
        "vote": "confirm" if n_conf == len(e) else "narrow",
        "bar": "source rule (the owner's extension of the 6 Oct rule to Sackmann's Roland Garros 2022-2025 rows, "
               "docs/decisions/2026-10-09-roland-garros-box-scores.md, point 1)",
        "scope": (f"{n_conf} of the {len(e)} W22 matches I had left out (234 under the 8 Oct bar, and the addendum's 3 "
                  "blank service-game pairs), every one with the amended table's values, which equal mine on all 18 "
                  f"counts. overrides_scope.csv now lists {len(mine)} matches, the whole amended table, and {equal} "
                  "of them carry its values exactly."),
        "reasons": (
            "Each of the 237 meets every condition of the source rule (extension.py). "
            "(1) The override row is RG's record of the match: my links place every one on the feed key's code, with "
            "RG's winner as the raw winner, and my parse of RG's documents gives the amended eight counts in 237 of "
            f"237. Service games reproduce in 237 of 237. In {how.get('exact (score + first server by the capture' + chr(39) + 's parity)', 0)}, "
            "they are the exact count from RG's set scores and the first server implied by every game the capture "
            "holds. In "
            f"{how.get('exact (the score forces the split, whoever served first)', 0)}, the score forces the split "
            "whoever served first. In "
            f"{how.get('row' + chr(39) + 's own count (fits the score; orientation unverifiable without a capture)', 0)} "
            "without any capture and with an unequal split, they are the row's own count. Those are 2025 Q1 QM075 "
            "Burruchaga d. Lestienne '6-3 7-6(6)', 11 and 10, and QM080 Trotter d. Holt '6-1 6-4', 9 and 8. "
            "That is the proposal's fallback, consistent with the score's total, with an "
            "orientation no record can check; Sackmann's 2022-2025 orientation is wrong in about 1 of 920 unequal "
            "splits. "
            "(2) Every box passes Stage 0's checks B0-B9 under the row's score (0 failures). "
            "(3) No record shows RG's value wrong on a count that changes: 0 matches. Where an independent record "
            f"holds every point, it reads RG's value: {summ['matches_with_a_record_reading_rg']} matches, "
            f"{summ['support_readings']} readings (hand charts, Court Vision 2022, and Court Vision's serve points), "
            "against none for the row. One chart reads neither value on one count (Royer, 2025 R128, first serves in: "
            "chart 86, RG 87, row 89), and the same chart reads RG's points won on both serves. "
            "Where the evidence is silent, I examined it. The 199 matches with a '-'/'0' split side and the 18 with "
            "an ace or double fault higher in the row have no record against RG, so the rule takes RG's record. "
            "Incomplete captures: RG's statistics are never shorter than the capture. In Monfils 2025 R128 the "
            "capture, the key statistics and Sackmann's row all read 147. The capture ends at 40-0 on Monfils' serve "
            "at 5-1 in the fifth set, one point before the end. RG's statistics hold that match point (148, with first "
            "serves in and first-serve points won one higher), so RG is the complete record. The 2 retirements where "
            "the row holds more serve points than RG's capture: in 2024 R64 Etcheverry-Rinderknech, Court Vision's "
            "copy holds RG's 109 and 108, not the row's 110 and 110. In 2023 Q1 Watanuki-Pellegrino no other record "
            "exists, and Sackmann's 2022-2025 rows over-count serve points elsewhere (167 player rows), so the row is "
            "no evidence against RG. The blanks (Karatsev-Moreno de Alboran's whole box; the 3 service-game pairs of "
            "2023 qualifying) are filled from RG's record, with exact service games. "
            "For the record: my earlier narrowing of W22 was not only about who may extend the rule. It was the 8 Oct "
            "bar applied to the data: on '-' sides Court Vision catches RG's record wrong about once in 23, and some "
            "counts had no record at all. The extension changes the bar to the source rule, under which none of the "
            "237 has a record against RG."),
        "checks": [
            "extension.py -> extension_check.csv, extension_summary.json: per match, link and winner, the eight counts "
            "against my parse, the service games reproduced (first server by the capture's parity; forced splits; the "
            "row's count only where no capture exists), Stage 0's checks, every record against or for RG on a count "
            "that changes (Court Vision 2022, Court Vision's serve points, hand charts, MatchBeats, key statistics)",
            "apply_extension.py: 237 rows appended, every earlier row unchanged (asserted); the table before kept as "
            "overrides_scope_v2.csv",
            "dry_run.py, rerun: my 1,541 override rows applied to the raw rows with stage0_build.apply_box_overrides, "
            "each names one row and reads my values; the 4 exchanges read exchanged; 1,545 rows change, 0 outside my "
            "tables; 252 rows without a box get one",
            f"comparison: my {len(mine)} rows equal the amended proposed_overrides.csv ({len(v2)} rows) on all 18 "
            f"values in {equal}"]}
    v["groups"]["extension"] = entry
    v["extension"] = entry
    yr = mine["feed_key"].str.extract(r":(\d{4})/")[0].astype(int)
    st = v["scope_totals"]
    st["W22"].update({"confirmed_in_extension": n_conf, "confirmed_total": int((yr <= 2025).sum()),
                      "proposed_total_amended": int(v2["feed_key"].str.extract(r":(\d{4})/")[0].astype(int).le(2025)
                                                    .sum())})
    st["W26"]["confirmed_total"] = int((yr == 2026).sum())
    st["override_rows_in_overrides_scope_csv"] = int(len(mine))
    st["rows_equal_to_the_amended_proposal_on_all_18_values"] = equal
    st["amended_proposal_rows"] = int(len(v2))
    (OUT / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(st, indent=1))
    print(entry["vote"], "|", entry["scope"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
