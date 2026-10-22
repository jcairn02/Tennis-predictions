"""The odds rule of 21 Oct 2026 on a built instance's frame, in memory: which source each match would take, month by
month, against the rule it was built with; TennisExplorer's coverage and the step's 75% guard. Nothing is fitted, no
result is read, and the instance is not touched (the owner deferred the test build on 21 Oct 2026: "DO NOT DO THE TEST
YET"). Uses the site's tables as staged (no download) and the live Stage 0's player names.

Writes data/studies/pinnacle_gap/dry_run.json (counts only).

    ./python.sh src/eda/pinnacle_gap/dry_run.py [--instance data/studies/current_best_model/template_2026-10-21b]
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import odds_input as O  # noqa: E402
from src.eda.odds_sources import common as OC  # noqa: E402
from src.ingest import tennisexplorer as TEI  # noqa: E402

OUT = ROOT / "data" / "studies" / "pinnacle_gap" / "dry_run.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", type=Path, default=ROOT / "data" / "studies" / "current_best_model" /
                    "template_2026-10-21b")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    inst = a.instance if a.instance.is_absolute() else ROOT / a.instance
    sources = pd.read_parquet(inst / "odds_sources.parquet")
    before = pd.read_parquet(inst / "book_prices.parquet").set_index("match_id")
    frame = pd.read_parquet(inst / "model_frame.parquet", columns=["match_id", "tournament_date", "tour"])
    link, how = TEI.link_frame(inst / "model_frame.parquet", dt.date.fromisoformat(O.TE_LINK_SINCE))
    te = O.te_columns(link)
    timed = te["tex_timed"]
    s = sources.drop(columns=[c for c in sources.columns if c.startswith("tex_")]).merge(te, on="match_id", how="left")
    built = O.construct(s, O.RULE)
    cov = O.te_coverage(frame, built)
    b = built.set_index("match_id").reindex(before.index)
    f = frame.set_index("match_id").reindex(before.index)
    month = pd.to_datetime(f["tournament_date"]).dt.strftime("%Y-%m")
    era = month >= "2025-08"
    tab = pd.crosstab([month[era], before.loc[era, "odds_input"].rename("before")],
                      b.loc[era, "odds_input"].rename("now"))
    changed = b["odds_input"] != before["odds_input"]
    out = {"instance": str(inst.relative_to(ROOT)), "rule": O.RULE, "link": how,
           "te_rows_timed": int(timed.sum()), "te_rows_with_pinnacle": int(link["pin_a"].notna().sum()),
           "changed_matches": int(changed.sum()),
           "changed_by_kind": {f"{k[0]} -> {k[1]}": int(v) for k, v in
                               pd.crosstab(before.loc[changed, "odds_input"], b.loc[changed, "odds_input"]).stack().items()
                               if v},
           "changed_before_2025_08": sorted(before.index[changed & ~era].astype(str)),
           "by_source_now": {k: int((b["odds_input"] == k).sum()) for k in O.KINDS},
           "tennisexplorer_coverage": cov, "guard_passes": not cov["low_months"],
           "tennis_data_swapped": sorted(b.index[b["tennis_data_swapped"]].astype(str)),
           "tennisexplorer_gross_vs_betonline": sorted(b.index[b["te_bol_gross"]].astype(str)),
           "tennisexplorer_left_out": {m: r for m, r in b["te_left_out"].items() if r},
           "by_month": {f"{m}|{k}": {c: int(v) for c, v in r.items() if v} for (m, k), r in tab.iterrows()}}
    OC.write_json(OUT, out)
    print(f"link: {how}")
    print(f"changed: {out['changed_matches']}  by kind: {out['changed_by_kind']}")
    print(f"before Aug 2025: {out['changed_before_2025_08']}")
    print(f"by source now: {out['by_source_now']}")
    print("TennisExplorer's share by month:", {m: r["share"] for m, r in cov["by_month"].items()})
    print(f"guard passes: {out['guard_passes']} (low months: {cov['low_months']})")
    print(f"TennisExplorer far from BetOnline (listed): {len(out['tennisexplorer_gross_vs_betonline'])}")
    print(f"tennis-data swapped: {out['tennis_data_swapped']}")
    print(f"the site's Pinnacle left out: {out['tennisexplorer_left_out']}")
    print(tab.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
