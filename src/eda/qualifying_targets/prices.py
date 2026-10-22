"""Step 4: the closing prices of the study's qualifying matches, and the odds input they give the model.

For each linked qualifying match (link.py), from OddsTrader's every-book lines (books_lines.parquet, after the pull of
22 Oct 2026), oriented to Stage 0's side A by OddsTrader's participant ids (away_is_a):
    pin    Pinnacle's last line (book 20) and its opening line (pino)
    bol    BetOnline's last line (book 8); also read from the BetOnline-only pull (lines.parquet) as a cross-check
A line counts when both prices are above 1 with an overround of 1.00-1.20 (coherent) and it is stamped no later than
30 minutes after OddsTrader's listed start (the odds-sources rules: odds_sources/quality.drop_late, LATE_MIN); the
margin is removed proportionally. The odds input, as the instance's rule ranks the books: Pinnacle's close, else
BetOnline's, else none (no tennis-data average exists for qualifying). Reads no result.

Writes data/studies/qualifying_targets/prices.parquet and prices_counts.json.
Run: ./python.sh src/eda/qualifying_targets/prices.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.qualifying_targets import common as C  # noqa: E402

BOOKS = {"pin": ("last", C.PINNACLE), "pino": ("open", C.PINNACLE), "bol": ("last", C.BETONLINE)}


def devig(d_a, d_b) -> np.ndarray:
    ia, ib = 1.0 / np.asarray(d_a, float), 1.0 / np.asarray(d_b, float)
    return ia / (ia + ib)


def coherent(d_a, d_b) -> np.ndarray:
    d_a, d_b = np.asarray(d_a, float), np.asarray(d_b, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        over = 1.0 / d_a + 1.0 / d_b
    return np.isfinite(d_a) & np.isfinite(d_b) & (d_a > 1) & (d_b > 1) & (over >= C.OVERROUND_OK[0]) & \
        (over <= C.OVERROUND_OK[1])


def side_lines(o: pd.DataFrame, lines: pd.DataFrame, kind: str, paid: int) -> tuple[np.ndarray, ...]:
    g = lines[(lines["kind"] == kind) & (lines["paid"] == paid)].drop_duplicates(["eid", "partid"], keep="last")
    g = g.set_index(["eid", "partid"])
    ka, kb = list(zip(o["eid"], o["part_a"])), list(zip(o["eid"], o["part_b"]))
    pa, pb = g["pri"].reindex(ka).to_numpy(float), g["pri"].reindex(kb).to_numpy(float)
    ta, tb = g["tim_ms"].reindex(ka).to_numpy(float), g["tim_ms"].reindex(kb).to_numpy(float)
    return pa, pb, np.fmax(ta, tb)


def build() -> tuple[pd.DataFrame, dict]:
    lk = pd.read_parquet(C.LINK)
    ev = pd.read_parquet(C.OT_EVENTS, columns=["eid", "dt_ms", "home_partid", "away_partid"])
    o = lk.merge(ev, on="eid", how="left", validate="many_to_one")
    a_away = o["away_is_a"].to_numpy(bool)
    o["part_a"] = np.where(a_away, o["away_partid"], o["home_partid"])
    o["part_b"] = np.where(a_away, o["home_partid"], o["away_partid"])
    books = pd.read_parquet(C.OT_BOOKS, columns=["kind", "paid", "eid", "partid", "pri", "tim_ms"])
    books = books[books["eid"].isin(set(o["eid"]))]
    listed = o["dt_ms"].to_numpy(float)
    cols = {"match_id": o["match_id"].to_numpy(), "eid": o["eid"].to_numpy(), "t_listed_ms": listed}
    counts = {"linked": int(len(o)), "events_with_any_book_line": int(books["eid"].nunique())}
    for name, (kind, paid) in BOOKS.items():
        pa, pb, t = side_lines(o, books, kind, paid)
        after = (t - listed) / 60000.0
        ok = coherent(pa, pb)
        on_time = ok & ~(after > C.LATE_MIN)
        cols[f"{name}_a"], cols[f"{name}_b"] = np.where(on_time, pa, np.nan), np.where(on_time, pb, np.nan)
        cols[f"p_{name}"] = np.where(on_time, devig(pa, pb), np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            cols[f"over_{name}"] = np.where(on_time, 1.0 / pa + 1.0 / pb, np.nan)
        cols[f"after_{name}_min"] = after
        counts[name] = {"quoted": int((np.isfinite(pa) & np.isfinite(pb)).sum()), "coherent": int(ok.sum()),
                        "late_left_out": int((ok & (after > C.LATE_MIN)).sum()), "kept": int(on_time.sum())}
    out = pd.DataFrame(cols)
    # the BetOnline-only pull (lines.parquet) as a cross-check of the every-book pull's BetOnline line
    bl = pd.read_parquet(C.OT_LINES, columns=["kind", "book", "market", "eid", "partid", "pri", "tim_ms"])
    bl = bl[(bl["book"] == "BetOnline") & (bl["market"] == "match_winner") & bl["eid"].isin(set(o["eid"]))]
    bl = bl.rename(columns={"book": "paid"}).assign(paid=C.BETONLINE)
    xa, xb, _ = side_lines(o, bl, "last", C.BETONLINE)
    both = np.isfinite(out["bol_a"]) & np.isfinite(xa) & np.isfinite(xb)
    agree = both & np.isclose(out["bol_a"], xa) & np.isclose(out["bol_b"], xb)
    counts["betonline_cross_check"] = {"both_pulls_priced": int(both.sum()), "equal": int(agree.sum())}
    has_pin, has_bol = np.isfinite(out["p_pin"]), np.isfinite(out["p_bol"])
    out["p_close"] = np.where(has_pin, out["p_pin"], np.where(has_bol, out["p_bol"], np.nan))
    out["close_source"] = np.where(has_pin, "pinnacle", np.where(has_bol, "betonline", "none"))
    return out, counts


def main() -> int:
    out, counts = build()
    out.to_parquet(C.PRICES, index=False)
    lk = pd.read_parquet(C.LINK, columns=["match_id", "tour", "year", "kind"])
    j = lk.merge(out[["match_id", "close_source"]], on="match_id")
    counts["by_season"] = j.groupby(["tour", "kind", "year"])["close_source"].value_counts().unstack(fill_value=0) \
        .reset_index().to_dict("records")
    counts["books_lines_sha256"] = C.sha256_file(C.OT_BOOKS)
    C.write_json(C.OUT / "prices_counts.json", counts)
    C.log(f"prices: {counts}")
    print(j.pivot_table(index=["tour", "kind"], columns="year", values="close_source",
                        aggfunc=lambda s: round((s == "pinnacle").mean(), 2)).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
