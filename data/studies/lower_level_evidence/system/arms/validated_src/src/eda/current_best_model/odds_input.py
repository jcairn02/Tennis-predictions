"""The current best model's odds input, "Pinnacle first" (the owner's decision of 9 Oct 2026:
docs/decisions/2026-10-09-pinnacle-first-odds-input.md).

The chain (model_rebuild/run_chain.py) builds the frame with the books' average close as the odds input. This step
replaces it, match by match, with the margin-free (proportional) chance of A from:
    1. Pinnacle's close: tennis-data's PSW/PSL (Stage 1) for matches up to 31 Jul 2025, cross-checked against
       OddsTrader's timed recording of Pinnacle (book 20). Where the two differ by more than 0.1 in log-odds and at
       least 3 other books price the match, the one nearer the other books' median; OddsTrader's where tennis-data has
       none (it runs to 7 Sep 2025)
    2. BetOnline's closing line (OddsTrader's last line, book 8) where Pinnacle has none
    3. the books' average (the chain's own input) where neither book prices the match
OddsTrader's lines stamped more than 30 minutes after the listed start are left out (some are in-play prices). The
rules are the odds-sources study's (src/eda/odds_sources/: quality.drop_late, pools.reconciled), so the study and the
model use one implementation.

NOTE (the owner, 9 Oct 2026). Pinnacle's own closes are missing from August 2025. If they are obtained, the model is
retrained on Pinnacle's closes throughout, replacing the BetOnline stand-ins. Live, at every venue, the model is fed
Pinnacle's current line with the margin removed (BetOnline's while Pinnacle has none).

    --apply <folder>            a built instance (the folder run_chain.py --collect wrote): the per-source table of its
                                matches first (odds_sources/table.py's build on its frame and Stage 1; OddsTrader's link
                                and every-book lines must cover them), then the frame rewritten
    --from-reference <folder>   a new instance from the frozen reference's frame and input list (the same matches and
                                inputs; only the odds input changes), with the odds-sources study's table of those matches
The rewrite: in_odds_logit = the chance's log-odds, p_mkt = the chance (the frame's "closing price" for scoring),
odds_input = its source, p_mkt_avg = the books' average (the earlier input). A frame already rewritten is refused.
Also written: odds_input.json (counts by tour, season and source; the rule; the sources' SHA-256) and book_prices.parquet
(gitignored: OddsTrader's prices are not committed): per match, the decimal odds for A and B of the Pinnacle close used
and of BetOnline's close, for backtests at either book.
Run: ./python.sh src/eda/current_best_model/odds_input.py --apply <folder> | --from-reference <folder>
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.odds_sources import pools as P  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402
from src.eda.odds_sources import table as T  # noqa: E402

LIVE_STAGE1 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet"
KINDS = ("pinnacle (tennis-data)", "pinnacle (oddstrader)", "betonline", "average")
NOTE = ("Pinnacle's own closes are missing from August 2025 (tennis-data's column stops being Pinnacle's close; "
        "OddsTrader's recording stops on 7 Sep 2025). If they are obtained, the model is retrained on Pinnacle's closes "
        "throughout, replacing the BetOnline stand-ins (the owner, 9 Oct 2026). Live, at every venue: Pinnacle's current "
        "line with the margin removed, BetOnline's while Pinnacle has none.")


def construct(sources: pd.DataFrame) -> pd.DataFrame:
    """Per match: the Pinnacle-first chance of A, its source, and the decimal odds of the Pinnacle close used and of
    BetOnline's close. Reads no result."""
    df = Q.drop_late(sources).reset_index(drop=True)
    p_pin, _, choice = P.reconciled(df, with_choice=True)
    p_bol, p_avg = df["p_ot8"].to_numpy(float), df["p_avg"].to_numpy(float)
    has_pin, has_bol = np.isfinite(p_pin), np.isfinite(p_bol)
    p = np.where(has_pin, p_pin, np.where(has_bol, p_bol, p_avg))
    kind = np.where(has_pin, np.where(choice == "oddstrader", KINDS[1], KINDS[0]),
                    np.where(has_bol, KINDS[2], KINDS[3]))
    td, ot = choice == "tennis-data", choice == "oddstrader"
    out = pd.DataFrame({
        "match_id": df["match_id"].astype(str).to_numpy(), "p_input": p, "odds_input": kind,
        "pin_a": np.where(td, df["ps_a"], np.where(ot, df["ot20_a"], np.nan)),
        "pin_b": np.where(td, df["ps_b"], np.where(ot, df["ot20_b"], np.nan)),
        "bol_a": df["ot8_a"].to_numpy(float), "bol_b": df["ot8_b"].to_numpy(float),
        "bol_after_listed_min": df["after_ot8_min"].to_numpy(float), "p_avg": p_avg})
    if not np.isfinite(out["p_input"]).all():
        raise RuntimeError(f"{int((~np.isfinite(out['p_input'])).sum())} matches have no price at all")
    priced = out["pin_a"].notna()
    check = OC.devig(out.loc[priced, "pin_a"], out.loc[priced, "pin_b"])
    if not np.allclose(check, out.loc[priced, "p_input"], atol=1e-12):
        raise RuntimeError("the Pinnacle odds kept do not give the chance used")
    return out


def rewrite(folder: Path, built: pd.DataFrame, sources_desc: dict) -> dict:
    """Rewrite folder/model_frame.parquet's odds input with `built` (match order and columns kept)."""
    path = folder / "model_frame.parquet"
    f = pd.read_parquet(path)
    if "odds_input" in f.columns:
        raise SystemExit(f"{path}: the odds input was already rewritten")
    ids = f["match_id"].astype(str)
    b = built.set_index("match_id").reindex(ids)
    if b["p_input"].isna().any():
        raise SystemExit(f"{int(b['p_input'].isna().sum())} frame matches are missing from the per-source table")
    if not np.allclose(b["p_avg"].to_numpy(float), f["p_mkt"].to_numpy(float), atol=1e-12):
        raise SystemExit("the per-source table's average differs from the frame's p_mkt: built on another frame")
    p = b["p_input"].to_numpy(float)
    f["p_mkt_avg"] = f["p_mkt"].to_numpy(float)
    f["p_mkt"] = p
    f["in_odds_logit"] = np.log(p / (1.0 - p))
    f["odds_input"] = b["odds_input"].to_numpy()
    f.to_parquet(path, index=False)
    b.reset_index().to_parquet(folder / "book_prices.parquet", index=False)
    by = pd.Series(1, index=f.index).groupby([f["tour"], f["season"], f["odds_input"]]).sum()
    record = {"decision": "docs/decisions/2026-10-09-pinnacle-first-odds-input.md", "note": NOTE,
              "rule": {"pinnacle_tennis_data_until": P.PS_FAITHFUL_UNTIL, "reconcile_log_odds": P.RECONCILE,
                       "min_other_books": P.MIN_REF, "late_line_minutes": Q.LATE_MIN,
                       "order": ["pinnacle", "betonline", "average"]},
              "matches": int(len(f)),
              "by_source": {k: int((f["odds_input"] == k).sum()) for k in KINDS},
              "by_tour_season_source": {f"{t}|{s}|{k}": int(v) for (t, s, k), v in by.items()},
              "frame_sha256": R.sha(path), **sources_desc}
    OC.write_json(folder / "odds_input.json", record)
    return record


def apply(folder: Path, stage1: Path = LIVE_STAGE1) -> dict:
    """A built instance: its per-source table, then the rewrite."""
    out = folder / "odds_sources.parquet"
    T.build(frame_path=folder / "model_frame.parquet", stage1_path=stage1, out_path=out,
            counts_path=folder / "odds_sources_counts.json")
    built = construct(pd.read_parquet(out))
    return rewrite(folder, built, {"sources_table": R.rel(out), "stage1": R.rel(stage1)})


def from_reference(folder: Path) -> dict:
    """A new instance: the frozen reference's frame and input list, with the Pinnacle-first odds input."""
    if (folder / "model_frame.parquet").exists():
        raise SystemExit(f"{folder} already holds a frame")
    folder.mkdir(parents=True, exist_ok=True)
    src = R.REF / "frozen" / "instance"
    for name in ("model_frame.parquet", "model_inputs.json"):
        shutil.copyfile(src / name, folder / name)
        (folder / name).chmod(0o644)                     # the frozen copies are read-only; these are the instance's
    sources = pd.read_parquet(OC.SOURCES)
    counts = OC.read_json(OC.OUT / "sources_counts.json")
    built = construct(sources)
    return rewrite(folder, built, {"from_reference": R.rel(src / "model_frame.parquet"),
                                   "sources_table": R.rel(OC.SOURCES), "sources_table_frame": counts.get("frame")})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", type=Path, help="a built instance's folder")
    g.add_argument("--from-reference", type=Path, help="a new folder for an instance from the frozen reference")
    ap.add_argument("--stage1", type=Path, default=LIVE_STAGE1, help="Stage 1's odds table for --apply")
    a = ap.parse_args()
    folder = a.apply or a.from_reference
    folder = folder if folder.is_absolute() else ROOT / folder
    rec = apply(folder, a.stage1) if a.apply else from_reference(folder)
    print(json.dumps({k: rec[k] for k in ("matches", "by_source")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
