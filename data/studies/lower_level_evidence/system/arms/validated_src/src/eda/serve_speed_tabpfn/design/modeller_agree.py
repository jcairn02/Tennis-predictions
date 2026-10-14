"""R3 check (agent 2, modeller): does the built spd_f agree with the auditor's independent rebuild (auditor_lib)?
Criterion (2_audit.md C7, R4): the A - B correlation >= 0.995 and |difference| <= 0.05 s_f on >= 99% of frame matches.
Feature values only; no result is read.

    (i)  fully independent: auditor_lib's own panel (ks-first, from the R1 records), its own as-of snapshots
         (Snapshots), its own histories and filter (kalman_batch, men's constants), on the frame's sides
    (ii) implementation only: auditor_lib's snapshots, histories and filter run on the engineer's panel
         (speed_panel.parquet), so panel differences are taken out
Both are standardised with the build's s_f and clipped at +-4 like spd_f; men's matches carry the comparison (women's
spd_f is 0 in both, and is reported separately).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_agree.py
Writes data/studies/serve_speed_tabpfn/features/agreement_auditor_lib.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.design import auditor_lib as AL  # noqa: E402

OUTF = F.OUT / "agreement_auditor_lib.json"


def auditor_f(p: pd.DataFrame, t: pd.DataFrame) -> np.ndarray:
    """auditor_lib's f_hat for the men's target sides t on panel p (its column names)."""
    pa = p[p["tour"].eq("atp")].sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"],
                                            kind="mergesort").reset_index(drop=True)
    snaps = {"atp": AL.Snapshots(pa)}
    h = AL.histories(pa, t)
    Z = AL.centred_values(pa, t, h, "asof", snaps=snaps)
    kf = AL.kalman_batch(Z, AL.noise(pa, h, AL.MEN), AL.days_matrix(pa, h), t["es"].to_numpy(float), AL.MEN)
    return kf["f_hat"]


def compare(m: pd.DataFrame, t: pd.DataFrame, f_al: np.ndarray, s_f: float) -> dict:
    t = t.assign(f_al=f_al)
    a = t[t["side"].eq("A")].set_index("match_id")["f_al"]
    b = t[t["side"].eq("B")].set_index("match_id")["f_al"]
    men = m[m["tour"].eq("atp")].set_index("match_id")
    d_al = (a - b).reindex(men.index)
    mine = men["spd_f"].to_numpy()
    theirs = np.clip(d_al.to_numpy() / s_f, -F.CLIP, F.CLIP)
    diff = np.abs(mine - theirs)
    out = {"men_matches": int(len(men)), "corr": float(np.corrcoef(mine, theirs)[0, 1]),
           "share_within_0.05": float((diff <= 0.05).mean()), "max_abs_diff": float(diff.max()),
           "share_within_0.01": float((diff <= 0.01).mean())}
    for lab, s in (("2013-2021", men["season"].le(2021)), ("2022-2023", men["season"].between(2022, 2023)),
                   ("2024-2026", men["season"].ge(2024))):
        k = s.to_numpy()
        out[lab] = {"matches": int(k.sum()), "corr": float(np.corrcoef(mine[k], theirs[k])[0, 1]),
                    "share_within_0.05": float((diff[k] <= 0.05).mean())}
    n_all = len(m)
    out["share_within_0.05_all_frame_matches"] = float(((diff <= 0.05).sum() + (m["tour"].eq("wta")).sum()) / n_all)
    out["pass"] = bool(out["corr"] >= 0.995 and out["share_within_0.05"] >= 0.99)
    return out


def main() -> None:
    meta = json.loads(F.META.read_text(encoding="utf-8"))
    s_f = meta["s_f"]
    m = pd.read_parquet(F.FEATURES, columns=["match_id", "tour", "season", "spd_f"])
    keys = P.load_frame_keys()
    t = F.side_targets(keys)
    t = t[t["tour"].eq("atp")].reset_index(drop=True)
    res = {"s_f": s_f, "criterion": "corr >= 0.995 and |diff| <= 0.05 (in s_f units) on >= 99% of matches",
           "features_parquet_sha256": F.sha256(F.FEATURES), "panel_sha256": F.sha256(F.PANEL_FILE)}
    # (i) the fully independent rebuild
    p_al = AL.panel("ks_first")
    res["i_independent_panel"] = compare(m, t, auditor_f(p_al, t), s_f)
    print("(i)", json.dumps(res["i_independent_panel"]))
    # (ii) auditor_lib on the engineer's panel
    pe = P.load_panel(use_only=True).rename(columns={"family": "fam"})
    pe["obs"] = pe["obs"].astype(float)
    res["ii_engineer_panel"] = compare(m, t, auditor_f(pe, t), s_f)
    print("(ii)", json.dumps(res["ii_engineer_panel"]))
    # (iii) attribution: (ii) with the auditor's family definition (Slam or 'tour' x draw: Challengers and team/ITF
    # editions pooled with tour events, i.e. without the C1/E7 'ch' family)
    pf = pe.copy()
    slam = pf["fam"].str.split("|").str[0]
    draw = pf["fam"].str.split("|").str[1]
    pf["fam"] = np.where(slam.isin(["AO", "RG", "W", "USO"]), slam, "tour") + "_" + draw
    res["iii_engineer_panel_auditor_families"] = compare(m, t, auditor_f(pf, t), s_f)
    print("(iii)", json.dumps(res["iii_engineer_panel_auditor_families"]))
    # panel differences behind (i)
    k_al = set(zip(p_al["match_id"], p_al["side"]))
    k_en = set(zip(pe["match_id"], pe["side"]))
    res["panels"] = {"auditor_rows": len(k_al), "engineer_use_rows": len(k_en), "common": len(k_al & k_en),
                     "auditor_only": len(k_al - k_en), "engineer_only": len(k_en - k_al)}
    OUTF.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res["panels"]))


if __name__ == "__main__":
    main()
