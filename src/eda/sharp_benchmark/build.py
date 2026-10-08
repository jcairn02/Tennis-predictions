"""Sharp benchmark for 2026, step 1: tour-level matches with every sharp price the project holds.

Three venues, all from data already downloaded:
  * Pinnacle (PSW/PSL) and Betfair Exchange (BFEW/BFEL) closing odds in the tennis-data.co.uk season files of
    2025 and 2026, staged under data/dump/odds/tennis_data_couk/ (downloaded from the relaunched live site on
    5 Oct 2026). Bet365 (B365W/L) and OddsPortal's market average (AvgW/AvgL) come along as yardsticks. In
    these files Pinnacle stops on 13-14 Jan 2026 and Betfair runs from 17 Aug 2025 to late September 2026.
  * Polymarket: the outcome-0 price of every singles match-winner market at fixed times before its scheduled
    start, from the minute-level price history (data/dump/odds/polymarket/price_history/). The price at each
    horizon is the last point before the cut-off, if no older than an hour; at horizon 0 that is the closing
    price of src/eda/polymarket_sharp_money/prematch.py.

tennis-data names are "Surname I." and Polymarket's are full names, so a Polymarket market links to a
tennis-data row when one "surname span + first initial" form of each of its players (scan.py's td_variants)
gives the row's winner > loser pair, on the same tour, with the scheduled start from 3 days before to 2 days
after the row's match day. The nearest day wins; then a market with a closing price, then the most traded.
Each row takes one market and each market one row (a tie between rows leaves the market out). Which outcome
is the row's winner comes from the outcome labels, and Polymarket's own settlement checks it.

Odds of 0 or 1.00 are not quotes, and a pair whose overround lies outside 1.00-1.20 is not a coherent quote
(src/eda/predictability_diagnostic/stage1_odds.py). A row dated outside its file's season takes the file's
year (the archived WTA 2026 file had one row written as 2029).

Writes, in data/studies/sharp_benchmark/:
    matches.parquet      one row per tennis-data row of 2025 and 2026: result, every book's odds and whether
                         they are coherent, and the linked Polymarket market with the winner's price at each
                         horizon (pw_pm_m<minutes>)
    pm_markets.parquet   one row per Polymarket singles match-winner market: players, level, settlement,
                         scheduled start, outcome-0 price at each horizon, and its tennis-data row if linked
    link_summary.json    rows, quotes, links by season, tour, level and month, unlinked markets, settlement
                         agreement and price coverage

Usage:
    ./python.sh src/eda/sharp_benchmark/build.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.polymarket_sharp_money import build_positions as B  # noqa: E402

TD = ROOT / "data" / "dump" / "odds" / "tennis_data_couk"
PM = ROOT / "data" / "dump" / "odds" / "polymarket"
OUT = ROOT / "data" / "studies" / "sharp_benchmark"
SEASONS = (2025, 2026)
BOOKS = {"ps": ("PSW", "PSL"), "bfe": ("BFEW", "BFEL"), "b365": ("B365W", "B365L"), "avg": ("AvgW", "AvgL")}
OVERROUND_OK = (1.0, 1.2)
LEVELS = {"grand_slam": "GS", "masters_1000": "T1000", "wta1000": "T1000", "atp500": "T500", "wta500": "T500",
          "atp250": "T250", "wta250": "T250", "masters_cup": "FIN", "tour_championships": "FIN"}
WINDOW = (-3, 2)                                  # Polymarket's start day minus tennis-data's match day
HORIZONS = (2880, 1440, 720, 360, 180, 60, 30, 10, 0)   # minutes before the scheduled start
MAX_AGE = 3600                                    # seconds; a price must be from the hour before its cut-off
MAIN_TYPES = ("slam_atp", "slam_wta", "finals", "t1000_atp", "t1000_wta", "t500_atp", "t500_wta", "t250_atp",
              "t250_wta")


# --------------------------------------------------------------------------------------
# tennis-data.co.uk
# --------------------------------------------------------------------------------------
def outside_season(date: pd.Series, season: pd.Series) -> pd.Series:
    """More than a month before the file's season starts, or after it ends (stage1_odds.py's rule)."""
    start = pd.to_datetime(season.astype(str) + "-01-01") - pd.Timedelta(days=31)
    end = pd.to_datetime(season.astype(str) + "-12-31")
    return (date < start) | (date > end)


def clean_odds(td: pd.DataFrame) -> pd.DataFrame:
    """Odds as numbers with 0 and 1.00 missing; each book's overround and whether its pair is coherent."""
    for pair in BOOKS.values():
        for c in pair:
            v = pd.to_numeric(td[c], errors="coerce")
            td[c] = v.where(v > 1.0)
    for book, (w, l) in BOOKS.items():
        s = 1.0 / td[w] + 1.0 / td[l]
        td[f"overround_{book}"] = s
        td[f"ok_{book}"] = td[w].notna() & td[l].notna() & s.between(*OVERROUND_OK)
    return td


def load_td() -> pd.DataFrame:
    frames = []
    for season in SEASONS:
        for f in sorted(TD.glob(f"*/*/{season}.parquet")):
            df = pd.read_parquet(f)
            frames.append(pd.DataFrame({
                "tour": f.parts[-3], "season": season, "level_label": df["Series"] if "Series" in df else df["Tier"],
                "level": LEVELS.get(f.parts[-2], f.parts[-2]), "td_file": df["_source_file"],
                "td_row": df["_row"].astype(int), "date_text": df["Date"], "tournament": df["Tournament"],
                "round": df["Round"], "surface": df["Surface"], "best_of": df["Best of"], "winner": df["Winner"],
                "loser": df["Loser"], "comment": df["Comment"],
                **{c: (df[c] if c in df else None) for pair in BOOKS.values() for c in pair}}))
    td = pd.concat(frames, ignore_index=True)
    td["td_id"] = td.tour + "-" + td.season.astype(str) + "-" + td.td_row.map("{:05d}".format)
    td["date"] = pd.to_datetime(td.date_text, errors="coerce")
    td["redated"] = outside_season(td.date, td.season)
    td.loc[td.redated, "date"] = [d.replace(year=int(y)) for d, y in zip(td.loc[td.redated, "date"],
                                                                         td.loc[td.redated, "season"])]
    td["wk"], td["lk"] = td.winner.map(S.td_key), td.loser.map(S.td_key)
    return clean_odds(td)


# --------------------------------------------------------------------------------------
# Polymarket
# --------------------------------------------------------------------------------------
def load_markets() -> pd.DataFrame:
    """Every singles match-winner market in the staged index, with its players, the study event type of the
    sharp-money study (build_positions.event_type), settlement and scheduled start."""
    events = pd.read_parquet(PM / "event_index.parquet",
                             columns=["id", "title", "league", "sport_date", "bucket_slug", "bucket_tour"])
    markets = pd.read_parquet(PM / "market_index.parquet",
                              columns=["question", "conditionId", "sportsMarketType", "event_id", "closed", "outcomes",
                                       "outcomePrices", "gameStartTime", "volumeNum"])
    markets = markets[(markets.sportsMarketType == "moneyline") & markets.conditionId.notna()]
    df = markets.drop_duplicates("conditionId").merge(
        events.drop_duplicates("id", keep="last").rename(columns={"id": "event_id"}), on="event_id", how="left")
    text = df.question.fillna(df.title).fillna("")
    parts = text.str.split(r"\s+vs\.?\s+", regex=True)
    keep = ~text.str.contains("/", regex=False) & ~text.str.contains(" & ", regex=False) & (parts.str.len() == 2)
    df, parts = df[keep].copy(), parts[keep]
    df["name_a"] = parts.str[0].str.rsplit(":", n=1).str[-1].str.strip()
    df["name_b"] = parts.str[1].str.strip()
    df["league"] = df.league.fillna(df.title.map(lambda t: t.split(":")[0].strip() if isinstance(t, str) else None))
    df["event_type"] = [B.event_type(b, t, lg) for b, t, lg in zip(df.bucket_slug, df.bucket_tour, df.league)]
    status = [B.settlement(x) if c == "True" else ("unresolved", None) for x, c in zip(df.outcomePrices, df.closed)]
    df["status"], df["y0"] = [s for s, _ in status], [y for _, y in status]
    start = pd.to_datetime(df.gameStartTime, utc=True, errors="coerce")
    df["start_ts"] = (start - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    day = start.fillna(pd.to_datetime(df.sport_date, utc=True, errors="coerce"))
    df["day"] = day.dt.tz_convert(None).dt.normalize()
    df["tour"] = df.bucket_tour.map({"ATP": "atp", "WTA": "wta"})
    df["volume"] = pd.to_numeric(df.volumeNum, errors="coerce")
    df["outcome_list"] = df.outcomes.map(S.parse_list)
    df = df.rename(columns={"conditionId": "condition_id"})
    return df[["condition_id", "event_id", "title", "league", "bucket_slug", "event_type", "tour", "name_a", "name_b",
               "outcome_list", "sport_date", "day", "start_ts", "status", "y0", "volume"]].reset_index(drop=True)


def horizon_prices(start: pd.Series, horizons=HORIZONS) -> pd.DataFrame:
    """Outcome-0 price at each horizon (minutes before the scheduled start): the last minute-level point before
    start - horizon, if it is no older than MAX_AGE. `start` maps condition_id -> scheduled start (epoch s).
    Also the time of the closing point and of the market's first point."""
    found, first = [], []
    for path in sorted((PM / "price_history").glob("*/*.parquet")):
        ph = pd.read_parquet(path, columns=["condition_id", "t", "p"])
        ph = ph[ph.condition_id.isin(start.index)]
        if ph.empty:
            continue
        first.append(ph.groupby("condition_id").t.min())
        st, t = ph.condition_id.map(start).to_numpy(), ph.t.to_numpy()
        for h in horizons:
            cut = st - 60 * h
            sel = ph[(t < cut) & (t >= cut - MAX_AGE)]
            if len(sel):
                found.append(sel.sort_values("t").groupby("condition_id").tail(1).assign(h=h))
    points = pd.concat(found).sort_values("t").groupby(["condition_id", "h"]).tail(1)
    wide = points.pivot(index="condition_id", columns="h", values="p")
    wide = wide.reindex(columns=list(horizons)).rename(columns=lambda h: f"p0_m{h}")
    wide["close_t"] = points[points.h == 0].set_index("condition_id").t
    wide["first_t"] = pd.concat(first).groupby(level=0).min()
    return wide


# --------------------------------------------------------------------------------------
# linking
# --------------------------------------------------------------------------------------
def candidate_pairs(pm: pd.DataFrame) -> pd.DataFrame:
    """Every winner > loser pair, in tennis-data's 'surname span + first initial' form, that a Polymarket market
    could appear as; a_won says whether its first-named player would be the winner. A pair a market gives in
    both directions (two players with the same surname and initial) cannot say who won and is dropped."""
    out = []
    for a_won, (first, second) in ((True, ("name_a", "name_b")), (False, ("name_b", "name_a"))):
        x = pm[["condition_id", "tour", "day"]].assign(wv=pm[first].map(S.td_variants),
                                                       lv=pm[second].map(S.td_variants), a_won=a_won)
        x = x.explode("wv").explode("lv")
        out.append(x.assign(pair=x.wv + ">" + x.lv).drop(columns=["wv", "lv"]))
    cand = pd.concat(out, ignore_index=True).drop_duplicates(["condition_id", "pair", "a_won"])
    both = cand.groupby(["condition_id", "pair"]).a_won.transform("size") > 1
    return cand[~both].reset_index(drop=True)


def link(td: pd.DataFrame, pm: pd.DataFrame, window=WINDOW) -> pd.DataFrame:
    """One market per tennis-data row and one row per market. td needs td_id, tour, date, wk, lk; pm needs
    condition_id, tour (atp, wta or missing), day, name_a, name_b, has_close, volume.
    Returns td_id, condition_id, a_won, gap (Polymarket's day minus tennis-data's, in days)."""
    rows = td.loc[(td.wk != "") & (td.lk != ""), ["td_id", "tour", "date", "wk", "lk"]]
    rows = rows.assign(pair=rows.wk + ">" + rows.lk).drop(columns=["wk", "lk"])
    m = rows.merge(candidate_pairs(pm), on="pair", suffixes=("", "_pm"))
    m = m[m.tour_pm.isna() | (m.tour_pm == m.tour)]
    m = m.assign(gap=(m.day - m.date).dt.days)
    m = m[m.gap.between(*window)].drop_duplicates(["td_id", "condition_id"])
    m = m.merge(pm[["condition_id", "has_close", "volume"]], on="condition_id", how="left")
    m = m.assign(abs_gap=m.gap.abs()).sort_values(["abs_gap", "has_close", "volume"], ascending=[True, False, False])
    best = m.groupby("td_id", sort=False).head(1)
    best = best[best.abs_gap == best.groupby("condition_id").abs_gap.transform("min")]
    tie = best.groupby("condition_id").td_id.transform("size") > 1
    return best[~tie][["td_id", "condition_id", "a_won", "gap"]].reset_index(drop=True)


def outcome_index(name: str, outcomes: list) -> int | None:
    """The outcome whose label names this player: every word of the label is in the full name, and only one
    label qualifies."""
    words = set(S.norm(name).split())
    hits = [k for k, o in enumerate(outcomes) if S.norm(o) and set(S.norm(o).split()) <= words]
    return hits[0] if len(hits) == 1 else None


def first_player_outcome(name_a: str, name_b: str, outcomes: list) -> tuple[int, str]:
    """Outcome index of the first-named player, and how it was found."""
    if len(outcomes) != 2:
        return 0, "title order"
    ia, ib = outcome_index(name_a, outcomes), outcome_index(name_b, outcomes)
    if ia is not None and ib is not None and ia != ib:
        return ia, "both labels"
    if ia is not None and ib is None:
        return ia, "first label"
    if ib is not None and ia is None:
        return 1 - ib, "second label"
    return 0, "title order"


# --------------------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------------------
def counts(frame: pd.DataFrame, by: list[str], linked: pd.Series) -> list[dict]:
    g = frame.assign(linked=linked.to_numpy()).groupby(by, observed=True)
    out = g.agg(rows=("linked", "size"), linked=("linked", "sum")).reset_index()
    out["share"] = (out.linked / out.rows).round(4)
    return json.loads(out.to_json(orient="records", date_format="iso"))


def summarise(td: pd.DataFrame, pm: pd.DataFrame, matches: pd.DataFrame) -> dict:
    out = {"generated": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
           "rules": {"overround_ok": list(OVERROUND_OK), "window_days": list(WINDOW), "horizons_min": list(HORIZONS),
                     "max_price_age_s": MAX_AGE},
           "tennis_data": {"rows": int(len(td)), "redated": int(td.redated.sum()),
                           "by_file": counts(td, ["tour", "season"], td[[f"ok_{b}" for b in BOOKS]].any(axis=1)),
                           "comments": td.groupby(["season", "comment"]).size().rename("rows").reset_index()
                           .to_dict(orient="records")}}
    quotes = {}
    for book, (w, l) in BOOKS.items():
        have = td[w].notna() & td[l].notna()
        x = td.assign(have=have, ok=td[f"ok_{book}"], quoted_date=td.date.where(have),
                      ok_overround=td[f"overround_{book}"].where(td[f"ok_{book}"]))
        q = x.groupby(["tour", "season"]).agg(rows=("ok", "size"), quoted=("have", "sum"), coherent=("ok", "sum"),
                                               first=("quoted_date", "min"), last=("quoted_date", "max"),
                                               overround_median=("ok_overround", "median"))
        quotes[book] = json.loads(q.reset_index().to_json(orient="records", date_format="iso"))
    out["quotes"] = quotes
    era = matches.date >= pm.loc[pm.event_type.isin(MAIN_TYPES), "day"].min()
    linked = matches.condition_id.notna()
    out["links"] = {
        "polymarket_era_starts": str(matches.loc[era, "date"].min().date()),
        "rows_in_era": int(era.sum()), "linked": int((era & linked).sum()),
        "by_tour_season": counts(matches[era], ["tour", "season"], linked[era]),
        "by_level": counts(matches[era], ["level"], linked[era]),
        "by_month": counts(matches[era].assign(month=matches.date.dt.strftime("%Y-%m")), ["month"], linked[era]),
        "orientation_basis": matches.loc[linked, "pm_orientation"].value_counts().to_dict(),
        "gap_days": matches.loc[linked, "link_gap"].value_counts().sort_index().to_dict()}
    done = linked & matches.pm_status.eq("decisive")
    out["settlement_check"] = {
        "decisive_linked": int(done.sum()),
        "agree_by_comment": matches[done].groupby("comment").pm_settle_agree.agg(["size", "sum"])
        .rename(columns={"size": "rows", "sum": "agree"}).reset_index().to_dict(orient="records"),
        "void_linked_by_comment": matches[linked & matches.pm_status.eq("void")].comment.value_counts().to_dict(),
        "disagreements": matches[done & ~matches.pm_settle_agree.astype(bool)][
            ["td_id", "date", "tournament", "winner", "loser", "comment", "pm_title"]].astype(str).to_dict(orient="records")}
    window = pm.event_type.isin(MAIN_TYPES) & pm.day.between(td.date.min() - pd.Timedelta(days=3),
                                                             td.date.max() + pd.Timedelta(days=3))
    pm_linked = pm.condition_id.isin(matches.condition_id.dropna())
    out["polymarket_main_tour_markets"] = {
        "in_tennis_data_dates": int(window.sum()), "linked": int((window & pm_linked).sum()),
        "by_event_type": counts(pm[window], ["event_type"], pm_linked[window]),
        "unlinked_examples": pm[window & ~pm_linked].sort_values("day").head(40)[["day", "title", "status"]]
        .astype(str).to_dict(orient="records")}
    out["price_coverage"] = {f"m{h}": int(pm[f"p0_m{h}"].notna().sum()) for h in HORIZONS}
    out["price_coverage"]["markets"] = int(len(pm))
    out["price_coverage"]["linked_with_close"] = int(matches.pw_pm_m0.notna().sum())
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    td = load_td()
    pm = load_markets()
    timed = pm[pm.start_ts.notna()]
    prices = horizon_prices(timed.set_index("condition_id").start_ts)
    pm = pm.merge(prices, left_on="condition_id", right_index=True, how="left")
    pm["has_close"] = pm.p0_m0.notna()
    links = link(td, pm)

    # orientation: which outcome is the tennis-data winner, and Polymarket's own verdict
    lk = links.merge(pm, on="condition_id", how="left")
    basis = [first_player_outcome(a, b, o) for a, b, o in zip(lk.name_a, lk.name_b, lk.outcome_list)]
    ia = np.array([k for k, _ in basis])
    lk["pm_orientation"] = [why for _, why in basis]
    lk["winner_outcome"] = np.where(lk.a_won, ia, 1 - ia)
    pm_winner = np.where(lk.y0 == 1.0, 0, np.where(lk.y0 == 0.0, 1, -1))
    lk["pm_settle_agree"] = np.where(pm_winner >= 0, pm_winner == lk.winner_outcome, np.nan)
    for h in HORIZONS:
        p0 = lk[f"p0_m{h}"]
        lk[f"pw_pm_m{h}"] = np.where(lk.winner_outcome == 0, p0, 1.0 - p0)
    keep = (["td_id", "condition_id", "gap", "pm_orientation", "winner_outcome", "pm_settle_agree", "event_type",
             "title", "status", "volume", "start_ts", "close_t", "first_t"] + [f"pw_pm_m{h}" for h in HORIZONS])
    lk = lk[keep].rename(columns={"gap": "link_gap", "event_type": "pm_event_type", "title": "pm_title",
                                  "status": "pm_status", "volume": "pm_volume", "start_ts": "pm_start_ts",
                                  "close_t": "pm_close_t", "first_t": "pm_first_t"})
    matches = td.drop(columns=["wk", "lk"]).merge(lk, on="td_id", how="left")
    pm = pm.merge(links[["condition_id", "td_id"]], on="condition_id", how="left")

    matches.to_parquet(OUT / "matches.parquet", index=False)
    pm.drop(columns=["outcome_list"]).assign(outcomes=pm.outcome_list.map(json.dumps)).to_parquet(
        OUT / "pm_markets.parquet", index=False)
    summary = summarise(td, pm, matches)
    (OUT / "link_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("links", "price_coverage")}, indent=1, default=str)[:4000])
    print("settlement:", json.dumps(summary["settlement_check"]["agree_by_comment"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
