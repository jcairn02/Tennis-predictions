"""R3-referee, group SVS: service games set from the score where they are blank, zero or wrong without being an
exchange (set_svgms, rule E8).

For every row of followup/service_games/proposed_sets.csv, from my own tables (svx.py, svx_addendum.py runs):
  * my class, my proof of the first server (the stricter test), my truth (the score's alternation from that server),
    MatchBeats' own completed non-tiebreak games, and the independent records (Court Vision where it holds the match:
    RG 2019-2024 and AO 2020-2024, a tiebreak counted only where both players serve; the hand charts);
  * the guards the operation checks: the row's serve points (w_svpt, l_svpt) and the service games it replaces
    ("value", "<w>/<l>", blank for a missing count), against the raw rows read with Stage 0's loader;
  * the consistency test (R2's identity): each player's games won outside tiebreaks = service games - breaks
    conceded + breaks made, breaks from the row's own break points (faced - saved), for my truth and for the row;
  * for a "fill", whether the other eight counts are present; for an "other", which convention, if any, the row's
    counts follow (tiebreak games counted for their first server; the score read as if the winner served first; the
    unfinished game of a retirement; an equal split).
Writes svs_rows.csv and svs_summary.json into data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402
from addendum import alternation  # noqa: E402

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

EIGHT = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "bpSaved", "bpFaced"]


def games_outside_tiebreaks(score: str) -> tuple[float, float]:
    """(winner, loser) games won in the score, the deciding game of a tiebreak set taken from its winner."""
    sets, _ = B.tokens_of(str(score or ""))
    w = l = 0
    for a, b, tb, br in sets:
        if br:
            continue
        w, l = w + a, l + b
        if B.is_tiebreak(a, b, tb, br, False) and B.set_complete(a, b, tb, br, False):
            if a > b:
                w -= 1
            else:
                l -= 1
    return float(w), float(l)


def with_tiebreaks(score: str, first_is_winner: bool) -> tuple[float, float]:
    """Service games counting each tiebreak game for the player who serves its first point (the slot's server)."""
    sets, _ = B.tokens_of(str(score or ""))
    slot, w, l = 0, 0, 0
    for a, b, tb, br in sets:
        if br:
            slot += 1
            continue
        for _ in range(a + b):
            if (slot % 2 == 0) == first_is_winner:
                w += 1
            else:
                l += 1
            slot += 1
    return float(w), float(l)


def main() -> int:
    ps = pd.read_csv(F.FOLLOW / "service_games" / "proposed_sets.csv", dtype=str, keep_default_na=False)
    ps["key"] = F.rowkey(ps["source_file"], ps["source_row"])
    # my tables of classes and records
    parts = []
    r1 = pd.read_csv(F.OUT / "svx_ref_rows.csv", low_memory=False)          # AO 2025, RG 2019-2026 (with referees)
    parts.append(r1)
    for f in ("svx_add_rows.csv", "svx_add2_rows.csv"):
        parts.append(pd.read_csv(F.OUT / f, low_memory=False))
    mine = pd.concat(parts, ignore_index=True).drop_duplicates("key").set_index("key")
    # raw rows: serve points, break points, the counts replaced
    raws = [pd.read_parquet(F.OUT / f) for f in ("sub_raw.parquet", "svx_add_raw.parquet", "svx_add2_raw.parquet")]
    raw = pd.concat(raws, ignore_index=True)
    raw["key"] = F.rowkey(raw["_source_file"], raw["_row"])
    raw = raw.drop_duplicates("key").set_index("key")
    num = lambda v: pd.to_numeric(str(v).strip() if v is not None else "", errors="coerce")
    out = []
    for r in ps.to_dict("records"):
        k = r["key"]
        m = mine.loc[k] if k in mine.index else None
        x = raw.loc[k] if k in raw.index else None
        rec = {"key": k, "match_id": r["match_id"], "round": r["round"], "winner_name": r["winner_name"],
               "loser_name": r["loser_name"], "value": r["value"], "prop_w": num(r["w_SvGms"]), "prop_l": num(r["l_SvGms"]),
               "guard_w_svpt": num(r["w_svpt"]), "guard_l_svpt": num(r["l_svpt"]),
               "in_my_tables": m is not None, "in_raw": x is not None}
        if m is None or x is None:
            out.append(rec)
            continue
        rec.update({"event": m["event"], "season": int(m["season"]), "score": m["score"], "status": m["status_s0"],
                    "my_cls": m["my_cls"], "proven": bool(m["proven"]) if pd.notna(m["proven"]) else False,
                    "first_side": m["first_side"], "true_w": m["true_w"], "true_l": m["true_l"],
                    "mb_w": m["mb_w"], "mb_l": m["mb_l"], "mb_whole": m.get("mb_whole")})
        for ref in ("cv", "mcp"):
            for c in ("holds", "reading", "first_agrees", "w", "l"):
                rec[f"{ref}_{c}"] = m.get(f"{ref}_{c}")
        rw, rl = num(x["w_SvGms"]), num(x["l_SvGms"])
        rec.update({"row_w": rw, "row_l": rl, "row_w_svpt": num(x["w_svpt"]), "row_l_svpt": num(x["l_svpt"])})
        val = f"{'' if pd.isna(rw) else int(rw)}/{'' if pd.isna(rl) else int(rl)}"
        rec["value_guard_ok"] = val == r["value"]
        rec["svpt_guard_ok"] = rec["row_w_svpt"] == rec["guard_w_svpt"] and rec["row_l_svpt"] == rec["guard_l_svpt"]
        rec["values_equal_my_truth"] = rec["prop_w"] == rec["true_w"] and rec["prop_l"] == rec["true_l"]
        rec["other_eight_present"] = all(pd.notna(num(x[f"{s}_{c}"])) for s in ("w", "l") for c in EIGHT)
        # the consistency test
        gw, gl = games_outside_tiebreaks(m["score"])
        bcw = num(x["w_bpFaced"]) - num(x["w_bpSaved"])
        bcl = num(x["l_bpFaced"]) - num(x["l_bpSaved"])
        def consistent(sw, sl):
            if any(pd.isna(v) for v in (sw, sl, bcw, bcl)):
                return None
            return bool(gw == sw - bcw + bcl and gl == sl - bcl + bcw)
        rec["games_w_outside_tb"], rec["games_l_outside_tb"], rec["breaks_w"], rec["breaks_l"] = gw, gl, bcw, bcl
        rec["consistent_truth"] = consistent(rec["true_w"], rec["true_l"])
        rec["consistent_row"] = consistent(rw, rl) if not (rw == 0 and rl == 0) else False
        # which convention an "other" row follows
        conv = []
        fs = m["first_side"]
        if isinstance(fs, str) and pd.notna(rw) and pd.notna(rl) and not (rw == 0 and rl == 0):
            if (rw, rl) == with_tiebreaks(m["score"], fs == "w"):
                conv.append("tiebreaks counted")
            if (rw, rl) == with_tiebreaks(m["score"], fs != "w"):
                conv.append("tiebreaks counted, served first exchanged")
            if (rw, rl) == alternation(m["score"], True) and fs == "l":
                conv.append("as if the winner served first")
            if (rw, rl) == alternation(m["score"], False) and fs == "w":
                conv.append("as if the loser served first")
            if rw == rl:
                conv.append("equal split")
            if rw + rl == rec["true_w"] + rec["true_l"] + 1 and m["status_s0"] == "retired":
                conv.append("unfinished game counted")
            if rw + rl < rec["true_w"] + rec["true_l"] - 1:
                conv.append("total short")
            if rw + rl > rec["true_w"] + rec["true_l"] + 1:
                conv.append("total long")
        rec["row_convention"] = "; ".join(conv)
        rec["kind"] = "fill" if r["value"] in ("/", "0/0") or (pd.isna(rw) or pd.isna(rl)) else "other"
        out.append(rec)
    d = pd.DataFrame(out)
    d.to_csv(F.OUT / "svs_rows.csv", index=False)
    smry = {
        "proposed": int(len(d)), "found_in_my_tables": int(d["in_my_tables"].sum()), "in_raw": int(d["in_raw"].sum()),
        "by_kind": d["kind"].value_counts().to_dict(),
        "by_event_season": d.groupby(["event", "season"]).size().rename("rows").reset_index().astype(str).to_dict("records"),
        "my_class": d["my_cls"].value_counts().to_dict(), "proven": int(d["proven"].sum()),
        "values_equal_my_truth": int(d["values_equal_my_truth"].sum()),
        "value_guard_ok": int(d["value_guard_ok"].sum()), "svpt_guard_ok": int(d["svpt_guard_ok"].sum()),
        "consistent_truth": d["consistent_truth"].value_counts(dropna=False).to_dict(),
        "consistent_row_other": d.loc[d["kind"].eq("other"), "consistent_row"].value_counts(dropna=False).to_dict(),
        "fill_other_eight_present": int(d.loc[d["kind"].eq("fill"), "other_eight_present"].sum()),
        "mb_equals_truth": int((d["mb_w"].eq(d["true_w"]) & d["mb_l"].eq(d["true_l"])).sum()),
        "other_conventions": d.loc[d["kind"].eq("other"), "row_convention"].value_counts().to_dict(),
        "referees": {ref: {"held": int(d[f"{ref}_holds"].fillna(False).astype(bool).sum()),
                           "readings": d.loc[d[f"{ref}_holds"].fillna(False).astype(bool), f"{ref}_reading"]
                           .value_counts().to_dict(),
                           "first_agrees": d.loc[d[f"{ref}_holds"].fillna(False).astype(bool), f"{ref}_first_agrees"]
                           .astype(str).value_counts().to_dict()} for ref in ("cv", "mcp")},
    }
    (F.OUT / "svs_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
