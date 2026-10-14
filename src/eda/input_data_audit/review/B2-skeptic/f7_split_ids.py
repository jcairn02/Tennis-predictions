"""B2-skeptic review of F7 (players split across two ids). Read-only; writes only under
data/studies/input_data_audit/fixes/B2-skeptic/.

For each of the 13 pairs in frame_split_ids_oct07.csv:
  * every Stage 0 id (either tour) whose sorted-word name key equals the pair's key, with match counts and dates;
  * the new id's rows in full (event, date, round, opponent, country, age, hand, height, rank, source);
  * the established id's demographics (countries, birth-date estimates from age, hand, height) and last matches;
  * same-week clashes: the established id playing a different event within 6 days of the new id's rows;
  * rank continuity: the established id's latest rank before the new id's date against the new id's rank.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
S0 = ROOT / "data/studies/predictability_diagnostic"


def key(name) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return " ".join(sorted(re.findall(r"[a-z]+", s)))


def main() -> None:
    pairs = pd.read_csv(ROOT / "data/studies/input_data_audit/frame_split_ids_oct07.csv")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "opponent_id", "side", "won", "player_name", "rank",
                                 "seed", "entry", "age", "height", "hand", "country", "has_box"])
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "level", "qualifying", "round", "tournament_id", "tournament_name",
                                 "tournament_date", "source", "score", "status"])
    d = p.merge(m, on="match_id", how="left")
    d["key"] = d["player_name"].map(key)
    d["tournament_date"] = pd.to_datetime(d["tournament_date"])
    sane_age = d["age"].where(d["age"].between(5, 100))   # garbage ages (F8) would overflow the date arithmetic
    d["birth_est"] = d["tournament_date"] - pd.to_timedelta(sane_age * 365.25, unit="D")
    name_of = d.drop_duplicates("player_id").set_index("player_id")["player_name"]
    lines = []
    out_rows = []
    for r in pairs.itertuples():
        lines.append("=" * 110)
        lines.append(f"{r.tour} | {r.name_key} | established {r.established_id} ({r.established_matches}) | new {r.new_id}")
        same = d[d["key"].eq(r.name_key)]
        ids = same.groupby(["tour", "player_id"]).agg(n=("match_id", "size"), first=("tournament_date", "min"),
                                                      last=("tournament_date", "max"),
                                                      names=("player_name", lambda s: "; ".join(sorted(set(s)))),
                                                      sources=("source", lambda s: ",".join(sorted(set(s))))).reset_index()
        lines.append("  ids sharing the key (any tour):")
        for x in ids.itertuples():
            lines.append(f"    {x.tour} {x.player_id:16s} n={x.n:4d} {x.first.date()}..{x.last.date()} [{x.names}] src={x.sources}")
        # loose key: surname-only matches on same tour (other people with the same surname and a first-name initial)
        est = d[d["player_id"].eq(r.established_id)].sort_values("tournament_date")
        new = d[d["player_id"].eq(r.new_id)].sort_values("tournament_date")
        lines.append("  established demographics: countries %s | hand %s | height %s" % (
            est["country"].value_counts(dropna=False).to_dict(), est["hand"].value_counts(dropna=False).to_dict(),
            est["height"].value_counts(dropna=False).to_dict()))
        be = est["birth_est"].dropna()
        if len(be):
            lines.append(f"  established birth estimate from age: median {be.median().date()} "
                         f"IQR {be.quantile(.25).date()}..{be.quantile(.75).date()} (n={len(be)})")
        lines.append("  established source split: %s" % est["source"].value_counts().to_dict())
        lines.append("  established last 6 rows:")
        for x in est.tail(6).itertuples():
            lines.append(f"    {x.tournament_date.date()} {x.tournament_name[:28]:28s} {x.round:5s} q={x.qualifying!s:5s} "
                         f"rank={x.rank} age={x.age} ctry={x.country} src={x.source} opp={name_of.get(x.opponent_id, x.opponent_id)}")
        lines.append("  new id rows:")
        for x in new.itertuples():
            lines.append(f"    {x.tournament_date.date()} {x.tournament_name[:28]:28s} {x.round:5s} q={x.qualifying!s:5s} lvl={x.level} "
                         f"won={x.won} rank={x.rank} seed={x.seed} entry={x.entry} age={x.age} ht={x.height} hand={x.hand} "
                         f"ctry={x.country} src={x.source} name='{x.player_name}' opp={name_of.get(x.opponent_id, x.opponent_id)} "
                         f"score={x.score}")
            # same-week clash: established id in a different event within 6 days
            near = est[(est["tournament_date"] - x.tournament_date).abs().le(pd.Timedelta(days=6))
                       & est["tournament_id"].ne(x.tournament_id)]
            clash = ";".join(f"{y.tournament_date.date()} {y.tournament_name}" for y in near.itertuples())
            prev = est[est["tournament_date"] < x.tournament_date]
            prev_rank = prev["rank"].dropna().iloc[-1] if prev["rank"].notna().any() else np.nan
            prev_date = prev.loc[prev["rank"].notna(), "tournament_date"].iloc[-1].date() if prev["rank"].notna().any() else None
            if clash:
                lines.append(f"      ** same-week established rows elsewhere: {clash}")
            lines.append(f"      established's last rank before: {prev_rank} on {prev_date}")
            out_rows.append({"tour": r.tour, "name_key": r.name_key, "established_id": r.established_id, "new_id": r.new_id,
                             "match_id": x.match_id, "tournament_date": x.tournament_date.date(),
                             "tournament_name": x.tournament_name, "round": x.round, "new_rank": x.rank,
                             "new_age": x.age, "new_country": x.country, "new_hand": x.hand, "new_height": x.height,
                             "est_prev_rank": prev_rank, "est_prev_rank_date": prev_date,
                             "est_countries": ",".join(sorted(est["country"].dropna().astype(str).unique())),
                             "est_birth_median": be.median().date() if len(be) else None,
                             "new_birth_est": x.birth_est.date() if pd.notna(x.birth_est) else None,
                             "same_week_clash": clash, "source": x.source})
    (OUT / "f7_pairs_detail.txt").write_text("\n".join(lines), encoding="utf-8")
    pd.DataFrame(out_rows).to_csv(OUT / "f7_new_id_rows.csv", index=False)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
