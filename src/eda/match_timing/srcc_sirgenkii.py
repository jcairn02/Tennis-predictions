"""Source 6, sirgenkii: the SirGenkii/infotennis SQL dumps (decrypted ATP Stats Centre data, January-April 2025), staged
under data/dump/points/sirgenkii_infotennis/ (src/eda/gap_sources/sirgenkii_matches.py).

Observed (5 Oct 2026): none of the six tables carries a match day or time. atp_results has year, tournament id, match
code, round, players, seeds and score; atp_calendars gives each tournament's date range ("2025.02.03 - 2025.02.09"),
which is a tournament week, not a match day; rally_analysis, key_stats, stroke_analysis and court_vision are keyed by
year, tournament and match code only. The CREATE TABLE statements of the raw dumps (data/raw/gap_sources/sirgenkii/
backup_sql/) hold no date or time column but the calendar's date_start, and the scraper code under
data/raw/gap_sources/sirgenkii/infotennis/ stores none. So no row is linked: the links file is written empty, in the
common schema, and the summary says why.
"""
from __future__ import annotations

import re

import pandas as pd
import pyarrow.parquet as pq

from src.eda.match_timing import srcc_common as K

SOURCE = "sirgenkii"
DUMP = K.DUMP / "points" / "sirgenkii_infotennis"
RAW_SQL = K.RAW / "gap_sources" / "sirgenkii" / "backup_sql"


def run() -> dict:
    tables = {}
    time_like = {}
    for f in sorted(DUMP.glob("atp_*.parquet")):
        names = pq.ParquetFile(f).schema_arrow.names
        tables[f.stem] = int(pq.ParquetFile(f).metadata.num_rows)
        time_like[f.stem] = [c for c in names if re.search(r"date|time|stamp|day", c, re.I) and not c.startswith("_")]
    sql_cols = {}
    for f in sorted(RAW_SQL.glob("*.sql")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"CREATE TABLE `[^`]+` \((.*?)\n\) ENGINE", text, re.S)
        cols = [ln.split("`")[1] for ln in (m.group(1).splitlines() if m else []) if ln.strip().startswith("`")]
        sql_cols[f.stem] = [c for c in cols if re.search(r"date|time|stamp|day", c, re.I)]
    res = pq.read_table(DUMP / "atp_results.parquet", columns=["year", "tournament_id", "match_id"]).to_pandas()
    path = K.write_links(pd.DataFrame(columns=K.LINK_COLUMNS), SOURCE)
    return {
        "source": SOURCE, "file": str(path.relative_to(K.ROOT)),
        "method": "none: the source holds no match day or time",
        "rows_read": int(len(res)), "tables": tables,
        "date_or_time_columns_in_staged_tables": time_like,
        "date_or_time_columns_in_raw_sql": sql_cols,
        "linked": 0, "ambiguous": 0, "unlinked": int(len(res)),
        "outcomes": {"no match day or time in the source (calendar date ranges only)": int(len(res))},
        "date_basis": {}, "with_start_utc": 0,
    }
