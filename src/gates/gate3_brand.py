"""
Gate 3 — Brand Integrity.

Full Disclosure and Regulatory History are checkable against Companies House
(UK) and the FSA Food Alerts API respectively. Customer Service responsiveness
is intentionally NOT automated here — see README — it must stay a human test.
"""

from __future__ import annotations
from dataclasses import dataclass

from src.schemas import Product, Gate3Result
from src.datasets.fsa_client import check_recent_alerts, FSAClientError
from src.datasets.companies_house_client import check_company_exists, extract_company_name, CompaniesHouseError


@dataclass
class BrandInputs:
    all_ingredients_disclosed: bool
    disclosure_text: str  # the free-text disclosure justification, used to extract a real company name if stated
    mfg_location_disclosed: bool
    mfg_location_verifiable: bool
    customer_service_tested: bool  # must be True — this parameter cannot be auto-PASSed
    customer_service_result: str
    fabricated_testimonials_detected: bool
    disease_claims_in_marketing: bool
    misleading_imagery_detected: bool


def check_full_disclosure(brand: str, inputs: BrandInputs) -> tuple[bool, str]:
    """
    Calls Companies House directly rather than accepting a pre-computed
    boolean - an earlier version of this function expected the caller to
    have already verified the company, with no client actually wired in to
    do that verification anywhere in this codebase.

    KNOWN LIMITATION, not fixable by better matching: validated against
    real ground truth, this check only tests company existence. "Full
    Disclosure" in the source framework is a compound criterion - company
    existence, facility/GMP disclosure, and correct brand attribution
    together - of which this tests only the first component. Two confirmed
    cases in validation failed manually for reasons this check cannot
    detect: one for missing facility/GMP disclosure on an otherwise
    verified company, one because the product was not actually made by the
    brand it was listed under at all.
    """
    if not inputs.all_ingredients_disclosed:
        return False, "Ingredient list is incomplete or undisclosed."

    company_name = extract_company_name(inputs.disclosure_text, brand)
    try:
        result = check_company_exists(company_name)
    except CompaniesHouseError as exc:
        return False, f"Companies House lookup failed ({exc}) — route to human review, do not assume PASS"

    if result["found"]:
        return True, f"Complete ingredient disclosure; company verified — {result['company_name']} (no. {result['company_number']})"
    return False, f"Could not verify an active company matching '{company_name}' on Companies House."


def check_regulatory_history(brand: str) -> tuple[bool, str]:
    try:
        alerts = check_recent_alerts(brand)
    except FSAClientError as exc:
        return False, f"FSA Food Alerts lookup failed ({exc}) — route to human review, do not assume clean history."
    if alerts["found"]:
        first = alerts["alerts"][0]
        title = first.get("title", "unspecified alert")
        return False, f"Active FSA alert found for this brand: {title}"
    return True, "No FSA food-safety alerts found in the checked window (does not cover ASA/advertising rulings — see Gate 3 limitations)."


def check_mfg_location(inputs: BrandInputs) -> tuple[bool, str]:
    if inputs.mfg_location_disclosed and inputs.mfg_location_verifiable:
        return True, "Manufacturing location disclosed and verifiable."
    return False, "Manufacturing location undisclosed or unverifiable — refusal to confirm is a transparency failure."


def check_customer_service(inputs: BrandInputs) -> tuple[bool, str]:
    if not inputs.customer_service_tested:
        return False, "Customer service has not been directly tested — this parameter cannot be marked PASS untested."
    return inputs.customer_service_result.upper().startswith("PASS"), inputs.customer_service_result


def check_ethical_marketing(inputs: BrandInputs) -> tuple[bool, str]:
    issues = []
    if inputs.fabricated_testimonials_detected:
        issues.append("fabricated testimonials")
    if inputs.disease_claims_in_marketing:
        issues.append("disease claims")
    if inputs.misleading_imagery_detected:
        issues.append("misleading before/after imagery")
    if issues:
        return False, f"Issues found: {', '.join(issues)}."
    return True, "No fabricated testimonials, disease claims, or misleading imagery detected."


def run_gate3(product: Product, inputs: BrandInputs) -> Gate3Result:
    disclosure_ok, disclosure_msg = check_full_disclosure(product.brand, inputs)
    history_ok, history_msg = check_regulatory_history(product.brand)
    location_ok, location_msg = check_mfg_location(inputs)
    service_ok, service_msg = check_customer_service(inputs)
    ethics_ok, ethics_msg = check_ethical_marketing(inputs)

    all_pass = disclosure_ok and history_ok and location_ok and service_ok and ethics_ok
    result = "PASS" if all_pass else "FAIL"

    return Gate3Result(
        id=product.id,
        supplement=product.supplement,
        brand=product.brand,
        full_disclosure=("PASS \u2013 " if disclosure_ok else "FAIL \u2013 ") + disclosure_msg,
        regulatory_history=("PASS \u2013 " if history_ok else "FAIL \u2013 ") + history_msg,
        mfg_location=("PASS \u2013 " if location_ok else "FAIL \u2013 ") + location_msg,
        customer_service=("PASS \u2013 " if service_ok else "FAIL \u2013 ") + service_msg,
        ethical_marketing=("PASS \u2013 " if ethics_ok else "FAIL \u2013 ") + ethics_msg,
        result=result,
        correction_applied=None,
        explanation=f"{disclosure_msg} | {history_msg} | {location_msg} | {service_msg} | {ethics_msg}",
    )
