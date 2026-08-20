"""
Data models for the Gate Analysis pipeline.

Every field name here was taken directly from CN_Final_Corrected.xlsx so that
report_writer.py can regenerate that exact workbook shape from pipeline output.
Do not rename fields without updating both the sheet headers in report_writer.py
and the manual-review team's expectations — they will open this file in Excel.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Literal

Verdict = Literal["PASS", "FAIL", "CONDITIONAL", "ADEQUATE", "NOT_FOUND"]


@dataclass
class Product:
    """A single brand x supplement candidate entering the pipeline."""
    id: int
    supplement: str
    brand: str
    product_name: str
    ingredients_key: str  # free-text ingredient/dose string, as it appears on the label
    population: str = "adult"  # adult | child | elderly | pregnant


@dataclass
class Gate0Result:
    """Mirrors the 'Gate 0 — Formulation' sheet."""
    id: int
    supplement: str
    brand: str
    product_name: str
    ingredients_key: str
    form_quality: str          # "Yes" / "No" + reason, kept as free text to match existing sheet style
    dosage_adequacy: str
    formulation_logic: str
    transparency: str
    use_case_match: str
    result: Verdict
    explanation: str


@dataclass
class Gate1Result:
    """Mirrors the 'Gate 1 — Regulatory' sheet."""
    id: int
    supplement: str
    brand: str
    product_name: str
    uk_legal_status: str
    novel_food_gb: str
    gmp_mfg_standard: str
    batch_traceability: str
    safety_documentation: str
    label_compliance: str
    result: Verdict
    correction_applied: Optional[str]
    explanation: str


@dataclass
class Gate2Result:
    """Mirrors the 'Gate 2 — Quality' sheet."""
    id: int
    supplement: str
    brand: str
    product_name: str
    coa_available: str
    coa_date: str
    heavy_metals: str
    microbial: str
    potency: str
    packaging: str
    lab_accreditation: str
    result: Verdict
    correction_applied: Optional[str]
    explanation: str


@dataclass
class Gate3Result:
    """Mirrors the 'Gate 3 — Brand Integrity' sheet."""
    id: int
    supplement: str
    brand: str
    full_disclosure: str
    regulatory_history: str
    mfg_location: str
    customer_service: str
    ethical_marketing: str
    result: Verdict
    correction_applied: Optional[str]
    explanation: str


@dataclass
class Gate4Result:
    """Mirrors the 'Gate 4 — Medical' sheet."""
    id: int
    supplement: str
    brand: str
    product_name: str
    ingredients_key: str
    form_match: str
    dose_match: str
    population_safety: str
    evidence_alignment: str
    use_case_fit: str
    multi_ingredient_check: str
    result: Verdict
    correction_applied: Optional[str]
    explanation: str


@dataclass
class PipelineResult:
    """Everything the pipeline produced for one product, across whichever gates it reached."""
    product: Product
    gate0: Optional[Gate0Result] = None
    gate1: Optional[Gate1Result] = None
    gate2: Optional[Gate2Result] = None
    gate3: Optional[Gate3Result] = None
    gate4: Optional[Gate4Result] = None
    final_tier: str = "Tier 0"  # Tier 1 / Tier 2 / Tier 3 / Tier 0
    stopped_at_gate: Optional[int] = None  # which gate ended evaluation, if any
    needs_human_review: bool = False
    review_reason: str = ""
