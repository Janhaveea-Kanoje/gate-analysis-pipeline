"""
Keeps the 21-case demo (run_demo.py) in sync with the pipeline.

Only the three LIVE lookups (FSA Novel Food, FSA Food Alerts, Companies House) are
replaced with stand-ins so the test runs offline; every other check is the real code.
It therefore proves each case stops at the gate and for the reason the demo claims,
but it cannot prove the live lookups themselves - run run_demo.py with internet and a
COMPANIES_HOUSE_API_KEY for that.
"""
from collections import Counter

import pytest

import run_demo
import src.gates.gate1_regulatory as gate1
import src.gates.gate3_brand as gate3


@pytest.fixture(autouse=True)
def offline_lookups(monkeypatch):
    monkeypatch.setattr(gate1, "check_novel_food", lambda category, product_name: (True, "stub: no register match"))
    monkeypatch.setattr(gate3, "check_regulatory_history", lambda brand: (True, "stub: no alerts"))

    def disclosure(brand, inputs):
        if not inputs.all_ingredients_disclosed:
            return False, "Ingredient list is incomplete or undisclosed."
        if brand == "Healthspan":
            return True, "stub: company verified"
        return False, "stub: no active company found"

    monkeypatch.setattr(gate3, "check_full_disclosure", disclosure)


def test_every_demo_case_stops_where_the_demo_says():
    _, rows = run_demo.run_all()
    wrong = [(r["id"], r["expected"], r["actual"], r["tier"]) for r in rows if not r["ok"]]
    assert not wrong, f"Demo cases that no longer behave as documented: {wrong}"


def test_demo_funnel_shape():
    _, rows = run_demo.run_all()
    stops = Counter(r["actual"] for r in rows)
    assert stops == {
        "Stopped at Gate 0": 6, "Stopped at Gate 1": 3, "Stopped at Gate 2": 3,
        "Stopped at Gate 3": 3, "Stopped at Gate 4": 2, "Cleared all gates": 4,
    }


def test_demo_flags_a_fictional_brand_that_matches_a_real_company(monkeypatch):
    # If the company lookup "verifies" the fictional brands of cases 18-19 (as the real lookup did for
    # lookalike names), the demo must flag them rather than present the result as fine.
    def lenient(brand, inputs):
        if not inputs.all_ingredients_disclosed:  # this rule never touches the company search
            return False, "Ingredient list is incomplete or undisclosed."
        return True, "stub: verified as an unrelated company"

    monkeypatch.setattr(gate3, "check_full_disclosure", lenient)
    _, rows = run_demo.run_all()
    flagged = {r["id"] for r in rows if not r["ok"]}
    assert flagged == run_demo.UNVERIFIABLE_BRAND_IDS
