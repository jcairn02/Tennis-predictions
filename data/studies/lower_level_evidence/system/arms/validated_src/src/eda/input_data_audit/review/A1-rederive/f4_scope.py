"""F4 scope: my per-pair decisions (f4_pairs.csv) against the audit's pairs (box_raw_copies.csv rows with same_players
True, and the Dusseldorf 2012 rows), mapped to Stage 0. The audit names the later match the copy; here each pair's copy
is the row decided by f4_decide.py. Writes f4_audit_pairs.csv (one line per audit row) and f4_copies_all.csv (every copy row
decided, one line per Stage 0 player row; finalize.py keeps those in the candidate's pairs as f4_scope.csv)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_colwidth", 60)
P = pd.read_csv(R.OUT / "f4_pairs.csv")
P["date_s"] = pd.to_datetime(P["date"]).dt.strftime("%Y%m%d")
A = pd.read_csv(R.AUDIT / "box_raw_copies.csv")
A = A[A["same_players"].eq(True) | A["copy_event"].eq("Dusseldorf")].copy()
print("audit rows:", len(A), " duplicated lines:", int(A.duplicated().sum()))


def find(event, date, match):
    m = P[(P["event"].eq(event)) & (P["date_s"].eq(str(date))) & (P["match"].eq(match))]
    return m


rows = []
for a in A.to_dict("records"):
    src = find(a["source_event"], a["source_date"], a["source_match"].rsplit(" ", 0)[0])
    # the audit's match strings include the score; strip the score by matching the start
    src = P[(P["event"].eq(a["source_event"])) & (P["date_s"].eq(str(a["source_date"])))
            & a["source_match"].startswith(tuple(P["match"]))]
    src = P[(P["event"].eq(a["source_event"])) & (P["date_s"].eq(str(a["source_date"])))]
    src = src[[a["source_match"].startswith(x) for x in src["match"]]]
    cp = P[(P["event"].eq(a["copy_event"])) & (P["date_s"].eq(str(a["copy_date"])))]
    cp = cp[[a["copy_match"].startswith(x) for x in cp["match"]]]
    if len(src) != 1 or len(cp) != 1:
        rows.append({**a, "my_verdict": f"not found ({len(src)}, {len(cp)})"})
        continue
    s_role, c_role = src["role"].iloc[0], cp["role"].iloc[0]
    if c_role == "copy" and s_role == "genuine":
        v = "confirm: audit's copy row is the copy"
    elif s_role == "copy" and c_role == "genuine":
        v = "REVERSED: the audit's source row is the copy"
    elif c_role == "copy" and s_role == "copy":
        v = "both rows copies"
    else:
        v = "undecided"
    rows.append({**a, "my_verdict": v, "reason": cp["reason"].iloc[0],
                 "source_record": src["record_detail"].iloc[0], "copy_record": cp["record_detail"].iloc[0]})
AP = pd.DataFrame(rows)
AP.to_csv(R.OUT / "f4_audit_pairs.csv", index=False)
print(AP["my_verdict"].value_counts().to_string())
print(AP[["source_event", "source_date", "copy_event", "copy_date", "copy_match", "my_verdict"]].to_string())

# scope: the rows decided as copies within the audit's pairs (dedup), mapped to Stage 0
m, p = R.stage0()
mk = m.assign(k=m["source_file"] + "#" + m["source_row"].astype(str)).set_index("k")
in_audit = set()
for a in AP.to_dict("records"):
    for ev, dt, mt in ((a["source_event"], a["source_date"], a["source_match"]), (a["copy_event"], a["copy_date"], a["copy_match"])):
        x = P[(P["event"].eq(ev)) & (P["date_s"].eq(str(dt)))]
        x = x[[mt.startswith(y) for y in x["match"]]]
        for r in x.to_dict("records"):
            in_audit.add((r["_source_file"], r["_row"]))
C = P[P["role"].eq("copy")].copy()
C["in_candidate_pairs"] = [(a, b) in in_audit for a, b in zip(C["_source_file"], C["_row"])]
out = []
for r in C.to_dict("records"):
    k = f"{r['_source_file']}#{r['_row']}"
    mid = mk.loc[k, "match_id"] if k in mk.index else None
    hb = bool(mk.loc[k, "has_box"]) if k in mk.index else None
    for pr in (p[p["match_id"].eq(mid)].to_dict("records") if mid else [{}]):
        out.append({"match_id": mid, "player_id": pr.get("player_id"), "player_name": pr.get("player_name"),
                    "_source_file": r["_source_file"], "_row": r["_row"], "event": r["event"], "date": r["date"],
                    "round": r["round"], "match": r["match"], "score": r["score"], "s0_has_box": hb,
                    "in_candidate_pairs": r["in_candidate_pairs"], "reason": r["reason"]})
S = pd.DataFrame(out)
S.to_csv(R.OUT / "f4_copies_all.csv", index=False)
print(S.drop_duplicates("_row")[["event", "date", "round", "match", "s0_has_box", "in_candidate_pairs"]].to_string())
print("copy rows:", S["_row"].nunique(), " in the candidate's pairs:", S.loc[S["in_candidate_pairs"], "_row"].nunique(),
      " with a Stage 0 box:", S.loc[S["s0_has_box"].eq(True), "_row"].nunique())
