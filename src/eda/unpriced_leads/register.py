"""Builds the registry of the unpriced-leads study's five lead groups (docs/studies/unpriced_leads/preregistration.md),
revised before the freeze on the red team's findings (team/red_team.md).

For each member: its values file (SHA-256), column, registered sign, completeness gate, and, for the frozen-projection
secondary, its orthogonal projection on the model's 48 non-price inputs and its scales, fitted on seasons <= 2024 with no
outcome. The registry also names the instance the looks read (frame, book prices, input list, forecast table, with their
SHA-256) and the Look-B-only hypothesis H7. Then the discovery readings (seasons <= 2024, through the harness) of every
member, group and the omnibus with the looks' base and scoring, and the power of the registered two-look design
(Look A at one-sided 0.02; the final, A and B combined, at 0.03; t on 20 degrees of freedom at Look A), at realisations
1, 0.5, 0.45 and 0.25 of the discovery effect.

Writes docs/studies/unpriced_leads/registry.json (frozen with the preregistration),
data/studies/unpriced_leads/registration/discovery_registered.csv, power.json and h7_rust_store.parquet.
Run: ./python.sh src/eda/unpriced_leads/register.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal, norm
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import look as LK  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

REGISTRY = ROOT / "docs" / "studies" / "unpriced_leads" / "registry.json"
OUTD = H.OUT / "registration"
C = "data/studies/unpriced_leads/candidates"
STORE = ROOT / "data" / "studies" / "feature_universe" / "store.parquet"

# The five groups (synthesis 2, revised on the red team's M4). Members: (values file, column, sign, gate, label).
# Signs: -1 = the player higher on the statistic is expected to do worse than the close. Gates: the outcome-free input
# series whose monthly count must stay at 80% or more of the same month a year earlier (look.py).
LUCK, RHYTHM, POOL = f"{C}/luck/values.parquet", f"{C}/rhythm/values.parquet", f"{C}/pool_rebuilt/values.parquet"
GROUPS: list[dict] = [
    {"id": "G1", "name": "Luck read as skill", "members": [
        (LUCK, "PS03_net", -1, "box_all", "net break-point luck (saves and conversions beyond the serve and return rates)"),
        (LUCK, "PS06_close", -1, "box_all", "close-set luck (sets from 5-5 beyond expectation)"),
        (LUCK, "PS04_flat", -1, "box_all", "a flattering last scoreline (games share beyond points share)")]},
    {"id": "G2", "name": "The post-Slam letdown", "members": [
        (POOL, "rb__fi__B-MOTIV__post_slam", -1, "none", "reached a Slam quarter-final or better elsewhere within 21 days")]},
    {"id": "G3", "name": "Fast courts amplify big servers", "members": [
        (POOL, "rb__fi__B-VENUE__f09_venue_pace_x_ace", +1, "none", "venue pace x the ace-offence gap")]},
    {"id": "G4", "name": "Status over-priced, low-visibility form under-priced", "members": [
        (POOL, "rb__el__low_share_diff", +1, "lower_level", "share of last year's matches below the main tour"),
        (POOL, "rb__fp__f12_salience__hasL_a-b", +1, "lower_level", "has recent form earned where nobody watches"),
        (POOL, "rb__pp__seeded_a-b", -1, "none", "seeded"),
        (POOL, "rb__fp__f14_anchor__fame_a-b", -1, "none", "fame (titles and Slam quarter-finals since 2010)")]},
    {"id": "G5", "name": "Rhythm the singles record misses", "members": [
        (RHYTHM, "rb01_d7_else", +1, "doubles", "doubles played at other events in the previous 7 days"),
        (RHYTHM, "rb03_lt20", -1, "presence", "rest under 20 hours since the previous match ended"),
        (POOL, "rb__fp__f28_state__bdst_pastfat_a-b", +1, "presence", "past fatigue: recent match load (14 days)")],
     "secondary_members": [
        (RHYTHM, "rb14_cold28", +1, "none", "a bye seed's first match against an opponent who has played here (dropped "
                                           "from the score on the red team's M4; a member-level secondary)")]},
]
H7 = {"id": "H7", "name": "Rust after a break (Look B only)", "members": [
    ("data/studies/unpriced_leads/registration/h7_rust_store.parquet", "rust0_diff", -1, "lower_level",
     "the rust state after a break of six weeks or more (pool U-135, store values; rebuilt at Look B)")]}
LOOK_B_END = "2027-08-01"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def member_entry(frame: pd.DataFrame, values: str, column: str, sign: int, gate: str, label: str) -> dict:
    v = pd.read_parquet(ROOT / values, columns=["match_id", column]).astype({"match_id": str})
    x = v.drop_duplicates("match_id").set_index("match_id")[column].reindex(frame["match_id"]).to_numpy(float)
    xo, coef = H.orthogonal_part(frame, x)
    sc_o, sc_r = {}, {}
    for tour in ("atp", "wta"):
        m = (frame["tour"] == tour).to_numpy()
        sc_o[tour] = float(np.sqrt(np.nanmean(xo[m] ** 2)))
        sc_r[tour] = float(np.sqrt(np.nanmean(x[m] ** 2)))
    return {"name": column, "label": label, "values": values, "column": column, "sign": int(sign), "kind": "diff",
            "gate": gate, "values_sha256": sha256(ROOT / values), "orth_coef": coef, "scale_orth": sc_o,
            "scale_raw": sc_r}


def h7_values() -> None:
    """The store's rust state as A - B for every store match (outcome-free; the store has no result column)."""
    s = pd.read_parquet(STORE, columns=["match_id", "fp__f26_impairment__bdinj_rust0_a",
                                        "fp__f26_impairment__bdinj_rust0_b"]).astype({"match_id": str})
    s["rust0_diff"] = s["fp__f26_impairment__bdinj_rust0_a"] - s["fp__f26_impairment__bdinj_rust0_b"]
    OUTD.mkdir(parents=True, exist_ok=True)
    s[["match_id", "rust0_diff"]].to_parquet(OUTD / "h7_rust_store.parquet", index=False)


def build_registry(frame: pd.DataFrame) -> dict:
    inst = H.INSTANCE
    rel = lambda p: str(Path(p).relative_to(ROOT)).replace("\\", "/")  # noqa: E731
    groups = []
    for g in GROUPS:
        entry = {"id": g["id"], "name": g["name"], "tours": "both",
                 "members": [member_entry(frame, *m) for m in g["members"]],
                 "secondary_members": [member_entry(frame, *m) for m in g.get("secondary_members", [])]}
        groups.append(entry)
    h7 = {"id": H7["id"], "name": H7["name"], "tours": "both", "members": [member_entry(frame, *m) for m in H7["members"]]}
    return {"study": "unpriced_leads", "discovery_seasons": "2013-2024", "look_b_end": LOOK_B_END,
            "alpha_look_a": LK.ALPHA_A, "alpha_final": LK.ALPHA_FINAL, "gate_ratio": LK.GATE_RATIO,
            "frame": rel(inst / "model_frame.parquet"), "frame_sha256": sha256(inst / "model_frame.parquet"),
            "book_prices": rel(inst / "book_prices.parquet"), "book_prices_sha256": sha256(inst / "book_prices.parquet"),
            "model_inputs": rel(inst / "model_inputs.json"), "model_inputs_sha256": sha256(inst / "model_inputs.json"),
            "forecasts": rel(H.ANALYSIS), "forecasts_sha256": sha256(H.ANALYSIS),
            "code_sha256": {f: sha256(ROOT / "src" / "eda" / "unpriced_leads" / f) for f in
                            ("screen.py", "look.py", "register.py", "build_luck.py", "build_rhythm.py",
                             "rebuild_pool.py")},
            "groups": groups, "look_b_only": [h7]}


def discovery(reg: dict, frame: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(level: str, gid: str, name: str, s: np.ndarray):
        for tour in ("both", "atp", "wta"):
            m = np.ones(len(frame), bool) if tour == "both" else (frame["tour"] == tour).to_numpy()
            fr = frame[m].reset_index(drop=True)
            r = LK.fit(fr, s[m])
            r0 = LK.fit(fr, s[m], curv=False)
            eras = {}
            for era, (a, b) in H.ERAS.items():
                e = fr["season"].between(a, b).to_numpy()
                eras[f"z_{era}"] = LK.fit(fr[e].reset_index(drop=True), s[m][e])["z"]
            rows.append({"level": level, "group": gid, "name": name, "tour": tour, "beta": r["beta"], "se": r["se"],
                         "z": r["z"], "z_no_curv": r0["z"], "n": r["n"], **eras})

    groups = reg["groups"]
    add("omnibus", "ALL", "omnibus", LK.omnibus_score(groups, frame, "window"))
    for g in groups:
        add("group", g["id"], g["name"], LK.group_score(g, frame, "window"))
        for mm in g["members"]:
            add("member", g["id"], mm["label"], LK.member_score(mm, frame, "window"))
        for mm in g.get("secondary_members", []):
            add("secondary member", g["id"], mm["label"], LK.member_score(mm, frame, "window"))
    for h in reg.get("look_b_only", []):
        add("look B only", h["id"], h["name"], LK.group_score(h, frame, "window"))
    return pd.DataFrame(rows)


def power(disc: pd.DataFrame) -> dict:
    """The registered two-look design's power for the omnibus and each group (both tours): Look A one-sided 0.02
    (t, 20 df), the final (A and B combined, ~5,100 Look B matches) one-sided 0.03; with the discovery beta per SD
    times k (1, 0.5, 0.45, 0.25). SE from resolution.json (design effect 1.08)."""
    res = json.loads((H.OUT / "resolution.json").read_text(encoding="utf-8"))
    se_a = res["lookA_2025_to_2026-07-28"]["both"]["se_beta_per_rms"]
    se_b = 1.08 / np.sqrt(5100 * 0.206)
    se_ab = 1 / np.sqrt(1 / se_a ** 2 + 1 / se_b ** 2)
    rho = se_ab / se_a                          # corr(Z_A, Z_AB) = sqrt(I_A / (I_A + I_B))
    ca = student_t.isf(LK.ALPHA_A, 20)
    cf = norm.isf(LK.ALPHA_FINAL)
    ca05 = student_t.isf(0.05, 20)
    out = {"se_look_a": se_a, "se_look_b_5100": float(se_b), "se_a_plus_b": float(se_ab), "rho": float(rho),
           "critical_look_a_t20": float(ca), "critical_final_z": float(cf)}
    d = disc[(disc["tour"] == "both") & disc["level"].isin(["omnibus", "group"])]
    for _, r in d.iterrows():
        k_out = {}
        for k in (1.0, 0.5, 0.45, 0.25):
            da, dab = k * r["beta"] / se_a, k * r["beta"] / se_ab
            p_a = float(norm.sf(ca - da))
            # P(confirm at A or (not at A and Z_AB >= cf)) = 1 - P(Z_A < ca, Z_AB < cf)
            both_below = multivariate_normal(mean=[da, dab], cov=[[1, rho], [rho, 1]]).cdf([ca, cf])
            k_out[f"k_{k}"] = {"expected_z_A": float(da), "power_A_at_0.02": p_a,
                               "power_by_final": float(1 - both_below),
                               "power_A_alone_at_0.05": float(norm.sf(ca05 - da))}
        out[r["name"]] = {"beta_discovery_per_sd": float(r["beta"]), "z_discovery": float(r["z"]), **k_out}
    return out


def main() -> int:
    h7_values()
    frame = H.load_frame()
    reg = build_registry(frame)
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=1), encoding="utf-8")
    OUTD.mkdir(parents=True, exist_ok=True)
    disc = discovery(reg, frame)
    disc.to_csv(OUTD / "discovery_registered.csv", index=False)
    pw = power(disc)
    (OUTD / "power.json").write_text(json.dumps(pw, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 60)
    print(disc[disc["tour"] == "both"].round(3).to_string(index=False))
    for k, v in pw.items():
        if isinstance(v, dict):
            print(k[:44], {kk: (round(vv["expected_z_A"], 2), round(vv["power_A_at_0.02"], 2),
                                round(vv["power_by_final"], 2), round(vv["power_A_alone_at_0.05"], 2))
                           for kk, vv in v.items() if kk.startswith("k_")})
        else:
            print(k, round(v, 4))
    print("registry sha256:", sha256(REGISTRY))
    return 0


if __name__ == "__main__":
    sys.exit(main())
