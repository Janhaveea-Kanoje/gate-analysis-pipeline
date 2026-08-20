"""
Gate 0 — Formulation Viability.

Question: does this formulation actually work, based on evidence about
bioavailability and dosing — not what the label claims?

Every check here is a lookup against src/data/*.csv, never an LLM judgment call.
The extraction layer (src/extraction/, not yet built — see README) is responsible
for turning raw label text into the (ingredient, form, amount, unit) tuples this
module consumes. This module only ever compares numbers and strings that have
already been extracted.
"""

from __future__ import annotations
import csv
from pathlib import Path
from dataclasses import dataclass

from src.schemas import Product, Gate0Result

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class ExtractedIngredient:
    """What the extraction layer must hand this gate for each ingredient in a product."""
    name: str
    form: str
    amount: float
    unit: str


def _load_csv(name: str) -> list[dict]:
    with open(DATA_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


_FORM_TIERS = _load_csv("form_tiers.csv")
_DOSAGE_BANDS = _load_csv("dosage_bands.csv")
_CONTRAINDICATIONS = _load_csv("contraindicated_pairs.csv")


def check_form_quality(ingredient: ExtractedIngredient, use_case: str = "general") -> tuple[bool, str]:
    """
    Uses substring matching, not exact equality - this is the actual logic
    validated in the accuracy work behind this pipeline's reported results
    (Cohen's kappa figures), not the original exact-match design this
    function had before that validation work was done. Exact matching
    against real extracted form text (e.g. an LLM's output, or any other
    extraction source) essentially never succeeds, because form descriptions
    vary in minor wording even when they mean the same specific compound.

    Also applies the same substring-overlap correction found during that
    validation work: "glycinate" is a literal substring of "bisglycinate",
    so a naive substring check would treat every bisglycinate form as also
    matching "glycinate" - the longer, more specific match wins here.
    """
    ingredient_rows = [row for row in _FORM_TIERS if row["ingredient"].lower() == ingredient.name.lower()]
    if not ingredient_rows:
        return False, f"'{ingredient.name}' has no entry in the form-tier table at all — needs a human-added evidence file entry, not an auto-pass."

    candidates = []
    for row in ingredient_rows:
        known_form = row["form"].lower()
        extracted_form = ingredient.form.lower()
        if known_form in extracted_form or extracted_form in known_form:
            candidates.append(row)

    if not candidates:
        return False, f"'{ingredient.form}' for {ingredient.name} did not match any known form in the evidence table — needs a human-added evidence file entry, not an auto-pass."

    # Prefer the longest/most specific matching form text, same
    # substring-overlap fix validated during the accuracy work.
    best = max(candidates, key=lambda r: len(r["form"]))
    if best["tier"] == "Reject":
        return False, f"{ingredient.form} rejected — {best['bioavailability_note']} (source: {best['source']})"
    return True, f"{best['tier']} form — {best['bioavailability_note']} (source: {best['source']})"


UNIT_TO_MG = {"mg": 1, "mcg": 0.001, "µg": 0.001, "ug": 0.001, "g": 1000}


def _to_mg(value: float, unit: str) -> float | None:
    factor = UNIT_TO_MG.get(unit.lower())
    return value * factor if factor else None


def check_dosage_adequacy(ingredient: ExtractedIngredient, population: str = "adult") -> tuple[bool, str]:
    """
    Converts both the extracted dose and the evidence-table dose to mg
    before comparing - the original version of this function compared raw
    numbers with no unit check at all, which silently produces a wrong
    result whenever the extracted unit differs from the stored unit (the
    same category of bug caught and fixed during this pipeline's accuracy
    validation work, e.g. a dose stated in grams compared directly against
    a limit stated in milligrams).
    """
    matches = [
        row for row in _DOSAGE_BANDS
        if row["ingredient"].lower() == ingredient.name.lower()
        and row["population"].lower() == population.lower()
    ]
    if not matches:
        return False, f"No dosage band on file for {ingredient.name} / {population} — route to human review."
    row = matches[0]

    amount_mg = _to_mg(ingredient.amount, ingredient.unit)
    min_dose_mg = _to_mg(float(row["min_effective_dose"]), row["unit"])
    if amount_mg is None or min_dose_mg is None:
        return False, f"Cannot compare {ingredient.unit} against evidence-table unit {row['unit']} — no conversion available (e.g. IU), route to human review rather than guess."

    if amount_mg < 0.5 * min_dose_mg:
        return False, f"{ingredient.amount}{ingredient.unit} is fairy-dusting — under 50% of the {row['min_effective_dose']}{row['unit']} minimum effective dose."
    if row["upper_limit"] not in ("NA", ""):
        upper_limit_mg = _to_mg(float(row["upper_limit"]), row["unit"])
        if upper_limit_mg is not None and amount_mg > upper_limit_mg:
            return False, f"{ingredient.amount}{ingredient.unit} exceeds the safety upper limit of {row['upper_limit']}{row['unit']}."
    return True, f"{ingredient.amount}{ingredient.unit} within the evidence-based range for {population} (min effective: {row['min_effective_dose']}{row['unit']})."


def check_formulation_logic(ingredients: list[ExtractedIngredient], has_lipid_carrier: bool) -> tuple[bool, str]:
    names = {i.name.lower() for i in ingredients}
    issues = []
    for row in _CONTRAINDICATIONS:
        a, b = row["ingredient_a"].lower(), row["ingredient_b"].lower()
        if b == "none-without-fat" and a in names and not has_lipid_carrier:
            issues.append(f"{row['ingredient_a']} needs a lipid carrier — none declared ({row['issue']})")
        elif a in names and b in names:
            issues.append(f"{row['ingredient_a']} + {row['ingredient_b']}: {row['issue']}")
    if issues:
        return False, "; ".join(issues)
    return True, "No contraindicated ingredient combinations detected."


def check_transparency(has_proprietary_blend: bool, all_amounts_declared: bool) -> tuple[bool, str]:
    if has_proprietary_blend:
        return False, "Proprietary blend detected — exact per-ingredient dosages not disclosed."
    if not all_amounts_declared:
        return False, "One or more ingredients missing a declared exact amount."
    return True, "Every ingredient declared with its exact amount."


def check_use_case_match(ingredient: ExtractedIngredient, claimed_use_case: str) -> tuple[bool, str]:
    matches = [
        row for row in _FORM_TIERS
        if row["ingredient"].lower() == ingredient.name.lower()
        and row["form"].lower() == ingredient.form.lower()
    ]
    if not matches:
        return False, "Cannot verify use-case match — form not in lookup table."
    approved_cases = matches[0]["use_case"].lower().split(";")
    if claimed_use_case.lower() in approved_cases or "general" in approved_cases:
        return True, f"{ingredient.form} is appropriate for '{claimed_use_case}'."
    return False, f"{ingredient.form} is not the evidence-preferred form for '{claimed_use_case}' — check against form_tiers.csv use_case column."


def run_gate0(
    product: Product,
    ingredients: list[ExtractedIngredient],
    has_proprietary_blend: bool,
    all_amounts_declared: bool,
    has_lipid_carrier: bool,
    claimed_use_case: str,
) -> Gate0Result:
    """Runs every Gate 0 parameter and produces one row matching the 'Gate 0 — Formulation' sheet."""
    reasons = []

    form_ok, form_msg = True, []
    for ing in ingredients:
        ok, msg = check_form_quality(ing, claimed_use_case)
        form_ok = form_ok and ok
        form_msg.append(msg)

    dose_ok, dose_msg = True, []
    for ing in ingredients:
        ok, msg = check_dosage_adequacy(ing, product.population)
        dose_ok = dose_ok and ok
        dose_msg.append(msg)

    logic_ok, logic_msg = check_formulation_logic(ingredients, has_lipid_carrier)
    transp_ok, transp_msg = check_transparency(has_proprietary_blend, all_amounts_declared)

    usecase_ok, usecase_msg = True, []
    for ing in ingredients:
        ok, msg = check_use_case_match(ing, claimed_use_case)
        usecase_ok = usecase_ok and ok
        usecase_msg.append(msg)

    all_pass = form_ok and dose_ok and logic_ok and transp_ok and usecase_ok
    result = "PASS" if all_pass else "FAIL"

    explanation = " | ".join(form_msg + dose_msg + [logic_msg, transp_msg] + usecase_msg)

    return Gate0Result(
        id=product.id,
        supplement=product.supplement,
        brand=product.brand,
        product_name=product.product_name,
        ingredients_key=product.ingredients_key,
        form_quality="Yes" if form_ok else "No — " + "; ".join(m for m in form_msg if "Reject" in m or "not in" in m),
        dosage_adequacy="Yes" if dose_ok else "No — " + "; ".join(m for m in dose_msg if "fairy" in m or "exceeds" in m),
        formulation_logic="Yes" if logic_ok else f"No — {logic_msg}",
        transparency="Yes" if transp_ok else f"No — {transp_msg}",
        use_case_match="Yes" if usecase_ok else "No — " + "; ".join(m for m in usecase_msg if "not the evidence" in m),
        result=result,
        explanation=explanation,
    )
