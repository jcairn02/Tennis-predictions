"""The ATP-site scrape of the Hugging Face handoff on Stage 0's ids (reader tp_atp_scraped of the source-reconciliation
study; brief: docs/studies/source_reconciliation/subagent_briefs.md).

Inputs (read-only): data/raw/public_dump/atp_pipeline_handoff/atp_scraped_enriched/atp_matches_<year>.csv.gz and
atp_matches_qual_chall_<year>.csv.gz (main tour, and qualifying with Challengers), and the earlier atp_scraped/ files
of the same names, 2009-2024 (Stage 0 starts with the 2010 season). The handoff labels the rows data_source
"atp_hawkeye": atptour.com's match statistics pages. Family "atp_official" (the ATP's own numbers, scraped by a third
party); the brief puts the reader here because it is a scrape.

What the files hold (observed 16 Oct 2026): Sackmann-format rows (winner/loser, ATP player codes such as D643, the ATP
tournament id, the tournament's start date; the match date only in 1,283 rows), with the nine counts per side
(w_/l_ ace, df, svpt, 1stIn, 1stWon, 2ndWon, SvGms, bpSaved, bpFaced) and extras (svcPtsTot, svcPtsWon, retPtsWon,
bpConv, bpOpp, ret_rating, the season-to-date statistics). Every enriched row carries the nine counts; the per-set
statistics are empty in every row (stats null); match_status is "F" in every row. The atp_scraped/ files hold more
rows but fewer with counts, and outside 2016 and 2018 no tournament date and no round: their rows with counts are
compared with the enriched rows on (file, tournament id, winner and loser codes) and not used (the JSON's
plain_copies: 56,770 of 57,473 are in the enriched files, equal on all 18 counts in 56,734; the other 703 cannot be
linked without a date).

Mapping: the nine counts as named (Sackmann's own column names); sv_won = 1stWon + 2ndWon (x_svc_won is the page's
own service points won, x_svc_tot its service points: they should equal sv_won and svpt).
Link: srcc_common.link (identity: both names, the tournament week, identical set scores or the round), per season,
on the study's snapshot of Stage 0 (tp_common.link), with the ATP player codes for the id pass. Orientation: the
linker's p1_side, which grades the winner's and loser's names against Stage 0's A and B (never by who won).
complete: the row carries all nine counts for both players (the source marks every row finished).
x_src_won: the scrape's winner, oriented by names.
Writes box/readers/tp_atp_scraped.{parquet,json}.
Run: ./python.sh src/eda/source_reconciliation/tp_atp_scraped.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import tp_common as T  # noqa: E402

READER, FAMILY = "tp_atp_scraped", "atp_official"
BASE = C.HANDOFF
YEARS = range(2009, 2025)
NINE = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon", "second_won": "2ndWon",
        "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}
EXTRA = {"x_svc_tot": "svcPtsTot", "x_svc_won": "svcPtsWon", "x_ret_won": "retPtsWon", "x_bp_conv": "bpConv",
         "x_bp_opp": "bpOpp"}
KEEP = ["tourney_id", "tourney_name", "tourney_date", "tourney_level", "round", "score", "match_num", "winner_id",
        "winner_name", "loser_id", "loser_name", "match_date", "best_of"]


def files() -> list[tuple[Path, str]]:
    out = []
    for folder in ("atp_scraped_enriched", "atp_scraped"):
        for y in YEARS:
            for stem in (f"atp_matches_{y}", f"atp_matches_qual_chall_{y}"):
                for suf in (".csv.gz", ".csv"):
                    p = BASE / folder / f"{stem}{suf}"
                    if p.exists():
                        out.append((p, folder))
                        break
    return out


def load() -> tuple[pd.DataFrame, dict]:
    frames, stats = [], {}
    for p, folder in files():
        cols = KEEP + [f"{s}_{c}" for s in ("w", "l") for c in list(NINE.values()) + list(EXTRA.values())]
        d = pd.read_csv(p, low_memory=False, dtype=str, usecols=lambda c: c in cols)
        d["x_file"] = f"{folder}/{p.name}"
        d["x_folder"] = folder
        d["x_stem"] = p.name.split(".")[0]
        frames.append(d)
        stats[f"{folder}/{p.name}"] = int(len(d))
    t = pd.concat(frames, ignore_index=True)
    for s in ("w", "l"):
        for c in list(NINE.values()) + list(EXTRA.values()):
            col = f"{s}_{c}"
            t[col] = C.num(t[col]) if col in t else np.nan
    nine = [f"{s}_{c}" for s in ("w", "l") for c in NINE.values()]
    t["has_nine"] = t[nine].notna().all(axis=1)
    t["mkey"] = t["x_stem"] + "|" + t["tourney_id"].astype(str) + "|" + t["round"].astype(str) + "|" + \
        t["winner_id"].astype(str) + "|" + t["loser_id"].astype(str)
    enriched = t[t["x_folder"].eq("atp_scraped_enriched")]
    # the plain copies (atp_scraped/): no tournament date and no round outside 2016 and 2018, so they cannot be
    # linked by themselves; compared here with the enriched rows on (file, tournament id, winner, loser)
    plain = t[t["x_folder"].eq("atp_scraped") & t["has_nine"]].copy()
    k = lambda d: d["x_stem"] + "|" + d["tourney_id"].astype(str) + "|" + d["winner_id"].astype(str) + "|" + \
        d["loser_id"].astype(str)  # noqa: E731
    plain["k"], enr = k(plain), enriched.assign(k=k(enriched))
    j = plain.drop_duplicates("k").merge(enr.drop_duplicates("k")[["k"] + nine], on="k", how="left",
                                         suffixes=("", "_e"), indicator=True)
    both = j[j["_merge"].eq("both")]
    same = pd.concat([both[c] == both[f"{c}_e"] for c in nine], axis=1).all(axis=1)
    info = {"rows_by_file": stats, "rows_read": int(len(t)), "enriched_rows": int(len(enriched)),
            "duplicate_keys_in_enriched": int(enriched["mkey"].duplicated().sum()),
            "plain_copies": {"distinct_rows_with_counts": int(len(j)), "also_in_enriched": int(len(both)),
                             "equal_to_enriched_on_all_18_counts": int(same.sum()),
                             "not_in_enriched_and_not_linkable_without_date_or_round": int(j["_merge"].eq("left_only").sum()),
                             "used": "no: the enriched files hold every linkable row"}}
    out = enriched[~enriched["mkey"].duplicated(keep="first")].reset_index(drop=True)
    out["sid"] = "atp_scraped:" + out["mkey"]
    return out, info


def main() -> int:
    t0 = time.time()
    rec = T.receipts([p for p, _ in files()])
    D, info = load()
    T.log(f"{len(D):,} scrape rows")
    day = pd.to_datetime(D["tourney_date"].astype(str).str[:8], format="%Y%m%d", errors="coerce")
    rnd = D["round"].map(T.K.round_code)
    src = pd.DataFrame({"sid": D["sid"], "tour": "atp", "day": day, "p1": D["winner_name"], "p2": D["loser_name"],
                        "sets": D["score"].map(lambda s: tuple(x[:2] for x in T.K.s0_sets(s)) if isinstance(s, str) else ()),
                        "rnd": rnd, "qual": D["round"].astype(str).str.match(r"^Q\d"), "tid": None,
                        "id1": D["winner_id"].astype(str), "id2": D["loser_id"].astype(str)})
    src = src[src["day"].notna()]
    links, reason, amb = T.link(src)
    lk = links.set_index("sid")
    J = D[D["sid"].isin(lk.index)].copy()
    J["match_id"] = J["sid"].map(lk["match_id"])
    J["a1"] = J["sid"].map(lk["p1_side"]).eq("A")
    J["link_method"] = "identity_" + J["sid"].map(lk["pass"]).astype(str)
    J["x_score_agrees"] = J["sid"].map(lk["sc"]).astype(bool)
    w = pd.DataFrame({"source_key": J["sid"], "match_id": J["match_id"], "a1": J["a1"],
                      "complete": J["has_nine"].to_numpy(), "link_method": J["link_method"]})
    for s, k in (("w", "p1"), ("l", "p2")):
        for f, c in NINE.items():
            w[f"{k}_{f}"] = J[f"{s}_{c}"].to_numpy()
        w[f"{k}_sv_won"] = (J[f"{s}_1stWon"] + J[f"{s}_2ndWon"]).to_numpy()
        for f, c in EXTRA.items():
            w[f"{k}_{f}"] = J[f"{s}_{c}"].to_numpy()
        w[f"{k}_x_src_won"] = (s == "w")
        w[f"{k}_x_src_name"] = J["winner_name" if s == "w" else "loser_name"].to_numpy()
        w[f"{k}_x_atp_code"] = J["winner_id" if s == "w" else "loser_id"].to_numpy()
    for c in ("x_file", "x_score_agrees"):
        w[c] = J[c].to_numpy()
    w["x_tourney_level"] = J["tourney_level"].to_numpy()
    w["x_tourney_date"] = J["tourney_date"].astype(str).to_numpy()
    pe = list(EXTRA) + ["x_src_won", "x_src_name", "x_atp_code"]
    rows = T.to_contract(w, READER, FAMILY, "box", player_extra=pe,
                         match_extra=["x_file", "x_score_agrees", "x_tourney_level", "x_tourney_date"])
    rows["x_src_won"] = rows["x_src_won"].astype("boolean")
    cons = {"svc_tot_equals_svpt": float((rows["x_svc_tot"] == rows["svpt"])[rows["x_svc_tot"].notna()].mean()),
            "svc_won_equals_first_won_plus_second_won":
                float((rows["x_svc_won"] == rows["sv_won"])[rows["x_svc_won"].notna()].mean())}
    rs = reason.value_counts()
    summary = {
        "inputs": rec, "records": info,
        "linked": {"rows_offered": int(len(src)), "linked": int(len(links)),
                   "by_pass": T.tidy_counts(links["pass"].value_counts()),
                   "score_agrees": int(links["sc"].astype(bool).sum())},
        "dropped": {"no_tournament_date": int(len(D) - len(src)),
                    "not_linked_by_reason": T.tidy_counts(rs[rs.index != "linked"]),
                    "ambiguous": int(len(amb))},
        "contract_checks": T.check_contract(rows),
        "complete_rows": int(rows["complete"].sum()),
        "self_consistency_share": {k: round(v, 5) for k, v in cons.items()},
        "winner_vs_stage0": T.winner_check(rows),
        "definitions": __doc__.split("Mapping:")[1].split("Writes box")[0].strip(),
        "sanity_vs_stage0_by_level_group": T.records(T.sanity(rows, by=["level_group"])),
        "hand_check": {"keys": T.sample_keys(rows), "status": "pending"},
    }
    T.write_reader(rows, READER, summary)
    T.log(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
