"""Tennis My Life against Sackmann on the same matches: does TML carry Sackmann's box scores, field by field?

Stage 0 appends TML rows only where no Sackmann row exists, so it never compares the two on a shared match. This
script runs Stage 0's own loading, cleaning and linking (src/eda/predictability_diagnostic/stage0_build.py: the first
steps of build(), up to link_tml) in memory, writes nothing of Stage 0's, and compares the nine counts of each player
for every linked pair where both rows have them. The players are aligned by resolved id or name, so a pair whose
sources name different winners is compared player to player.

Writes to data/studies/data_continuity/:
    tml_vs_sackmann_fields.csv     agreement per field, by tour and season
    tml_vs_sackmann_levels.csv     agreement per field, by tour and level, 2022-2026
    tml_vs_sackmann_matches.csv    share of pairs whose 18 counts are all identical, by tour and season
    tml_vs_sackmann_svgms.csv      service-game differences against the tiebreaks in the score
    tml_vs_sackmann_examples.csv   disagreeing pairs, up to 15 per tour and field, with both source rows
    tml_vs_sackmann_pairs.parquet  every aligned pair and player with both sources' counts (read by referees.py)
    tml_vs_sackmann.json           summary
Run: ./python.sh src/eda/data_continuity/tml_vs_sackmann.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def linked_pairs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    """Stage 0's TML -> Sackmann links, made exactly as build() makes them (keep in step with it)."""
    raw = B.load_raw()
    df = B.normalise(raw)
    df = B.parse_scores(df)
    df = B.rule_levels(df)
    off = df["tdate"].isna() | (df["tdate"].dt.year < df["season"] - 1) | (df["tdate"].dt.year > df["season"])
    early = ~off & (df["tdate"] < pd.Timestamp(f"{B.C.FIRST_YEAR - 1}-12-01"))
    unknown_round = ~off & ~early & ~df["round"].isin(list(B.C.ROUND_ORDER))
    no_name = ~off & ~early & ~unknown_round & df["pair"].eq("")
    df = df[~(off | early | unknown_round | no_name)].copy()
    tm = df["source"].eq("tml")
    main_day = df[tm & ~df["qualifying"]].groupby(["tour", "ekey"])["tdate"].min()
    any_day = df[tm].groupby(["tour", "ekey"])["tdate"].min()
    day = B.lookup(main_day.combine_first(any_day), df, ["tour", "ekey"])
    move = tm & day.notna() & df["tdate"].ne(day) & ((df["tdate"] - day).dt.days.abs() <= 21)
    df.loc[move, "tdate"] = day[move]
    sack = B.drop_repeats(df[df["source"] == "sackmann"].copy(), "sackmann")
    tml = B.drop_repeats(df[df["source"] == "tml"].copy(), "tml")
    log(f"after repeats: Sackmann {len(sack):,}, TML {len(tml):,}")
    tml, xw = B.link_tml(sack, tml, {})
    return sack, tml, df, xw


def tiebreaks(score: str) -> int:
    sets, _ = B.tokens_of(score)
    return sum(1 for a, b, tb, br in sets if not br and (tb >= 0 or (max(a, b), min(a, b)) in ((7, 6), (13, 12))))


def aligned(sack: pd.DataFrame, tml: pd.DataFrame, xw: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Two aligned long frames (Sackmann, TML), one row per linked pair and player, and the orientation counts."""
    lk = tml[tml["link_rid"].notna()].copy()
    t = lk.reset_index(drop=True)
    s = sack.set_index("rid").loc[t["link_rid"].astype("int64").to_numpy()].reset_index()
    tw, tl = B.resolve_ids(t, "winner", xw), B.resolve_ids(t, "loser", xw)
    sw, sl = s["tour"] + ":" + s["winner_id"], s["tour"] + ":" + s["loser_id"]
    same = ((tw == sw) & (tw != "")) | ((tl == sl) & (tl != "")) | (t["wkey"] == s["wkey"]) | (t["lkey"] == s["lkey"])
    swap = ((tw == sl) & (tw != "")) | ((tl == sw) & (tl != "")) | (t["wkey"] == s["lkey"]) | (t["lkey"] == s["wkey"])
    orient = np.select([same & ~swap, swap & ~same], ["same", "swapped"], "unclear")
    meta = pd.DataFrame({"tour": s["tour"], "season": s["season"].astype("Int64"), "level": s["level"],
                         "qualifying": s["qualifying"], "link_status": t["link_status"], "orientation": orient,
                         "tdate": s["tdate"], "tourney_name": s["tourney_name"], "score": s["score"],
                         "s_file": s["_source_file"], "s_row": s["_row"], "t_file": t["_source_file"], "t_row": t["_row"],
                         "status": s["status"], "tiebreaks": s["score"].map(tiebreaks)})
    lefts, rights = [], []
    for role, other in (("w", "l"), ("l", "w")):
        sv = pd.DataFrame({c: K.num(s[f"{role}_{src}"]) for c, src in K.SACKMANN_NAMES.items()})
        t_role = np.where(orient == "swapped", other, role)
        tv = pd.DataFrame({c: np.where(t_role == "w", K.num(t[f"w_{src}"]), K.num(t[f"l_{src}"]))
                           for c, src in K.SACKMANN_NAMES.items()})
        name = s["winner_name"] if role == "w" else s["loser_name"]
        lefts.append(K.finish(sv).assign(**meta, role=role, player=name.to_numpy()))
        rights.append(K.finish(tv).assign(**meta, role=role, player=name.to_numpy()))
    left, right = pd.concat(lefts, ignore_index=True), pd.concat(rights, ignore_index=True)
    keep = left["orientation"].ne("unclear")
    counts = {k: int(v) for k, v in pd.Series(orient).value_counts().items()}
    return left[keep].reset_index(drop=True), right[keep].reset_index(drop=True), counts


def main() -> int:
    K.OUT.mkdir(parents=True, exist_ok=True)
    sack, tml, _, xw = linked_pairs()
    status = tml["link_status"].value_counts().to_dict()
    log(f"TML linked: {status}")
    left, right, orientation = aligned(sack, tml, xw)
    log(f"aligned player rows: {len(left):,}")
    full = left[K.COUNTS].notna().all(axis=1) & right[K.COUNTS].notna().all(axis=1)
    # a pair counts when both players have all nine counts in both sources
    pair_key = left["s_file"] + "#" + left["s_row"].astype(str)
    full_pair = full.groupby(pair_key).transform("all")
    left["period"] = np.where(left["tdate"] < K.SPLICE, "before the splice", "from the splice")

    fields = K.agreement(left, right, ["tour", "season"])
    fields.to_csv(K.OUT / "tml_vs_sackmann_fields.csv", index=False)
    recent = left["season"].between(2022, 2026)
    levels = K.agreement(left[recent], right[recent], ["tour", "level"])
    levels.to_csv(K.OUT / "tml_vs_sackmann_levels.csv", index=False)

    same_all = (left[K.COUNTS] == right[K.COUNTS]).all(axis=1)
    m = pd.DataFrame({"pair": pair_key, "tour": left["tour"], "season": left["season"], "same": same_all})[full_pair]
    per_pair = m.groupby(["pair", "tour", "season"])["same"].all().reset_index()
    matches = per_pair.groupby(["tour", "season"]).agg(pairs=("same", "size"), identical=("same", "sum")).reset_index()
    matches["identical_share"] = matches["identical"] / matches["pairs"]
    matches.to_csv(K.OUT / "tml_vs_sackmann_matches.csv", index=False)

    d = (right["sv_gms"] - left["sv_gms"]).where(left["sv_gms"].notna() & right["sv_gms"].notna())
    sv = pd.DataFrame({"tour": left["tour"], "tiebreaks": left["tiebreaks"].clip(upper=3), "diff": d.clip(-3, 3)})
    svt = sv.dropna().groupby(["tour", "tiebreaks", "diff"]).size().rename("players").reset_index()
    svt.to_csv(K.OUT / "tml_vs_sackmann_svgms.csv", index=False)

    ex = []
    for f in K.COUNTS:
        diff = left[f].notna() & right[f].notna() & (left[f] != right[f])
        if diff.any():
            sub = left[diff].assign(field=f, sackmann=left.loc[diff, f], tml=right.loc[diff, f])
            ex.append(sub.sort_values("tdate").groupby("tour").tail(15))
    cols = ["field", "tour", "season", "tdate", "tourney_name", "player", "role", "score", "sackmann", "tml",
            "s_file", "s_row", "t_file", "t_row", "link_status"]
    examples = pd.concat(ex, ignore_index=True)[cols] if ex else pd.DataFrame(columns=cols)
    examples.to_csv(K.OUT / "tml_vs_sackmann_examples.csv", index=False)

    # the aligned pairs, for referees.py (both sources' raw counts per player of every linked pair)
    keep = ["tour", "season", "level", "qualifying", "tdate", "tourney_name", "s_file", "s_row", "t_file", "t_row",
            "role", "player", "link_status", "orientation", "status"]
    pairs = left[keep].copy()
    for f in K.FIELDS:
        pairs[f"s_{f}"], pairs[f"t_{f}"] = left[f], right[f]
    pairs.to_parquet(K.OUT / "tml_vs_sackmann_pairs.parquet", index=False)

    overall = K.agreement(left, right, ["tour"])
    bad_s, bad_t = K.invariant_failures(left), K.invariant_failures(right)
    pairs_total = int(pair_key.nunique())
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "inputs": "data/dump/matches (Sackmann archive and Tennis My Life, as staged), via stage0_build in memory",
        "tml_rows_by_link_status": {k: int(v) for k, v in status.items()},
        "linked_pairs_by_orientation": orientation,
        "linked_pairs_compared": pairs_total,
        "pairs_with_full_box_in_both": int(per_pair.shape[0]),
        "pairs_identical_all_18_counts": int(per_pair["same"].sum()),
        "pairs_identical_share_by_tour": per_pair.groupby("tour")["same"].mean().round(5).to_dict(),
        "overall_by_tour": overall.to_dict("records"),
        "invariant_failure_rows": {"sackmann": bad_s.sum().to_dict(), "tml": bad_t.sum().to_dict()},
        "last_linked_week": str(left["tdate"].max().date()),
    }
    K.write_json(K.OUT / "tml_vs_sackmann.json", summary)
    log(f"pairs with full box in both: {summary['pairs_with_full_box_in_both']:,}; identical: "
        f"{summary['pairs_identical_all_18_counts']:,}")
    print(overall.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
