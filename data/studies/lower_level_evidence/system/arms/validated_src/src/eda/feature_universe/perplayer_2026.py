"""Each player's own two-week profile (17 inputs), sets in the last 14 days and age, for the model population of
2013-2026: the feature-interactions cartographer's rebuilds (src/eda/feature_interactions/inventory/perplayer_form.py and
perplayer_load.py, which stop at 2024) with the same algorithm and constants, extended to 2026 for the feature store.

Checks before writing (both must hold): val_A - val_B reproduces the model frame's inputs on every season 2013-2026 (as
the originals check on 2013-2024), and the 2013-2024 rows equal the frozen 2013-2024 files exactly. Reads no result
(`a_won` is never loaded). Writes data/studies/feature_universe/perplayer_form_2013_2026.parquet,
perplayer_load_2013_2026.parquet and perplayer_2026_check.json.
Run: ./python.sh src/eda/feature_universe/perplayer_2026.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.inventory import perplayer_form as PF  # noqa: E402  (constants, read-only)
from src.eda.feature_interactions.inventory import perplayer_load as PL  # noqa: E402
from src.eda.predictability_diagnostic import common as PC  # noqa: E402  (asof_sums: the time rule)
from src.eda.predictability_diagnostic import stage3_traits as T3  # noqa: E402  (sums_before)

OUT = ROOT / "data" / "studies" / "feature_universe"
MAX_SEASON = 2026


def model_frame(cols: list[str]) -> pd.DataFrame:
    mf = pd.read_parquet(PF.MODEL, columns=["match_id", "season"] + cols)
    return mf[mf["season"] <= MAX_SEASON].reset_index(drop=True)


def form() -> tuple[pd.DataFrame, dict]:
    """perplayer_form.main()'s algorithm on 2013-2026."""
    used = json.loads((PF.S / "ufc_ideas" / "stageB_adj_summary.json").read_text(encoding="utf-8"))["used"]
    mf = model_frame([f"in_{n}" for n in PF.INPUTS])
    m0 = pd.read_parquet(PF.OLD / "predictability_diagnostic" / "stage0_matches.parquet",
                         columns=["match_id", "tour", "tournament_date", "tournament_id", "round_order",
                                  "player_a_id", "player_b_id"])
    adj = pd.read_parquet(PF.S / "ufc_ideas" / "stageB_adj.parquet",
                          columns=["match_id", "player_id", "tour"] + [f"z_{v}" for v in PF.INPUTS.values()])
    box = adj.merge(m0[["match_id", "tournament_date", "tournament_id", "round_order"]], on="match_id", how="left")
    q = mf[["match_id"]].merge(m0, on="match_id", how="left")
    cols = ["match_id", "player_id", "tour", "tournament_date", "tournament_id", "round_order"]
    allr = pd.concat([box.assign(_side="box"), q.assign(player_id=q["player_a_id"], _side="a")[cols + ["_side"]],
                      q.assign(player_id=q["player_b_id"], _side="b")[cols + ["_side"]]], ignore_index=True)
    day = pd.to_datetime(allr["tournament_date"]).to_numpy().astype("datetime64[D]").astype("int64")
    out = {"match_id": mf["match_id"].to_numpy()}
    check = {}
    is_a, is_b = (allr["_side"] == "a").to_numpy(), (allr["_side"] == "b").to_numpy()
    tour = allr["tour"].to_numpy()
    for name, col in PF.INPUTS.items():
        z = allr[f"z_{col}"].to_numpy(dtype="float64")
        ok = np.isfinite(z) & (allr["_side"] == "box").to_numpy()
        val = np.full(len(allr), np.nan)
        for t in ("atp", "wta"):
            k = used[col][t]
            h3, K3, tau = float(k["h3"]), float(k["K3"]), int(k["tau"])
            if tau != 0:
                raise ValueError(f"{col} {t}: tau {tau} is not handled here")
            f = np.exp2((day - PF.REF_DAY) / (7.0 * h3))
            tmp = allr[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
            sel = tour == t
            tmp["s1"] = np.where(ok & sel, z, 0.0) * f
            tmp["s0"] = np.where(ok & sel, 1.0, 0.0) * f
            tmp["n"] = np.where(ok & sel, 1.0, 0.0)
            sums = PC.asof_sums(tmp, ["s1", "s0", "n"]).to_numpy()
            s1, s0, n = sums[:, 0] / f, sums[:, 1] / f, sums[:, 2]
            val = np.where(sel, np.where(n > 0.5, s1 / (s0 + K3), np.nan), val)
        va, vb = val[is_a], val[is_b]
        out[f"{name}_a"], out[f"{name}_b"] = va, vb
        model = mf[f"in_{name}"].to_numpy(dtype="float64")
        diff = np.where(np.isfinite(va) & np.isfinite(vb), va - vb, np.nan)
        both = np.isfinite(diff) & np.isfinite(model)
        late = both & (mf["season"] >= 2025).to_numpy()
        check[name] = {"compared": int(both.sum()), "max_abs_gap": float(np.max(np.abs(diff[both] - model[both]))),
                       "compared_2025_2026": int(late.sum()),
                       "max_abs_gap_2025_2026": float(np.max(np.abs(diff[late] - model[late]))) if late.any() else None,
                       "missing_pattern_equal": bool(np.array_equal(np.isfinite(diff), np.isfinite(model)))}
    return pd.DataFrame(out), check


def load() -> tuple[pd.DataFrame, dict]:
    """perplayer_load.main()'s algorithm on 2013-2026."""
    mf = model_frame(["in_sets_14d", "in_age"])
    m = pd.read_parquet(PL.OLD / "predictability_diagnostic" / "stage0_matches.parquet",
                        columns=["match_id", "tournament_date", "tournament_id", "round_order", "status"])
    p = pd.read_parquet(PL.OLD / "predictability_diagnostic" / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "side", "sets_won_d", "age"])
    r = p.merge(m, on="match_id", how="left")
    played = r["status"].isin(["completed", "retired"]).to_numpy()
    sets = r["sets_won_d"].to_numpy(dtype="float64")
    V = np.column_stack([(played & ~np.isfinite(sets)).astype(float), np.where(played & np.isfinite(sets), sets, 0.0)])
    tmp = r[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    tmp["v0"], tmp["v1"] = V[:, 0], V[:, 1]
    car = PC.asof_sums(tmp, ["v0", "v1"]).to_numpy()
    day = pd.to_datetime(r["tournament_date"]).to_numpy().astype("datetime64[D]").astype("int64")
    pcode = pd.factorize(r["player_id"])[0]
    win = car - T3.sums_before(pcode, day, V, pcode, day - PL.WINDOW)
    r["sets_14d"] = np.where(win[:, 0] < 0.5, np.log1p(np.maximum(win[:, 1], 0.0)), np.nan)
    age = r["age"].to_numpy(dtype="float64")
    r["age_c"] = np.where((age >= 14) & (age <= 50), age - 25.0, np.nan)
    A = mf[["match_id"]].merge(r[r["side"] == "A"][["match_id", "sets_14d", "age_c"]], on="match_id", how="left")
    B = mf[["match_id"]].merge(r[r["side"] == "B"][["match_id", "sets_14d", "age_c"]], on="match_id", how="left")
    check = {"sets_14d": PL.gap(A["sets_14d"].to_numpy() - B["sets_14d"].to_numpy(), mf["in_sets_14d"].to_numpy(float)),
             "age": PL.gap(A["age_c"].to_numpy() - B["age_c"].to_numpy(), mf["in_age"].to_numpy(float))}
    out = pd.DataFrame({"match_id": mf["match_id"], "sets_14d_a": A["sets_14d"], "sets_14d_b": B["sets_14d"],
                        "age_a": A["age_c"] + 25.0, "age_b": B["age_c"] + 25.0})
    return out, check


def equals_frozen(new: pd.DataFrame, frozen_path: Path) -> bool:
    old = pd.read_parquet(frozen_path)
    m = new.set_index("match_id").reindex(old["match_id"])
    return all(np.array_equal(m[c].to_numpy(float), old[c].to_numpy(float), equal_nan=True)
               for c in old.columns if c != "match_id")


def main() -> int:
    fm, fcheck = form()
    lm, lcheck = load()
    inv = ROOT / "data" / "studies" / "feature_interactions" / "inventory"
    checks = {"form": fcheck, "load": lcheck,
              "form_2013_2024_equals_frozen": equals_frozen(fm, inv / "perplayer_form_2013_2024.parquet"),
              "load_2013_2024_equals_frozen": equals_frozen(lm, inv / "perplayer_load_2013_2024.parquet")}
    worst = max(v["max_abs_gap"] for v in fcheck.values())
    ok = (checks["form_2013_2024_equals_frozen"] and checks["load_2013_2024_equals_frozen"] and worst < 1e-5
          and all(v["missing_pattern_equal"] for v in fcheck.values())
          and lcheck["sets_14d"]["max_abs_gap"] < 1e-6 and lcheck["age"]["max_abs_gap"] < 1e-6)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "perplayer_2026_check.json").write_text(json.dumps(checks, indent=1, default=str), encoding="utf-8")
    if not ok:
        raise SystemExit(f"checks failed: see {OUT / 'perplayer_2026_check.json'}")
    fm.to_parquet(OUT / "perplayer_form_2013_2026.parquet", index=False)
    lm.to_parquet(OUT / "perplayer_load_2013_2026.parquet", index=False)
    print(f"form {fm.shape}, load {lm.shape}; worst form gap {worst:.2e}; 2013-2024 equal frozen: "
          f"{checks['form_2013_2024_equals_frozen']}, {checks['load_2013_2024_equals_frozen']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
