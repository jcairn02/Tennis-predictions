"""The override rows of an Australian Open or Roland Garros edition from the Slam's own records, for the editions after
the frozen reference (decision of 9 Oct 2026: docs/decisions/2026-10-09-ao-rg-box-scores-from-feeds.md; AO 2027 and
RG 2027 on). The rows join the decided override table (data/studies/data_continuity/slam_box_overrides.csv) at the next
coordinated Stage 0 rebuild, as Wimbledon's and the US Open's 2026 rows did (docs/decisions/2026-10-06-slam-box-scores.md).

The records, read from their raw files (src/ingest/point_sources/infosys_slams.py collects them, raw only):
    statistics   the Slam's Infosys key statistics (route keystats-api), the match ("set0"): aces, double faults, first
                 serve in/served, win on 1st serve won/in, win on 2nd serve won/played; break points faced and saved
                 from the opponent's "break points won"
    point file   the Infosys MatchBeats file (match-beats, else match-beats-api): who served first and the games
                 (sources._mb_counts), and a second record of the split, aces and double faults
A match takes an override row when all of these hold (else its class says why not):
    linked       the point file's two players are placed on the Stage 0 match by year, draw, round and both names
                 (service_games.link), and each is the raw row's winner or loser by name
    record       the statistics give all eight counts for both players, and they hang together: first won <= first in
                 <= served, second won <= served - first in, saved <= faced
    complete     the point file holds no more serve points than the statistics, for both players (else the statistics
                 miss points: a snapshot taken before the match point, as at RG 2024-2025)
    second       where the point file holds every point of a player (its serve points equal the statistics'), it gives
                 the same split, aces and double faults
    service      service games from the point file where it holds every point of both players, else from the score's
                 alternation from the proven first server, else the row's own; each only where it fits the score
                 (whole_box.official_sv_gms)
    checks       the box passes Stage 0's checks under the row's score (whole_box.stage0_checks)
    changes      a count differs from the row, or the row has no box
For Roland Garros, rolandgarros.com's statistics (src/ingest/point_sources/rolandgarros.py) are the other record of the
same counts where held: they agreed with the key statistics on every count in 99.7% of 2025 rows.

Writes data/studies/data_continuity/slam_infosys_overrides/<SLAM><year>/: rows.csv (every player row: the row, the
records, the class), overrides.csv (the override table's columns, with source), summary.json (classes, agreement of the
statistics with the row on each count, the checks).
Usage: ./python.sh src/eda/data_continuity/slam_infosys_overrides.py --edition AO2027 [--edition RG2027 ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.rg_first_serve_recount import recount as RC  # noqa: E402
from src.eda.rg_first_serve_recount import service_games as SG  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402
from src.eda.rg_first_serve_recount import whole_box as WB  # noqa: E402

OUT = K.OUT / "slam_infosys_overrides"
EIGHT = WB.EIGHT
SECOND = ["first_in", "first_won", "second_won", "ace", "df"]
ORDER = ["walkover", "no_link", "names", "record_fails_checks", "statistics_short", "mb_contradicts",
         "fails_stage0_checks", "equal", "proposed"]
NAMES = {  # a key statistic's name at Roland Garros, then at the Australian Open (2026 files)
    "aces": ("Aces",), "double_faults": ("Double Faults",), "first_serve": ("First Serve", "1st Serve In"),
    "win_1st": ("Win On 1st Serve", "Win 1st Serve"), "win_2nd": ("Win On 2nd Serve", "Win 2nd Serve"),
    "break_points_won": ("Break Points Won",)}


def keystats(slam: str, year: int) -> pd.DataFrame:
    """The key statistics of every raw keystats-api file of the edition, per match code and slot (player1/player2 are
    MatchBeats' slots 1/2), in Stage 0's counts."""
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import infosys_slams as I
    rows = []
    for path in sorted((S.RAW / "infosys_slams" / slam / str(year) / "keystats-api").glob("*.json.gz")):
        try:
            doc = I.decrypt(I.blocks_of("keystats-api", P.read_json(path))["stats"])
        except Exception as err:                       # recorded, never silently dropped
            rows.append({"code": path.name.split(".")[0], "slot": np.nan, "error": str(err)})
            continue
        rows += keystat_rows(path.name.split(".")[0], doc)
    return pd.DataFrame(rows)


def keystat_rows(code: str, doc: dict) -> list[dict]:
    """One decrypted key-statistics document's two players (slots 1 and 2) in Stage 0's counts; none when it holds no
    first-serve statistic. The two Slams name the same statistics differently (NAMES)."""
    st = {e.get("name"): (e.get("player1"), e.get("player2"))
          for e in ((doc or {}).get("setStats") or {}).get("set0") or []}

    def stat(key: str) -> tuple:
        return next((st[n] for n in NAMES[key] if n in st), (None, None))
    if stat("first_serve") == (None, None):
        return []
    out = []
    for j, k in ((0, 1), (1, 2)):
        fi, sv = S.frac(stat("first_serve")[j])
        bw, bo = S.frac(stat("break_points_won")[1 - j])
        out.append({"code": code, "slot": k, "ks_ace": S.num(stat("aces")[j]), "ks_df": S.num(stat("double_faults")[j]),
                    "ks_svpt": sv, "ks_first_in": fi, "ks_first_won": S.frac(stat("win_1st")[j])[0],
                    "ks_second_won": S.frac(stat("win_2nd")[j])[0], "ks_bp_faced": bo, "ks_bp_saved": bo - bw})
    return out


def edition_rows(slam: str, year: int) -> pd.DataFrame:
    """The edition's Stage 0 player rows, linked to the point files and the statistics, with the raw row's counts."""
    rows = SG.stage0_rows()
    rows = rows[rows["event"].eq(slam) & rows["year"].eq(year)].copy()
    links = SG.link(rows, SG.matchbeats(slam, {f"{slam}{year}"}))
    rows = rows.merge(links.drop(columns=["event", "year"]), on=["match_id", "player_id"], how="left")
    mb = S.mb(slam)
    mb = mb[mb["year"].eq(year)][["match_id", "slot", "svpt", "first_in", "first_won", "second_won", "ace", "df",
                                  "unfinished_games"]]
    mb = mb.rename(columns={"match_id": "code", **{c: f"mb_{c}" for c in mb.columns if c not in ("match_id", "slot")}})
    rows = rows.merge(mb, on=["code", "slot"], how="left")
    ks = keystats(slam, year)
    if len(ks):
        rows = rows.merge(ks.drop(columns=[c for c in ("error",) if c in ks]), on=["code", "slot"], how="left")
    for c in EIGHT:
        rows[f"ks_{c}"] = rows.get(f"ks_{c}", np.nan)
        rows[f"off_{c}"] = rows[f"ks_{c}"]
    rows = RC.attach_raw(rows)
    rows = rows.rename(columns={"alternation_ok": "mb_alternation_ok", "served_first": "mb_served_first",
                                "mb_sv_gms": "mb_sv_gms_regular"})
    proven = rows["mb_alternation_ok"].eq(True).groupby(rows["match_id"]).transform("all")
    rows["mb_served_first"] = rows["mb_served_first"].where(proven)     # a first server the file does not prove: none
    return WB.official_sv_gms(rows, stats_svpt="ks_svpt")


def classify(rows: pd.DataFrame) -> pd.DataFrame:
    by = rows["match_id"]

    def either(s: pd.Series) -> pd.Series:
        return s.groupby(by).transform("any")
    walkover = rows["status"].eq("walkover") | either(rows["off_svpt"].eq(0))
    no_link = either(rows["code"].isna())
    sides = rows.groupby("match_id")["raw_side"].transform(lambda s: "".join(sorted(s.astype(str))))
    names = ~sides.eq("lw")
    f = {c: rows[f"off_{c}"] for c in EIGHT}
    bad = (pd.concat([f[c].isna() for c in EIGHT], axis=1).any(axis=1) | (f["first_won"] > f["first_in"])
           | (f["first_in"] > f["svpt"]) | (f["second_won"] > f["svpt"] - f["first_in"])
           | (f["bp_saved"] > f["bp_faced"]))
    record = either(bad)
    short = either(rows["mb_svpt"].gt(rows["off_svpt"]))              # the point file holds points the statistics lack
    complete = rows["mb_svpt"].eq(rows["off_svpt"])
    contra = either(complete & ~np.all([rows[f"mb_{c}"].eq(rows[f"off_{c}"]) for c in SECOND], axis=0))
    fails = WB.stage0_checks(rows, "off").drop(columns="B5")
    failed = fails.any(axis=1)
    no_box = rows["raw_svpt"].isna()
    same = np.all([rows[f"raw_{c}"].eq(rows[f"off_{c}"]) for c in EIGHT + ["sv_gms"]], axis=0)
    equal = ~either(pd.Series(~same, index=rows.index) | no_box)
    rows["cls"] = np.select([walkover, no_link, names, record, short, contra, failed, equal], ORDER[:-1], ORDER[-1])
    rows["checks_failed"] = fails.apply(lambda r: ";".join(r.index[r]), axis=1)
    return rows


def override_rows(rows: pd.DataFrame, slam: str, year: int) -> pd.DataFrame:
    raw = S.raw_rows().set_index(["source_file", "source_row"])
    out = []
    for mid, g in rows[rows["cls"].eq("proposed")].groupby("match_id"):
        r = raw.loc[(g["source_file"].iloc[0], int(g["source_row"].iloc[0]))]
        x = {s: g[g["raw_side"].eq(s)].iloc[0] for s in ("w", "l")}
        rec = {"box_source": f"{slam.lower()}_infosys", "feed_key": f"infosys_{slam.lower()}:{year}/{g['code'].iloc[0]}",
               "stage0_match_id": mid, "source": r["source"], "tour": r["tour"], "tid": r["tid"], "round": r["round"],
               "winner_key": r["wkey"], "loser_key": r["lkey"], "winner_name": r["winner_name"],
               "loser_name": r["loser_name"]}
        for s in ("w", "l"):
            for name, col in C.BOX_SOURCE_NAMES.items():
                v = x[s][f"off_{name}"]
                rec[f"{s}_{col}"] = "" if pd.isna(v) else str(int(v))
        rec.update({"score": "", "minutes": "", "tml_score": r["score"], "feed_sha256": "", "feed_retrieved_at": ""})
        out.append(rec)
    return pd.DataFrame(out, columns=WB.OV_COLUMNS)


def run(edition: str) -> dict:
    slam, year = edition[:2].upper(), int(edition[2:])
    out = OUT / f"{slam}{year}"
    out.mkdir(parents=True, exist_ok=True)
    rows = classify(edition_rows(slam, year))
    keep = ["year", "tour", "draw", "round", "match_id", "code", "player_name", "won", "status", "score", "source",
            "source_file", "source_row", "raw_side", "cls", "checks_failed", "sv_gms_from", "mb_alternation_ok"] + \
        [f"{p}_{c}" for c in WB.NINE for p in ("raw", "off")] + [f"mb_{c}" for c in ("svpt", "first_in", "ace", "df")]
    rows[[k for k in keep if k in rows]].to_csv(out / "rows.csv", index=False)
    ov = override_rows(rows, slam, year)
    ov.to_csv(out / "overrides.csv", index=False)
    m = rows.drop_duplicates("match_id")
    with_box = rows[rows["raw_svpt"].notna() & rows["off_svpt"].notna()]
    summary = {"edition": edition, "stage0_matches": int(len(m)),
               "matches_by_class": m["cls"].value_counts().reindex(ORDER).fillna(0).astype(int).to_dict(),
               "overrides": int(len(ov)),
               "statistics_equal_to_the_row_by_count": {c: round(float(with_box[f"raw_{c}"].eq(with_box[f"off_{c}"])
                                                                       .mean()), 4) for c in WB.NINE}
               if len(with_box) else {},
               "player_rows_compared": int(len(with_box)),
               "sv_gms_source": rows["sv_gms_from"].value_counts().to_dict()}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edition", action="append", required=True, help="AO2027, RG2027, ...")
    for e in ap.parse_args().edition:
        print(json.dumps(run(e), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
