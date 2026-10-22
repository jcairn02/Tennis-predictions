"""The ATP player code -> Stage 0 player id crosswalk the atp_ readers link with (box/atp_crosswalk.parquet).

Learned from ManTennisData (2015-2026), whose rows carry both players' ATP codes and full names: each row is linked to
Stage 0 by names only (the event linker without ids), and only links where BOTH players matched by full name vote
(code, Stage 0 id). A code takes the id that holds at least 80% of its votes (XW_MIN_SHARE, as the live speed
pipeline's crosswalk, serve_speed_tabpfn/live/link.py); codes below that are listed as conflicts and left out.
Reads only the snapshot and the staged ManTennisData files.

Run: ./python.sh src/eda/source_reconciliation/atp_crosswalk.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import atp_common as A  # noqa: E402
from src.eda.source_reconciliation import atp_mantd as MT  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

XW_MIN_SHARE = 0.8


def main() -> int:
    m = MT.load()
    linker = A.EventLinker()
    lk = linker.link(m, xw=None)
    m = m.join(lk)
    ok = m["link_method"].eq("event+full/full")
    p1, p2 = A.side_ids(m.loc[ok, "match_id"], m.loc[ok, "p1_side"])
    votes = pd.DataFrame({"code": pd.concat([m.loc[ok, "c1"], m.loc[ok, "c2"]]).to_numpy(),
                          "pid": pd.concat([p1, p2]).to_numpy()})
    votes = votes[(votes["code"] != "") & votes["pid"].notna()]
    top = votes.groupby(["code", "pid"]).size().reset_index(name="votes")
    top["total"] = top.groupby("code")["votes"].transform("sum")
    top["share"] = top["votes"] / top["total"]
    best = top.sort_values(["code", "votes", "pid"], ascending=[True, False, True]).drop_duplicates("code")
    keep = best[best["share"] >= XW_MIN_SHARE].reset_index(drop=True)
    conflicts = best[best["share"] < XW_MIN_SHARE]
    # a Stage 0 id claimed by two codes (one player under two ATP codes, or a linker slip)
    multi = keep.groupby("pid")["code"].nunique()
    A.BOX.mkdir(parents=True, exist_ok=True)
    keep[["code", "pid", "votes", "total", "share"]].to_parquet(A.XW_PATH, index=False)
    info = {"source": "ManTennisData 2015-2026 linked by full names (both players)",
            "rows_read": int(len(m)), "linked_by_full_names": int(ok.sum()),
            "link_methods_without_ids": m["link_method"].value_counts().to_dict(),
            "codes_with_votes": int(best["code"].nunique()), "codes_kept": int(len(keep)),
            "codes_below_share": int(len(conflicts)),
            "conflict_examples": conflicts.head(20).to_dict(orient="records"),
            "stage0_ids_with_two_codes": int((multi > 1).sum()),
            "stage0_ids_with_two_codes_examples": keep[keep["pid"].isin(multi[multi > 1].index)].head(20)
            .to_dict(orient="records"),
            "min_share": XW_MIN_SHARE}
    C.write_json(A.BOX / "atp_crosswalk.json", info)
    print(info["codes_kept"], "codes kept;", info["codes_below_share"], "below share;",
          info["stage0_ids_with_two_codes"], "ids with two codes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
