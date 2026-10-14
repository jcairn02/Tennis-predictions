"""R2-skeptic (round 2, addendum): add the addendum's ruling to verdict.json (as groups.addendum and top-level
addendum, identical), note in W26 that QM080 is superseded, and update scope_totals from my files.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/verdict_addendum.py
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
    chk = pd.read_csv(OUT / "addendum_check.csv")
    mine = pd.read_csv(OUT / "overrides_scope.csv", dtype=str, keep_default_na=False)
    v2 = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    m = mine.merge(v2[mine.columns], on=list(mine.columns), how="left", indicator=True)
    equal_v2 = int(m["_merge"].eq("both").sum())
    conf = chk[chk["confirmed"]]
    w22 = conf[conf["group"].eq("W22")]
    w26 = conf[conf["group"].eq("W26") & conf["what"].eq("added")]
    left = chk[~chk["confirmed"]]
    codes = lambda d: ", ".join(d["feed_key"].str.split(":").str[1])  # noqa: E731
    entry = {
        "vote": "narrow",
        "bar": "8 Oct bar for the 13 added matches of 2023-2024 (W22); source rule for the 19 added matches of 2026 and "
               "for QM080 (W26), as before",
        "scope": (f"{int(chk['confirmed'].sum())} of the 33 confirmed, every one with the amended values, which equal "
                  f"mine. QM080 (Maestrelli-Noguchi 2026) replaced: service games 14 and 15 (blank before), its eight "
                  f"counts as confirmed in v1. Appended ({len(w22) + len(w26)}): {len(w22)} of the 2023-2024 main "
                  f"draws ({codes(w22)}) and {len(w26)} of TML's 2026 qualifying ({codes(w26)}). Left out "
                  f"({len(left)}): the 2023 qualifying matches whose Sackmann service games are blank ({codes(left)})."),
        "reasons": (
            "Checked on my own tables for all 33 (addendum.py). In every one, the amended service games equal the exact "
            "count: completed non-tiebreak games, from RG's set scores and MatchBeats' first server. That first server "
            "is certain in all 33. MatchBeats' first point is the match's first (set 1, game 1, point 1), and all "
            f"{int(chk['games_held'].sum())} non-tiebreak games the files hold are served by the player the alternation "
            "names (0 exceptions). The eight counts of every added match equal RG's in the row and in the amended "
            "table, and every confirmed box passes B0-B9 under the row's score. "
            "W22, 8 Oct bar: the 10 main-draw matches are corrupt beyond doubt on service games. Each capture holds "
            "RG's serve points and passes the integrity test. The score and the certain first server disprove "
            "Sackmann's counts, which are neither the tiebreaks-counted convention nor an exchange between the players. "
            "In 9, the total or both counts are wrong: 2023 SF Muchova-Sabalenka has 15 and 16 for 18 and 18, which "
            "Stage 0's B5 already drops; 2024 SD035 has 15 and 15 for 15 and 16, which B5's tolerance keeps. In 1, the "
            "total is right but the split impossible: 2023 SD048, 13 and 11 in a 24-game match. The 3 blanks are "
            "missing, not corrupt. Filling them is the source rule's 'replacing beats blanking', which I do not apply "
            "to Sackmann's history (as T0, Karatsev-Moreno de Alboran). Their values are right (complete, coherent "
            "captures; exact counts), so they would pass the source rule. "
            "W26, source rule: TML's zeros are missing values (Stage 0 already treats them so, C25); the feed's exact "
            "count fills them in all 19. QM084 (Molcan-Crawford) has a stale in-progress MatchBeats snapshot (status "
            "'I') holding 21 of the 24 non-tiebreak games. Its first point is the match's, and its 21 games follow the "
            "alternation, so 12 and 12 from RG's score is certain; TML's eight counts equal RG's. QM080: MatchBeats is "
            "also a stale snapshot ('I'), holding every game but the last (set 3, game 8, Maestrelli's turn by the "
            "alternation). All 28 non-tiebreak games it holds follow the alternation from its first point, so "
            "Maestrelli 14 and Noguchi 15 are certain. The 18 serve points RG gives Maestrelli beyond the snapshot "
            "(91 against 73) fit that one missing game on his serve, with the match total of 205 that TML gives too. "
            "The amendment's other change, completed games only in retirements, is what my v1 rows already carried. "
            f"So {equal_v2} of my {len(mine)} rows now equal the amended table on all 18 values.")
        ,
        "checks": [
            "addendum.py -> addendum_check.csv, addendum_summary.json: per match, the eight counts (row, amended, RG), "
            "the first server's certainty (first point; every held game on the alternation), the exact count, the row's "
            "kind (TML zero, blank, neither, impossible split; never the tiebreaks-counted convention nor an exchange), "
            "Stage 0's checks",
            "apply_addendum.py: QM080's row replaced (service games only, asserted), 29 rows appended, every other row "
            "unchanged (asserted); the pre-addendum table kept as overrides_scope_v1.csv",
            "dry_run.py, rerun: my 1,304 override rows applied to the raw rows with stage0_build.apply_box_overrides, "
            "each names one row and reads my values; the 4 exchanges read exchanged; 1,308 rows change, 0 outside my "
            "tables",
            "comparison: the amended proposed_overrides.csv differs from v1 only by the 32 added matches and 13 "
            f"service-game cells of 12 matches; my {len(mine)} rows equal it on all 18 values in {equal_v2}"]}
    v["groups"]["addendum"] = entry
    v["addendum"] = entry
    g26 = v["groups"]["W26"]
    if "Superseded" not in g26["scope"]:
        g26["scope"] += (" Superseded by the addendum: QM080 now carries 14 and 15 (confirmed), and the amended table "
                         "adopted the completed-games count of the 3 retirements.")
    yr = mine["feed_key"].str.extract(r":(\d{4})/")[0].astype(int)
    v["scope_totals"] = {
        "RGX": {"proposed": 4, "confirmed": 4},
        "W22": {"proposed_v1": 1177, "confirmed_v1": 943, "added_in_addendum": 13,
                "confirmed_in_addendum": int(len(w22)), "confirmed_total": int((yr <= 2025).sum())},
        "W26": {"proposed_v1": 332, "confirmed_v1": 332, "added_in_addendum": 19,
                "confirmed_in_addendum": int(len(w26)), "confirmed_total": int((yr == 2026).sum()),
                "qm080": "service games 14 and 15 (were blank)"},
        "override_rows_in_overrides_scope_csv": int(len(mine)),
        "rows_equal_to_the_amended_proposal_on_all_18_values": equal_v2}
    (OUT / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(v["scope_totals"], indent=1))
    print(entry["scope"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
