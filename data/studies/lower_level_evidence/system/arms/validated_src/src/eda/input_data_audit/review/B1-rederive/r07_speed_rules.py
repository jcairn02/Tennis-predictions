"""B1-rederive reviewer: F14-F16, the exact rule and its fallback (read-only).

Rules compared (a flagged record is 'not a candidate', as the panel's mislink rules):
  R_above : key statistic, y_raw >  spd_max
  R_at    : key statistic, y_raw >= spd_max, n >= 10
  R_w1    : key statistic, y_raw >= spd_max - 1, n >= 10
For every player-match whose panel-chosen record is flagged, the fallback is recomputed with EVERY flagged record of
the rule excluded at once (and the panel's own invalid records excluded), by the panel's ordering. The fallback is
compared with the player's norm (median of his other use rows within 365 days) and checked for being another copy of
the same key statistic (equal y_raw from the other key-statistic source).
F16: same-source pairs of identical (y_raw, n, spd2_raw, spd_max) on two matches of one player, with every other
record of both matches; and both sides of one match with identical (y_raw, n).
Writes speed_rule_effects.csv, speed_f16_pairs.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
SP = ROOT / "data/studies/serve_speed_tabpfn"
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 600)

rec = pd.read_parquet(SP / "speed_records.parquet")
pan = pd.read_parquet(SP / "speed_panel.parquet")
r = rec.copy()
r["rid"] = np.arange(len(r))
key = pan.set_index(["match_id", "side"])
r = r.merge(pan[["match_id", "side", "source", "source_key", "use"]].assign(chosen=True),
            on=["match_id", "side", "source", "source_key"], how="left")
r["chosen"] = r.chosen.fillna(False).astype(bool)
r["use"] = r["use"].fillna(False).astype(bool)
pinfo = pan[["match_id", "side", "player_id", "tdate", "level", "tour"]]
r = r.merge(pinfo, on=["match_id", "side"], how="left")

# point-mean records at / within 1 of their max
pm = r[r.kind.eq("point_mean") & (r.y_raw >= r.spd_max - 1)]
print("point-mean records with mean >= max - 1:", len(pm))
print(pm[["match_id", "side", "source", "y_raw", "n", "spd_max", "valid", "invalid_reason", "chosen", "use"]].to_string())

ks = r.kind.eq("keystat")
RULES = {"R_above": ks & (r.y_raw > r.spd_max),
         "R_at": ks & (r.y_raw >= r.spd_max) & (r.n >= 10),
         "R_w1": ks & (r.y_raw >= r.spd_max - 1) & (r.n >= 10)}
pu = pan[pan.use][["match_id", "side", "player_id", "tdate", "y"]]


def norm(pid, mid, td):
    if pd.isna(pid) or pd.isna(td):
        return np.nan
    o = pu[pu.player_id.eq(pid) & pu.match_id.ne(mid) & (pu.tdate - td).abs().le(365)]
    return float(o.y.median()) if len(o) else np.nan


SRC_RANK = {**{s: i for i, s in enumerate(["infosys_slams", "sirgenkii", "infosys", "slam_tracking", "slamtracker",
                                            "slam_pbp"])}, "mantennisdata": 0, "handoff_ks": 1, "ausopen_mc": 0}


def pick(cands, slam):
    k = np.select([cands.kind.eq("point_mean"), cands.kind.eq("keystat"), cands.kind.eq("mc_floor")],
                  [0 if slam else 1, 1 if slam else 0, 2], 9)
    nn = np.where(cands.kind.eq("point_mean"), -cands.n.fillna(0), 0)
    s = cands.source.map(SRC_RANK).fillna(9)
    return cands.assign(_k=k, _n=nn, _s=s).sort_values(["_k", "_n", "_s"]).iloc[0]


rows = []
for rule, mask in RULES.items():
    flagged = r[mask]
    print(f"\n== {rule}: {len(flagged)} records ({flagged.source.value_counts().to_dict()}); chosen {int(flagged.chosen.sum())},"
          f" chosen&use {int((flagged.chosen & flagged.use).sum())}; n<10 among them {int((flagged.n < 10).sum())}")
    hit = flagged[flagged.chosen][["match_id", "side"]].drop_duplicates()
    for mid, side in hit.itertuples(index=False):
        same = r[r.match_id.eq(mid) & r.side.eq(side) & r.linked]
        cur = same[same.chosen].iloc[0]
        cands = same[same.valid & ~same.rid.isin(flagged.rid)]
        slam = cur.level == "GS"
        nb = norm(cur.player_id, mid, cur.tdate)
        if len(cands):
            nx = pick(cands, slam)
            other_ks_copy = bool(nx.kind == "keystat" and nx.y_raw == cur.y_raw)
            rows.append({"rule": rule, "match_id": mid, "side": side, "player_id": cur.player_id, "cur_source": cur.source,
                         "cur_y_raw": cur.y_raw, "cur_n": cur.n, "cur_max": cur.spd_max, "cur_use": cur.use,
                         "norm": nb, "cur_minus_norm": cur.y - nb if cur.use else np.nan,
                         "fb_source": nx.source, "fb_kind": nx.kind, "fb_y": nx.y, "fb_n": nx.n, "fb_max": nx.spd_max,
                         "fb_minus_norm": nx.y - nb, "fb_same_ks_copy": other_ks_copy,
                         "fb_lowN": bool(nx.n < 10) if pd.notna(nx.n) else True})
        else:
            rows.append({"rule": rule, "match_id": mid, "side": side, "player_id": cur.player_id, "cur_source": cur.source,
                         "cur_y_raw": cur.y_raw, "cur_n": cur.n, "cur_max": cur.spd_max, "cur_use": cur.use, "norm": nb,
                         "cur_minus_norm": cur.y - nb if cur.use else np.nan, "fb_source": None})
eff = pd.DataFrame(rows)
eff.to_csv(OUT / "speed_rule_effects.csv", index=False)
for rule in RULES:
    e = eff[eff.rule.eq(rule)]
    u = e[e.cur_use]
    has = u.fb_source.notna()
    print(f"\n{rule}: player-matches whose chosen record is flagged {len(e)}; of them used now {len(u)}; "
          f"fallback exists {int(has.sum())} (of which another copy of the same KS: {int(u.fb_same_ks_copy.fillna(False).sum())}, "
          f"low n: {int(u.fb_lowN.fillna(False).sum())}); no fallback -> value dropped: {int((~has).sum())}")
    print(f"   |current - norm| median {u.cur_minus_norm.abs().median():.1f}, share>10 {(u.cur_minus_norm.abs() > 10).mean():.2f};"
          f" |fallback - norm| median {u.fb_minus_norm.abs().median():.1f}, share>10 {(u.fb_minus_norm.abs() > 10).mean():.2f}")
print("\nR_at/R_w1 fallbacks that are another KS copy or whose fallback is far from the norm:")
print(eff[(eff.rule.ne("R_above")) & eff.cur_use & (eff.fb_same_ks_copy.fillna(False) | (eff.fb_minus_norm.abs() > 10))]
      .to_string())
print("\nR_above fallbacks far from the norm (> 10):")
print(eff[eff.rule.eq("R_above") & eff.cur_use & (eff.fb_minus_norm.abs() > 10)].to_string())

# ---------- F16
blk = ["y_raw", "n", "spd2_raw", "spd_max"]
full = r[r[blk].notna().all(axis=1) & r.player_id.notna() & r.linked]
g = full.groupby(["source", "player_id"] + blk).match_id.transform("nunique")
same_src = full[g > 1].sort_values(["player_id", "source", "y_raw", "match_id"])
print("\nF16: same-source identical blocks on different matches of one player:", len(same_src), "records")
pairs = []
for (src, pid), grp in same_src.groupby(["source", "player_id"]):
    mids = sorted(set(grp.match_id))
    for mid in mids:
        allrec = r[r.match_id.eq(mid) & r.player_id.eq(pid) & r.linked]
        for x in allrec.itertuples():
            pairs.append({"pair_source": src, "player_id": pid, "match_id": mid, "tdate": x.tdate, "rec_source": x.source,
                          "source_key": x.source_key, "y_raw": x.y_raw, "n": x.n, "spd2_raw": x.spd2_raw,
                          "spd_max": x.spd_max, "valid": x.valid, "invalid_reason": x.invalid_reason,
                          "chosen": x.chosen, "use": x.use, "in_block": bool(((grp.match_id == mid)).any() and
                                                                            x.y_raw == grp.y_raw.iloc[0] and x.n == grp.n.iloc[0])})
pp = pd.DataFrame(pairs).drop_duplicates()
pp.to_csv(OUT / "speed_f16_pairs.csv", index=False)
print(pp.to_string())

# both sides of a match identical (y_raw, n), same source
two = r[r.linked & r.y_raw.notna() & r.n.notna()]
gg = two.groupby(["match_id", "source", "y_raw", "n"]).side.transform("nunique") > 1
sides = two[gg].sort_values(["match_id", "source", "side"])
print("\nboth sides identical (y_raw, n), same source:", sides.match_id.nunique(), "matches")
print(sides[["match_id", "side", "source", "source_key", "y_raw", "n", "spd2_raw", "spd_max", "valid", "chosen", "use"]].to_string())
