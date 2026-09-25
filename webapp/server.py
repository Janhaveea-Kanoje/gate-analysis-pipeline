"""
Flask backend for the Gate Analysis web app.

Reuses the existing pipeline code exactly as-is (src.pipeline.run_pipeline,
all five gate modules, src.schemas) - nothing about the actual verification
logic changes here, only how a frontend talks to it. This replaces the
earlier Streamlit version, which fought against having a real single-row
header (logo + nav + button together) the way this project's reference
design required.
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, render_template
import pandas as pd

from src.schemas import Product
from src.gates.gate0_formulation import ExtractedIngredient, _FORM_TIERS, _DOSAGE_BANDS
from src.gates.gate1_regulatory import RegulatoryInputs
from src.gates.gate2_quality import QualityInputs
from src.gates.gate3_brand import BrandInputs
from src.gates.gate4_medical import MedicalInputs
from src.pipeline import run_pipeline

app = Flask(__name__)

FORMS_DF = pd.DataFrame(_FORM_TIERS)
DOSAGE_DF = pd.DataFrame(_DOSAGE_BANDS)

_GT_CACHE = None


def load_ground_truth():
    global _GT_CACHE
    if _GT_CACHE is not None:
        return _GT_CACHE
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "CN_Final_Corrected.xlsx"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "CN_Final_Corrected.xlsx"),
    ]
    for path in candidates:
        if os.path.exists(path):
            df = pd.read_excel(path, sheet_name="Gate 0 — Formulation", header=2)
            _GT_CACHE = df[["Supplement", "Brand", "Product Name"]].dropna()
            return _GT_CACHE
    _GT_CACHE = pd.DataFrame(columns=["Supplement", "Brand", "Product Name"])
    return _GT_CACHE


# ---------- Page routes ----------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/try-a-product")
def try_a_product():
    return render_template("try_a_product.html")


@app.route("/accuracy")
def accuracy():
    return render_template("accuracy.html")


@app.route("/methodology")
def methodology():
    return render_template("methodology.html")


# ---------- API routes: real evidence-base data, no fabricated content ----------

@app.route("/api/categories")
def api_categories():
    return jsonify(sorted(FORMS_DF["ingredient"].unique().tolist()))


@app.route("/api/forms/<category>")
def api_forms(category):
    rows = FORMS_DF[FORMS_DF["ingredient"] == category]
    return jsonify([
        {"form": r["form"], "tier": r["tier"], "use_case": r.get("use_case", "")}
        for _, r in rows.iterrows()
    ])


@app.route("/api/dosage/<category>")
def api_dosage(category):
    rows = DOSAGE_DF[DOSAGE_DF["ingredient"] == category]
    if rows.empty:
        return jsonify(None)
    r = rows.iloc[0]
    return jsonify({
        "min_effective_dose": r["min_effective_dose"],
        "optimal_low": r["optimal_low"],
        "optimal_high": r["optimal_high"],
        "upper_limit": r["upper_limit"],
        "unit": r["unit"],
    })


@app.route("/api/brands/<category>")
def api_brands(category):
    gt = load_ground_truth()
    brands = sorted(gt[gt["Supplement"] == category]["Brand"].unique().tolist())
    return jsonify(brands)


@app.route("/api/products/<category>/<brand>")
def api_products(category, brand):
    gt = load_ground_truth()
    products = sorted(gt[(gt["Supplement"] == category) & (gt["Brand"] == brand)]["Product Name"].unique().tolist())
    return jsonify(products)


@app.route("/api/run-pipeline", methods=["POST"])
def api_run_pipeline():
    data = request.json
    try:
        ingredients = [ExtractedIngredient(
            name=data["category"], form=data["form"], amount=float(data["amount"]), unit=data["unit"]
        )]
        product = Product(
            id=1, supplement=data["category"], brand=data["brand"], product_name=data["product_name"],
            ingredients_key=f"{data['category']} {data['form']} {data['amount']}{data['unit']}",
            population=data.get("population", "adult"),
        )
        gate0_extra = {
            "has_proprietary_blend": False, "all_amounts_declared": True,
            "has_lipid_carrier": True, "claimed_use_case": data.get("claimed_use_case", "general"),
            "uses_superior_forms": data.get("tier") == "Superior", "doses_upper_range": False,
        }
        adv = data.get("advanced", {})
        gate1_inputs = RegulatoryInputs(
            category=data["category"],
            gmp_certifying_body=adv.get("gmp_body") if adv.get("gmp_body") != "None / Unknown" else None,
            gmp_certificate_current=adv.get("gmp_body") not in (None, "None / Unknown"),
            gmp_facility_matches_label=adv.get("gmp_body") not in (None, "None / Unknown"),
            has_batch_lot_number=adv.get("has_batch", True),
            contraindications_disclosed=adv.get("contraindications_disclosed", True),
            special_population_warnings_present=True,
            makes_disease_claim=adv.get("makes_disease_claim", False),
        )
        gate2_inputs = QualityInputs(
            coa_provided=True, coa_date=date.today(), coa_batch_matches_current_stock=True,
            lab_iso17025_accredited=True, lab_name="Demo Lab",
            heavy_metals_ppm={
                "lead": adv.get("lead", 0.05), "mercury": adv.get("mercury", 0.01),
                "cadmium": adv.get("cadmium", 0.02), "arsenic": adv.get("arsenic", 0.1),
            },
            microbial_detected={"e_coli": False, "salmonella": False},
            label_claim_amount=float(data["amount"]), tested_amount=float(adv.get("tested_amount", data["amount"])),
            ingredient_name=data["category"], packaging_appropriate=True, packaging_note="Opaque bottle.",
        )
        gate3_inputs = BrandInputs(
            all_ingredients_disclosed=True,
            disclosure_text=adv.get("disclosure_text", f"Full ingredients listed, {data['brand']} identity disclosed"),
            mfg_location_disclosed=True, mfg_location_verifiable=True,
            customer_service_tested=True, customer_service_result="PASS - responded within 24h",
            fabricated_testimonials_detected=False, disease_claims_in_marketing=adv.get("makes_disease_claim", False),
            misleading_imagery_detected=False,
        )
        gate4_inputs = MedicalInputs(
            ingredients=ingredients, population=data.get("population", "adult"),
            claimed_benefit=data.get("claimed_use_case", ""),
            cited_study_dose={data["category"]: adv["cited_dose"]} if adv.get("cited_dose", 0) > 0 else {},
            cited_study_form={data["category"]: adv["cited_form"]} if adv.get("cited_form") else {},
        )

        result = run_pipeline(product, ingredients, gate0_extra, gate1_inputs, gate2_inputs, gate3_inputs, gate4_inputs)

        def gate_json(g):
            if g is None:
                return None
            return {"result": g.result, "explanation": g.explanation}

        return jsonify({
            "stopped_at_gate": result.stopped_at_gate,
            "final_tier": result.final_tier,
            "needs_human_review": result.needs_human_review,
            "gate0": gate_json(result.gate0),
            "gate1": gate_json(result.gate1),
            "gate2": gate_json(result.gate2),
            "gate3": gate_json(result.gate3),
            "gate4": gate_json(result.gate4),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
