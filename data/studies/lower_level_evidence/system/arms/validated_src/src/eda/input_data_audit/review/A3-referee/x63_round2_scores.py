"""Round 2, F2x: where Sackmann's score differs from the WTA API's, is the exchanged box consistent with the API's
score (games identity on both players)? Shows that the remaining identity miss is the score, not the box."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402
from x60_round2 import boxes, raw_row  # noqa: E402

E = pd.read_csv(rc.OUT / "round2_evidence.csv")
cand = pd.read_csv(rc.ROOT / "data/studies/input_data_audit/fixes/round2_A_candidates.csv")
g = E[(E["cand"] == "F2x") & E["api_score"].notna()].copy()
g["api_score_s"] = g["api_score"].str.replace(",", " ").str.replace("Ret'd", "RET")
diff = g[g["api_score_s"].str.strip() != g["score"].str.strip()]
for _, r in diff.iterrows():
    c = cand[cand["match_id"] == r["match_id"]].iloc[0]
    rr = raw_row(c["source_file"], int(c["source_row"]))
    w, l_ = boxes(rr)
    sp = rc.score_parts(pd.Series([r["api_score_s"]]))
    gw, gl, tw, tl = sp["games_w"][0], sp["games_l"][0], sp["tb_w"][0], sp["tb_l"][0]
    ident = rc.games_identity(pd.Series([gw]), pd.Series([gl]), l_, w, pd.Series([tw]), pd.Series([tl]))   # exchanged
    print(f"{r['event']} {r['round']}: Sackmann score '{r['score']}' vs API '{r['api_score_s']}'; exchanged box with the "
          f"API's score: identity winner {bool(ident['w_fits'][0])}, loser {bool(ident['l_fits'][0])}")
