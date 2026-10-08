"""Exact days from Sackmann's point-by-point copy, linked to Stage 0 (the match-timing study).

Source: data/raw/point_shot_sources/pbp_copy_2015/ and pbp_copy_2018/ (two GitHub snapshots of Jeff Sackmann's
tennis_pointbypoint): men's tour, Challenger and Futures matches, main draws and qualifying, with a date on every match
from July 2011 to February 2017 (the online research's finding, docs/research/match-timing/README.md). Names are
abbreviated ('P Heras'); there is no round label, only Main or Qual; scores are given.

Linking reuses the small-sources linker (srcb_common.Linker): both players' abbreviated keys within the match's
expected days, confirmed by identical set scores; then a one-player anchor with identical scores. The copy does not say
which calendar its dates follow, so every day is kept as 'utc_date' (the local day may be one either side).

Writes data/studies/match_timing/links/pbp_copy.parquet and pbp_copy.json.
Run: ./python.sh src/eda/match_timing/link_pbp_copy.py
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import link_sources_b as LB  # noqa: E402
from src.eda.match_timing import srcb_common as X  # noqa: E402
from src.eda.match_timing import srcb_sources as SRC  # noqa: E402

FILES = sorted(glob.glob(str(ROOT / "data/raw/point_shot_sources/pbp_copy_20*/pbp_matches_*.csv")))


def load() -> tuple[pd.DataFrame, dict]:
    frames = []
    cols = ["date", "tny_name", "tour", "draw", "server1", "server2", "winner", "score"]
    for f in FILES:
        d = pd.read_csv(f, dtype=str)                   # the 2015 snapshot predates the pbp_id column
        frames.append(d[cols].assign(file=Path(f).name))
    df = pd.concat(frames, ignore_index=True)
    info = {"files": len(FILES), "rows_read": int(len(df))}
    # one key per match from its own content, so the two snapshots' copies of a match collapse to one row
    df["pbp_id"] = (df["date"].fillna("") + "|" + df["tny_name"].fillna("") + "|" + df["server1"].fillna("") + "|"
                    + df["server2"].fillna("") + "|" + df["score"].fillna(""))
    df = df.drop_duplicates("pbp_id", keep="last")
    info["distinct_matches"] = int(len(df))
    day = pd.to_datetime(df["date"], format="%d %b %y", errors="coerce")
    keep = day.notna() & (day >= pd.Timestamp("2009-12-01"))
    info["left_out_unreadable_or_early_date"] = int((~keep).sum())
    doubles = df["server1"].fillna("").str.contains("/") | df["server2"].fillna("").str.contains("/")
    info["left_out_doubles"] = int((keep & doubles).sum())
    keep &= ~doubles
    df, day = df[keep], day[keep]
    qual = df["draw"].astype(str).str.lower().str.startswith("qual")
    out = pd.DataFrame({
        "source_key": "pbp:" + df["pbp_id"].astype(str).to_numpy(), "tour": "atp", "date": day.to_numpy(),
        "name1": df["server1"].to_numpy(), "name2": df["server2"].to_numpy(),
        "sets": [X.sets_of_score(s) for s in df["score"].fillna("")],
        "rspec": [X.round_spec("", bool(q)) for q in qual], "tournament": df["tny_name"].to_numpy()})
    # an abbreviated name ('P Heras') gives its one key; a full name ('Roger Federer') gives its abbreviated forms (and,
    # through _finish, its full key), as the other sources' linkers do
    for side in ("1", "2"):
        out["a" + side] = out["name" + side].map(lambda n: (X.abbr_short(n),) if X.abbr_short(n) else X.abbr_from_full(n))
    out = SRC._finish(out)
    info["rows_in_scope"] = int(len(out))
    info["date_range"] = [str(out["date"].min().date()), str(out["date"].max().date())]
    return out, info


def main() -> int:
    src, info = load()
    s0 = X.load_stage0()
    scope = LB.scope_by_dates(s0, src, tours=("atp",))
    L = X.Linker("pbp_copy", src, s0, scope)
    sl = X.src_long_from(src, f1="f1", f2="f2", a1="a1", a2="a2")
    tl = X.s0_long(s0, scope, forms=("F", "A"))
    L.pair_pass("full_names", sl, ["F"], s0_long_=tl)
    L.pair_pass("abbreviated_names", sl, ["A"], s0_long_=tl)
    L.anchor_pass("one_player_anchor", sl, forms=("F", "A"), need_score=True, s0_long_=tl)
    res = LB.package("pbp_copy", L, src, s0, info, "local_date",
                     ["The copy's day; its calendar is unstated, so kept as utc_date (one day either side)."])
    out = res["out"].copy()
    out["date_basis"] = "utc_date"
    X.write_links(out, MT.LINKS / "pbp_copy.parquet")
    st = res["status"].value_counts().to_dict()
    lk = out.assign(level=out["level"], qual=out["qualifying"])
    info.update({"status": st, "passes": res["passes"],
                 "linked_by_level": lk.groupby(["level", "qual"]).size().rename("linked").reset_index().to_dict("records"),
                 "linked_by_year": lk.groupby("year").size().to_dict(),
                 "score_agrees": int(out["score_agrees"].fillna(False).sum())})
    MT.jdump(info, MT.LINKS / "pbp_copy.json")
    MT.log(f"pbp copy: {len(out):,} of {info['rows_in_scope']:,} rows linked; {st}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
