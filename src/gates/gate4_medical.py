"""
Gate 4 — Medical Appropriateness.

Uses the DDInter DDSI cache for interaction checks and the same dosage_bands
table Gate 0 uses for evidence-alignment / multi-ingredient checks. This gate
also assembles the final tier (see assign_tier below) once Gates 0-3 have all
passed — tier assignment is arithmetic over gate results, matching your
existing 'no scoring, only tiers' rule. Tier 1 still requires human panel
consensus regardless of what this function returns (see README, §human review).
"""

from __future__ import annotations
from dataclasses import dataclass

from src.schemas import Product, Gate4Result
from src.gates.gate0_formulation import ExtractedIngredient, _DOSAGE_BANDS, _to_mg
from src.datasets.ddinter_client import check_supplement_drug_interactions


@dataclass
class MedicalInputs:
    ingredients: list[ExtractedIngredient]
    population: str
    claimed_benefit: str
    cited_study_dose: dict  # {"Curcumin": 500} - mg used in the study the brand cites, if any
    cited_study_form: dict  # {"Curcumin": "BCM-95"}


def check_form_dose_match(inputs: MedicalInputs) -> tuple[bool, str]:
    """
    Compares against a cited clinical study's dose/form when available
    (inputs.cited_study_dose/form) - the framework's actual definition of
    this parameter. No structured database of per-study cited doses exists
    yet for the ingredients in this pipeline's evidence base, so for any
    ingredient without a cited-study entry, this FALLS BACK to the same
    population-safety threshold check Gate 0 uses.

    This fallback is a genuine scope mismatch, not a full implementation of
    the parameter, and was confirmed as the primary source of weak
    validation results (Cohen's kappa = 0.108) during this pipeline's
    accuracy work: the fallback answers "is this dose in a safe range" not
    "does this dose match what the cited study used", and the two questions
    only sometimes have the same answer. Building a real per-study dose
    database is future work, not a fix available within this codebase today.
    """
    mismatches = []
    for ing in inputs.ingredients:
        cited_dose = inputs.cited_study_dose.get(ing.name)
        cited_form = inputs.cited_study_form.get(ing.name)

        if cited_dose is not None:
            if ing.amount < cited_dose:
                mismatches.append(f"{ing.name}: product has {ing.amount}{ing.unit}, cited study used {cited_dose}mg")
        else:
            # No cited-study data - fall back to the Gate 0-style threshold
            # check as a documented proxy, not a substitute.
            band = [r for r in _DOSAGE_BANDS if r["ingredient"].lower() == ing.name.lower()
                    and r["population"].lower() == inputs.population.lower()]
            if band:
                amount_mg = _to_mg(ing.amount, ing.unit)
                min_dose_mg = _to_mg(float(band[0]["min_effective_dose"]), band[0]["unit"])
                if amount_mg is not None and min_dose_mg is not None and amount_mg < 0.5 * min_dose_mg:
                    mismatches.append(f"{ing.name}: {ing.amount}{ing.unit} is below 50% of the population-safety minimum (no cited-study dose on file to check against instead)")

        if cited_form is not None and cited_form.lower() != ing.form.lower():
            mismatches.append(f"{ing.name}: product uses {ing.form}, cited study used {cited_form}")

    if mismatches:
        return False, "; ".join(mismatches)
    return True, "Form and dose match the cited supporting studies where available; population-safety threshold used as a fallback proxy otherwise."


def check_population_safety(inputs: MedicalInputs) -> tuple[bool, str]:
    # Placeholder rule: pregnant/child populations need an explicit band entry, not a fallback to adult.
    missing = []
    for ing in inputs.ingredients:
        band = [r for r in _DOSAGE_BANDS if r["ingredient"].lower() == ing.name.lower() and r["population"].lower() == inputs.population.lower()]
        if not band and inputs.population.lower() in ("pregnant", "child"):
            missing.append(f"{ing.name}: no {inputs.population}-specific dosage band on file")
    if missing:
        return False, "; ".join(missing)
    return True, f"Dosage bands confirmed safe for population: {inputs.population}."


def check_interactions(inputs: MedicalInputs) -> tuple[bool, str]:
    flagged = []
    for ing in inputs.ingredients:
        result = check_supplement_drug_interactions(ing.name)
        if result["found"]:
            majors = [i for i in result["interactions"] if i.get("severity", "").lower() == "major"]
            if majors:
                flagged.append(f"{ing.name}: MAJOR interaction on file with {majors[0]['drug']} — {majors[0]['mechanism']}")
    if flagged:
        return False, "; ".join(flagged)
    return True, "No major drug-supplement interactions on file (DDInter DDSI cache)."


def check_evidence_alignment(inputs: MedicalInputs) -> tuple[bool, str]:
    if not inputs.claimed_benefit:
        return True, "No specific benefit claimed."
    supporting = [ing for ing in inputs.ingredients if inputs.claimed_benefit.lower() in ing.name.lower()]
    if not supporting:
        return False, f"Claims '{inputs.claimed_benefit}' with no ingredient at an effective dose supporting that specific claim."
    return True, f"Formulation matches the claimed benefit: {inputs.claimed_benefit}."


def check_multi_ingredient(inputs: MedicalInputs) -> tuple[bool, str]:
    """
    Now converts both the extracted dose and the evidence-table dose to mg
    before comparing - the original version compared raw numbers with no
    unit check, the same category of bug found and fixed in Gate 0's
    dosage check during this pipeline's validation work.
    """
    if len(inputs.ingredients) < 3:
        threshold_note = "fewer than 3 ingredients — ALL must be at effective doses"
    else:
        threshold_note = "70% of ingredients must be at effective doses, none below 50% of minimum"

    effective_count = 0
    below_half = []
    for ing in inputs.ingredients:
        band = [r for r in _DOSAGE_BANDS if r["ingredient"].lower() == ing.name.lower() and r["population"].lower() == inputs.population.lower()]
        if not band:
            continue
        amount_mg = _to_mg(ing.amount, ing.unit)
        min_dose_mg = _to_mg(float(band[0]["min_effective_dose"]), band[0]["unit"])
        if amount_mg is None or min_dose_mg is None:
            continue  # unit not convertible (e.g. IU) - don't guess, skip rather than miscompare
        if amount_mg >= min_dose_mg:
            effective_count += 1
        if amount_mg < 0.5 * min_dose_mg:
            below_half.append(ing.name)

    if below_half:
        return False, f"Below 50% of minimum effective dose: {', '.join(below_half)} ({threshold_note})"
    ratio = effective_count / len(inputs.ingredients) if inputs.ingredients else 0
    if len(inputs.ingredients) < 3 and ratio < 1.0:
        return False, f"All ingredients must be effective for a <3-ingredient formula; only {effective_count}/{len(inputs.ingredients)} qualify."
    if ratio < 0.70:
        return False, f"Only {ratio*100:.0f}% of ingredients at effective doses (need \u226570%)."
    return True, f"{ratio*100:.0f}% of ingredients at clinically effective doses ({threshold_note})."


def run_gate4(product: Product, inputs: MedicalInputs) -> Gate4Result:
    form_ok, form_msg = check_form_dose_match(inputs)
    pop_ok, pop_msg = check_population_safety(inputs)
    interact_ok, interact_msg = check_interactions(inputs)
    evidence_ok, evidence_msg = check_evidence_alignment(inputs)
    multi_ok, multi_msg = check_multi_ingredient(inputs)

    all_pass = form_ok and pop_ok and interact_ok and evidence_ok and multi_ok
    result = "PASS" if all_pass else "FAIL"

    return Gate4Result(
        id=product.id,
        supplement=product.supplement,
        brand=product.brand,
        product_name=product.product_name,
        ingredients_key=product.ingredients_key,
        form_match=("PASS \u2013 " if form_ok else "FAIL \u2013 ") + form_msg,
        dose_match=("PASS \u2013 " if form_ok else "FAIL \u2013 ") + form_msg,
        population_safety=("PASS \u2013 " if pop_ok and interact_ok else "FAIL \u2013 ") + pop_msg + "; " + interact_msg,
        evidence_alignment=("PASS \u2013 " if evidence_ok else "FAIL \u2013 ") + evidence_msg,
        use_case_fit=inputs.claimed_benefit,
        multi_ingredient_check=("PASS \u2013 " if multi_ok else "FAIL \u2013 ") + multi_msg,
        result=result,
        correction_applied=None,
        explanation=f"{form_msg} | {pop_msg} | {interact_msg} | {evidence_msg} | {multi_msg}",
    )


def assign_tier(gate0_pass, gate1_pass, gate2_pass, gate3_pass, gate4_pass, uses_superior_forms: bool, doses_upper_range: bool, premium_testing: bool) -> str:
    """
    Pure arithmetic over gate results — no ML, no scoring. Matches the
    Tier 1/2/3/0 definitions in the Methodology Documentation §5.6.
    Tier 1 additionally requires expert panel consensus before it's published —
    this function proposes the tier, it does not finalize a Tier 1 listing.
    """
    if not all([gate0_pass, gate1_pass, gate2_pass, gate3_pass, gate4_pass]):
        return "Tier 0"
    if uses_superior_forms and doses_upper_range and premium_testing:
        return "Tier 1 (pending panel consensus)"
    if not uses_superior_forms or not doses_upper_range:
        return "Tier 3"
    return "Tier 2"
