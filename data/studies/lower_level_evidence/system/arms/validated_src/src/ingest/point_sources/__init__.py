"""Acquisition adapters for point-by-point web sources (SofaScore, TennisLive.net).

Each adapter downloads verbatim responses into ``data/raw/point_sources/<source>/`` with receipts,
stages them as string Parquet under ``data/dump/points/<source>/`` and writes a small tracked run
summary under ``data/studies/point_shot_sources/scrape/``. See ``common.py`` for the shared client.
"""
