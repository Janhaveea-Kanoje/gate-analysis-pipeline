"""
Client for DDInter 2.0 (ddinter.scbdd.com) — open-access drug interaction database
that now includes DDSIs (drug-dietary-supplement interactions).

DDInter does not currently publish a documented public REST API (unlike FSA/DSLD) —
as of this writing it's a searchable web database. Two practical options, in order
of preference:

1. Request a bulk data export/API access directly from the DDInter team
   (contact info on their site) — this is the right long-term answer since your
   pipeline needs to run unattended.
2. Until you have that, mirror the query pattern below against a locally-cached
   copy of their published DDSI dataset (download once, store in src/data/,
   re-sync monthly per the roadmap's Phase 4 monitoring cadence).

This module is written against option 2 so the pipeline works today. Swap
`_load_local_ddsi_cache()` for a real API/DB call once you have bulk access.
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Optional

_CACHE_PATH = Path(__file__).parent.parent / "data" / "ddsi_cache.csv"


def _load_local_ddsi_cache() -> list[dict]:
    if not _CACHE_PATH.exists():
        return []
    with open(_CACHE_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_supplement_drug_interactions(ingredient_name: str) -> dict:
    """
    Returns {"found": bool, "interactions": list[dict]} for a given supplement ingredient.
    Each interaction dict has: drug, severity, mechanism, management (per DDInter schema).
    """
    cache = _load_local_ddsi_cache()
    matches = [
        row for row in cache
        if ingredient_name.strip().lower() in row.get("supplement", "").strip().lower()
    ]
    return {"found": bool(matches), "interactions": matches}
