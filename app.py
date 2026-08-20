"""
Navigation controller. Uses Streamlit's native top-position navigation
(st.navigation(..., position="top")) so pages are reached via a horizontal
header bar, matching the reference site's structure, rather than the
default left sidebar page list.
"""

import streamlit as st

st.set_page_config(page_title="Code Nutrition — Automated Verification", page_icon="⚗️", layout="wide")

home = st.Page("home_view.py", title="Home", default=True)
try_product = st.Page("pages/1_Try_a_Product.py", title="Try a Product")
accuracy = st.Page("pages/2_Accuracy_and_Validation.py", title="Accuracy & Validation")
methodology = st.Page("pages/3_Methodology.py", title="Methodology")

pg = st.navigation([home, try_product, accuracy, methodology], position="top")
pg.run()
