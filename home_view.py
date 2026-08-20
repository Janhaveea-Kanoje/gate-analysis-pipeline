import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from theme import inject_theme, logo_header, eyebrow, stat_bar, gate_card_html, gate_pipeline_diagram, pull_quote, DARK, GOLD, INK, CHART_SEQUENCE

inject_theme()
logo_header()

eyebrow("Independent automated assessment")
st.markdown(f"""
<h1 style="font-size:3rem; line-height:1.1; margin-bottom:0.6rem;">
The automated gate<br>for supplement verification.
</h1>
""", unsafe_allow_html=True)
st.markdown("""
<p style="font-family:Inter,sans-serif; font-size:1.05rem; color:#4A4740; max-width:640px;">
Five sequential clinical gates. ~3,100 UK/US products assessed. An automated implementation of
the Code Nutrition verification framework, checked against real, manually-reviewed ground truth.
</p>
""", unsafe_allow_html=True)

stat_bar([
    ("5/5", "Gates built"),
    ("4/5", "Empirically validated"),
    ("~3,100", "Products in ground truth"),
    ("96.5%", "Best gate agreement"),
])

eyebrow("The framework")
st.markdown('<h2 style="font-size:1.9rem;">Sequential. Evidence-based. On the record.</h2>', unsafe_allow_html=True)
st.markdown("""
<p style="font-family:Inter,sans-serif; color:#4A4740; max-width:700px; margin-bottom:1.5rem;">
A product that fails Gate 0 is not assessed against Gate 1. There is no overall score and no
partial credit — every gate is a binary pass/fail, and one failure ends evaluation.
</p>
""", unsafe_allow_html=True)

st.markdown("##### Live status")
st.markdown(
    gate_pipeline_diagram({0: "pass", 1: "pass", 2: "unvalidated", 3: "pass", 4: "pass"}),
    unsafe_allow_html=True,
)
st.caption("Gate 2 (?) has no empirical result yet — no public dataset of batch-specific lab certificates exists.")

st.markdown("<br>", unsafe_allow_html=True)

gates = [
    ("0", "Formulation", "Is this product's form and dose backed by real evidence?",
     "Ingredient form, bioavailability tier, and effective-dose check against a 101-ingredient evidence base."),
    ("1", "Regulatory", "Is this product lawful to sell in the UK today?",
     "Live UK FSA Novel Food register check. The single strongest result in this project — kappa 0.412."),
    ("2", "Quality", "Does the batch in market match the label on the bottle?",
     "Requires a batch certificate of analysis from an ISO 17025 lab. No public dataset of this exists yet."),
    ("3", "Brand Integrity", "Is the company behind this product real and clean?",
     "Live UK Companies House verification + live FSA Food Alerts recall history."),
]
cols = st.columns(4)
for col, (num, name, question, detail) in zip(cols, gates):
    with col:
        st.markdown(gate_card_html(num, name, question, detail), unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

st.markdown(
    pull_quote("A plain database lookup outperformed every AI-assisted reading approach we tested — "
               "even after several rounds of fixing the reading step. Where a question can be answered "
               "by checking a real database directly, that beat asking a model to read and decide, every time."),
    unsafe_allow_html=True,
)

eyebrow("Real findings")
st.markdown('<h2 style="font-size:1.9rem;">What the corpus actually shows.</h2>', unsafe_allow_html=True)

fcol1, fcol2 = st.columns(2)
with fcol1:
    st.markdown(f"""
    <div style="background:{DARK}; border-radius:8px; padding:1.5rem; margin-bottom:1rem;">
        <div style="font-family:'Fraunces',serif; font-size:2.2rem; font-weight:700; color:{GOLD};">Lookup &gt; LLM</div>
        <div style="font-family:Inter,sans-serif; color:#DDD8C6; font-size:0.9rem; margin-top:0.4rem;">
        The gate needing no AI reading step at all (Gate 1, live database lookup) scored highest.
        Every AI-assisted extraction gate scored lower, even after multiple rounds of fixes.
        </div>
    </div>
    """, unsafe_allow_html=True)
with fcol2:
    st.markdown(f"""
    <div style="background:{DARK}; border-radius:8px; padding:1.5rem; margin-bottom:1rem;">
        <div style="font-family:'Fraunces',serif; font-size:2.2rem; font-weight:700; color:{GOLD};">Cheap forms, pushed harder</div>
        <div style="font-family:Inter,sans-serif; color:#DDD8C6; font-size:0.9rem; margin-top:0.4rem;">
        Magnesium oxide (the rejected form) was dosed highest and blended most across the market.
        Premium forms were dosed conservatively and sold with less adulteration.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.subheader("How each gate performed against real, manually-reviewed data")

results = pd.DataFrame({
    "Gate": ["Gate 0\nFormulation", "Gate 1\nRegulatory", "Gate 3\nRegulatory Hist.", "Gate 3\nDisclosure", "Gate 4\nMedical"],
    "Agreement (%)": [67.5, 96.5, 91.4, 93.2, 67.5],
    "Cohen's kappa": [0.297, 0.412, -0.033, -0.013, 0.108],
})

fig = go.Figure()
fig.add_trace(go.Bar(x=results["Gate"], y=results["Agreement (%)"], name="Agreement %", marker_color=DARK))
fig.add_trace(go.Scatter(x=results["Gate"], y=results["Cohen's kappa"] * 100, name="Kappa (×100 for scale)",
                          mode="lines+markers", marker_color=GOLD, line=dict(width=3), yaxis="y2"))
fig.update_layout(
    yaxis=dict(title="Agreement (%)", range=[0, 100]),
    yaxis2=dict(title="Cohen's kappa", overlaying="y", side="right", range=[-0.5, 5]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=420,
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="Inter"),
)
st.plotly_chart(fig, use_container_width=True)

st.info(
    "**Why show both numbers?** Agreement alone can be misleading when most products naturally "
    "pass. Cohen's kappa corrects for that, so a low kappa next to a high agreement percentage "
    "(see Gate 3) is flagged honestly here rather than hidden behind a good-looking headline number."
)

st.divider()
st.caption("Use the sidebar to try a real product through the pipeline, or explore the full accuracy breakdown.")
