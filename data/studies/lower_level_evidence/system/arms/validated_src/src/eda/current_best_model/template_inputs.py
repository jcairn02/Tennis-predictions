"""The current best model's input list (docs/decisions/2026-10-08-current-best-model.md, "The configuration").

The template's chain (src/eda/model_rebuild/run_chain.py) builds 58 input columns and lists all of them in
model_inputs.json, as every build has since 6 Oct 2026. The owner has since dropped inputs from the model, and this step
writes the list the model is fitted and forecast on:

    ios_points_short   dropped by the owner on 9 Oct 2026 ("Drop ios_points_short"), after the lean review's T2
                       (docs/studies/lean_review/README.md): no measurable effect at Pinnacle's opening line or close

The dropped columns stay in the frame, so the chain's checks of each input against its source are unchanged; no fit
reads them. Earlier builds keep their lists: the frozen reference of 8 Oct and the Pinnacle-first instance of 9 Oct are
58-input models, as built, and the fit runner (model_rebuild/fits.py) accepts both lists.

Run: ./python.sh src/eda/current_best_model/template_inputs.py --apply <folder>    (after run_chain.py --collect)
     ./python.sh src/eda/current_best_model/template_inputs.py --check <folder>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BUILT = 58                  # the inputs the chain builds and lists
DROPPED = {"ios_points_short": "the owner, 9 Oct 2026: 'Drop ios_points_short' (decision amendment of "
                               "2026-10-08-current-best-model; the lean review's T2)"}


def template_names(names: list[str]) -> list[str]:
    """The built list without the dropped inputs, in the built order."""
    return [n for n in names if n not in DROPPED]


def kind(names: list[str]) -> str:
    """'template' for the decided list, 'built' for the chain's full list (every build before 9 Oct 2026 was fitted on
    it). Anything else raises: a list that is neither is not this model's."""
    names = list(names)
    if len(set(names)) != len(names):
        raise ValueError("the input list repeats a name")
    if len(names) == BUILT and set(DROPPED) <= set(names):
        return "built"
    if len(names) == BUILT - len(DROPPED) and not set(DROPPED) & set(names):
        return "template"
    raise ValueError(f"{len(names)} inputs: neither the chain's {BUILT} nor the template's {BUILT - len(DROPPED)} "
                     f"(without {', '.join(DROPPED)})")


def names_of(folder: Path) -> list[str]:
    meta = json.loads((folder / "model_inputs.json").read_text(encoding="utf-8"))
    return [d["name"] for d in meta["inputs"]]


def apply(folder: Path) -> dict:
    """Rewrite <folder>/model_inputs.json to the template's list, keeping every other field and each input's entry.
    Idempotent: a folder already on the template's list is left as it is."""
    path = Path(folder) / "model_inputs.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    was = kind([d["name"] for d in meta["inputs"]])
    if was == "built":
        meta["inputs"] = [d for d in meta["inputs"] if d["name"] not in DROPPED]
        meta["template_dropped"] = DROPPED
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(meta, indent=1), encoding="utf-8")
        tmp.replace(path)
    return {"folder": str(folder), "was": was, "inputs": len(meta["inputs"]), "dropped": sorted(DROPPED)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", metavar="FOLDER")
    g.add_argument("--check", metavar="FOLDER")
    a = ap.parse_args()
    if a.apply:
        print(json.dumps(apply(Path(a.apply))))
        return 0
    k = kind(names_of(Path(a.check)))
    print(f"{a.check}: {k} list")
    return 0 if k == "template" else 1


if __name__ == "__main__":
    sys.exit(main())
