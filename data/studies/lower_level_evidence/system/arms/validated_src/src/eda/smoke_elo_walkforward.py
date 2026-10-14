"""End-to-end scaffolding smoke test: Sackmann ATP 2023-2025 -> Elo walk-forward.

Not a study — just proof the ingest -> ratings spine works on real data and
produces a sane log loss (single-K Elo on ATP typically lands ~0.59-0.63 once
ratings warm up; the first season here is cold-start so its loss runs higher).

Run:  ./python.sh src/eda/smoke_elo_walkforward.py
"""

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.load_matches import load_sackmann_matches
from src.ratings.elo import SurfaceBlendElo


def main() -> None:
    df = load_sackmann_matches("atp", 2023, 2025)
    n_missing_surface = int((~df["surface"].isin(["Hard", "Clay", "Grass", "Carpet"])).sum())
    print(f"Loaded {len(df):,} ATP matches 2023-2025 "
          f"({n_missing_surface} rows lack a standard surface -> overall-only policy)")

    elo = SurfaceBlendElo(surface_weight=0.5, missing_surface="overall")
    preds = elo.fit(df)

    p = preds["p_winner"].to_numpy()
    years = (df["tourney_date"] // 10000).to_numpy()
    for label, mask in [("all 2023-2025", np.ones(len(df), bool)),
                        ("2024-2025 (post burn-in)", years >= 2024)]:
        log_loss = -np.log(p[mask]).mean()
        acc = (p[mask] > 0.5).mean()
        print(f"{label:>26}: n={mask.sum():5d}  log_loss={log_loss:.4f}  acc={acc:.3f}")

    top = sorted(elo.overall.items(), key=lambda kv: kv[1], reverse=True)[:5]
    print("Top 5 overall Elo:", ", ".join(f"{name} {r:.0f}" for name, r in top))


if __name__ == "__main__":
    main()
