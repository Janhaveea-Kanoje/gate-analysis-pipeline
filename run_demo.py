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
from datetime import date, timedelta
from src.schemas import Product
from src.gates.gate0_formulation import ExtractedIngredient, _FORM_TIERS
from src.gates.gate1_regulatory import RegulatoryInputs
from src.gates.gate2_quality import QualityInputs
from src.gates.gate3_brand import BrandInputs
from src.gates.gate4_medical import MedicalInputs
from src.pipeline import run_pipeline
from src.report_writer import write_report

# A recent, valid COA date for the demo cases (kept relative so the demo never goes stale).
COA_DATE = date.today() - timedelta(days=90)


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
        coa_provided=True, coa_date=COA_DATE, coa_batch_matches_current_stock=True,
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
        coa_provided=True, coa_date=COA_DATE, coa_batch_matches_current_stock=True,
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
        coa_provided=True, coa_date=COA_DATE, coa_batch_matches_current_stock=True,
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
        coa_provided=True, coa_date=COA_DATE, coa_batch_matches_current_stock=True,
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
        ingredients=ingredients, population="adult", claimed_benefit=gate0_extra["claimed_use_case"],
        cited_study_dose={}, cited_study_form={},
    )
    return product, ingredients, gate0_extra, gate1, gate2, gate3, gate4


# ---------------------------------------------------------------------------
# Extended demo set. Each case below is a clean, passing product with exactly ONE
# thing changed, so it stops at a known gate for a known reason. Form strings and
# use cases are read from the same evidence table the live pipeline uses.
# Real brand names appear only on cases that pass or are tested against a real
# documented fact; failing marketing/quality scenarios use clearly fictional brands.
# ---------------------------------------------------------------------------

def _evidence_form(category, tier):
    """Exact form string and first listed use case for a category's first form at the given tier."""
    row = next(r for r in _FORM_TIERS if r["ingredient"] == category and r["tier"] == tier)
    use = next((u.strip() for u in row["use_case"].split(";") if u.strip() and u.strip().lower() != "none"), "general")
    return row["form"], use


def build_case(case_id, category, brand, product_name, tier, amount, *, unit="mg",
               doses_upper_range=False, has_proprietary_blend=False, gmp_body="BRCGS",
               has_batch=True, disease_claim=False, lead_ppm=0.05, tested_ratio=1.0,
               coa_age_days=90, ingredients_disclosed=True,
               customer_service="PASS - responded within 24h",
               fabricated_testimonials=False, marketing_disease_claims=False):
    form, use_case = _evidence_form(category, tier)
    ingredients = [ExtractedIngredient(name=category, form=form, amount=amount, unit=unit)]
    product = Product(id=case_id, supplement=category, brand=brand, product_name=product_name,
                      ingredients_key=f"{category} {amount}{unit}")
    gate0_extra = {
        "has_proprietary_blend": has_proprietary_blend, "all_amounts_declared": True,
        "has_lipid_carrier": True, "claimed_use_case": use_case,
        "uses_superior_forms": tier == "Superior", "doses_upper_range": doses_upper_range,
    }
    gate1 = RegulatoryInputs(
        category=category, gmp_certifying_body=gmp_body, gmp_certificate_current=True,
        gmp_facility_matches_label=True, has_batch_lot_number=has_batch,
        contraindications_disclosed=True, special_population_warnings_present=True,
        makes_disease_claim=disease_claim,
    )
    gate2 = QualityInputs(
        coa_provided=True, coa_date=date.today() - timedelta(days=coa_age_days),
        coa_batch_matches_current_stock=True, lab_iso17025_accredited=True, lab_name="Eurofins",
        heavy_metals_ppm={"lead": lead_ppm, "mercury": 0.01, "cadmium": 0.02, "arsenic": 0.1},
        microbial_detected={"e_coli": False, "salmonella": False},
        label_claim_amount=amount, tested_amount=amount * tested_ratio, ingredient_name=category,
        packaging_appropriate=True, packaging_note="Opaque bottle.",
    )
    gate3 = BrandInputs(
        all_ingredients_disclosed=ingredients_disclosed,
        disclosure_text=f"Full ingredients listed, {brand} identity disclosed",
        mfg_location_disclosed=True, mfg_location_verifiable=True,
        customer_service_tested=True, customer_service_result=customer_service,
        fabricated_testimonials_detected=fabricated_testimonials,
        disease_claims_in_marketing=marketing_disease_claims, misleading_imagery_detected=False,
    )
    gate4 = MedicalInputs(ingredients=ingredients, population="adult", claimed_benefit=use_case,
                          cited_study_dose={}, cited_study_form={})
    return product, ingredients, gate0_extra, gate1, gate2, gate3, gate4


# (builder, expected stopping gate or None for a full pass, expected tier, what it demonstrates)
DEMO_CASES = [
    # --- the original five ---
    (build_magnesium_gold_standard, 0, "Tier 0", "Over the safe upper limit: 400 mg against a 350 mg limit (Gate 0 dose check)"),
    (build_underdosed_curcumin_fail, 0, "Tier 0", "Wrong form and underdosed: plain curcumin with no piperine, 100 mg against a 500 mg minimum (Gate 0)"),
    (build_zinc_full_pipeline_pass, None, "Tier 3", "Clean pass through all five gates, with live FSA and Companies House checks"),
    (build_multi_ingredient_contraindication_fail, 0, "Tier 0", "Two individually fine ingredients that conflict when combined: Copper + Zinc (Gate 0 Formulation Logic)"),
    (build_drug_interaction_caution, 4, "Tier 0", "Clean through Gates 0-3, then a documented Major drug interaction (Dolutegravir) at Gate 4"),
    # --- full passes: what decides the tier ---
    (lambda: build_case(6, "Iron (Bisglycinate)", "Healthspan", "Healthspan Iron Bisglycinate 18mg (demo)", "Superior", 18, doses_upper_range=True),
     None, "Tier 1 (pending panel consensus)", "Superior form + dose at the top of the evidence range + ISO 17025 lab = Tier 1 candidate, flagged for expert-panel review, never auto-published"),
    (lambda: build_case(7, "L-Arginine", "Healthspan", "Healthspan L-Arginine 2000mg (demo)", "Superior", 2000),
     None, "Tier 3", "Everything passes and the form is Superior, but the dose sits at the bottom of the range, so the tier is 3"),
    (lambda: build_case(8, "Lion's Mane", "Healthspan", "Healthspan Lion's Mane Fruiting-Body Powder 3000mg (demo)", "Acceptable", 3000, doses_upper_range=True),
     None, "Tier 3", "An Acceptable (not Superior) form passes every gate but caps the tier at 3, even with a top-of-range dose"),
    # --- Gate 0 ---
    (lambda: build_case(9, "Zinc", "Zorvane Naturals", "Zorvane Zinc Oxide 15mg (demo)", "Reject", 15),
     0, "Tier 0", "A form the evidence file rejects outright (zinc oxide) fails Form Quality"),
    (lambda: build_case(10, "Zinc", "Quillfeather Health", "Quillfeather Zinc Picolinate Blend (demo)", "Superior", 15, has_proprietary_blend=True),
     0, "Tier 0", "Right form, right dose, but a proprietary blend hides the exact amounts (Gate 0 Transparency)"),
    (lambda: build_case(11, "Lion's Mane", "Brindlemoor Labs", "Brindlemoor Lion's Mane 300mg (demo)", "Superior", 300),
     0, "Tier 0", "Fairy-dusting: 300 mg is under half of the 1,000 mg minimum effective dose"),
    # --- Gate 1 ---
    (lambda: build_case(12, "Zinc", "Aldermoss Wellness", "Aldermoss Zinc Picolinate 15mg (demo)", "Superior", 15, gmp_body="NSF"),
     1, "Tier 0", "Zinc needs BRCGS-tier certification; a generic recognised body (NSF) is not enough (ingredient-specific GMP check)"),
    (lambda: build_case(13, "Iron (Bisglycinate)", "Tarnwick Health", "Tarnwick Iron Bisglycinate 16mg (demo)", "Superior", 16, has_batch=False),
     1, "Tier 0", "No batch/lot number on the product, so there is no traceability (Gate 1)"),
    (lambda: build_case(14, "L-Arginine", "Fenlow Nutrition", "Fenlow L-Arginine 2500mg (demo)", "Superior", 2500, disease_claim=True),
     1, "Tier 0", "The label makes a disease claim, which a food supplement may not (Gate 1 label compliance)"),
    # --- Gate 2 ---
    (lambda: build_case(15, "Zinc", "Hollowbrook Health", "Hollowbrook Zinc Picolinate 15mg (demo)", "Superior", 15, lead_ppm=0.9),
     2, "Tier 0", "Lab certificate shows lead at 0.9 ppm against a 0.5 ppm limit (Gate 2 heavy metals)"),
    (lambda: build_case(16, "L-Arginine", "Marrowdale Labs", "Marrowdale L-Arginine 2000mg (demo)", "Superior", 2000, tested_ratio=0.85),
     2, "Tier 0", "The lab measured 15% less than the label claims, outside the 10% tolerance (Gate 2 potency)"),
    (lambda: build_case(17, "Lion's Mane", "Sedgewick Naturals", "Sedgewick Lion's Mane Powder 1500mg (demo)", "Acceptable", 1500, coa_age_days=450),
     2, "Tier 0", "The certificate of analysis is about 15 months old, past the 12-month validity rule"),
    # --- Gate 3 (cases 18-19 use single, unusual-word fictional brands so Companies House finds no matching
    #     company; run_all() flags the case if a name ever matches a real company - see UNVERIFIABLE_BRAND_IDS) ---
    (lambda: build_case(18, "Zinc", "Zqxorvil", "Zqxorvil Zinc Picolinate 15mg (demo)", "Superior", 15, customer_service="FAIL - no response after 3 attempts"),
     3, "Tier 0", "The brand did not respond to a direct customer-service test, which cannot be automated or assumed (Gate 3)"),
    (lambda: build_case(19, "Iron (Bisglycinate)", "Vkthrane", "Vkthrane Iron Bisglycinate 16mg (demo)", "Superior", 16, fabricated_testimonials=True, marketing_disease_claims=True),
     3, "Tier 0", "Marketing uses fabricated testimonials and disease claims (Gate 3 ethical marketing)"),
    (lambda: build_case(20, "L-Arginine", "Oakhollow Health", "Oakhollow L-Arginine 2000mg (demo)", "Superior", 2000, ingredients_disclosed=False),
     3, "Tier 0", "The full ingredient list is not disclosed (Gate 3 full disclosure)"),
    # --- Gate 4 ---
    (lambda: build_case(21, "Zinc", "Healthspan", "Healthspan Zinc Picolinate 6mg (demo, underdosed)", "Superior", 6),
     4, "Tier 0", "Passes Gate 0 (above half the minimum) but is below the minimum effective dose, so Gate 4 requires it to be effective"),
]


# Cases whose brand is fictional: Full Disclosure must come back unverified. The company check accepts the
# first active company the search returns without comparing names, so a fictional name could match an
# unrelated real company. If that happens the demo flags it instead of silently showing it.
UNVERIFIABLE_BRAND_IDS = {18, 19}


def _outcome(result):
    return "Cleared all gates" if result.stopped_at_gate is None else f"Stopped at Gate {result.stopped_at_gate}"


def run_all():
    """Runs every demo case and returns (results, rows) where rows hold expected-vs-actual for the guide."""
    results, rows = [], []
    for builder, expected_stop, expected_tier, shows in DEMO_CASES:
        product, ingredients, gate0_extra, gate1, gate2, gate3, gate4 = builder()
        result = run_pipeline(product, ingredients, gate0_extra, gate1, gate2, gate3, gate4)
        expected = "Cleared all gates" if expected_stop is None else f"Stopped at Gate {expected_stop}"
        actual = _outcome(result)
        tier_ok = expected_stop is not None or result.final_tier == expected_tier
        brand_ok = True
        if product.id in UNVERIFIABLE_BRAND_IDS and result.gate3 is not None:
            brand_ok = result.gate3.full_disclosure.upper().startswith("FAIL")
            if not brand_ok:
                shows += "  [CHECK: this fictional brand matched a real company on Companies House - rename it]"
        rows.append({
            "id": product.id, "product": product.product_name, "brand": product.brand, "shows": shows,
            "expected": expected, "actual": actual, "tier": result.final_tier,
            "ok": actual == expected and tier_ok and brand_ok,
        })
        results.append(result)
    return results, rows


def add_demo_guide(path, rows):
    from openpyxl import load_workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    wb = load_workbook(path)
    ws = wb.create_sheet("Demo Guide", 0)
    ws.append(["DEMO GUIDE - what each case demonstrates, and whether the pipeline behaved as expected"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([])
    ws.append(["Case #", "Product", "Brand", "What it demonstrates", "Expected", "Actual", "Tier", "Matches"])
    for c in ws[3]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="171D24")
    for r in sorted(rows, key=lambda r: (999 if r["actual"] == "Cleared all gates" else int(r["actual"][-1]), r["id"])):
        ws.append([r["id"], r["product"], r["brand"], r["shows"], r["expected"], r["actual"], r["tier"], "Yes" if r["ok"] else "NO - check"])
    for col, w in zip("ABCDEFGH", (8, 46, 22, 70, 20, 20, 30, 12)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=4):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)


if __name__ == "__main__":
    results, rows = run_all()
    for r in rows:
        flag = "ok " if r["ok"] else "!! "
        print(f"{flag}[{r['id']:>2}] {r['brand']} - {r['product']}: {r['actual']} | tier={r['tier']}")

    os.makedirs("output", exist_ok=True)
    out = "output/CN_Automated_Output.xlsx"
    write_report(results, out)
    add_demo_guide(out, rows)

    mismatches = [r for r in rows if not r["ok"]]
    print(f"\nWrote {out} with {len(rows)} cases (see the 'Demo Guide' sheet).")
    if mismatches:
        print(f"{len(mismatches)} case(s) did not behave as expected - usually a live API call failing "
              f"(check COMPANIES_HOUSE_API_KEY and your internet connection): "
              + ", ".join(str(r['id']) for r in mismatches))
    else:
        print("Every case behaved as expected.")
