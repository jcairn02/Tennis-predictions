"""Odds sources, step 1: the table. One row per model-frame match, 2013 on, with every source's price for side A.

    --link    tennis-data's rows of 2018 on (every season staged: common.td_seasons) linked to OddsTrader's listed
              singles events with the sharp benchmark's linker
              (as the BetOnline-lines and bet-timing studies link them): oddstrader_link.parquet (gitignored) and the
              event ids for the every-book pull, oddstrader_eids.csv
    --build   after `src.ingest.oddstrader --books-eids`: sources.parquet (gitignored: OddsTrader's prices are not
              republished) and sources_counts.json

Sources, each as decimal odds for A and B, P(A) with the margin removed proportionally, and a coherence flag (both
prices above 1, overround 1.00-1.20):
    avg, max, ps, b365   tennis-data's closes as Stage 1 holds them for the frame (frozen reference of 8 Oct 2026):
                         OddsPortal's average and maximum, Pinnacle, Bet365. Untimed ("generally the most recent before
                         play starts", the provider's claim). avg is the current model's odds input
    bfe, ex, lb          tennis-data's Betfair exchange (from Aug 2025), Expekt and Ladbrokes (to 2018) closes, read with
                         the sharp benchmark's loader and joined on tour, day, winner and loser
    ot<id>               OddsTrader's last line of book <id> (BetOnline is ot8, Pinnacle ot20), with its UTC stamp and
                         the minutes after OddsTrader's listed start; ot20o is Pinnacle's opening line there
    pm_m30               Polymarket 30 minutes before the listed start (2025-2026; the sharp benchmark's table)

A is the frame's side A; the label is the frame's a_won. tennis-data's winner is A unless Stage 1 linked the row with
winner and loser exchanged (as frame.py of the bet-timing study orients BetOnline).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.betonline_lines import sharpness as SH  # noqa: E402
from src.eda.odds_sources import common as C  # noqa: E402
from src.eda.sharp_benchmark import build as BLD  # noqa: E402

KEY = ["tour", "td_date", "td_winner", "td_loser"]
TD_BOOKS = {"avg": "avg", "max": "max", "ps": "ps", "b365": "b365"}     # Stage 1's <book>_a / <book>_b
TD_EXTRA = {"bfe": ("BFEW", "BFEL"), "ex": ("EXW", "EXL"), "lb": ("LBW", "LBL")}
MIN_LINES_PER_BOOK = 500     # an OddsTrader book with fewer coherent last lines on frame matches is left out


def link() -> int:
    td = SH.load_tennis_data(C.OT_SEASONS)
    bo, frame = SH.betonline_markets()
    lk = BLD.link(td, frame).rename(columns={"condition_id": "eid", "a_won": "away_is_td_winner", "gap": "link_gap"})
    out = td[["td_id", "tour", "season", "date", "winner", "loser"]].merge(lk, on="td_id", how="inner",
                                                                          validate="one_to_one")
    C.OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(C.LINK, index=False)
    pd.DataFrame({"eid": sorted(out["eid"].astype(int).unique())}).to_csv(C.EIDS, index=False)
    by = td.groupby("season").size().to_frame("tennis_data_rows").join(out.groupby("season").size().rename("linked"))
    counts = {"tennis_data_rows": int(len(td)), "linked": int(len(out)),
              "by_season": {str(s): {"rows": int(r.tennis_data_rows), "linked": int(r.linked)} for s, r in by.iterrows()}}
    C.write_json(C.OUT / "link_counts.json", counts)
    C.log(f"link: {counts['linked']:,} of {counts['tennis_data_rows']:,} tennis-data rows; {len(set(out['eid'])):,} events")
    return 0


def frame_rows(frame_path: Path = C.MODEL_FRAME, stage1_path: Path = C.STAGE1) -> pd.DataFrame:
    """The frame's matches with the label and Stage 1's tennis-data keys and prices (oriented to A)."""
    f = pd.read_parquet(frame_path, columns=["match_id", "tour", "season", "tournament_date", "a_won", "p_mkt"])
    f["match_id"] = f["match_id"].astype(str)
    s1 = pd.read_parquet(stage1_path)
    s1["match_id"] = s1["match_id"].astype(str)
    cols = ["match_id", "link", "td_date", "td_winner", "td_loser", "td_round"] + \
        [f"{b}_{s}" for b in TD_BOOKS.values() for s in "ab"]
    f = f.merge(s1[cols], on="match_id", how="left", validate="one_to_one")
    f["a_is_w"] = f["a_won"].astype(bool).to_numpy() ^ f["link"].eq("winner_swapped").to_numpy()
    f["td_date"] = pd.to_datetime(f["td_date"]).dt.normalize()
    f["td_winner"], f["td_loser"] = f["td_winner"].astype(str), f["td_loser"].astype(str)
    return f


def add(cols: dict, name: str, d_a, d_b) -> None:
    """A source's columns into cols: coherent odds for A and B, P(A) margin-free, overround, quoted at all."""
    d_a, d_b = np.asarray(d_a, dtype=float), np.asarray(d_b, dtype=float)
    ok = C.coherent(d_a, d_b)
    cols[f"{name}_a"], cols[f"{name}_b"] = np.where(ok, d_a, np.nan), np.where(ok, d_b, np.nan)
    cols[f"p_{name}"] = np.where(ok, C.devig(d_a, d_b), np.nan)
    cols[f"over_{name}"] = np.where(ok, 1.0 / d_a + 1.0 / d_b, np.nan)
    cols[f"raw_{name}"] = np.isfinite(d_a) & np.isfinite(d_b)


def keyed(df: pd.DataFrame) -> pd.DataFrame:
    """tennis-data rows on the join key; a key two rows share is dropped (as frame.py of the bet-timing study)."""
    df = df.rename(columns={"date": "td_date", "winner": "td_winner", "loser": "td_loser"})
    df["td_date"] = pd.to_datetime(df["td_date"]).dt.normalize()
    df["td_winner"], df["td_loser"] = df["td_winner"].astype(str), df["td_loser"].astype(str)
    return df[~df.duplicated(KEY, keep=False)]


def tennis_data_extra(f: pd.DataFrame) -> pd.DataFrame:
    """tennis-data's Betfair, Expekt and Ladbrokes closes and Polymarket's 30-minute price on the frame's keys."""
    saved = dict(BLD.BOOKS)
    BLD.BOOKS.update(TD_EXTRA)                  # the loader reads and cleans every pair in BLD.BOOKS
    try:
        td = SH.load_tennis_data(C.FRAME_SEASONS)
    finally:
        BLD.BOOKS.clear()
        BLD.BOOKS.update(saved)
    cols = [c for pair in TD_EXTRA.values() for c in pair]
    td = keyed(td[["tour", "date", "winner", "loser"] + cols])
    sb = keyed(pd.read_parquet(C.POLYMARKET, columns=["tour", "date", "winner", "loser", "pw_pm_m30"]))
    o = f[["match_id", "a_is_w"] + KEY].merge(td, on=KEY, how="left", validate="one_to_one")
    return o.merge(sb, on=KEY, how="left", validate="one_to_one")


def oddstrader(f: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Every OddsTrader book's last line (and Pinnacle's opening) for A and B, with stamps, on the frame's matches."""
    lk = pd.read_parquet(C.LINK).rename(columns={"date": "td_date", "winner": "td_winner", "loser": "td_loser"})
    lk["td_date"] = pd.to_datetime(lk["td_date"]).dt.normalize()
    lk["td_winner"], lk["td_loser"] = lk["td_winner"].astype(str), lk["td_loser"].astype(str)
    o = f[["match_id", "a_is_w"] + KEY].merge(lk[KEY + ["eid", "away_is_td_winner"]], on=KEY, how="inner",
                                              validate="one_to_one")
    ev = pd.read_parquet(C.OT_EVENTS, columns=["eid", "dt_ms", "home_partid", "away_partid"])
    o = o.merge(ev, on="eid", how="left", validate="many_to_one")
    # A's side at OddsTrader: tennis-data's winner is the away side when away_is_td_winner
    a_is_away = o["a_is_w"].to_numpy(bool) == o["away_is_td_winner"].to_numpy(bool)
    o["part_a"] = np.where(a_is_away, o["away_partid"], o["home_partid"])
    o["part_b"] = np.where(a_is_away, o["home_partid"], o["away_partid"])
    lines = pd.read_parquet(C.OT_BOOKS, columns=["kind", "paid", "eid", "partid", "pri", "tim_ms", "iof"])
    lines = lines[lines["eid"].isin(o["eid"])]
    wide = {}
    for (kind, paid), g in lines.groupby(["kind", "paid"]):
        name = f"ot{int(paid)}" + ("o" if kind == "open" else "")
        g = g.set_index(["eid", "partid"])
        pa = g["pri"].reindex(list(zip(o["eid"], o["part_a"]))).to_numpy(float)
        pb = g["pri"].reindex(list(zip(o["eid"], o["part_b"]))).to_numpy(float)
        ta = g["tim_ms"].reindex(list(zip(o["eid"], o["part_a"]))).to_numpy(float)
        tb = g["tim_ms"].reindex(list(zip(o["eid"], o["part_b"]))).to_numpy(float)
        if np.isfinite(pa).sum() == 0:
            continue
        wide[name] = (pa, pb, np.fmax(ta, tb))
    listed = o["dt_ms"].to_numpy(float)
    cols = {"match_id": o["match_id"].to_numpy(), "eid": o["eid"].to_numpy(), "t_listed_ms": listed}
    kept, dropped = [], []
    for name, (pa, pb, t) in sorted(wide.items(), key=lambda kv: int(kv[0][2:].rstrip("o"))):
        if C.coherent(pa, pb).sum() < MIN_LINES_PER_BOOK:
            dropped.append(name)
            continue
        add(cols, name, pa, pb)
        cols[f"t_{name}_ms"] = t
        cols[f"after_{name}_min"] = (t - listed) / 60000.0
        kept.append(name)
    return pd.DataFrame(cols), {"frame_matches_linked": int(len(o)), "books_kept": kept,
                                "books_dropped_few_lines": dropped}


def build(frame_path: Path = C.MODEL_FRAME, stage1_path: Path = C.STAGE1, out_path: Path = C.SOURCES,
          counts_path: Path = C.OUT / "sources_counts.json") -> int:
    """The per-source table of a frame's matches (default: the frozen reference's frame, this study's table). The
    frame's p_mkt must still be the books' average (a frame the Pinnacle-first step has rewritten is refused)."""
    f = frame_rows(frame_path, stage1_path)
    cols = {}
    for name, col in TD_BOOKS.items():
        add(cols, name, f[f"{col}_a"], f[f"{col}_b"])
    x = tennis_data_extra(f)
    if not (x["match_id"].to_numpy() == f["match_id"].to_numpy()).all():
        raise RuntimeError("the extra tennis-data books are not in the frame's row order")
    a = x["a_is_w"].to_numpy(bool)
    for name, (w, l) in TD_EXTRA.items():
        add(cols, name, np.where(a, x[w], x[l]), np.where(a, x[l], x[w]))
    cols["p_pm_m30"] = np.where(a, x["pw_pm_m30"], 1.0 - x["pw_pm_m30"])
    base = f[["match_id", "tour", "season", "tournament_date", "td_date", "td_round", "a_won", "p_mkt"]]
    out = pd.concat([base.reset_index(drop=True), pd.DataFrame(cols)], axis=1)
    if not np.allclose(out["p_avg"].dropna(), out.loc[out["p_avg"].notna(), "p_mkt"]):
        raise RuntimeError("the frame's market input is not Stage 1's average with the margin removed")
    ot, ot_counts = oddstrader(f)
    out = out.merge(ot, on="match_id", how="left", validate="one_to_one")
    out["block"] = C.blocks(out["td_date"].to_numpy("datetime64[D]"))
    out.to_parquet(out_path, index=False)
    priced = {s: {str(k): int(v) for k, v in out.groupby("season")[f"p_{s}"].count().items()}
              for s in ["avg", "max", "ps", "b365"] + list(TD_EXTRA) + ["pm_m30"] + ot_counts["books_kept"]}
    counts = {"matches": int(len(out)), "frame": str(frame_path), "stage1": str(stage1_path), **ot_counts,
              "priced_by_season": priced}
    C.write_json(counts_path, counts)
    C.log(f"{out_path.name}: {len(out):,} matches; OddsTrader books kept {len(ot_counts['books_kept'])}")
    return 0


if __name__ == "__main__":
    if "--link" in sys.argv:
        sys.exit(link())
    if "--build" in sys.argv:
        sys.exit(build())
    print(__doc__)
    sys.exit(2)
