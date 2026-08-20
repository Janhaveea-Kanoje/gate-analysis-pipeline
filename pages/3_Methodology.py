"""Methodology — the architecture, in plain terms."""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import inject_theme, logo_header, eyebrow, status_pill, numbered_steps, GOLD, DARK

inject_theme()
logo_header()
eyebrow("Methodology")
st.title("How this actually works")

st.subheader("The core design rule: AI reads, rules decide")
st.markdown("""
Every gate in this pipeline follows one strict rule: a large language model is only ever
allowed to **read messy text and turn it into structured data** (e.g. "what form and dose
does this label describe?"). It is **never** allowed to make the actual pass/fail decision.
That decision always comes from plain, fixed, deterministic code.

This matters because language models are known to occasionally get precise numbers wrong —
a real risk for a health-adjacent decision. Keeping AI restricted to reading, and rules
restricted to deciding, means every decision this tool makes can be traced back to an
explicit, checkable threshold, not a model's best guess.
""")

st.divider()
st.subheader("Where each gate gets its evidence")
sources = {
    "Gate 0 — Formulation": "A 101-ingredient evidence file (forms, safe dose ranges) built from the research team's data",
    "Gate 1 — Regulatory": "The live UK Food Standards Agency Novel Food register — a real government database, checked in real time",
    "Gate 2 — Quality": "No open dataset exists for this yet — the biggest remaining gap, being worked on with a research contact",
    "Gate 3 — Brand Integrity": "Live UK Companies House (company verification) + live FSA Food Alerts (recall history)",
    "Gate 4 — Medical": "The same evidence file as Gate 0, used as a stand-in for a full clinical-study-dose database that doesn't exist yet",
}
for gate, source in sources.items():
    st.markdown(f"**{gate}**")
    st.write(source)
    st.write("")

st.divider()
st.subheader("The headline finding")
st.info(
    "Across every gate tested, the **plain database lookup** (Gate 1) outperformed every "
    "**AI-assisted text-reading** approach (Gates 0 and 4) — even after multiple rounds of "
    "fixing the reading step. Where a question can be answered by checking a real database "
    "directly, this project's evidence says that beats asking an AI model to read and decide, "
    "every time it was tested."
)

st.divider()
eyebrow("Section 01 · Outcomes")
st.subheader("Verdict states")
st.markdown("A product clearing all five gates receives one of three tiers — never a numeric score, and never partial credit for a gate it didn't clear.")

vc1, vc2, vc3, vc4 = st.columns(4)
with vc1:
    st.markdown(status_pill("PASS"), unsafe_allow_html=True)
    st.markdown("**Tier 1**")
    st.caption("All 5 gates pass, using Superior-tier forms at the upper end of the evidence-based dose range, with premium (ISO 17025) testing. Requires expert panel consensus before publication — this pipeline flags it, it does not auto-publish it.")
with vc2:
    st.markdown(status_pill("PASS"), unsafe_allow_html=True)
    st.markdown("**Tier 2**")
    st.caption("All 5 gates pass, using acceptable (not necessarily Superior) forms or doses outside the upper range.")
with vc3:
    st.markdown(status_pill("CONDITIONAL"), unsafe_allow_html=True)
    st.markdown("**Tier 3**")
    st.caption("All 5 gates pass, but neither the Superior-form nor upper-dose-range condition is met — a baseline, adequate product.")
with vc4:
    st.markdown(status_pill("FAIL"), unsafe_allow_html=True)
    st.markdown("**Tier 0**")
    st.caption("Failed at least one gate. Evaluation stops at the first failing gate — a product is never assessed against later gates once it has failed an earlier one.")

st.divider()
eyebrow("Section 02 · The corpus")
st.subheader("How the ground truth was built")
st.markdown(
    numbered_steps([
        ("Manual review", "A single researcher applied the same five-gate criteria this pipeline now applies automatically, to roughly 1,850 real UK products — before any of this automation existed."),
        ("Evidence base", "Forms and safe-dose ranges for 101 ingredients were compiled from the research team's clinical evidence sources."),
        ("Extraction", "A large language model reads each product's free-text label and turns it into structured form and dose data — it never decides pass or fail."),
        ("Rule engine", "Fixed, deterministic thresholds compare the extracted data against the evidence base to reach a verdict."),
        ("Comparison", "The automated verdict is checked against the original manual review, using Cohen's kappa to correct for chance agreement rather than raw percentage alone."),
    ]),
    unsafe_allow_html=True,
)
st.markdown("""
This matters for how the accuracy numbers on the previous page should be read: they measure
agreement with **one reviewer's judgement**, not against an independent panel. The framework's
own design already requires panel consensus for its highest-confidence tier (Tier 1, above) —
this dissertation is transparent that its ground truth does not yet meet that same bar, and
names independent expert-panel labelling as a specific direction for future work rather than
treating the current ground truth as beyond question.
""")

st.divider()
eyebrow("Section 03 · Honesty")
st.subheader("What this pipeline doesn't claim")
st.markdown("""
This automated pipeline is a research prototype, evaluated against real data, not a certified
consumer product. Stated plainly:
""")
st.markdown("""
- **It is not a medical endorsement, and not a guarantee of individual safety** for any person or product.
- **Gate 2 has no empirical result.** No open dataset of batch-specific laboratory certificates
  exists anywhere — this is stated as a data gap, not glossed over as "in progress."
- **Gate 4 uses a safety-threshold proxy**, not an implementation of its actual defined
  requirement (matching a product's dose against the specific clinical study it cites) — that
  real per-study dose database does not exist yet.
- **Outcomes depend on the evidence available at assessment time.** New evidence, or a
  corrected evidence-file entry (this project already found and fixed one real contradiction
  in its own source data), can change a prior result.
- **Every live API this pipeline depends on** (FSA Novel Food, FSA Food Alerts, UK Companies
  House) is a third-party government service outside this project's control — several real
  integration errors were caught and corrected during this work, illustrating that such
  dependencies need ongoing verification, not a one-time integration effort.
""")
