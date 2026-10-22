"""The venue key joins a renamed event to its history (f09_venue.RENAMED, 16 Oct 2026). The bug: the 2026 Shanghai
main draw is filed as "Shanghai", its qualifying and 2010-2025 as "Shanghai Masters", so the venue pace of a 2026 match
read only this year's rows. No data: names only."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.features import f09_venue as F  # noqa: E402


def key(tour, name, surface="Hard"):
    return F.venue_key([tour], [name], [surface])[0]


def test_renamed_events_join_their_history():
    assert key("atp", "Shanghai") == key("atp", "Shanghai Masters") == "atp|shanghaimasters|Hard"
    assert key("atp", "Nur-Sultan") == key("atp", "Astana")
    assert key("atp", "ATP Rio de Janeiro", "Clay") == key("atp", "Rio De Janeiro", "Clay")
    assert key("wta", "Adelaide 2") == key("wta", "Adelaide 1") == key("wta", "Adelaide")
    assert key("wta", "Calvia", "Grass") == key("wta", "Mallorca", "Grass")
    assert key("wta", "Cluj-Napoca 2") == key("wta", "Cluj Napoca")


def test_moves_of_city_or_surface_stay_apart():
    assert key("wta", "Montreal") != key("wta", "Toronto")
    assert key("atp", "Casablanca", "Clay") != key("atp", "Marrakech", "Clay")
    assert key("atp", "Almaty") != key("atp", "Astana")
    assert key("atp", "Stuttgart", "Clay") != key("atp", "Stuttgart", "Grass")
    assert key("atp", "Shanghai", "Clay") != key("atp", "Shanghai Masters", "Hard")


def test_only_whole_names_of_the_same_tour():
    assert key("atp", "Shanghai CH") == "atp|shanghaich|Hard"                  # not a prefix match
    assert key("wta", "Shanghai") == "wta|shanghai|Hard"                         # the map is per tour
    assert key("atp", "Calvia", "Grass") == "atp|calvia|Grass"
    many = F.venue_key(["atp", "wta", "atp"], ["Shanghai", "Charleston 1", "Beijing"], ["Hard", "Clay", "Hard"])
    assert list(many) == ["atp|shanghaimasters|Hard", "wta|charleston|Clay", "atp|beijing|Hard"]
