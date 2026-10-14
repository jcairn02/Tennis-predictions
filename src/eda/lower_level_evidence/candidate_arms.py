"""The role-08 candidate's arms and gates (lower-level evidence): translating a lower-level match's contribution to the
17 one-step forms and to points_52w. The plan, fixed before any result: data/studies/lower_level_evidence/candidates/
preregistration.md.

    --low-share   low_share_diff for every frame match: A's share minus B's of the previous 365 days' played matches
                  below the main tour (event_levels/blend.history, unchanged, on the frozen reference's Stage 0; the
                  result column is replaced by a constant before the call, so no outcome is read), checked against
                  event_levels' universe_columns.parquet on the matches both hold   -> candidates/low_share.parquet
    --gates       G1 (FP's frame against the frozen frame), G2 (invariance where no lower-level box score can reach an
                  input), G3 (direction against the share difference)                -> candidates/checks/g1..g3
    --build       the arms F, P, FP_placebo, R_L, FP_L from the reference's and FP's frames (pyarrow: the label column
                  passes through unread), and R_S2 (the dated addition of 9 Oct)     -> candidates/<arm>/
    --half        FP_half from the linearity gate's outputs (g4_linearity.py)        -> candidates/FP_half/

No outcome is read except a_won of seasons <= 2024 in G1 (a filtered read, to check the labels are the reference's).
Run: ./python.sh src/eda/lower_level_evidence/candidate_arms.py --low-share | --gates | --build | --half
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.lower_level_evidence import translate_hooks as H  # noqa: E402

CAND = LC.OUT / "candidates"
CHECKS = CAND / "checks"
OFFSETS = CAND / "offsets"
REF_FRAME, REF_INPUTS = LC.FRAME, LC.INPUTS
SIDES = LC.OUT / "composition" / "reference_2026-10-08" / "sides.parquet"
LOW_SHARE = CAND / "low_share.parquet"
UNIVERSE = ROOT / "data" / "studies" / "event_levels" / "universe_columns.parquet"
FORMS = [H.input_name(s, ch) for s, ch in H.FORM_SPECS]            # the 17
TRANSLATED = FORMS + ["points_52w"]                                 # the 18
ID_COLS = ["match_id", "tour", "season", "tournament_date", "p_mkt", "tabpfn_split", "debut_season"]
LOWER = list(LC.LOWER)
ALL_BUCKETS = list(LC.BUCKETS)
PLACEBO_SEED = 20261009
NEW = "low_share_diff"
F32_ULPS = 2


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o) if np.isfinite(o) else None
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return str(o)
    path.write_text(json.dumps(obj, indent=1, default=default), encoding="utf-8")


def inputs_of(path: Path) -> pd.DataFrame:
    """A frame's identifiers and inputs, without the result column."""
    cols = [c for c in pq.read_schema(path).names if c != "a_won"]
    f = pd.read_parquet(path, columns=cols)
    f["match_id"] = f["match_id"].astype(str)
    return f


def labels_through_2024(path: Path) -> pd.Series:
    f = pd.read_parquet(path, columns=["match_id", "season", "a_won"], filters=[("season", "<=", 2024)])
    if len(f) and f["season"].max() > 2024:
        raise RuntimeError("a result after 2024 was read")
    return pd.Series(f["a_won"].to_numpy(), index=f["match_id"].astype(str).to_numpy())


# ------------------------------------------------------------------------------------------------
# low_share_diff

def low_share() -> int:
    from src.eda.event_levels import blend as BL
    from src.eda.event_levels import common as EC
    m = pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "map_level", "tournament_id", "tournament_name",
                                 "tournament_date", "round_order", "status", "player_a_id", "player_b_id", "has_box",
                                 "order", "surface"])
    m["tier"] = m["map_level"].map(EC.TIER_OF)
    m["date"] = pd.to_datetime(m["tournament_date"])
    p = pd.read_parquet(LC.STAGE0_DIR / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "opponent_id", "side", "rank", "entry", "has_box"])
    p["won"] = False                       # blend.history counts wins too; a constant keeps every outcome unread
    p = p.merge(m[["match_id", "tour", "year", "map_level", "tier", "date", "order", "status", "tournament_id"]],
                on="match_id", how="left", validate="many_to_one")
    frame = inputs_of(REF_FRAME)[["match_id", "season", "tour"]]
    h = BL.history(m, p, years=(EC.TRAIN_FROM, 2026), levels=EC.MAIN, match_ids=frame["match_id"])
    a = h[h["side"] == "A"].set_index("match_id")
    b = h[h["side"] == "B"].set_index("match_id")
    ids = pd.Index(frame["match_id"])
    found = ids.isin(a.index) & ids.isin(b.index)
    if not found.all() or a.index.duplicated().any() or b.index.duplicated().any():
        raise RuntimeError(f"{int((~found).sum())} frame matches lack a side")
    sides = m.set_index("match_id").reindex(ids)
    out = pd.DataFrame({"match_id": ids, "season": frame["season"].to_numpy(), "tour": frame["tour"].to_numpy(),
                        "player_a_id": sides["player_a_id"].to_numpy(), "player_b_id": sides["player_b_id"].to_numpy(),
                        "low_share_a": a["low_share"].reindex(ids).to_numpy(float),
                        "low_share_b": b["low_share"].reindex(ids).to_numpy(float),
                        "n_all_a": a["n_all"].reindex(ids).to_numpy(), "n_all_b": b["n_all"].reindex(ids).to_numpy()})
    out["low_share_diff"] = out["low_share_a"] - out["low_share_b"]
    checks = {"frame_matches": int(len(ids)), "found_both_sides": int(found.sum()),
              "side_a_is_stage0_player_a": bool((a["player_id"].reindex(ids).to_numpy() == out["player_a_id"].to_numpy()).all()),
              "shares_in_0_1": bool(np.nanmin(out[["low_share_a", "low_share_b"]].to_numpy()) >= 0
                                    and np.nanmax(out[["low_share_a", "low_share_b"]].to_numpy()) <= 1),
              "missing_diff": int(out["low_share_diff"].isna().sum()),
              "coverage_by_season": {int(s): float(np.isfinite(g.to_numpy()).mean())
                                     for s, g in out.groupby("season")["low_share_diff"]}}
    # sides.parquet (role 02) names the same player on each side
    sp = pd.read_parquet(SIDES, columns=["match_id", "side", "player_id"])
    spa = sp[sp["side"] == "A"].set_index("match_id")["player_id"].reindex(ids)
    checks["sides_parquet_side_a_agrees"] = bool((spa.to_numpy() == out["player_a_id"].to_numpy()).all())
    # event_levels' column (the 30 Sep snapshot, 63,737 matches) on the matches both hold
    u = pd.read_parquet(UNIVERSE).set_index("match_id")
    common = ids.intersection(u.index)
    o = out.set_index("match_id").loc[common]
    uu = u.loc[common]
    same_a = (o["player_a_id"].to_numpy() == uu["player_a_id"].to_numpy())
    va, vb = o["low_share_diff"].to_numpy(float), uu["low_share_diff"].to_numpy(float)
    eq = (np.isnan(va) & np.isnan(vb)) | (va == vb)
    diff = pd.DataFrame({"match_id": common, "season": o["season"].to_numpy(), "ours": va, "event_levels": vb,
                         "same_side_a": same_a})[~eq]
    checks["event_levels"] = {"matches_both_hold": int(len(common)), "equal": int(eq.sum()),
                              "different": int((~eq).sum()), "side_a_differs": int((~same_a).sum()),
                              "largest_abs_difference": float(np.nanmax(np.abs(va - vb))) if len(common) else None,
                              "frame_matches_not_in_event_levels": int(len(ids) - len(common))}
    CHECKS.mkdir(parents=True, exist_ok=True)
    diff.to_csv(CHECKS / "low_share_vs_event_levels_differences.csv", index=False)
    out.to_parquet(LOW_SHARE, index=False)
    checks["file_sha256"] = sha256(LOW_SHARE)
    write_json(CHECKS / "low_share_check.json", {"what": "low_share_diff for the 67,226 frame matches (blend.history "
                                                        "on the frozen Stage 0; outcomes replaced by a constant)",
                                                 **checks})
    print(json.dumps({k: v for k, v in checks.items() if k != "coverage_by_season"}, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------
# Gates

def max_gap(a: np.ndarray, b: np.ndarray) -> tuple[float, bool, int]:
    a, b = np.asarray(a, float), np.asarray(b, float)
    same_nan = bool(np.array_equal(np.isnan(a), np.isnan(b)))
    both = np.isfinite(a) & np.isfinite(b)
    gap = float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0
    changed = int(((np.abs(a - b) > 0) & both).sum() + (np.isnan(a) != np.isnan(b)).sum())
    return gap, same_nan, changed


def side_shares(window: str) -> pd.DataFrame:
    """Per frame match: A's and B's lower-level share of box-score evidence in the window, and both counts."""
    cols = [f"box_{window}_{b}" for b in ALL_BUCKETS]
    s = pd.read_parquet(SIDES, columns=["match_id", "side"] + cols)
    tot = s[cols].sum(axis=1).to_numpy(float)
    low = s[[f"box_{window}_{b}" for b in LOWER]].sum(axis=1).to_numpy(float)
    s["share"] = np.where(tot > 0, low / np.where(tot > 0, tot, 1.0), np.nan)
    s["low"] = low
    s["tot"] = tot
    a = s[s["side"] == "A"].set_index("match_id")
    b = s[s["side"] == "B"].set_index("match_id")
    return pd.DataFrame({"share_a": a["share"], "share_b": b["share"].reindex(a.index), "low_a": a["low"],
                         "low_b": b["low"].reindex(a.index), "tot_a": a["tot"], "tot_b": b["tot"].reindex(a.index)})


def g1(ref: pd.DataFrame, cand: pd.DataFrame, cand_path: Path) -> dict:
    out = {"what": "FP's frame against the frozen reference frame", "rows_reference": int(len(ref)),
           "rows_candidate": int(len(cand))}
    out["same_ids_in_order"] = bool(len(ref) == len(cand) and (ref["match_id"].to_numpy() == cand["match_id"].to_numpy()).all())
    if not out["same_ids_in_order"]:
        out["pass"] = False
        return out
    ids = {}
    for c in ID_COLS[1:]:
        x, y = ref[c], cand[c]
        ids[c] = bool(x.equals(y)) if x.dtype == y.dtype else bool((x.astype(str) == y.astype(str)).all())
    la, lb = labels_through_2024(REF_FRAME), labels_through_2024(cand_path)
    ids["a_won_seasons_to_2024"] = bool(la.index.equals(lb.index) and (la.to_numpy() == lb.to_numpy()).all())
    out["identifiers_equal"] = ids
    rows = []
    inputs_ref = [c[3:] for c in ref.columns if c.startswith("in_")]
    inputs_cand = [c[3:] for c in cand.columns if c.startswith("in_")]
    out["same_input_columns"] = inputs_ref == inputs_cand
    for n in inputs_ref:
        gap, same_nan, changed = max_gap(ref[f"in_{n}"].to_numpy(), cand[f"in_{n}"].to_numpy())
        rows.append({"input": n, "translated": n in TRANSLATED, "largest_difference": gap, "same_missing": same_nan,
                     "rows_changed": changed, "rows": int(len(ref))})
    t = pd.DataFrame(rows)
    t.to_csv(CHECKS / "g1_inputs.csv", index=False)
    other = t[~t["translated"]]
    tr = t[t["translated"]]
    out["untranslated_inputs"] = int(len(other))
    out["untranslated_identical"] = bool(((other["largest_difference"] == 0) & other["same_missing"]).all())
    out["untranslated_differing"] = other.loc[(other["largest_difference"] > 0) | ~other["same_missing"],
                                              "input"].tolist()
    out["translated_inputs"] = int(len(tr))
    out["translated_all_changed"] = bool((tr["rows_changed"] > 0).all())
    out["translated_same_missing"] = bool(tr["same_missing"].all())
    ri = json.loads(REF_INPUTS.read_text(encoding="utf-8"))
    ci = json.loads((cand_path.parent / "model_inputs.json").read_text(encoding="utf-8"))
    out["model_inputs_names_kinds_equal"] = [(d["name"], d["kind"]) for d in ri["inputs"]] == \
        [(d["name"], d["kind"]) for d in ci["inputs"]]
    out["pass"] = bool(out["same_ids_in_order"] and all(ids.values()) and out["same_input_columns"]
                       and out["untranslated_identical"] and out["translated_all_changed"]
                       and out["translated_same_missing"] and out["model_inputs_names_kinds_equal"]
                       and len(tr) == 18)
    return out


def g2(ref: pd.DataFrame, cand: pd.DataFrame) -> dict:
    ids = ref["match_id"].to_numpy()
    car = side_shares("career").reindex(ids)
    y365 = side_shares("365d").reindex(ids)
    none_career = ((car["low_a"] == 0) & (car["low_b"] == 0)).to_numpy()
    none_365 = ((y365["low_a"] == 0) & (y365["low_b"] == 0)).to_numpy()
    out = {"what": "inputs that no lower-level box score can reach must not move",
           "forms": {"matches_without_lower_box_scores_career": int(none_career.sum()), "inputs": {}},
           "points_52w": {"matches_without_lower_box_scores_365d": int(none_365.sum())}}
    ok_forms = True
    for n in FORMS:
        a, b = ref[f"in_{n}"].to_numpy(float)[none_career], cand[f"in_{n}"].to_numpy(float)[none_career]
        gap, same_nan, changed = max_gap(a, b)
        out["forms"]["inputs"][n] = {"largest_difference": gap, "same_missing": same_nan, "rows_changed": changed}
        ok_forms &= gap == 0 and same_nan
    a, b = ref["in_points_52w"].to_numpy(float)[none_365], cand["in_points_52w"].to_numpy(float)[none_365]
    gap, same_nan, changed = max_gap(a, b)
    both = np.isfinite(a) & np.isfinite(b)
    ulp = np.spacing(np.abs(a[both]).astype(np.float32)).astype(float)
    within = np.abs(a[both] - b[both]) <= F32_ULPS * ulp
    out["points_52w"].update({"largest_difference": gap, "same_missing": same_nan, "rows_changed": changed,
                              "exact_zeros": int((a[both] == b[both]).sum()), "rows_compared": int(both.sum()),
                              "within_2_float32_ulps": bool(within.all())})
    out["forms"]["pass"] = bool(ok_forms)
    out["points_52w"]["pass"] = bool(same_nan and within.all())
    out["pass"] = bool(ok_forms and out["points_52w"]["pass"])
    return out


def evidence_weights() -> dict:
    """Per tour: the summed two-week effective box-score counts of each lower bucket over the frame's player rows."""
    s = pd.read_parquet(SIDES, columns=["tour"] + [f"box_h2w_{b}" for b in LOWER])
    return {t: {b: float(g[f"box_h2w_{b}"].sum()) for b in LOWER} for t, g in s.groupby("tour")}


def g3(ref: pd.DataFrame, cand: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    ids = ref["match_id"].to_numpy()
    tour = ref["tour"].to_numpy()
    sh = {"h2w": side_shares("h2w").reindex(ids), "365d": side_shares("365d").reindex(ids)}
    offs = pd.read_csv(OFFSETS / "forms_offsets.csv")
    w = evidence_weights()
    rows = []
    for n in TRANSLATED:
        win = "365d" if n == "points_52w" else "h2w"
        ds = (sh[win]["share_a"] - sh[win]["share_b"]).to_numpy(float)
        d = cand[f"in_{n}"].to_numpy(float) - ref[f"in_{n}"].to_numpy(float)
        for t in ("atp", "wta"):
            m = (tour == t) & np.isfinite(d) & np.isfinite(ds)
            corr = float(np.corrcoef(d[m], ds[m])[0, 1]) if m.sum() > 2 and np.std(d[m]) > 0 else np.nan
            slope = float(np.polyfit(ds[m], d[m], 1)[0]) if m.sum() > 2 else np.nan
            if n == "points_52w":
                dbar, expected = np.nan, -1
                required = True
            else:
                key = [k for k in offs["key"].unique() if H.input_name(k.split("|")[1], k.split("|")[0]) == n][0]
                o = offs[(offs["key"] == key) & (offs["tour"] == t)].set_index("bucket")["value_used"]
                dbar = float(sum(o[b] * w[t][b] for b in LOWER) / sum(w[t].values()))
                expected = -int(np.sign(dbar)) if dbar != 0 else 0
                required = abs(dbar) >= 0.05
            sign_ok = (np.sign(corr) == expected) if np.isfinite(corr) and expected != 0 else None
            rows.append({"input": n, "tour": t, "window": win, "matches": int(m.sum()), "correlation": corr,
                         "slope_change_on_share_diff": slope, "evidence_weighted_offset": dbar,
                         "expected_sign": expected, "sign_as_expected": sign_ok, "required": required,
                         "median_abs_change_sd": float(np.median(np.abs(d[m])) / np.nanstd(ref[f"in_{n}"].to_numpy(float)[tour == t]))
                         if m.any() else np.nan})
    t3 = pd.DataFrame(rows)
    req = t3[t3["required"]]
    out = {"what": "the translated inputs' change against the two players' lower-level share difference",
           "required_cells": int(len(req)), "required_as_expected": int(req["sign_as_expected"].fillna(False).sum()),
           "failed": req.loc[~req["sign_as_expected"].fillna(False).astype(bool), ["input", "tour", "correlation",
                                                                                     "evidence_weighted_offset"]].to_dict("records"),
           "pass": bool(req["sign_as_expected"].fillna(False).all())}
    return out, t3


def gates() -> int:
    cand_path = CAND / "FP" / "model_frame.parquet"
    ref, cand = inputs_of(REF_FRAME), inputs_of(cand_path)
    CHECKS.mkdir(parents=True, exist_ok=True)
    r1 = g1(ref, cand, cand_path)
    r1["candidate_frame_sha256"] = sha256(cand_path)
    write_json(CHECKS / "g1_reproduction.json", r1)
    print("G1", {k: r1[k] for k in ("pass", "untranslated_identical", "untranslated_differing", "translated_all_changed",
                                    "translated_same_missing", "identifiers_equal") if k in r1})
    if not r1.get("same_ids_in_order"):
        return 1
    r2 = g2(ref, cand)
    write_json(CHECKS / "g2_invariance.json", r2)
    print("G2", {"pass": r2["pass"], "forms": r2["forms"]["pass"], "points": r2["points_52w"]})
    r3, t3 = g3(ref, cand)
    t3.to_csv(CHECKS / "g3_direction.csv", index=False)
    write_json(CHECKS / "g3_direction.json", r3)
    with pd.option_context("display.width", 220, "display.max_rows", 60):
        print(t3.round(4).to_string(index=False))
    print("G3", {k: r3[k] for k in ("pass", "required_cells", "required_as_expected", "failed")})
    return 0 if (r1["pass"] and r2["pass"] and r3["pass"]) else 1


# ------------------------------------------------------------------------------------------------
# Arms

def table_without(path: Path) -> pa.Table:
    return pq.read_table(path)


def replace(table: pa.Table, name: str, values: np.ndarray) -> pa.Table:
    i = table.schema.get_field_index(name)
    if i < 0:
        return table.append_column(pa.field(name, pa.float64()), pa.array(np.asarray(values, float)))
    return table.set_column(i, pa.field(name, pa.float64()), pa.array(np.asarray(values, float)))


def write_arm(arm: str, table: pa.Table, inputs: dict, what: str, record: dict) -> None:
    d = CAND / arm
    d.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, d / "model_frame.parquet")
    meta = copy.deepcopy(inputs)
    meta["arm"] = {"name": arm, "what": what, "built_by": "src/eda/lower_level_evidence/candidate_arms.py",
                   "preregistration": "data/studies/lower_level_evidence/candidates/preregistration.md"}
    write_json(d / "model_inputs.json", meta)
    record[arm] = {"what": what, "frame_sha256": sha256(d / "model_frame.parquet"),
                   "inputs": [x["name"] for x in meta["inputs"]].__len__()}
    print(f"{arm}: {what}")


def with_low_share(inputs: dict) -> dict:
    meta = copy.deepcopy(inputs)
    if NEW in [d["name"] for d in meta["inputs"]]:
        return meta
    meta["inputs"].append({"name": NEW, "kind": "diff",
                           "source": "event-levels experiment C1's input: A's share minus B's of the previous 365 days' "
                                     "played matches below the main tour (blend.history on the frozen reference's Stage "
                                     "0; src/eda/lower_level_evidence/candidate_arms.py --low-share)"})
    return meta


SHARE_INPUTS = {"box_low_share_h2w_diff": "h2w", "box_low_share_365d_diff": "365d"}   # R_S2 (dated addition, 9 Oct)


def share_inputs(ids: np.ndarray) -> dict:
    """R_S2's two inputs: A's minus B's lower-level share of box-score evidence (TQ + GSQ + CH + CHQ + ITF + ITFQ over all
    8 buckets) in the two-week-half-life window and over 365 days (sides.parquet, role 02; counts only); missing when a
    side has no box-score evidence in the window."""
    out = {}
    for name, win in SHARE_INPUTS.items():
        sh = side_shares(win).reindex(ids)
        out[name] = (sh["share_a"] - sh["share_b"]).to_numpy(float)
    return out


def with_shares(inputs: dict) -> dict:
    meta = copy.deepcopy(inputs)
    for name, win in SHARE_INPUTS.items():
        if name not in [d["name"] for d in meta["inputs"]]:
            meta["inputs"].append({"name": name, "kind": "diff",
                                   "source": f"A's minus B's lower-level share of box-score evidence, window {win} "
                                             f"(sides.parquet of role 02, box channel); the R_S2 control, the dated "
                                             f"addition of 9 Oct 2026 to the pre-registration"})
    return meta


def placebo_delta(ref: pd.DataFrame, fp: pd.DataFrame) -> tuple[dict, np.ndarray]:
    """FP's per-match change vector over the 18 inputs, permuted across matches within tour x season."""
    rng = np.random.default_rng(PLACEBO_SEED)
    perm = np.arange(len(ref))
    keys = ref[["tour", "season"]].astype({"season": int})
    for (t, s), g in keys.groupby(["tour", "season"], sort=True):
        idx = g.index.to_numpy()
        perm[idx] = idx[rng.permutation(len(idx))]
    out = {}
    for n in TRANSLATED:
        d = np.nan_to_num(fp[f"in_{n}"].to_numpy(float) - ref[f"in_{n}"].to_numpy(float), nan=0.0)
        out[n] = ref[f"in_{n}"].to_numpy(float) + d[perm]          # a missing reference value stays missing
    return out, perm


def build() -> int:
    fp_path = CAND / "FP" / "model_frame.parquet"
    g1r = json.loads((CHECKS / "g1_reproduction.json").read_text(encoding="utf-8"))
    if not g1r.get("pass"):
        raise SystemExit("G1 has not passed: no arm is built")
    ref, fp = inputs_of(REF_FRAME), inputs_of(fp_path)
    if not (ref["match_id"].to_numpy() == fp["match_id"].to_numpy()).all():
        raise SystemExit("FP's frame is not in the reference's order")
    inputs = json.loads(REF_INPUTS.read_text(encoding="utf-8"))
    ls = pd.read_parquet(LOW_SHARE).set_index("match_id")["low_share_diff"].reindex(ref["match_id"]).to_numpy(float)
    record = {}
    t_ref = table_without(REF_FRAME)
    t = t_ref
    for n in FORMS:
        t = replace(t, f"in_{n}", fp[f"in_{n}"].to_numpy(float))
    write_arm("F", t, inputs, "the reference frame with FP's 17 forms", record)
    write_arm("P", replace(t_ref, "in_points_52w", fp["in_points_52w"].to_numpy(float)), inputs,
              "the reference frame with FP's points_52w", record)
    pl, perm = placebo_delta(ref, fp)
    t = t_ref
    for n in TRANSLATED:
        t = replace(t, f"in_{n}", pl[n])
    write_arm("FP_placebo", t, inputs, f"the reference plus FP's per-match change vector permuted within tour x "
                                       f"season (default_rng({PLACEBO_SEED}))", record)
    np.save(CAND / "FP_placebo" / "permutation.npy", perm)
    write_arm("R_L", replace(t_ref, f"in_{NEW}", ls), with_low_share(inputs),
              "the reference plus low_share_diff as a 59th input", record)
    t_fp = pq.read_table(fp_path)
    fp_inputs = json.loads((fp_path.parent / "model_inputs.json").read_text(encoding="utf-8"))
    write_arm("FP_L", replace(t_fp, f"in_{NEW}", ls), with_low_share(fp_inputs), "FP plus low_share_diff", record)
    t = t_ref
    for name, v in share_inputs(ref["match_id"].to_numpy()).items():
        t = replace(t, f"in_{name}", v)
    write_arm("R_S2", t, with_shares(inputs), "the reference plus A's minus B's lower-level box-score share, two-week "
                                              "window and 365 days (the dated addition of 9 Oct 2026)", record)
    # checks of the arms (no result read)
    chk = {}
    for arm in ("F", "P", "FP_placebo", "R_L", "FP_L", "R_S2"):
        a = inputs_of(CAND / arm / "model_frame.parquet")
        base = fp if arm == "FP_L" else ref
        names = [c[3:] for c in base.columns if c.startswith("in_")]
        moved = [n for n in names if max_gap(base[f"in_{n}"].to_numpy(), a[f"in_{n}"].to_numpy())[2] > 0]
        chk[arm] = {"same_ids": bool((a["match_id"].to_numpy() == ref["match_id"].to_numpy()).all()),
                    "inputs_moved_from_base": moved, "extra_inputs": [c[3:] for c in a.columns
                                                                      if c.startswith("in_") and c[3:] not in names]}
    # the placebo: same size, alignment destroyed
    size = {}
    for n in TRANSLATED:
        d_fp = fp[f"in_{n}"].to_numpy(float) - ref[f"in_{n}"].to_numpy(float)
        d_pl = pl[n] - ref[f"in_{n}"].to_numpy(float)
        size[n] = {"sd_change_fp": float(np.nanstd(d_fp)), "sd_change_placebo": float(np.nanstd(d_pl)),
                   "corr_fp_placebo_change": float(pd.Series(d_fp).corr(pd.Series(d_pl)))}
    chk["placebo_size"] = size
    write_json(CHECKS / "arms_check.json", chk)
    write_json(CAND / "arms.json", {"built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                                    "reference_frame_sha256": sha256(REF_FRAME), "fp_frame_sha256": sha256(fp_path),
                                    "low_share_sha256": sha256(LOW_SHARE), "arms": record})
    print(json.dumps({k: v for k, v in chk.items() if k != "placebo_size"}, indent=1))
    return 0


def half() -> int:
    """FP_half: forms by interpolation (linear, G4) and points_52w from g4_linearity.py's exact half-scale column when it
    is not linear; refused unless G4's checks passed."""
    g4 = json.loads((CHECKS / "g4_linearity.json").read_text(encoding="utf-8"))
    if not g4.get("forms", {}).get("pass"):
        raise SystemExit("G4 has not passed for the forms: FP_half is not built")
    ref, fp = inputs_of(REF_FRAME), inputs_of(CAND / "FP" / "model_frame.parquet")
    t = table_without(REF_FRAME)
    for n in FORMS:
        r = ref[f"in_{n}"].to_numpy(float)
        t = replace(t, f"in_{n}", r + 0.5 * (fp[f"in_{n}"].to_numpy(float) - r))
    pts = g4.get("points_52w", {})
    if pts.get("linear"):
        r = ref["in_points_52w"].to_numpy(float)
        v = r + 0.5 * (fp["in_points_52w"].to_numpy(float) - r)
        how = "interpolated (linear)"
    elif pts.get("half_column_accepted"):
        h = pd.read_parquet(CHECKS / "g4_points_half.parquet").set_index("match_id")["points_52w_half"]
        v = h.reindex(ref["match_id"]).to_numpy(float)
        how = "the exact value at scale 0.5 (Stage 4's code; it reproduced the reference and FP at scales 0 and 1)"
    else:
        raise SystemExit("points_52w is neither linear nor reproduced at scale 0.5: FP_half is not built")
    t = replace(t, "in_points_52w", v)
    inputs = json.loads(REF_INPUTS.read_text(encoding="utf-8"))
    record = {}
    write_arm("FP_half", t, inputs, f"the reference plus half of FP's change: the 17 forms interpolated; points_52w "
                                    f"{how}", record)
    a = json.loads((CAND / "arms.json").read_text(encoding="utf-8")) if (CAND / "arms.json").exists() else {"arms": {}}
    a["arms"].update(record)
    write_json(CAND / "arms.json", a)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--low-share", action="store_true")
    g.add_argument("--gates", action="store_true")
    g.add_argument("--build", action="store_true")
    g.add_argument("--half", action="store_true")
    a = ap.parse_args()
    if a.low_share:
        return low_share()
    if a.gates:
        return gates()
    if a.build:
        return build()
    return half()


if __name__ == "__main__":
    sys.exit(main())
