"""TennisLive's match statistics on Stage 0's ids (reader tp_tennislive_stats of the source-reconciliation study; brief:
docs/studies/source_reconciliation/subagent_briefs.md).

Inputs (read-only): data/dump/points/tennislive/matches.parquet and statistics.parquet: every match page held (the ten
careers, the P4 samples, the P5 gap pages; `sampled_in` and `gaps_in` name them).

Mapping (period "match"; the mapping of lower_level_evidence/candidate_stage0.py load_tennislive_pages):
    first_in / svpt "First serve" detail "17/33" · first_won "First serve points won" "16/17" (x_first_den, should equal
    first_in) · second_won "Second serve points won" "12/16" (x_second_den, should equal svpt - first_in) · ace "Aces" ·
    df "Double faults" · bp_faced / bp_saved from the OPPONENT's "Break points converted" "5/13" (faced = the opponent's
    chances, saved = those less his conversions) · sv_won = first_won + second_won. Pages of the newer layout (42 held)
    add "Service points won" "27/40" (sv_won / svpt where "First serve" is missing), "Break points saved" "2/4" (the
    player's own, preferred to the opponent's line) and "Service games won" "6/8" (sv_gms = played); the usual layout
    gives no service games (sv_gms NaN).
Link: the pages' own players, day (reference_utc), round and set scores (oriented by set_winners), linked by
srcc_common.link per season on the study's snapshot of Stage 0 (tp_common.link), with TennisLive's player ids for the
id pass; as candidate_stage0.py links them. Orientation: the linker's p1_side (names; never by who won).
A page whose statistics may belong to the other player: candidate_stage0.py found TennisLive's two players' statistics
exchanged on 2 of 36 tour matches it checked and leaves out a page whose winner took under 45% of the points; here such
a page is kept with x_swap_suspect and is not complete.
complete: the page says finished (not a walkover), the eight statistics are there for both players, and the page is
not a swap suspect.
x_src_won: the page's winner_id, oriented.
Writes box/readers/tp_tennislive_stats.{parquet,json}.
Run: ./python.sh src/eda/source_reconciliation/tp_tennislive.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import tp_common as T  # noqa: E402

READER, FAMILY = "tp_tennislive_stats", "tennislive"
TL = C.DUMP / "points" / "tennislive"
STATS = {"First serve": "fs", "First serve points won": "fw", "Second serve points won": "sw",
         "Break points converted": "bpc", "Total points won": "tp", "Aces": "ace", "Double faults": "df",
         "Service points won": "spw", "Break points saved": "bps", "Service games won": "sgw"}
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


def frac(v) -> tuple[float, float]:
    m = FRAC.match(str(v or ""))
    return (float(m.group(1)), float(m.group(2))) if m else (np.nan, np.nan)


def main() -> int:
    t0 = time.time()
    rec = T.receipts([TL / "matches.parquet", TL / "statistics.parquet"])
    m = pd.read_parquet(TL / "matches.parquet")
    n_pages = len(m)
    m = m.drop_duplicates("url")
    fin = m["doubles"].eq("FALSE") & m["state"].eq("finished") & ~m["end_reason"].fillna("").eq("walkover")
    s = pd.read_parquet(TL / "statistics.parquet", columns=["url", "period", "name", "player1_value", "player1_detail",
                                                            "player2_value", "player2_detail"])
    s = s[s["period"].eq("match") & s["name"].isin(STATS)].assign(k=lambda d: d["name"].map(STATS))
    s = s.drop_duplicates(["url", "k"])
    rows = m[fin & m["url"].isin(set(s["url"]))].copy()
    W = pd.DataFrame(index=rows["url"])
    for side in (1, 2):
        for k in ("fs", "fw", "sw", "bpc", "tp", "spw", "bps", "sgw"):
            v = s[s["k"].eq(k)].set_index("url")[f"player{side}_detail"]
            fr = rows["url"].map(v).map(frac)
            W[f"{k}{side}_n"], W[f"{k}{side}_d"] = fr.str[0].to_numpy(), fr.str[1].to_numpy()
        for k in ("ace", "df"):
            v = s[s["k"].eq(k)].set_index("url")[f"player{side}_value"]
            W[f"{k}{side}"] = pd.to_numeric(rows["url"].map(v), errors="coerce").to_numpy()
    out = pd.DataFrame(index=W.index)
    for side, opp in ((1, 2), (2, 1)):
        out[f"p{side}_first_in"] = W[f"fs{side}_n"]
        out[f"p{side}_svpt"] = W[f"fs{side}_d"].where(W[f"fs{side}_d"].notna(), W[f"spw{side}_d"])
        out[f"p{side}_first_won"], out[f"p{side}_x_first_den"] = W[f"fw{side}_n"], W[f"fw{side}_d"]
        out[f"p{side}_second_won"], out[f"p{side}_x_second_den"] = W[f"sw{side}_n"], W[f"sw{side}_d"]
        out[f"p{side}_ace"], out[f"p{side}_df"] = W[f"ace{side}"], W[f"df{side}"]
        own = W[f"bps{side}_d"].notna()
        out[f"p{side}_bp_faced"] = np.where(own, W[f"bps{side}_d"], W[f"bpc{opp}_d"])
        out[f"p{side}_bp_saved"] = np.where(own, W[f"bps{side}_n"], W[f"bpc{opp}_d"] - W[f"bpc{opp}_n"])
        out[f"p{side}_sv_gms"] = W[f"sgw{side}_d"]
        sv = W[f"fw{side}_n"] + W[f"sw{side}_n"]
        out[f"p{side}_sv_won"] = sv.where(sv.notna(), W[f"spw{side}_n"])
        out[f"p{side}_x_total_points_won"] = W[f"tp{side}_n"]
    rows = rows.set_index("url")
    win = np.where(rows["winner_id"].astype(str).eq(rows["player2_id"].astype(str)), 2,
                   np.where(rows["winner_id"].astype(str).eq(rows["player1_id"].astype(str)), 1, 0))
    tp_w = np.where(win == 1, out["p1_x_total_points_won"], out["p2_x_total_points_won"])
    tp_all = out["p1_x_total_points_won"] + out["p2_x_total_points_won"]
    with np.errstate(invalid="ignore", divide="ignore"):
        share = tp_w / tp_all
    out["x_winner_points_share"] = share
    out["x_swap_suspect"] = (share < 0.45) & (win > 0)
    # set scores, player 1 first (the page writes each set from its winner's side; set_winners: 0 = player 1)
    sets = []
    for st, sw_ in zip(rows["sets"].fillna(""), rows["set_winners"].fillna("")):
        toks = re.findall(r"(\d+)-(\d+)(?:\((\d+)\))?", str(st))
        who = str(sw_).split(";")
        p1f = []
        for i, (a, b, _) in enumerate(toks):
            a, b = int(a), int(b)
            first_won_set = a > b
            p1_won_set = (who[i] == "0") if i < len(who) and who[i] in ("0", "1") else first_won_set
            p1f.append((a, b) if first_won_set == p1_won_set else (b, a))
        sets.append(tuple(p1f))
    tour = pd.Series(rows.index, index=rows.index).str.extract(r"^/(atp|wta)/", expand=False)
    day = pd.to_datetime(rows["reference_utc"].astype(str).str[:10], format="%Y-%m-%d", errors="coerce")
    src = pd.DataFrame({"sid": "tennislive:" + rows.index.to_series().astype(str), "tour": tour.to_numpy(),
                        "day": day.to_numpy(), "p1": rows["player1_name"].to_numpy(), "p2": rows["player2_name"].to_numpy(),
                        "sets": sets, "rnd": rows["stage"].map(T.K.round_code).to_numpy(),
                        "qual": rows["stage"].fillna("").str.contains("qualif").to_numpy(), "tid": None,
                        "id1": rows["player1_id"].astype(str).to_numpy(), "id2": rows["player2_id"].astype(str).to_numpy()})
    ok = src["tour"].notna() & src["day"].notna()
    links, reason, amb = T.link(src[ok].reset_index(drop=True))
    lk = links.set_index("sid")
    out["sid"] = "tennislive:" + out.index.to_series().astype(str)
    J = out[out["sid"].isin(lk.index)].copy()
    J["match_id"] = J["sid"].map(lk["match_id"])
    J["a1"] = J["sid"].map(lk["p1_side"]).eq("A")
    J["link_method"] = "identity_" + J["sid"].map(lk["pass"]).astype(str)
    R = rows.loc[J.index]
    eight = [f"p{k}_{c}" for k in (1, 2) for c in ("first_in", "svpt", "first_won", "second_won", "ace", "df",
                                                   "bp_faced", "bp_saved")]
    J["complete"] = J[eight].notna().all(axis=1) & ~J["x_swap_suspect"].astype(bool)
    w = J.rename(columns={"sid": "source_key"}).reset_index(drop=True)
    wv = win[rows.index.get_indexer(J.index)]
    w["p1_x_src_won"] = np.where(wv > 0, wv == 1, np.nan)
    w["p2_x_src_won"] = np.where(wv > 0, wv == 2, np.nan)
    w["p1_x_src_name"], w["p2_x_src_name"] = R["player1_name"].to_numpy(), R["player2_name"].to_numpy()
    w["x_url"] = J.index.to_numpy()
    w["x_collection"] = np.where(R["gaps_in"].notna(), "P5:" + R["gaps_in"].astype(str),
                                 np.where(R["sampled_in"].notna(), "P4:" + R["sampled_in"].astype(str), "careers"))
    w["x_end_reason"] = R["end_reason"].to_numpy()
    w["x_score_agrees"] = J["sid"].map(lk["sc"]).astype(bool).to_numpy()
    rows_out = T.to_contract(w, READER, FAMILY, "box",
                             player_extra=["x_first_den", "x_second_den", "x_total_points_won", "x_src_won",
                                           "x_src_name"],
                             match_extra=["x_url", "x_collection", "x_end_reason", "x_score_agrees",
                                          "x_winner_points_share", "x_swap_suspect"])
    rows_out["x_src_won"] = rows_out["x_src_won"].astype("boolean")
    cons = {"first_den_equals_first_in": (rows_out["x_first_den"] == rows_out["first_in"]),
            "second_den_equals_svpt_minus_first_in": (rows_out["x_second_den"] == rows_out["svpt"] - rows_out["first_in"])}
    have = rows_out[["first_in", "svpt", "x_first_den", "x_second_den"]].notna().all(axis=1)
    rs = reason.value_counts()
    summary = {
        "inputs": rec,
        "records": {"pages": int(n_pages), "distinct_pages": int(len(m)), "finished_singles_not_walkover": int(fin.sum()),
                    "with_match_statistics": int(len(rows)),
                    "by_collection": T.tidy_counts(pd.Series(np.where(rows["gaps_in"].notna(), "P5",
                                                                     np.where(rows["sampled_in"].notna(), "P4",
                                                                              "careers"))).value_counts())},
        "linked": {"offered": int(ok.sum()), "linked": int(len(links)),
                   "by_pass": T.tidy_counts(links["pass"].value_counts())},
        "dropped": {"no_tour_or_day": int((~ok).sum()), "not_linked_by_reason": T.tidy_counts(rs[rs.index != "linked"]),
                    "ambiguous": int(len(amb))},
        "checks": {"swap_suspects_linked": int(J["x_swap_suspect"].sum()), "complete": int(J["complete"].sum())},
        "self_consistency_share": {k: round(float(v[have].mean()), 5) for k, v in cons.items()},
        "contract_checks": T.check_contract(rows_out),
        "winner_vs_stage0": T.winner_check(rows_out),
        "definitions": __doc__.split("Mapping (period")[1].split("Writes box")[0].strip(),
        "sanity_vs_stage0_by_level_group": T.records(T.sanity(rows_out, by=["level_group"])),
        "hand_check": {"keys": T.sample_keys(rows_out, where=rows_out["complete"]), "status": "pending"},
    }
    T.write_reader(rows_out, READER, summary)
    T.log(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
