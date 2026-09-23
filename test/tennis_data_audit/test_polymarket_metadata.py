"""Regression: optional Gamma volume must not become fabricated zero activity."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    path = ROOT / "src/eda/tennis_data_audit" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class MarketMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.implementations = [module("polymarket_census"), module("analyze_polymarket_census")]

    def test_missing_and_null_volume_stays_unknown(self):
        for implementation in self.implementations:
            for record in ({}, {"volumeNum": None}, {"volumeNum": None, "volume": ""}):
                with self.subTest(implementation=implementation.__name__, record=record):
                    self.assertIsNone(implementation.volume_value(record))

    def test_explicit_zero_is_a_measurement(self):
        for implementation in self.implementations:
            self.assertEqual(implementation.volume_value({"volume": "0"}), 0)
            self.assertEqual(implementation.volume_value({"volumeNum": 0}), 0)

    def test_numeric_zero_is_not_overwritten_by_alternate_field(self):
        for implementation in self.implementations:
            self.assertEqual(implementation.volume_value({"volumeNum": 0, "volume": "10"}), 0)

    def test_string_volume_used_when_numeric_field_absent(self):
        for implementation in self.implementations:
            self.assertEqual(implementation.volume_value({"volumeNum": None, "volume": "12.5"}), 12.5)

    def test_invalid_volume_does_not_silently_become_zero(self):
        for implementation in self.implementations:
            with self.assertRaises(ValueError):
                implementation.volume_value({"volume": "unknown"})

    def test_calendar_window_is_half_open_with_explicit_utc(self):
        census = self.implementations[0]
        start, end = census.parse_date(census.START), census.parse_date(census.END)
        self.assertTrue(start <= census.parse_date("2025-09-10") < end)
        self.assertTrue(start <= census.parse_date("2026-09-10T23:59:59Z") < end)
        self.assertFalse(start <= census.parse_date("2026-09-11T00:00:00Z") < end)
        self.assertEqual((end-start).days, 366)


if __name__ == "__main__":
    unittest.main()
