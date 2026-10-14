"""R3-referee (follow-up), step 5: the four exchanged boxes of RG 2021 (fix RGX, exchange_box).

For each row of followup/proposed_exchanges.csv:
  * the winner: the row's score read from the winner's side against RG's sets (by names), RG's winner flag,
    MatchBeats' matchWinner, and who plays the next round of the same event in the raw rows (Sackmann's and TML's);
  * the nine counts: RG's statistics (eight counts) and MatchBeats (service games, tiebreaks not counted; and its own
    split, aces, double faults, break points as a second record) against the row's two boxes as recorded and
    exchanged;
  * names swapped rather than boxes: the row's other player fields (rank, seed, age, height, hand, country) against
    RG's player data (ranking, country) and the player's other rows of the season;
  * independent records: the Court Vision copy (RG 2021) and the hand charts, where they hold the match.
Writes rgx_check.csv and rgx_summary.json into data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/rgx.py
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import official as OF  # noqa: E402
import r3f as F  # noqa: E402

NEXT = {"R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF", "SF": "F"}


def main() -> int:
    ex = pd.read_csv(F.FOLLOW / "proposed_exchanges.csv", dtype=str, keep_default_na=False)
    raw = pd.read_parquet(F.OUT / "sub_raw.parquet")
    raw["_row"] = pd.to_numeric(raw["_row"]).astype("int64")
    o = pd.read_csv(F.OUT / "official_rows.csv", low_memory=False)
    P = pd.read_csv(F.OUT / "ref_rows.csv", low_memory=False)
    out = []
    for e in ex.itertuples():
        r = raw[(raw["_source_file"] == e.source_file) & (raw["_row"] == int(e.source_row))].iloc[0]
        x = o[(o["source_file"] == e.source_file) & (o["source_row"] == int(e.source_row))].iloc[0]
        code, year = x["code"], int(x["season"])
        doc = json.load(gzip.open(F.RAW / "rolandgarros" / "matches" / str(year) / f"{code}.json.gz"))
        route, mb = OF.mb_doc(year, code)
        mbc = OF.mb_counts(mb)
        rec = {"source_file": e.source_file, "source_row": int(e.source_row), "match_id": e.match_id, "code": code,
               "round": r["round"], "winner_name": r["winner_name"], "loser_name": r["loser_name"], "score": r["score"],
               "rg_sets_from_row_winner": x["rg_sets"], "score_sets_equal": bool(x["score_sets_equal"]),
               "rg_winner_flag_is_row_winner": bool(x["rg_w_is_winner"]) and not bool(x["rg_l_is_winner"]),
               "rg_end_cause": x.get("rg_end_cause")}
        # MatchBeats' winner slot, paired by name
        w_slot = "1" if F.name_ok(mbc["p1_name"], r["winner_name"]) > F.name_ok(mbc["p1_name"], r["loser_name"]) else "2"
        rec["mb_winner_is_row_winner"] = str(mbc["winner_slot"]) == w_slot
        # the next round: who of the two plays it (any source)
        nxt = NEXT.get(r["round"])
        nr = raw[(raw["tid"] == r["tid"]) & (raw["round"] == nxt) & (raw["tour"] == r["tour"])]
        in_next = lambda nm: bool(((nr["winner_name"].map(lambda s: F.name_ok(s, nm) == 2))
                                   | (nr["loser_name"].map(lambda s: F.name_ok(s, nm) == 2))).any())
        rec["next_round"] = nxt
        rec["row_winner_plays_next_round"] = in_next(r["winner_name"])
        rec["row_loser_plays_next_round"] = in_next(r["loser_name"])
        # the counts: RG's statistics and MatchBeats per player (by name), against the row as recorded / exchanged
        diffs_rec, diffs_exch = [], []
        for s, o_s in (("w", "l"), ("l", "w")):
            for c, col in F.NINE.items():
                rowv = pd.to_numeric(r[f"{s}_{col}"], errors="coerce")
                other = pd.to_numeric(r[f"{o_s}_{col}"], errors="coerce")
                offv = x[f"rg_{s}_{c}"] if c != "sv_gms" else x[f"mb_{s}_sv_gms"]
                rec[f"row_{s}_{c}"], rec[f"rg_{s}_{c}"] = rowv, offv
                if offv != rowv:
                    diffs_rec.append(f"{s}_{c}")
                if offv != other:
                    diffs_exch.append(f"{s}_{c}")
                if c not in ("sv_gms",):
                    rec[f"mb_{s}_{c}"] = x.get(f"mb_{s}_{c}")
        rec["counts_differing_as_recorded"] = " ".join(diffs_rec)
        rec["counts_differing_once_exchanged"] = " ".join(diffs_exch)
        rec["mb_complete_both"] = bool(x["mb_complete_both"])
        rec["mb_equals_rg_split_ace_df_bp"] = all(x[f"mb_{s}_{c}"] == x[f"rg_{s}_{c}"] for s in ("w", "l")
                                                  for c in ["svpt", "first_in", "first_won", "second_won", "ace", "df",
                                                            "bp_faced", "bp_saved"])
        rec["mb_sv_gms"] = f"{x['mb_w_sv_gms']:g}-{x['mb_l_sv_gms']:g}"
        rec["mb_sv_gms_incl_tb"] = f"{x['mb_w_sv_gms_incl_tb']:g}-{x['mb_l_sv_gms_incl_tb']:g}"
        rec["row_sv_gms"] = f"{rec['row_w_sv_gms']:g}-{rec['row_l_sv_gms']:g}"
        # names swapped rather than boxes: the row's player fields against RG's player data
        m = doc["match"]
        teams = {}
        for t in ("A", "B"):
            p = m[f"team{t}"]["players"][0]
            teams[f"{p.get('firstName', '')} {p.get('lastName', '')}"] = {"ranking": p.get("ranking"),
                                                                          "country": p.get("country"),
                                                                          "seed": m[f"team{t}"].get("seed")}
        for s, who in (("w", "winner"), ("l", "loser")):
            nm = r[f"{who}_name"]
            t = next((v for k, v in teams.items() if F.name_ok(k, nm) >= 1), {})
            rec[f"{s}_row_rank"], rec[f"{s}_rg_ranking_now"] = r[f"{who}_rank"], t.get("ranking")
            rec[f"{s}_row_ioc"], rec[f"{s}_rg_country"] = r[f"{who}_ioc"], t.get("country")
            rec[f"{s}_row_seed"], rec[f"{s}_rg_seed"] = r[f"{who}_seed"], t.get("seed")
        # independent records on this match
        q = P[(P["source_file"] == e.source_file) & (P["source_row"] == int(e.source_row))]
        for s in ("w", "l"):
            h = q[q["side"] == s]
            for ref in ("cv", "mcp"):
                for c in ["svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced", "bp_saved", "sv_gms"]:
                    rec[f"{ref}_{s}_{c}"] = h[f"{ref}_{c}"].iloc[0] if len(h) and f"{ref}_{c}" in h else np.nan
        out.append(rec)
    d = pd.DataFrame(out)
    d.to_csv(F.OUT / "rgx_check.csv", index=False)
    # what the referees read: the row as recorded, or exchanged
    ref_reads = []
    for rec in out:
        for ref in ("cv", "mcp"):
            for s, o_s in (("w", "l"), ("l", "w")):
                v = {c: rec.get(f"{ref}_{s}_{c}") for c in ["svpt", "first_in", "ace", "df", "first_won", "second_won"]}
                if pd.isna(v["svpt"]):
                    continue
                as_rec = sum(v[c] == rec[f"row_{s}_{c}"] for c in v)
                as_exch = sum(v[c] == rec[f"row_{o_s}_{c}"] for c in v)
                ref_reads.append({"match": rec["match_id"], "record": ref, "side": s, "counts": len(v),
                                  "equal_as_recorded": int(as_rec), "equal_once_exchanged": int(as_exch)})
    smry = {"exchanges": int(len(d)),
            "score_orientation_and_rg_winner_agree": int((d["score_sets_equal"] & d["rg_winner_flag_is_row_winner"]).sum()),
            "mb_winner_is_row_winner": int(d["mb_winner_is_row_winner"].sum()),
            "row_winner_plays_next_round": int(d["row_winner_plays_next_round"].sum()),
            "row_loser_plays_next_round": int(d["row_loser_plays_next_round"].sum()),
            "equal_once_exchanged_all_nine": int(d["counts_differing_once_exchanged"].eq("").sum()),
            "differing_as_recorded": d["counts_differing_as_recorded"].tolist(),
            "service_games_row_vs_matchbeats": d[["row_sv_gms", "mb_sv_gms", "mb_sv_gms_incl_tb"]].to_dict("records"),
            "mb_complete_and_equal_to_rg": int((d["mb_complete_both"] & d["mb_equals_rg_split_ace_df_bp"]).sum()),
            "referee_reads": ref_reads}
    (F.OUT / "rgx_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 200)
    print(json.dumps(smry, indent=1, default=str))
    print(d.T.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
