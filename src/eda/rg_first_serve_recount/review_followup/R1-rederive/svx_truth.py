"""R1-rederive (group SVX): the true service games from the row's score and the proven first server; the swaps.

Inputs (mine): work/svx_files.parquet, work/svx_games.parquet (svx_parse.py); Stage 0's raw rows
(work/stage0_rg_rows.parquet, work/stage0_ao_rows.parquet, read with stage0_build.normalise(load_raw())); my RG links
(links.csv: RG's documents to Stage 0 rows by names, winner and games) and RG's documents (work/rg_api.parquet), whose
player ids are MatchBeats' ids. AO 2025 files are linked here to Sackmann's rows by names within tour and round.

The first server is proven (all must hold):
  P1  the file's games are in order (set, game strictly increasing) and no service game has points of both servers;
  P2  the file's first game is set 1 game 1, the set's first game (set score 1-0 or 0-1 after it);
  P3  every game the file holds is served by the player the alternation names from that first server, the games of
      earlier sets counted from the row's score, a tiebreak taking its turn by its first point;
  P4  each set the file holds whole has the row's games, counted by the games' winners.
The truth: walking the row's score set by set, game by game, servers alternate from the first server; a 7-6 set's last
game is its tiebreak, which takes a turn and is not counted; a retirement's score holds its finished games only.
A row is "swapped" when its two counts are the truth's exchanged and the truth's two differ.

Writes svx_rows.csv (one row per Stage 0 match with a file: the proof, the truth, the class) and svx_mine.csv (my
swaps, before any comparison). Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/svx_truth.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"
AO_ROUND = {"7": "F", "6": "SF", "5": "QF", "4": "R16", "3": "R32", "2": "R64", "1": "R128"}
AO_QROUND = {"3": "Q3", "2": "Q2", "1": "Q1"}


def toks(name) -> frozenset:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return frozenset(t for t in re.sub(r"[^a-z]+", " ", s).split() if t)


def sim(a, b) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def sets_of(score: str) -> tuple[list[tuple[int, int]], str]:
    out, rest = [], []
    for tok in str(score or "").split():
        m = re.match(r"^(\d+)-(\d+)(\(\d+(?:-\d+)?\))?$", tok)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
        else:
            rest.append(tok)
    return out, " ".join(rest)


def truth(score: str, first_is_w: bool) -> dict:
    """Service games of the row's winner and loser from its score, the winner serving first or not."""
    sets, marker = sets_of(score)
    pos, sv = 0, {"w": 0, "l": 0}
    first, second = ("w", "l") if first_is_w else ("l", "w")
    flags = []
    for a, b in sets:
        tb = max(a, b) == 7 and min(a, b) == 6
        n = a + b
        for g in range(1, n + 1):
            pos += 1
            srv = first if pos % 2 == 1 else second
            if tb and g == n:
                continue            # the tiebreak takes its turn, uncounted
            sv[srv] += 1
    if re.search(r"RET|DEF|W/O|ABN|ABD", marker, re.I):
        flags.append(marker)
        last = sets[-1] if sets else None
        if last and max(last) == 7 and min(last) == 6:
            flags.append("retired at 7-6: tiebreak assumed")
    return {"t_w": sv["w"], "t_l": sv["l"], "flags": "; ".join(flags)}


def positions(score: str) -> dict:
    """(set, game) -> alternation position, from the row's score (the winner's games first)."""
    sets, _ = sets_of(score)
    out, pos = {}, 0
    for k, (a, b) in enumerate(sets, 1):
        for g in range(1, a + b + 1):
            pos += 1
            out[(k, g)] = pos
    return out


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_rows", 200)
    files = pd.read_parquet(WORK / "svx_files.parquet")
    games = pd.read_parquet(WORK / "svx_games.parquet")
    files = files[files["status"].eq("ok")]
    gx = {k: g.sort_values("order") for k, g in games.groupby(["slam", "year", "code"])}
    # ---------------- rows and links
    rg = pd.read_parquet(WORK / "stage0_rg_rows.parquet")
    rg = rg[rg["source"].eq("sackmann") | (rg["source"].eq("tml") & rg["group"].eq("atp_qualifying")
                                           & rg["tid"].eq("2026-520"))]
    links = pd.read_csv(HERE / "links.csv")
    links = links[links["state"].eq("paired") & links["label"].eq("stage0")]
    api = pd.read_parquet(WORK / "rg_api.parquet")
    pid = api.set_index(["year", "code", "team"])["player_id"]
    rec = []
    for L in links.itertuples():
        rec.append({"slam": "RG", "year": int(L.year), "code": L.code, "rid": int(L.rid),
                    "w_pid": str(pid.get((L.year, L.code, L.w_team))), "l_pid": str(pid.get((L.year, L.code, L.l_team))),
                    "link_sim": min(L.sim_w, L.sim_l), "winner_agrees": bool(L.winner_agrees)})
    ao = pd.read_parquet(WORK / "stage0_ao_rows.parquet")
    ao = ao[ao["source"].eq("sackmann")]
    af = files[files["slam"].eq("AO")].copy()
    af["tour"] = np.where(af["code"].str[0].eq("M"), "atp", "wta")
    af["round"] = [(AO_QROUND if c[1] == "Q" else AO_ROUND)[c[2]] for c in af["code"]]
    for (tour, rnd), grp in af.groupby(["tour", "round"]):
        rows = ao[ao["tour"].eq(tour) & ao["round"].eq(rnd)]
        fl, rl = grp.to_dict("records"), rows.to_dict("records")
        t1 = [toks(f"{f['first1']} {f['last1']}") for f in fl]
        t2 = [toks(f"{f['first2']} {f['last2']}") for f in fl]
        tw = [toks(r["winner_name"]) for r in rl]
        tl = [toks(r["loser_name"]) for r in rl]
        sc = np.array([[max(sim(t1[i], tw[j]) + sim(t2[i], tl[j]), sim(t1[i], tl[j]) + sim(t2[i], tw[j]))
                        for j in range(len(rl))] for i in range(len(fl))])
        for i, j in zip(*linear_sum_assignment(-sc)):
            if sc[i, j] < 1.0:
                continue
            f, r = fl[i], rl[j]
            one_w = sim(t1[i], tw[j]) + sim(t2[i], tl[j]) >= sim(t1[i], tl[j]) + sim(t2[i], tw[j])
            rec.append({"slam": "AO", "year": 2025, "code": f["code"], "rid": int(r["rid"]),
                        "w_pid": f["id1"] if one_w else f["id2"], "l_pid": f["id2"] if one_w else f["id1"],
                        "link_sim": min(sim(t1[i] if one_w else t2[i], tw[j]), sim(t2[i] if one_w else t1[i], tl[j])),
                        "winner_agrees": f["match_winner"] == ("1" if one_w else "2")})
    lk = pd.DataFrame(rec)
    allrows = pd.concat([rg.assign(slam="RG"), ao.assign(slam="AO")], ignore_index=True)
    allrows = allrows.drop_duplicates("rid")
    lk = lk.merge(allrows[["rid", "source", "tour", "round", "season", "winner_name", "loser_name", "score", "w_SvGms",
                           "l_SvGms", "w_bpFaced", "w_bpSaved", "l_bpFaced", "l_bpSaved", "_source_file", "_row",
                           "s0_match_id", "tourney_id"]], on="rid", how="left")
    lk = lk.merge(files[["slam", "year", "code", "id1", "id2", "order_ok", "games", "first_set", "first_game",
                         "first_server", "first_gs1", "first_gs2", "match_complete"]], on=["slam", "year", "code"],
                  how="left")
    lk = lk.rename(columns={"_source_file": "source_file", "_row": "source_row"})   # itertuples drops "_" names
    # ---------------- proof and truth
    x = classify(prove(lk, gx))
    report(x)


def prove(lk: pd.DataFrame, gx: dict) -> pd.DataFrame:
    """P1-P4 and the truth for every linked row (columns of lk: slam, year, code, w_pid, id1, id2, order_ok,
    first_set, first_game, first_server, first_gs1, first_gs2, score, ...); gx maps (slam, year, code) to the file's
    games in order. Used for this round's editions and the addendum's."""
    out = []
    for r in lk.itertuples():
        d = r._asdict()
        if pd.isna(r.id1):
            d.update({"proof": "no_file"})
            out.append(d)
            continue
        mbw = "1" if r.w_pid == r.id1 else ("2" if r.w_pid == r.id2 else None)
        g = gx[(r.slam, r.year, r.code)]
        pos = positions(r.score)
        p1 = bool(r.order_ok) and not g["mixed"].any()
        # P2: the file's first game is set 1 game 1, the set's first game (set score 1-0 or 0-1 after it). Its first
        # point need not be the game's (a file may lack it); every point of a service game has the same server.
        g0 = g.iloc[0]
        try:
            opens = int(g0["set1"]) + int(g0["set2"]) == 1
        except (TypeError, ValueError):
            opens = False
        p2_point = {(r.first_gs1, r.first_gs2)} <= {("15", "0"), ("0", "15")}   # recorded: the first point opens it
        # either the set score after it (1-0 or 0-1) or its first point (15-0 or 0-15) shows the file's first game is
        # the match's first; old files (RG 2013-2017) leave the set-score field empty, so the point alone can show it
        p2 = r.first_set == 1 and r.first_game == 1 and int(g0["set"]) == 1 and int(g0["game"]) == 1 and \
            (opens or p2_point)
        fs = r.first_server
        held, bad, beyond = 0, 0, 0
        for x in g.itertuples():
            if x.server is None:
                continue
            p = pos.get((x.set, x.game))
            if p is None:
                beyond += 1          # past the row's games (a retirement's unfinished game) or not in the score
                continue
            held += 1
            exp = fs if p % 2 == 1 else ("2" if fs == "1" else "1")
            bad += x.server != exp
        p3 = held > 0 and bad == 0
        # P4: each set the file holds whole (games 1..n, every one finished) has the row's games, counted by the
        # games' winners from the row winner's side (the set-score field is not used: it can be wrong after a
        # tiebreak, 8-6 for 7-6 in RG 2021 SD103)
        sets, _ = sets_of(r.score)
        p4, sets_held = True, 0
        for k, (a, b) in enumerate(sets, 1):
            gs = g[g["set"].eq(k)]
            n = len(gs)
            if n == 0 or mbw is None or list(gs["game"]) != list(range(1, n + 1)) or not gs["complete"].all():
                continue
            if max(a, b) >= 6 and n != a + b:      # a finished set of the row: the file must hold its games
                if n < a + b:
                    continue                       # the file stops inside the set: not held whole
                p4 = False
                continue
            other = "2" if mbw == "1" else "1"
            gw = int((gs["winner"] == mbw).sum())
            gl = int((gs["winner"] == other).sum())
            unknown = n - gw - gl                  # a game whose winner the file leaves as "0" (AO 2025 has 117)
            if n == a + b:
                sets_held += 1
                if (unknown == 0 and (gw, gl) != (a, b)) or gw > a or gl > b:
                    p4 = False
        proven = p1 and p2 and p3 and p4 and mbw is not None and fs in ("1", "2")
        d.update({"mb_w_team": mbw, "p1_order": p1, "p2_opens": bool(p2), "p2_first_point_opens": bool(p2_point),
                  "p3_alternation": p3, "p4_sets": p4, "sets_held_whole": sets_held,
                  "games_checked": held, "games_off": bad, "games_beyond_score": beyond,
                  "proof": "proven" if proven else "unproven"})
        if proven:
            t = truth(r.score, fs == mbw)
            d.update(t)
            # MatchBeats' own count of completed non-tiebreak games, where it holds every game of the score
            reg = g[~g["tb"] & g["complete"] & g["server"].notna()]
            n_reg = sum(a + b - (1 if max(a, b) == 7 and min(a, b) == 6 else 0) for a, b in sets)
            d["mb_whole"] = len(reg) == n_reg
            d["mb_w"] = int((reg["server"] == mbw).sum())
            d["mb_l"] = int((reg["server"] != mbw).sum())
        out.append(d)
    return pd.DataFrame(out)


def classify(x: pd.DataFrame) -> pd.DataFrame:
    """The class of each row against its truth, the winner-served-first reading, and B8 before and after."""
    for c in ("t_w", "t_l", "flags", "mb_whole", "mb_w", "mb_l"):
        if c not in x:
            x[c] = np.nan
    rw, rl_ = x["w_SvGms"], x["l_SvGms"]
    pr = x["proof"].eq("proven")
    x["cls"] = np.select(
        [~pr, rw.isna() | rl_.isna(), rw.eq(x["t_w"]) & rl_.eq(x["t_l"]),
         rw.eq(x["t_l"]) & rl_.eq(x["t_w"]) & x["t_w"].ne(x["t_l"])],
        ["unproven", "no_count", "equal", "swapped"], "other")
    # the winner-served-first reading: does the row equal the score's count with the winner serving first?
    wf = [truth(s, True) for s in x["score"].fillna("")]
    x["row_is_winner_first"] = rw.eq([t["t_w"] for t in wf]) & rl_.eq([t["t_l"] for t in wf])
    # B8 after the exchange: breaks conceded no more than service games
    x["b8_after_ok"] = ((x["w_bpFaced"] - x["w_bpSaved"]) <= x["l_SvGms"]) & \
        ((x["l_bpFaced"] - x["l_bpSaved"]) <= x["w_SvGms"])
    x["b8_before_ok"] = ((x["w_bpFaced"] - x["w_bpSaved"]) <= x["w_SvGms"]) & \
        ((x["l_bpFaced"] - x["l_bpSaved"]) <= x["l_SvGms"])
    return x


def report(x: pd.DataFrame, tag: str = "") -> None:
    """Write svx_rows<tag>.csv and svx_mine<tag>.csv, and print the tallies."""
    pr = x["proof"].eq("proven")
    x.to_csv(HERE / f"svx_rows{tag}.csv", index=False)
    sw = x[x["cls"].eq("swapped")]
    print("rows with a file:", int(x["proof"].ne("no_file").sum()), "| linked rows:", len(x))
    print(pd.crosstab([x["slam"], x["year"]], x["cls"], margins=True).to_string())
    print("\nswapped by source:", sw.groupby(["slam", "year", "source"]).size().to_dict())
    print("swapped rows equal to the winner-served-first reading:", int(sw["row_is_winner_first"].sum()), "of", len(sw))
    print("swapped rows with flags:", sw[sw["flags"].fillna("").ne("")][["slam", "year", "code", "score",
                                                                       "flags"]].to_string())
    print("B8 fails after the exchange:", int((~sw["b8_after_ok"]).sum()), "| before:", int((~sw["b8_before_ok"]).sum()))
    whole = x[pr & x["mb_whole"].astype(bool)]
    print("proven rows where MatchBeats holds every game: its own count equals the truth on",
          int((whole["mb_w"].eq(whole["t_w"]) & whole["mb_l"].eq(whole["t_l"])).sum()), "of", len(whole))
    print("unproven by reason:", {k: int((~x.loc[x["proof"].eq("unproven"), k].astype(bool)).sum())
                                  for k in ("p1_order", "p2_opens", "p3_alternation", "p4_sets")})
    sw[["slam", "year", "code", "source_file", "source_row", "s0_match_id", "winner_name", "loser_name", "score",
        "w_SvGms", "l_SvGms", "t_w", "t_l"]].to_csv(HERE / f"svx_mine{tag}.csv", index=False)


if __name__ == "__main__":
    main()
