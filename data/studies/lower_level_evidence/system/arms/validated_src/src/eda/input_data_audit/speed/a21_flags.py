"""Audit step 21: the edition-level flag table. Spikes are recomputed within one reference regime (men: 2021-2026, when the
tour's key-statistic main draws are the reference; men 2011-2020 and women: Slam main draws). Writes
scratch/t_flags_editions.csv. Read-only on the repo."""
from pathlib import Path
import numpy as np
import pandas as pd

SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)
E = pd.read_csv(SCR / "t_edition_effects.csv")
E["regime"] = np.where((E["tour"] == "atp") & (E["year"] >= 2021), "men_tour_ref",
                       np.where(E["tour"] == "atp", "men_slam_ref", "women_slam_ref"))
E["ev"] = E["event"].astype(str) + "|" + E["mq"] + "|" + E["basis"]
out = []
for (tour, regime, ev), g in E.groupby(["tour", "regime", "ev"]):
    for i, r in g.iterrows():
        oth = g[(g["year"] != r["year"]) & (g["rows_ident"] >= 10)]
        out.append({"i": i, "spike_r": r["gamma_c"] - oth["gamma_c"].median() if len(oth) >= 2 else np.nan,
                    "n_other_r": len(oth)})
E = E.join(pd.DataFrame(out).set_index("i"))
E["group"] = np.where(E["level"].eq("GS"), "slam", E["family"])
sd = E[(E["rows_ident"] >= 20) & E["spike_r"].notna()].groupby(["tour", "group"])["spike_r"].std()
print("SD of one-year spikes by group (normal edition-to-edition variation):")
print(sd.round(2).to_string())
E["sd_group"] = [sd.get((t, g), np.nan) for t, g in zip(E["tour"], E["group"])]
E["flag_spike"] = (E["rows_ident"] >= 20) & (E["spike_r"].abs() >= 2 + E["sd_group"]) & (E["spike_r"].abs() >= 3 * E["se"])
E["flag_step"] = E["level"].eq("GS") & (E["rows_ident"] >= 20) & ((E["step_from_prev"].abs() >= 3)
                                                                 | (E["step_to_next"].abs() >= 3))
cols = ["tour", "tournament_name", "year", "mq", "basis", "sources", "rows", "rows_ident", "gamma_c", "se", "spike_r",
        "sd_group", "step_from_prev", "step_to_next", "flag_spike", "flag_step"]
F = E[E["flag_spike"] | E["flag_step"]].sort_values(["tour", "group", "tournament_name", "year"])
print(f"\nflagged editions: {len(F)} (spike beyond 2 km/h + normal SD: {int(F['flag_spike'].sum())}; Slam steps >= 3: "
      f"{int(F['flag_step'].sum())})")
print(F[cols].round(2).to_string(index=False))
F[cols].to_csv(SCR / "t_flags_editions.csv", index=False)
print("\nSlam main draws 2021-2026, edition effect (km/h; men vs the tour's key statistics, women vs the Slam mean):")
s = E[E["level"].eq("GS") & E["mq"].eq("M") & (E["year"] >= 2021)]
print(s.pivot_table(index=["tour", "tournament_name"], columns="year", values="gamma_c").round(1).to_string())
