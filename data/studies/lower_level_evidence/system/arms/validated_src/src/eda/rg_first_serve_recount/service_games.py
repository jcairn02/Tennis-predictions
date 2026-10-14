"""The service-game fix of the owner's decision of 9 Oct 2026 (docs/decisions/2026-10-09-roland-garros-box-scores.md,
point 3): at the Australian Open and Roland Garros, Sackmann's rows often give the two players each other's service
games, mostly as the score gives them if the winner had served first. Where the Slam's own point record (Infosys
MatchBeats) proves who served first, the two counts are exchanged back with exchange_svgms (decided 8 Oct as F2y).

For every Stage 0 match of the two Slams, 2013-2026, with a MatchBeats file:
    first server   the player serving the file's first point, proven when that point opens set 1 and every game the
                   file holds, in order, follows the alternation of serve from that player (sources._mb_counts,
                   alternation_ok); the file is placed on the Stage 0 match by year, draw, round and both names
    truth          each player's service games from the score and the first server: servers alternate game by game,
                   a tiebreak takes its turn uncounted, and a retirement's unfinished game is not in the score
                   (whole_box.score_sv_gms, Sackmann's convention)
    class          equal; swapped (the row's two counts are the truth exchanged, and differ); other (any other
                   difference: not proposed); incomplete (a count missing); unproven (no proven first server)

Proposed: every swapped match, except those the candidate already changes another way: a row the decided corrections
of 8 Oct name (an exchanged box carries its service games with it), and a Roland Garros match with an override (its
box takes MatchBeats' service games). Walkovers have no service games.

Writes, in data/studies/rg_first_serve_recount/followup/service_games/:
    matches.csv               one row per Stage 0 match with a MatchBeats file: the row's and the true counts, class
    proposed_swaps.csv        the exchange_svgms rows, in row_corrections.csv's columns (fix SVX)
    summary.json              classes by Slam and year, the exclusions, and the "as if the winner served first" share
Reads no model result. Usage: ./python.sh src/eda/rg_first_serve_recount/service_games.py [--editions RG2019-2026,AO2025]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.rg_first_serve_recount import link as L  # noqa: E402
from src.eda.rg_first_serve_recount import propose as PR  # noqa: E402
from src.eda.rg_first_serve_recount import recount as RC  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402
from src.eda.rg_first_serve_recount import whole_box as WB  # noqa: E402
from src.ingest.point_sources import infosys_slams as I  # noqa: E402

OUT = WB.OUT / "service_games"
SLAMS = {"AO": "Australian Open", "RG": "Roland Garros"}
YEARS = (2013, 2026)


def stage0_rows() -> pd.DataFrame:
    """Stage 0's player rows of the two Slams, 2013-2026, with the match's keys and source row."""
    m = pd.read_parquet(S.S0 / "stage0_matches.parquet")
    p = pd.read_parquet(S.S0 / "stage0_match_players.parquet")
    m = m[m["tournament_name"].isin(SLAMS.values()) & m["year"].between(*YEARS)].copy()
    m["event"] = m["tournament_name"].map({v: k for k, v in SLAMS.items()})
    keep = ["match_id", "event", "year", "tour", "qualifying", "round", "score", "status", "source", "source_file",
            "source_row"]
    rows = p.merge(m[keep], on="match_id")
    rows["tour"] = rows["tour"].map({"atp": "M", "wta": "W"})
    rows["draw"] = np.where(rows["qualifying"], "qual", "main")
    rows["name_key"] = rows["player_name"].map(S.nkey)
    return rows


def matchbeats(slam: str, editions: set[str] | None = None) -> pd.DataFrame:
    """The Slam's MatchBeats files recounted (sources.mb), with each code's tour, draw and round; only the editions
    named ("RG2021", "AO2025"), where given."""
    mb = S.mb(slam)
    mb = mb[mb["slot"].notna()].copy()
    if editions is not None:
        mb = mb[(slam + mb["year"].astype(int).astype(str)).isin(editions)]
    rounds = I.round_lookup()
    mb["round"] = mb["match_id"].map(lambda c: rounds.get((slam, c)))
    fam = mb["match_id"].str[:2]
    women = fam.str[0].eq("W") if slam == "AO" else fam.str[1].eq("D")
    qual = fam.str[1].eq("Q") if slam == "AO" else fam.str[0].eq("Q")
    mb["tour"], mb["draw"], mb["event"] = np.where(women, "W", "M"), np.where(qual, "qual", "main"), slam
    return mb


def link(rows: pd.DataFrame, mb: pd.DataFrame) -> pd.DataFrame:
    """MatchBeats slots placed on Stage 0's player rows by year, draw, round and both names (link.place)."""
    s0m = L.stage0_matches(rows)
    mm = mb.pivot_table(index=["event", "year", "match_id", "tour", "draw", "round"], columns="slot",
                        values="name_key", aggfunc="first").reset_index()
    mm = mm.rename(columns={1: "name1", 2: "name2", "match_id": "code"})
    placed = L.place(mm, s0m, ["event", "year", "tour", "draw", "round"], "name1", "name2")
    placed = placed[placed["match_id"].notna()]
    s0i = s0m.set_index("match_id")
    out = []
    for r in placed.itertuples():
        for slot, side in ((1 if r.a_is == "1" else 2, "a"), (2 if r.a_is == "1" else 1, "b")):
            out.append({"match_id": r.match_id, "player_id": s0i.loc[r.match_id, f"pid_{side}"], "event": r.event,
                        "year": r.year, "code": r.code, "slot": slot, "link_score": r.link_score})
    links = pd.DataFrame(out)
    cols = ["event", "year", "match_id", "slot", "served_first", "alternation_ok", "alternation_strict",
            "sv_gms_regular", "route"]
    m = mb[cols].rename(columns={"match_id": "code", "sv_gms_regular": "mb_sv_gms"})
    return links.merge(m, on=["event", "year", "code", "slot"], how="left")


def classify(g: pd.DataFrame) -> str:
    w, l = g[g["raw_side"].eq("w")], g[g["raw_side"].eq("l")]
    if len(w) != 1 or len(l) != 1:
        return "names"
    w, l = w.iloc[0], l.iloc[0]
    if not (bool(w["alternation_ok"]) and (bool(w["served_first"]) ^ bool(l["served_first"]))):
        return "unproven"
    if pd.isna(w["raw_sv_gms"]) or pd.isna(l["raw_sv_gms"]) or pd.isna(w["true_sv_gms"]) or pd.isna(l["true_sv_gms"]):
        return "incomplete"
    if w["raw_sv_gms"] == w["true_sv_gms"] and l["raw_sv_gms"] == l["true_sv_gms"]:
        return "equal"
    if w["true_sv_gms"] != l["true_sv_gms"] and w["raw_sv_gms"] == l["true_sv_gms"] and l["raw_sv_gms"] == w["true_sv_gms"]:
        return "swapped"
    return "other"


def editions_of(text: str | None) -> set[str] | None:
    """"RG2019-2026,AO2025" -> {"RG2019", ..., "RG2026", "AO2025"}; None for every edition held."""
    if not text:
        return None
    out = set()
    for part in text.upper().split(","):
        slam, years = part.strip()[:2], part.strip()[2:]
        lo, _, hi = years.partition("-")
        out |= {f"{slam}{y}" for y in range(int(lo), int(hi or lo) + 1)}
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--editions", help='e.g. "RG2019-2026,AO2025" (default: every edition with MatchBeats files)')
    editions = editions_of(ap.parse_args().editions)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = stage0_rows()
    links = pd.concat([link(rows, matchbeats(s, editions)) for s in SLAMS], ignore_index=True)
    rows = rows.merge(links.drop(columns=["event", "year"]), on=["match_id", "player_id"], how="left")
    rows = RC.attach_raw(rows)                              # the raw row's counts and each player's side by name
    rows = rows[rows["code"].notna()].copy()
    # the truth: the score's alternation from the proven first server, oriented by the raw row's sides
    first_w = (rows["served_first"].eq(True) & rows["raw_side"].eq("w")).groupby(rows["match_id"]).transform("any")
    rows["true_sv_gms"] = [WB.score_sv_gms(sc, bool(fw))[0 if side == "w" else 1] if side in ("w", "l") else np.nan
                           for sc, fw, side in zip(rows["score"], first_w, rows["raw_side"])]
    rows["as_if_winner_first"] = [WB.score_sv_gms(sc, True)[0 if side == "w" else 1] if side in ("w", "l") else np.nan
                                  for sc, side in zip(rows["score"], rows["raw_side"])]
    rows.loc[rows["status"].eq("walkover"), ["true_sv_gms", "as_if_winner_first"]] = np.nan
    cls = rows.groupby("match_id").apply(classify, include_groups=False).rename("cls")
    rows = rows.merge(cls, left_on="match_id", right_index=True)
    # what the candidate already changes another way
    decided = pd.read_csv(K.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    named = set(K._row_key(decided["source_file"], decided["source_row"]))
    conf = WB.OUT / "confirmed" / "confirmed_overrides.csv"
    overridden = set(pd.read_csv(conf)["stage0_match_id"]) if conf.exists() else set()
    rows["decided_correction"] = K._row_key(rows["source_file"], rows["source_row"]).isin(named)
    rows["rg_override"] = rows["match_id"].isin(overridden)
    winner_first = rows.groupby("match_id")["as_if_winner_first"].transform(
        lambda s: True) & (rows["raw_sv_gms"].eq(rows["as_if_winner_first"]))
    rows["row_is_as_if_winner_first"] = winner_first.groupby(rows["match_id"]).transform("all")
    keep = ["event", "year", "tour", "draw", "round", "match_id", "code", "player_name", "won", "raw_side", "score",
            "status", "source", "source_file", "source_row", "served_first", "alternation_ok", "alternation_strict",
            "raw_sv_gms",
            "true_sv_gms", "mb_sv_gms", "as_if_winner_first", "row_is_as_if_winner_first", "cls",
            "decided_correction", "rg_override", "link_score", "route"]
    rows[keep].sort_values(["event", "year", "match_id", "raw_side"]).to_csv(OUT / "matches.csv", index=False)

    m = rows.drop_duplicates("match_id")
    take = m[m["cls"].eq("swapped") & ~rows.groupby("match_id")["decided_correction"].transform("any").loc[m.index]
             & ~m["rg_override"]]
    raw = S.raw_rows().set_index(["source_file", "source_row"])
    out = []
    for r in take.itertuples():
        x = raw.loc[(r.source_file, int(r.source_row))]
        out.append({"fix": "SVX", "action": "exchange_svgms", "match_id": r.match_id, "source_file": r.source_file,
                    "source_row": int(r.source_row), **{k: x[k] for k in K.ROW_GUARDS}})
    table = pd.DataFrame(out).reindex(columns=PR.ROW_COLUMNS)
    table.to_csv(OUT / "proposed_swaps.csv", index=False)
    summary = {
        "editions": sorted(editions) if editions else "every edition held",
        "matches_with_a_matchbeats_file": int(len(m)),
        "classes_by_slam_year": m.groupby(["event", "year", "cls"]).size().rename("matches").reset_index()
        .to_dict("records"),
        "classes": m["cls"].value_counts().to_dict(),
        "swapped_as_if_winner_first": int((m["cls"].eq("swapped") & m["row_is_as_if_winner_first"]).sum()),
        "swapped_left_out": {"decided_correction": int((m["cls"].eq("swapped") & rows.groupby("match_id")
                                                         ["decided_correction"].transform("any").loc[m.index]).sum()),
                             "rg_override": int((m["cls"].eq("swapped") & m["rg_override"]).sum())},
        "proposed_swaps": int(len(table)),
        "proposed_swaps_whose_file_fails_the_strict_check": take.loc[~take["alternation_strict"].astype(bool),
                                                                     "match_id"].tolist(),
        "proposed_by_slam_year": take.groupby(["event", "year"]).size().rename("matches").reset_index()
        .to_dict("records"),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "classes_by_slam_year"}, indent=1, default=str))
    print(m.pivot_table(index=["event", "year"], columns="cls", values="match_id", aggfunc="count", fill_value=0)
          .to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
