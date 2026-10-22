"""How close a round-1 qualifying match's live row, built as a live run builds it before anything of its edition is
published, comes to the row Tennis My Life published once it was played (master pipeline process log, Part 8).

For every men's 2026 tour-level and Slam qualifying round-1 match in Tennis My Life's qualifying file (TML carries no
women's qualifying): Tennis My Life's rows cut to before the edition's first row (what a live run on that morning would
have read); the event built from its previous edition (src/pipeline/qualifying.previous_edition, built_event); each
player's columns from their latest earlier row, aged to the match's day (prediction_run/live_rows.player_columns). Then
field by field against the match's own row:
    the event     surface, indoor flag, level (as the model sees it: Slam qualifying or tour qualifying), best of
    the players   hand, height, country (equal or not), age (the difference in days), rank
The match's day is its own Tennis My Life date (the linker reads Pinnacle's start time; TML's date is a day late at some
events). Inputs the model reads from these: surface, indoor, level, best of, age; ranks are no input.
Writes data/studies/master_pipeline/qualifying_replay/rows_check.csv (one row per match) and rows_check.json.
Run: ./python.sh src/eda/master_pipeline/qualifying_rows_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import live_rows as LR  # noqa: E402
from src.pipeline import live as L  # noqa: E402
from src.pipeline import qualifying as Q  # noqa: E402

OUT = ROOT / "data" / "studies" / "master_pipeline" / "qualifying_replay"


def main() -> int:
    tml = L._tml([2025, 2026])
    q1 = tml[tml["tour"].eq("atp") & tml["round"].astype(str).str.upper().eq("Q1")
             & tml["_date"].dt.year.eq(2026) & tml["tourney_level"].astype(str).isin(L.MAIN_TML_LEVELS)]
    rows = []
    for (tid, name), ev in q1.groupby(["_tid", "tourney_name"]):
        first = tml.loc[tml["_tid"].eq(tid) & tml["tourney_name"].eq(name), "_date"].min()
        cut = tml[tml["_date"] < first]
        prev, note = Q.previous_edition(cut, "atp", name, first, L.MAIN_TML_LEVELS)
        built = Q.built_event(prev, first) if prev else None
        empty = cut.iloc[0:0]
        for _, r in ev.iterrows():
            rec = {"tourney_id": tid, "event": name, "level": r["tourney_level"], "day": r["_date"].date().isoformat(),
                   "winner": r["winner_name"], "loser": r["loser_name"], "previous": prev["tid"] if prev else None,
                   "previous_note": note}
            if built:
                for k, col in (("event_surface", "surface"), ("event_indoor", "indoor"), ("event_level", "tourney_level"),
                               ("event_draw_size", "draw_size")):
                    rec[f"{col}_equal"] = str(built[k]).strip() == str(r[col]).strip() if col != "draw_size" else \
                        str(built[k]) == str(int(float(r[col]))) if str(r[col]).strip() else False
                slam_live, slam_true = str(built["event_level"]) == "G", str(r["tourney_level"]) == "G"
                rec["level_class_equal"] = slam_live == slam_true
                rec["best_of_live"] = Q.best_of("atp", built["event_level"], "Q1", prev) or 3
                rec["best_of_equal"] = int(rec["best_of_live"]) == int(float(r["best_of"] or 3))
            day = r["_date"].strftime("%Y%m%d")
            for side in ("winner", "loser"):
                try:
                    cols = LR.player_columns(cut, "atp", LR.B.S.name_key(str(r[f"{side}_name"])), empty, day)
                except SystemExit:
                    rec[f"{side}_found"] = False
                    continue
                rec[f"{side}_found"] = True
                for b in ("hand", "ht", "ioc"):
                    rec[f"{side}_{b}_equal"] = str(cols[b]).strip() == str(r[f"{side}_{b}"]).strip()
                live_age = pd.to_numeric(cols["age"], errors="coerce")
                true_age = pd.to_numeric(r[f"{side}_age"], errors="coerce")
                rec[f"{side}_age_days"] = float((live_age - true_age) * 365.25) if np.isfinite(live_age) and \
                    np.isfinite(true_age) else np.nan
                rec[f"{side}_rank_equal"] = str(cols["rank"]).strip() == str(r[f"{side}_rank"]).strip()
            rows.append(rec)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "rows_check.csv", index=False)

    def share(col) -> float | None:
        v = t[col].dropna() if col in t else pd.Series(dtype=bool)
        return round(float(v.astype(bool).mean()), 4) if len(v) else None
    ages = pd.concat([t["winner_age_days"], t["loser_age_days"]]).dropna()
    out = {"matches": int(len(t)), "editions": int(t["tourney_id"].nunique()),
           "previous_edition_found": round(float(t["previous"].notna().mean()), 4),
           "no_previous_edition": sorted(t.loc[t["previous"].isna(), "event"].unique().tolist()),
           "event": {c: share(f"{c}_equal") for c in ("surface", "indoor", "tourney_level", "draw_size")} | {
               "level_class (Slam or tour qualifying)": share("level_class_equal"), "best_of": share("best_of_equal")},
           "players_found": round(float(pd.concat([t["winner_found"], t["loser_found"]]).mean()), 4),
           "players": {b: round(float(pd.concat([t[f"winner_{b}_equal"], t[f"loser_{b}_equal"]]).dropna()
                                       .astype(bool).mean()), 4) for b in ("hand", "ht", "ioc", "rank")},
           "age_days": {"rows": int(len(ages)), "median_abs": float(ages.abs().median()),
                        "p90_abs": float(ages.abs().quantile(0.9)), "max_abs": float(ages.abs().max())},
           "events_with_a_differing_field": sorted(
               t.loc[~t[[c for c in t.columns if c.endswith("_equal") and c.startswith(("surface", "indoor",
                                                                                         "level_class", "best_of"))]]
                     .fillna(False).astype(bool).all(axis=1), "event"].unique().tolist())}
    (OUT / "rows_check.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
