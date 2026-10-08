"""Rebuild shortlisted histories on source-supported match dates only.

The archived event-start clock cannot establish result availability. This repair
uses accepted tennis-data match-day joins for BOTH history and targets. A result
becomes usable on the following date; strictly earlier rounds of the same event
may be used on the same date. There are no invented dates for undated matches.
This is a reduced history universe, not a reconstruction of the full database.

The existing history kernels work unchanged on this day axis. In particular IOS
snapshots must be rebuilt on these rows, never joined from the original cache.
Dates remain provider-reported days, not verified end times or quote timestamps.
"""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C
from src.eda.predictability_diagnostic import stage1_baselines as E
from src.eda.predictability_diagnostic import stage3_ratings as SR
from src.eda.predictability_diagnostic import stage4_features as F

OUT = ROOT / "data/studies/feature_alpha_audit/repairs"
DATE_COLUMNS = ["match_id", "td_date", "td_redated", "link", "round_agrees", "same_set_scores"]


def select_dated_matches(matches: pd.DataFrame, odds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Filter and order dates without consulting target labels or box values.

    Existing score agreement is identity-join evidence, not a model input. The
    plausibility window only rejects suspicious joins; it never supplies dates.
    Event identity includes original tour/id/start, even after replacing the time
    axis. A/B orientation and match_id are unchanged.
    """
    if matches.match_id.duplicated().any() or odds.match_id.duplicated().any():
        raise ValueError("Match/date evidence must have unique match_id")
    audit = matches[["match_id", "tour", "year", "level", "tournament_date"]].merge(
        odds[DATE_COLUMNS], on="match_id", how="left", validate="one_to_one")
    day = pd.to_datetime(audit.td_date, errors="coerce").dt.normalize()
    gap = (day - pd.to_datetime(audit.tournament_date)).dt.days
    reason = np.full(len(audit), "accepted", dtype=object)
    # First applicable reason wins, so missing dates are not called bad links.
    for mask, label in [
        (day.isna(), "no_match_day"),
        (~audit.link.isin(["name_pair", "one_player_anchor"]), "untrusted_identity_link"),
        (audit.td_redated.fillna(True).astype(bool), "date_was_reassigned"),
        (~audit.same_set_scores.fillna(False).astype(bool), "score_identity_not_confirmed"),
        (~audit.round_agrees.eq("yes"), "round_identity_not_confirmed"),
        (~gap.between(-7, 21), "implausible_event_date_gap"),
    ]:
        reason[(reason == "accepted") & np.asarray(mask)] = label
    audit["accepted"] = reason == "accepted"
    audit["reason"] = reason
    audit["match_date"] = day
    audit["event_date_gap_days"] = gap
    dated = audit.loc[audit.accepted, ["match_id", "match_date"]]
    m = matches.merge(dated, on="match_id", how="inner", validate="one_to_one")
    m["original_tournament_date"] = m.tournament_date
    m["original_tournament_id"] = m.tournament_id
    m["original_order"] = m.order
    m["original_year"] = m.year
    m["tournament_id"] = (m.tour.astype(str) + "|" + m.tournament_id.astype(str)
                          + "|event_start=" + m.tournament_date.astype(str))
    m["tournament_date"] = m.match_date
    m["year"] = m.match_date.dt.year
    m = m.sort_values(["match_date", "round_order", "tournament_id", "match_id"], kind="stable").reset_index(drop=True)
    m["order"] = np.arange(len(m))
    return m, audit


def build_rows(matches: pd.DataFrame, players: pd.DataFrame, odds: pd.DataFrame) -> pd.DataFrame:
    """Raw paired player rows; no original learned feature or rating is loaded."""
    if players.duplicated(["match_id", "side"]).any():
        raise ValueError("Duplicate player side within match")
    keep = players[players.match_id.isin(matches.match_id)].copy()
    # Match-level columns are authoritative when both files carry them.
    keep = keep.drop(columns=[c for c in keep if c != "match_id" and c in matches])
    rows = keep.merge(matches, on="match_id", how="inner", validate="many_to_one")
    rows = rows.sort_values(["order", "side"], kind="stable").reset_index(drop=True)
    if len(rows) != 2 * len(matches) or not rows.side.iloc[::2].eq("A").all() or not rows.side.iloc[1::2].eq("B").all():
        raise ValueError("Expected exactly A then B for every accepted match")
    if not np.array_equal(rows.match_id.iloc[::2], rows.match_id.iloc[1::2]):
        raise ValueError("Player pairs do not align")
    quotes = odds.set_index("match_id")
    rows["p_mkt_a"] = rows.match_id.map(quotes.p_avg_a).to_numpy()
    rows["box_stat_from"] = np.where(rows.tour.eq("wta"), C.WTA_BOX_FROM, C.EVAL_YEARS[0])
    # Stage 0's anatomy label can classify an entire event from a later score.
    # Preserve it for audit, but never let it decide earlier history eligibility.
    rows["observed_format"] = rows["format"]
    if "nonstandard_format" in rows:
        rows["observed_nonstandard_format"] = rows["nonstandard_format"]
    schedule_input = rows.assign(year=rows.original_year) if "original_year" in rows else rows
    schedule = F.scheduled_format(schedule_input)
    rows["history_format_supported"] = schedule.supported.to_numpy()
    rows["history_format_reason"] = schedule.reason.to_numpy()
    rows["format"] = schedule["format"].where(schedule.supported, "unknown").to_numpy()
    rows["nonstandard_format"] = ~rows.history_format_supported
    return F.prepare(rows)


def frozen_constants() -> tuple[dict, dict, dict]:
    elo = json.loads(E.SUMMARY.read_text(encoding="utf-8"))
    sr = json.loads(SR.SUMMARY.read_text(encoding="utf-8"))
    ek = {r["tour"]: r for r in elo["chosen"] if r["rule"] == "ret"}
    mu = {(r["tour"], r["surface"]): float(r["mu"]) for r in sr["surface_means"]}
    return ek, sr["chosen"], mu


def rebuild_ratings(rows: pd.DataFrame, elo_constants: dict | None = None,
                    sr_constants: dict | None = None, mu_constants: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Fresh Elo and S/R passes with frozen pre-2019 constants and day ordering."""
    if elo_constants is None or sr_constants is None or mu_constants is None:
        ek, sk, mus = frozen_constants()
        elo_constants = ek if elo_constants is None else elo_constants
        sr_constants = sk if sr_constants is None else sr_constants
        mu_constants = mus if mu_constants is None else mu_constants
    rows = rows.copy()
    a = rows.iloc[::2].copy().reset_index(drop=True)
    if not a.tournament_date.is_monotonic_increasing:
        raise ValueError("Repaired rows must be sorted by observed match date")
    elo = np.full((len(a), 8), np.nan)
    sr = np.full((len(a), 12), np.nan)
    p_elo = np.full(len(a), np.nan)
    mu = np.array([mu_constants.get((t, s), mu_constants[(t, "all")])
                   for t, s in zip(a.tour, a.surface)])
    na, wa = rows.spw_d.to_numpy()[::2], rows.spw_n.to_numpy()[::2]
    nb, wb = rows.spw_d.to_numpy()[1::2], rows.spw_n.to_numpy()[1::2]
    valid = np.isfinite(np.column_stack([na, wa, nb, wb])).all(axis=1)
    valid &= (na > 0) & (nb > 0) & (wa >= 0) & (wa <= na) & (wb >= 0) & (wb <= nb)
    update = valid & a.status.eq("completed").to_numpy() & a.history_format_supported.to_numpy(dtype=bool)
    for tour in sorted(set(a.tour)):
        ix = np.flatnonzero(a.tour.eq(tour).to_numpy())
        t = a.iloc[ix].reset_index(drop=True)
        h = F.elo_inputs(t)
        k = elo_constants[tour]
        elo[ix] = E.elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"],
                             t.status.isin(E.UPDATES["ret"]).tolist(), h["n_players"],
                             k["k0"], k["offset"], k["shape"])
        p_elo[ix] = E.blend(elo[ix], k["w"])
        s = sr_constants[tour]
        sr[ix] = SR.rating_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], mu[ix].tolist(),
                                update[ix].tolist(), na[ix].tolist(), wa[ix].tolist(), nb[ix].tolist(), wb[ix].tolist(),
                                h["n_players"], s["var_serve"], s["var_return"], s["drift"],
                                s.get("start_serve", 0.0), s.get("start_return", 0.0))
    pa, pb = SR.expected_serve(sr, mu)
    def own(x, y):
        return np.column_stack([x, y]).reshape(-1)
    rows["elo_own"] = own(elo[:, 0], elo[:, 1])
    rows["elo_surf_own"] = own(elo[:, 4], elo[:, 5])
    rows["serve_own"] = own(sr[:, 0], sr[:, 1])
    rows["return_own"] = own(sr[:, 2], sr[:, 3])
    rows["serve_opp"] = F.opp(rows.serve_own.to_numpy())
    rows["return_opp"] = F.opp(rows.return_own.to_numpy())
    rows["p_serve_own"] = own(pa, pb)
    rows["p_serve_opp"] = F.opp(rows.p_serve_own.to_numpy())
    rows["p_elo_a"] = np.repeat(p_elo, 2)
    rows["mu_logit"] = np.repeat(mu, 2)
    rows["rating_update"] = np.repeat(update, 2)
    ratings = a[["match_id", "tour", "year", "order", "tournament_id", "tournament_date",
                 "original_tournament_date", "match_date"]].copy()
    ratings["p_elo"] = p_elo
    ratings["p_serve_a"], ratings["p_serve_b"] = pa, pb
    ratings["updates"] = update
    for j, c in enumerate(["elo_a", "elo_b", "elo_n_a", "elo_n_b", "elo_surf_a", "elo_surf_b", "elo_surf_n_a", "elo_surf_n_b"]):
        ratings[c] = elo[:, j]
    for j, c in enumerate(["serve_a", "serve_b", "return_a", "return_b", "var_serve_a", "var_serve_b", "var_return_a", "var_return_b", "serve_pts_a", "serve_pts_b", "return_pts_a", "return_pts_b"]):
        ratings[c] = sr[:, j]
    return rows, ratings, {"elo_constants": elo_constants, "sr_constants": sr_constants,
                           "rating_updates": int(update.sum()), "all_matches": len(a)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Loading raw matches, players and local date provenance", flush=True)
    matches = C.load_matches()
    players = pd.read_parquet(C.MATCH_PLAYERS)
    odds = pd.read_parquet(E.ODDS)
    from src.eda.feature_alpha_audit.repair_data import repair_tables
    matches, players, data_audit = repair_tables(matches, players)
    matched, audit = select_dated_matches(matches, odds)
    print(f"Accepted {len(matched):,}/{len(matches):,} match days; building fresh rating histories", flush=True)
    rows = build_rows(matched, players, odds)
    rows, ratings, rating_meta = rebuild_ratings(rows)
    rows.to_parquet(OUT / "repair_rows.parquet", index=False, compression="zstd")
    ratings.to_parquet(OUT / "repair_matches.parquet", index=False, compression="zstd")
    audit.to_parquet(OUT / "repair_date_audit.parquet", index=False, compression="zstd")
    coverage = audit.groupby(["tour", "year", "level", "reason"], dropna=False).size().rename("matches").reset_index()
    coverage.to_csv(OUT / "repair_date_coverage.csv", index=False)
    summary = {
        "policy": "Accepted provider match-day joins for history and targets; earlier days + same-event strictly earlier rounds only",
        "availability": "End of prior date assumed available; no exact match-end or quote timestamp claim",
        "history_matches_original": len(matches), "history_matches_accepted": len(matched),
        "history_matches_excluded": len(matches) - len(matched),
        "date_reasons": audit.reason.value_counts().to_dict(),
        "frozen_constants_period": "2010-2018; used only as training era for subsequent predictive assessment",
        "data_repairs": data_audit, "ratings": rating_meta,
        "box_history_format": {
            "rule": "Outcome-independent scheduled edition metadata only; unsupported editions excluded from all box histories",
            "observed_format": "Stage 0 score-derived label preserved in observed_format for audit only",
            "unsupported_matches": int((~rows.history_format_supported.to_numpy()[::2]).sum()),
            "observed_label_differs_matches": int(rows['format'].iloc[::2].ne(rows.observed_format.iloc[::2]).sum()),
        },
        "inputs_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (C.MATCHES, C.MATCH_PLAYERS, E.ODDS)},
        "outputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (OUT / "repair_rows.parquet", OUT / "repair_matches.parquet")},
        "limitations": ["Restricted main-draw history loses undated lower-level history",
                        "Identity linkage uses retrospective source concordance",
                        "Historical periods already inspected; no untouched holdout created",
                        "Dates are provider-reported and cannot establish availability versus exact market quote time"],
    }
    (OUT / "repair_history_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ["history_matches_original", "history_matches_accepted", "date_reasons"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
