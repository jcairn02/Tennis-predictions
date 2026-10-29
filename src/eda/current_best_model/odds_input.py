"""The current best model's odds input, "Pinnacle first" (the owner's decision of 9 Oct 2026:
docs/decisions/2026-10-09-pinnacle-first-odds-input.md, with its amendments of 21 Oct 2026).

The chain (model_rebuild/run_chain.py) builds the frame with the books' average close as the odds input. This step
replaces it, match by match, with the margin-free (proportional) chance of A from:
    1. Pinnacle's close:
       a. tennis-data's PSW/PSL (Stage 1) for matches up to 31 Jul 2025, cross-checked against OddsTrader's timed
          recording of Pinnacle (book 20). Where the two differ by more than 0.1 in log-odds and at least 3 other books
          price the match, the one nearer the other books' median; OddsTrader's where tennis-data has none (it runs to
          7 Sep 2025)
       b. since the rule of 21 Oct 2026 (RULE): TennisExplorer's time-stamped Pinnacle price, its last before the match
          (src/ingest/tennisexplorer.py), for matches played from 1 Nov 2025 (TE_FROM) where a. has none. Not used: a
          price the site shows without any time (most of Aug - Oct 2025); the site's own errors (22 Oct 2026), i.e. a
          Pinnacle row grossly apart from the median of the site's other books (3 in 2026), or a price grossly apart
          from both BetOnline's close and the books' average while those two agree (its page the wrong way round: 1 in
          2026). There BetOnline's close stays (te_left_out)
    2. BetOnline's closing line (OddsTrader's last line, book 8) where Pinnacle has none
    3. the books' average (the chain's own input) where neither book prices the match
Mirror images (RULE): the rule of 21 Oct 2026 reversed (the owner, 21 Oct 2026: "when OddsTrader and tennis-data are
mirror images, OddsTrader wins"). Where OddsTrader's Pinnacle (chosen by the reconciliation: the other books sided with
it) or BetOnline's close is the mirror image of tennis-data's books, tennis-data's row is the one with the two players'
prices swapped (all four such matches of the instance of 21 Oct 2026; every book on TennisExplorer sided with
OddsTrader), and OddsTrader's price stands. Under the earlier rule (RULE_BEFORE, the instances built to 21 Oct 2026) it
was the OddsTrader price that was left out. Only those two cases: a Pinnacle close the reconciliation took from
tennis-data stays (the 2021 US Open, where OddsTrader's recording of Pinnacle failed, has 18 lines that look like
mirrors), and a BetOnline mirror beside it is only listed.
OddsTrader's lines stamped more than 30 minutes after the listed start are left out (some are in-play prices). The
rules are the odds-sources study's (src/eda/odds_sources/: quality.drop_late, pools.reconciled), so the study and the
model use one implementation.

NOTE (the owner, 9 and 21 Oct 2026). Pinnacle's own closes are missing from 24 Jul 2025 (the day after Pinnacle closed
its public API; docs/research/pinnacle-gap/). From the next retrain after 21 Oct 2026 the model trains on TennisExplorer's
time-stamped Pinnacle closes from 1 Nov 2025 (RULE); Aug - Oct 2025 keep OddsTrader's Pinnacle (to 7 Sep) and BetOnline's
close. The owner asked for a test build compared with the current model and then deferred it ("DO NOT DO THE TEST YET",
21 Oct 2026): don't run it until the owner asks. Live, at every venue, the model is fed Pinnacle's current line with the
margin removed (BetOnline's while Pinnacle has none): unchanged.

    --apply <folder>            a built instance (the folder run_chain.py --collect wrote): OddsTrader's tables brought up
                                to date first (since 21 Oct 2026: a month listed again where its listing predates a
                                match's final line, the link rebuilt, the every-book pull for the events it lacks), and
                                (RULE) TennisExplorer's pages of the matches from 20 Oct 2025 (refresh: only pages not on
                                disk; the daily download keeps them current), restaged and linked to this frame
                                (te_pinnacle.parquet in the folder); --no-refresh skips both pulls. Then the per-source
                                table of its matches (odds_sources/table.py's build on its frame and Stage 1, which
                                refuses a frame those tables do not cover), then the frame rewritten. A month from
                                1 Nov 2025 with 50 or more matches of which under TE_MIN_SHARE take TennisExplorer's
                                Pinnacle stops the step before anything is rewritten (a broken feed must not fall back
                                to BetOnline unseen), unless --allow-low-te-coverage. odds_input.json records the refresh,
                                the rule, the swapped tennis-data rows, TennisExplorer's coverage by month and the
                                average's share month by month from August 2025
    --from-reference <folder>   a new instance from the frozen reference's frame and input list (the same matches and
                                inputs; only the odds input changes), with the odds-sources study's table of those matches
                                (it has no TennisExplorer columns: its matches from 1 Nov 2025 keep BetOnline's close)
    --rule 2026-10-09           the rule as built to 21 Oct 2026 (a reproduction of those instances)
The rewrite: in_odds_logit = the chance's log-odds, p_mkt = the chance (the frame's "closing price" for scoring),
odds_input = its source, p_mkt_avg = the books' average (the earlier input). A frame already rewritten is refused.
Also written: odds_input.json (counts by tour, season and source; the rule; the sources' SHA-256) and book_prices.parquet
(gitignored, as every parquet: the books' prices are not committed): per match, the decimal odds for A and B of the
Pinnacle close used (pin_source says whose) and of BetOnline's close, for backtests at either book.
Run: ./python.sh src/eda/current_best_model/odds_input.py --apply <folder> | --from-reference <folder>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.odds_sources import pools as P  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402
from src.eda.odds_sources import table as T  # noqa: E402
from src.ingest import oddstrader as OTI  # noqa: E402
from src.ingest import tennisexplorer as TEI  # noqa: E402

LIVE_STAGE1 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet"
K_TD, K_OT, K_TE, K_BOL, K_AVG = ("pinnacle (tennis-data)", "pinnacle (oddstrader)", "pinnacle (tennisexplorer)",
                                  "betonline", "average")
KINDS = (K_TD, K_OT, K_TE, K_BOL, K_AVG)
RULE = "2026-10-21"          # TennisExplorer's time-stamped Pinnacle from TE_FROM; OddsTrader wins a mirror image
RULE_BEFORE = "2026-10-09"   # as built to 21 Oct 2026: no TennisExplorer; a mirrored OddsTrader price left out
RULES = (RULE, RULE_BEFORE)
TE_FROM = "2025-11-01"       # the match day from which TennisExplorer's Pinnacle is used (the owner, 21 Oct 2026)
TE_LINK_SINCE = "2025-10-20"  # frame tournaments starting from here are linked (Paris 2025 began on 27 Oct)
TE_MIN_SHARE = 0.75          # a month from TE_FROM with TE_MIN_MATCHES or more matches priced below this stops the step
TE_MIN_MATCHES = 50
NOTE = ("Pinnacle's own closes are missing from 24 Jul 2025 (Pinnacle's public API closed on 23 Jul). From the rule of "
        "21 Oct 2026 the model trains on TennisExplorer's time-stamped Pinnacle closes from 1 Nov 2025, BetOnline's close "
        "where the site has none; Aug - Oct 2025 keep OddsTrader's Pinnacle (to 7 Sep) and BetOnline. When OddsTrader "
        "and tennis-data are mirror images, OddsTrader wins (tennis-data's row is the swapped one). The owner deferred "
        "the test build comparing it with the current model (21 Oct 2026). Live, at every venue: Pinnacle's current "
        "line with the margin removed, BetOnline's while Pinnacle has none.")


def _col(df: pd.DataFrame, name: str) -> np.ndarray:
    return df[name].to_numpy(float) if name in df.columns else np.full(len(df), np.nan)


def _apart(q: np.ndarray, p_avg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A price grossly apart from tennis-data's books (the odds study's "gross": over GROSS in log-odds and GROSS_PP in
    chance from them), and of those the ones within SWAP of their mirror image ("swapped")."""
    with np.errstate(divide="ignore", invalid="ignore"):
        za, z = np.log(p_avg / (1.0 - p_avg)), np.log(q / (1.0 - q))
        gross = np.isfinite(z) & np.isfinite(za) & (np.abs(z - za) > Q.GROSS) & (np.abs(q - p_avg) > Q.GROSS_PP)
        return gross, gross & (np.abs(z + za) < Q.SWAP)


def _gross_between(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        zp, zq = np.log(p / (1.0 - p)), np.log(q / (1.0 - q))
        return np.isfinite(zp) & np.isfinite(zq) & (np.abs(zp - zq) > Q.GROSS) & (np.abs(p - q) > Q.GROSS_PP)


def construct(sources: pd.DataFrame, rule: str = RULE) -> pd.DataFrame:
    """Per match: the Pinnacle-first chance of A, its source, and the decimal odds of the Pinnacle close used and of
    BetOnline's close. Reads no result. TennisExplorer's columns (tex_a, tex_b, tex_date, tex_timed) are optional."""
    if rule == RULE_BEFORE:
        return _construct_before(sources)
    if rule != RULE:
        raise ValueError(f"unknown rule {rule!r}: one of {RULES}")
    df = Q.drop_late(sources).reset_index(drop=True)
    p_pin, _, choice = P.reconciled(df, with_choice=True)
    p_bol, p_avg = df["p_ot8"].to_numpy(float), df["p_avg"].to_numpy(float)
    # The 21 Oct rule reversed (the owner, 21 Oct 2026: "when OddsTrader and tennis-data are mirror images, OddsTrader
    # wins"), in the two cases it acted on: OddsTrader's Pinnacle where the reconciliation chose it (the other books
    # sided with it) and BetOnline's close, each the mirror image of tennis-data's books, now stand (tennis-data's row is
    # the swapped one). Only those: where the Pinnacle used is tennis-data's own because the other books sided with it,
    # it stays (at the 2021 US Open OddsTrader's recording of Pinnacle failed, and 18 of its lines look like mirrors)
    pin_mirror = _apart(p_pin, p_avg)[1] & (choice == "oddstrader")
    bol_gross, bol_mirror = _apart(p_bol, p_avg)
    bol_gross = bol_gross & ~bol_mirror
    has_pin = np.isfinite(p_pin)
    swapped = pin_mirror | (bol_mirror & ~has_pin)
    listed = bol_mirror & has_pin & (choice == "tennis-data")   # beside tennis-data's own Pinnacle close: listed only
    # TennisExplorer's time-stamped Pinnacle, for matches played from TE_FROM (the owner, 21 Oct 2026)
    te_a, te_b = _col(df, "tex_a"), _col(df, "tex_b")
    timed = df["tex_timed"].eq(True).to_numpy() if "tex_timed" in df.columns else np.zeros(len(df), bool)
    te_day = pd.to_datetime(df["tex_date"]) if "tex_date" in df.columns else pd.Series(pd.NaT, index=df.index)
    p_raw = OC.devig(te_a, te_b)
    # The site's own errors (22 Oct 2026, on the gap's matches): its Pinnacle row far from its other books (3 in 2026),
    # or its whole page with the players' prices the wrong way round, found as the site against BetOnline's close and the
    # books' average when those two agree with each other (1 in 2026). Either way BetOnline's close stays.
    bz, bn, biqr = _col(df, "tex_books_z"), _col(df, "tex_books_n"), _col(df, "tex_books_iqr")
    with np.errstate(divide="ignore", invalid="ignore"):
        z_raw, p_books = np.log(p_raw / (1.0 - p_raw)), 1.0 / (1.0 + np.exp(-bz))
        off_books = (np.isfinite(bz) & (bn >= Q.MIN_REF) & (biqr < Q.AGREE)
                     & (np.abs(z_raw - bz) > Q.GROSS) & (np.abs(p_raw - p_books) > Q.GROSS_PP))
    off_both = _gross_between(p_raw, p_bol) & _gross_between(p_raw, p_avg) & ~_gross_between(p_bol, p_avg)
    te_out = off_books | off_both
    te_ok = OC.coherent(te_a, te_b) & timed & (te_day >= pd.Timestamp(TE_FROM)).to_numpy() & ~te_out
    p_te = np.where(te_ok, p_raw, np.nan)
    has_te = ~has_pin & te_ok
    swapped = swapped | (has_te & _apart(p_te, p_avg)[1])          # recorded only: the site's price stands anyway
    has_bol = np.isfinite(p_bol)
    p = np.where(has_pin, p_pin, np.where(has_te, p_te, np.where(has_bol, p_bol, p_avg)))
    td, ot = has_pin & (choice == "tennis-data"), has_pin & (choice == "oddstrader")
    kind = np.where(td, K_TD, np.where(ot, K_OT, np.where(has_te, K_TE, np.where(has_bol, K_BOL, K_AVG))))
    out = pd.DataFrame({
        "match_id": df["match_id"].astype(str).to_numpy(), "p_input": p, "odds_input": kind,
        "pin_a": np.where(td, df["ps_a"], np.where(ot, df["ot20_a"], np.where(has_te, te_a, np.nan))),
        "pin_b": np.where(td, df["ps_b"], np.where(ot, df["ot20_b"], np.where(has_te, te_b, np.nan))),
        "pin_source": np.where(td, "tennis-data", np.where(ot, "oddstrader", np.where(has_te, "tennisexplorer", ""))),
        "bol_a": df["ot8_a"].to_numpy(float), "bol_b": df["ot8_b"].to_numpy(float),
        "bol_after_listed_min": df["after_ot8_min"].to_numpy(float), "p_avg": p_avg,
        "tennis_data_swapped": swapped, "betonline_mirror_listed": listed, "oddstrader_mirror": np.zeros(len(df), bool),
        "bol_gross": bol_gross, "te_bol_gross": has_te & _gross_between(p_te, p_bol),
        "te_left_out": np.where(~has_pin & timed & off_books, "the site's Pinnacle far from its other books",
                                np.where(~has_pin & timed & off_both, "the site against BetOnline and the average", ""))})
    return _checked(out)


def _construct_before(sources: pd.DataFrame) -> pd.DataFrame:
    """RULE_BEFORE: the rule as built to 21 Oct 2026 (template_2026-10-21b), for reproductions."""
    df = Q.drop_late(sources).reset_index(drop=True)
    p_pin, _, choice = P.reconciled(df, with_choice=True)
    p_bol, p_avg = df["p_ot8"].to_numpy(float), df["p_avg"].to_numpy(float)
    has_pin, has_bol = np.isfinite(p_pin), np.isfinite(p_bol)
    # An OddsTrader price that is the mirror image of tennis-data's books was taken to come from an event linked with
    # its sides exchanged and left out (21 Oct 2026). A gross gap that is not a mirror is only listed (bol_gross).
    pin_mirror = _apart(p_pin, p_avg)[1] & (choice == "oddstrader")
    # a mirrored OddsTrader recording of Pinnacle hands the match back to tennis-data's, where that one is Pinnacle's
    faithful = (pd.to_datetime(df["td_date"]) <= P.PS_FAITHFUL_UNTIL).to_numpy()
    p_ps = np.where(faithful, df["p_ps"].to_numpy(float), np.nan)
    back = pin_mirror & np.isfinite(p_ps)
    p_pin, choice = np.where(back, p_ps, p_pin), np.where(back, "tennis-data", choice)
    bol_gross, bol_mirror = _apart(p_bol, p_avg)
    has_pin, has_bol = has_pin & ~(pin_mirror & ~back), has_bol & ~bol_mirror
    p = np.where(has_pin, p_pin, np.where(has_bol, p_bol, p_avg))
    kind = np.where(has_pin, np.where(choice == "oddstrader", K_OT, K_TD), np.where(has_bol, K_BOL, K_AVG))
    td, ot = has_pin & (choice == "tennis-data"), has_pin & (choice == "oddstrader")
    out = pd.DataFrame({
        "match_id": df["match_id"].astype(str).to_numpy(), "p_input": p, "odds_input": kind,
        "pin_a": np.where(td, df["ps_a"], np.where(ot, df["ot20_a"], np.nan)),
        "pin_b": np.where(td, df["ps_b"], np.where(ot, df["ot20_b"], np.nan)),
        "pin_source": np.where(td, "tennis-data", np.where(ot, "oddstrader", "")),
        "bol_a": np.where(bol_mirror, np.nan, df["ot8_a"].to_numpy(float)),
        "bol_b": np.where(bol_mirror, np.nan, df["ot8_b"].to_numpy(float)),
        "bol_after_listed_min": df["after_ot8_min"].to_numpy(float), "p_avg": p_avg,
        "tennis_data_swapped": np.zeros(len(df), bool), "betonline_mirror_listed": np.zeros(len(df), bool),
        "oddstrader_mirror": pin_mirror | bol_mirror, "bol_gross": bol_gross & ~bol_mirror,
        "te_bol_gross": np.zeros(len(df), bool), "te_left_out": np.full(len(df), "", dtype=object)})
    return _checked(out)


def _checked(out: pd.DataFrame) -> pd.DataFrame:
    if not np.isfinite(out["p_input"]).all():
        raise RuntimeError(f"{int((~np.isfinite(out['p_input'])).sum())} matches have no price at all")
    priced = out["pin_a"].notna()
    check = OC.devig(out.loc[priced, "pin_a"], out.loc[priced, "pin_b"])
    if not np.allclose(check, out.loc[priced, "p_input"], atol=1e-12):
        raise RuntimeError("the Pinnacle odds kept do not give the chance used")
    return out


def te_coverage(frame: pd.DataFrame, built: pd.DataFrame) -> dict:
    """TennisExplorer's share of the frame's matches by month (tournament date) from TE_FROM, and the months under
    TE_MIN_SHARE with TE_MIN_MATCHES or more matches."""
    f = frame[["match_id", "tournament_date"]].astype({"match_id": str}).merge(built[["match_id", "odds_input"]],
                                                                               on="match_id")
    f = f[pd.to_datetime(f["tournament_date"]) >= pd.Timestamp(TE_FROM)]
    month = pd.to_datetime(f["tournament_date"]).dt.strftime("%Y-%m")
    by = f.groupby(month).agg(matches=("match_id", "size"), tennisexplorer=("odds_input", lambda s: int((s == K_TE).sum())))
    by["share"] = (by["tennisexplorer"] / by["matches"]).round(4)
    low = by[(by["matches"] >= TE_MIN_MATCHES) & (by["share"] < TE_MIN_SHARE)]
    return {"by_month": {m: {k: (float(v) if k == "share" else int(v)) for k, v in r.items()} for m, r in by.iterrows()},
            "low_months": sorted(low.index), "min_share": TE_MIN_SHARE, "min_matches": TE_MIN_MATCHES}


def te_prices(folder: Path, stage1: Path, refresh_net: bool) -> tuple[pd.DataFrame, dict]:
    """TennisExplorer's Pinnacle for this frame's matches from TE_LINK_SINCE: the site's pages brought up to date
    (refresh_net), restaged, linked to the frame (te_pinnacle.parquet in the folder). Returns per match the decimal odds
    of A and B, the day, and whether the site shows the price with times."""
    since = dt.date.fromisoformat(TE_LINK_SINCE)
    desc: dict = {}
    if refresh_net:
        try:
            desc["refresh"] = TEI.refresh(since)
        except TEI.Stop as err:
            raise SystemExit(f"TennisExplorer's pull stopped ({err}): nothing was rewritten") from None
    players = stage1.parent / "stage0_match_players.parquet"
    players = players if players.exists() else TEI.STAGE0_PLAYERS
    link, how = TEI.link_frame(folder / "model_frame.parquet", since, players)
    link.to_parquet(folder / "te_pinnacle.parquet", index=False)
    desc.update({"link": how, "players": R.rel(players), "link_table": R.rel(folder / "te_pinnacle.parquet")})
    return te_columns(link), desc


def te_columns(link: pd.DataFrame) -> pd.DataFrame:
    """The adapter's link table (TEI.link_frame) as the per-source table's TennisExplorer columns (tex_*): Pinnacle's
    last decimal odds for A and B, the day, whether the site shows times, and the site's other books for A (their median
    log-odds, count and spread: the referee of the Pinnacle row)."""
    if link.empty or "pin_a" not in link.columns:
        return pd.DataFrame(columns=["match_id"])
    timed = link["pin_open_t"].notna() | (link["pin_n_moves"].fillna(0) > 0)
    col = lambda c: link[c] if c in link.columns else pd.Series(np.nan, index=link.index)  # noqa: E731
    return pd.DataFrame({"match_id": link["match_id"].astype(str), "tex_id": link["te_id"],
                         "tex_a": link["pin_a"].astype(float), "tex_b": link["pin_b"].astype(float),
                         "tex_date": link["te_date"], "tex_timed": timed.astype(bool), "tex_open_t": link["pin_open_t"],
                         "tex_last_t": link["pin_last_t"], "tex_moves": link["pin_n_moves"],
                         "tex_start_utc": link["start_utc"], "tex_books_z": col("books_z_a").astype(float),
                         "tex_books_n": col("books_n").astype(float), "tex_books_iqr": col("books_iqr").astype(float)})


def rewrite(folder: Path, built: pd.DataFrame, sources_desc: dict, rule: str = RULE, te_cov: dict | None = None) -> dict:
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
    # the fallback's share month by month in BetOnline's era, where a stale OddsTrader table shows first (21 Oct 2026)
    when = f["tournament_date"] if "tournament_date" in f.columns else pd.Series(pd.NaT, index=f.index)
    month = pd.to_datetime(when.astype(str), errors="coerce").dt.strftime("%Y-%m")
    era = month >= "2025-08"
    avg_share = (f.loc[era, "odds_input"] == K_AVG).groupby(month[era]).mean().round(4)
    flag = lambda col: sorted(b.index[b[col].fillna(False).astype(bool)].astype(str)) if col in b.columns else []  # noqa: E731
    record = {"decision": "docs/decisions/2026-10-09-pinnacle-first-odds-input.md", "note": NOTE,
              "rule": {"id": rule, "pinnacle_tennis_data_until": P.PS_FAITHFUL_UNTIL, "reconcile_log_odds": P.RECONCILE,
                       "min_other_books": P.MIN_REF, "late_line_minutes": Q.LATE_MIN,
                       "pinnacle_tennisexplorer_from": TE_FROM if rule == RULE else None,
                       "mirror_image": ("oddstrader wins: tennis-data's row is the swapped one" if rule == RULE else
                                        "the oddstrader price is left out"),
                       "order": ["pinnacle", "betonline", "average"]},
              "matches": int(len(f)),
              "by_source": {k: int((f["odds_input"] == k).sum()) for k in KINDS},
              "by_tour_season_source": {f"{t}|{s}|{k}": int(v) for (t, s, k), v in by.items()},
              "average_share_by_month_from_2025_08": {str(k): float(v) for k, v in avg_share.items()},
              # mirror images of tennis-data's books: under RULE tennis-data's row is taken as swapped and OddsTrader's
              # price stands; under RULE_BEFORE the OddsTrader price was left out
              "tennis_data_swapped": flag("tennis_data_swapped"),
              "betonline_mirrors_listed_where_pinnacle_decides": flag("betonline_mirror_listed"),
              "oddstrader_mirrors_left_out": flag("oddstrader_mirror"),
              "betonline_gross_listed": sorted(b.index[b["bol_gross"].astype(bool) & (b["odds_input"] == K_BOL)]
                                               .astype(str)),
              "tennisexplorer_gross_vs_betonline_listed": flag("te_bol_gross"),
              "tennisexplorer_left_out": ({m: r for m, r in b["te_left_out"].items() if r}
                                          if "te_left_out" in b.columns else {}),
              "tennisexplorer_coverage": te_cov,
              "frame_sha256": R.sha(path), **sources_desc}
    OC.write_json(folder / "odds_input.json", record)
    return record


def refresh(frame_path: Path, stage1: Path) -> dict:
    """OddsTrader's three tables brought up to date for this frame before it is priced (21 Oct 2026): each month whose
    listing predates a match's final line listed again, the link rebuilt, the every-book pull for the linked events
    it lacks. Here rather than in the callers: the builds of 13-21 Oct ran a copy of the steps without the last two,
    and their newest matches fell back to the books' average while BetOnline's closes were on disk."""
    f = T.frame_rows(frame_path, stage1)
    done = {"at": pd.Timestamp.now("UTC").isoformat(timespec="seconds")}
    months = T.stale_months(f)
    if months and OTI.pull_months(months) != 0:
        raise SystemExit(f"OddsTrader's monthly pull of {', '.join(months)} stopped (a block?): nothing was rewritten")
    done["months_listed_again"] = months
    if T.link() != 0:
        raise SystemExit("table.py --link failed: nothing was rewritten")
    if OTI.pull_books(pd.read_csv(OC.EIDS)["eid"].tolist()) != 0:
        raise SystemExit("OddsTrader's every-book pull stopped (a block?): nothing was rewritten")
    done["link"] = OC.read_json(OC.OUT / "link_counts.json")
    done["link"].pop("by_season", None)
    return done


def apply(folder: Path, stage1: Path = LIVE_STAGE1, refresh_tables: bool = True, rule: str = RULE,
          allow_low_te: bool = False) -> dict:
    """A built instance: OddsTrader's tables brought up to date (refresh) and, under RULE, TennisExplorer's pages and
    link (te_prices); its per-source table (which refuses a frame OddsTrader's tables do not cover: table.coverage);
    TennisExplorer's coverage checked; then the rewrite."""
    if "odds_input" in pq.read_schema(folder / "model_frame.parquet").names:
        raise SystemExit(f"{folder / 'model_frame.parquet'}: the odds input was already rewritten")
    fresh = refresh(folder / "model_frame.parquet", stage1) if refresh_tables else {"skipped": "--no-refresh"}
    out = folder / "odds_sources.parquet"
    T.build(frame_path=folder / "model_frame.parquet", stage1_path=stage1, out_path=out,
            counts_path=folder / "odds_sources_counts.json")
    sources = pd.read_parquet(out)
    desc: dict = {"sources_table": R.rel(out), "stage1": R.rel(stage1), "oddstrader_refresh": fresh}
    cov = None
    if rule == RULE:
        te, desc["tennisexplorer"] = te_prices(folder, stage1, refresh_tables)
        sources = sources.drop(columns=[c for c in sources.columns if c.startswith("tex_")]).merge(
            te, on="match_id", how="left")
        sources.to_parquet(out, index=False)        # the per-source table keeps TennisExplorer's columns
    built = construct(sources, rule)
    if rule == RULE:
        cov = te_coverage(pd.read_parquet(folder / "model_frame.parquet", columns=["match_id", "tournament_date"]),
                          built)
        if cov["low_months"] and not allow_low_te:
            raise SystemExit(f"TennisExplorer's Pinnacle prices fewer than {TE_MIN_SHARE:.0%} of the matches of "
                             f"{', '.join(cov['low_months'])} ({json.dumps({m: cov['by_month'][m] for m in cov['low_months']})}). "
                             "A broken feed would otherwise fall back to BetOnline unseen: nothing was rewritten. Look "
                             "at the site's pages (src/ingest/tennisexplorer.py), or rerun with --allow-low-te-coverage")
    return rewrite(folder, built, desc, rule, cov)


def from_reference(folder: Path, rule: str = RULE) -> dict:
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
    built = construct(sources, rule)
    return rewrite(folder, built, {"from_reference": R.rel(src / "model_frame.parquet"),
                                   "sources_table": R.rel(OC.SOURCES), "sources_table_frame": counts.get("frame")}, rule)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", type=Path, help="a built instance's folder")
    g.add_argument("--from-reference", type=Path, help="a new folder for an instance from the frozen reference")
    ap.add_argument("--stage1", type=Path, default=LIVE_STAGE1, help="Stage 1's odds table for --apply")
    ap.add_argument("--no-refresh", action="store_true",
                    help="--apply on OddsTrader's and TennisExplorer's tables as they are (a reproduction): a frame "
                         "OddsTrader's do not cover is still refused")
    ap.add_argument("--rule", choices=RULES, default=RULE,
                    help=f"{RULE} (default): TennisExplorer's Pinnacle from {TE_FROM}, OddsTrader wins a mirror image; "
                         f"{RULE_BEFORE}: the rule as built to 21 Oct 2026")
    ap.add_argument("--allow-low-te-coverage", action="store_true",
                    help=f"rewrite even where TennisExplorer prices under {TE_MIN_SHARE:.0%}% of a month's matches")
    a = ap.parse_args()
    folder = a.apply or a.from_reference
    folder = folder if folder.is_absolute() else ROOT / folder
    rec = apply(folder, a.stage1, refresh_tables=not a.no_refresh, rule=a.rule,
                allow_low_te=a.allow_low_te_coverage) if a.apply else from_reference(folder, a.rule)
    print(json.dumps({k: rec[k] for k in ("matches", "by_source")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
