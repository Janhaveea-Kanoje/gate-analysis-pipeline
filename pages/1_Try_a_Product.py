"""
Try a Product — runs a real product through the actual pipeline code.

Every field is a dropdown wherever a sensible list of real options exists,
each with an "Other (type your own)" fallback for full flexibility:
- Ingredient form: filtered to the selected category, from the evidence base.
- Brand / Product name: filtered to real products for that category, pulled
  directly from the manual ground-truth file (CN_Final_Corrected.xlsx) -
  these are genuine products a reviewer actually checked, not made up.
- Amount: suggested real values (minimum effective / optimal / upper limit)
  from the evidence base's dosage table.
- Unit: the fixed set of units the pipeline actually understands.
"""

import sys
import os
from datetime import date

import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import inject_theme, logo_header, status_pill

from src.schemas import Product
from src.gates.gate0_formulation import ExtractedIngredient, _FORM_TIERS, _DOSAGE_BANDS
from src.gates.gate1_regulatory import RegulatoryInputs
from src.gates.gate2_quality import QualityInputs
from src.gates.gate3_brand import BrandInputs
from src.gates.gate4_medical import MedicalInputs
from src.pipeline import run_pipeline

inject_theme()
logo_header()
st.title("Try a Product")
st.caption("This runs the real pipeline code. Every dropdown below filters to real, evidence-backed or ground-truth options for whatever you pick.")

OTHER = "Other (type your own)"


@st.cache_data
def load_ground_truth():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate_paths = [
        os.path.join(project_root, "CN_Final_Corrected.xlsx"),
        os.path.join(project_root, "output", "CN_Final_Corrected.xlsx"),
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            df = pd.read_excel(path, sheet_name="Gate 0 — Formulation", header=2)
            return df[["Supplement", "Brand", "Product Name"]].dropna()

    st.error(
        f"Could not find CN_Final_Corrected.xlsx. Checked: {candidate_paths}. "
        "Place it in one of these locations, or edit candidate_paths in this function."
    )
    st.stop()


forms_df = pd.DataFrame(_FORM_TIERS)
dosage_df = pd.DataFrame(_DOSAGE_BANDS)
ground_truth = load_ground_truth()

known_categories = sorted(forms_df["ingredient"].unique())

st.subheader("Basic product details")
c1, c2 = st.columns(2)
with c1:
    category = st.selectbox("Ingredient category", options=known_categories,
                              index=known_categories.index("Zinc") if "Zinc" in known_categories else 0)

category_forms = forms_df[forms_df["ingredient"] == category].copy()
form_options = [f"{row['form']} ({row['tier']})" for _, row in category_forms.iterrows()]
form_lookup = {f"{row['form']} ({row['tier']})": row for _, row in category_forms.iterrows()}

with c2:
    if form_options:
        form_display = st.selectbox("Ingredient form", options=form_options,
                                      help="Only forms in the evidence base for this category, including Reject-tier ones so you can demo a failure case.")
        selected_form_row = form_lookup[form_display]
    else:
        st.warning(f"No forms on file for '{category}' yet.")
        selected_form_row = None
        form_display = ""

# --- Brand: real brands that actually sell this category, per ground truth ---
category_gt = ground_truth[ground_truth["Supplement"] == category]
real_brands = sorted(category_gt["Brand"].unique())
brand_options = real_brands + [OTHER]

c3, c4 = st.columns(2)
with c3:
    brand_choice = st.selectbox("Brand", options=brand_options,
                                  help="Real brands that sell this category, from the manual ground-truth review.")
    if brand_choice == OTHER:
        brand = st.text_input("Enter brand name", value="")
    else:
        brand = brand_choice

# --- Product name: real products for this specific category + brand ---
if brand_choice != OTHER:
    brand_products = sorted(category_gt[category_gt["Brand"] == brand_choice]["Product Name"].unique())
else:
    brand_products = []
product_options = brand_products + [OTHER]

with c4:
    product_choice = st.selectbox("Product name", options=product_options,
                                    help="Real products for this brand and category, where available.")
    if product_choice == OTHER or not brand_products:
        product_name = st.text_input("Enter product name", value=f"{brand} {category}" if brand else "")
    else:
        product_name = product_choice

st.subheader("Dose & use case")
c5, c6, c7 = st.columns(3)

dosage_row = dosage_df[dosage_df["ingredient"] == category]
dose_options_map = {}
if not dosage_row.empty:
    r = dosage_row.iloc[0]
    if pd.notna(r["min_effective_dose"]):
        dose_options_map[f"{r['min_effective_dose']}{r['unit']} (minimum effective)"] = float(r["min_effective_dose"])
    if pd.notna(r["optimal_low"]) and r["optimal_low"] != r["min_effective_dose"]:
        dose_options_map[f"{r['optimal_low']}{r['unit']} (optimal low)"] = float(r["optimal_low"])
    if pd.notna(r["optimal_high"]) and r["optimal_high"] != r["optimal_low"]:
        dose_options_map[f"{r['optimal_high']}{r['unit']} (optimal high)"] = float(r["optimal_high"])
    if pd.notna(r["upper_limit"]) and str(r["upper_limit"]) not in ("NA", ""):
        dose_options_map[f"{r['upper_limit']}{r['unit']} (upper safety limit)"] = float(r["upper_limit"])
suggested_unit = dosage_row.iloc[0]["unit"] if not dosage_row.empty else "mg"

dose_display_options = list(dose_options_map.keys()) + [OTHER]

with c5:
    dose_choice = st.selectbox("Amount", options=dose_display_options,
                                 help="Real thresholds from the evidence base for this category.")
    if dose_choice == OTHER:
        amount = st.number_input("Enter amount manually", min_value=0.0, value=15.0, step=1.0)
    else:
        amount = dose_options_map[dose_choice]
        st.caption(f"Using: {amount}")

with c6:
    unit_options = ["mg", "mcg", "g", "IU", OTHER]
    unit_choice = st.selectbox("Unit", options=unit_options,
                                 index=unit_options.index(suggested_unit) if suggested_unit in unit_options else 0)
    if unit_choice == OTHER:
        unit = st.text_input("Enter unit manually", value="mg")
    else:
        unit = unit_choice

use_case_options = []
if selected_form_row is not None and isinstance(selected_form_row.get("use_case"), str):
    use_case_options = [uc.strip() for uc in selected_form_row["use_case"].split(";") if uc.strip() and uc.strip() != "none"]
if not use_case_options:
    use_case_options = ["general"]

with c7:
    claimed_use_case = st.selectbox("Claimed use case", options=use_case_options,
                                      help="Filtered to only the use case(s) this specific form is evidence-backed for.")

population = st.selectbox("Target population", options=["adult", "elderly", "pregnant", "child"], index=0)

with st.expander("Advanced: regulatory, quality & brand details (defaults are a clean, passing example)"):
    st.markdown("**Gate 1 — Regulatory**")
    gc1, gc2 = st.columns(2)
    with gc1:
        gmp_body = st.selectbox("GMP certifying body", ["NSF", "Informed Sport", "USP", "BRCGS", "None / Unknown"])
        has_batch = st.checkbox("Has batch/lot tracking", value=True)
    with gc2:
        makes_disease_claim = st.checkbox("Label makes a disease claim", value=False)
        contraindications_disclosed = st.checkbox("Contraindications disclosed", value=True)

    st.markdown("**Gate 2 — Quality (lab data, hypothetical for this demo)**")
    qc1, qc2, qc3 = st.columns(3)
    with qc1:
        lead = st.number_input("Lead (ppm)", value=0.05, format="%.3f")
        mercury = st.number_input("Mercury (ppm)", value=0.01, format="%.3f")
    with qc2:
        cadmium = st.number_input("Cadmium (ppm)", value=0.02, format="%.3f")
        arsenic = st.number_input("Arsenic (ppm)", value=0.1, format="%.3f")
    with qc3:
        tested_amount = st.number_input("Lab-tested amount (same unit as above)", value=float(amount))

    st.markdown("**Gate 3 — Brand Integrity**")
    disclosure_text = st.text_area(
        "Free-text disclosure statement (as a reviewer might write it)",
        value=f"Full ingredients listed, {brand} Ltd identity and contacts disclosed" if brand else "",
        help="If this mentions 'X Ltd/Limited/PLC', that exact company is checked live on Companies House."
    )

    st.markdown("**Gate 4 — Medical (cited-study data, if you have it — leave blank to use the safety-threshold fallback)**")
    mc1, mc2 = st.columns(2)
    with mc1:
        cited_dose = st.number_input("Cited study dose (mg, 0 = none available)", value=0.0)
    with mc2:
        cited_form = st.text_input("Cited study form (blank = none available)", value="")

run_clicked = st.button("Run through the pipeline", type="primary", disabled=(selected_form_row is None or not brand))

if run_clicked and selected_form_row is not None:
    form = selected_form_row["form"]
    ingredients = [ExtractedIngredient(name=category, form=form, amount=amount, unit=unit)]
    product = Product(id=1, supplement=category, brand=brand, product_name=product_name,
                       ingredients_key=f"{category} {form} {amount}{unit}", population=population)

    gate0_extra = {
        "has_proprietary_blend": False, "all_amounts_declared": True,
        "has_lipid_carrier": True, "claimed_use_case": claimed_use_case,
        "uses_superior_forms": selected_form_row["tier"] == "Superior", "doses_upper_range": False,
    }
    gate1_inputs = RegulatoryInputs(
        category=category,
        gmp_certifying_body=None if gmp_body == "None / Unknown" else gmp_body,
        gmp_certificate_current=gmp_body != "None / Unknown",
        gmp_facility_matches_label=gmp_body != "None / Unknown",
        has_batch_lot_number=has_batch,
        contraindications_disclosed=contraindications_disclosed,
        special_population_warnings_present=True,
        makes_disease_claim=makes_disease_claim,
    )
    gate2_inputs = QualityInputs(
        coa_provided=True, coa_date=date.today(), coa_batch_matches_current_stock=True,
        lab_iso17025_accredited=True, lab_name="Demo Lab",
        heavy_metals_ppm={"lead": lead, "mercury": mercury, "cadmium": cadmium, "arsenic": arsenic},
        microbial_detected={"e_coli": False, "salmonella": False},
        label_claim_amount=amount, tested_amount=tested_amount, ingredient_name=category,
        packaging_appropriate=True, packaging_note="Opaque bottle.",
    )
    gate3_inputs = BrandInputs(
        all_ingredients_disclosed=True, disclosure_text=disclosure_text,
        mfg_location_disclosed=True, mfg_location_verifiable=True,
        customer_service_tested=True, customer_service_result="PASS - responded within 24h",
        fabricated_testimonials_detected=False, disease_claims_in_marketing=makes_disease_claim,
        misleading_imagery_detected=False,
    )
    gate4_inputs = MedicalInputs(
        ingredients=ingredients, population=population, claimed_benefit=claimed_use_case,
        cited_study_dose={category: cited_dose} if cited_dose > 0 else {},
        cited_study_form={category: cited_form} if cited_form else {},
    )

    with st.spinner("Running through Gates 0 → 4 (Gate 1 and Gate 3 make live API calls)..."):
        try:
            result = run_pipeline(product, ingredients, gate0_extra, gate1_inputs, gate2_inputs, gate3_inputs, gate4_inputs)
        except Exception as exc:
            st.error(f"Pipeline error: {exc}")
            st.stop()

    st.divider()
    if result.stopped_at_gate is None:
        st.success(f"Cleared all 5 gates — Final tier: **{result.final_tier}**")
    else:
        st.error(f"Stopped at Gate {result.stopped_at_gate} — Tier: **{result.final_tier}**")

    gate_results = [
        ("Gate 0 — Formulation", result.gate0),
        ("Gate 1 — Regulatory", result.gate1),
        ("Gate 2 — Quality", result.gate2),
        ("Gate 3 — Brand Integrity", result.gate3),
        ("Gate 4 — Medical", result.gate4),
    ]
    for name, gate_result in gate_results:
        if gate_result is None:
            st.write(f"**{name}**: not reached")
            continue
        icon = "PASS" if gate_result.result == "PASS" else "FAIL"
        with st.expander(f"**{name}**", expanded=(gate_result.result != "PASS")):
            st.markdown(status_pill(gate_result.result), unsafe_allow_html=True)
            st.write(gate_result.explanation)
