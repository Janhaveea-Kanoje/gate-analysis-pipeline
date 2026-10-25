# Gate Analysis — Automated 5-Gate Supplement Verification Pipeline

An automated implementation of the Gate Analysis framework: a sequential,
binary-gate methodology for evaluating dietary supplement products across
Formulation Viability, Regulatory Compliance, Quality Verification, Brand
Integrity, and Medical Appropriateness. Built as part of an MSc
dissertation (Data Science, AI and Digital Business, GISMA University of
Applied Sciences).

This is a **partially validated research prototype**. It runs end to end,
and four of the five gates were compared with a manually-labelled ground
truth of ~3,100 rows (2,120 comparisons), each only in part. Gate 2 could
not be tested because no open data exists. Two gates (1 and 3) make live
calls to three public services. Its verdicts are screening aids, not
medical, legal or certification decisions.

## The headline finding

**The one gate that needs no AI reading step — a live lookup in a
structured government register — scored best.** The two gates that depend
on an LLM reading label text (Gates 0 and 4) scored lower, even after
multiple rounds of correcting the extraction logic:

| Gate | What it checks | Result |
|---|---|---|
| 0 — Formulation | Form Quality, Dosage Adequacy, Transparency (3 of 5 parameters) | 70.7% agreement, κ = 0.352 (n=648) |
| 1 — Regulatory | Live UK FSA Novel Food register lookup (Novel Food check only) | **96.5% agreement, κ = 0.412 (n=766)** — strongest result |
| 2 — Quality | Batch lab-certificate verification | Not tested — no open dataset of batch-specific COA data exists (the research team's own search of 274 products found none) |
| 3 — Brand Integrity | Live FSA Food Alerts + UK Companies House (1 of 5 parameters each) | 91.4% / 93.2% agreement, κ = −0.033 / −0.013 (91–98% of labels are one class) |
| 4 — Medical | Dose match (safety-threshold proxy); drug-interaction check (static DDInter cache) | 75.9% agreement, κ = 0.153 (n=145) |

Kappa (κ) is agreement with the chance matches removed: 0 means no better
than guessing, and 0.41–0.60 is conventionally called moderate. It matters
here because most labels share one answer: a check that always says PASS
scores 88.4% agreement on Gate 4.

This is a pattern in these results, not a general law: only one gate is a
clean lookup, and Gate 3's lookups are limited by data coverage and very
skewed labels.

**What the numbers hide.** Where the manual review failed a product, the
engine sometimes passed it: 117 of 239 on Gate 0, 25 of 35 labelled novel
foods on Gate 1, and 11 of 18 on Gate 4. Treat a PASS as a screening result
that a person should confirm.

## Architecture: AI reads, rules decide

Every gate follows one strict rule: a large language model is only ever
used to extract structured data (ingredient, form, dose, unit) from
unstructured text. It never makes a pass/fail decision. Every threshold
comparison is plain, deterministic Python — auditable, not a model's best
guess. This is a deliberate response to documented LLM hallucination risk
on precise numeric claims (see the dissertation's Chapter 2 for the full
literature basis).

A product moves through Gates 0 to 4 in order and stops at the first one it
fails. If it clears all five it earns a tier:

- **Tier 1** — a Superior-grade form, a dose at the top of the evidence
  range and an accredited laboratory. Only ever a candidate: it needs
  expert-panel agreement.
- **Tier 3** — any other product that clears every gate.
- **Tier 0** — a product that failed a gate.
- Tier 2 is part of the design but cannot occur today: Gate 2 already
  requires an accredited laboratory, which is the same fact Tier 2 was
  meant to test.

## What's real, and what's a documented limitation

**Real, live, and tested:**

- The full Gate 0–4 rule engine (`src/gates/`)
- Live API integrations for Gates 1 and 3: UK FSA Novel Food register, UK
  FSA Food Alerts, UK Companies House (`src/datasets/`)
- A 507-row form-tier evidence table and 108-row dosage-band table
  (`src/data/form_tiers.csv`, `dosage_bands.csv`), sourced from a
  101-ingredient research evidence file
- A 334-record drug/supplement interaction cache
  (`src/data/ddsi_cache.csv`): 329 records filtered from DDInter 1.0 bulk
  downloads plus 5 curated seed rows. A static copy, refreshed by hand
- 21 curated ingredient-combination contraindication pairs
  (`src/data/contraindicated_pairs.csv`)
- An ingredient-specific GMP certification-tier check
  (`src/data/recommended_testing.csv`) — 55 of 101 ingredients require
  BRCGS/GFSI certification specifically, not just any recognised GMP body
- `src/pipeline.py` — sequential orchestration, stops at the first FAIL
- `src/report_writer.py` — writes output matching the original manual
  ground-truth spreadsheet's structure, for direct row-by-row comparison
- 16 offline unit tests, all passing (`tests/test_gate0.py` 6,
  `test_gate4.py` 7, `test_demo_cases.py` 3)
- `run_demo.py` — 21 hand-built product cases, each a clean product with
  one thing changed, plus a Demo Guide sheet comparing expected and actual
  results. It flags a fictional brand that matches a real company
- `webapp/` — a small Flask website that runs the pipeline on one product
  at a time

**Documented, honest limitations (not oversights):**

- Partial validation: four gates were tested, each in part (3 of 5
  parameters for Gate 0, 1 of 5 for each Gate 3 check, a dose proxy for
  Gate 4). Gate 2 has no empirical result — no open dataset of
  batch-specific lab certificates exists. This is stated plainly rather
  than worked around.
- Gate 4's Form/Dose Match uses a population-safety threshold as a proxy
  for its actual defined requirement (matching a product's dose against the
  specific clinical study it cites) — the real per-study dose database this
  would need does not currently exist. Its claim check reuses Gate 0's
  use-case lookup.
- Evidence provenance: the 101 evidence entries have no row-level
  citations, and some underlying studies are contested. Treat the tables as
  a strong draft that needs source checking. Some rows contain data quirks
  (for example, Turmeric's upper dose limit is below its minimum effective
  dose, so no dose can pass Gate 0).
- The manually-labelled ground truth was produced through independent
  double-labelling (researcher + research-team collaborator, reconciled to
  consensus), but the pre-reconciliation label sets were not retained
  separately, so a formal inter-rater kappa for the ground truth's own
  construction cannot be computed.
- No unseen-data test yet: fixes were iterated against the same labels,
  which risks tuning to them.
- Live-data limits: FSA Food Alerts cover food-safety recalls, not
  advertising rulings, and work per brand. The Novel Food check misses
  species-specific cases (25 of Gate 1's 27 errors sit in five categories
  such as Cordyceps and krill oil). The Companies House check takes the
  first active result without comparing names, so an unrelated company can
  count as verified.

Several real implementation bugs were found and fixed during this project's
validation work (a Python NaN-as-truthy defect that silently inflated two
reported accuracy figures; a non-existent API search parameter; a
JSON-nesting error; and a Gate 4 claim check that compared the claim with
the ingredient's name and so could never pass) — all are documented with
before/after figures in the accompanying dissertation, Chapter 5.

## Data sources

- FSA Novel Food register (Gate 1) — live,
  `data.food.gov.uk/regulated-products/id/regime/novel-foods.json`, no key
- FSA Food Alerts (Gate 3) — live, `data.food.gov.uk/food-alerts/id`, no
  key
- UK Companies House (Gate 3) — live,
  `api.company-information.service.gov.uk/search/companies`, free key, HTTP
  Basic
- DDInter (Gate 4) — local file `src/data/ddsi_cache.csv`, no key
- NIH DSLD API v9 and USDA FoodData Central — market-data collection only
  (`dsld_api_pull.py`, `usda_filter_supplements.py`), not needed to run the
  pipeline

FSA data is released under Open Government Licence v3; acknowledge the
source if you publish results.

## Project structure

```
codenutrition-pipeline/
├── run_demo.py                  # entry point — 21 worked examples, writes output/CN_Automated_Output.xlsx
├── requirements.txt
├── .env.example                 # key template (the code reads environment variables; it does not load .env)
├── src/
│   ├── schemas.py                # data models
│   ├── pipeline.py                # orchestrator: Gate 0 -> 1 -> 2 -> 3 -> 4
│   ├── report_writer.py           # writes output/*.xlsx
│   ├── gates/
│   │   ├── gate0_formulation.py    # Form, Dose, Transparency, Formulation Logic, Use Case
│   │   ├── gate1_regulatory.py     # Novel Food (live), GMP + GMP-specificity, batch, label claims
│   │   ├── gate2_quality.py        # lab-certificate rules; no real data behind it
│   │   ├── gate3_brand.py          # Disclosure (live Companies House), Alerts (live FSA)
│   │   └── gate4_medical.py        # Dose match (proxy), drug interactions, tier assignment
│   ├── datasets/
│   │   ├── fsa_client.py           # live FSA Novel Food + Food Alerts
│   │   ├── companies_house_client.py  # live UK Companies House
│   │   └── ddinter_client.py       # reads the local interaction cache
│   └── data/                      # the five rule tables (see above)
├── tests/
│   ├── test_gate0.py
│   ├── test_gate4.py
│   └── test_demo_cases.py
├── webapp/                      # Flask website: server.py, templates/, static/
├── validate_*.py                # compare each gate with the ground truth, print kappa
├── convert_science_research.py, parse_ingredients_key*.py, extract_*.py
│                                # build the tables from the research evidence file
├── llm_extract_*.py, llm_form_extractor.py, run_llm_extraction.py
│                                # AI extraction (paid; needs ANTHROPIC_API_KEY)
├── dsld_*.py, usda_filter_supplements.py, build_magnesium_dose_comparison.py
│                                # market-data collection (not needed to run the pipeline)
└── .vscode/
```

An older Streamlit interface (`app.py`, `pages/`, `theme.py`,
`home_view.py`) is retired and can be deleted.

## Setup

Python 3.10 or newer is needed (the author used 3.14 on Windows), plus Git.

1. Clone this repository and open it in VS Code.
2. Create a virtual environment and install the packages:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install flask           # only for the website
   pip install anthropic       # only for the LLM extraction scripts
   ```
   Never move or copy a `.venv` folder; recreate it instead.
3. Set your keys as **environment variables**, in the terminal you will run
   from. The code does not read a `.env` file:
   ```bash
   export COMPANIES_HOUSE_API_KEY=your-key   # Windows PowerShell: $env:COMPANIES_HOUSE_API_KEY="your-key"
   ```
   - `COMPANIES_HOUSE_API_KEY` — free key from
     [developer.company-information.service.gov.uk](https://developer.company-information.service.gov.uk/);
     needed for the demo, the website and Gate 3
   - `ANTHROPIC_API_KEY` — only needed to re-run the LLM extraction scripts
     that built the evidence files (paid calls); not required to run the
     demo itself
   - FSA, NIH and DDInter data sources are open/keyless — no entry needed
4. Run the tests (offline); expect `16 passed`:
   ```bash
   python -m pytest tests -q
   ```
5. Run the demo (needs internet):
   ```bash
   python run_demo.py
   ```
   This runs all 21 worked product cases end to end and writes
   `output/CN_Automated_Output.xlsx`, with a Demo Guide sheet that lists
   each case's expected and actual result. Expect 21 lines starting `ok`
   and then "Every case behaved as expected"; a line starting `!!` means a
   live call failed. Each case is a clean product with one thing changed,
   so every stop has one clear reason (for example an underdosed magnesium
   product, or a curcumin product missing its bioavailability co-factor) —
   this is the pipeline correctly catching formulation issues, not a bug.
   Close the workbook in Excel before re-running.
6. Run the website:
   ```bash
   cd webapp
   python server.py
   ```
   Then open `http://127.0.0.1:5000`. Its brand and product dropdowns read
   `CN_Final_Corrected.xlsx` from the project root (sheet "Gate 0 —
   Formulation", headers on row 3); without that file those lists are
   empty.

## Data ownership

The evidence file (`science_research.xlsx`) and the ground-truth workbook
(`CN_Final_Corrected.xlsx`) belong to the research team, and the tables in
`src/data/` derive from the evidence file. Confirm who may receive, reuse
and publish them before sharing this repository. Never commit API keys.

## Further detail

Full methodology, the complete accuracy validation (with confusion matrices
and iteration histories for every gate), the literature this design is
grounded in, and a critical discussion of where automation is and is not
appropriate in this domain, are in the accompanying dissertation.
