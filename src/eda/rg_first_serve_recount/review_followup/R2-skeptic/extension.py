"""R2-skeptic (round 2, extension): the 237 W22 matches I left out under the 8 Oct bar, re-ruled under the source rule
after the owner's extension of the 6 Oct rule to Sackmann's 2022-2025 rows
(docs/decisions/2026-10-09-roland-garros-box-scores.md, point 1).

The source rule (brief § 1): confirm a match when its override row is RG's record of the match (the right match,
players and orientation, the values as RG's documents give them), the official box passes Stage 0's checks, and no
record shows RG's value wrong on a count that changes; where the evidence is silent, RG's record is taken.

Per match (the list: followup/confirmed/not_unanimous_overrides.csv; values: the amended proposed_overrides.csv),
from my own tables:
    link       my code is the feed key's; RG's winner is the raw winner; names (link score)
    eight      my parse of RG's statistics equals the amended table's eight counts
    sv_gms     my value: the exact count (completed non-tie-break games, from RG's set scores and MatchBeats' first
               server) where the first server is certain (MatchBeats' first point is the match's and every held game
               follows the alternation), else the row's own count where it fits the score's total exactly (the
               proposal's fallback, the one count RG's documents do not give), else blank; against the amended table
    checks     Stage 0's B0-B9 on my values under the row's score
    against    any record that shows RG's value wrong on a count that changes:
                 a referee (my Court Vision 2022 recount; the Court Vision copy of 2023-2024 on serve points only; a
                 hand chart) holding every point and reading the row's value
                 RG's second records (MatchBeats; the 2025 key statistics) holding every point and giving another
                 split, aces or double faults, or holding MORE serve points than RG's statistics
    notes      silent evidence, examined: incomplete captures (is RG's record the longer one, and why), retirements
               where the row holds more serve points than RG's capture, no capture at all
Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    extension_check.csv, extension_scope_rows.csv, extension_summary.json
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/extension.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import addendum as AD  # noqa: E402  (my alternation check)
import build_scope as BS  # noqa: E402  (my Stage 0 box checks)
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
R1 = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
EIGHT = [c for c in NINE if c != "SvGms"]
SPLIT = {"1stIn": "first_in", "1stWon": "first_won", "2ndWon": "second_won", "ace": "ace", "df": "df"}


def first_server_by_parity(pts: pd.DataFrame, set_games: list[tuple[int, int]]) -> tuple[str | None, int, int]:
    """The match's first server (MatchBeats slot) implied by every non-tie-break game the capture holds: a game at an
    odd place in the match is served by the first server, at an even place by the other. Certain when all held games
    imply the same slot (the capture need not hold the first point). Returns (slot or None, games held, dissenting)."""
    offset, before = {}, 0
    for i, (a, b) in enumerate(set_games, 1):
        offset[i] = before
        before += a + b
    votes = []
    for (st, gm), game in pts.groupby(["set", "game"]):
        if bool(game["tb"].iloc[0]) or int(st) not in offset:
            continue
        k = offset[int(st)] + int(gm)
        server = game["server"].mode().iloc[0]
        votes.append(server if k % 2 == 1 else ("2" if server == "1" else "1"))
    if not votes:
        return None, 0, 0
    top = max(set(votes), key=votes.count)
    return top, len(votes), sum(v != top for v in votes)


def exact_sv(g_w: list, g_l: list, w_first: bool) -> tuple[int, int]:
    """Completed non-tie-break games served by the winner and the loser, from RG's set scores (winner's side first),
    serving alternating game by game through the match, a 7-6 set's last game a tie-break taking one turn."""
    turn_w, sw, sl = w_first, 0, 0
    for a, b in zip(g_w, g_l):
        if a is None or b is None:
            continue
        n = a + b
        for i in range(n):
            tb_game = (max(a, b) == 7 and min(a, b) == 6) and i == n - 1
            if not tb_game:
                sw, sl = sw + turn_w, sl + (not turn_w)
            turn_w = not turn_w
    return sw, sl


def main() -> int:
    todo = pd.read_csv(LEAD / "confirmed" / "not_unanimous_overrides.csv")
    v2 = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    s = pd.read_parquet(OUT / "players.parquet")
    sv = pd.read_csv(OUT / "svgms_rows.csv")[["match_id", "side", "exp_excl"]]
    s = s.merge(sv, on=["match_id", "side"], how="left")
    it = pd.read_csv(OUT / "mb_integrity.csv")[["year", "code", "integrity", "last_game_open"]]
    s = s.merge(it, on=["year", "code"], how="left")
    lead = pd.read_csv(LEAD / "whole_box_rows.csv", low_memory=False).rename(columns={"raw_side": "side"})
    s = s.merge(lead[["match_id", "side", "cv_svpt", "mcp_svpt", "mcp_first_in", "mcp_first_won", "mcp_second_won",
                      "mcp_ace", "mcp_df"]], on=["match_id", "side"], how="left")
    cv = pd.read_csv(R1 / "cv2022_sides.csv", low_memory=False)[
        ["source_file", "source_row", "side", "cv_svpt", "cv_first_in", "cv_first_won", "cv_second_won", "cv_ace",
         "cv_df"]].rename(columns=lambda c: "my" + c if c.startswith("cv_") else c)
    cv["source_row_i"] = pd.to_numeric(cv["source_row"], errors="coerce")
    s["source_row_i"] = pd.to_numeric(s["source_row"], errors="coerce")
    s = s.merge(cv.drop(columns="source_row"), on=["source_file", "source_row_i", "side"], how="left")
    pts = pd.read_parquet(OUT / "mb_points.parquet")
    rows, scope = [], []
    for t in todo.itertuples(index=False):
        mid = t.stage0_match_id
        g = s[s["match_id"].eq(mid)]
        w, l = g[g["side"].eq("w")].iloc[0], g[g["side"].eq("l")].iloc[0]
        o = v2[v2["stage0_match_id"].eq(mid)].iloc[0]
        rec = {"feed_key": t.feed_key, "stage0_match_id": mid, "year": int(w["year"]), "draw": w["draw"],
               "round": w["round"], "status": w["status"], "winner": w["player"], "loser": l["player"],
               "row_score": w["raw_score"], "code_agrees": t.feed_key.endswith("/" + str(w["code"])),
               "winner_agrees": bool(w["winner_agrees"]), "link_score": w["lscore"]}
        # the eight counts
        rec["eight_equal_amended"] = all(float(o[f"{sd}_{c}"]) == x[f"my_{c}"] for sd, x in (("w", w), ("l", l))
                                         for c in EIGHT)
        # service games
        sg = [(a, b) for a, b in zip(json.loads(w["rg_set_games"]), json.loads(w["rg_opp_set_games"]))
              if a is not None and b is not None]
        p = pts[(pts["year"].eq(rec["year"])) & pts["code"].eq(w["code"])]
        gw, gl = json.loads(w["rg_set_games"]), json.loads(w["rg_opp_set_games"])
        rec["has_capture"] = bool(len(p))
        slot, held, dissent = first_server_by_parity(p, sg) if len(p) else (None, 0, 0)
        certain = slot is not None and dissent == 0 and held > 0 and pd.notna(w["mb_slot"])
        rec["first_server_certain"], rec["games_held"], rec["games_dissenting"] = certain, held, dissent
        hyp_w_first, hyp_l_first = exact_sv(gw, gl, True), exact_sv(gw, gl, False)
        rec["exact_if_winner_first"], rec["exact_if_loser_first"] = hyp_w_first, hyp_l_first
        row_sv = (w["raw_SvGms"], l["raw_SvGms"])
        if certain:
            w_first = str(int(w["mb_slot"])) == slot
            mine_sv, how = exact_sv(gw, gl, w_first), "exact (score + first server by the capture's parity)"
        elif hyp_w_first == hyp_l_first:
            mine_sv, how = hyp_w_first, "exact (the score forces the split, whoever served first)"
        elif pd.notna(row_sv[0]) and pd.notna(row_sv[1]) and tuple(row_sv) in (hyp_w_first, hyp_l_first):
            mine_sv, how = row_sv, "row's own count (fits the score; orientation unverifiable without a capture)"
        else:
            mine_sv, how = (np.nan, np.nan), "blank"
        mine_sv = tuple(float(v) for v in mine_sv)
        rec["sv_gms_how"] = how
        amended_sv = tuple(float(o[f"{sd}_SvGms"]) if o[f"{sd}_SvGms"] != "" else np.nan for sd in ("w", "l"))
        rec["sv_gms_mine"], rec["sv_gms_amended"] = mine_sv, amended_sv
        rec["sv_gms_equal_amended"] = all((pd.isna(a) and pd.isna(b)) or a == b for a, b in zip(mine_sv, amended_sv))
        vals = {}
        for sd, x, v in (("w", w, mine_sv[0]), ("l", l, mine_sv[1])):
            for cc in EIGHT:
                vals[f"{sd}_{cc}"] = x[f"my_{cc}"]
            vals[f"{sd}_SvGms"] = v
        fails = BS.stage0_checks({cc: vals[f"w_{cc}"] for cc in NINE}, {cc: vals[f"l_{cc}"] for cc in NINE},
                                 w["raw_score"], w["status"])
        rec["stage0_checks_failed"] = ";".join(fails)
        # records against RG on a count that changes
        against, support, notes = [], [], []
        for x in (w, l):
            for short, long_ in SPLIT.items():
                if x[f"raw_{short}"] == x[f"my_{short}"] or pd.isna(x[f"raw_{short}"]):
                    continue
                for ref, col, ok in (("Court Vision 2022", "mycv", x["year"] == 2022), ("hand chart", "mcp", True)):
                    full = ok and (x[f"{col}_svpt"] == x["my_svpt"] or x[f"{col}_svpt"] == x["raw_svpt"])
                    if not full or pd.isna(x[f"{col}_{long_}"]):
                        continue
                    if x[f"{col}_{long_}"] == x[f"raw_{short}"]:
                        against.append(f"{ref} reads the row's {short} ({x['player']})")
                    elif x[f"{col}_{long_}"] == x[f"my_{short}"]:
                        support.append(f"{ref} reads RG's {short} ({x['player']})")
                    else:
                        notes.append(f"{ref} reads neither {short} ({x['player']})")
            if pd.notna(x["raw_svpt"]) and x["raw_svpt"] != x["my_svpt"]:
                for ref, col in (("Court Vision", "cv"), ("hand chart", "mcp")):
                    if pd.notna(x[f"{col}_svpt"]):
                        if x[f"{col}_svpt"] == x["raw_svpt"]:
                            against.append(f"{ref} holds the row's serve points ({x['player']})")
                        elif x[f"{col}_svpt"] == x["my_svpt"]:
                            support.append(f"{ref} holds RG's serve points ({x['player']})")
            # RG's second records
            for src, cols in (("MatchBeats", {k: f"mb_{v}" for k, v in SPLIT.items()}),
                              ("key statistics", {k: f"ks_{v}" for k, v in SPLIT.items()})):
                hold = x.get(f"{src[:2].lower()}_svpt") if src == "MatchBeats" else x.get("ks_svpt")
                if pd.isna(hold):
                    continue
                if hold > x["my_svpt"]:
                    against.append(f"{src} holds more serve points than RG ({x['player']})")
                elif hold == x["my_svpt"] and any(x[v] != x[f"my_{k}"] for k, v in cols.items()):
                    against.append(f"{src} holds every point and differs ({x['player']})")
        if w["status"] == "retired" and any(x["raw_svpt"] > x["my_svpt"] for x in (w, l)):
            notes.append("retirement: the row holds more serve points than RG's capture")
        if rec["has_capture"] and not bool(w["mb_complete_match"]):
            ext = [f"{x['player']}: RG {int(x['my_svpt'])}, capture {int(x['mb_svpt']) if pd.notna(x['mb_svpt']) else 'none'}"
                   for x in (w, l)]
            notes.append("incomplete capture (" + "; ".join(ext) + ")" +
                         (", last game open" if w["last_game_open"] is True or w["last_game_open"] == True else ""))
        if not rec["has_capture"]:
            notes.append("no capture")
        rec["against"], rec["support"], rec["notes"] = "; ".join(against), "; ".join(support), "; ".join(notes)
        reasons = []
        if not rec["code_agrees"] or not rec["winner_agrees"]:
            reasons.append("link or orientation")
        if not rec["eight_equal_amended"]:
            reasons.append("eight counts not reproduced")
        if not rec["sv_gms_equal_amended"]:
            reasons.append(f"service games not reproduced (mine {mine_sv}, amended {amended_sv})")
        if fails:
            reasons.append("fails Stage 0 checks: " + ";".join(fails))
        if against:
            reasons.append("a record shows RG wrong: " + "; ".join(against))
        rec["confirmed"] = not reasons
        rec["reasons"] = "; ".join(reasons)
        rows.append(rec)
        if rec["confirmed"]:
            scope.append({"feed_key": t.feed_key, "stage0_match_id": mid,
                          **{k: ("" if pd.isna(vals[k]) else int(vals[k]))
                             for k in [f"{sd}_{cc}" for sd in ("w", "l") for cc in NINE]}})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "extension_check.csv", index=False)
    pd.DataFrame(scope).to_csv(OUT / "extension_scope_rows.csv", index=False)
    sup = out["support"].fillna("").str.len().gt(0)
    summ = {"matches": int(len(out)), "confirmed": int(out["confirmed"].sum()),
            "left_out": out[~out["confirmed"]][["stage0_match_id", "reasons"]].to_dict("records"),
            "eight_equal_amended": int(out["eight_equal_amended"].sum()),
            "sv_gms_equal_amended": int(out["sv_gms_equal_amended"].sum()),
            "sv_gms_how": out["sv_gms_how"].value_counts().to_dict(),
            "matches_with_a_record_against_rg": int(out["against"].fillna("").ne("").sum()),
            "matches_with_a_record_reading_rg": int(sup.sum()),
            "support_readings": int(out["support"].fillna("").str.count("reads RG|holds RG").sum()),
            "neither_readings": out[out["notes"].fillna("").str.contains("neither")][["stage0_match_id", "notes"]]
            .to_dict("records"),
            "examined_notes": out[out["notes"].fillna("").ne("")][["stage0_match_id", "status", "notes",
                                                                   "sv_gms_how"]].to_dict("records")}
    (OUT / "extension_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summ.items() if k not in ("examined_notes",)}, indent=1, default=str))
    pd.set_option("display.width", 260)
    pd.set_option("display.max_colwidth", 150)
    pd.set_option("display.max_rows", 80)
    print(pd.DataFrame(summ["examined_notes"]).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
