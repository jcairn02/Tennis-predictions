import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import rc, refs, pandas as pd, numpy as np
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
o = pd.read_csv(rc.OUT/"f4_pairs.csv")
m, p = rc.stage0()
W = rc.wide(m[m.match_id.isin(o.match_id.dropna())], p[p.match_id.isin(o.match_id.dropna())]).set_index("match_id")
raw = {}
def rawrow(f, r):
    tour = "atp" if "/atp/" in f else "wta"
    name = f.split("/")[-1].replace(".csv", ".parquet")
    if name not in raw:
        raw[name] = pd.read_parquet(rc.SACK/tour/name).set_index("_row")
    return raw[name].loc[int(r)]
out = []
for _, d in o.iterrows():
    rr = rawrow(d["_source_file"], d["_row"])
    s0 = W.loc[d.match_id]
    tour = "atp" if "/atp/" in d["_source_file"] else "wta"
    flip = s0.w_player_id != f"{tour}:{rr['winner_id']}"
    gw, gl = (s0.l_games_won_n, s0.w_games_won_n) if flip else (s0.w_games_won_n, s0.l_games_won_n)
    tw, tl = (s0.l_tb_won_n, s0.w_tb_won_n) if flip else (s0.w_tb_won_n, s0.l_tb_won_n)
    num = lambda x: float(pd.to_numeric(str(x), errors="coerce")) if str(x).strip() not in ("", "nan", "<NA>", "None") else np.nan
    B = (num(rr.w_bpFaced) - num(rr.w_bpSaved)) - (num(rr.l_bpFaced) - num(rr.l_bpSaved))
    dg, dtb = gw - gl, (tw or 0) - (tl or 0)
    D1, D2 = dg + 2*B - dtb, dg + 2*B
    out.append({"group": d.group[:60], "event": d.event, "round": d["round"], "role": d.role, "B": B, "dg": dg, "dtb": dtb,
                "Dmin": min(abs(D1), abs(D2)), "ppg": d.pts_per_game, "mcp": d.mcp, "svg": d.svg_total, "games": d.games,
                "min_pts": d.min_points_ok})
x = pd.DataFrame(out)
print(x.to_string())
