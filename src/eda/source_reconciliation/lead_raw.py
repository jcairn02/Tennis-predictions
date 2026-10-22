"""The lead's readers: Stage 0's own counts, and Sackmann's and Tennis My Life's raw counts, on Stage 0's ids.

Three readers in the box contract (docs/studies/source_reconciliation/subagent_briefs.md), written to
data/studies/source_reconciliation/box/readers/:
    lead_stage0         the counts the model's chain reads: Stage 0's player rows (the snapshot), after the decided
                        overrides, the 8 Oct corrections and Stage 0's row checks (a count that fails is blank)
    lead_sackmann_raw   Sackmann's raw row for every Stage 0 match whose row is Sackmann's (before any override,
                        correction or check)
    lead_tml_raw        Tennis My Life's raw row of the same match: for TML-only matches the row Stage 0 took; for
                        Sackmann matches, the TML row Stage 0's own linking ties to it
The TML-to-Sackmann links are made by Stage 0's own code, as src/eda/data_continuity/tml_vs_sackmann.py makes them
(its linked_pairs() and aligned(), imported unchanged; nothing of theirs is written). Each raw row is placed on its
Stage 0 match through the Sackmann row's file and row number, and on its players by who won, checked by name.

Run: ./python.sh src/eda/source_reconciliation/lead_raw.py   (about 2 minutes)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.data_continuity import tml_vs_sackmann as T  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

READERS = C.OUT / "box" / "readers"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def contract(frame: pd.DataFrame, reader: str, family: str, kind: str) -> pd.DataFrame:
    out = pd.DataFrame({"reader": reader, "family": family, "kind": kind,
                        "source_key": frame["source_key"].astype(str), "match_id": frame["match_id"].astype(str),
                        "player_id": frame["player_id"].astype(str)})
    for f in C.COUNTS:
        out[f] = pd.to_numeric(frame[f], errors="coerce").astype("float64")
    out["sv_won"] = out["first_won"] + out["second_won"]
    out["complete"] = frame.get("complete", pd.Series(True, index=frame.index)).astype(bool).to_numpy()
    out["link_method"] = frame.get("link_method", pd.Series("", index=frame.index)).astype(str).to_numpy()
    for c in frame.columns:
        if c.startswith("x_"):
            out[c] = frame[c].to_numpy()
    return out


def side_rows(rows: pd.DataFrame, prefix_w: str, prefix_l: str) -> pd.DataFrame:
    """A raw winner/loser row as two player rows: role w (the row's winner) and l, with the nine counts."""
    parts = []
    for role, pre in (("w", prefix_w), ("l", prefix_l)):
        part = pd.DataFrame({c: K.num(rows[f"{pre}{src}"]) for c, src in K.SACKMANN_NAMES.items()}, index=rows.index)
        part["role"] = role
        part["raw_name"] = rows["winner_name" if role == "w" else "loser_name"].to_numpy()
        part["_file"] = rows["_source_file"].astype(str).to_numpy()
        part["_rowno"] = rows["_row"].astype(str).to_numpy()
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def place(raw: pd.DataFrame, m: pd.DataFrame, p: pd.DataFrame, file_col: str, row_col: str) -> tuple[pd.DataFrame, dict]:
    """Raw player rows -> Stage 0 (match_id, player_id) through the match's source file and row, the player by who
    won, kept only where the raw name and Stage 0's name agree (name keys, as merge_feasibility makes them)."""
    where = m[["match_id", "source_file", "source_row"]].copy()
    where["source_row"] = where["source_row"].astype(str)
    j = raw.merge(where, left_on=[file_col, row_col], right_on=["source_file", "source_row"], how="inner")
    j["won"] = j["role"].eq("w")
    j = j.merge(p[["match_id", "won", "player_id", "player_name"]], on=["match_id", "won"], how="inner")
    same = K.norm_name(j["raw_name"]).eq(K.norm_name(j["player_name"]))
    stats = {"raw_player_rows": int(len(raw)), "placed": int(len(j)), "name_mismatch_dropped": int((~same).sum())}
    return j[same].drop_duplicates(["match_id", "player_id"]), stats


def main() -> int:
    READERS.mkdir(parents=True, exist_ok=True)
    m, p = C.stage0(["match_id", "tour", "year", "source", "source_file", "source_row", "status"],
                    ["match_id", "player_id", "won", "player_name"] + C.COUNTS)
    summary = {"snapshot": str(C.SNAP), "readers": {}}

    # 1. Stage 0 itself
    s0 = p.assign(source_key="stage0:" + p["match_id"].astype(str), link_method="identity")
    s0 = s0.merge(m[["match_id", "status"]], on="match_id", how="left")
    s0["complete"] = s0["status"].isin(["completed", "retired"])
    out = contract(s0, "lead_stage0", "stage0", "box")
    out.to_parquet(READERS / "lead_stage0.parquet", index=False)
    summary["readers"]["lead_stage0"] = {"rows": int(len(out)), "with_any_count": int(out[C.COUNTS].notna().any(axis=1).sum())}
    log(f"lead_stage0: {len(out):,} rows")

    # 2. Sackmann's and TML's raw rows, linked as Stage 0 links them
    sack, tml, _, xw = T.linked_pairs()
    log(f"linked_pairs: Sackmann {len(sack):,}, TML {len(tml):,}")
    ms = m[m["source"].eq("sackmann")]
    sr, st = place(side_rows(sack, "w_", "l_"), ms, p, "_file", "_rowno")
    sr = sr.assign(source_key="sackmann:" + sr["_file"].str.rsplit("/", n=1).str[-1] + "#" + sr["_rowno"],
                   link_method="stage0_row", complete=True)
    out = contract(sr, "lead_sackmann_raw", "sackmann", "box")
    out.to_parquet(READERS / "lead_sackmann_raw.parquet", index=False)
    summary["readers"]["lead_sackmann_raw"] = {**st, "rows": int(len(out))}
    log(f"lead_sackmann_raw: {len(out):,} rows ({st})")

    # TML rows Stage 0 took (TML-only matches)
    mt = m[m["source"].eq("tml")]
    tr_only, st_only = place(side_rows(tml, "w_", "l_"), mt, p, "_file", "_rowno")
    tr_only = tr_only.assign(link_method="stage0_row")
    # TML rows linked to a Sackmann row: placed through that Sackmann row; the TML row's own orientation from
    # aligned() (which matches the two rows' players by resolved id or name key)
    left, right, orient = T.aligned(sack, tml, xw)
    right = right.assign(raw_name=right["player"], _file=right["s_file"].astype(str), _rowno=right["s_row"].astype(str))
    tr_link, st_link = place(right, ms, p, "_file", "_rowno")
    tr_link = tr_link.assign(link_method="stage0_tml_link")
    tr_link["_tfile"] = tr_link["t_file"].astype(str)
    tr_link["_trow"] = tr_link["t_row"].astype(str)
    tr_only["_tfile"], tr_only["_trow"] = tr_only["_file"], tr_only["_rowno"]
    tr = pd.concat([tr_only, tr_link], ignore_index=True)
    tr["source_key"] = "tml:" + tr["_tfile"].str.rsplit("/", n=1).str[-1] + "#" + tr["_trow"]
    tr["complete"] = True
    tr = tr.drop_duplicates(["match_id", "player_id"])
    out = contract(tr, "lead_tml_raw", "tml", "box")
    out.to_parquet(READERS / "lead_tml_raw.parquet", index=False)
    summary["readers"]["lead_tml_raw"] = {"tml_only": st_only, "linked_to_sackmann": st_link,
                                         "aligned_orientation": orient, "rows": int(len(out))}
    log(f"lead_tml_raw: {len(out):,} rows (only {st_only}; linked {st_link})")
    C.write_json(READERS / "lead_raw.json", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
