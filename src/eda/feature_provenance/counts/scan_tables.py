# Counting script of the feature-provenance study (8 Oct 2026), written by the session's data-availability
# audit and copied here with its output folder moved to data/studies/feature_provenance/counts/.
# Counts only: no result column is read for any match after 28 Jul 2026.
"""Which study tables hold rows for matches after 28 Jul 2026, and do they carry a label column?
Reads only the match_id column (and the schema). Run from the repo root: ./python.sh <this file>
"""
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

S0 = "data/studies/predictability_diagnostic/stage0_matches.parquet"
m = pd.read_parquet(S0, columns=["match_id", "tournament_date", "level", "qualifying", "year"])
post_ids = set(m.loc[m["tournament_date"] > "2026-07-28", "match_id"])
main_post = set(m.loc[(m["tournament_date"] > "2026-07-28") & m["level"].isin(["GS", "FIN", "T1000", "T500", "T250"])
                      & ~m["qualifying"], "match_id"])
atp18 = set(m.loc[(m["year"] == 2018) & m["level"].isin(["GS", "FIN", "T1000", "T500", "T250"]) & ~m["qualifying"]
                  & m["match_id"].str.startswith("atp"), "match_id"])
LABELS = {"a_won", "won", "y", "label", "y0", "winner", "target", "outcome"}
rows = []
for f in sorted(Path("data/studies").rglob("*.parquet")):
    try:
        sch = pq.read_schema(f)
    except Exception as e:  # noqa
        continue
    if "match_id" not in sch.names:
        continue
    try:
        pf = pq.ParquetFile(f)
        idx = pf.schema_arrow.get_field_index("match_id")
        ids = pd.Series(pf.read(columns=["match_id"], use_pandas_metadata=False).column(0).to_pylist())
    except Exception as e:  # noqa
        print("skip", f, type(e).__name__)
        continue
    u = set(ids.dropna().unique())
    n_post, n_main = len(u & post_ids), len(u & main_post)
    rows.append({"file": f.as_posix(), "rows": len(ids), "post_matches": n_post, "post_main": n_main,
                 "atp2018_main": len(u & atp18),
                 "labels": ",".join(sorted(LABELS & set(sch.names))),
                 "mtime": pd.Timestamp(f.stat().st_mtime, unit="s").strftime("%m-%d %H:%M")})
r = pd.DataFrame(rows)
pd.set_option("display.width", 250, "display.max_colwidth", 90, "display.max_rows", 500)
print(r[(r["post_matches"] > 0)].sort_values("file").to_string(index=False))
print("\n--- tables with ATP 2018 main-draw rows (top by count):")
print(r[r["atp2018_main"] > 0].sort_values("file")[["file", "rows", "atp2018_main", "labels", "mtime"]].to_string(index=False))
