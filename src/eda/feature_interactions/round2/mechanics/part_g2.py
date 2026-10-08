"""Part G2: the joint fit r ~ 1 + O + D + Oace + O*D + Oace*D (both structures at once), same rows and SEs as part_g.
Run: ./python.sh src/eda/feature_interactions/round2/mechanics/part_g2.py"""
import json
import numpy as np
import pandas as pd
import part_g as G
from common import OUT, load, logit


def main():
    f, _ = load()
    p = pd.read_parquet(G.OLD / "stage0_match_players.parquet", columns=["match_id", "side", "svpt", "first_won", "second_won"])
    p = p[p["match_id"].isin(f["match_id"])].copy()
    p["spw"] = p["first_won"] + p["second_won"]
    rows = []
    for srv, ret, side in (("a", "b", "A"), ("b", "a", "B")):
        d = f.join(p[p["side"].eq(side)].set_index("match_id")[["spw", "svpt"]], on="match_id").dropna(subset=["spw"])
        d = d[d["svpt"] >= 20]
        rows.append(pd.DataFrame({"tour": d["tour"].to_numpy(), "n": d["svpt"].to_numpy(), "mu": d["mu_spw"].to_numpy(),
            "r": logit((d["spw"] + 0.5) / (d["svpt"] + 1)) - (logit(d["mu_spw"]) + d[f"srf_O_eff_spw_{srv}"] - d[f"srf_D_eff_spw_{ret}"]),
            "O": d[f"srf_O_eff_spw_{srv}"].to_numpy(), "D": d[f"srf_D_eff_spw_{ret}"].to_numpy(), "Oa": d[f"srf_O_eff_ace_{srv}"].to_numpy()}))
    r = pd.concat(rows, ignore_index=True).dropna()
    out = {}
    for t, g in r.groupby("tour"):
        O, D, Oa = (g[c] - g[c].mean() for c in ("O", "D", "Oa"))
        X = np.column_stack([np.ones(len(g)), O, D, Oa, O * D, Oa * D])
        b, s = G.wls(g["r"].to_numpy(), X, (g["n"] * g["mu"] * (1 - g["mu"])).to_numpy())
        out[t] = {"O*D": [round(float(b[4]), 4), round(float(s[4]), 4)], "Oace*D": [round(float(b[5]), 4), round(float(s[5]), 4)],
                  "corr(O*D, Oace*D)": round(float(np.corrcoef(O * D, Oa * D)[0, 1]), 3)}
    (OUT / "part_g2.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
