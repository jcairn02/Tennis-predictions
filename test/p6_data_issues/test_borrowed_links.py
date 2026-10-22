"""The borrowed-link rule's surname test (offline, synthetic teams in SofaScore's form)."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.p6_data_issues import borrowed_links as B  # noqa: E402


def team(name, slug, short=None):
    return {"name": name, "slug": slug, "shortName": short}


def test_surnames_come_from_the_slug_against_the_name_in_both_spellings():
    assert B.surname_words(team("Elmer Møller", "moeller-elmer")) == {"moeller", "moller"}
    assert B.surname_words(team("Javier Barranco Cosano", "barranco-cosano-javier", "J. Cosano")) == {"barranco", "cosano"}
    assert B.surname_words(team("Thiago Agustin Tirante", "tirante-thiago-agustin")) == {"tirante"}
    assert B.surname_words(team("Max Schönhaus", "schoenhaus-max")) == {"schoenhaus", "schonhaus"}
    # surname first in both, so they do not line up: the short name's words
    assert B.surname_words(team("Wu Yibing", "wu-yibing", "Y. Wu")) == {"wu"}


def test_a_surname_matches_exactly_or_within_a_letter_or_two():
    assert B.shares_surname(frozenset({"marvin", "moeller"}), frozenset({"moller"}))
    assert B.shares_surname(frozenset({"demetris", "azoides"}), frozenset({"azoidis"}))
    assert B.shares_surname(frozenset({"san", "hui", "sin"}), frozenset({"shin"}))      # three letters count
    assert not B.shares_surname(frozenset({"juan", "pablo", "ficovich"}), frozenset({"paz"}))
    assert not B.shares_surname(frozenset({"alexander", "shevchenko"}), frozenset({"shevtsov"}))
    assert B.shares_surname(frozenset({"anyone"}), frozenset())                         # no surname found: not tested


def test_surnames_agree_in_either_orientation_and_a_first_name_alone_fails():
    event = {"homeTeam": team("Lorenzo Angelini", "angelini-lorenzo"), "awayTeam": team("Matteo Arnaldi", "arnaldi-matteo")}
    assert not B.surnames_agree("Lorenzo Musetti", "Matteo Gigante", event)       # Forli 2022: borrowed
    assert B.surnames_agree("Matteo Arnaldi", "Lorenzo Angelini", event)           # the event's own match, reversed
    married = {"homeTeam": team("Jovana Jovic", "jovic-jovana"), "awayTeam": team("Jil Teichmann", "teichmann-jil")}
    assert not B.surnames_agree("Jil Teichmann", "Jovana Jaksic", married)         # a name change fails this test alone:
    # the rule refuses a link only when the official result disagrees too, which a name change's does not
