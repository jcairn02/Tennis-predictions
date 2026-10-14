"""Assemble the G2 rulings (rulings_a/b/c) with the measured metrics (audit.py) and the test-window row counts
(test_counts.py) into data/studies/feature_interactions/round1/feasibility.csv and one file per family under
docs/studies/feature_interactions/round1/feasibility/. Run after audit.py and test_counts.py.
Run: ./python.sh src/eda/feature_interactions/round1/feasibility/assemble.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402
from src.eda.feature_interactions.round1.feasibility import rulings_a, rulings_b, rulings_c  # noqa: E402
from src.eda.feature_interactions.round1.feasibility.family_notes import FAMILY_NOTES  # noqa: E402

DOCS = B.ROOT / "docs" / "studies" / "feature_interactions" / "round1" / "feasibility"
TIMING = {"SAFE": "safe by construction (own matches in order)",
          "CLOCK-BUILT": "solved together; inputs already built on the leak-proof clock",
          "CLOCK-NEW": "cross-player; must be built on the leak-proof clock and pass probe.py",
          "MARKET": "the match's own closing quotes (pre-match)",
          "WF-RESULTS": "uses a fit on results: walk-forward by season, strictly earlier seasons (M6)",
          "STATIC": "static attribute or schedule, known before the match"}
# coverage of candidates not built here, estimated from their inputs (men d, women d, men r, women r) and why
EST = {"I-007": ((1, 1, 1, 1), "model frame"), "I-018": ((0.999, 0.994, 1.0, 0.979), "both hands known"),
       "I-021": ((0.999, 0.994, 1.0, 0.979), "both hands known"), "I-025": ((1, 1, 1, 1), "own history, 0 when empty"),
       "I-028": ((1, 1, 1, 1), "set scores"), "I-058": ((0.999, 0.944, 1.0, 0.995), "box scores both, this match's tour level"),
       "I-060": ((1, 1, 1, 1), "country; event country to extend"), "I-067": ((np.nan,) * 4, "data not held"),
       "I-072": ((1, 1, 1, 1), "box-score history by event"), "I-073": ((1.0, 0.0, 1.0, 0.0), "indoor flag: men only"),
       "I-074": ((np.nan,) * 4, "table not held"), "I-075": ((np.nan,) * 4, "tables not held"),
       "I-077": ((np.nan,) * 4, "table not held"), "I-082": ((1, 1, 1, 1), "weight 0 without evidence"),
       "I-085": ((0.3775, 0.3188, 1.0, 1.0), "no-odds forecasts from 2019 only")}
MEN_ONLY = {"I-022", "I-023", "I-024", "I-050", "I-073"}


def main() -> int:
    R = {**rulings_a.R, **rulings_b.R, **rulings_c.R}
    met = pd.read_csv(B.OUT / "feasibility_metrics.csv")
    tc = json.loads((B.OUT / "test_counts.json").read_text(encoding="utf-8"))
    n_all = tc["model_rows_2025_2026"]
    special = {"I-020": tc["speed_history_both"], "I-039": tc["pinnacle_present"]}
    ml = pd.read_csv(B.C.OUT / "master_list.csv", usecols=["master_id", "family_no", "family", "title", "type"])
    rows = []
    for _, m in ml.iterrows():
        hid = m["master_id"]
        tables, timing, probe, hours, verdict, reason, notes = R[hid]
        mm = met[met["hid"] == hid]
        prim = mm[mm["primary"]].iloc[0] if len(mm) else None
        if prim is not None:
            cov = [prim[k] for k in ("cov_disc_atp", "cov_disc_wta", "cov_rep_atp", "cov_rep_wta")]
            r2, r2a, swap = prim["novelty_r2"], prim["novelty_r2_aug"], bool(prim["swap_ok"])
            others = "; ".join(f"{r.column} R2 {r.novelty_r2:.2f}" for r in mm[~mm["primary"]].itertuples())
            built = f"built here ({prim['column']}); swap {'ok' if swap else 'FAILS'}; aug R2 {r2a:.2f}"
        else:
            cov, why = EST.get(hid, ((np.nan,) * 4, "not built"))
            cov, r2, others, built = list(cov), np.nan, "", f"not built here; coverage estimated ({why}); R2 in round 2"
        n = special.get(hid, {"atp": n_all["atp"], "wta": 0 if hid in MEN_ONLY else n_all["wta"]})
        if hid in ("I-022", "I-023", "I-024"):
            n = {"atp": tc["height_both_present"]["atp"], "wta": 0}
        rows.append({"hid": hid, "family_no": f"{int(m['family_no']):02d}", "title": m["title"], "type": m["type"],
                     "tables_columns": tables, "cov_disc_atp": cov[0], "cov_disc_wta": cov[1], "cov_rep_atp": cov[2],
                     "cov_rep_wta": cov[3], "n_test_2025_2026": int(n["atp"] + n["wta"]),
                     "timing_class": TIMING[timing], "probe_needed": probe, "novelty_r2": r2, "build_hours": hours,
                     "verdict": verdict, "reason": reason,
                     "notes": "; ".join(x for x in (notes, built, others) if x)})
    F = pd.DataFrame(rows)
    keep = ["hid", "tables_columns", "cov_disc_atp", "cov_disc_wta", "cov_rep_atp", "cov_rep_wta", "n_test_2025_2026",
            "timing_class", "probe_needed", "novelty_r2", "build_hours", "verdict", "reason", "notes"]
    F[keep].to_csv(B.OUT / "feasibility.csv", index=False)
    DOCS.mkdir(parents=True, exist_ok=True)
    fam_files = sorted((B.C.DOCS / "master_list").glob("[0-9][0-9]_*.md"))
    for f in fam_files:
        no = f.name[:2]
        g = F[F["family_no"] == no]
        pct = lambda v: "–" if pd.isna(v) else f"{100 * v:.0f}"  # noqa: E731
        fam_name = ml.loc[ml["family_no"].astype(int) == int(no), "family"].iloc[0]
        lines = [f"# Feasibility (G2) · family {no}: {fam_name}", "",
                 f"6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/{f.name})",
                 "", "Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). "
                 "R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). "
                 "Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.", "",
                 "| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |",
                 "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in g.itertuples():
            cov = f"{pct(r.cov_disc_atp)} / {pct(r.cov_disc_wta)} | {pct(r.cov_rep_atp)} / {pct(r.cov_rep_wta)}"
            r2 = "–" if pd.isna(r.novelty_r2) else f"{r.novelty_r2:.2f}"
            code = [k for k, v in TIMING.items() if v == r.timing_class][0]
            cells = [r.hid, r.title, r.tables_columns, cov, f"{r.n_test_2025_2026:,}", code, r.probe_needed, r2,
                     str(r.build_hours), f"**{r.verdict}**", f"{r.reason}. {r.notes}"]
            lines.append("| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |")
        lines += ["", "## Auditor's notes", "", FAMILY_NOTES.get(no, "None beyond the table."), ""]
        (DOCS / f.name).write_text("\n".join(lines), encoding="utf-8")
    print(F["verdict"].value_counts().to_dict(), "hours:", F.groupby("verdict")["build_hours"].sum().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
