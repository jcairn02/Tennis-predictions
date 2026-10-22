"""Tennis My Life's edition dates against the days the matches were played: the weekly check (owner, 14 Oct 2026).

Why. Since Sackmann's files ended (June 2026), Tennis My Life is Stage 0's only source of men's Challenger results, and
its own revisions enter by themselves (docs/decisions/2026-10-13-tml-lower-level-revisions.md). It dates some editions
in another week than the one played, often an earlier edition's date and name: 67 Challenger editions of 2018-2025, the
latest in 2025 (Nottingham, Manama, Targu Mures; docs/studies/p6_data_issues/README.md, section 3). While Sackmann's
copy stood beside it, Stage 0 kept his date; a misdated edition from Tennis My Life alone enters with its wrong date, and
the leak-proof clock then lets its results count before they were played (the third Tenerife Challenger of 2024 did).
The owner's decision of 14 Oct 2026 (docs/decisions/2026-10-14-p6-data-issues.md, point 3): check every week.

What. The P6 study's linking and edition verdicts (src/eda/p6_data_issues/tml_misdates.py, its functions, unchanged),
re-run on today's files: every Tennis My Life row of 2018 on, linked by the two players and identical set scores to
Sackmann's row, TennisLive's listing day, SofaScore's start and TDI's day; each edition's true start from the play days
(or Sackmann's date where they agree); an edition is MISDATED when Tennis My Life dates it in another week ("another
week (early)" or "(late)"). The study's misdated editions are the known list (KNOWN, data/studies/tml_revisions/
edition_dates/known.csv, written from the study on 14 Oct 2026 by --init-known), so an alarm names only an edition
flagged anew: a new edition, or an old one that Tennis My Life re-dated. Acknowledge one by adding it to KNOWN.
An edition of the current week has no play days yet: it is judged the week after.

Writes data/studies/tml_revisions/edition_dates/<label>/: editions.csv (every edition with its verdict and evidence),
misdated.csv (the misdated ones, "known" marked), summary.json (counts, the new editions' keys); and a line in
data/studies/tml_revisions/edition_dates/runs.jsonl.
Exit: 0 no new misdated edition; 3 a new one (the alarm, as the coverage check's); 1 a failure.

Run: ./python.sh src/eda/tml_revisions/edition_dates.py [--label weekly]      (about a minute; no request)
     ./python.sh src/eda/tml_revisions/edition_dates.py --init-known         (once: the known list from the study)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.p6_data_issues import tml_misdates as T  # noqa: E402  (the study's loaders, linker and verdicts)

OUT = ROOT / "data" / "studies" / "tml_revisions" / "edition_dates"
KNOWN = OUT / "known.csv"
STUDY_FLAGGED = ROOT / "data" / "studies" / "p6_data_issues" / "tml_misdates" / "misdated_editions.csv"
RUNS = OUT / "runs.jsonl"
ALARM = 3


def is_misdated(date_error: pd.Series) -> pd.Series:
    """The study's verdict 'another week (early)' or 'another week (late)' (not 'unresolved ...')."""
    return date_error.fillna("").astype(str).str.startswith("another week")


def editions_today() -> pd.DataFrame:
    """Every Tennis My Life edition of 2018 on with the study's verdict, on today's files (its main(), up to the
    editions' table, without its outputs)."""
    tml = T.load_tml()
    sources = {"sk": T.load_sackmann(), "tl": T.load_tennislive(), "ss": T.load_sofascore()}
    tdi = T.load_tdi()
    links = {}
    for name, right in sources.items():
        r = right.assign(rid=np.arange(len(right)))
        lk = T.link(tml, r)
        if name == "sk":
            lk = pd.concat([lk, T.link_same_event(tml, r, lk)], ignore_index=True)
        links[name] = lk.merge(r.drop(columns=["tour", "pair", "k1", "k2", "n1", "n2", "sig", "draw", "rnd"]),
                               on="rid", how="left")
    r = tdi.assign(rid=np.arange(len(tdi)))
    links["tdi"] = T.link_tdi(tml, r).merge(r[["rid", "day", "tournament"]], on="rid", how="left")
    t = T.attach(tml.copy(), links)
    t["cand_start"] = T.implied_start(t, T.round_offsets(t))
    return T.editions(t)


def new_misdated(ed: pd.DataFrame, known: set) -> pd.DataFrame:
    """The misdated editions not in the known list (by the study's edition key: tour|id|name|date)."""
    m = ed[is_misdated(ed["date_error"])]
    return m[~m["edition"].isin(known)]


def load_known(path: Path = KNOWN) -> set:
    return set(pd.read_csv(path, dtype=str)["edition"]) if path.exists() else set()


def init_known() -> int:
    """The known list from the P6 study's flagged editions (its misdated ones), with what was done about each."""
    f = pd.read_csv(STUDY_FLAGGED, dtype=str)
    f = f[f["category"].fillna("").str.startswith("misdated")].copy()
    tenerife = f["tml_id"].eq("2024-2847")
    f["status"] = np.where(tenerife, "Stage 0 holds Tennis My Life's date: date correction D1, decided by the owner on "
                                     "14 Oct 2026", "Stage 0 holds Sackmann's copy with the true date")
    f["acknowledged"] = "2026-10-14, the P6 data-issues study"
    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["edition", "tour", "season", "level", "tml_id", "tml_name", "tml_date", "true_start", "category", "status",
            "acknowledged"]
    f[[c for c in cols if c in f.columns]].to_csv(KNOWN, index=False)
    print(f"known list: {len(f)} editions -> {KNOWN.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--label", default="weekly")
    ap.add_argument("--init-known", action="store_true")
    a = ap.parse_args()
    if a.init_known:
        return init_known()
    known = load_known()
    if not known:
        print(f"no known list ({KNOWN}): run --init-known first", file=sys.stderr)
        return 1
    ed = editions_today()
    out = OUT / a.label
    out.mkdir(parents=True, exist_ok=True)
    ed.to_csv(out / "editions.csv", index=False, date_format="%Y-%m-%d")
    mis = ed[is_misdated(ed["date_error"])].copy()
    mis["known"] = mis["edition"].isin(known)
    mis.to_csv(out / "misdated.csv", index=False, date_format="%Y-%m-%d")
    new = new_misdated(ed, known)
    gone = sorted(known - set(mis["edition"]))
    summary = {"run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "editions": int(len(ed)),
               "misdated": int(len(mis)), "known_still_misdated": int(mis["known"].sum()),
               "known_no_longer_flagged": len(gone), "new": sorted(new["edition"]),
               "new_detail": [{"edition": r.edition, "level": r.level, "tml_date": str(r.tml_date)[:10],
                               "true_start": str(r.true_start)[:10], "date_error": r.date_error}
                              for r in new.itertuples()],
               "known_list": str(KNOWN.relative_to(ROOT))}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    with RUNS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({k: summary[k] for k in ("run_at", "editions", "misdated", "known_still_misdated",
                                                      "new")} | {"label": a.label}) + "\n")
    print(f"{len(ed):,} editions; {len(mis)} misdated, {int(mis['known'].sum())} of them known; new: {len(new)}")
    return ALARM if len(new) else 0


if __name__ == "__main__":
    raise SystemExit(main())
