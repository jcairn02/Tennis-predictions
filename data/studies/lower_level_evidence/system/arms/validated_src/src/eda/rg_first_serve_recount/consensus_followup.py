"""The reviewers' consensus on the follow-ups of 9 Oct 2026 (whole_box.py): RG's whole box score for Roland Garros
2022-2026 under the Slam rule of 6 Oct, and the four RG 2021 boxes exchanged between winner and loser.

As on 8 Oct (docs/decisions/2026-10-08-corrupt-data-fixes.md), a change is kept only where all three independent
reviewers confirmed it: an override only where all three name the same match with the same eighteen values (blank
equals blank), an exchange only where all three name the same raw row. Each reviewer writes, in
data/studies/rg_first_serve_recount/followup/review/<reviewer>/,
    verdict.json          {"reviewer", "lens", "groups": {"RGX": {"vote", ...}, "W22": {...}, "W26": {...}}, ...}
    overrides_scope.csv   the matches the reviewer confirms: feed_key, stage0_match_id and the eighteen values it
                          derived (w_ace ... l_bpFaced, as stage0_build.OVERRIDE_COUNTS names them)
    exchanges_scope.csv   the exchanges it confirms: source_file, source_row
    swaps_scope.csv       the service-game swaps it confirms (service_games.py; group SVX): source_file, source_row

Writes, in data/studies/rg_first_serve_recount/followup/confirmed/:
    confirmed_overrides.csv     the confirmed RG override rows (stage0_build's --box-overrides format, with source)
    confirmed_exchanges.csv     the confirmed exchange_box rows (row_corrections.csv's format)
    confirmed_swaps.csv         the confirmed exchange_svgms rows (fix SVX), in the same format
    not_unanimous_overrides.csv the proposed matches short of unanimity, with each reviewer's word (confirmed, other
                                values, not listed): part of no candidate
    editions_after.csv          pooled first serves in, aces and double faults by edition and draw: the rows as read,
                                after the candidate, and RG's own
    consensus.json              votes, counts by group and edition, what was dropped, and the candidate's dry run
    candidate/                  the inputs of a candidate Stage 0 build:
        slam_box_overrides.csv            the decided table of 6 Oct with the confirmed RG rows appended
        corrections/row_corrections.csv   the decided table of 8 Oct with, appended, step 2's confirmed split rows of
                                          every match that takes no override, and the confirmed exchanges
        corrections/id_aliases.csv        the decided table, copied
    (stage0_build.py --box-overrides <candidate>/slam_box_overrides.csv --corrections-dir <candidate>/corrections)
Usage: ./python.sh src/eda/rg_first_serve_recount/consensus_followup.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402
from src.eda.rg_first_serve_recount import whole_box as WB  # noqa: E402

REVIEW = WB.OUT / "review"
OUT = WB.OUT / "confirmed"
REVIEWERS = ("R1-rederive", "R2-skeptic", "R3-referee")
OKEY = ["feed_key", "stage0_match_id"]
XKEY = ["source_file", "source_row"]
VALS = B.OVERRIDE_COUNTS


def canon(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Counts as whole numbers written without a decimal point, blank for missing."""
    df = df.copy()
    for c in cols:
        v = pd.to_numeric(df[c].astype(str).str.strip().replace({"": np.nan, "nan": np.nan, "None": np.nan}),
                          errors="coerce")
        df[c] = v.map(lambda x: "" if pd.isna(x) else str(int(x)))
    return df


def read(reviewer: str, name: str, key: list[str]) -> pd.DataFrame:
    f = pd.read_csv(REVIEW / reviewer / name, dtype=str, keep_default_na=False)
    f = f.apply(lambda s: s.str.strip())
    if "source_row" in f:
        f["source_row"] = pd.to_numeric(f["source_row"]).astype(int).astype(str)
    if f.duplicated(key).any():
        raise SystemExit(f"{reviewer}: a match named twice in {name}")
    return f


def year_of(feed_key: pd.Series) -> pd.Series:
    return feed_key.str.extract(r":(\d{4})/")[0].astype(int)


def editions_after(conf_ov: pd.DataFrame, split: pd.DataFrame) -> pd.DataFrame:
    """Pooled first serves in, aces and double faults per serve point, and player rows with a full box, by edition
    and draw of RG 2022-2026: the rows as read, after the candidate (a confirmed override takes RG's box; else step
    2's confirmed split where it has one; else the row), and RG's own statistics."""
    rows = pd.read_csv(WB.OUT / "whole_box_rows.csv")
    rows["source_row"] = rows["source_row"].astype(int)
    after = {f"after_{c}": rows[f"raw_{c}"].astype(float) for c in WB.NINE}
    over = rows["match_id"].isin(set(conf_ov["stage0_match_id"]))
    for c in WB.NINE:
        after[f"after_{c}"] = after[f"after_{c}"].where(~over, rows[f"off_{c}"])
    sp = split.copy()
    sp["source_row"] = sp["source_row"].astype(int)
    sp = sp[~sp["match_id"].isin(set(conf_ov["stage0_match_id"]))]
    for s in ("w", "l"):
        given = sp[sp[f"{s}_1stIn"].astype(str).str.strip().ne("")]
        key = given.set_index(["source_file", "source_row"])
        hit = rows.set_index(["source_file", "source_row"]).index.isin(key.index) & rows["raw_side"].eq(s).to_numpy()
        idx = pd.MultiIndex.from_frame(rows.loc[hit, ["source_file", "source_row"]])
        for c, col in (("first_in", "1stIn"), ("first_won", "1stWon"), ("second_won", "2ndWon")):
            after[f"after_{c}"].loc[hit] = pd.to_numeric(key.loc[idx, f"{s}_{col}"]).to_numpy()
    rows = rows.assign(**after)
    out = []
    for k, g in rows.groupby(["year", "tour", "draw"]):
        rec = dict(zip(["year", "tour", "draw"], k))
        for p in ("raw", "after", "off"):
            h = g[g[f"{p}_svpt"].notna() & g[f"{p}_first_in"].notna()]
            sv = h[f"{p}_svpt"].sum()
            rec.update({f"{p}_rows": int(len(h)), f"{p}_first_in_pct": round(100 * h[f"{p}_first_in"].sum() / sv, 2),
                        f"{p}_ace_pct": round(100 * h[f"{p}_ace"].sum() / sv, 2),
                        f"{p}_df_pct": round(100 * h[f"{p}_df"].sum() / sv, 2)})
        out.append(rec)
    return pd.DataFrame(out)


def main() -> int:
    prop = canon(pd.read_csv(WB.OUT / "proposed_overrides.csv", dtype=str, keep_default_na=False), VALS)
    pex = pd.read_csv(WB.OUT / "proposed_exchanges.csv", dtype=str, keep_default_na=False)
    pex["source_row"] = pd.to_numeric(pex["source_row"]).astype(int).astype(str)
    prop["group"] = np.where(year_of(prop["feed_key"]).eq(2026), "W26", "W22")
    sw_path = WB.OUT / "service_games" / "proposed_swaps.csv"
    psw = pd.read_csv(sw_path, dtype=str, keep_default_na=False) if sw_path.exists() else pd.DataFrame(columns=XKEY)
    psw["source_row"] = pd.to_numeric(psw["source_row"]).astype("Int64").astype(str)
    report: dict = {"proposed_overrides": prop["group"].value_counts().to_dict(), "proposed_exchanges": int(len(pex)),
                    "proposed_swaps": int(len(psw)), "per_reviewer": {}}
    agreed_ov, agreed_ex, agreed_sw = prop[OKEY], pex[XKEY], psw[XKEY]
    said = prop[OKEY + ["group", "source", "winner_name", "loser_name"]].copy()     # each reviewer's word per match
    for r in REVIEWERS:
        verdict = json.loads((REVIEW / r / "verdict.json").read_text(encoding="utf-8"))
        so = canon(read(r, "overrides_scope.csv", OKEY), VALS)
        se = read(r, "exchanges_scope.csv", XKEY)
        m = prop.merge(so[OKEY + VALS], on=OKEY, how="left", suffixes=("", "_r"))     # against the full proposal
        same = np.all([m[c].eq(m[f"{c}_r"]) for c in VALS], axis=0)
        named = m[f"{VALS[0]}_r"].notna()
        report["per_reviewer"][r] = {
            "groups": {g: v.get("vote") for g, v in (verdict.get("groups") or {}).items()},
            "overrides_named": int(len(so)), "of_proposed_with_the_same_values": m[same]["group"].value_counts().to_dict(),
            "named_with_other_values": int((named & ~same).sum()),
            "outside_the_proposal": int(len(so.merge(prop[OKEY], on=OKEY, how="left", indicator=True)
                                            .query("_merge == 'left_only'"))),
            "exchanges_confirmed": int(len(se.merge(pex[XKEY], on=XKEY)))}
        agreed_ov = agreed_ov.merge(m.loc[same, OKEY], on=OKEY)                     # the running intersections
        agreed_ex = agreed_ex.merge(se[XKEY], on=XKEY)
        ss = read(r, "swaps_scope.csv", XKEY) if (REVIEW / r / "swaps_scope.csv").exists() \
            else pd.DataFrame(columns=XKEY)
        agreed_sw = agreed_sw.merge(ss[XKEY], on=XKEY)
        report["per_reviewer"][r]["swaps_confirmed"] = int(len(ss.merge(psw[XKEY], on=XKEY)))
        report["per_reviewer"][r]["swaps_outside_the_proposal"] = int(len(ss) - len(ss.merge(psw[XKEY], on=XKEY)))
        said[r] = np.where(same, "confirmed", np.where(named, "other values", "not listed"))
    conf_ov = prop.merge(agreed_ov, on=OKEY)
    conf_ex = pex.merge(agreed_ex, on=XKEY)
    dropped = prop.merge(agreed_ov, on=OKEY, how="left", indicator=True).query("_merge == 'left_only'")
    report.update({
        "confirmed_overrides": conf_ov["group"].value_counts().to_dict(),
        "confirmed_overrides_by_year_and_source": conf_ov.assign(year=year_of(conf_ov["feed_key"]))
        .groupby(["year", "source"]).size().rename("matches").reset_index().to_dict("records"),
        "dropped_overrides": dropped["group"].value_counts().to_dict(),
        "dropped_override_matches": dropped["stage0_match_id"].tolist()[:400],
        "confirmed_exchanges": conf_ex[["match_id", "winner_name", "loser_name"]].to_dict("records")})
    OUT.mkdir(parents=True, exist_ok=True)
    conf_ov.drop(columns="group").reindex(columns=WB.OV_COLUMNS).to_csv(OUT / "confirmed_overrides.csv", index=False)
    conf_ex.to_csv(OUT / "confirmed_exchanges.csv", index=False)
    conf_sw = psw.merge(agreed_sw, on=XKEY)
    conf_sw.to_csv(OUT / "confirmed_swaps.csv", index=False)
    tid = conf_sw["match_id"].str.split("|").str[1] if len(conf_sw) else pd.Series(dtype=str)
    report["confirmed_swaps"] = int(len(conf_sw))
    report["confirmed_swaps_by_slam_year"] = (pd.DataFrame({"slam": tid.str.endswith("-580").map({True: "AO", False: "RG"}),
                                                            "year": tid.str[:4]}).value_counts().sort_index()
                                              .rename("matches").reset_index().to_dict("records") if len(conf_sw) else [])
    report["dropped_swaps"] = int(len(psw) - len(conf_sw))
    # the proposed matches short of unanimity, with each reviewer's word: not part of any candidate
    short = said[~said.set_index(OKEY).index.isin(agreed_ov.set_index(OKEY).index)].copy()
    short["confirmed_by"] = short[list(REVIEWERS)].eq("confirmed").sum(axis=1)
    short.to_csv(OUT / "not_unanimous_overrides.csv", index=False)
    report["not_unanimous"] = short.groupby(["group", "confirmed_by"] + list(REVIEWERS)).size() \
        .rename("matches").reset_index().to_dict("records")

    # the candidate's inputs: the decided tables plus the confirmed rows; step 2's split rows stay for the matches
    # that take no override (candidate_tables leaves out those of overridden matches)
    split = pd.read_csv(S.STUDY / "confirmed" / "confirmed_corrections.csv", dtype=str, keep_default_na=False)
    ov, rc = WB.candidate_tables(conf_ov.drop(columns="group").reindex(columns=WB.OV_COLUMNS), conf_ex, split,
                                 conf_sw)
    cand = OUT / "candidate"
    (cand / "corrections").mkdir(parents=True, exist_ok=True)
    ov.to_csv(cand / "slam_box_overrides.csv", index=False)
    rc.to_csv(cand / "corrections" / "row_corrections.csv", index=False)
    shutil.copy2(K.ID_ALIASES, cand / "corrections" / "id_aliases.csv")
    kept = split[~split["match_id"].isin(set(conf_ov["stage0_match_id"]))]
    report["candidate"] = {
        "folder": cand.relative_to(ROOT).as_posix() if cand.is_relative_to(ROOT) else cand.as_posix(),
        "override_rows": {"decided": int((ov["box_source"] != "rolandgarros").sum()),
                          "rolandgarros": int((ov["box_source"] == "rolandgarros").sum())},
        "correction_rows": {"decided": int(len(pd.read_csv(K.ROW_CORRECTIONS))),
                            "step2_split_rows_kept": kept["fix"].value_counts().to_dict(),
                            "step2_split_rows_left_to_the_overrides": int(len(split) - len(kept)),
                            "exchanges": int(len(conf_ex)), "service_game_swaps": int(len(conf_sw))},
        "sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (B.DECIDED_OVERRIDES, K.ROW_CORRECTIONS, K.ID_ALIASES,
                             S.STUDY / "confirmed" / "confirmed_corrections.csv")}}
    ed = editions_after(conf_ov, split)
    ed.to_csv(OUT / "editions_after.csv", index=False)
    report["editions_after"] = ed.to_dict("records")
    report["dry_run"] = WB.dry_run(ov, rc)
    (OUT / "consensus.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "dropped_override_matches"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
