"""The level offsets of the role-08 candidate (lower-level evidence), estimated on seasons 2010-2018 only.

    --rates         delta_rate[spw | rpw, tour, bucket] from Stage 4's own history rows (stage4_features.load_rows and
                    stat_xd, unchanged: completed, standard format, both counts present), on the live Stage 0, which is
                    checked to be the frozen reference's file first. Written before the build; the sandbox's Stage 4
                    hook re-estimates them from its own rows and refuses to run if they differ.
    --check-forms   after the build: delta_z re-derived from the untranslated z the hook recorded
                    (offsets/forms_z_untranslated.parquet) must equal the hook's forms_offsets.csv
    --summary       both tables in a readable wide form (offsets/offsets_summary.csv)

The rule is translate_hooks.offsets_from_levels (the pre-registration's). No outcome is read beyond 2018 box scores.
Run: ./python.sh src/eda/lower_level_evidence/offsets.py --rates | --check-forms | --summary
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.lower_level_evidence import translate_hooks as H  # noqa: E402

CAND = LC.OUT / "candidates"
OFFSETS = CAND / "offsets"
RATES = OFFSETS / "rate_offsets.csv"
FORMS = OFFSETS / "forms_offsets.csv"
Z_RECORD = OFFSETS / "forms_z_untranslated.parquet"
FILES = LC.REF / "files.csv.gz"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def frozen_sha(source: str) -> str:
    f = pd.read_csv(FILES)
    return str(f.loc[f["source"] == source, "sha256"].iloc[0])


def rates() -> int:
    from src.eda.predictability_diagnostic import stage4_features as F
    for name in ("stage0_matches.parquet", "stage0_match_players.parquet"):
        src = f"data/studies/predictability_diagnostic/{name}"
        if sha256(ROOT / src) != frozen_sha(src):
            raise SystemExit(f"{src} is not the frozen reference's: the offsets must come from the reference's Stage 0")
    rows, _ = F.load_rows()
    xd = F.stat_xd(rows)
    bucket = H.buckets_of(rows["match_id"].to_numpy(), {"stage0_matches": ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet"})
    t = H.estimate_rates({s: xd[s] for s in H.RATE_STATS}, rows["tour"].to_numpy().astype(str),
                         rows["player_id"].to_numpy().astype(str), rows["year"].to_numpy().astype(int), bucket)
    OFFSETS.mkdir(parents=True, exist_ok=True)
    t.to_csv(RATES, index=False, float_format="%.17g")
    rec = {"what": "delta_rate[spw | rpw, tour, bucket]: same player-season (>= 3 admitted rows at MAIN and at the "
                   "bucket), pooled rate at the bucket minus at MAIN, mean over player-seasons of 2010-2018; points per "
                   "point; fallbacks and placeholders as the pre-registration",
           "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
           "rows_read": int(len(rows)), "seasons": list(H.YEARS),
           "stage0_sha256": {n: sha256(ROOT / f"data/studies/predictability_diagnostic/{n}")
                             for n in ("stage0_matches.parquet", "stage0_match_players.parquet")},
           "file_sha256": sha256(RATES)}
    (OFFSETS / "rate_offsets.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    show = t[t["bucket"].isin(H.ESTIMATED)][["key", "tour", "bucket", "player_seasons", "estimate", "lo", "hi",
                                             "value_used", "source"]]
    with pd.option_context("display.width", 200, "display.max_rows", 100):
        print(show.round(5).to_string(index=False))
    return 0


def check_forms() -> int:
    z = pd.read_parquet(Z_RECORD)
    Z = {(s, ch): z[f"z_{ch}_{s}"].to_numpy(float) for s, ch in H.FORM_SPECS if f"z_{ch}_{s}" in z.columns}
    again = H.estimate_forms(Z, z["tour"].to_numpy().astype(str), z["player_id"].to_numpy().astype(str),
                             z["year"].to_numpy().astype(int), z["bucket"].to_numpy().astype(str))
    stored = H.read_offsets(FORMS)
    ok, gap = H.same_offsets(stored, again)
    res = {"what": "the form offsets re-derived outside the build from the untranslated z the hook recorded",
           "pairs": len(Z), "box_rows": int(len(z)), "equal": bool(ok), "largest_gap": gap,
           "checked_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    (CAND / "checks").mkdir(parents=True, exist_ok=True)
    (CAND / "checks" / "offsets_forms_rederived.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res)
    return 0 if ok else 1


def summary() -> int:
    parts = []
    for path in (FORMS, RATES):
        if path.exists():
            parts.append(pd.read_csv(path))
    t = pd.concat(parts, ignore_index=True)
    t["cell"] = t["tour"] + " " + t["bucket"]
    est = t[t["bucket"].isin(H.ESTIMATED)].copy()
    own = est["source"].eq("own tour").to_numpy()
    both = est["source"].str.startswith("both tours").to_numpy()
    se = np.where(own, est["se"], est["both_tours_se"])
    n = np.where(own, est["player_seasons"], est["both_tours_player_seasons"]).astype(int)
    v = est["value_used"].to_numpy(float)
    est["text"] = [f"{x:+.3f} [{x - 1.96 * s:+.3f}, {x + 1.96 * s:+.3f}] n={k}{'' if o else (' (both tours)' if b else '')}"
                   if np.isfinite(s) and (o or b) else f"{x:+.3f} (zero: too few)"
                   for x, s, k, o, b in zip(v, se, n, own, both)]
    wide = est.pivot_table(index=["kind", "key"], columns="cell", values="text", aggfunc="first")
    wide.to_csv(OFFSETS / "offsets_summary.csv")
    with pd.option_context("display.width", 250, "display.max_columns", 20, "display.max_colwidth", 40):
        print(wide.to_string())
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rates", action="store_true")
    g.add_argument("--check-forms", action="store_true")
    g.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.rates:
        return rates()
    if a.check_forms:
        return check_forms()
    return summary()


if __name__ == "__main__":
    sys.exit(main())
