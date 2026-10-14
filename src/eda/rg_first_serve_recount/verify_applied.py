"""Was the Roland Garros candidate applied as confirmed? End-to-end checks of the built candidate. Reads no result.

Asked by the owner on 10 Oct 2026, after the harm check: "The next possiblity is that you fixed it incorrectly? how
likely is that?"

    V1 values       every confirmed row reads in the candidate's Stage 0 as its table gives it, on the right player:
                    the overrides (all nine counts), the exchanged boxes, the exchanged and the set service games, the
                    replaced first-serve splits (the reference's Stage 0 is the "before")
    V2 orientation  two checks that use none of this study's derivations:
                    (a) the match winner won more points than the loser (true in the large majority of completed
                        matches): the share in each corrected group, before and after, beside the Slams' other matches;
                    (b) service games agree with the row's own break points and the score (games won, tiebreaks apart =
                        service games - breaks conceded + breaks made): the share of completed matches passing, before
                        and after
    V3 timing       for each model input, by tour, the first event at which it changes (exactly, and by more than 1e-4
                    of its SD), beside the first event each kind of correction touches. Where a point-based input
                    moves before the tour's first point-level correction, the route is checked: boxes the fix rescued
                    (the reference had dropped them) as seeds; per-player inputs inside their light cone, inputs
                    solved jointly (IOS) only from the day the seeds' results count on the build's timeline
    V4 direction    the overridden Roland Garros rows of Sackmann (2022-2025): how often first serves in went down, and
                    each edition's pooled first-serve-in percentage before and after
    V5 box checks   Stage 0's cleaning log (rules B0-B9 and C25) at the Australian Open and Roland Garros, before and
                    after
Writes <out>/verify_applied/: v1_values.csv, v2_orientation.csv, v3_timing.csv, v4_direction.csv, v5_box_rules.csv and
summary.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/verify_applied.py
           --candidate-stage0 C:/Users/zerom/tnr_sb/data/studies/predictability_diagnostic
           --out data/studies/current_best_model/2026-10-09_rg_box_scores
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.rg_first_serve_recount.service_games import regular_games_won  # noqa: E402

REF_STAGE0 = (ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "tables" / "data"
              / "studies" / "predictability_diagnostic")
CANDIDATE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "confirmed" / "candidate"
DECIDED_OVERRIDES = ROOT / "data" / "studies" / "data_continuity" / "slam_box_overrides.csv"
DECIDED_CORRECTIONS = ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "row_corrections.csv"
COUNTS = {"ace": "ace", "df": "df", "svpt": "svpt", "1stIn": "first_in", "1stWon": "first_won", "2ndWon": "second_won",
          "SvGms": "sv_gms", "bpSaved": "bp_saved", "bpFaced": "bp_faced"}
SLAMS = ("Australian Open", "Roland Garros")


def stage0(folder: Path) -> pd.DataFrame:
    """One row per match: its keys and the winner's (w_) and loser's (l_) nine counts."""
    m = pd.read_parquet(folder / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "tournament_name", "tournament_date", "round",
                                 "status", "score", "box_status"])
    p = pd.read_parquet(folder / "stage0_match_players.parquet", columns=["match_id", "won", *COUNTS.values()])
    w = p[p["won"]].drop(columns="won").set_index("match_id").add_prefix("w_")
    lo = p[~p["won"]].drop(columns="won").set_index("match_id").add_prefix("l_")
    return m.set_index("match_id").join(w).join(lo)


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace("", np.nan), errors="coerce")


def new_rows(path: Path, decided: Path) -> pd.DataFrame:
    """The table's rows that the decided table lacks."""
    t, d = (pd.read_csv(p, dtype=str, keep_default_na=False) for p in (path, decided))
    cols = [c for c in d.columns if c in t.columns]
    j = t.merge(d[cols].drop_duplicates(), on=cols, how="left", indicator=True)
    return j[j["_merge"].eq("left_only")].drop(columns="_merge").reset_index(drop=True)


def same(a, b) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    return (a == b) | (np.isnan(a) & np.isnan(b))


def v1_values(ref: pd.DataFrame, cand: pd.DataFrame, ov: pd.DataFrame, rc: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def record(group, ids, field, expected, actual):
        ok = same(expected, actual)
        rows.append({"group": group, "field": field, "rows": int(len(ids)), "equal": int(ok.sum()),
                     "unequal": int((~ok).sum()), "first_unequal": ", ".join(list(np.asarray(ids)[~ok][:3]))})

    # the overrides: every count the row gives, on the side it names (C25: 0 service games with serve points = missing)
    ids = ov["stage0_match_id"].to_numpy()
    c = cand.reindex(ids)
    for src, col in COUNTS.items():
        for s in ("w", "l"):
            exp = num(ov[f"{s}_{src}"]).to_numpy(float)
            if col == "sv_gms":
                exp = np.where((exp == 0) & (num(ov[f"{s}_svpt"]).to_numpy(float) > 0), np.nan, exp)
            act = c[f"{s}_{col}"].to_numpy(float)
            given = ~np.isnan(exp)
            record("overrides (new)", ids[given], f"{s}_{col}", exp[given], act[given])
    for action, group in (("exchange_box", "exchanged boxes"), ("exchange_svgms", "exchanged service games"),
                          ("set_svgms", "set service games"), ("replace_split", "replaced splits")):
        t = rc[rc["action"].eq(action)]
        ids = t["match_id"].to_numpy()
        r_, c_ = ref.reindex(ids), cand.reindex(ids)
        if action == "exchange_box":
            for col in COUNTS.values():
                record(group, ids, f"w_{col}", r_[f"l_{col}"], c_[f"w_{col}"])
                record(group, ids, f"l_{col}", r_[f"w_{col}"], c_[f"l_{col}"])
        elif action == "exchange_svgms":
            record(group, ids, "w_sv_gms", r_["l_sv_gms"], c_["w_sv_gms"])
            record(group, ids, "l_sv_gms", r_["w_sv_gms"], c_["l_sv_gms"])
        elif action == "set_svgms":
            for s in ("w", "l"):
                record(group, ids, f"{s}_sv_gms", num(t[f"{s}_SvGms"]), c_[f"{s}_sv_gms"])
        else:
            for src in ("1stIn", "1stWon", "2ndWon", "ace", "df", "svpt"):
                for s in ("w", "l"):
                    exp = num(t[f"{s}_{src}"]).to_numpy(float)
                    given = ~np.isnan(exp)
                    record(group, ids[given], f"{s}_{COUNTS[src]}", exp[given], c_[f"{s}_{COUNTS[src]}"].to_numpy(float)[given])
    return pd.DataFrame(rows)


def points_won(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    w_sv = df["w_first_won"] + df["w_second_won"]
    l_sv = df["l_first_won"] + df["l_second_won"]
    return (w_sv + df["l_svpt"] - l_sv).to_numpy(float), (l_sv + df["w_svpt"] - w_sv).to_numpy(float)


def identity_ok(df: pd.DataFrame) -> np.ndarray:
    won = np.array([regular_games_won(s) for s in df["score"]], dtype=float).reshape(-1, 2)
    bw, bl = df["w_bp_faced"] - df["w_bp_saved"], df["l_bp_faced"] - df["l_bp_saved"]
    ok = ((df["w_sv_gms"] - bw + bl).to_numpy(float) == won[:, 0]) & ((df["l_sv_gms"] - bl + bw).to_numpy(float) == won[:, 1])
    return ok & (bw <= df["w_sv_gms"]).to_numpy() & (bl <= df["l_sv_gms"]).to_numpy()


def v2_orientation(ref: pd.DataFrame, cand: pd.DataFrame, groups: dict[str, np.ndarray]) -> pd.DataFrame:
    rows = []
    for name, ids in groups.items():
        for label, df in (("before", ref.reindex(ids)), ("after", cand.reindex(ids))):
            d = df[df["status"].eq("completed")]
            wp, lp = points_won(d)
            have = ~np.isnan(wp) & ~np.isnan(lp)
            have_sv = d[["w_sv_gms", "l_sv_gms", "w_bp_faced", "l_bp_faced", "w_bp_saved", "l_bp_saved"]].notna().all(axis=1).to_numpy()
            ok = identity_ok(d[have_sv]) if have_sv.any() else np.array([], bool)
            rows.append({"group": name, "stage0": label, "completed": int(len(d)),
                         "with_points": int(have.sum()), "winner_won_more_points": float((wp[have] > lp[have]).mean()) if have.any() else np.nan,
                         "with_service_games": int(have_sv.sum()),
                         "service_games_consistent": float(ok.mean()) if len(ok) else np.nan})
    return pd.DataFrame(rows)


def v3_timing(out: str, ref_s0: pd.DataFrame, kinds: dict[str, np.ndarray]) -> tuple[pd.DataFrame, pd.DataFrame]:
    _, p_cand, _ = CMP.candidate(out)
    ref, cand = CMP.inputs_frame(R.paths("reference")), CMP.inputs_frame(p_cand)
    cand = cand.reindex(ref.index)
    rows = []
    for col in [c for c in ref.columns if c.startswith("in_")]:
        a, b = pd.to_numeric(ref[col], errors="coerce"), pd.to_numeric(cand[col], errors="coerce")
        for tour in ("atp", "wta"):
            t = ref["tour"].eq(tour)
            sd = a[t].std()
            diff = (a - b).abs()
            moved = t & ((diff > 1e-12) | (a.isna() != b.isna()))
            material = t & ((diff > 1e-4 * sd) | (a.isna() != b.isna()))
            first = lambda m: (str(pd.to_datetime(ref.loc[m, "tournament_date"]).min().date()) if m.any() else "")
            rows.append({"input": col[3:], "tour": tour, "first_change": first(moved),
                         "first_material_change": first(material), "rows_changed": int(moved.sum())})
    first_kind = []
    for name, ids in kinds.items():
        k = ref_s0.reindex(ids)
        for tour in ("atp", "wta"):
            d = pd.to_datetime(k.loc[k["tour"].eq(tour), "tournament_date"])
            first_kind.append({"kind": name, "tour": tour, "matches": int(len(d)),
                               "first_event": str(d.min().date()) if len(d) else ""})
    return pd.DataFrame(rows), pd.DataFrame(first_kind)


def v3_light_cone(out: str, seeds: list[str], before: str, timing: Path, tour: str = "wta") -> pd.DataFrame:
    """A point-based input may change before the tour's first point-level correction only through boxes the fix
    rescued (seeds). Two routes, by kind of input:
        per player (each player's own matches, opponent-adjusted): the light cone, the seeds' players and every player
            who meets a player already in it, from the seeds on, at any level; every changed row must lie inside it;
        solved jointly (IOS and its products, on the leak-proof clock): any rating may move once the seeds' results
            count (lf + 1); no changed row may start (es) before that day."""
    _, p_cand, _ = CMP.candidate(out)
    ref, cand = CMP.inputs_frame(R.paths("reference")), CMP.inputs_frame(p_cand)
    cand = cand.reindex(ref.index)
    m = pd.read_parquet(REF_STAGE0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "order", "player_a_id", "player_b_id"]).set_index("match_id")
    t = m[m["tour"].eq(tour)].sort_values("order")
    rows = []
    if not seeds:
        return pd.DataFrame(rows)
    touched, in_cone = set(), {}
    for mid, r in t[t["order"] >= t.loc[seeds, "order"].min()].iterrows():
        a, b = r["player_a_id"], r["player_b_id"]
        in_cone[mid] = (a in touched) or (b in touched)     # a match reads its players' states before it
        if mid in seeds or in_cone[mid]:
            touched |= {a, b}
    day = pd.to_datetime(ref["tournament_date"])
    tm = pd.read_parquet(timing, columns=["match_id", "es", "lf"]).set_index("match_id")
    counts_from = float(tm.loc[seeds, "lf"].min()) + 1            # day numbers since 1970-01-01
    for col in ("in_ratings_iid", "in_adjperf_tpw_2w", "in_points_52w", "in_form_ace", "in_form_first_in",
                "in_iosO_ace", "in_iosD_ace", "in_ios_points_short", "in_prod_ace"):
        changed = ref.index[ref["tour"].eq(tour) & (day < before) & ((ref[col] - cand[col]).abs() > 1e-12)]
        joint = col.startswith(("in_ios", "in_prod"))
        if joint:
            inside = (tm["es"].reindex(changed) >= counts_from).to_numpy()
        else:
            inside = np.array([in_cone.get(i, False) for i in changed], dtype=bool)
        rows.append({"input": col[3:], "tour": tour, "before": before,
                     "route": "joint solve: starts on or after the seeds' results count" if joint else "light cone",
                     "rows_changed": int(len(changed)), "allowed": int(inside.sum()), "not_allowed": int((~inside).sum())})
    return pd.DataFrame(rows)


def v4_direction(ref: pd.DataFrame, cand: pd.DataFrame, ov_new: pd.DataFrame) -> pd.DataFrame:
    ids = ov_new.loc[ov_new["source"].eq("sackmann"), "stage0_match_id"].to_numpy()
    r_, c_ = ref.reindex(ids), cand.reindex(ids)
    rows = []
    for (tour, year), g in r_.groupby(["tour", "year"]):
        cg = c_.loc[g.index]
        before = pd.concat([g["w_first_in"], g["l_first_in"]]).to_numpy(float)
        after = pd.concat([cg["w_first_in"], cg["l_first_in"]]).to_numpy(float)
        sv_b = pd.concat([g["w_svpt"], g["l_svpt"]]).to_numpy(float)
        sv_a = pd.concat([cg["w_svpt"], cg["l_svpt"]]).to_numpy(float)
        both = ~np.isnan(before) & ~np.isnan(after)
        if not both.any():
            continue
        rows.append({"tour": tour, "year": int(year), "player_rows": int(both.sum()),
                     "first_in_down": int((after[both] < before[both]).sum()),
                     "first_in_up": int((after[both] > before[both]).sum()),
                     "first_in_same": int((after[both] == before[both]).sum()),
                     "pooled_first_in_pct_before": round(100 * np.nansum(before[both]) / np.nansum(sv_b[both]), 2),
                     "pooled_first_in_pct_after": round(100 * np.nansum(after[both]) / np.nansum(sv_a[both]), 2)})
    return pd.DataFrame(rows)


def v5_box_rules(cand_folder: Path) -> pd.DataFrame:
    out = []
    for label, folder in (("before", REF_STAGE0), ("after", cand_folder)):
        log = pd.read_csv(folder / "stage0_cleaning_log.csv")
        out.append(log.assign(stage0=label))
    log = pd.concat(out, ignore_index=True)
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate-stage0", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    folder = Path(a.out) / "verify_applied"
    folder.mkdir(parents=True, exist_ok=True)
    ref, cand = stage0(REF_STAGE0), stage0(Path(a.candidate_stage0))
    ov_new = new_rows(CANDIDATE / "slam_box_overrides.csv", DECIDED_OVERRIDES)
    rc_new = new_rows(CANDIDATE / "corrections" / "row_corrections.csv", DECIDED_CORRECTIONS)
    summary = {"new_override_rows": int(len(ov_new)), "new_correction_rows": rc_new["action"].value_counts().to_dict(),
               "reads_no_result": True}

    v1 = v1_values(ref, cand, ov_new, rc_new)
    v1.to_csv(folder / "v1_values.csv", index=False)
    summary["v1_unequal_by_group"] = v1.groupby("group")["unequal"].sum().to_dict()
    summary["v1_checked_by_group"] = v1.groupby("group")["rows"].sum().to_dict()
    # the service-game rows that do not read as expected, classified: a box the reference had dropped (a failed box
    # check, so its "before" is blank) that now passes the score check; or a partial box Stage 0 still drops
    expl = []
    for action, expected in (("exchange_svgms", None), ("set_svgms", "set")):
        t = rc_new[rc_new["action"].eq(action)].set_index("match_id")
        r_, c_ = ref.reindex(t.index), cand.reindex(t.index)
        if expected is None:
            ok = same(r_["l_sv_gms"], c_["w_sv_gms"]) & same(r_["w_sv_gms"], c_["l_sv_gms"])
        else:
            ok = same(num(t["w_SvGms"]), c_["w_sv_gms"]) & same(num(t["l_SvGms"]), c_["l_sv_gms"])
        for mid in t.index[~ok]:
            before, after = r_.loc[mid, "box_status"], c_.loc[mid, "box_status"]
            if before == "failed_check" and after == "full" and bool(identity_ok(c_.loc[[mid]])[0]):
                why = "rescued: the reference dropped the box (a failed box check); it now passes the score check"
            elif after == "partial":
                why = "partial box (other counts blank): Stage 0 still drops it; the set changes nothing yet"
            else:
                why = "UNEXPLAINED"
            expl.append({"action": action, "match_id": mid, "before": before, "after": after, "explanation": why})
    expl = pd.DataFrame(expl, columns=["action", "match_id", "before", "after", "explanation"])
    expl.to_csv(folder / "v1_unequal_explained.csv", index=False)
    summary["v1_unequal_explained"] = expl["explanation"].str.split(":").str[0].value_counts().to_dict()

    named = set(ov_new["stage0_match_id"]) | set(rc_new["match_id"])
    other = cand.index[cand["tournament_name"].isin(SLAMS) & cand["year"].between(2013, 2026)
                       & ~cand.index.isin(list(named))]
    wimbledon_uso = cand.index[cand["level"].eq("GS") & ~cand["tournament_name"].isin(SLAMS)
                               & cand["year"].between(2013, 2026)]
    groups = {"overrides (new)": ov_new["stage0_match_id"].to_numpy(),
              "exchanged boxes": rc_new.loc[rc_new["action"].eq("exchange_box"), "match_id"].to_numpy(),
              "replaced splits": rc_new.loc[rc_new["action"].eq("replace_split"), "match_id"].to_numpy(),
              "exchanged service games": rc_new.loc[rc_new["action"].eq("exchange_svgms"), "match_id"].to_numpy(),
              "set service games": rc_new.loc[rc_new["action"].eq("set_svgms"), "match_id"].to_numpy(),
              "AO and RG, not corrected": other.to_numpy(),
              "Wimbledon and US Open": wimbledon_uso.to_numpy()}
    v2 = v2_orientation(ref, cand, groups)
    v2.to_csv(folder / "v2_orientation.csv", index=False)

    v3, kinds = v3_timing(a.out, ref, {k: v for k, v in groups.items() if k not in ("AO and RG, not corrected",
                                                                                   "Wimbledon and US Open")})
    v3.to_csv(folder / "v3_timing.csv", index=False)
    kinds.to_csv(folder / "v3_first_correction.csv", index=False)
    # the women's first point-level correction (the exchanged boxes, the replaced splits, the overrides)
    point = kinds[kinds["kind"].isin(["overrides (new)", "exchanged boxes", "replaced splits"]) & kinds["tour"].eq("wta")
                  & kinds["first_event"].ne("")]
    first_point = min(point["first_event"]) if len(point) else "2100-01-01"
    rescued = expl[expl["explanation"].str.startswith("rescued")]["match_id"]
    seeds = [i for i in rescued if i.startswith("wta|")
             and str(pd.Timestamp(ref.loc[i, "tournament_date"]).date()) < first_point]
    timing = Path(a.candidate_stage0).parent / "match_timing" / "timing.parquet"   # the build's own timeline
    cone = v3_light_cone(a.out, seeds, first_point, timing)
    cone.to_csv(folder / "v3_light_cone.csv", index=False)
    summary["v3_light_cone"] = {"seeds": seeds, "before": first_point, "timing": str(timing),
                                "not_allowed": int(cone["not_allowed"].sum()) if len(cone) else 0}

    v4 = v4_direction(ref, cand, ov_new)
    v4.to_csv(folder / "v4_direction.csv", index=False)

    v5 = v5_box_rules(Path(a.candidate_stage0))
    v5.to_csv(folder / "v5_box_rules.csv", index=False)
    piv = v5.groupby(["rule_id", "rule", "stage0"])["count"].sum().unstack("stage0").fillna(0).astype(int)
    piv["change"] = piv.get("after", 0) - piv.get("before", 0)
    piv = piv[piv["change"] != 0].reset_index()
    piv.to_csv(folder / "v5_rules_changed.csv", index=False)
    checks = piv[piv["rule"].str.startswith("box score check")]
    summary["v5_box_checks_failing_change"] = int(checks["change"].sum())
    summary["v5_box_checks_worse"] = checks.loc[checks["change"] > 0, "rule_id"].tolist()
    (folder / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")

    with pd.option_context("display.width", 250, "display.max_rows", 400, "display.max_columns", 30):
        print(json.dumps(summary, indent=1, default=str))
        print("\nV1 values (unequal rows by group and field, nonzero only):")
        print(v1[v1["unequal"] > 0].to_string(index=False) if (v1["unequal"] > 0).any() else "  none")
        print("\nV2 orientation:"); print(v2.round(4).to_string(index=False))
        print("\nV3 first correction by kind:"); print(kinds.to_string(index=False))
        print("\nV3 first change by input (changed inputs):"); print(v3[v3["rows_changed"] > 0].to_string(index=False))
        print("\nV1 rows that do not read as expected, explained:"); print(expl.to_string(index=False))
        print("\nV3 light cone:"); print(cone.to_string(index=False))
        print("\nV4 direction:"); print(v4.to_string(index=False))
        print("\nV5 Stage 0 rules whose counts changed:"); print(piv[["rule_id", "before", "after", "change", "rule"]]
                                                                .to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
