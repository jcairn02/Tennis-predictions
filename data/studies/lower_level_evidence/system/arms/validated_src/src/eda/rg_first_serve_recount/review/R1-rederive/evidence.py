"""R1-rederive: further evidence on the disputed sides, from my own tables and the raw MatchBeats files.

1. Radar evidence (RG 2023-2025, where MatchBeats fills faultSrvSpd, the speed of a faulted first serve): per server,
   the points labelled second serve that carry a measured first-serve fault. Their number is a lower bound on the
   server's second-serve points even where the point file misses points; a Sackmann side with fewer second-serve
   points (svpt - 1stIn) than that bound is impossible.
2. Pooled rates by edition: first serves in, first- and second-serve points won, Sackmann against RG's statistics.
3. The make-up of the disputed sides: sign, size, rate at which the moved points were won, what else differs (class B),
   and the corrected side's internal checks (Stage 0's B1-B3, B6, B7 and the stricter 2ndWon + df <= svpt - 1stIn).

Writes work/mb_radar.parquet, pooled_rates.csv, radar_sides.csv, and prints the summaries.
Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/evidence.py
"""
from __future__ import annotations

import glob
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.ingest.point_sources.infosys_slams import blocks_of, decrypt  # noqa: E402

HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive"
WORK = HERE / "work"
RAW = ROOT / "data" / "raw" / "point_sources" / "infosys_slams" / "RG"


def radar() -> pd.DataFrame:
    rows = []
    for year, route in [(y, "match-beats") for y in range(2019, 2025)] + [(2025, "match-centre")]:
        for path in sorted(glob.glob(str(RAW / str(year) / route / "*.json.gz"))):
            code = Path(path).name.split(".")[0]
            with gzip.open(path, "rb") as fh:
                blocks = blocks_of(route, json.loads(fh.read()))
            if "mbData" not in blocks:
                continue
            mb = decrypt(blocks["mbData"])
            if not isinstance(mb, dict) or not mb.get("setData"):
                continue
            c = {t: Counter() for t in ("1", "2")}
            for st in mb.get("setData") or []:
                for g in st.get("gameData") or []:
                    for p in g.get("pointData") or []:
                        t = str(p.get("server"))
                        if t not in c:
                            continue
                        spd = (p.get("serveSpeed") or 0) > 0
                        fault = (p.get("faultSrvSpd") or 0) > 0
                        if p.get("serve") == 1:
                            c[t]["n1"] += 1
                            c[t]["n1_spd"] += spd
                            c[t]["n1_fault"] += fault
                            c[t]["n1_spd_nofault"] += spd and not fault
                        else:
                            c[t]["n2"] += 1
                            c[t]["n2_fault"] += fault
                            c[t]["n2_spd"] += spd
            pdx = mb.get("playerData") or {}
            for t in ("1", "2"):
                rows.append({"year": year, "code": code, "player_id": str(pdx.get(f"tm{t}Ply1Id")),
                             **{k: c[t][k] for k in ("n1", "n1_spd", "n1_fault", "n1_spd_nofault", "n2", "n2_fault",
                                                     "n2_spd")}})
    return pd.DataFrame(rows)


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    d = pd.read_csv(HERE / "sides.csv", keep_default_na=False, na_values=[""], dtype={"rec_id": str})
    for c in ("m_complete", "m_split_agrees", "rec_checks"):
        d[c] = d[c].astype(str).eq("True")
    # ---------------- 1. radar
    rad = radar()
    rad.to_parquet(WORK / "mb_radar.parquet", index=False)
    rg = d[d["event"].eq("RG")].merge(rad, left_on=["year", "key", "rec_id"], right_on=["year", "code", "player_id"],
                                      how="left")
    rg["s_second_pts"] = rg["s_svpt"] - rg["s_first_in"]
    rg["o_second_pts"] = rg["o_svpt"] - rg["o_first_in"]
    rg["radar_rules_out_sack"] = rg["n2_fault"] > rg["s_second_pts"]
    rg["radar_rules_out_official"] = rg["n2_fault"] > rg["o_second_pts"]
    dis = rg[rg["year"].ge(2023) & rg["cls"].isin(["split", "split_other"])]
    print("\n[1] radar, RG 2023-2025 disputed sides: does the count of points with a measured first-serve fault "
          "exceed Sackmann's second-serve points?")
    print(pd.crosstab([dis["year"], dis["sign"]], [dis["radar_rules_out_sack"]], margins=True))
    print("radar rules out the official split on", int(dis["radar_rules_out_official"].sum()), "disputed sides;",
          "on all RG 2023-25 linked sides:", int(rg[rg["year"].ge(2023)]["radar_rules_out_official"].sum()))
    # how much of the '+' gap does the radar cover?
    plus = dis[dis["sign"].eq("+")]
    cover = (plus["n2_fault"] - plus["s_second_pts"]).clip(lower=0)
    print("'+' sides 2023-25:", len(plus), "| gap (official - Sackmann second-serve points) total",
          int((plus["o_second_pts"] - plus["s_second_pts"]).sum()), "| shown impossible by radar on",
          int(plus["radar_rules_out_sack"].sum()), "sides, covering", int(cover.sum()), "of the moved points")
    minus = dis[dis["sign"].isin(["-", "0"])]
    print("'-'/'0' sides 2023-25:", len(minus), "; serve-1 points with a measured speed and no fault speed exceed "
          "Sackmann's first serves in on", int((minus["n1_spd_nofault"] > minus["s_first_in"]).sum()))
    # radar on the clean years, as a control of the bound itself: 2023-25 equal sides
    eq = rg[rg["year"].ge(2023) & rg["cls"].eq("equal")]
    print("control: equal sides 2023-25 where the radar bound exceeds the (agreed) second-serve points:",
          int(eq["radar_rules_out_sack"].sum()), "of", len(eq))
    rg.to_csv(HERE / "radar_sides.csv", index=False)

    # ---------------- 2. pooled rates by edition
    sack = pd.read_parquet(WORK / "sackmann_rows.parquet")
    api = pd.read_parquet(WORK / "rg_api.parquet")
    rows = []
    s_rg = sack[sack["event"].eq("RG")].copy()
    s_rg["qual"] = s_rg["round"].str.fullmatch(r"Q\d")
    for (y, tour, q), g in s_rg.groupby(["year", "tour", "qual"]):
        tot = {k: g[f"w_{k}"].sum() + g[f"l_{k}"].sum() for k in ("svpt", "1stIn", "1stWon", "2ndWon", "df")}
        ok = g["w_svpt"].notna() & g["l_svpt"].notna()
        rows.append({"source": "sackmann", "event": "RG", "year": y, "tour": tour, "qual": q, "rows": int(ok.sum()),
                     "first_in_pct": tot["1stIn"] / tot["svpt"], "first_won_pct": tot["1stWon"] / tot["1stIn"],
                     "second_won_pct": tot["2ndWon"] / (tot["svpt"] - tot["1stIn"])})
    a = api[api["has_stats"]].copy()
    a["tour"] = np.where(a["family"].isin(["SM", "QM"]), "atp", "wta")
    a["qual"] = a["family"].str.startswith("Q")
    for (y, tour, q), g in a.groupby(["year", "tour", "qual"]):
        rows.append({"source": "rg_official", "event": "RG", "year": y, "tour": tour, "qual": q, "rows": len(g) // 2,
                     "first_in_pct": g["first_in"].sum() / g["svpt"].sum(),
                     "first_won_pct": g["first_won"].sum() / g["first_in"].sum(),
                     "second_won_pct": g["second_won"].sum() / (g["svpt"].sum() - g["first_in"].sum())})
    og = d[d["event"].eq("OG")]
    for (tour), g in og.groupby("tour"):
        for src, p in (("sackmann", "s_"), ("og_official", "o_")):
            h = g[g["s_svpt"].notna() & g["o_svpt"].notna()]
            rows.append({"source": src, "event": "OG", "year": 2024, "tour": tour, "qual": False, "rows": len(h) // 2,
                         "first_in_pct": h[f"{p}first_in"].sum() / h[f"{p}svpt"].sum(),
                         "first_won_pct": h[f"{p}first_won"].sum() / h[f"{p}first_in"].sum(),
                         "second_won_pct": h[f"{p}second_won"].sum() / (h[f"{p}svpt"].sum() - h[f"{p}first_in"].sum())})
    pr = pd.DataFrame(rows)
    pr.to_csv(HERE / "pooled_rates.csv", index=False)
    print("\n[2] pooled first-serve-in rate by edition (Sackmann | RG's statistics)")
    piv = pr.pivot_table(index=["event", "tour", "qual", "year"], columns="source", values="first_in_pct")
    print((piv * 100).round(1).to_string())

    # ---------------- 3. make-up of the disputed sides
    dd = d[d["year"].ge(2022) | d["event"].eq("OG")]
    dis = dd[dd["cls"].isin(["split", "split_other"])].copy()
    print("\n[3] disputed sides by event, class and sign")
    print(pd.crosstab([dis["event"], dis["cls"]], dis["sign"], margins=True))
    plus = dis[dis["sign"].eq("+")]
    o2 = plus["o_second_won"].sum() / (plus["o_svpt"] - plus["o_first_in"]).sum()
    o1 = plus["o_first_won"].sum() / plus["o_first_in"].sum()
    mv = plus["d_first_won"].sum() / plus["d_first_in"].sum()
    print(f"'+' sides: moved points won by the server {mv:.3f} (official 2nd-serve win rate {o2:.3f}, "
          f"1st-serve {o1:.3f}); moved points {int(plus['d_first_in'].sum())}")
    for ev in ("RG", "OG"):
        p = plus[plus["event"].eq(ev)]
        print(f"   {ev}: moved {int(p['d_first_in'].sum())}, won {int(p['d_first_won'].sum())} "
              f"({p['d_first_won'].sum() / p['d_first_in'].sum():.3f}); official 2nd-serve win rate "
              f"{p['o_second_won'].sum() / (p['o_svpt'] - p['o_first_in']).sum():.3f}")
    mi = dis[dis["sign"].eq("-")]
    print(f"'-' sides: {len(mi)}; first serves in moved {int(mi['d_first_in'].sum())}, won moved "
          f"{int(mi['d_first_won'].sum())}; sizes {mi['d_first_in'].value_counts().to_dict()}")
    ze = dis[dis["sign"].eq("0")]
    print(f"'0' sides: {len(ze)}; first-serve points won moved {ze['d_first_won'].value_counts().to_dict()}")
    print("sizes of '+':", plus["d_first_in"].value_counts().sort_index().to_dict())
    # class B: what else differs
    b = dis[dis["cls"].eq("split_other")].copy()
    for k in ("ace", "df", "bp_faced", "bp_saved"):
        b[f"x_{k}"] = b[f"s_{k}"] - b[f"o_{k}"]
    print("\nclass B sides: other counts that differ (Sackmann - official), value counts")
    for k in ("ace", "df", "bp_faced", "bp_saved"):
        print("  ", k, b[f"x_{k}"].value_counts().sort_index().to_dict())
    # corrected-side checks (official split with Sackmann's svpt, ace, df)
    c = dis.copy()
    fi, fw, sw, sv = c["o_first_in"], c["o_first_won"], c["o_second_won"], c["s_svpt"]
    c["B1"] = fi > sv
    c["B2"] = fw > fi
    c["B3"] = sw > sv - fi
    c["B6"] = c["s_df"] > sv - fi
    c["B7"] = c["s_ace"] > fw + sw
    c["strict"] = sw + c["s_df"] > sv - fi
    print("\ncorrected sides failing a check:", c[["B1", "B2", "B3", "B6", "B7", "strict"]].sum().to_dict())
    # Sackmann's own sides: the stricter check fails before correction?
    s = dis.copy()
    s["strict_before"] = s["s_second_won"] + s["s_df"] > s["s_svpt"] - s["s_first_in"]
    print("Sackmann's disputed sides failing the stricter check before correction:", int(s["strict_before"].sum()))


if __name__ == "__main__":
    main()
