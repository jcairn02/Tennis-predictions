"""B3-referee, round 2: writes data/studies/input_data_audit/fixes/B3-referee/round2.json from round2_evidence.json
(computed by round2_f11x.py). Read-only on the repo."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
D = ROOT / "data/studies/input_data_audit/fixes/B3-referee"

REASONS = {
    "atp|2010-560|SF|atp:103819|atp:104925": (
        "US Open 2010 SF, Djokovic (rank 3) d. Federer (rank 2) 5-7 6-1 5-7 6-2 7-5. All 5 books on the raw row oppose "
        "the average: B365 3.50/1.30, EX 3.75/1.25, LB 3.50/1.29, PS 3.49/1.36, SJ 3.50/1.29 (W/L), p(Djokovic) "
        "0.250-0.280; stored Avg 1.30/3.53 (p 0.731) and Max 1.39/4.00 are the mirror. Max for Djokovic 1.39 sits below "
        "every book's Djokovic price (3.49-3.75), which a maximum cannot. After exchanging Avg and Max: Avg 3.53/1.30 "
        "(p 0.269, inside the books' range; each side inside that side's book range), Max 4.00/1.39 >= every book on "
        "both sides, Avg <= Max on both sides, overround 1.053 unchanged. Ranks (Federer 2nd) side with the books. "
        "Link sound: name_pair, same set scores, round and both ranks agree."),
    "atp|2011-424|F|atp:104269|atp:105683": (
        "SAP Open 2011 F, Raonic (rank 84) d. Verdasco (rank 9) 7-6(6) 7-6(5). The row holds 4 independent books (no "
        "PS) and all 4 oppose the average: B365 3.40/1.33, EX 3.15/1.33, LB 3.25/1.33, SJ 3.00/1.36 (W/L), p(Raonic) "
        "0.281-0.312; stored Avg 1.35/3.03 (p 0.692) and Max 1.42/3.60 are the mirror. Max for Raonic 1.42 sits below "
        "every book's Raonic price (3.00-3.40). After exchanging Avg and Max: Avg 3.03/1.35 (p 0.308, inside the "
        "books' range; each side inside its book range), Max 3.60/1.42 >= every book on both sides, Avg <= Max on "
        "both sides, overround 1.071 unchanged. Ranks (9th v 84th) side with the books. Link sound: name_pair, same "
        "set scores, round and both ranks agree."),
    "atp|2011-520|F|atp:103819|atp:104745": (
        "Roland Garros 2011 F, Nadal (rank 1) d. Federer (rank 3) 7-5 7-6(3) 5-7 6-1; Stage 1 links it to "
        "tennis_data_couk/atp/grand_slam/2011.parquet row 253. All 5 books oppose the average: B365 1.36/3.20, EX "
        "1.40/2.80, LB 1.40/3.00, PS 1.39/3.37, SJ 1.40/3.00 (W/L), p(Nadal) 0.667-0.708; stored Avg 2.99/1.40 (p "
        "0.319) and Max 3.37/1.47 are the mirror. Max for Federer 1.47 sits below every book's Federer price "
        "(2.80-3.37). After exchanging Avg and Max: Avg 1.40/2.99 (p 0.681, inside the books' range; each side inside "
        "its book range), Max 1.47/3.37 >= every book on both sides (3.37 = PS), Avg <= Max on both sides, overround "
        "1.049 unchanged. Ranks (1st v 3rd) side with the books. Link sound: name_pair, same set scores, round and "
        "both ranks agree."),
}


def main() -> None:
    ev = json.loads((D / "round2_evidence.json").read_text(encoding="utf-8"))
    rows = []
    for r in ev:
        c = r["checks"]
        ok = (len(c["books_opposing_avg"]) == len(c["books_on_row"]) >= 4 and c["max_stored_below_a_book"]
              and c["after_avg_within_book_range_w"] and c["after_avg_within_book_range_l"]
              and c["after_max_ge_every_book"] and c["after_avg_le_max_both_sides"]
              and r["same_set_scores"] and r["rank_agrees_a"] and r["rank_agrees_b"])
        rows.append({"match_id": r["match_id"], "td_file": r["td_file"], "td_row": r["td_row"],
                     "vote": "confirm" if ok else "reject", "books": "avg max",
                     "fix": "exchange AvgW<->AvgL and MaxW<->MaxL as linked (Stage 1: avg_a<->avg_b, max_a<->max_b, "
                            "p_avg_a := 1 - p_avg_a)",
                     "reasons": REASONS[r["match_id"]],
                     "evidence": "data/studies/input_data_audit/fixes/B3-referee/round2_evidence.json "
                                 "(src/eda/input_data_audit/review/B3-referee/round2_f11x.py)"})
    (D / "round2.json").write_text(json.dumps({"reviewer": "B3-referee", "F11x": rows}, indent=1), encoding="utf-8")
    for x in rows:
        print(x["match_id"], x["vote"], x["books"])


if __name__ == "__main__":
    main()
