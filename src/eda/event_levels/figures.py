"""Figures for the event-levels report (docs/studies/event_levels/), from the study's CSV outputs.

    ladder.png/.svg      each level's players by ranking at the match (P10-P90 line, P25-P75 bar, median dot), the
                         model's training levels in the accent hue, the others in gray (emphasis form)
    band_mix.png/.svg    for each rank band, the share of its matches at each tier (stacked; an ordinal one-hue ramp
                         for the ordered tiers, gray for team events)
    experiment_a.png/.svg  experiment A's arms against the current model on each target level (estimate and 95% interval)

Palette: the dataviz skill's reference palette (light surface), ordinal ramp validated with validate_palette.js
--ordinal. Every value plotted is in the report's tables.
Run: ./python.sh src/eda/event_levels/figures.py [--only ladder,band_mix,experiment_a]
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

from src.eda.event_levels import common as C  # noqa: E402

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
ACCENT, DEEMPH = "#2a78d6", "#898781"
GOOD, CRITICAL = "#0ca30c", "#d03b3b"                         # the reference palette's status pair
RAMP = ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef"]          # main tour -> ITF (ordinal, validated)
TEAM_GRAY = "#c3c2b7"
NAMES = {"GS": "Grand Slams", "FIN": "Tour Finals", "T1000": "1000s", "T500": "500s", "T250": "250s",
         "TEAM": "Team events", "TQ": "Tour qualifying", "GSQ": "Slam qualifying", "CH": "Challenger / WTA 125",
         "CHQ": "Challenger qualifying", "ITF": "ITF", "ITFQ": "ITF qualifying"}
TOUR = {"atp": "Men (ATP)", "wta": "Women (WTA)"}

plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9.5, "axes.edgecolor": AXIS,
                     "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2, "axes.linewidth": 0.8,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "svg.fonttype": "none"})


def save(fig, name: str) -> None:
    C.DOCS.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(C.DOCS / f"{name}.{ext}", dpi=170 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def recessive(ax, axis: str = "x") -> None:
    ax.grid(axis=axis, color=GRID, linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)


def ladder() -> None:
    t = pd.read_csv(C.OUT / "blend" / "ladder.csv")
    levels = [lv for lv in C.LEVELS if lv != "ITFQ"]           # men's ITF qualifying: 206 matches, no source lists it
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), sharey=True)
    for ax, tour in zip(axes, C.TOURS):
        g = t[t["tour"] == tour].set_index("level")
        for i, lv in enumerate(levels):
            if lv not in g.index:
                continue
            r = g.loc[lv]
            col = ACCENT if lv in C.MAIN else DEEMPH
            y = len(levels) - 1 - i
            ax.plot([r["p10"], r["p90"]], [y, y], color=col, linewidth=2, solid_capstyle="round", zorder=2)
            ax.plot([r["p25"], r["p75"]], [y, y], color=col, linewidth=9, solid_capstyle="butt", zorder=3)
            ax.scatter([r["median"]], [y], s=46, color=col, edgecolor=SURFACE, linewidth=2, zorder=4)
        ax.set_xscale("log")
        ax.set_xlim(1.5, 2000)
        ax.set_xticks([2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000])
        ax.set_xticklabels(["2", "5", "10", "20", "50", "100", "200", "500", "1,000", "2,000"])
        ax.set_yticks(range(len(levels)))
        ax.set_yticklabels([NAMES[lv] for lv in reversed(levels)])
        ax.set_title(TOUR[tour], loc="left", color=INK, fontsize=10.5, fontweight="semibold")
        ax.set_xlabel("Player's ranking at the match (log scale; better to the left)")
        recessive(ax)
        ax.axhspan(len(levels) - 5.5, len(levels) - 0.5, color="#f0efec", zorder=0)
    axes[0].text(1.6, len(levels) - 0.5 + 0.05, "the model's training levels", color=INK2, fontsize=8.5,
                 va="bottom")
    fig.suptitle("How the levels overlap by ranking, 2013-2024", x=0.01, ha="left", color=INK, fontsize=12,
                 fontweight="semibold")
    fig.text(0.01, 0.905, "Line: 10th-90th percentile of the players' rankings; bar: 25th-75th; dot: median. "
                          "Blue: levels the current model trains on; gray: levels it never sees as rows.",
             color=INK2, fontsize=8.8)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    save(fig, "ladder")


def band_mix() -> None:
    t = pd.read_csv(C.OUT / "blend" / "band_mix.csv")
    tiers = [("Main tour", C.MAIN), ("Tour & Slam qualifying", ("TQ", "GSQ")),
             ("Challenger / WTA 125 (incl. qualifying)", ("CH", "CHQ")), ("ITF (incl. qualifying)", ("ITF", "ITFQ")),
             ("Team events", ("TEAM",))]
    colors = RAMP + [TEAM_GRAY]
    bands = [b for b in C.BAND_ORDER if b != "unranked"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.9), sharey=True)
    for ax, tour in zip(axes, C.TOURS):
        g = t[t["tour"] == tour].set_index("band")
        left = np.zeros(len(bands))
        for (name, lvls), col in zip(tiers, colors):
            share = np.array([sum(g.loc[b, lv] for lv in lvls if lv in g.columns) for b in bands])
            y = np.arange(len(bands))[::-1]
            ax.barh(y, share * 100, left=left * 100, height=0.62, color=col, edgecolor=SURFACE, linewidth=1.5,
                    label=name)
            for yi, s, l0 in zip(y, share, left):
                if s >= 0.14:
                    lum = 0 if col in RAMP[:3] else 1
                    ax.text((l0 + s / 2) * 100, yi, f"{s:.0%}", ha="center", va="center", fontsize=8,
                            color="#ffffff" if lum == 0 else INK)
            left += share
        ax.set_yticks(range(len(bands)))
        ax.set_yticklabels([b.replace("-", "–") for b in reversed(bands)])
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
        ax.set_xlabel("Share of the band's matches")
        ax.set_title(TOUR[tour], loc="left", color=INK, fontsize=10.5, fontweight="semibold")
        recessive(ax)
    axes[0].set_ylabel("Player's ranking at the match")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper left", bbox_to_anchor=(0.01, 0.915), ncol=5, frameon=False, fontsize=8.6,
               handlelength=1.2, columnspacing=1.2, labelcolor=INK2)
    fig.suptitle("Where each rank band plays, 2013-2024", x=0.01, ha="left", color=INK, fontsize=12,
                 fontweight="semibold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    save(fig, "band_mix")


def experiment_a() -> None:
    full = C.OUT / "results.csv"
    r = pd.read_csv(full if full.exists() else C.OUT / "results_A.csv")
    r = r[(r["part"].astype(str) == "2") & (r["window"] == "2020-2024") & (r["population"] == "both")]
    rows = []
    for L in C.TARGETS:
        g = r[r["level"] == L]
        for comp, arm, label in (("expL_vs_exp", "exp_L", "Recalibrate per level"),
                                 ("exp2pL_vs_exp", "exp_2pL", "Re-size moves per level"),
                                 ("vs_exp", f"own_{L}", "Own level only"),
                                 ("vs_exp", f"w25_{L}", "Own + others at 25%"),
                                 ("vs_exp", f"w50_{L}", "Own + others at 50%"),
                                 ("drop_on_own_level", f"drop_{L}", "Without this level (on it)")):
            x = g[(g["comparison"] == comp) & (g["arm"] == arm)]
            if len(x):
                rows.append({"level": L, "label": label, **x.iloc[0][["estimate", "lo", "hi"]].to_dict()})
    d = pd.DataFrame(rows)
    labels = list(dict.fromkeys(d["label"]))
    fig, axes = plt.subplots(1, len(C.TARGETS), figsize=(11, 3.6), sharey=True, sharex=True)
    for ax, L in zip(axes, C.TARGETS):
        g = d[d["level"] == L].set_index("label").reindex(labels)
        y = np.arange(len(labels))[::-1]
        ax.axvline(0, color=AXIS, linewidth=1)
        for yi, (_, row) in zip(y, g.iterrows()):
            if not np.isfinite(row["estimate"]):
                continue
            col = GOOD if row["lo"] > 0 else (DEEMPH if row["hi"] >= 0 else CRITICAL)      # status colours
            ax.plot([row["lo"], row["hi"]], [yi, yi], color=col, linewidth=2, solid_capstyle="round")
            ax.scatter([row["estimate"]], [yi], s=40, color=col, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.set_title(NAMES[L], loc="left", color=INK, fontsize=10.5, fontweight="semibold")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(list(reversed(labels)))
        ax.set_xlabel("mLL vs current model\n(+ = better)")
        recessive(ax)
    fig.suptitle("Segmenting the current model by level, 2020-2024 (both tours, both stages)", x=0.01, ha="left",
                 color=INK, fontsize=12, fontweight="semibold")
    fig.text(0.01, 0.885, "Dot: estimate; line: 95% interval (four-week blocks + seeds). Gray: tie (interval spans 0); "
                          "red: worse than the current model; green: better.", color=INK2, fontsize=8.8)
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    save(fig, "experiment_a")


def main() -> int:
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else ["ladder", "band_mix",
                                                                                            "experiment_a"]
    for name in only:
        globals()[name]()
        C.log(f"{name} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
