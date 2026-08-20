# Code Nutrition — Automated 5-Gate Supplement Verification Pipeline

An automated implementation of the Code Nutrition framework: a sequential,
binary-gate methodology for evaluating dietary supplement products across
Formulation Viability, Regulatory Compliance, Quality Verification, Brand
Integrity, and Medical Appropriateness. Built as part of an MSc dissertation
(Data Science, AI and Digital Business, GISMA University of Applied Sciences).

This is a working, empirically-validated pipeline, not a prototype — four of
the five gates have been tested against a manually-labelled ground truth of
~3,100 real UK-market products, and three gates make live calls to real
government/registry APIs.

## The headline finding

Across every gate tested, **a deterministic database lookup outperformed
every large-language-model-assisted extraction approach**, even after
multiple rounds of correcting the extraction logic:

| Gate | What it checks | Result |
|---|---|---|
| 0 — Formulation | Form Quality, Dosage Adequacy, Transparency | 70.7% agreement, κ = 0.352 (n=648) |
| 1 — Regulatory | Live UK FSA Novel Food register lookup | **96.5% agreement, κ = 0.412 (n=766)** — strongest result |
| 2 — Quality | Batch lab-certificate verification | Not empirically evaluated — no open dataset of batch-specific COA data exists anywhere (confirmed via a 274-product research search, 100% "Conditional") |
| 3 — Brand Integrity | Live FSA Food Alerts + UK Companies House | 91.4% / 93.2% agreement, weak kappa (severe class imbalance in ground truth) |
| 4 — Medical | Dose match, live DDInter drug-interaction check | 75.9% agreement, κ = 0.153 (n=145) |

Gate 1 needed no AI at all — just a live lookup against a structured
government register — and scored best. Gates 0 and 4, which depend on an LLM
reading unstructured label text before any threshold comparison, scored
lower despite extensive, iterative correction of the extraction logic. This
pattern is the central empirical argument of the dissertation this code
supports.

## Architecture: AI reads, rules decide

Every gate follows one strict rule: a large language model is only ever used
to extract structured data (ingredient, form, dose, unit) from unstructured
text. It never makes a pass/fail decision. Every threshold comparison is
plain, deterministic Python — auditable, not a model's best guess. This is
a deliberate response to documented LLM hallucination risk on precise
numeric claims (see the dissertation's Chapter 2 for the full literature
basis).

## What's real, and what's a documented limitation

**Real, live, and tested:**
- The full Gate 0–4 rule engine (`src/gates/`)
- Live API integrations: UK FSA Novel Food register, UK FSA Food Alerts,
  UK Companies House (`src/datasets/`)
- A 507-row form-tier evidence table and 108-row dosage-band table
  (`src/data/form_tiers.csv`, `dosage_bands.csv`), sourced from a 101-ingredient
  research evidence file
- A 334-record drug/supplement interaction cache (`src/data/ddsi_cache.csv`),
  filtered from DDInter 2.0 and cross-checked against every known ingredient
  category
- 21 curated ingredient-combination contraindication pairs
  (`src/data/contraindicated_pairs.csv`)
- An ingredient-specific GMP certification-tier check (`src/data/recommended_testing.csv`)
  — 55 of 101 ingredients require BRCGS/GFSI certification specifically, not
  just any recognised GMP body
- `src/pipeline.py` — sequential orchestration, stops at the first FAIL
- `src/report_writer.py` — writes output matching the original manual
  ground-truth spreadsheet's structure, for direct row-by-row comparison
- 6 unit tests, all passing (`tests/test_gate0.py`)
- `run_demo.py` — 5 real, worked product cases, including a full clean
  pass through all 5 gates with every live API call succeeding

**Documented, honest limitations (not oversights):**
- Gate 2 has no empirical result — no open dataset of batch-specific lab
  certificates exists. This is stated plainly rather than worked around.
- Gate 4's Form/Dose Match uses a population-safety threshold as a proxy for
  its actual defined requirement (matching a product's dose against the
  specific clinical study it cites) — the real per-study dose database this
  would need does not currently exist.
- The manually-labelled ground truth was produced through independent
  double-labelling (researcher + research-team collaborator, reconciled to
  consensus), but the pre-reconciliation label sets were not retained
  separately, so a formal inter-rater kappa for the ground truth's own
  construction cannot be computed.

Several real implementation bugs were found and fixed during this project's
validation work (a Python NaN-as-truthy defect that silently inflated two
reported accuracy figures; a wrong API endpoint; a JSON-nesting error) — all
are documented with before/after figures in the accompanying dissertation,
Chapter 4.

## Project structure

```
codenutrition-pipeline/
├── run_demo.py                  # entry point — 5 real worked examples
├── requirements.txt
├── .env.example                 # copy to .env, fill in real API keys
├── src/
│   ├── schemas.py                # data models
│   ├── pipeline.py                # orchestrator: Gate 0 -> 1 -> 2 -> 3 -> 4
│   ├── report_writer.py           # writes output/*.xlsx
│   ├── gates/
│   │   ├── gate0_formulation.py    # Form, Dose, Transparency, Formulation Logic, Use Case
│   │   ├── gate1_regulatory.py     # Novel Food (live), GMP + GMP-specificity
│   │   ├── gate2_quality.py        # architecture only — see limitations above
│   │   ├── gate3_brand.py          # Disclosure (live Companies House), Alerts (live FSA)
│   │   └── gate4_medical.py        # Dose match, drug interactions (live DDInter), tier assignment
│   ├── datasets/
│   │   ├── fsa_client.py           # live FSA Novel Food + Food Alerts
│   │   ├── companies_house_client.py  # live UK Companies House
│   │   └── ddinter_client.py       # drug-interaction lookups
│   └── data/                      # evidence tables (see above)
├── tests/
│   └── test_gate0.py
└── .vscode/
```

## Setup

1. Clone this repository and open it in VS Code.
2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in:
   - `COMPANIES_HOUSE_API_KEY` — free key from
     [developer.company-information.service.gov.uk](https://developer.company-information.service.gov.uk/)
   - `ANTHROPIC_API_KEY` — only needed to re-run the LLM extraction scripts
     that built the evidence files; not required to run the demo itself
   - FSA and DDInter data sources are open/keyless — no entry needed
4. Run the demo:
   ```bash
   python run_demo.py
   ```
   This runs all 5 worked product cases end to end and writes
   `output/CN_Automated_Output.xlsx`. Two of the five deliberately fail Gate 0
   (an underdosed magnesium product, a curcumin product missing its
   bioavailability co-factor) — this is the pipeline correctly catching real
   formulation issues, not a bug.
5. Run the tests: `pytest -v`

## Further detail

Full methodology, the complete accuracy validation (with confusion matrices
and iteration histories for every gate), the literature this design is
grounded in, and a critical discussion of where automation is and is not
appropriate in this domain, are in the accompanying dissertation.
