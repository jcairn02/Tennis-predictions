"""Candidate whole-box replacements where the tour's own two records agree with each other and not with Stage 0.

Class O1. For a match of a trio in box_votes.py (Stage 0 · the tour's published box · the tour's point record
recounted), Stage 0 is the odd one out: the published box equals the complete recount on every count both hold, for
both players, and Stage 0 differs on at least one. The replacement is the tour's published box, whole (all nine counts,
both players), as the 8 Oct 2026 decision did for WTA Adelaide 2 2022 (fix F3: "replaced by the WTA's own statistics
of the match"), with the decided action replace_box. A match is a candidate only when, in addition:
    * the published box holds all nine counts for both players and passes the definition checks (I3);
    * it passes the games and serving-order identities (I1, I2) with Stage 0's score, where the match was completed;
    * the match's row is Sackmann's (the decided table names raw rows by file and row) and the raw row still reads
      Stage 0's counts; TML rows (2026, after the splice) are listed apart, for the open source-order question
      (data_continuity section 4.5), not as table rows;
    * the match is not already in the decided row-correction table.

Writes data/studies/source_reconciliation/box/:
    official_candidates.csv     the O1 rows in the decided table's format (fix O1, action replace_box), Sackmann rows
    official_candidates_tml.csv the TML rows that would qualify (ids and both versions' counts), for the owner's
                                open source-order question
    official_candidates.json    counts, the checks, by trio and season
Run: ./python.sh src/eda/source_reconciliation/lead_official_corrections.py   (after box_votes.py and box_engine.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.input_data_audit import corrections as COR  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation.box_engine import games_from_score  # noqa: E402

BOX = C.OUT / "box"
SACK = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon", "second_won": "2ndWon",
        "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}


def checks(w: pd.Series, l: pd.Series, score: str, completed: bool) -> tuple[bool, bool, bool]:
    """(I3 both players, I1 both, I2) for a box given as the winner's and the loser's counts."""
    def i3(x):
        second = x["svpt"] - x["first_in"]
        return bool((x["first_in"] <= x["svpt"]) and (x["first_won"] <= x["first_in"]) and
                    (x["second_won"] + x["df"] <= second) and (x["bp_saved"] <= x["bp_faced"]) and
                    (x["ace"] <= x["first_won"] + x["second_won"]))
    ok3 = i3(w) and i3(l)
    if not completed:
        return ok3, True, True
    gw, gl, tw, tl, _, swf_w, swf_l = games_from_score(score)
    i1 = (w["sv_gms"] - (w["bp_faced"] - w["bp_saved"]) + (l["bp_faced"] - l["bp_saved"]) + tw == gw) and \
         (l["sv_gms"] - (l["bp_faced"] - l["bp_saved"]) + (w["bp_faced"] - w["bp_saved"]) + tl == gl)
    i2 = ((w["sv_gms"] == swf_w) and (l["sv_gms"] == swf_l)) or ((w["sv_gms"] == swf_l) and (l["sv_gms"] == swf_w))
    return ok3, bool(i1), bool(i2)


def main() -> int:
    L = pd.read_parquet(BOX / "votes_long.parquet")
    m = pd.read_parquet(C.SNAP / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "map_level", "status", "score", "tournament_name", "round",
                                 "source", "source_file", "source_row"])
    p = pd.read_parquet(C.SNAP / "stage0_match_players.parquet", columns=["match_id", "player_id", "won"])
    decided = set(pd.read_csv(COR.ROW_CORRECTIONS, dtype=str)["match_id"])
    rows, tml_rows, stats = [], [], {}
    for trio, g in L.groupby("trio"):
        if trio == "atp_mtd":           # the same matches as trio atp (ManTennisData and the key statistics agree)
            continue
        if trio == "atp_site2":
            # two scrapes of the ATP's numbers, no point record. Not a referee at the Slams: Stage 0's Slam rows carry
            # the decided service-game corrections (9 Oct 2026) that the ATP site's copies still lack. Matches that a
            # stronger trio already covers are left to it
            stronger = set(L.loc[L["trio"].isin(["atp", "atp_ch"]), "match_id"])
            g = g[~g["level_group"].eq("slam") & ~g["match_id"].isin(stronger)]
        odd = g.groupby("match_id")["s0_odd_row"].any()
        ids = odd[odd].index
        sub = g[g["match_id"].isin(ids)].merge(p, on=["match_id", "player_id"], how="left")
        st = {"stage0_odd_matches": int(len(ids)), "candidates": 0, "tml": 0, "dropped": {}}
        for mid, two in sub.groupby("match_id"):
            if len(two) != 2:
                st["dropped"]["not_two_players"] = st["dropped"].get("not_two_players", 0) + 1
                continue
            mm = m[m["match_id"] == mid].iloc[0]
            w = two[two["won"].astype(bool)].iloc[0]
            l = two[~two["won"].astype(bool)].iloc[0]
            wb = pd.Series({f: w[f"{f}_b"] for f in C.COUNTS})
            lb = pd.Series({f: l[f"{f}_b"] for f in C.COUNTS})
            if wb.isna().any() or lb.isna().any():
                st["dropped"]["box_not_full"] = st["dropped"].get("box_not_full", 0) + 1
                continue
            ok3, i1, i2 = checks(wb, lb, mm["score"], mm["status"] == "completed")
            if not (ok3 and i1 and i2):
                key = "box_fails_" + ("I3" if not ok3 else "I1" if not i1 else "I2")
                st["dropped"][key] = st["dropped"].get(key, 0) + 1
                continue
            if mid in decided:
                st["dropped"]["already_decided"] = st["dropped"].get("already_decided", 0) + 1
                continue
            rec = {"match_id": mid, "tour": mm["tour"], "year": int(mm["year"]), "tournament": mm["tournament_name"],
                   "round": mm["round"], "trio": trio, "source": mm["source"], "source_file": mm["source_file"],
                   "source_row": mm["source_row"],
                   "evidence": "two_site_copies" if trio == "atp_site2" else "box_and_point_record"}
            for side, x, xb in (("w", w, wb), ("l", l, lb)):
                for f, s in SACK.items():
                    rec[f"{side}_{s}"] = int(xb[f])
                    rec[f"x_stage0_{side}_{s}"] = x[f]
            if mm["source"] == "sackmann":
                rows.append(rec)
                st["candidates"] += 1
            else:
                tml_rows.append(rec)
                st["tml"] += 1
        stats[trio] = st
    cand = pd.DataFrame(rows)
    if not cand.empty:
        # the raw row's guards and the check that it still reads Stage 0's counts
        parts = []
        for f in sorted(set(cand["source_file"])):
            staged = C.DUMP / "matches" / "sackmann_archive" / ("atp" if "/atp/" in f else "wta") / (Path(f).stem + ".parquet")
            parts.append(pd.read_parquet(staged, columns=["tourney_id", "round", "winner_name", "loser_name",
                                                          "_source_file", "_row"] + [f"w_{s}" for s in SACK.values()]
                                         + [f"l_{s}" for s in SACK.values()]))
        raw = pd.concat(parts, ignore_index=True)
        raw["key"] = raw["_source_file"].astype(str) + "#" + raw["_row"].astype(str)
        cand["key"] = cand["source_file"].astype(str) + "#" + cand["source_row"].astype(str)
        raw = raw.rename(columns={c: f"raw_{c}" for c in raw.columns if c.startswith(("w_", "l_"))})
        cand = cand.merge(raw.drop(columns=["_source_file", "_row"]).rename(columns={"round": "raw_round"}), on="key",
                          how="left", validate="one_to_one")
        reads = np.ones(len(cand), dtype=bool)
        for side in ("w", "l"):
            for s in SACK.values():
                reads &= (pd.to_numeric(cand[f"raw_{side}_{s}"], errors="coerce").to_numpy() ==
                          pd.to_numeric(cand[f"x_stage0_{side}_{s}"], errors="coerce").to_numpy()) | \
                         cand[f"x_stage0_{side}_{s}"].isna().to_numpy()
        cand["x_raw_reads_stage0"] = reads
        table = pd.DataFrame({"fix": "O1", "action": "replace_box", "match_id": cand["match_id"],
                              "source_file": cand["source_file"], "source_row": cand["source_row"],
                              "tourney_id": cand["tourney_id"], "round": cand["raw_round"],
                              "winner_name": cand["winner_name"], "loser_name": cand["loser_name"], "side": "",
                              "value": ""})
        for side in ("w", "l"):
            for s in SACK.values():
                table[f"{side}_{s}"] = cand[f"{side}_{s}"].astype(int)
        for c in ["trio", "evidence", "tour", "year", "tournament", "x_raw_reads_stage0"] + \
                 [c for c in cand.columns if c.startswith("x_stage0_")]:
            table[c if c.startswith("x_") else f"x_{c}"] = cand[c].to_numpy()
        # where Stage 0 differs only on the first-serve split, the WTA event log's split was calibrated to the WTA box
        # by subagent 1 (box/REPORT_wta.md, "choices made after seeing results"), so the referee is not blind there
        split = {"1stIn", "1stWon", "2ndWon"}
        diff = [{s for side in ("w", "l") for s in SACK.values()
                 if pd.notna(r[f"x_stage0_{side}_{s}"]) and r[f"x_stage0_{side}_{s}"] != r[f"{side}_{s}"]}
                for _, r in table.iterrows()]
        table["x_counts_differing"] = [",".join(sorted(d)) for d in diff]
        table["x_split_only"] = [bool(d) and d <= split for d in diff]
        # a difference only in service games at a retirement is the convention for the game in progress (the WTA box
        # counts it, Sackmann's rows in 227 of 253 such rows: box/REPORT_wta.md Q4), not corruption: left out
        status = table["match_id"].map(m.set_index("match_id")["status"])
        definitional = [d == {"SvGms"} and s == "retired" for d, s in zip(diff, status)]
        stats["left_out_retirement_service_game_only"] = int(sum(definitional))
        table = table[~pd.Series(definitional, index=table.index)].reset_index(drop=True)
        cand = cand[cand["match_id"].isin(set(table["match_id"]))].reset_index(drop=True)
        table.to_csv(BOX / "official_candidates.csv", index=False)
    tml = pd.DataFrame(tml_rows)
    if not tml.empty:
        tdiff = [{s for side in ("w", "l") for s in SACK.values()
                  if pd.notna(r[f"x_stage0_{side}_{s}"]) and r[f"x_stage0_{side}_{s}"] != r[f"{side}_{s}"]}
                 for _, r in tml.iterrows()]
        tstatus = tml["match_id"].map(m.set_index("match_id")["status"])
        tdef = [d == {"SvGms"} and s == "retired" for d, s in zip(tdiff, tstatus)]
        tml["x_counts_differing"] = [",".join(sorted(d)) for d in tdiff]
        stats["tml_left_out_retirement_service_game_only"] = int(sum(tdef))
        tml = tml[~pd.Series(tdef, index=tml.index)].reset_index(drop=True)
    tml_rows = tml.to_dict("records")
    tml.to_csv(BOX / "official_candidates_tml.csv", index=False)
    summary = {"by_trio": stats, "sackmann_candidates": int(len(cand)),
               "split_only": int(table["x_split_only"].sum()) if not cand.empty else 0,
               "raw_reads_stage0": int(cand["x_raw_reads_stage0"].sum()) if not cand.empty else 0,
               "by_tour_year": cand.groupby(["tour", "year"]).size().rename("matches").reset_index().to_dict("records")
               if not cand.empty else [], "tml_rows": len(tml_rows)}
    C.write_json(BOX / "official_candidates.json", summary)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
