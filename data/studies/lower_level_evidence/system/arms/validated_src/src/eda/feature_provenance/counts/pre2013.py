# Counting script of the feature-provenance study (8 Oct 2026), written by the session's data-availability
# audit and copied here with its output folder moved to data/studies/feature_provenance/counts/.
# Counts only: no result column is read for any match after 28 Jul 2026.
"""Q2: what pre-2013 results, box scores and closing odds are on disk (read-only, counts only).

Run from the repo root:  ./python.sh <this file>
"""
from pathlib import Path
import re
import pandas as pd

BOX = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]


def box_flag(d: pd.DataFrame) -> pd.Series:
    cols = [f"{s}_{c}" for s in "wl" for c in BOX]
    if not all(c in d.columns for c in cols):
        return pd.Series(False, index=d.index)
    v = d[cols].apply(pd.to_numeric, errors="coerce")
    return v.notna().all(axis=1) & (v[["w_svpt", "l_svpt"]] > 0).all(axis=1)


def lvl(code: str, tour: str) -> str:
    code = str(code)
    if code == "G":
        return "GS"
    if code in ("F",):
        return "FIN"
    if code in ("M", "1000", "PM", "P5", "T1"):
        return "T1000/tier1"
    if code in ("A", "250", "500", "P", "I", "T2", "T3", "T4", "T5", "W"):
        return "tour (250/500/Intl/Premier/Tier2-5)"
    if code in ("D",):
        return "TEAM"
    if code in ("C", "CH"):
        return "CH"
    if code in ("S", "15", "25", "ITF") or code.startswith("W") or code.isdigit():
        return "ITF/other"
    return f"other:{code}"


# ---- Tennis My Life, 2000-2012
rows = []
for f in sorted(Path("data/raw/public_dump/tennis_my_life").glob("*.csv")):
    m = re.fullmatch(r"(\d{4})(_challenger|_wta)?\.csv", f.name)
    if not m or int(m.group(1)) > 2012:
        continue
    d = pd.read_csv(f, low_memory=False)
    d["season"] = int(m.group(1))
    d["file"] = {"": "atp_main", "_challenger": "atp_challenger", "_wta": "wta_main"}[m.group(2) or ""]
    d["box"] = box_flag(d)
    rows.append(d[["season", "file", "tourney_level", "box"]])
for f in sorted(Path("data/raw/public_dump/tennis_my_life/atp_quali").glob("*_atp_quali.csv")):
    yr = int(f.name[:4])
    if yr > 2012:
        continue
    d = pd.read_csv(f, low_memory=False)
    d["season"], d["file"], d["box"] = yr, "atp_quali", box_flag(d)
    rows.append(d[["season", "file", "tourney_level", "box"]])
tml = pd.concat(rows, ignore_index=True)
t = tml.groupby(["file", "season"]).agg(matches=("box", "size"), with_box=("box", "sum")).unstack("file")
print("TML 2000-2012, matches and full box scores, by file:\n", t.to_string())
print("TML tourney_level codes by file:", tml.groupby("file")["tourney_level"].unique().to_dict())

# ---- Sackmann tennis_atp (Hugging Face handoff copy), 1968-2009
rows = []
for f in sorted(Path("data/raw/public_dump/atp_pipeline_handoff/tennis_atp").glob("atp_matches_*")):
    m = re.fullmatch(r"atp_matches_(qual_chall_|futures_)?(\d{4})\.csv(\.gz)?", f.name)
    if not m or int(m.group(2)) < 1990:
        continue
    d = pd.read_csv(f, low_memory=False)
    d["season"] = int(m.group(2))
    d["file"] = {"": "main", "qual_chall_": "qual_chall", "futures_": "futures"}[m.group(1) or ""]
    d["box"] = box_flag(d)
    rows.append(d[["season", "file", "tourney_level", "box"]])
sk = pd.concat(rows, ignore_index=True)
s = sk.groupby(["file", "season"]).agg(matches=("box", "size"), with_box=("box", "sum")).unstack("file")
print("\nSackmann ATP (handoff copy) 1990-2009, matches and full box scores:\n", s.to_string())
mm = sk[sk["file"].eq("main")]
print("main-file levels 2000-2009:\n", pd.crosstab(mm.loc[mm.season >= 2000, "season"], mm.loc[mm.season >= 2000, "tourney_level"]).to_string())

# ---- tennis-data.co.uk, 2000-2012
rows = []
for f in sorted(Path("data/dump/odds/tennis_data_couk").glob("*/*/*.parquet")):
    yr = int(f.stem)
    if yr > 2012:
        continue
    d = pd.read_parquet(f)
    rec = {"tour": f.parts[-3], "season": yr, "series": f.parts[-2], "rows": len(d)}
    for b in ("PS", "Avg", "Max", "B365", "EX", "CB", "GB", "IW", "SB", "UB", "LB", "SJ"):
        w, l = pd.to_numeric(d.get(f"{b}W"), errors="coerce"), pd.to_numeric(d.get(f"{b}L"), errors="coerce")
        rec[b] = int(((w > 1) & (l > 1)).sum()) if w is not None and l is not None else 0
    rows.append(rec)
td = pd.DataFrame(rows).groupby(["tour", "season"]).sum(numeric_only=True)
print("\ntennis-data.co.uk 2000-2012 (staged parquet), rows and rows with both quotes, by book:\n", td.to_string())
