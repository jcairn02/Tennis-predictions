"""Sharp-money study, last step: render the HTML report, how beatable Polymarket tennis is before the match.

Fills report_template.html: `{{name}}` tokens take numbers and sentences built by report_text.py from the
pre-match results, and `__REPORT_DATA__` takes the compact JSON the page's charts and tables are drawn from.

Reads data/studies/polymarket_sharp_money/{prematch,prematch_buffer30,composition,build_summary,fee_check}.json;
writes docs/studies/polymarket_sharp_money/report.html.
Run: ./python.sh src/eda/polymarket_sharp_money/render_report.py
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_text import GROUP_DEFS, texts  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "data" / "studies" / "polymarket_sharp_money"
TEMPLATE = Path(__file__).with_name("report_template.html")
OUT = ROOT / "docs" / "studies" / "polymarket_sharp_money" / "report.html"
MEN = ["slams_m", "k1000_m", "k500_m", "k250_m", "challenger_m", "itf_m"]


def pct(v, d=0) -> str:
    return f"{v * 100:.{d}f}%"


def money(v) -> str:
    if v >= 1e9:
        return f"${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"${v / 1e6:.1f}M"
    return f"${v / 1e3:.0f}K"


def nice_step(values: list[float], target: int = 6) -> float:
    lo, hi = min(values + [0.0]), max(values + [0.0])
    for step in (0.0025, 0.005, 0.01, 0.02, 0.025, 0.05, 0.1):
        if (hi - lo) / step <= target + 1:
            return step
    return 0.2


def spread(rows: list[dict], key: str, groups: list[str]) -> list[float]:
    return [v for r in rows for g in groups for part in (r[key][g],) if part for v in (part["lo"], part["hi"])]


def report_data(pm: dict, pm_buf: dict) -> dict:
    shown = [x for x in pm["levels"] if x["key"] != "other"]
    hidden = [x for x in pm["levels"] if x["key"] == "other"]
    split = {x["key"]: x for x in pm["split"]}
    buf = {x["key"]: x for x in pm_buf["levels"]}
    robust = [{"label": "All tennis", "total": True, "main_win": pm["overall"]["edge"]["win"],
               "buffer_win": pm_buf["overall"]["edge"]["win"], "main_lose": pm["overall"]["edge"]["lose"],
               "buffer_lose": pm_buf["overall"]["edge"]["lose"]}]
    for x in shown:
        b = buf.get(x["key"])
        robust.append({"label": x["label"], "main_win": x["edge"]["win"], "buffer_win": b["edge"]["win"] if b else None,
                       "main_lose": x["edge"]["lose"], "buffer_lose": b["edge"]["lose"] if b else None})
    groups_vals = spread([pm["overall"]], "edge", ["win", "unsure", "lose"]) + \
        spread([pm["overall"]], "edge_after_fees", ["win", "unsure", "lose"])
    level_vals = spread([pm["overall"]] + shown, "edge", ["win"]) + spread([pm["overall"]] + shown, "edge_after_fees", ["win"])
    return {"overall": pm["overall"], "levels_shown": shown, "levels_hidden": hidden,
            "men": [split[k] for k in MEN if k in split], "calibration": pm["calibration"], "info": pm["info"],
            "group_defs": GROUP_DEFS, "robust": robust,
            "steps": {"groups": nice_step(groups_vals), "levels": nice_step(level_vals)}}


def fill(template: str, tokens: dict) -> str:
    def sub(m):
        key = m.group(1)
        if key not in tokens:
            raise KeyError(f"template token {{{{{key}}}}} has no value")
        return tokens[key]
    return re.sub(r"\{\{([A-Za-z0-9_]+)\}\}", sub, template)


def main() -> int:
    pm = json.loads((STUDY / "prematch.json").read_text(encoding="utf-8"))
    pm_buf = json.loads((STUDY / "prematch_buffer30.json").read_text(encoding="utf-8"))
    comp = json.loads((STUDY / "composition.json").read_text(encoding="utf-8"))
    build = json.loads((STUDY / "build_summary.json").read_text(encoding="utf-8"))
    fee_check = json.loads((STUDY / "fee_check.json").read_text(encoding="utf-8"))
    pm["window_start"], pm["window_end"] = comp["window_start"], comp["window_end"]
    known, total = [int(x.replace(",", "")) for x in re.findall(r"[\d,]+", comp["itf_gender_note"])[:2]]
    pm["itf_gender_share"] = known / total
    tokens = texts(pm, pm_buf, build, fee_check, dict(pct=pct, money=money, esc=html.escape))
    page = fill(TEMPLATE.read_text(encoding="utf-8"), tokens)
    blob = json.dumps(report_data(pm, pm_buf), separators=(",", ":"), default=float).replace("</", "<\\/")
    page = page.replace("__REPORT_DATA__", blob)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
