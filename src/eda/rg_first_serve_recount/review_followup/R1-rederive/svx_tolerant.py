"""R1-rederive (SVX): a glitch-tolerant reading of the proof, applied to every row my strict proof leaves unproven.

The strict proof (svx_truth.prove) fails a file whose games are out of order or hold a service game with points of
both servers. A file can carry such a glitch in the middle of a match (AO 2024 MS136: set 4 repeats game 4 with one
point and its game 5 names both servers) and still prove who served first. The tolerant reading accepts the first
server when all of these hold:
  T1  P2: the file's first game is set 1 game 1 (set score 1-0 or 0-1 after it);
  T2  every game record follows the alternation from that first server, except records that are glitches: a repeated
      (set, game) number, or a game whose points name both servers; at least 20 games agree, and the glitch is local: at
      most 3 records, all in one set;
  T3  P4: each set held whole has the row's games by the games' winners (glitch sets are not held whole);
  T4  the break identity (from the row's own score and break points, no MatchBeats) gives the same truth.
Prints, for both rounds' editions, the rows this reading proves and how they then classify.
Writes svx_tolerant.csv. Run after svx_truth.py, svx_checks.py and svx_addendum.py:
  ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/svx_tolerant.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"r1_{name}", Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = load("svx_truth")


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    out = []
    pairs = [("svx_checked.csv", "svx_games.parquet"), ("svx_checked_add.csv", "svx_games_add.parquet"),
             ("svx_checked_add2.csv", "svx_games_add2.parquet")]
    for rows_f, games_f in pairs:
        if not (HERE / rows_f).exists():
            continue
        x = pd.read_csv(HERE / rows_f, low_memory=False)
        games = pd.read_parquet(WORK / games_f)
        gx = {k: g.sort_values("order") for k, g in games.groupby(["slam", "year", "code"])}
        un = x[x["proof"].eq("unproven") & x["mb_w_team"].notna()]
        for r in un.itertuples():
            g = gx[(r.slam, int(r.year), r.code)]
            pos = T.positions(r.score)
            fs = str(int(r.first_server)) if pd.notna(r.first_server) else None
            mbw = str(int(r.mb_w_team))
            dup = g.duplicated(["set", "game"], keep=False)
            agree = off = glitch = 0
            glitch_sets = set()
            for gg, d in zip(g.itertuples(), dup):
                if gg.server is None:
                    continue
                if d or gg.mixed:
                    glitch += 1
                    glitch_sets.add(gg.set)
                    continue
                p = pos.get((gg.set, gg.game))
                if p is None:
                    continue
                exp = fs if p % 2 == 1 else ("2" if fs == "1" else "1")
                if gg.server == exp:
                    agree += 1
                else:
                    off += 1
            t2 = fs in ("1", "2") and off == 0 and agree >= 20 and glitch <= 3 and len(glitch_sets) <= 1
            ok = bool(r.p2_opens) and t2 and bool(r.p4_sets)
            rec = {"rows": rows_f, "slam": r.slam, "year": int(r.year), "code": r.code, "score": r.score,
                   "w_SvGms": r.w_SvGms, "l_SvGms": r.l_SvGms, "games_agree": agree, "games_off": off,
                   "glitch_records": glitch, "p2": bool(r.p2_opens), "p4": bool(r.p4_sets), "tolerant_proof": ok,
                   "source_file": r.source_file, "source_row": r.source_row, "s0_match_id": r.s0_match_id}
            if ok:
                t = T.truth(r.score, fs == mbw)
                rec.update(t)
                bw, bl = r.w_bpFaced - r.w_bpSaved, r.l_bpFaced - r.l_bpSaved
                rec["bp_sv_w"], rec["bp_sv_l"] = r.reg_w + bw - bl, r.reg_l + bl - bw
                rec["t4_break_identity"] = rec["bp_sv_w"] == t["t_w"] and rec["bp_sv_l"] == t["t_l"]
                rw, rl = r.w_SvGms, r.l_SvGms
                rec["cls"] = ("equal" if (rw, rl) == (t["t_w"], t["t_l"]) else
                              "swapped" if (rw, rl) == (t["t_l"], t["t_w"]) and t["t_w"] != t["t_l"] else "other")
            out.append(rec)
    o = pd.DataFrame(out)
    o.to_csv(HERE / "svx_tolerant.csv", index=False)
    print("unproven rows with a linked file:", len(o), "| proven by the tolerant reading:", int(o["tolerant_proof"].sum()))
    p = o[o["tolerant_proof"]]
    print(p[["slam", "year", "code", "score", "w_SvGms", "l_SvGms", "t_w", "t_l", "bp_sv_w", "bp_sv_l",
             "t4_break_identity", "cls", "games_agree", "glitch_records"]].to_string())


if __name__ == "__main__":
    main()
