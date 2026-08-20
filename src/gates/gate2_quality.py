"""
Gate 2 — Quality Verification.

This is the gate with no open dataset behind it (see the automation guide,
§3). Every field here comes from OCR/LLM extraction of a submitted COA PDF,
cross-checked against the UKAS accredited-labs list for lab_accreditation.
The rule engine still owns the threshold decisions — extraction never judges
pass/fail, it only reports the numbers it read.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date

CRITICAL_INGREDIENTS = {"folate", "iodine", "iron", "vitamin d"}

from src.schemas import Product, Gate2Result


@dataclass
class QualityInputs:
    coa_provided: bool
    coa_date: date | None
    coa_batch_matches_current_stock: bool
    lab_iso17025_accredited: bool
    lab_name: str | None
    heavy_metals_ppm: dict  # {"lead": 0.2, "mercury": 0.05, "cadmium": 0.1, "arsenic": 0.8}
    microbial_detected: dict  # {"e_coli": False, "salmonella": False}
    label_claim_amount: float
    tested_amount: float
    ingredient_name: str
    packaging_appropriate: bool
    packaging_note: str


USP_LIMITS_PPM = {"lead": 0.5, "mercury": 0.1, "cadmium": 0.3, "arsenic": 1.5}


def check_coa(inputs: QualityInputs) -> tuple[bool, str]:
    if not inputs.coa_provided:
        return False, "No COA provided — no documentation, no listing."
    if inputs.coa_date is None:
        return False, "COA has no date."
    months_old = (date.today() - inputs.coa_date).days / 30
    if months_old > 12:
        return False, f"COA is {months_old:.0f} months old — exceeds 12-month validity."
    if not inputs.coa_batch_matches_current_stock:
        return False, "COA batch number does not match the batch currently on sale."
    return True, f"COA dated {inputs.coa_date.isoformat()}, batch-matched to current stock."


def check_heavy_metals(inputs: QualityInputs) -> tuple[bool, str]:
    over_limit = []
    for metal, limit in USP_LIMITS_PPM.items():
        value = inputs.heavy_metals_ppm.get(metal)
        if value is None:
            over_limit.append(f"{metal}: not tested")
        elif value > limit:
            over_limit.append(f"{metal}: {value}ppm exceeds {limit}ppm limit")
    if over_limit:
        return False, "; ".join(over_limit)
    return True, "All heavy metals within USP limits: " + ", ".join(
        f"{m}={inputs.heavy_metals_ppm.get(m, 'n/a')}ppm" for m in USP_LIMITS_PPM
    )


def check_microbial(inputs: QualityInputs) -> tuple[bool, str]:
    detected = [k for k, v in inputs.microbial_detected.items() if v]
    if detected:
        return False, f"Detected: {', '.join(detected)} — must show not detected."
    return True, "E. coli and Salmonella: not detected."


def check_potency(inputs: QualityInputs) -> tuple[bool, str]:
    if inputs.label_claim_amount == 0:
        return False, "Label claim amount is zero or missing."
    variance = (inputs.tested_amount - inputs.label_claim_amount) / inputs.label_claim_amount
    tolerance = 0.05 if inputs.ingredient_name.lower() in CRITICAL_INGREDIENTS else 0.10
    if variance < -tolerance:
        return False, f"Tested at {variance*100:.1f}% vs label claim — exceeds -{tolerance*100:.0f}% tolerance for {'a critical' if tolerance == 0.05 else 'a standard'} ingredient."
    return True, f"Potency within tolerance: {variance*100:+.1f}% vs label claim (tolerance ±{tolerance*100:.0f}%)."


def check_lab_accreditation(inputs: QualityInputs) -> tuple[bool, str]:
    if not inputs.lab_iso17025_accredited:
        return False, f"Lab '{inputs.lab_name}' not confirmed ISO 17025 accredited — cross-check against the UKAS register."
    return True, f"{inputs.lab_name} is ISO 17025 accredited."


def run_gate2(product: Product, inputs: QualityInputs) -> Gate2Result:
    coa_ok, coa_msg = check_coa(inputs)
    metals_ok, metals_msg = check_heavy_metals(inputs)
    microbial_ok, microbial_msg = check_microbial(inputs)
    potency_ok, potency_msg = check_potency(inputs)
    lab_ok, lab_msg = check_lab_accreditation(inputs)

    all_pass = coa_ok and metals_ok and microbial_ok and potency_ok and lab_ok
    result = "PASS" if all_pass else "FAIL"

    return Gate2Result(
        id=product.id,
        supplement=product.supplement,
        brand=product.brand,
        product_name=product.product_name,
        coa_available=("PASS\n" if coa_ok else "FAIL\n") + coa_msg,
        coa_date=inputs.coa_date.isoformat() if inputs.coa_date else "FAIL - no date",
        heavy_metals=("PASS\n" if metals_ok else "FAIL\n") + metals_msg,
        microbial=("PASS\n" if microbial_ok else "FAIL\n") + microbial_msg,
        potency=("PASS\n" if potency_ok else "FAIL\n") + potency_msg,
        packaging="ADEQUATE\n" + inputs.packaging_note if inputs.packaging_appropriate else "FAIL\n" + inputs.packaging_note,
        lab_accreditation=("PASS\n" if lab_ok else "FAIL\n") + lab_msg,
        result=result,
        correction_applied=None,
        explanation=f"{coa_msg} | {metals_msg} | {microbial_msg} | {potency_msg} | {lab_msg}",
    )
