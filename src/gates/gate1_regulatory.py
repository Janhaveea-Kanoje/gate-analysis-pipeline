"""
Gate 1 — Regulatory Compliance.

Live-checks against the FSA Novel Food register and Food Alerts API (see
src/datasets/fsa_client.py). Everything the FSA client can't confirm
automatically (GMP certificate authenticity, batch traceability, label
compliance wording) is a human/extraction task feeding into this same
PASS/FAIL structure — the rule engine still makes the final call once those
fields are populated.
"""

from __future__ import annotations
from dataclasses import dataclass

from src.schemas import Product, Gate1Result
from src.datasets.fsa_client import check_novel_food_status, check_recent_alerts, FSAClientError

RECOGNISED_GMP_BODIES = {"nsf", "informed sport", "usp", "brcgs"}

_RECOMMENDED_TESTING: dict[str, dict] = {}
def _load_recommended_testing():
    global _RECOMMENDED_TESTING
    if _RECOMMENDED_TESTING:
        return _RECOMMENDED_TESTING
    import csv
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "recommended_testing.csv")
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            _RECOMMENDED_TESTING[row["ingredient"]] = {
                "text": row["recommended_testing"],
                "requires_brcgs_tier": row["requires_brcgs_tier"].strip().lower() == "true",
            }
    return _RECOMMENDED_TESTING


@dataclass
class RegulatoryInputs:
    """Fields the extraction layer / human reviewer must supply for this gate."""
    category: str  # the ingredient category, e.g. "Magnesium Citrate", "Cordyceps"
    gmp_certifying_body: str | None
    gmp_certificate_current: bool
    gmp_facility_matches_label: bool
    has_batch_lot_number: bool
    contraindications_disclosed: bool
    special_population_warnings_present: bool
    makes_disease_claim: bool


def check_novel_food(category: str, product_name: str) -> tuple[bool, str]:
    """
    Checks the product's ingredient category against the live GB Novel Food
    register. A "found": True result means Novel Food authorisation may be
    required - this is a flag for further verification, not automatically
    a fail, since a product CAN legally use a Novel Food ingredient if it
    has the required authorisation. Extend RegulatoryInputs with an
    authorisation-confirmed field if that distinction needs to be tracked;
    this function currently treats any match as needing verification.
    """
    try:
        result = check_novel_food_status(category, product_name)
    except FSAClientError as exc:
        return False, f"{category}: FSA lookup failed ({exc}) — route to human review, do not assume PASS"
    if result["found"]:
        return False, f"{category}: matches Novel Food register entry '{result['matched_slug']}' — requires confirmed authorisation, route to human review"
    return True, "No Novel Food register match found for this ingredient category."


def check_gmp(inputs: RegulatoryInputs) -> tuple[bool, str]:
    if not inputs.gmp_certifying_body or inputs.gmp_certifying_body.lower() not in RECOGNISED_GMP_BODIES:
        return False, f"GMP body '{inputs.gmp_certifying_body}' is not a recognised standard (NSF, Informed Sport, USP, BRCGS). ISO 22000 alone does not satisfy this parameter — it's a food-safety standard, not a supplement GMP standard."
    if not inputs.gmp_certificate_current:
        return False, "GMP certificate is not current."
    if not inputs.gmp_facility_matches_label:
        return False, "GMP certificate does not match the facility named on the label."
    return True, f"Current {inputs.gmp_certifying_body} certification, matched to labelled facility."


def check_gmp_specificity(category: str, gmp_certifying_body: str | None) -> tuple[bool, str]:
    """
    Checks the claimed GMP body against an ingredient-specific recommended
    testing standard (science_research.xlsx column Q: "Which testing is
    recommended (BRCGS > GMP > basic FDA > or any other specified test)").

    SCOPE, DELIBERATE: this data names a recommended TESTING REGIME per
    ingredient (e.g. "GMP mandatory with CFU verification at expiry" for a
    probiotic), not measured batch results - it cannot substitute for real
    Certificate of Analysis data (Gate 2's actual, unmet requirement). It
    supports a narrower, real question: does the claimed certification meet
    the TIER this specific ingredient needs, using the column's own stated
    hierarchy (BRCGS > GMP > basic FDA), rather than treating every
    recognised GMP body as interchangeable regardless of ingredient.

    Returns (True, "no ingredient-specific tier requirement on file") when
    the category isn't in the evidence file, rather than failing on absent
    data - consistent with this project's practice of not guessing.
    """
    lookup = _load_recommended_testing()
    entry = lookup.get(category)
    if entry is None:
        return True, f"No ingredient-specific testing-tier recommendation on file for '{category}'."
    if not entry["requires_brcgs_tier"]:
        return True, f"Recommended standard for {category} is GMP-tier — no BRCGS/GFSI-specific requirement."
    if gmp_certifying_body and gmp_certifying_body.lower() == "brcgs":
        return True, f"BRCGS-certified, matching the recommended tier for {category}."
    return False, (f"{category}'s recommended testing standard specifically calls for BRCGS/GFSI "
                   f"certification ('{entry['text']}'), but the claimed body is "
                   f"'{gmp_certifying_body}' — a lower tier per this evidence file's own stated hierarchy.")


def check_batch_traceability(inputs: RegulatoryInputs) -> tuple[bool, str]:
    if inputs.has_batch_lot_number:
        return True, "Batch/lot tracking system in place."
    return False, "No visible batch/lot number on product pages or label images reviewed."


def check_safety_documentation(inputs: RegulatoryInputs) -> tuple[bool, str]:
    if inputs.contraindications_disclosed and inputs.special_population_warnings_present:
        return True, "Contraindications and special-population warnings disclosed."
    missing = []
    if not inputs.contraindications_disclosed:
        missing.append("contraindications")
    if not inputs.special_population_warnings_present:
        missing.append("special-population warnings")
    return False, f"Missing: {', '.join(missing)}."


def check_label_compliance(inputs: RegulatoryInputs) -> tuple[bool, str]:
    if inputs.makes_disease_claim:
        return False, "Disease-adjacent or therapeutic claim detected — cross-flag to Gate 3 per methodology."
    return True, "Structure/function claims only; no disease claims detected."


def run_gate1(
    product: Product,
    inputs: RegulatoryInputs,
    brand_alerts_checked: bool = True,
) -> Gate1Result:
    novel_ok, novel_msg = check_novel_food(inputs.category, product.product_name)
    gmp_ok, gmp_msg = check_gmp(inputs)
    gmp_specificity_ok, gmp_specificity_msg = check_gmp_specificity(inputs.category, inputs.gmp_certifying_body)
    batch_ok, batch_msg = check_batch_traceability(inputs)
    safety_ok, safety_msg = check_safety_documentation(inputs)
    label_ok, label_msg = check_label_compliance(inputs)

    alert_note = ""
    if brand_alerts_checked:
        try:
            alerts = check_recent_alerts(product.brand)
            if alerts["found"]:
                alert_note = f" | ACTIVE FSA ALERT for this brand: {alerts['alerts'][0]}"
        except FSAClientError as exc:
            alert_note = f" | FSA Food Alerts lookup failed ({exc}) — verify manually before approving."

    all_pass = novel_ok and gmp_ok and gmp_specificity_ok and batch_ok and safety_ok and label_ok
    result = "PASS" if all_pass else "FAIL"

    return Gate1Result(
        id=product.id,
        supplement=product.supplement,
        brand=product.brand,
        product_name=product.product_name,
        uk_legal_status="PASS" if novel_ok else f"FAIL\n{novel_msg}",
        novel_food_gb=novel_msg,
        gmp_mfg_standard=("PASS\n" if (gmp_ok and gmp_specificity_ok) else "FAIL\n") + gmp_msg + " | " + gmp_specificity_msg,
        batch_traceability=("PASS\n" if batch_ok else "FAIL\n") + batch_msg,
        safety_documentation=("PASS\n" if safety_ok else "FAIL\n") + safety_msg,
        label_compliance=("PASS\n" if label_ok else "FAIL\n") + label_msg,
        result=result,
        correction_applied=None,
        explanation=f"{novel_msg} | {gmp_msg} | {gmp_specificity_msg} | {batch_msg} | {safety_msg} | {label_msg}{alert_note}",
    )
