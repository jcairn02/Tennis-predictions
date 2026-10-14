"""F4: which row of each copied pair carries a box that cannot be its own (from x40_f4.py's f4_pairs.csv).

A row's box is judged NOT its own (copy, to blank) only on evidence that one miscounted break cannot produce:
    * B5 with service games recorded: the box's service games differ from the row's games by 2 or more;
    * serve points per game outside every clean match of its kind (conditional tail < 0.1% among clean completed WTA
      tour/Slam matches 2010-19 with the same number of sets and +-1 games), or the minimum-points rule broken;
    * the games identity without service games missing by |D| >= 4 (two or more breaks would have to be miscounted);
    * the Match Charting Project's chart of that match contradicts the box (<= 25% of counts equal).
A pair decided only by |D| = 2-3 (one break away) or by nothing is left as it is (not clear).
Writes f4_verdict_rows.csv (every row) and f4_scope.csv (the rows confirmed for blanking).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

o = pd.read_csv(rc.OUT / "f4_pairs.csv")
m, p = rc.stage0()

# clean reference: serve points per game by sets and games
mm = m[m.has_box & m.status.eq("completed") & m.year.between(2010, 2019) & m.tour.eq("wta")
       & m.level.isin(["GS", "T1000", "T500", "T250"])]
Wc = rc.wide(mm, p[p.match_id.isin(mm.match_id)])
sp = rc.score_parts(Wc["score"])
ref = pd.DataFrame({"g": sp.games_w + sp.games_l - sp.std_tb, "sets": sp.sets_w + sp.sets_l,
                    "ppg": (Wc.w_svpt + Wc.l_svpt) / (sp.games_w + sp.games_l - sp.std_tb)})


def tail(ppg: float, games_played: int, sets: int) -> float:
    r = ref[(ref.sets == sets) & ref.g.between(games_played - 1, games_played + 1)].ppg
    if len(r) < 200:
        r = ref.ppg
    return float(min((r <= ppg).mean(), (r >= ppg).mean()))


W = rc.wide(m[m.match_id.isin(o.match_id.dropna())], p[p.match_id.isin(o.match_id.dropna())]).set_index("match_id")
raws = {}


def rawrow(f, r):
    tour = "atp" if "/atp/" in f else "wta"
    name = f.split("/")[-1].replace(".csv", ".parquet")
    if name not in raws:
        raws[name] = pd.read_parquet(rc.SACK / tour / name).set_index("_row")
    return raws[name].loc[int(r)], tour


def num(x):
    s = str(x).strip()
    return float(s) if s not in ("", "nan", "<NA>", "None") else np.nan


rows = []
for _, d in o.iterrows():
    rr, tour = rawrow(d["_source_file"], d["_row"])
    s0 = W.loc[d.match_id]
    flip = s0.w_player_id != f"{tour}:{rr['winner_id']}"
    gw, gl = (s0.l_games_won_n, s0.w_games_won_n) if flip else (s0.w_games_won_n, s0.l_games_won_n)
    tw, tl = (s0.l_tb_won_n, s0.w_tb_won_n) if flip else (s0.w_tb_won_n, s0.l_tb_won_n)
    B = (num(rr.w_bpFaced) - num(rr.w_bpSaved)) - (num(rr.l_bpFaced) - num(rr.l_bpSaved))
    dg, dtb = gw - gl, (tw if pd.notna(tw) else 0) - (tl if pd.notna(tl) else 0)
    dmin = min(abs(dg + 2 * B - dtb), abs(dg + 2 * B))
    spr = rc.score_parts(pd.Series([s0.score]))
    played = int(spr.games_w[0] + spr.games_l[0] - spr.std_tb[0])
    sets = int(spr.sets_w[0] + spr.sets_l[0])
    tl_ = tail(d.pts_per_game, played, sets)
    svg_gap = abs(d.svg_total - d.games) if pd.notna(d.svg_total) else np.nan
    svg_gap_ex = abs(d.svg_total - played) if pd.notna(d.svg_total) else np.nan
    strong = []
    if pd.notna(svg_gap) and min(svg_gap, svg_gap_ex) >= 2:
        strong.append(f"B5: box service games {d.svg_total:g} against {d.games} games played")
    if tl_ < 0.001:
        strong.append(f"serve points per game {d.pts_per_game} (tail {tl_:.4f} among clean matches like it)")
    if not d.min_points_ok:
        strong.append("minimum-points rule broken")
    if dmin >= 4:
        strong.append(f"games identity misses by |D|={dmin:g} (two or more breaks)")
    if d.mcp == "contradicts":
        strong.append(f"MCP's chart contradicts the box ({d.mcp_agreement_with_box})")
    rows.append({**d.to_dict(), "Dmin": dmin, "ppg_tail": round(tl_, 5), "strong_evidence_box_not_own": "; ".join(strong)})
x = pd.DataFrame(rows)

# decide per group
x["verdict"] = ""
x["reason"] = ""
for gname, g in x.groupby("group"):
    not_own = g["strong_evidence_box_not_own"].ne("")
    if not_own.all():
        for i in g.index:
            x.loc[i, ["verdict", "reason"]] = ["copy_confirmed",
                                               "the box cannot belong to this row or to the other(s): "
                                               + x.loc[i, "strong_evidence_box_not_own"]]
        continue
    for i in g.index:
        if not_own[i]:
            x.loc[i, ["verdict", "reason"]] = ["copy_confirmed", x.loc[i, "strong_evidence_box_not_own"]]
        elif not_own.any() and g.loc[i, "fits"]:
            x.loc[i, ["verdict", "reason"]] = ["genuine", "the box fits this row's score; left unchanged"]
        else:
            why = ("weak: the other row fails only the games identity by |D|=2-3 (one miscounted break)"
                   if g["role"].isin(["copy", "genuine"]).any() else "both rows fit (or neither); no record decides")
            x.loc[i, ["verdict", "reason"]] = ["not_clear", why]
x.to_csv(rc.OUT / "f4_verdict_rows.csv", index=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 120)
print(x["verdict"].value_counts().to_string())
print(x[["event", "date", "round", "match", "verdict", "reason"]].to_string())
sc = x[x["verdict"].eq("copy_confirmed")][["match_id", "match", "event", "date", "round", "_source_file", "_row",
                                            "stage0_has_box", "reason"]]
sc = sc.assign(operation="blank all nine counts of both players on this row (box missing)")
sc.to_csv(rc.OUT / "f4_scope.csv", index=False)
print("rows confirmed for blanking:", len(sc), "already without a Stage 0 box:", int((~sc["stage0_has_box"]).sum()))
