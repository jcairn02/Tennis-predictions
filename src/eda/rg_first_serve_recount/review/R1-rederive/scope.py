"""R1-rederive: my scope (the sides I confirm) with the values I derived, from my own tables only.

A side of a Sackmann row of RG 2022-2025 or Paris 2024 is confirmed when all hold:
  T1  the link is verified: both players by name (married names and transliterations reviewed by hand), the games of
      every set (a retirement's unplayed 0-0 set aside, tiebreak notation aside) and the winner agree with the record;
  T2  the official record passes its own checks for both players (RG: the denominators of "win on 1st/2nd serve" are
      first serves in and serve points - first serves in, receiving points' denominator is the opponent's serve points,
      total points won = serve + return points won, counts in order; Olympics: OFFICIAL, PTS_WON_SERVE = 1st + 2nd
      won over the serve points, 2ND_SERVE attempts = serve points - first serves in);
  T3  class A ("split") or B ("split_other"), by my own comparison: serve points and serve points won equal, the
      split (1stIn, 1stWon, 2ndWon) differs; B: an ace, double-fault or break-point count differs too;
  T4  the venue's point-by-point record (RG MatchBeats, my recount; Olympic play-by-play, my recount) contradicts the
      official split for neither player of the match: where it holds every serve point of a player its split equals
      the official one; where it holds part, none of its four cells (first serve won / lost, second serve won / lost)
      exceeds the official cell. A failure drops both sides of the match;
  T5  for '-' and '0' sides (the direction opposite to the named fault) the point record itself shows Sackmann's split
      impossible: one of its four cells holds more points than Sackmann's cell (always true where it is complete and
      agrees with the official split, which differs from Sackmann's on the same serve points).
The values written are the official record's first serves in, first-serve points won and second-serve points won.

Writes scope.csv (source_file, source_row, side, first_in, first_won, second_won, fix, notes) and scope_all.csv (every
A/B side with each test). Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/scope.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive"
WORK = HERE / "work"


def cells(df: pd.DataFrame, p: str) -> dict[str, pd.Series]:
    fi, fw, sw, sv = df[f"{p}first_in"], df[f"{p}first_won"], df[f"{p}second_won"], df[f"{p}svpt"]
    return {"fw": fw, "fl": fi - fw, "sw": sw, "sl": sv - fi - sw}


def main() -> None:
    d = pd.read_csv(HERE / "sides.csv", keep_default_na=False, na_values=[""], dtype={"rec_id": str})
    for c in ("rec_checks", "games_agree"):
        d[c] = d[c].astype(str).eq("True")
    d = d[(d["event"].eq("RG") & d["year"].between(2022, 2025)) | d["event"].eq("OG")].copy()
    lr = pd.read_csv(HERE / "links_rg.csv", keep_default_na=False, na_values=[""])
    lo = pd.read_csv(HERE / "links_ol.csv", keep_default_na=False, na_values=[""])

    # ---- T1: the link. Games agree except a retirement's trailing 0-0 set and tiebreak notation; names reviewed.
    def games_ok_rg(r) -> bool:
        if bool(r["games_agree"]):
            return True
        rg = " ".join(t for t in str(r["rg_games"]).split() if t != "0-0")
        sk = " ".join(t.split("(")[0] for t in str(r["sack_score"]).split() if t[0].isdigit())
        return rg == sk
    lr["games_ok"] = lr.apply(games_ok_rg, axis=1)
    lr["link_ok"] = lr["games_ok"] & lr["rg_winner_flag_agrees"].astype(str).eq("True") & \
        lr["sim_w"].ge(0.0) & lr["sim_l"].ge(0.0)
    # every name pair below 1 was reviewed by hand (links_rg.csv): married names, transliterations, nicknames, and two
    # Sackmann identity slips on the right match (Eduardo Nava for Emilio Nava, RG 2023; "T. Farquhar" for Thomas
    # Faurel, RG 2024 QM126); the opponent, the games and the winner agree on every one.
    def games_ok_ol(r) -> bool:
        import re as _re
        a = [(int(m.group(1)), int(m.group(2))) for m in
             (_re.match(r"^(\d+)-(\d+)", t) for t in str(r["sack_score"]).split()) if m]
        b = [(int(m.group(1)), int(m.group(2))) for m in
             (_re.match(r"^\s*(\d+)(?:\(\d+\))?-(\d+)", s) for s in str(r["ol_final_result"]).split(",")) if m]
        return a == b
    lo["games_ok"] = lo.apply(games_ok_ol, axis=1)
    # names: every pair below 1 reviewed by hand (WANG Xinyu = Xin Yu Wang); the walkover Struff-Moutet has no box
    lo["link_ok"] = lo["games_ok"] & lo["sim_w"].ge(0.5) & lo["sim_l"].ge(0.5)
    link_ok = pd.concat([lr[["source_file", "source_row", "link_ok"]], lo[["source_file", "source_row", "link_ok"]]])
    link_ok = link_ok.dropna(subset=["source_file"])
    link_ok["source_row"] = link_ok["source_row"].astype(int)
    d = d.merge(link_ok, on=["source_file", "source_row"], how="left")
    d["T1"] = d["link_ok"].fillna(False).astype(bool)
    d["T2"] = d["rec_checks"]
    d["T3"] = d["cls"].isin(["split", "split_other"])

    # ---- T4: the point record against the official split
    oc, mc, sc = cells(d, "o_"), cells(d, "m_"), cells(d, "s_")
    has_m = d["m_svpt"].notna() & d["m_svpt"].gt(0)
    full = has_m & d["m_svpt"].eq(d["o_svpt"])
    part = has_m & d["m_svpt"].lt(d["o_svpt"])
    agree_full = d["m_first_in"].eq(d["o_first_in"]) & d["m_first_won"].eq(d["o_first_won"]) & \
        d["m_second_won"].eq(d["o_second_won"])
    m_within_o = pd.concat([mc[k] <= oc[k] for k in mc], axis=1).all(axis=1)    # a part record inside the official
    o_within_m = pd.concat([oc[k] <= mc[k] for k in mc], axis=1).all(axis=1)    # the official inside a longer record
    d["m_state"] = np.select(
        [~has_m, full & agree_full, full, part & m_within_o, part, o_within_m],
        ["none", "full_agrees", "full_contradicts", "part_within", "part_exceeds", "over_within"], "over_other")
    # RG 2025: the key statistics block (same file) where it holds every serve point of the side
    k_full = d["k_svpt"].eq(d["o_svpt"]) if "k_svpt" in d else pd.Series(False, index=d.index)
    k_agree = k_full & d["k_first_in"].eq(d["o_first_in"]) & d["k_first_won"].eq(d["o_first_won"]) & \
        d["k_second_won"].eq(d["o_second_won"])
    d["k_state"] = np.select([k_full & k_agree, k_full], ["full_agrees", "full_contradicts"], "none")
    side_bad = d["m_state"].isin(["full_contradicts", "part_exceeds", "over_other"]) | d["k_state"].eq("full_contradicts")
    # a full point record contradicting the official split anywhere in the match drops the whole match
    match_bad = d.groupby(["source_file", "source_row"])["m_state"].transform(lambda s: s.eq("full_contradicts").any())
    d["T4"] = ~side_bad & ~match_bad
    # ---- T5: the point record shows Sackmann's split impossible ('-' and '0' sides)
    kc = cells(d, "k_")
    exceeds_sack = (pd.concat([mc[k] > sc[k] for k in mc], axis=1).any(axis=1) & has_m) | \
        (pd.concat([kc[k] > sc[k] for k in kc], axis=1).any(axis=1) & k_full)
    d["point_record_refutes_sackmann"] = exceeds_sack
    d["T5"] = np.where(d["sign"].isin(["-", "0"]), exceeds_sack, True)
    d["confirmed"] = d[["T1", "T2", "T3", "T4", "T5"]].all(axis=1)

    # radar note (RG 2023-2025)
    rad = pd.read_csv(HERE / "radar_sides.csv", keep_default_na=False, na_values=[""])
    rad = rad[["source_file", "source_row", "side", "n2_fault", "radar_rules_out_sack"]]
    d = d.merge(rad, on=["source_file", "source_row", "side"], how="left")

    # fix id: the match row's class (a row with a B side among its candidate sides is B), by event
    rowB = d[d["T3"]].groupby(["source_file", "source_row"])["cls"].apply(lambda s: (s == "split_other").any())
    d["row_B"] = [bool(rowB.get((f, r), False)) for f, r in zip(d["source_file"], d["source_row"])]
    d["fix"] = np.where(d["event"].eq("RG"), "RGFS", "OGFS") + np.where(d["row_B"], "B", "A")
    d["side_class"] = np.where(d["cls"].eq("split"), "A", np.where(d["cls"].eq("split_other"), "B", d["cls"])) + \
        d["sign"].where(d["T3"], "")
    d.to_csv(HERE / "scope_all.csv", index=False)

    s = d[d["confirmed"]].copy()
    def note(r) -> str:
        parts = [f"class {r['side_class']}", f"Sackmann {int(r['s_first_in'])}/{int(r['s_first_won'])}/"
                 f"{int(r['s_second_won'])}", f"point record {r['m_state']}"]
        if r["radar_rules_out_sack"] is True or str(r["radar_rules_out_sack"]) == "True":
            parts.append("radar-measured first-serve faults exceed Sackmann's second serves")
        if r["cls"] == "split_other":
            other = [k for k in ("ace", "df", "bp_faced", "bp_saved") if r[f"s_{k}"] != r[f"o_{k}"]]
            parts.append("left as is: " + ",".join(f"{k} {int(r[f's_{k}'])} (official {int(r[f'o_{k}'])})"
                                                   for k in other))
        return "; ".join(parts)
    def fmt(x) -> str:
        return "blank" if pd.isna(x) else str(int(x))
    def note(r) -> str:  # noqa: F811  (blank-safe)
        parts = [f"class {r['side_class']}", f"Sackmann {fmt(r['s_first_in'])}/{fmt(r['s_first_won'])}/"
                 f"{fmt(r['s_second_won'])}", f"point record {r['m_state']}"]
        if str(r["radar_rules_out_sack"]) == "True":
            parts.append("radar-measured first-serve faults exceed Sackmann's second serves")
        if r["cls"] == "split_other":
            other = [k for k in ("ace", "df", "bp_faced", "bp_saved") if not (r[f"s_{k}"] == r[f"o_{k}"])]
            parts.append("left as is: " + ",".join(f"{k} {fmt(r[f's_{k}'])} (official {fmt(r[f'o_{k}'])})"
                                                   for k in other))
        return "; ".join(parts)
    s["notes"] = s.apply(note, axis=1)
    out = s[["source_file", "source_row", "side", "o_first_in", "o_first_won", "o_second_won", "fix", "notes"]].rename(
        columns={"o_first_in": "first_in", "o_first_won": "first_won", "o_second_won": "second_won"})
    for c in ("first_in", "first_won", "second_won"):
        out[c] = out[c].astype(int)
    out = out.sort_values(["source_file", "source_row", "side"])
    out.to_csv(HERE / "scope.csv", index=False)

    cand = d[d["T3"]]
    print("A/B sides:", len(cand), "| confirmed:", len(s))
    print(pd.crosstab([cand["event"], cand["side_class"]], cand["confirmed"], margins=True))
    print("\nfailed tests among A/B sides:", {t: int((~cand[t].astype(bool)).sum()) for t in ("T1", "T2", "T4", "T5")})
    print(cand[~cand["confirmed"]][["event", "year", "key", "side", "name", "side_class", "m_state", "T1", "T2", "T4",
                                    "T5", "s_first_in", "o_first_in", "m_first_in", "s_svpt", "m_svpt"]].to_string())
    print("\nby fix id (sides):", out["fix"].value_counts().to_dict(), "| match rows:",
          out.drop_duplicates(["source_file", "source_row"])["fix"].value_counts().to_dict())


if __name__ == "__main__":
    main()
