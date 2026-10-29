"""Are the decided id aliases in a Stage 0? stage0_build applies data/studies/input_data_audit/fixes/id_aliases.csv in
every build: a player's second id mapped to his established id. A Stage 0 holds an alias when no player row of its
tour carries the second id and the established id has rows. The retrain register's check for an alias added after the
shared tables' last build (data/studies/current_best_model/pending_at_retrain.json; Jakub Mensik's, 28 Oct 2026).

    --stage0 <folder>     the folder holding stage0_match_players.parquet
    --instance <folder>   noted only: an instance takes its player ids from the Stage 0 it was built from, which
                          --stage0 names (pending.py's instance check passes both)
    --aliases <csv>       the table (default: the decided one)
    --only FROM_ID ...    these aliases only (default: every row of the table)
Exit 0 when every alias checked is in the Stage 0, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.input_data_audit import corrections as X  # noqa: E402


def check(stage0: Path, aliases: pd.DataFrame) -> dict:
    """{from_id: result} and ok overall: the second id has no player row of its tour and the established id has some."""
    mp = pd.read_parquet(Path(stage0) / "stage0_match_players.parquet", columns=["match_id", "player_id"])
    tour = mp["match_id"].astype(str).str.split("|").str[0]
    out = {}
    for a in aliases.itertuples():
        ids = mp.loc[tour.eq(a.tour).to_numpy(), "player_id"]
        second, established = int(ids.eq(a.from_id).sum()), int(ids.eq(a.to_id).sum())
        out[a.from_id] = {"to_id": a.to_id, "name_key": a.name_key, "rows_second_id": second,
                          "rows_established_id": established, "ok": second == 0 and established > 0}
    return {"aliases": out, "ok": all(v["ok"] for v in out.values())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0", required=True)
    ap.add_argument("--instance", default=None)
    ap.add_argument("--aliases", default=str(X.ID_ALIASES))
    ap.add_argument("--only", nargs="+", default=None, metavar="FROM_ID")
    a = ap.parse_args(argv)
    stage0 = Path(a.stage0) if Path(a.stage0).is_absolute() else ROOT / a.stage0
    aliases = pd.read_csv(a.aliases, dtype=str)
    if a.only:
        missing = sorted(set(a.only) - set(aliases["from_id"]))
        if missing:
            raise SystemExit(f"--only: {missing} are not in {a.aliases}")
        aliases = aliases[aliases["from_id"].isin(a.only)]
    res = {"stage0": str(stage0), **check(stage0, aliases)}
    if a.instance:
        res["instance"] = f"{a.instance}: its player ids are the Stage 0's above"
    bad = [k for k, v in res["aliases"].items() if not v["ok"]]
    print(json.dumps({k: v for k, v in res.items() if k != "aliases"} | {"not_in_stage0": bad,
                     "checked": len(res["aliases"])}, indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
