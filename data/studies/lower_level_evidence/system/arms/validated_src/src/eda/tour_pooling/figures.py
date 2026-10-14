"""Figures of the tour-pooling study's report (docs/studies/tour_pooling/README.md), from the scorer's scores.csv.

    designs.png   each design against the current model, 2022 to 28 Jul 2026, both stages, both tours / men / women:
                  the estimate and its 95% interval (mLL per match; right of 0 = the design better)
    seasons.png   one model per tour against the current model, season by season, both tours / men / women

Static images for a markdown report: the reference palette's light surface, slot-1 blue for the estimates, muted ink
for intervals and text. Run: ./python.sh src/eda/tour_pooling/figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
SCORES = ROOT / "data" / "studies" / "tour_pooling" / "scores" / "scores.csv"
SEGMENTS = ROOT / "data" / "studies" / "tour_pooling" / "segments" / "segments.csv"
OUT = ROOT / "docs" / "studies" / "tour_pooling" / "figures"

SURFACE, INK, INK2, MUTED, GRID, BLUE = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#2a78d6"
DESIGNS = [("split", "One model per tour (split)"), ("notour", "One model, no men/women flag"),
           ("borrow25", "Own tour + 25% of the other"), ("borrow50", "Own tour + 50% of the other"),
           ("borrowsim", "Own tour + similar half of the other"), ("aligned", "One model, statistics per-tour scaled"),
           ("blend", "Composite: learned blend"), ("select", "Composite: past-seasons pick")]
POPS = [("both tours", "Both tours"), ("men", "Men"), ("women", "Women")]
POST_HOC = "post-hoc control, both stages: avg_split_pooled vs pooled"


def style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5))
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.axvline(0, color=INK2, linewidth=1.2, zorder=1)


def intervals(ax, rows: pd.DataFrame, labels: list[str]) -> None:
    y = list(range(len(rows)))[::-1]
    for yi, (_, r) in zip(y, rows.iterrows()):
        ax.plot([r["lo"], r["hi"]], [yi, yi], color=MUTED, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter([r["estimate"]], [yi], s=46, color=BLUE, edgecolors=SURFACE, linewidths=1.5, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, color=INK, fontsize=9)


def designs(s: pd.DataFrame) -> Path:
    w = s[(s["window"] == "W1") & (s["group"] == "primary")]
    t = w[w["comparison"] == "both stages: arm vs pooled"]
    present = [(a, lab) for a, lab in DESIGNS if a in set(t["arm"])]
    post = w[(w["comparison"] == POST_HOC) & (w["arm"] == "avg_split_pooled")]
    if len(post):
        t = pd.concat([t, post])
        present.append(("avg_split_pooled", "Post hoc: 50/50 average, own-tour + single"))
    fig, axes = plt.subplots(1, 3, figsize=(12, 0.42 * len(present) + 1.6), sharex=True, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    for ax, (pop, title) in zip(axes, POPS):
        style(ax)
        rows = pd.concat([t[(t["arm"] == a) & (t["population"] == pop)].head(1) for a, _ in present])
        intervals(ax, rows, [lab for _, lab in present])
        ax.set_title(title, color=INK, fontsize=10, loc="left")
    axes[1].set_xlabel("Log loss against the current model, thousandths per match (right of 0 = the design is better)",
                       color=INK2, fontsize=9)
    fig.suptitle("Every design against the current single model, 2022 to 28 Jul 2026 (dots: estimate; lines: 95% "
                 "range)", color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    path = OUT / "designs.png"
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def season_rows(s: pd.DataFrame, seg: pd.DataFrame, pop: str, years: list[str]) -> pd.DataFrame:
    """split against pooled per season, + = split better: both tours from scores.csv; each tour from the segment
    table's "pooled vs split" cells (+ = pooled better there, so negated, the interval mirrored)."""
    if pop == "both tours":
        t = s[(s["window"] == "W1") & (s["group"] == "season") & (s["arm"] == "split")
              & (s["comparison"] == "both stages: arm vs pooled")]
        return pd.concat([t[t["population"].astype(str) == Y].head(1) for Y in years])[["estimate", "lo", "hi"]]
    t = seg[(seg["window"] == "W1") & (seg["comparison"] == "pooled vs split") & (seg["dimension"] == "season")
            & (seg["tour"] == pop)]
    t = pd.concat([t[t["cell"].astype(str) == Y].head(1) for Y in years])
    return pd.DataFrame({"estimate": -t["estimate"].to_numpy(), "lo": -t["hi"].to_numpy(), "hi": -t["lo"].to_numpy()})


def seasons(s: pd.DataFrame) -> Path:
    seg = pd.read_csv(SEGMENTS)
    years = [str(Y) for Y in range(2022, 2027)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.2), sharex=True, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    for ax, (pop, title) in zip(axes, POPS):
        style(ax)
        rows = season_rows(s, seg, pop, years)
        labels = ["2026 (to 28 Jul)" if Y == "2026" else Y for Y in years][: len(rows)]
        intervals(ax, rows, labels)
        ax.set_title(title, color=INK, fontsize=10, loc="left")
    axes[1].set_xlabel("One model per tour against the current model, thousandths per match (right of 0 = split better)",
                       color=INK2, fontsize=9)
    fig.suptitle("Season by season: one model per tour against the single model (dots: estimate; lines: 95% range)",
                 color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout(w_pad=2.5)
    path = OUT / "seasons.png"
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def main() -> int:
    s = pd.read_csv(SCORES)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (designs(s), seasons(s)):
        print(f"written: {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
