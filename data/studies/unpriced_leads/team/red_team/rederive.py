"""R2 re-derivation of the registered discovery readings (seasons <= 2024 only), independent code (rt_common).

1. projections and scales refitted here vs the registry's frozen ones;
2. member, group and omnibus scores: refitted vs frozen;
3. the registered fit (per-tour slope + curvature, score at unit RMS, CR1 over 4-week blocks) by sklearn + my sandwich,
   both tours, each tour, each era: compared with registration/discovery_registered.csv.
Writes rederive.csv and rederive_checks.json beside this file.
Run: ./python.sh data/studies/unpriced_leads/team/red_team/rederive.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rt_common as R  # noqa: E402


def main() -> int:
    reg = R.registry()
    d = R.disc_frame()
    chk = {"disc_rows": int(len(d)), "disc_by_tour": d["tour"].value_counts().to_dict(),
           "season_range": [int(d["season"].min()), int(d["season"].max())], "members": {}}
    # 1. projections and scales
    for g in reg["groups"]:
        for m in g["members"]:
            x = R.values(d, m["values"], m["column"])
            xo, b = R.project(d, x)
            e = {}
            for t in ("atp", "wta"):
                breg = np.asarray(m["orth_coef"][t]["b"], float)
                tm = (d["tour"] == t).to_numpy()
                X = np.nan_to_num(d.loc[tm, [f"in_{n}" for n in R.diff_inputs()]].to_numpy(float))
                fit_diff = np.nanmax(np.abs(X @ b[t] - X @ breg))
                e[t] = {"inputs_match": m["orth_coef"][t]["inputs"] == R.diff_inputs(),
                        "max_abs_coef_diff": float(np.max(np.abs(b[t] - breg))),
                        "max_abs_fitted_diff": float(fit_diff),
                        "scale_here": float(np.sqrt(np.nanmean(xo[tm] ** 2))), "scale_reg": m["scale_orth"][t],
                        "present_share": float(np.mean(np.isfinite(x[tm])))}
            chk["members"][m["name"]] = e
    # 2. scores
    mem_o, grp_o, omni_o, gs_o = R.scores(d, reg, own_projection=True)
    mem_f, grp_f, omni_f, gs_f = R.scores(d, reg, own_projection=False)
    chk["score_max_abs_diff"] = {"omnibus": float(np.max(np.abs(omni_o - omni_f))),
                                 **{k: float(np.max(np.abs(grp_o[k] - grp_f[k]))) for k in grp_o}}
    chk["group_scale_here_vs_reg"] = {k: [gs_o[k], gs_f[k]] for k in gs_o}
    # 3. fits
    rows = []

    def add(level, name, s):
        for tour in ("both", "atp", "wta"):
            m = np.ones(len(d), bool) if tour == "both" else (d["tour"] == tour).to_numpy()
            fr = d[m].reset_index(drop=True)
            r = R.beta_z(fr, s[m])
            r0 = R.beta_z(fr, s[m], curv=False)
            eras = {}
            for era, (a, b) in R.ERAS.items():
                em = fr["season"].between(a, b).to_numpy()
                eras[f"z_{era}"] = R.beta_z(fr[em].reset_index(drop=True), s[m][em])["z"]
                eras[f"b_{era}"] = R.beta_z(fr[em].reset_index(drop=True), s[m][em])["beta"]
            rows.append({"level": level, "name": name, "tour": tour, "beta": r["beta"], "se": r["se"], "z": r["z"],
                         "se_model": r["se_model"], "deff": r["se"] / r["se_model"], "z_no_curv": r0["z"],
                         "n": r["n"], "G": r["G"], "grad_max": r["grad_max"], **eras})

    add("omnibus", "omnibus", omni_o)
    for g in reg["groups"]:
        add("group", g["id"], grp_o[g["id"]])
        for m in g["members"]:
            add("member", f"{g['id']}:{m['name']}", mem_o[f"{g['id']}:{m['name']}"])
    out = pd.DataFrame(rows)
    # compare with the registered readings
    regd = pd.read_csv(R.ROOT / "data" / "studies" / "unpriced_leads" / "registration" / "discovery_registered.csv")
    lab = {}
    for g in reg["groups"]:
        lab[g["name"]] = g["id"]
        for m in g["members"]:
            lab[m["label"]] = f"{g['id']}:{m['name']}"
    lab["omnibus"] = "omnibus"
    regd["key"] = [("omnibus" if lv == "omnibus" else (lab[n] if lv == "group" else lab[n])) for lv, n in
                   zip(regd["level"], regd["name"])]
    mg = out.merge(regd[["key", "tour", "beta", "se", "z", "z_no_curv", "z_2013-16", "z_2017-19", "z_2020-22",
                         "z_2023-24"]].rename(columns=lambda c: c if c in ("key", "tour") else f"reg_{c}"),
                   left_on=["name", "tour"], right_on=["key", "tour"], how="left")
    for c in ("beta", "se", "z", "z_no_curv", "z_2013-16", "z_2017-19", "z_2020-22", "z_2023-24"):
        mg[f"d_{c}"] = mg[c] - mg[f"reg_{c}"]
    chk["max_abs_diff_vs_registered"] = {c: float(np.nanmax(np.abs(mg[f"d_{c}"]))) for c in
                                         ("beta", "se", "z", "z_no_curv", "z_2013-16", "z_2017-19", "z_2020-22",
                                          "z_2023-24")}
    mg.to_csv(R.OUT / "rederive.csv", index=False)
    (R.OUT / "rederive_checks.json").write_text(json.dumps(chk, indent=1, default=float), encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    show = mg[mg["tour"] == "both"][["name", "beta", "reg_beta", "se", "reg_se", "z", "reg_z", "deff", "z_2013-16",
                                     "z_2017-19", "z_2020-22", "z_2023-24", "b_2013-16", "b_2017-19", "b_2020-22",
                                     "b_2023-24"]]
    print(show.round(4).to_string(index=False))
    print(json.dumps({k: v for k, v in chk.items() if k != "members"}, indent=1, default=float))
    worst = {k: max(v[t]["max_abs_fitted_diff"] for t in v) for k, v in chk["members"].items()}
    print("max |fitted projection diff| by member:", {k: f"{v:.2e}" for k, v in worst.items()})
    print("scales here vs registry:", {k: [round(v[t]["scale_here"] / v[t]["scale_reg"], 8) for t in v]
                                       for k, v in chk["members"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
