"""Scratch: read an xlsx header row + a sample row with stdlib only (no openpyxl).

Exists because the available conda envs lack openpyxl and installing into them
is out of scope; the dedicated `tennis` env (environment.yml) includes openpyxl.

Run:  ./python.sh src/eda/peek_xlsx_header.py data/raw/tennis_data_couk/atp/2026.xlsx
"""

import re
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def cell_col(ref: str) -> str:
    return re.match(r"([A-Z]+)", ref).group(1)


def main(path: str) -> None:
    zf = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in zf.namelist():
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        shared = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t"))
                  for si in root.findall("m:si", NS)]
    sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    rows = sheet.findall(".//m:row", NS)
    print(f"{path}: {len(rows) - 1} data rows")

    def render(row):
        out = {}
        for c in row.findall("m:c", NS):
            v = c.find("m:v", NS)
            if v is None:
                continue
            val = v.text
            if c.get("t") == "s":
                val = shared[int(val)]
            out[cell_col(c.get("r"))] = val
        return out

    header = render(rows[0])
    print("header:", list(header.values()))
    last = render(rows[-1])
    print("last row (by column letter):")
    for col, name in header.items():
        print(f"  {name:>12} = {last.get(col, '')}")


if __name__ == "__main__":
    main(sys.argv[1])
