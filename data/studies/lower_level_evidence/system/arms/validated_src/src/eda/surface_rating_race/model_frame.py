"""The model's inputs after the owner's decision of 6 Oct 2026 to swap the old Elo blend for the offset Elo
(docs/decisions/2026-10-06-offset-elo.md), for every match the best model could use: main tour with closing odds,
2013-2026, the leak-proof refit's 39,918 training and 23,819 test matches.

The model after that day's two decisions, 58 inputs:
    * the best 2026 model's inputs (the closing odds' log-odds and the pre-match inputs, leak-proof IOS:
      src/eda/tabpfn_leakproof/), of which 31 are unchanged;
    * its 21 IOS profile inputs built per surface (docs/decisions/2026-10-06-surface-ios-profile.md; the surface-IOS
      study's arm sprof, data/studies/surface_ios/arms/sprof.parquet);
    * elo_logit and surface_first replaced by six inputs (the race's arm elo_off): overall Elo, the surface offset,
      and both players' matches on the surface this season and days since their last match on it.

Columns: the frame's identifiers, then in_<name> per input in the model's order (the surface profile keeps its input
names). Checks before writing: the rows and their order equal the Elo-pieces frame and the surface-IOS arm; the 31
unchanged inputs equal the leak-proof refit's upload value for value (training and test rows); the surface profile
equals the surface-IOS arm, and the six Elo inputs the race's elo_off arm; swapping A and B twice gives the frame back.

Writes data/studies/surface_rating_race/model/model_frame.parquet and model_inputs.json.
Run: ./python.sh src/eda/surface_rating_race/model_frame.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import arms as EA  # noqa: E402
from src.eda.surface_rating_race import arms as A  # noqa: E402
from src.eda.surface_rating_race import common as C  # noqa: E402
from src.eda.tabpfn_leakproof import common as LP  # noqa: E402

OUT = C.OUT / "model"
META = ["match_id", "tour", "season", "tournament_date", "a_won", "p_mkt", "tabpfn_split", "debut_season"]
ELO_SWAP = ["elo_overall", "elo_surf_offset", "surf_season_a", "surf_season_b", "surf_layoff_a", "surf_layoff_b"]


def same(x, y) -> bool:
    return bool(np.array_equal(np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64"), equal_nan=True))


def main() -> int:
    f = A.load_frame(with_offset=False, with_sprof=True)
    cols = A.ARMS["model"]
    X = A.matrix(f, "model")
    names = [c[3:] if c.startswith("sf_") else c for c in cols]
    checks = {}
    # rows and order
    s = pd.read_parquet(A.SPROF_ARM)
    checks["rows_equal_surface_ios_arm"] = bool(np.array_equal(s["match_id"].astype(str).to_numpy(),
                                                               f["match_id"].astype(str).to_numpy()))
    # the surface profile and the Elo swap against their sources
    checks["surface_profile_equals_sprof_arm"] = all(same(X[f"sf_{n}"], s[f"in_{n}"]) for n in A.SPROF)
    elo = A.matrix(f, "elo_off")
    checks["elo_swap_equals_race_elo_off"] = all(same(X[n], elo[n]) for n in ELO_SWAP)
    # the unchanged inputs against the leak-proof refit's upload
    unchanged = [n for n in cols if not n.startswith("sf_") and n not in ELO_SWAP]
    X_train, y_train, X_query, ids, _ = LP.load_upload()
    tr = (f["tabpfn_split"] == "train").to_numpy()
    te = (f["tabpfn_split"] == "test").to_numpy()
    n_te = int(te.sum())
    checks["unchanged_inputs"] = len(unchanged)
    checks["unchanged_equal_upload_train"] = all(same(X.loc[tr, n], X_train[n]) for n in unchanged)
    checks["unchanged_equal_upload_test"] = all(same(X.loc[te, n], X_query[n].iloc[:n_te]) for n in unchanged)
    checks["labels_equal_upload"] = bool(np.array_equal(f.loc[tr, "a_won"].astype("int64").to_numpy(), y_train))
    checks["test_ids_equal_upload"] = bool(np.array_equal(f.loc[te, "match_id"].to_numpy(), ids["match_id"].to_numpy()[:n_te]))
    checks["flip_is_an_involution"] = bool(np.allclose(A.flip(A.flip(X)).to_numpy(), X.to_numpy(), equal_nan=True))
    bad = [k for k, v in checks.items() if v is False]
    if bad or len(cols) != 58:
        raise RuntimeError(f"checks failed: {bad} ({len(cols)} inputs)")
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.concat([f[META].reset_index(drop=True),
                       pd.DataFrame({f"in_{nm}": X[c].to_numpy(dtype="float64") for c, nm in zip(cols, names)})], axis=1)
    frame.to_parquet(OUT / "model_frame.parquet", index=False)

    def kind(c: str) -> str:
        if c in A.ANTISYMMETRIC:
            return "diff"
        return "pair" if c in EA.SWAP else "context"

    def source(c: str) -> str:
        if c.startswith("sf_"):
            return "surface IOS (decision 2026-10-06-surface-ios-profile; surface-IOS study, arm sprof)"
        if c in ELO_SWAP:
            return "offset Elo (decision 2026-10-06-offset-elo; surface-Elo-pieces study's pieces.py, race arm elo_off)"
        return "the best 2026 model, leak-proof refit (src/eda/tabpfn_leakproof/), unchanged"

    C.write_json(OUT / "model_inputs.json", {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "decisions": ["docs/decisions/2026-10-06-surface-ios-profile.md", "docs/decisions/2026-10-06-offset-elo.md"],
        "inputs": [{"name": nm, "kind": kind(c), "source": source(c)} for c, nm in zip(cols, names)],
        "replaced": {"elo_logit": "the 70/30 (men) or 75/25 (women) surface Elo blend", "surface_first":
                     "A's first matches on the surface this season minus B's"},
        "kinds": {"diff": "A - B, negated when A and B swap", "pair": "an (A, B) couple, exchanged when they swap",
                  "context": "describes the match, unchanged when they swap"},
        "rows": {"all": int(len(frame)), "train_2013_2021": int(tr.sum()), "test_2022_2026": n_te},
        "checks": checks,
        "sources_sha256": {p.name: C.sha256_file(p) for p in (C.PIECES_FRAME, A.SPROF_ARM)}})
    C.log(f"model_frame.parquet: {len(frame):,} matches x {len(cols)} inputs; checks {checks}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
