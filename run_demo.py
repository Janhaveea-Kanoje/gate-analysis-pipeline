"""
Runs two demo products through the full pipeline and writes an output workbook
that mirrors CN_Final_Corrected.xlsx's sheet structure.

Run from the project root:
    python run_demo.py

These two products are deliberately modeled on real rows from your own xlsx
(BetterYou-style Magnesium and a curcumin product) so you can compare the
automated output against your manual analysis directly.
"""

import os
from datetime import date
from src.schemas import Product
from src.gates.gate0_formulation import ExtractedIngredient
from src.gates.gate1_regulatory import RegulatoryInputs
from src.gates.gate2_quality import QualityInputs
from src.gates.gate3_brand import BrandInputs
from src.gates.gate4_medical import MedicalInputs
from src.pipeline import run_pipeline
from src.report_writer import write_report


def build_magnesium_gold_standard():
    product = Product(
        id=1, supplement="Magnesium", brand="BetterYou",
        product_name="BetterYou Magnesium 400mg + B6",
        ingredients_key="Magnesium Bisglycinate 400mg, Vitamin B6 2mg",
    )
    ingredients = [ExtractedIngredient(name="Magnesium", form="Bisglycinate", amount=400, unit="mg")]
    gate0_extra = {
        "has_proprietary_blend": False, "all_amounts_declared": True,
        "has_lipid_carrier": True, "claimed_use_case": "general",
        "uses_superior_forms": True, "doses_upper_range": True,
    }
    gate1 = RegulatoryInputs(
        category="Magnesium", gmp_certifying_body="NSF",
        gmp_certificate_current=True, gmp_facility_matches_label=True,
        has_batch_lot_number=True, contraindications_disclosed=True,
        special_population_warnings_present=True, makes_disease_claim=False,
    )
    gate2 = QualityInputs(
        coa_provided=True, coa_date=date(2026, 1, 15), coa_batch_matches_current_stock=True,
        lab_iso17025_accredited=True, lab_name="Eurofins",
        heavy_metals_ppm={"lead": 0.1, "mercury": 0.02, "cadmium": 0.05, "arsenic": 0.3},
        microbial_detected={"e_coli": False, "salmonella": False},
        label_claim_amount=400, tested_amount=410, ingredient_name="Magnesium",
        packaging_appropriate=True, packaging_note="Opaque bottle, moisture-resistant.",
    )
    gate3 = BrandInputs(
        all_ingredients_disclosed=True,
        disclosure_text="BetterYou Ltd, Companies House verified",
        mfg_location_disclosed=True, mfg_location_verifiable=True,
        customer_service_tested=True, customer_service_result="PASS - responded within 24h, working returns policy",
        fabricated_testimonials_detected=False, disease_claims_in_marketing=False,
        misleading_imagery_detected=False,
    )
    gate4 = MedicalInputs(
        ingredients=ingredients, population="adult", claimed_benefit="",
        cited_study_dose={}, cited_study_form={},
    )
    return product, ingredients, gate0_extra, gate1, gate2, gate3, gate4


def build_underdosed_curcumin_fail():
    product = Product(
        id=2, supplement="Curcumin", brand="Generic Brand X",
        product_name="Generic Brand X Turmeric Curcumin",
        ingredients_key="Curcumin 100mg (no piperine)",
    )
    ingredients = [ExtractedIngredient(name="Curcumin", form="Plain Curcumin (no piperine/lipid)", amount=100, unit="mg")]
    gate0_extra = {
        "has_proprietary_blend": False, "all_amounts_declared": True,
        "has_lipid_carrier": False, "claimed_use_case": "inflammation",
        "uses_superior_forms": False, "doses_upper_range": False,
    }
    # This product fails Gate 0 (form quality + dosage) so it never reaches later gates —
    # but we still build placeholder inputs to keep the function signature simple for the demo.
    gate1 = RegulatoryInputs(
        category="Curcumin", gmp_certifying_body=None,
        gmp_certificate_current=False, gmp_facility_matches_label=False,
        has_batch_lot_number=False, contraindications_disclosed=False,
        special_population_warnings_present=False, makes_disease_claim=True,
    )
    gate2 = QualityInputs(
        coa_provided=False, coa_date=None, coa_batch_matches_current_stock=False,
        lab_iso17025_accredited=False, lab_name=None, heavy_metals_ppm={},
        microbial_detected={}, label_claim_amount=100, tested_amount=0,
        ingredient_name="Curcumin", packaging_appropriate=False, packaging_note="Clear bottle.",
    )
    gate3 = BrandInputs(
        all_ingredients_disclosed=False,
        disclosure_text="",
        mfg_location_disclosed=False, mfg_location_verifiable=False,
        customer_service_tested=False, customer_service_result="",
        fabricated_testimonials_detected=True, disease_claims_in_marketing=True,
        misleading_imagery_detected=False,
    )
    gate4 = MedicalInputs(ingredients=ingredients, population="adult", claimed_benefit="",
                           cited_study_dose={"Curcumin": 500}, cited_study_form={"Curcumin": "BCM-95"})
    return product, ingredients, gate0_extra, gate1, gate2, gate3, gate4


def build_zinc_full_pipeline_pass():
    """
    A real, evidence-backed case chosen specifically to clear Gate 0 and
    flow through to Gate 1 and Gate 3, exercising their live network calls
    (FSA Novel Food register, FSA Food Alerts, Companies House) - the two
    earlier demo products both failed at Gate 0, which meant this pipeline's
    live network integration had never actually been run end-to-end.

    Zinc Picolinate at 15mg is a genuine Superior-tier form (src/data/
    form_tiers.csv) within the evidence-based adult dosage range (8-25mg,
    src/data/dosage_bands.csv), and "Picolinate" does not contain "pidolate"
    so it correctly should NOT trigger Gate 1's Zinc/Novel-Food qualifier
    check. Healthspan is used as the brand since it independently extracted
    a real, verifiable "Healthspan Ltd" company name during this pipeline's
    validation work - a reasonable real-world test case for Companies House.
    """
    product = Product(
        id=3, supplement="Zinc", brand="Healthspan",
        product_name="Healthspan Zinc Picolinate 15mg — Immune Support",
        ingredients_key="Zinc Picolinate 15mg",
    )
    ingredients = [ExtractedIngredient(name="Zinc", form="Picolinate", amount=15, unit="mg")]
    gate0_extra = {
        "has_proprietary_blend": False, "all_amounts_declared": True,
        "has_lipid_carrier": True, "claimed_use_case": "immunity",
        "uses_superior_forms": True, "doses_upper_range": False,
    }
    gate1 = RegulatoryInputs(
        category="Zinc", gmp_certifying_body="BRCGS",
        gmp_certificate_current=True, gmp_facility_matches_label=True,
        has_batch_lot_number=True, contraindications_disclosed=True,
        special_population_warnings_present=True, makes_disease_claim=False,
    )
    gate2 = QualityInputs(
        coa_provided=True, coa_date=date(2026, 2, 1), coa_batch_matches_current_stock=True,
        lab_iso17025_accredited=True, lab_name="Eurofins",
        heavy_metals_ppm={"lead": 0.05, "mercury": 0.01, "cadmium": 0.02, "arsenic": 0.1},
        microbial_detected={"e_coli": False, "salmonella": False},
        label_claim_amount=15, tested_amount=15.4, ingredient_name="Zinc",
        packaging_appropriate=True, packaging_note="Opaque bottle.",
    )
    gate3 = BrandInputs(
        all_ingredients_disclosed=True,
        disclosure_text="Full ingredients listed, Healthspan Ltd identity and contacts disclosed",
        mfg_location_disclosed=True, mfg_location_verifiable=True,
        customer_service_tested=True, customer_service_result="PASS - responded within 24h",
        fabricated_testimonials_detected=False, disease_claims_in_marketing=False,
        misleading_imagery_detected=False,
    )
    gate4 = MedicalInputs(
        ingredients=ingredients, population="adult", claimed_benefit="",
        cited_study_dose={}, cited_study_form={},
    )
    return product, ingredients, gate0_extra, gate1, gate2, gate3, gate4


def build_multi_ingredient_contraindication_fail():
    """
    Proves the new multi-ingredient Formulation Logic capability end-to-end.
    Both Copper Bisglycinate and Zinc Picolinate individually have Superior-
    tier forms and doses within their own evidence-based ranges - so this
    product would PASS Gate 0 entirely under the old single-ingredient
    calling pattern used everywhere else in this codebase. Passing both
    ingredients together correctly triggers the Copper+Zinc contraindication
    (added from science_research.xlsx extraction), isolating this one new
    finding cleanly rather than mixing it with an unrelated failure.
    """
    product = Product(
        id=4, supplement="Copper + Zinc", brand="Healthspan",
        product_name="Healthspan Copper & Zinc Complex",
        ingredients_key="Copper Bisglycinate 2mg, Zinc Picolinate 15mg",
    )
    ingredients = [
        ExtractedIngredient(name="Copper", form="Copper bisglycinate (chelate)", amount=2, unit="mg"),
        ExtractedIngredient(name="Zinc", form="Picolinate", amount=15, unit="mg"),
    ]
    gate0_extra = {
        "has_proprietary_blend": False, "all_amounts_declared": True,
        "has_lipid_carrier": True, "claimed_use_case": "immunity",
        "uses_superior_forms": True, "doses_upper_range": False,
    }
    gate1 = RegulatoryInputs(
        category="Copper + Zinc", gmp_certifying_body="NSF",
        gmp_certificate_current=True, gmp_facility_matches_label=True,
        has_batch_lot_number=True, contraindications_disclosed=True,
        special_population_warnings_present=True, makes_disease_claim=False,
    )
    gate2 = QualityInputs(
        coa_provided=True, coa_date=date(2026, 2, 1), coa_batch_matches_current_stock=True,
        lab_iso17025_accredited=True, lab_name="Eurofins",
        heavy_metals_ppm={"lead": 0.05, "mercury": 0.01, "cadmium": 0.02, "arsenic": 0.1},
        microbial_detected={"e_coli": False, "salmonella": False},
        label_claim_amount=2, tested_amount=2.1, ingredient_name="Copper",
        packaging_appropriate=True, packaging_note="Opaque bottle.",
    )
    gate3 = BrandInputs(
        all_ingredients_disclosed=True,
        disclosure_text="Full ingredients listed, Healthspan Ltd identity disclosed",
        mfg_location_disclosed=True, mfg_location_verifiable=True,
        customer_service_tested=True, customer_service_result="PASS - responded within 24h",
        fabricated_testimonials_detected=False, disease_claims_in_marketing=False,
        misleading_imagery_detected=False,
    )
    gate4 = MedicalInputs(
        ingredients=ingredients, population="adult", claimed_benefit="immunity",
        cited_study_dose={}, cited_study_form={},
    )
    return product, ingredients, gate0_extra, gate1, gate2, gate3, gate4


def build_drug_interaction_caution():
    """
    Proves the newly-wired real DDInter drug-interaction data end-to-end.
    Magnesium Citrate individually clears every other Gate 0/4 check
    cleanly (Superior form, dose within evidence-based range) - so this
    isolates the new finding: DDInter's real data shows Magnesium Citrate
    carries a genuine, documented Major-severity interaction (with several
    HIV antiretroviral drugs that divalent cations are known to chelate,
    reducing absorption). This is checked as a general caution about the
    ingredient, not a personalised check against a specific medication list
    the person is taking - see Chapter 3/4's documented scope note on this.
    """
    product = Product(
        id=5, supplement="Magnesium Citrate", brand="Healthspan",
        product_name="Healthspan Magnesium Citrate 300mg",
        ingredients_key="Magnesium Citrate 300mg",
    )
    ingredients = [ExtractedIngredient(name="Magnesium Citrate", form="Clearly dosed magnesium citrate with declared elemental magnesium", amount=300, unit="mg")]
    gate0_extra = {
        "has_proprietary_blend": False, "all_amounts_declared": True,
        "has_lipid_carrier": True, "claimed_use_case": "bowel‑support formulas.",
        "uses_superior_forms": True, "doses_upper_range": False,
    }
    gate1 = RegulatoryInputs(
        category="Magnesium Citrate", gmp_certifying_body="BRCGS",
        gmp_certificate_current=True, gmp_facility_matches_label=True,
        has_batch_lot_number=True, contraindications_disclosed=True,
        special_population_warnings_present=True, makes_disease_claim=False,
    )
    gate2 = QualityInputs(
        coa_provided=True, coa_date=date(2026, 2, 1), coa_batch_matches_current_stock=True,
        lab_iso17025_accredited=True, lab_name="Eurofins",
        heavy_metals_ppm={"lead": 0.05, "mercury": 0.01, "cadmium": 0.02, "arsenic": 0.1},
        microbial_detected={"e_coli": False, "salmonella": False},
        label_claim_amount=300, tested_amount=305, ingredient_name="Magnesium Citrate",
        packaging_appropriate=True, packaging_note="Opaque bottle.",
    )
    gate3 = BrandInputs(
        all_ingredients_disclosed=True,
        disclosure_text="Full ingredients listed, Healthspan Ltd identity disclosed",
        mfg_location_disclosed=True, mfg_location_verifiable=True,
        customer_service_tested=True, customer_service_result="PASS - responded within 24h",
        fabricated_testimonials_detected=False, disease_claims_in_marketing=False,
        misleading_imagery_detected=False,
    )
    gate4 = MedicalInputs(
        ingredients=ingredients, population="adult", claimed_benefit="bowel",
        cited_study_dose={}, cited_study_form={},
    )
    return product, ingredients, gate0_extra, gate1, gate2, gate3, gate4


if __name__ == "__main__":
    results = []
    for builder in (build_magnesium_gold_standard, build_underdosed_curcumin_fail,
                     build_zinc_full_pipeline_pass, build_multi_ingredient_contraindication_fail,
                     build_drug_interaction_caution):
        product, ingredients, gate0_extra, gate1, gate2, gate3, gate4 = builder()
        result = run_pipeline(product, ingredients, gate0_extra, gate1, gate2, gate3, gate4)
        stop = f"stopped at Gate {result.stopped_at_gate}" if result.stopped_at_gate is not None else "cleared all gates"
        print(f"[{product.brand} — {product.product_name}] {stop} | tier={result.final_tier} | needs_review={result.needs_human_review}")
        results.append(result)

    os.makedirs("output", exist_ok=True)
    write_report(results, "output/CN_Automated_Output.xlsx")
    print("\nWrote output/CN_Automated_Output.xlsx — open it and compare against CN_Final_Corrected.xlsx")
