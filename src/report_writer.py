"""
Regenerates the CN_Final_Corrected.xlsx sheet structure from pipeline output,
so the research team can open pipeline results in the exact format they
already review manually today. No formulas are written here — every cell is
a final computed value from the rule engine, not a live spreadsheet model.
"""

from __future__ import annotations
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.worksheet.worksheet import Worksheet

from src.schemas import PipelineResult

HEADER_FONT = Font(name="Arial", bold=True, size=10)
BODY_FONT = Font(name="Arial", size=10)
WRAP = Alignment(wrap_text=True, vertical="top")

GATE0_HEADERS = ["#", "Supplement", "Brand", "Product Name", "Ingredients (Key)",
                  "Form Quality", "Dosage Adequacy", "Formulation Logic", "Transparency",
                  "Use Case Match", "Result", "Explanation / Notes"]
GATE1_HEADERS = ["#", "Supplement", "Brand", "Product Name", "UK Legal Status", "Novel Food (GB)",
                  "GMP / Mfg Standard*", "Batch Traceability*", "Safety Documentation",
                  "Label Compliance", "Result", "Correction Applied", "Explanation / Notes"]
GATE2_HEADERS = ["#", "Supplement", "Brand", "Product Name", "COA Available", "COA Date",
                  "Heavy Metals", "Microbial", "Potency", "Packaging", "Lab Accreditation",
                  "Result", "Correction Applied", "Explanation / Notes"]
GATE3_HEADERS = ["#", "Supplement", "Brand", "Full Disclosure", "Regulatory History",
                  "Mfg Location", "Customer Service", "Ethical Marketing", "Result",
                  "Correction Applied", "Explanation / Notes"]
GATE4_HEADERS = ["#", "Supplement", "Brand", "Product Name", "Ingredients (Key)", "Form Match",
                  "Dose Match", "Population Safety", "Evidence Alignment", "Use Case Fit",
                  "Multi-Ingredient Check", "Result", "Correction Applied", "Explanation / Notes"]
PASS_LIST_HEADERS = ["#", "Supplement Category", "Brand Name", "Gate 0", "Gate 1", "Gate 2", "Gate 3", "Gate 4"]


def _write_header(ws: Worksheet, title: str, headers: list[str]):
    ws["A1"] = title
    ws["A1"].font = Font(name="Arial", bold=True, size=12)
    ws.append([])  # spacer row, mirrors the original sheets' parameter-legend row
    ws.append(headers)
    for cell in ws[3]:
        cell.font = HEADER_FONT
    ws.freeze_panes = "A4"


def _autosize(ws: Worksheet, widths: list[int]):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=3, column=i).column_letter].width = w


def write_report(results: list[PipelineResult], output_path: str) -> None:
    wb = Workbook()
    wb.remove(wb.active)

    ws0 = wb.create_sheet("Gate 0 — Formulation")
    _write_header(ws0, "GATE 0 — FORMULATION VIABILITY", GATE0_HEADERS)
    ws1 = wb.create_sheet("Gate 1 — Regulatory")
    _write_header(ws1, "GATE 1 — REGULATORY COMPLIANCE", GATE1_HEADERS)
    ws2 = wb.create_sheet("Gate 2 — Quality")
    _write_header(ws2, "GATE 2 — QUALITY VERIFICATION", GATE2_HEADERS)
    ws3 = wb.create_sheet("Gate 3 — Brand Integrity")
    _write_header(ws3, "GATE 3 — BRAND INTEGRITY", GATE3_HEADERS)
    ws4 = wb.create_sheet("Gate 4 — Medical")
    _write_header(ws4, "GATE 4 — MEDICAL APPROPRIATENESS", GATE4_HEADERS)
    ws_pass = wb.create_sheet("All-Gate PASS List")
    _write_header(ws_pass, "GATE ANALYSIS — SUPPLEMENTS & BRANDS THAT PASSED ALL GATES (0 → 4)", PASS_LIST_HEADERS)

    for r in results:
        if r.gate0:
            g = r.gate0
            ws0.append([g.id, g.supplement, g.brand, g.product_name, g.ingredients_key,
                        g.form_quality, g.dosage_adequacy, g.formulation_logic, g.transparency,
                        g.use_case_match, g.result, g.explanation])
        if r.gate1:
            g = r.gate1
            ws1.append([g.id, g.supplement, g.brand, g.product_name, g.uk_legal_status,
                        g.novel_food_gb, g.gmp_mfg_standard, g.batch_traceability,
                        g.safety_documentation, g.label_compliance, g.result,
                        g.correction_applied, g.explanation])
        if r.gate2:
            g = r.gate2
            ws2.append([g.id, g.supplement, g.brand, g.product_name, g.coa_available, g.coa_date,
                        g.heavy_metals, g.microbial, g.potency, g.packaging, g.lab_accreditation,
                        g.result, g.correction_applied, g.explanation])
        if r.gate3:
            g = r.gate3
            ws3.append([g.id, g.supplement, g.brand, g.full_disclosure, g.regulatory_history,
                        g.mfg_location, g.customer_service, g.ethical_marketing, g.result,
                        g.correction_applied, g.explanation])
        if r.gate4:
            g = r.gate4
            ws4.append([g.id, g.supplement, g.brand, g.product_name, g.ingredients_key,
                        g.form_match, g.dose_match, g.population_safety, g.evidence_alignment,
                        g.use_case_fit, g.multi_ingredient_check, g.result, g.correction_applied,
                        g.explanation])
        if r.final_tier != "Tier 0":
            ws_pass.append([
                r.product.id, r.product.supplement, r.product.brand,
                "Yes" if r.gate0 and r.gate0.result == "PASS" else "No",
                "Yes" if r.gate1 and r.gate1.result == "PASS" else "No",
                "Yes" if r.gate2 and r.gate2.result == "PASS" else "No",
                "Yes" if r.gate3 and r.gate3.result == "PASS" else "No",
                "Yes" if r.gate4 and r.gate4.result == "PASS" else "No",
            ])

    for ws in (ws0, ws1, ws2, ws3, ws4, ws_pass):
        for row in ws.iter_rows(min_row=4):
            for cell in row:
                cell.font = BODY_FONT
                cell.alignment = WRAP

    _autosize(ws0, [4, 14, 16, 30, 40, 30, 30, 30, 30, 30, 10, 45])
    _autosize(ws1, [4, 14, 16, 30, 35, 35, 35, 30, 30, 30, 10, 25, 45])
    _autosize(ws2, [4, 14, 16, 30, 35, 15, 35, 35, 30, 25, 30, 10, 25, 45])
    _autosize(ws3, [4, 14, 16, 35, 35, 30, 30, 30, 10, 25, 45])
    _autosize(ws4, [4, 14, 16, 30, 40, 30, 30, 30, 30, 20, 30, 10, 25, 45])
    _autosize(ws_pass, [4, 20, 20, 8, 8, 8, 8, 8])

    wb.save(output_path)
