"""Bet timing: the report's figure, docs/studies/bet_timing/edge_by_horizon.png, drawn from results.json.

Two panels in one unit (milli-log-loss per match), one per venue; x is hours before the listed start (log scale, the
close to the right):
    S(t)          how much softer the line at t is than the close (what the line gives away)
    A(t)          how much accuracy the model loses when fed the line at t instead of the close (what it inherits)
    S(t) - A(t)   the change in the model's edge from betting at t instead of the close (higher = betting early gains),
                  with its 95% interval
S and A are drawn without intervals: they move together match by match, so only their difference is measured precisely
(the tables in the report give each interval). Polymarket: the same matches at every horizon (priced from 24 hours,
every input known at 24 hours), against the price 30 minutes before the listed start. BetOnline: the opening line,
matches binned by how long before the listed start it was quoted, against the last line; each bin is its own matches.
Run: ./python.sh src/eda/bet_timing/figure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.bet_timing import common as C  # noqa: E402

INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


def panel(ax, rows: list[dict], title: str, subtitle: str, label_right: bool) -> None:
    rows = sorted(rows, key=lambda r: -r["early_hours_median"])
    xs = [r["early_hours_median"] for r in rows]
    s = [r["S_softness"]["est"] for r in rows]
    a = [r["A_model_loss"]["est"] for r in rows]
    net = [r["net_E_early_minus_E_close"] for r in rows]
    ax.axhline(0, color=AXIS, lw=1.0, zorder=1)
    ax.plot(xs, s, color=ORANGE, lw=1.8, marker="o", ms=5.5, mec=SURFACE, mew=1.2, zorder=3,
            label="Line softer than the close, S(t)")
    ax.plot(xs, a, color=AQUA, lw=1.8, marker="o", ms=5.5, mec=SURFACE, mew=1.2, zorder=3,
            label="Model's own loss when fed it, A(t)")
    ax.errorbar(xs, [n["est"] for n in net], yerr=[[n["est"] - n["lo"] for n in net], [n["hi"] - n["est"] for n in net]],
                color=BLUE, lw=2.0, marker="o", ms=6, mec=SURFACE, mew=1.2, elinewidth=1.2, capsize=3, zorder=4,
                label="Change in edge from betting early, S(t) - A(t)")
    if label_right:                                          # direct labels at the earliest point of each series
        close = abs(s[0] - a[0]) < 0.3                       # S and A on top of each other: one label
        labels = [(s[0], "S = A" if close else "S")] + ([] if close else [(a[0], "A")]) + [(net[0]["est"], "S - A")]
        for y, text in labels:
            ax.annotate(text, (xs[0], y), xytext=(-8, 0), textcoords="offset points", ha="right", va="center",
                        color=INK2, fontsize=8.5)
    ax.set_xscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{x:.0f}" for x in xs])
    ax.minorticks_off()
    ax.set_xlim(max(xs) * 1.45, min(xs) / 1.3)               # earlier bets to the left, the close to the right
    ax.set_xlabel("Hours before the listed start (log scale)", color=INK2, fontsize=9)
    ax.set_title(title, loc="left", color=INK, fontsize=11, fontweight="bold", pad=20)
    ax.text(0, 1.025, subtitle, transform=ax.transAxes, color=INK2, fontsize=8.5, va="bottom")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=8.5, length=0)


def main() -> int:
    res = C.read_json(C.OUT / "results.json")
    pm = res["polymarket_panel"]
    bol = [r for r in res["decomposition"] if r["label"].startswith("betonline|known|open_")]
    bol_all = next(r for r in res["decomposition"] if r["label"] == "betonline|known|all")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True, facecolor=SURFACE)
    for ax in axes:
        ax.set_facecolor(SURFACE)
    panel(axes[0], pm, "Polymarket, 2025-2026",
          f"The same {pm[0]['matches']:,} matches at every horizon; close = 30 minutes before the listed start", True)
    panel(axes[1], bol, "BetOnline's opening line, 2020-2026",
          f"{bol_all['matches']:,} matches, binned by when the line opened; close = BetOnline's last line", True)
    axes[0].set_ylabel("Milli-log-loss per match", color=INK2, fontsize=9)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, fontsize=9, labelcolor=INK,
               bbox_to_anchor=(0.5, 1.0))
    fig.text(0.01, 0.012, "Above 0, betting at that hour gains edge over betting at the close. Bars: 95% intervals of "
             "S - A over four-week blocks.\nS and A are drawn without intervals: they move together match by match, so "
             "only their difference is measured precisely.", color=MUTED, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.07, 1, 0.92))
    out = C.DOCS / "edge_by_horizon.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170, facecolor=SURFACE)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
