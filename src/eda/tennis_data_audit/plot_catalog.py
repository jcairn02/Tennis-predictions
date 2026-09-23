"""Static research figure from audited metrics; no network or model fitting."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

ROOT = Path(__file__).resolve().parents[3]
rows = json.loads((ROOT / "data/studies/tennis_data_audit/polymarket/audited-summary.json").read_text(encoding="utf-8"))["monthly"]
out = ROOT / "docs/research/tennis-data-audit/figures"
out.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(11.5, 5.2))
x = list(range(len(rows)))
other = [r["events"] - r["itf_series_events"] for r in rows]
itf = [r["itf_series_events"] for r in rows]
ax.bar(x, other, color="#767d85", label="Other tennis catalog groups", width=.7)
ax.bar(x, itf, bottom=other, color="#244d66", label="ITF series", width=.7)
ax.set_xticks(x, [r["month"][5:] + "/" + r["month"][2:4] + ("*" if i in (0,len(rows)-1) else "") for i,r in enumerate(rows)])
ax.set_ylabel("Event records (not deduplicated matches)")
ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
ax.set_title("Polymarket tennis catalog by sporting month", loc="left", fontweight="bold", pad=20)
ax.set_ylim(0, 7600)
ax.set_axisbelow(True)
ax.grid(axis="y", color="#e6e6e6")
ax.legend(frameon=False, loc="upper left")
fig.text(.07,.025,"Source: saved Gamma catalog, 10 Sep 2026. *Partial month. Accessible tagged records; nine football records excluded.", fontsize=9, color="#444444")
fig.subplots_adjust(left=.08, right=.985, bottom=.16, top=.86)
fig.savefig(out / "polymarket-catalog-by-month.png", dpi=160)
fig.savefig(out / "polymarket-catalog-by-month.svg")
print("Wrote PNG and SVG catalog figure")
