"""Part H: novelty of the serve-point link term. x = O_A*D_B - O_B*D_A on spw (= -prod_spw; the model's seven prods
exclude spw). R^2 on the 58 inputs (OLS fitted 2013-2018 per tour), remainder SD 2019-2021, and the implied match
log-odds RMS 0.27 * 4.8 * remainder (part G2's men's O*D, the iid leverage at 62%). No result read.
Run: ./python.sh src/eda/feature_interactions/round2/mechanics/part_h.py"""
import json
import numpy as np
from checks import design, remainder
from common import OUT, load


def main():
    f, names = load()
    x = (f["srf_O_eff_spw_a"] * f["srf_D_eff_spw_b"] - f["srf_O_eff_spw_b"] * f["srf_D_eff_spw_a"]).to_numpy()
    out = {}
    for t in ("atp", "wta"):
        m = f["tour"].eq(t).to_numpy()
        g = f[m]
        fit = g["season"].le(2018).to_numpy()
        r, ok = remainder(x[m], design(g, names), fit)
        sd_r = float(np.std(r[ok & ~fit]))
        out[t] = {"sd_x": round(float(np.std(x[m])), 4),
                  "r2_on_58_fit": round(float(1 - np.var(r[ok & fit]) / np.var(x[m][ok & fit])), 4),
                  "remainder_sd_2019_2021": round(sd_r, 4),
                  "implied_match_logodds_rms": round(0.27 * 4.8 * sd_r, 4)}
    (OUT / "part_h.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
