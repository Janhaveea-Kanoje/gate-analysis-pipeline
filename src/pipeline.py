"""
Sequential pipeline orchestrator: Gate 0 -> Gate 1 -> Gate 2 -> Gate 3 -> Gate 4.

Per the methodology doc: "A product must fully pass one gate before proceeding
to the next." This orchestrator enforces that — a FAIL at any gate stops
evaluation and the product is logged with stopped_at_gate set, matching your
existing 'FAIL early, document the reason' philosophy.

This file intentionally does NOT call any LLM. It only calls gate functions,
which only do table lookups and arithmetic. Wire in the extraction layer
(turning raw brand submissions into the *Inputs objects below) as a separate
step that runs BEFORE this orchestrator, not inside it — keep 'read the
document' and 'apply the rule' as two different, independently testable
pieces of code.
"""

from __future__ import annotations
from src.schemas import Product, PipelineResult
from src.gates.gate0_formulation import run_gate0, ExtractedIngredient
from src.gates.gate1_regulatory import run_gate1, RegulatoryInputs
from src.gates.gate2_quality import run_gate2, QualityInputs
from src.gates.gate3_brand import run_gate3, BrandInputs
from src.gates.gate4_medical import run_gate4, MedicalInputs, assign_tier


def run_pipeline(
    product: Product,
    ingredients: list[ExtractedIngredient],
    gate0_extra: dict,
    gate1_inputs: RegulatoryInputs,
    gate2_inputs: QualityInputs,
    gate3_inputs: BrandInputs,
    gate4_inputs: MedicalInputs,
) -> PipelineResult:
    result = PipelineResult(product=product)

    result.gate0 = run_gate0(
        product, ingredients,
        has_proprietary_blend=gate0_extra.get("has_proprietary_blend", False),
        all_amounts_declared=gate0_extra.get("all_amounts_declared", True),
        has_lipid_carrier=gate0_extra.get("has_lipid_carrier", True),
        claimed_use_case=gate0_extra.get("claimed_use_case", "general"),
    )
    if result.gate0.result != "PASS":
        result.stopped_at_gate = 0
        return result

    result.gate1 = run_gate1(product, gate1_inputs)
    if result.gate1.result != "PASS":
        result.stopped_at_gate = 1
        return result

    result.gate2 = run_gate2(product, gate2_inputs)
    if result.gate2.result != "PASS":
        result.stopped_at_gate = 2
        return result

    result.gate3 = run_gate3(product, gate3_inputs)
    if result.gate3.result != "PASS":
        result.stopped_at_gate = 3
        return result

    result.gate4 = run_gate4(product, gate4_inputs)
    if result.gate4.result != "PASS":
        result.stopped_at_gate = 4
        return result

    result.final_tier = assign_tier(
        gate0_pass=True, gate1_pass=True, gate2_pass=True, gate3_pass=True, gate4_pass=True,
        uses_superior_forms=gate0_extra.get("uses_superior_forms", False),
        doses_upper_range=gate0_extra.get("doses_upper_range", False),
        premium_testing=gate2_inputs.lab_iso17025_accredited,
    )
    result.needs_human_review = result.final_tier.startswith("Tier 1")
    result.review_reason = "Tier 1 candidate — requires expert panel consensus before listing." if result.needs_human_review else ""
    return result
