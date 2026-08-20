"""Accuracy & Validation — the full, honest breakdown per gate."""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import inject_theme, logo_header, eyebrow, GOLD, DARK, PASS_TEXT, FAIL_TEXT

inject_theme()
logo_header()
eyebrow("The evidence")
st.title("Accuracy & Validation")
st.caption("Every number here comes from comparing the automated pipeline against manually-reviewed real products.")

st.subheader("Sample sizes behind each result")
sample_sizes = pd.DataFrame({
    "Gate / check": ["Gate 0 (Form+Dose)", "Gate 1 (Novel Food)", "Gate 3 (Regulatory History)",
                       "Gate 3 (Full Disclosure)", "Gate 4 (Form+Dose)"],
    "Products compared": [806, 766, 280, 281, 165],
})
st.dataframe(sample_sizes, use_container_width=True, hide_index=True)
st.caption("Total: ~3,100 usable ground-truth rows across all gates, ~2,300 individual comparisons once every sub-check is counted.")

st.divider()
st.subheader("Gate 1 — the full improvement story")
st.markdown("This gate went through five real iterations before reaching its final result. Nothing here is a first-try number.")

gate1_progress = pd.DataFrame({
    "Iteration": ["1. Wrong API endpoint", "2. Fixed endpoint, wrong JSON parsing", "3. Category-level matching",
                   "4. Product-level (reversed) matching", "5. Hybrid — final"],
    "Kappa": [None, None, 0.001, -0.017, 0.412],
})
fig1 = px.line(gate1_progress.dropna(subset=["Kappa"]), x="Iteration", y="Kappa", markers=True,
               title="Gate 1: Cohen's kappa across iterations (first two failed outright — 0 successful API calls)",
               color_discrete_sequence=[GOLD])
fig1.update_traces(line=dict(width=3), marker=dict(size=10))
fig1.update_layout(height=400, plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Inter"))
st.plotly_chart(fig1, use_container_width=True)
st.dataframe(gate1_progress, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Gate 4 — before and after fixing extraction")
gate4_progress = pd.DataFrame({
    "Version": ["Majority-class baseline\n(always guess PASS)", "Before extraction fix", "After extraction fix"],
    "Agreement (%)": [88.4, 76.8, 67.5],
    "Kappa": [0.000, 0.069, 0.108],
})
fig4 = px.bar(gate4_progress, x="Version", y="Kappa", title="Gate 4: kappa improved even though raw agreement dropped",
              color_discrete_sequence=[DARK])
fig4.update_layout(height=380, plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Inter"))
st.plotly_chart(fig4, use_container_width=True)
st.warning(
    "Notice the majority-class baseline (88.4%) beats the raw agreement of both real versions. This is exactly "
    "why kappa is reported everywhere in this project — a high percentage next to a low kappa means the check "
    "isn't actually adding much insight over just guessing the common answer."
)

st.divider()
st.subheader("What each gate's remaining errors are actually caused by")
limitations = pd.DataFrame({
    "Gate": ["Gate 0", "Gate 1", "Gate 3 (Reg. History)", "Gate 3 (Disclosure)", "Gate 4"],
    "Main cause of remaining disagreement": [
        "Comparing 1-2 parameters against a 5-parameter manual decision",
        "Species/strain-specific cases not stated in a product's name (Cordyceps, Krill Oil, etc.)",
        "Checks brand-level, not product-level; doesn't cover advertising-claim rulings",
        "Only checks company existence, not the full compound 'Full Disclosure' criterion",
        "Tests a safety-threshold proxy, not the framework's actual cited-study-match requirement",
    ],
})
st.dataframe(limitations, use_container_width=True, hide_index=True)
