"""R3-referee (follow-up, addendum): my scope after the amended proposal.

Reads overrides_scope_v1.csv (my round-2 scope, 1,509 matches) and addendum_rows.csv (addendum.py: my own values for
the 12 changed and 32 added matches). A changed or added match is confirmed when:
    - my eighteen values equal the amended override row's (the service games derived here from MatchBeats' completed
      non-tiebreak games, or the score's alternation from MatchBeats' first server where MatchBeats lacks points);
    - for an added match, my eight counts from RG's statistics equal the row's (only the service games change);
    - where MatchBeats holds every point, its count equals the score's alternation;
    - no independent record (Court Vision 2019-2024, a hand chart) reads another count once the unfinished game of a
      retirement is set apart (they count games with a point served; the amended convention counts completed games).
Writes overrides_scope.csv: the v1 rows, the changed matches' rows replaced with my values, the added matches appended;
addendum_scope.json with the tests.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/addendum_scope.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402


def main() -> int:
    v1 = pd.read_csv(F.OUT / "overrides_scope_v1.csv", dtype=str, keep_default_na=False)
    d = pd.read_csv(F.OUT / "addendum_rows.csv", dtype={c: str for c in [f"mine_{x}" for x in F.OV_COLS]},
                    keep_default_na=False, na_values=[])
    d = d.replace({"nan": ""})
    num = lambda s: pd.to_numeric(s.replace("", np.nan), errors="coerce")
    tests = pd.DataFrame({"feed_key": d["feed_key"], "what": d["what"]})
    tests["values_equal_v2"] = d["differences_from_v2"].eq("")
    tests["eight_equal_row_if_added"] = d["what"].ne("added") | d["eight_mine_equal_row"].astype(str).eq("True")
    tests["mb_equals_alternation_where_complete"] = ~d["mb_complete_both"].astype(str).eq("True") | \
        d["mb_equals_alternation"].astype(str).eq("True")
    # the referees, the unfinished game of a retirement set apart for its server
    ok_ref = []
    for r in d.to_dict("records"):
        good = True
        for s in ("w", "l"):
            mine = num(pd.Series([r[f"my_{s}_sv_gms"]])).iloc[0]
            extra = 1 if r.get("unfinished_server_side") == s else 0
            for ref in ("cv", "mcp"):
                v = num(pd.Series([r[f"{ref}_{s}"]])).iloc[0]
                if not pd.isna(v) and v != mine + extra:
                    good = False
        ok_ref.append(good)
    tests["referees_agree"] = ok_ref
    tests["referees_holding"] = [sum(not pd.isna(num(pd.Series([r[f"{ref}_{s}"]])).iloc[0]) for ref in ("cv", "mcp")
                                     for s in ("w",)) for r in d.to_dict("records")]
    tests["confirmed"] = tests[["values_equal_v2", "eight_equal_row_if_added", "mb_equals_alternation_where_complete",
                                "referees_agree"]].all(axis=1)
    conf = d[tests["confirmed"].to_numpy()]
    rows = conf[["feed_key", "stage0_match_id"]].copy()
    for c in F.OV_COLS:
        rows[c] = conf[f"mine_{c}"].astype(str).replace({"nan": ""}).str.replace(r"\.0$", "", regex=True)
    changed = set(d.loc[d["what"].eq("changed"), "feed_key"])
    keep = v1[~v1["feed_key"].isin(changed)]
    out = pd.concat([keep, rows], ignore_index=True)[F.SCOPE_COLS]
    if out["stage0_match_id"].duplicated().any() or out["feed_key"].duplicated().any():
        raise SystemExit("duplicate matches in the scope")
    out.to_csv(F.OUT / "overrides_scope.csv", index=False)
    smry = {"v1_rows": int(len(v1)), "changed": int(d["what"].eq("changed").sum()), "added": int(d["what"].eq("added").sum()),
            "confirmed": tests.groupby("what")["confirmed"].sum().astype(int).to_dict(),
            "not_confirmed": tests.loc[~tests["confirmed"]].to_dict("records"),
            "referees_holding_matches": int((tests["referees_holding"] > 0).sum()),
            "scope_rows_after": int(len(out)),
            "changed_v1_rows_replaced": int(v1["feed_key"].isin(changed).sum())}
    tests.to_csv(F.OUT / "addendum_tests.csv", index=False)
    (F.OUT / "addendum_scope.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
