"""The ATP Challenger download's link key (src/ingest/point_sources/infosys_challengers.py): the copy writes players as
'A. ZVEREV', the map as full names, so a target links to a copy record by the two surnames."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.ingest.point_sources import infosys_challengers as IC  # noqa: E402


def test_surname_reads_the_copys_initial_form_and_full_names_alike():
    assert IC.surname("G. HEIDE") == IC.surname("Gustavo Heide") == "heide"
    assert IC.surname("A. LINGUA LAVALLEN") == IC.surname("Alejo Lorenzo Lingua Lavallen") == "lavallen"
    assert IC.surname("J.J. Wolf") == "wolf"
    assert IC.surname("Tomas Martin Etcheverry") == "etcheverry"


def test_surname_folds_accents_and_hyphens():
    assert IC.surname("Jesper de Jong") == "jong"
    assert IC.surname("Pablo Llamas Ruiz") == "ruiz"
    assert IC.surname("Hugo Grenier-Lacroix") == "lacroix"
    assert IC.surname("Zsombor Piros") == IC.surname("Z. PIRÓS") == "piros"
    assert IC.surname(None) == "" and IC.surname("") == ""
