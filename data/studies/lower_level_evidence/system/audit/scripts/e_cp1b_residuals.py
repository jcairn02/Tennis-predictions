"""Role E (red team), CP1b, question 2: how much do C0_now's known identity residuals touch the model's frame players?

Residual classes (F_rule_data.md section 5 and "What it does not show"), per new-match player slot of C0_now:
  wrong   route "name_subset" (a fuller or shorter name) whose given name differs from the Stage 0 name's: the class F
          estimates at about 19 wrong rows plus 39 unsure. Counted in full (an upper bound).
  split   the identity repair moved the slot from the id the link chose (x1/x2) to another id holding fewer frozen
          matches (Coleman Wong's 32 to a one-match id): the frame player loses the new rows.
  merge   the repair moved a slot onto a frame player's id from another id (F's sample of 20 moves: 18 right, 2 unsure).
  relative  crosswalk entries whose names share the surname but not the given name, and men's entries sharing no name
          word (a reused source id): F's "about eight entries, about 280 rows". A heuristic superset.
For each class: the frame players touched (ids in the 67,226 frame matches), their affected new rows within 365 days
of one of their frame matches, and their frame matches with an affected new row in the 365 days before. Ids, names and
dates only. Writes audit/cp1b/residuals.json and residual_slots.csv.
"""
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[6]
D = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now"
REF = ROOT / "data/studies/current_best_model/reference_2026-10-08/frozen"
REF_S0 = REF / "tables/data/studies/predictability_diagnostic"
FRAME = REF / "instance/model_frame.parquet"
OUT = Path(__file__).resolve().parents[1] / "cp1b"
OUT.mkdir(exist_ok=True)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return [t for t in re.split(r"[^a-z]+", s) if t]


a = pd.read_parquet(D / "additions.parquet")
m = pd.read_parquet(D / "stage0_matches.parquet", columns=["match_id", "tournament_date", "player_a_id", "player_b_id"]).rename(columns={"player_a_id": "s0_a", "player_b_id": "s0_b"})
a = a.merge(m, on="match_id", how="left")
assert (a["player_a_id"] == a["s0_a"]).all() and (a["player_b_id"] == a["s0_b"]).all(), "additions ids differ from Stage 0"
# frozen names and match counts per id
fp = pd.read_parquet(REF_S0 / "stage0_match_players.parquet", columns=["player_id", "player_name"])
names = fp.groupby("player_id")["player_name"].agg(lambda s: s.value_counts().index[0])
nfrozen = fp.groupby("player_id").size()
# frame players and their frame-match days
fr = pd.read_parquet(FRAME, columns=["match_id"])
fm = pd.read_parquet(REF_S0 / "stage0_matches.parquet", columns=["match_id", "tournament_date", "player_a_id",
                                                                   "player_b_id"])
fm = fm[fm["match_id"].isin(set(fr["match_id"]))]
fday = pd.concat([fm[["player_a_id", "tournament_date"]].rename(columns={"player_a_id": "pid"}),
                  fm[["player_b_id", "tournament_date"]].rename(columns={"player_b_id": "pid"})])
fday["d"] = pd.to_datetime(fday["tournament_date"]).values.astype("datetime64[D]").astype("int64")
frame_days = fday.groupby("pid")["d"].apply(lambda s: np.sort(s.to_numpy()))
frame_ids = set(frame_days.index)
# one row per slot: the id the link chose (pre), the final id, the source name and route
slots = []
for k in (1, 2):
    s = a[["match_id", "source", "tour", "tournament_date", "player_a_id", "player_b_id", f"x{k}", f"p{k}",
           f"route{k}"]].rename(columns={f"x{k}": "pre", f"p{k}": "name", f"route{k}": "route"})
    o = a[f"x{3 - k}"].to_numpy()
    A_, B_, pre = s["player_a_id"].to_numpy(), s["player_b_id"].to_numpy(), s["pre"].to_numpy()
    kept = (pre == A_) | (pre == B_)
    other_kept = (o == A_) | (o == B_)
    # the slot's final id: itself if kept; else the final id the other slot does not hold; if both moved, by side order
    fin = np.where(kept, pre, np.where(other_kept, np.where(o == A_, B_, A_), A_ if k == 1 else B_))
    s["final"] = fin
    s["both_moved"] = ~kept & ~other_kept
    slots.append(s)
S = pd.concat(slots, ignore_index=True)
S["day"] = pd.to_datetime(S["tournament_date"]).values.astype("datetime64[D]").astype("int64")
S["moved"] = S["pre"] != S["final"]
S["n_pre"] = S["pre"].map(nfrozen).fillna(0).astype(int)
S["n_final"] = S["final"].map(nfrozen).fillna(0).astype(int)
# class: wrong (name_subset with another given name)
sn = S["final"].map(names)
gn_src = S["name"].map(lambda x: (norm(x) or [""])[0])
gn_s0 = sn.map(lambda x: (norm(x) or [""])[0] if pd.notna(x) else "")
S["wrong"] = (S["route"] == "name_subset") & (gn_src != gn_s0)
# class: split (moved away from a bigger id) and merge (moved onto a frame player)
S["split"] = S["moved"] & (S["n_final"] < S["n_pre"])
S["merge"] = S["moved"] & S["final"].isin(frame_ids)
# class: relative / reused source id, from the crosswalks
rel = []
for f in sorted((D / "evidence").glob("crosswalk_*.csv")):
    c = pd.read_csv(f)
    src = f.stem.replace("crosswalk_", "")
    for r in c.itertuples(index=False):
        a_, b_ = norm(r.src_name), norm(r.s0_name)
        if not a_ or not b_:
            continue
        tour = str(r.s0).split(":")[0]
        shared = set(a_) & set(b_)
        same_sur = a_[-1] == b_[-1]
        g1, g2 = a_[0], b_[0]
        from difflib import SequenceMatcher
        other_shared = shared - {a_[-1]}
        given_differs = (not (g1.startswith(g2) or g2.startswith(g1)) and not other_shared
                         and SequenceMatcher(None, g1, g2).ratio() < 0.5 and len(g1) > 1 and len(g2) > 1)
        if (same_sur and given_differs and len(a_) > 1 and len(b_) > 1) or (tour == "atp" and not shared):
            rel.append({"source": src, "s0": r.s0, "src_name": r.src_name, "s0_name": r.s0_name, "n": r.n})
rel = pd.DataFrame(rel)
key = set(zip(rel["source"], rel["s0"], rel["src_name"])) if len(rel) else set()
S["relative"] = np.array([(s, p, n) in key for s, p, n in zip(S["source"], S["pre"], S["name"])]) & (S["route"] == "crosswalk").to_numpy()


def touch(cls: str, who: str) -> dict:
    x = S[S[cls]]
    ids = x[who]
    on_frame = x[ids.isin(frame_ids)]
    out = {"slots": int(len(x)), "slots_on_frame_players": int(len(on_frame)),
           "frame_players": int(on_frame[who].nunique())}
    near, hit_frame = 0, 0
    per = []
    for pid, g in on_frame.groupby(who):
        fdays = frame_days[pid]
        dd = g["day"].to_numpy()
        # affected new rows within 365 days of one of the player's frame matches
        idx = np.searchsorted(fdays, dd)
        lo = np.abs(dd - fdays[np.clip(idx - 1, 0, len(fdays) - 1)])
        hi = np.abs(fdays[np.clip(idx, 0, len(fdays) - 1)] - dd)
        nr = int((np.minimum(lo, hi) <= 365).sum())
        # frame matches with an affected new row in the 365 days before
        j = np.searchsorted(np.sort(dd), fdays - 365, side="left")
        k = np.searchsorted(np.sort(dd), fdays, side="left")
        fh = int(((k - j) > 0).sum())
        near += nr
        hit_frame += fh
        per.append({"player": pid, "name": names.get(pid, ""), "slots": int(len(g)), "within_365": nr,
                    "frame_matches_hit": fh, "frame_matches": int(len(fdays))})
    out["affected_rows_within_365d_of_a_frame_match"] = near
    out["frame_matches_with_an_affected_row_in_prior_365d"] = hit_frame
    out["top"] = sorted(per, key=lambda r: -r["frame_matches_hit"])[:8]
    return out


res = {"slots": int(len(S)), "moved_by_repair": int(S["moved"].sum()), "frame_matches": int(len(fm)),
       "frame_players": len(frame_ids),
       "wrong": touch("wrong", "final"),
       "split_loser": touch("split", "pre"),
       "merge_onto_frame_player": touch("merge", "final"),
       "relative_or_reused": touch("relative", "final"),
       "relative_entries": int(len(rel)), "relative_entry_examples": rel.sort_values("n", ascending=False).head(12)
       .astype(str).to_dict("records") if len(rel) else []}
# frame matches touched by any class (union), for scale
any_ids = set()
for cls, who in (("wrong", "final"), ("split", "pre"), ("relative", "final")):
    any_ids |= set(S.loc[S[cls], who]) & frame_ids
res["frame_players_any_corrupting_class"] = len(any_ids)

# conflicts: one id in two tournaments of one week, at least one of them a new match (a wrong join's footprint)
allm = pd.read_parquet(D / "stage0_matches.parquet", columns=["match_id", "tournament_id", "tournament_date",
                                                              "player_a_id", "player_b_id", "map_level"])
newset = set(a["match_id"])
lg = pd.concat([allm[["match_id", "tournament_id", "tournament_date", "player_a_id"]].rename(columns={"player_a_id": "pid"}),
                allm[["match_id", "tournament_id", "tournament_date", "player_b_id"]].rename(columns={"player_b_id": "pid"})])
lg["week"] = pd.to_datetime(lg["tournament_date"]).dt.to_period("W-SUN")
lg["new"] = lg["match_id"].isin(newset)
lg = lg[lg["pid"].isin(frame_ids)]
g = lg.groupby(["pid", "week"]).agg(nt=("tournament_id", "nunique"), anynew=("new", "any"), nnew=("new", "sum"))
conf = g[(g["nt"] >= 2) & g["anynew"]].reset_index()
res["conflict_two_events_one_week_frame_players"] = int(conf["pid"].nunique())
res["conflict_player_weeks"] = int(len(conf))
res["conflict_new_rows"] = int(conf["nnew"].sum())
res["conflict_examples"] = conf.assign(name=conf["pid"].map(names)).head(12).astype(str).to_dict("records")

S[S["wrong"] | S["split"] | S["merge"] | S["relative"]].to_csv(OUT / "residual_slots.csv", index=False)
(OUT / "residuals.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "relative_entry_examples"}, indent=1, default=str)[:7000])
print(json.dumps(res["relative_entry_examples"], indent=0)[:2500])
