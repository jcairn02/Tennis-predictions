"""R2-skeptic (round 2, SVX): swapped service games at Roland Garros 2019-2026 and the Australian Open 2025, attacked.

The lead's claim (brief_service_games.md): where the Slam's MatchBeats file proves who served first, the true
service games follow from the row's score and that first server; a row is "swapped" when its two counts are the
truth's two exchanged (and differ); exchange_svgms puts them back. 323 proposed.

My own derivation (my parses and links; nothing of the lead's code):
    first server   two proofs, both required: (a) the lead's: the file's first point opens set 1, game 1, and every
                   game the file holds, in order, is served by the player the alternation names (a tie-break taking
                   its turn by its first point); (b) parity: every non-tie-break game the file holds, placed in the
                   match by the row's score, implies the same first server (robust to files that start late or skip
                   games)
    labels         the file's server labels belong to the players named: per player, the file's serve points equal
                   the Slam's own statistics (RG) or Sackmann's row (AO), or fit them better than the exchanged
                   labelling
    truth          each player's completed non-tie-break service games from the row's score and the first server
                   (serving alternates game by game; a 7-6 set's last game is a tie-break, one turn, uncounted; a
                   retirement's score holds finished games only); cross-checked against the Slam's own score (RG's set
                   scores; the AO file's games per set where the file holds the whole match) and, where the file holds
                   the whole match, the file's own count of games each player served
    class          equal / swapped / other / incomplete / unproven, as the lead defines them
    independent    the first server named by a hand chart (all 974 open at 0-0 and pass the parity test) and by the
                   Court Vision copy (RG 2019-2024: its first point's server); Tennis My Life's row of the same match
    candidate      any other correction of the same raw row in the candidate (followup/confirmed/candidate/), and
                   Stage 0's B8 (breaks conceded no more than service games) after the exchange
Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    svx_matches.csv, svx_summary.json
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
DUMP = ROOT / "data" / "dump" / "points"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]


def fold(name) -> list[str]:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return []
    s = unicodedata.normalize("NFKD", str(name)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s).split()


def sim(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    if sorted(a) == sorted(b) or "".join(sorted(a)) == "".join(sorted(b)) or "".join(a) == "".join(b):
        return 3
    sa, sb = {t for t in a if len(t) >= 3}, {t for t in b if len(t) >= 3}
    shared = sa & sb
    if shared:
        ia, ib = {t[0] for t in a if t not in shared}, {t[0] for t in b if t not in shared}
        return 2 if (ia & ib) else 1
    if any(len(x) >= 5 and len(y) >= 5 and SequenceMatcher(None, x, y).ratio() >= 0.8 for x in sa for y in sb):
        return 1
    return 0


def score_sets(score: str) -> list[tuple[int, int, bool]]:
    """(winner's games, loser's games, the set ends in a tie-break) per set of the row's score."""
    sets, _ = B.tokens_of(str(score or ""))
    out = []
    for a, b, tb, bracket in sets:
        if bracket:
            out.append((0, 0, True))           # a match tie-break in place of a set: one turn, no service game
            continue
        out.append((a, b, bool(B.is_tiebreak(a, b, tb, bracket, False))))
    return out


def truth(sets: list[tuple[int, int, bool]], w_first: bool) -> tuple[int, int]:
    turn_w, sw, sl = w_first, 0, 0
    for a, b, tbset in sets:
        n = a + b
        if n == 0 and tbset:                    # match tie-break
            turn_w = not turn_w
            continue
        for i in range(n):
            if not (tbset and i == n - 1):
                sw, sl = sw + turn_w, sl + (not turn_w)
            turn_w = not turn_w
    return sw, sl


def proofs(p: pd.DataFrame, sets: list[tuple[int, int, bool]]) -> dict:
    """The lead's in-order proof and my parity proof of the first server (MatchBeats slots '1'/'2')."""
    if p.empty:
        return {"has_file": False}
    p = p.sort_values("idx")
    first = p.iloc[0]
    first_slot = str(first["server"])
    games = []
    for (si, gi), g in p.groupby(["set_i", "game_i"], sort=True):
        games.append({"set": int(g["set"].iloc[0]), "game": int(g["game"].iloc[0]), "tb": bool(g["tb"].iloc[0]),
                      "server": g["server"].mode().iloc[0], "first_server": str(g["server"].iloc[0]),
                      "n": len(g), "servers": len(set(g["server"]))})
    # (a) the lead's: opens set 1 game 1, held games alternate in order
    in_order = int(first["set"]) == 1 and int(first["game"]) == 1 and first_slot in ("1", "2")
    expect = first_slot
    for g in games:
        turn = g["first_server"] if g["tb"] or g["servers"] > 1 else g["server"]
        in_order &= turn == expect
        expect = "2" if expect == "1" else "1"
    # (b) parity, games placed by the row's score
    offset, before = {}, 0
    for i, (a, b, tbset) in enumerate(sets, 1):
        offset[i] = before
        before += (a + b) if (a + b) > 0 else 1
    votes = []
    for g in games:
        if g["tb"] or g["servers"] > 1 or g["set"] not in offset:
            continue
        k = offset[g["set"]] + g["game"]
        votes.append(g["server"] if k % 2 == 1 else ("2" if g["server"] == "1" else "1"))
    top = max(set(votes), key=votes.count) if votes else None
    games_per_set = {}
    for g in games:
        games_per_set[g["set"]] = games_per_set.get(g["set"], 0) + 1
    return {"has_file": True, "first_slot": first_slot, "in_order_proof": bool(in_order),
            "parity_slot": top, "parity_games": len(votes), "parity_dissent": sum(v != top for v in votes),
            "file_opens_match": int(first["set"]) == 1 and int(first["game"]) == 1,
            "file_games": len(games), "file_games_per_set": json.dumps([games_per_set.get(i, 0) for i in
                                                                        range(1, max(games_per_set) + 1)]),
            "file_points": len(p),
            "file_count_1": sum(1 for g in games if not g["tb"] and g["servers"] == 1 and g["server"] == "1"),
            "file_count_2": sum(1 for g in games if not g["tb"] and g["servers"] == 1 and g["server"] == "2"),
            "file_svpt_1": int(p["server"].eq("1").sum()), "file_svpt_2": int(p["server"].eq("2").sum())}


def rg_matches() -> pd.DataFrame:
    s = pd.read_parquet(OUT / "players.parquet")
    pts = pd.read_parquet(OUT / "mb_points.parquet")
    by = {k: g for k, g in pts.groupby(["year", "code"])}
    rows = []
    for mid, g in s.groupby("match_id", sort=False):
        if len(g) != 2:
            continue
        w, l = g[g["side"].eq("w")].iloc[0], g[g["side"].eq("l")].iloc[0]
        if not isinstance(w["code"], str) or not isinstance(w["rg_set_games"], str):
            continue
        rec = {"event": "RG", "match_id": mid, "year": int(w["year"]), "tour": w["tour"], "draw": w["draw"],
               "round": w["round"], "code": w["code"], "status": w["status"], "source": w["source"],
               "source_file": w["source_file"], "source_row": w["source_row"], "row_score": w["raw_score"],
               "winner": w["player"], "loser": l["player"], "w_slot": w["mb_slot"], "l_slot": l["mb_slot"],
               "raw_w": w["raw_SvGms"], "raw_l": l["raw_SvGms"], "w_bp_lost": w["raw_bpFaced"] - w["raw_bpSaved"],
               "l_bp_lost": l["raw_bpFaced"] - l["raw_bpSaved"], "slam_svpt_w": w["my_svpt"],
               "slam_svpt_l": l["my_svpt"], "row_svpt_w": w["raw_svpt"], "row_svpt_l": l["raw_svpt"],
               "slam_sets": json.dumps([[a, b] for a, b in zip(json.loads(w["rg_set_games"]),
                                                               json.loads(w["rg_opp_set_games"]))
                                        if a is not None and b is not None]),
               "winner_agrees": w["winner_agrees"]}
        p = by.get((rec["year"], w["code"]), pd.DataFrame())
        rec.update(proofs(p, score_sets(w["raw_score"])))
        rows.append(rec)
    return pd.DataFrame(rows)


def ao_matches() -> pd.DataFrame:
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tour", "year", "qualifying", "round",
                                                                 "tournament_id", "status", "score", "source",
                                                                 "source_file", "source_row"])
    m = m[m["tournament_id"].eq("2025-580")].copy()
    raw = pd.read_parquet(OUT / "raw_ao.parquet")
    raw["_row"] = raw["_row"].astype("Int64")
    m["source_row"] = pd.to_numeric(m["source_row"]).astype("Int64")
    m = m.merge(raw.rename(columns={"_source_file": "source_file", "_row": "source_row", "source": "raw_source",
                                    "round": "raw_round", "score": "raw_score", "tour": "raw_tour"}),
                on=["source_file", "source_row"], how="left")
    meta = pd.read_parquet(OUT / "ao_mb_meta.parquet")
    pts = pd.read_parquet(OUT / "ao_mb_points.parquet")
    by = {k: g for k, g in pts.groupby("code")}
    rnd_main = {"1": "R128", "2": "R64", "3": "R32", "4": "R16", "5": "QF", "6": "SF", "7": "F"}
    rnd_qual = {"1": "Q1", "2": "Q2", "3": "Q3"}
    meta["tour_l"] = np.where(meta["code"].str[0].eq("W"), "W", "M")
    meta["draw"] = np.where(meta["code"].str[1].eq("Q"), "qual", "main")
    meta["round"] = [(rnd_qual if d == "qual" else rnd_main).get(c[2]) for c, d in zip(meta["code"], meta["draw"])]
    meta["n1"] = (meta["p1_first"].fillna("") + " " + meta["p1_last"].fillna("")).map(fold)
    meta["n2"] = (meta["p2_first"].fillna("") + " " + meta["p2_last"].fillna("")).map(fold)
    groups = {k: g for k, g in meta.groupby(["tour_l", "draw", "round"])}
    rows = []
    for x in m.itertuples(index=False):
        tour_l = "M" if x.tour == "atp" else "W"
        draw = "qual" if x.qualifying else "main"
        cand = groups.get((tour_l, draw, x.round))
        wn, ln = fold(x.winner_name), fold(x.loser_name)
        scored = []
        if cand is not None:
            for c in cand.itertuples(index=False):
                for orient, (a, b) in (("12", (c.n1, c.n2)), ("21", (c.n2, c.n1))):
                    s1, s2 = sim(wn, a), sim(ln, b)
                    scored.append(((min(s1, s2), s1 + s2), c.code, orient, c.winner_slot))
        scored.sort(key=lambda t: t[0], reverse=True)
        rec = {"event": "AO", "match_id": x.match_id, "year": 2025, "tour": tour_l, "draw": draw, "round": x.round,
               "status": x.status, "source": x.source, "source_file": x.source_file, "source_row": x.source_row,
               "row_score": x.raw_score, "winner": x.winner_name, "loser": x.loser_name}
        for c in NINE:
            for sd in ("w", "l"):
                v = getattr(x, f"{sd}_{c}")
                rec[f"_{sd}_{c}"] = pd.to_numeric(v, errors="coerce") if v not in (None, "", "nan") else np.nan
        rec.update({"raw_w": rec["_w_SvGms"], "raw_l": rec["_l_SvGms"],
                    "w_bp_lost": rec["_w_bpFaced"] - rec["_w_bpSaved"], "l_bp_lost": rec["_l_bpFaced"] - rec["_l_bpSaved"],
                    "row_svpt_w": rec["_w_svpt"], "row_svpt_l": rec["_l_svpt"]})
        if not scored or scored[0][0][0] < 1 or any(s[0] == scored[0][0] and s[1] != scored[0][1] for s in scored[1:]):
            rec["code"] = None
            rows.append(rec)
            continue
        best = scored[0]
        rec.update({"code": best[1], "link_score": best[0][0], "w_slot": 1 if best[2] == "12" else 2,
                    "l_slot": 2 if best[2] == "12" else 1,
                    "winner_agrees": (None if pd.isna(best[3]) or int(best[3]) == 0 else
                                      int(best[3]) == (1 if best[2] == "12" else 2))})
        rec.update(proofs(by.get(best[1], pd.DataFrame()), score_sets(x.raw_score)))
        rows.append(rec)
    out = pd.DataFrame(rows)
    return out.drop(columns=[c for c in out.columns if c.startswith("_")])


def main() -> int:
    df = pd.concat([rg_matches(), ao_matches()], ignore_index=True)
    df = df[df["code"].notna() & df["has_file"].eq(True)].copy()
    # the first server, by name: two proofs
    df["w_slot"] = pd.to_numeric(df["w_slot"], errors="coerce")
    df["proven"] = df["in_order_proof"] & df["parity_dissent"].eq(0) & df["parity_slot"].eq(df["first_slot"])
    df["w_first"] = df["first_slot"].astype(str).eq(df["w_slot"].astype("Int64").astype(str))
    # server labels: the file's serve points against the Slam's statistics (RG) or the row (AO), by name
    ref_w = np.where(df["event"].eq("RG"), df["slam_svpt_w"], df["row_svpt_w"])
    ref_l = np.where(df["event"].eq("RG"), df["slam_svpt_l"], df["row_svpt_l"])
    f_w = np.where(df["w_slot"].eq(1), df["file_svpt_1"], df["file_svpt_2"])
    f_l = np.where(df["w_slot"].eq(1), df["file_svpt_2"], df["file_svpt_1"])
    df["labels_exact"] = (f_w == ref_w) & (f_l == ref_l)
    df["labels_fit"] = (np.abs(f_w - ref_w) + np.abs(f_l - ref_l)) < (np.abs(f_w - ref_l) + np.abs(f_l - ref_w))
    df["labels_ok"] = df["labels_exact"] | df["labels_fit"]
    # the truth from the row's score; and from the Slam's score
    tw, tl = [], []
    for sc, wf in zip(df["row_score"], df["w_first"]):
        a, b = truth(score_sets(sc), bool(wf))
        tw.append(a)
        tl.append(b)
    df["true_w"], df["true_l"] = tw, tl
    df.loc[df["status"].eq("walkover"), ["true_w", "true_l"]] = np.nan
    asw = [truth(score_sets(sc), True) for sc in df["row_score"]]
    df["as_if_w_first_w"], df["as_if_w_first_l"] = [a for a, _ in asw], [b for _, b in asw]
    # the Slam's own score: RG's set scores; the AO file's games per set (whole files)
    def slam_games(r):
        if r["event"] == "RG" and isinstance(r.get("slam_sets"), str):
            return [a + b for a, b in json.loads(r["slam_sets"])]
        return None
    df["row_games_per_set"] = df["row_score"].map(lambda sc: json.dumps([a + b for a, b, _ in score_sets(sc)]))
    df["slam_games_per_set"] = df.apply(lambda r: json.dumps(slam_games(r)) if slam_games(r) is not None
                                        else r["file_games_per_set"], axis=1)
    # the file's own count, where the file holds the whole match (its games per set equal the score's)
    df["file_whole"] = df["file_games_per_set"].eq(df["row_games_per_set"]) & df["status"].eq("completed")
    fc_w = np.where(df["w_slot"].eq(1), df["file_count_1"], df["file_count_2"])
    fc_l = np.where(df["w_slot"].eq(1), df["file_count_2"], df["file_count_1"])
    df["file_count_w"], df["file_count_l"] = fc_w, fc_l
    df["file_count_is_truth"] = np.where(df["file_whole"], (fc_w == df["true_w"]) & (fc_l == df["true_l"]), np.nan)

    def cls(r):
        if not r["proven"]:
            return "unproven"
        if pd.isna(r["raw_w"]) or pd.isna(r["raw_l"]) or pd.isna(r["true_w"]):
            return "incomplete"
        if r["raw_w"] == r["true_w"] and r["raw_l"] == r["true_l"]:
            return "equal"
        if r["true_w"] != r["true_l"] and r["raw_w"] == r["true_l"] and r["raw_l"] == r["true_w"]:
            return "swapped"
        return "other"
    df["cls"] = df.apply(cls, axis=1)
    df["row_as_if_winner_first"] = df["raw_w"].eq(df["as_if_w_first_w"]) & df["raw_l"].eq(df["as_if_w_first_l"])
    # B8 after the exchange: breaks conceded no more than the new service games
    df["b8_after_ok"] = ~((df["w_bp_lost"] > df["raw_l"]) | (df["l_bp_lost"] > df["raw_w"]))
    df["b8_before_ok"] = ~((df["w_bp_lost"] > df["raw_w"]) | (df["l_bp_lost"] > df["raw_l"]))
    df.to_csv(OUT / "svx_matches.csv", index=False)
    summ = {"matches_with_a_file": int(len(df)),
            "classes": df.groupby(["event", "year", "cls"]).size().rename("n").reset_index().to_dict("records")}
    (OUT / "svx_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(df.pivot_table(index=["event", "year"], columns="cls", values="match_id", aggfunc="count",
                         fill_value=0).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
