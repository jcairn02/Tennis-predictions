"""B1-rederive reviewer: F7 split ids, recomputed from the live Stage 0 tables (read-only).

For every (tour, name_key) pair in frame_split_ids_oct07.csv, and independently for every
non-Sackmann id whose name key matches exactly one Sackmann id of the same tour:
  * how many Sackmann ids share the name key (must be exactly 1);
  * the countries on both ids;
  * birth year implied by (tournament_date - age) on both ids;
  * the weeks where both ids play (overlap) and at which events;
  * the new id's matches (event, round, opponent, date, source).
Writes data/studies/input_data_audit/fixes/B1-rederive/f7_*.csv
"""
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
OUT.mkdir(parents=True, exist_ok=True)
S0 = ROOT / "data/studies/predictability_diagnostic"


def name_key(value):
    if pd.isna(value):
        return ""
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


m = pd.read_parquet(S0 / "stage0_matches.parquet",
                    columns=["match_id", "tour", "level", "qualifying", "round", "tournament_id",
                             "tournament_name", "tournament_date", "source", "score", "status"])
p = pd.read_parquet(S0 / "stage0_match_players.parquet",
                    columns=["match_id", "player_id", "opponent_id", "side", "won", "player_name",
                             "rank", "age", "country", "hand", "height"])
q = p.merge(m, on="match_id", how="left")
q["tdate"] = pd.to_datetime(q.tournament_date)
q["name_key"] = q.player_name.map(name_key)
q["birth_year_approx"] = q.tdate.dt.year + q.tdate.dt.dayofyear / 365.25 - pd.to_numeric(q.age, errors="coerce")
print("sources:", q.drop_duplicates("match_id").source.value_counts().to_dict())

pairs = pd.read_csv(ROOT / "data/studies/input_data_audit/frame_split_ids_oct07.csv")

# Independent scan: every non-Sackmann id whose exact name key belongs to Sackmann ids of the tour
sk = q[q.source.eq("sackmann") & q.name_key.ne("")]
sk_ids = sk.groupby(["tour", "name_key"]).player_id.agg(lambda s: tuple(sorted(set(s))))
ns = q[q.source.ne("sackmann") & q.name_key.ne("")]
ns_ids = ns.groupby(["tour", "name_key"]).player_id.agg(lambda s: tuple(sorted(set(s))))
scan = []
for (tour, key), nids in ns_ids.items():
    est = sk_ids.get((tour, key), ())
    if not est:
        continue
    for nid in nids:
        if nid in est:
            continue
        scan.append({"tour": tour, "name_key": key, "sackmann_ids": "|".join(est), "n_sackmann_ids": len(est),
                     "new_id": nid})
scan = pd.DataFrame(scan)
print("non-Sackmann ids whose exact name key matches Sackmann ids but carry another id:", len(scan))
print(scan.to_string())
scan.to_csv(OUT / "f7_independent_scan.csv", index=False)

# Also: all ids (any source) sharing a name key within tour -> name key collisions
allk = q[q.name_key.ne("")].groupby(["tour", "name_key"]).player_id.nunique()

rows = []
detail = []
for r in pairs.itertuples():
    key = r.name_key
    est, new = r.established_id, r.new_id
    a = q[q.player_id.eq(est)]
    b = q[q.player_id.eq(new)]
    sk_same_key = sk_ids.get((r.tour, key), ())
    # any id in the whole table (any source) with the same key
    any_ids = sorted(set(q.loc[q.tour.eq(r.tour) & q.name_key.eq(key), "player_id"]))
    # names used on each id
    names_a = sorted(set(a.player_name.dropna()))
    names_b = sorted(set(b.player_name.dropna()))
    ca = a.country.dropna().astype(str).str.upper().value_counts().to_dict()
    cb = b.country.dropna().astype(str).str.upper().value_counts().to_dict()
    by_a = a.birth_year_approx.dropna()
    by_b = b.birth_year_approx.dropna()
    # overlapping weeks: same ISO week at different tournament ids
    a_w = a.assign(wk=a.tdate.dt.to_period("W-SUN"))
    b_w = b.assign(wk=b.tdate.dt.to_period("W-SUN"))
    common = sorted(set(a_w.wk) & set(b_w.wk))
    clash = []
    for w in common:
        ta = set(a_w.loc[a_w.wk.eq(w), "tournament_name"])
        tb = set(b_w.loc[b_w.wk.eq(w), "tournament_name"])
        clash.append(f"{w}: est {sorted(ta)} / new {sorted(tb)}")
    # date windows: est last match before new first
    a_last = a.tdate.max()
    a_first = a.tdate.min()
    a_recent = a[a.tdate.ge(b.tdate.min() - pd.Timedelta(days=120))]
    # direct meeting between the two ids (would mean two people)
    meet = q[q.player_id.eq(est) & q.opponent_id.eq(new)]
    rows.append({
        "tour": r.tour, "name_key": key, "established_id": est, "new_id": new,
        "n_rows_est": len(a), "n_rows_new": len(b),
        "est_sources": "|".join(sorted(set(a.source))), "new_sources": "|".join(sorted(set(b.source))),
        "sackmann_ids_with_key": "|".join(sk_same_key), "n_sackmann_ids_with_key": len(sk_same_key),
        "all_ids_with_key": "|".join(any_ids),
        "names_est": "|".join(names_a), "names_new": "|".join(names_b),
        "country_est": str(ca), "country_new": str(cb),
        "hand_est": "|".join(sorted(set(a.hand.dropna().astype(str)))),
        "hand_new": "|".join(sorted(set(b.hand.dropna().astype(str)))),
        "height_est": "|".join(sorted(set(a.height.dropna().astype(str)))),
        "height_new": "|".join(sorted(set(b.height.dropna().astype(str)))),
        "birth_year_est_median": round(by_a.median(), 2) if len(by_a) else np.nan,
        "birth_year_est_minmax": f"{by_a.min():.2f}..{by_a.max():.2f}" if len(by_a) else "",
        "birth_year_new": "|".join(f"{v:.2f}" for v in by_b) if len(by_b) else "",
        "ages_new": "|".join(str(v) for v in b.age.tolist()),
        "est_first": a_first.date() if len(a) else None, "est_last": a_last.date() if len(a) else None,
        "new_first": b.tdate.min().date(), "new_last": b.tdate.max().date(),
        "est_rows_within_120d_of_new": len(a_recent),
        "same_week_clashes": " ; ".join(clash), "direct_meetings": len(meet),
    })
    for x in b.sort_values("tdate").itertuples():
        detail.append({"name_key": key, "new_id": new, "match_id": x.match_id, "side": x.side,
                       "player_name": x.player_name, "date": x.tdate.date(), "event": x.tournament_name,
                       "level": x.level, "qualifying": x.qualifying, "round": x.round, "won": x.won,
                       "opponent_id": x.opponent_id, "rank": x.rank, "age": x.age, "country": x.country,
                       "source": x.source})
    # the established id's last 8 rows for context
    for x in a.sort_values("tdate").tail(8).itertuples():
        detail.append({"name_key": key, "new_id": est + " (est, last rows)", "match_id": x.match_id,
                       "side": x.side, "player_name": x.player_name, "date": x.tdate.date(),
                       "event": x.tournament_name, "level": x.level, "qualifying": x.qualifying,
                       "round": x.round, "won": x.won, "opponent_id": x.opponent_id, "rank": x.rank,
                       "age": x.age, "country": x.country, "source": x.source})

res = pd.DataFrame(rows)
det = pd.DataFrame(detail)
res.to_csv(OUT / "f7_pairs_checks.csv", index=False)
det.to_csv(OUT / "f7_pairs_detail.csv", index=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 120)
for r in res.itertuples():
    print("\n#####", r.tour, r.name_key, r.established_id, "->", r.new_id)
    for k, v in r._asdict().items():
        if k in ("Index",):
            continue
        print(f"   {k}: {v}")
print("\n\nDETAIL")
print(det.to_string())
