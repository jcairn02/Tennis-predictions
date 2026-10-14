"""B1-rederive reviewer: write the exact scope CSVs of the rows this reviewer confirms (read-only on all inputs).

Outputs (data/studies/input_data_audit/fixes/B1-rederive/):
  scope_F7.csv   Stage 0 player rows of the confirmed new ids, with the established id to alias them to
  scope_F8.csv   the 12 rows with ages in the thousands, with the F8b value (TML convention: (tdate - dob)/365.25, 3 dp)
  scope_F9.csv   the 182 Prague/Todi 2020-08-17 rows, with the recomputed age (Sackmann convention: floor to 0.1)
  scope_F11.csv  the reversed-average odds rows (Stage 1 match_id, td_file, td_row, workbook row) and the exchange
  scope_F12.csv  the Nottingham 2017 final
  scope_F13.csv  the three in-play-captured averages (contested exclusion: blank avg/max)
  scope_F14.csv  key-statistic records with mean > own max (any n) or mean >= own max - 1 (n >= 10)
  scope_F15.csv  men's records with mean >= 240
  scope_F16.csv  the copied blocks on the later match of the three pairs whose original is verified by point data
"""
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
S0 = ROOT / "data/studies/predictability_diagnostic"
SP = ROOT / "data/studies/serve_speed_tabpfn"

m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tour", "level", "tournament_name",
                                                             "tournament_date", "source", "source_file", "source_row",
                                                             "player_a_id", "player_b_id"])
p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "opponent_id", "side",
                                                                   "player_name", "age", "country", "rank"])
q = p.merge(m, on="match_id")
q["tdate"] = pd.to_datetime(q.tournament_date)

# ---------------- F7
CONFIRMED = {  # new id -> established id, with the decisive evidence
    "wta:315232": ("wta:201548", "WTA API id 315232 = Ajla Tomljanovic (AUS); 23 of its matches are in Stage 0 under wta:201548"),
    "wta:320319": ("wta:211713", "WTA API id 320319 = Jaqueline Cristian (ROU); 8 matches under wta:211713"),
    "wta:324261": ("wta:215035", "WTA API id 324261 = Dayana Yastremska (UKR); 22 matches under wta:215035"),
    "wta:330332": ("wta:223253", "WTA API id 330332 = Alexandra Eala (PHI); 8 matches under wta:223253"),
    "wta:322082": ("wta:214082", "WTA API id 322082 = Daria Kasatkina (RUS->AUS); 33 matches under wta:214082"),
    "wta:328897": ("wta:221236", "WTA API id 328897 = Polina Kudermetova (RUS->UZB); 3 matches under wta:221236"),
    "wta:328884": ("wta:222391", "WTA API id 328884 = Lois Boisson (FRA); 2 matches under wta:222391"),
    "wta:332718": ("wta:260765", "WTA API id 332718 = Alisa Oktiabreva (RUS); its 3 Rome 125 2025 matches are under wta:260765"),
    "wta:321837": ("wta:215386", "WTA player page 321837 = Vivian Wolff, born 8 Oct 1998 (= Sackmann dob of wta:215386), now USA"),
    "atpcode:M0VL": ("atp:149128", "TML ATP database M0VL dob 2006-01-07 = Sackmann dob of atp:149128; PRT = POR"),
    "atpcode:M0PF": ("atp:212827", "TML ATP database M0PF dob 2006-02-13 = Sackmann dob of atp:212827 (and of atp:210458, "
                                   "a second Sackmann id of the same person, left as is)"),
    "atpcode:C0UQ": ("atp:214346", "TML age 19.699 on 2026-09-07 implies dob 2006-12-26 = Sackmann dob of atp:214346 "
                                   "('Tran Quoc Cuong'); VNM = VIE"),
}
f7 = q[q.player_id.isin(CONFIRMED)].copy()
f7["established_id"] = f7.player_id.map(lambda x: CONFIRMED[x][0])
f7["evidence"] = f7.player_id.map(lambda x: CONFIRMED[x][1])
f7["new_id"] = f7["player_id"]
f7["also_replace_in"] = "stage0_match_players.opponent_id of the opponent's row; stage0_matches.player_a_id/player_b_id"
f7[["match_id", "player_id", "new_id", "side", "established_id", "player_name", "tournament_name", "tournament_date", "source",
    "source_file", "source_row", "evidence", "also_replace_in"]].sort_values(["new_id", "match_id"]) \
    .to_csv(OUT / "scope_F7.csv", index=False)
print("F7 scope rows:", len(f7), "pairs:", f7.new_id.nunique())
# opponent rows that point at the new ids, and matches table references
opp_rows = int(q.opponent_id.isin(CONFIRMED).sum())
mt_refs = int(m.player_a_id.isin(CONFIRMED).sum() + m.player_b_id.isin(CONFIRMED).sum())
print("  opponent_id references:", opp_rows, " matches-table references:", mt_refs)
# guard: after aliasing, no match has the same id on both sides
alias = {k: v[0] for k, v in CONFIRMED.items()}
pa = m.player_a_id.map(lambda x: alias.get(x, x))
pb = m.player_b_id.map(lambda x: alias.get(x, x))
print("  matches that would collapse to one id:", int((pa == pb).sum()))

# ---------------- dobs
dob = []
for tour in ("atp", "wta"):
    d = pd.read_parquet(ROOT / f"data/dump/players/sackmann_archive/{tour}/{tour}_players.parquet", columns=["player_id", "dob"])
    d["pid"] = tour + ":" + d.player_id.astype(str)
    dob.append(d)
dob = pd.concat(dob).drop_duplicates("pid").set_index("pid")
dob["dt"] = pd.to_datetime(dob.dob.astype(str), format="%Y%m%d", errors="coerce")

# ---------------- F8 / F8b
f8 = q[q.age.gt(100)].copy()
f8["established_id"] = f8.player_id.map(lambda x: alias.get(x, x))
f8["dob"] = f8.established_id.map(dob.dt)
f8["age_f8b"] = ((f8.tdate - f8.dob).dt.days / 365.25).round(3)
f8[["match_id", "player_id", "side", "player_name", "tournament_name", "tournament_date", "source_file", "source_row",
    "age", "established_id", "dob", "age_f8b"]].rename(columns={"age": "age_now"}).assign(age_f8="missing") \
    .sort_values(["player_name", "match_id"]).to_csv(OUT / "scope_F8.csv", index=False)
print("F8 rows:", len(f8), f8[["player_name", "age", "age_f8b"]].drop_duplicates().values.tolist())

# ---------------- F9
q["dob"] = q.player_id.map(dob.dt)
q["age_dob"] = (q.tdate - q.dob).dt.days / 365.25
f9 = q[q.tdate.eq(pd.Timestamp("2020-08-17")) & q.tour.eq("atp") & q.level.eq("CH")].copy()
f9 = f9[(f9.age - f9.age_dob).abs() > 0.15]
f9["age_new"] = np.floor(f9.age_dob * 10 + 1e-9) / 10
# the players' other Sackmann rows: is the dob consistent with them?
oth = q[q.player_id.isin(f9.player_id) & ~q.match_id.isin(f9.match_id) & q.source.eq("sackmann") & q.age.notna()]
dev = (oth.age - oth.age_dob).abs().groupby(oth.player_id).max()
print("F9 rows:", len(f9), " players:", f9.player_id.nunique(), " events:", f9.tournament_name.value_counts().to_dict())
print("  players' other Sackmann rows: max |age - age_dob| over players: max", round(dev.max(), 3),
      " players with other rows:", int(dev.notna().sum()), " > 0.15:", int((dev > 0.15).sum()))
print("  1-decimal convention check on those other rows: floor share",
      round(float(np.isclose(oth.age, np.floor(oth.age_dob * 10 + 1e-9) / 10).mean()), 4))
print("  shift applied (age_new - age_now): min", round((f9.age_new - f9.age).min(), 2), "max", round((f9.age_new - f9.age).max(), 2))
f9[["match_id", "player_id", "side", "player_name", "tournament_name", "tournament_date", "source_file", "source_row",
    "age", "dob", "age_new"]].rename(columns={"age": "age_now"}).sort_values(["tournament_name", "match_id", "side"]) \
    .to_csv(OUT / "scope_F9.csv", index=False)

# ---------------- odds
o = pd.read_parquet(S0 / "stage1_odds.parquet")
chk = pd.read_csv(OUT / "odds_candidate_rows.csv", low_memory=False)


def odds_rows(ids, extra):
    x = o[o.match_id.isin(ids)][["match_id", "tour", "year", "evaluation", "link", "td_file", "td_row", "td_winner",
                                 "td_loser", "avg_a", "avg_b", "max_a", "max_b", "ps_a", "ps_b", "b365_a", "b365_b",
                                 "p_avg_a", "p_ps_a"]].copy()
    x = x.merge(chk[["match_id", "_source_file", "_sheet", "_row"]].rename(
        columns={"_source_file": "workbook", "_sheet": "sheet", "_row": "workbook_row"}), on="match_id", how="left")
    for k, v in extra.items():
        x[k] = x.match_id.map(v)
    return x


F11_ROWS = {  # match_id -> (columns to exchange, in the audit's a07 'reversed' list?)
    "atp|2013-891|SF|atp:104386|atp:105379": ("avg,max", True),
    "atp|2016-540|F|atp:104918|atp:105683": ("avg,max", True),
    "wta|2025-822|F|wta:210722|wta:211817": ("avg", True),
    "wta|2022-2030|R32|wta:201603|wta:216146": ("avg", True),
    "atp|2010-560|SF|atp:103819|atp:104925": ("avg,max", False),
    "atp|2011-424|F|atp:104269|atp:105683": ("avg,max", False),
    "atp|2011-520|F|atp:103819|atp:104745": ("avg,max", False),
}
f11 = odds_rows(F11_ROWS, {"exchange": {k: v[0] for k, v in F11_ROWS.items()},
                           "in_audit_a07_list": {k: v[1] for k, v in F11_ROWS.items()}})
f11["p_avg_a_new"] = 1 - f11.p_avg_a
f11.to_csv(OUT / "scope_F11.csv", index=False)
print("F11 rows:", len(f11))
print(f11[["match_id", "evaluation", "exchange", "avg_a", "avg_b", "max_a", "max_b", "p_avg_a", "p_avg_a_new"]].to_string())

f12 = odds_rows(["wta|2017-1080|F|wta:202427|wta:202499"], {"exchange": {"wta|2017-1080|F|wta:202427|wta:202499":
                                                                         "avg,ps,max,b365"}})
f12["p_avg_a_new"] = 1 - f12.p_avg_a
f12["p_ps_a_new"] = 1 - f12.p_ps_a
f12.to_csv(OUT / "scope_F12.csv", index=False)
print("F12:", f12[["match_id", "avg_a", "avg_b", "p_avg_a", "p_avg_a_new"]].values.tolist())

F13_ROWS = ["atp|2022-421|R64|atp:105138|atp:106218", "atp|2022-520|R128|atp:105967|atp:124079",
            "atp|2013-560|R128|atp:104297|atp:105577"]
f13 = odds_rows(F13_ROWS, {"fix": {k: "blank avg_a, avg_b, max_a, max_b (p_avg_a missing, avg_coherent False)"
                                   for k in F13_ROWS}})
f13.to_csv(OUT / "scope_F13.csv", index=False)
print("F13 contested rows:", f13[["match_id", "evaluation", "avg_a", "avg_b", "max_a", "max_b", "ps_a", "ps_b",
                                   "b365_a", "b365_b", "p_avg_a"]].to_string())

# ---------------- speed
rec = pd.read_parquet(SP / "speed_records.parquet")
pan = pd.read_parquet(SP / "speed_panel.parquet")
rec = rec.merge(pan[["match_id", "side", "source", "source_key", "use"]].assign(panel_chosen=True),
                on=["match_id", "side", "source", "source_key"], how="left")
rec["panel_chosen"] = rec.panel_chosen.fillna(False).astype(bool)
rec["panel_use"] = rec["use"].fillna(False).astype(bool)
ks = rec.kind.eq("keystat")
f14m = ks & ((rec.y_raw > rec.spd_max) | ((rec.y_raw >= rec.spd_max - 1) & (rec.n >= 10)))
f14 = rec[f14m].copy()
f14["class"] = np.where(f14.y_raw > f14.spd_max, "above", np.where(f14.y_raw == f14.spd_max, "at", "within_1"))
dupgrp = rec[ks & rec.linked].groupby(["match_id", "side", "source"]).size()
f14["same_source_copies_of_player_match"] = [dupgrp.get((a, b, c), 0) for a, b, c in zip(f14.match_id, f14.side, f14.source)]
eff = pd.read_csv(OUT / "speed_rule_effects.csv")
e = eff[eff.rule.eq("R_w1")][["match_id", "side", "fb_source", "fb_y", "fb_n"]]
f14 = f14.merge(e, on=["match_id", "side"], how="left")
cols = ["match_id", "side", "source", "source_key", "kind", "tour_s0", "year_s0", "level_s0", "y_raw", "n", "spd2_raw",
        "spd_max", "class", "valid", "invalid_reason", "panel_chosen", "panel_use", "same_source_copies_of_player_match",
        "fb_source", "fb_y", "fb_n"]
f14[cols].sort_values(["class", "match_id", "side", "source"]).to_csv(OUT / "scope_F14.csv", index=False)
print("F14 records:", len(f14), f14["class"].value_counts().to_dict(), " by source", f14.source.value_counts().to_dict(),
      " chosen&use:", int((f14.panel_chosen & f14.panel_use).sum()), " already invalid:", int((~f14.valid).sum()),
      " records with a same-source sibling for the player-match:", int((f14.same_source_copies_of_player_match > 1).sum()))
used = f14[f14.panel_chosen & f14.panel_use]
print("  used player-matches:", len(used), " with fallback:", int(used.fb_source.notna().sum()),
      " fallback sources:", used.fb_source.value_counts().to_dict())
f15 = rec[rec.tour_s0.eq("atp") & (rec.y_raw >= 240)]
f15[["match_id", "side", "source", "source_key", "y_raw", "n", "spd_max", "panel_chosen", "panel_use"]] \
    .to_csv(OUT / "scope_F15.csv", index=False)
print("F15 records:", len(f15), " all in F14 scope:", bool(f15.set_index(["match_id", "side", "source", "source_key"]).index
                                                           .isin(f14.set_index(["match_id", "side", "source", "source_key"]).index).all()))
F16 = [("atp|2026-422|R64|atp:105807|atp:126094", "A", "mantennisdata", "2026-422-re44-cd85-R64",
        "copy of the block of atp|2022-337|R16 (126094); that match's Infosys point data: mean 195.2 (ceil 196), n 33, "
        "2nd 146.1 (ceil 147), max 215"),
       ("atp|2025-404|F|atp:207733|atp:208029", "B", "mantennisdata", "2025-404-d0co-r0dg-F",
        "copy of the block of atp|2024-329|R16 (208029; Infosys there: 192.0 (ceil 193), 2nd 165.1, max 214); the final's "
        "own point data (sirgenkii) reads mean 193.2 (ceil 194), max 213"),
       ("atp|2023-352|R64|atp:104755|atp:126205", "A", "mantennisdata", "2023-352-pl56-g628-R64",
        "copy of the block of atp|2022-429|R32 (126205), whose Infosys point data equal it exactly (193/47/154/221)"),
       ("atp|2023-352|R64|atp:104755|atp:126205", "A", "handoff_ks", "2023_352_MS044",
        "the handoff's copy of the same block on the same later match (must go too, or it becomes the fallback)")]
k16 = pd.DataFrame(F16, columns=["match_id", "side", "source", "source_key", "evidence"])
f16 = rec.merge(k16, on=["match_id", "side", "source", "source_key"])
assert len(f16) == 4
f16[["match_id", "side", "source", "source_key", "y_raw", "n", "spd2_raw", "spd_max", "valid", "panel_chosen", "panel_use",
     "evidence"]].to_csv(OUT / "scope_F16.csv", index=False)
print("F16 records:", len(f16))
print(f16[["match_id", "side", "source", "y_raw", "n", "spd2_raw", "spd_max", "panel_chosen", "panel_use"]].to_string())
