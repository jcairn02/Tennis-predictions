"""The edge-anatomy report's two charts (static PNGs for the Markdown report).

    fig_parts.png    what each part of the model's disagreement with the close was worth, 2025 - 28 Jul 2026, men and
                     women: anatomy_parts.csv (the gain lost when the part is removed), with 95% intervals
    fig_seasons.png  the model's gain over its recalibrated price, season by season, men and women: edge_A.csv

Palette: the dataviz reference's categorical slots 1-2 (blue #2a78d6, orange #eb6834), validated with its
validate_palette.js (light mode, all checks pass), on its light chart surface.
Run: ./python.sh src/eda/edge_anatomy/charts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402

DOCS = ROOT / "docs" / "studies" / "edge_anatomy"
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = {"atp": ("Men", "#2a78d6"), "wta": ("Women", "#eb6834")}
PARTS = [("schedule", "Schedule and body\n(recent sets, surface rust, age)"),
         ("ios", "Serve and return profile\n(long memory, opponent-adjusted)"),
         ("form", "Two-week box-score form"),
         ("stage 2 (speed offset)", "Serve-speed change (men only)"),
         ("price shape", "Re-shaping the price curve"),
         ("ratings", "Win/loss ratings (Elo, rankings)"),
         ("context", "Context (level, surface, round)")]


def style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def parts_chart() -> Path:
    a = pd.read_csv(E.OUT / "anatomy_parts.csv")
    a = a[a["window"] == "2025-26"]
    fig, ax = plt.subplots(figsize=(8.2, 5.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    ys = np.arange(len(PARTS))[::-1]
    for (tour, (label, color)), off in zip(SERIES.items(), (0.14, -0.14)):
        for y, (part, _) in zip(ys, PARTS):
            r = a[(a["tour"] == tour) & (a["part"] == part)]
            if r.empty:
                continue
            r = r.iloc[0]
            ax.plot([r["worth_lo"], r["worth_hi"]], [y + off, y + off], color=color, lw=2, solid_capstyle="round")
            ax.scatter([r["worth_est"]], [y + off], s=60, color=color, edgecolor=SURFACE, linewidth=2, zorder=3,
                       label=label if part == "schedule" else None)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([p[1] for p in PARTS], color=INK2, fontsize=9)
    ax.set_xlabel("Accuracy this part adds over the closing price, mLL  (+ = helps; line = 95% range)", color=INK2,
                  fontsize=9)
    leg = ax.legend(loc="lower right", frameon=False, fontsize=9)
    for t in leg.get_texts():
        t.set_color(INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    fig.text(0.015, 0.97, "Where the 2025–26 edge comes from", color=INK, fontsize=11, ha="left", va="top")
    fig.text(0.015, 0.93, "Each part of the model's disagreement with the closing price, and what it was worth.\n"
             "January 2025 – 28 July 2026, main tour; men 4,394 matches, women 4,157.", color=MUTED, fontsize=8.5,
             ha="left", va="top", linespacing=1.5)
    out = DOCS / "fig_parts.png"
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out


def seasons_chart() -> Path:
    a = pd.read_csv(E.OUT / "edge_A.csv")
    a = a[a["comparison"] == "model (both stages) vs its recalibrated price"]
    seasons = [str(y) for y in range(2020, 2027)]
    fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    xs = np.arange(len(seasons))
    for (tour, (label, color)), off in zip(SERIES.items(), (-0.12, 0.12)):
        for x, s in zip(xs, seasons):
            r = a[(a["window"] == s) & (a["tour"] == tour)]
            if r.empty:
                continue
            r = r.iloc[0]
            ax.plot([x + off, x + off], [r["lo"], r["hi"]], color=color, lw=2, solid_capstyle="round")
            ax.scatter([x + off], [r["est"]], s=60, color=color, edgecolor=SURFACE, linewidth=2, zorder=3,
                       label=label if s == "2020" else None)
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_xticks(xs)
    ax.set_xticklabels([s if s != "2026" else "2026\n(to 28 Jul)" for s in seasons], color=INK2, fontsize=9)
    ax.set_ylabel("Model over the closing price, mLL\n(+ = model more accurate; line = 95% range)", color=INK2,
                  fontsize=9)
    ax.set_title("The edge over the closing price, season by season", color=INK, fontsize=10.5, loc="left", pad=22)
    ax.text(0, 1.03, "The current model, both stages, each season forecast before it was played.",
            transform=ax.transAxes, color=MUTED, fontsize=8.5)
    leg = ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=2)
    for t in leg.get_texts():
        t.set_color(INK2)
    fig.tight_layout()
    out = DOCS / "fig_seasons.png"
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out


LADDER = [("L1", "The price alone, re-drawn"), ("L2", "+ match context"), ("L3", "+ win/loss ratings"),
          ("L4", "+ schedule and body\n(recent sets, surface rust, age)"), ("L5", "+ two-week box-score form"),
          ("full", "+ long-memory serve/return profile")]
WINDOWS = {"2025-26": ("Jan 2025 – Jul 2026", "#2a78d6"), "2020-24": ("2020–2024", "#eb6834")}


def ladder_chart() -> Path:
    """fig_ladder.png: each ladder step's gain (stage 1, both tours), 2025-26 against 2020-24 (ladder_scores.csv)."""
    a = pd.read_csv(E.OUT / "ladder_scores.csv")
    a = a[(a["reading"] == "ladder step") & (a["stage"] == "s1") & (a["tour"] == "both")]
    fig, ax = plt.subplots(figsize=(8.2, 5.0), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    ys = np.arange(len(LADDER))[::-1]
    for (win, (label, color)), off in zip(WINDOWS.items(), (0.14, -0.14)):
        for y, (arm, _) in zip(ys, LADDER):
            r = a[(a["window"] == win) & (a["arm"] == arm)]
            if r.empty:
                continue
            r = r.iloc[0]
            ax.plot([r["lo"], r["hi"]], [y + off, y + off], color=color, lw=2, solid_capstyle="round")
            ax.scatter([r["est"]], [y + off], s=60, color=color, edgecolor=SURFACE, linewidth=2, zorder=3,
                       label=label if arm == "L1" else None)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([s[1] for s in LADDER], color=INK2, fontsize=9)
    ax.set_xlabel("Accuracy the step adds over the closing price, mLL  (+ = helps; line = 95% range)", color=INK2,
                  fontsize=9)
    leg = ax.legend(loc="lower right", frameon=False, fontsize=9)
    for t in leg.get_texts():
        t.set_color(INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.text(0.015, 0.97, "The model rebuilt one family at a time", color=INK, fontsize=11, ha="left", va="top")
    fig.text(0.015, 0.93, "Each row: what adding that family of statistics gains, the model refitted each time.\n"
             "Both tours, the model without its serve-speed stage. The steps add up to the model's whole edge.",
             color=MUTED, fontsize=8.5, ha="left", va="top", linespacing=1.5)
    out = DOCS / "fig_ladder.png"
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out


def main() -> int:
    for p in (parts_chart(), seasons_chart(), ladder_chart()):
        E.log(f"written {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
