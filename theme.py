"""
Design system v2 - matched against real reference screenshots (not guessed).

Palette: warm cream paper paired with a near-black navy for dark sections and
a bold lime-green + mustard-gold accent pair. High-contrast display serif
(Fraunces) for headlines, clean sans (Inter) for body, tracked-caps labels
for "eyebrow" section markers.

Structural patterns borrowed from the reference: a dark stat bar with huge
serif numerals, numbered gate cards (01/04 style) with a lime top border,
and colored status pills (Full Pass / Conditional / Rejected / Direct Fail).
"""

import streamlit as st

PAPER = "#F3EFE0"
PAPER_ALT = "#EBE6D4"
CARD = "#FDFCF7"
DARK = "#171D24"
DARK_ALT = "#1E2831"
INK = "#1B2130"
GOLD = "#BF9A2E"
LIME = "#C9E23A"

PASS_BG, PASS_TEXT = "#DCEEDD", "#2F6D3B"
CONDITIONAL_BG, CONDITIONAL_TEXT = "#F7E8C9", "#8A6511"
REJECTED_BG, REJECTED_TEXT = "#E7E5DD", "#55524A"
FAIL_BG, FAIL_TEXT = "#F5DBD7", "#9C3B2E"

CHART_SEQUENCE = [DARK, GOLD, PASS_TEXT, FAIL_TEXT, "#7A6C5D"]


def inject_theme():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;0,700;1,500;1,600&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        color: {INK};
    }}

    .stApp {{
        background-color: {PAPER};
    }}

    h1, h2, h3 {{
        font-family: 'Fraunces', serif !important;
        color: {INK} !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
    }}

    h1 {{ font-size: 2.6rem !important; }}

    [data-testid="stMetricValue"] {{
        font-family: 'Fraunces', serif !important;
        font-weight: 700 !important;
        color: {INK} !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-family: 'Inter', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.72rem !important;
        color: #6B6858 !important;
    }}
    [data-testid="stMetric"] {{
        background-color: {CARD};
        border: 1px solid #DDD8C6;
        border-radius: 6px;
        padding: 1rem;
    }}

    button[kind="primary"] {{
        background-color: {DARK} !important;
        border-color: {DARK} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 3px !important;
    }}
    button[kind="primary"]:hover {{
        background-color: {DARK_ALT} !important;
        border-color: {DARK_ALT} !important;
    }}

    [data-testid="stExpander"] {{
        border: 1px solid #DDD8C6 !important;
        border-radius: 6px !important;
        background-color: {CARD} !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: {DARK};
    }}
    [data-testid="stSidebar"] * {{
        color: {PAPER} !important;
    }}

    #MainMenu, footer {{visibility: hidden;}}
    hr {{ border-color: #DDD8C6 !important; }}
    </style>
    """, unsafe_allow_html=True)


def eyebrow(text: str):
    """The '— LABEL' tracked-caps pattern used above every major heading in the reference."""
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:0.4rem;">
        <div style="width:24px; height:2px; background:{GOLD};"></div>
        <span style="font-family:'Inter',sans-serif; font-size:0.75rem; font-weight:600;
                     letter-spacing:0.12em; color:{GOLD}; text-transform:uppercase;">{text}</span>
    </div>
    """, unsafe_allow_html=True)


def stat_bar(stats: list):
    """Dark navy bar with big serif numerals - the reference's stats-under-hero pattern."""
    cells = "".join(f"""
        <div style="flex:1; text-align:left;">
            <div style="font-family:'Fraunces',serif; font-size:2.8rem; font-weight:700; color:{PAPER}; line-height:1;">{value}</div>
            <div style="font-family:'Inter',sans-serif; font-size:0.7rem; letter-spacing:0.1em;
                        text-transform:uppercase; color:#9AA3A8; margin-top:6px;">{label}</div>
        </div>
    """ for value, label in stats)
    st.markdown(f"""
    <div style="background:{DARK}; padding:2rem 1.5rem; border-radius:8px; display:flex; gap:2rem; margin:1rem 0 2rem 0;">
        {cells}
    </div>
    """, unsafe_allow_html=True)


def status_pill(status: str) -> str:
    """Returns HTML for a colored pill badge, matching the reference's Full Pass /
    Conditional / Rejected / Direct Fail pattern, mapped onto our own PASS/FAIL states."""
    mapping = {
        "PASS": (PASS_BG, PASS_TEXT, "PASS"),
        "FAIL": (FAIL_BG, FAIL_TEXT, "FAIL"),
        "CONDITIONAL": (CONDITIONAL_BG, CONDITIONAL_TEXT, "CONDITIONAL"),
        "NOT_FOUND": (REJECTED_BG, REJECTED_TEXT, "NOT FOUND"),
    }
    bg, text, label = mapping.get(status, (REJECTED_BG, REJECTED_TEXT, status))
    return (f'<span style="background:{bg}; color:{text}; padding:3px 12px; border-radius:20px; '
            f'font-family:Inter,sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:0.05em;">{label}</span>')


def gate_card_html(number: str, name: str, question: str, detail: str) -> str:
    """The numbered gate card pattern (01/04 huge serif numeral + lime top border)."""
    return f"""
    <div style="background:{CARD}; border-radius:10px; padding:1.6rem 1.5rem; position:relative;
                border-top:4px solid {LIME}; height:100%;">
        <div style="font-family:'Fraunces',serif; font-size:2.6rem; font-weight:700; color:{INK}; line-height:1;">
            {number}<span style="font-size:1.1rem; color:#9AA3A8; font-family:Inter,sans-serif;">/04</span>
        </div>
        <div style="font-family:Inter,sans-serif; font-size:0.7rem; letter-spacing:0.1em; color:#9AA3A8;
                    text-transform:uppercase; margin:0.6rem 0 0.3rem 0;">GATE {number}</div>
        <div style="font-family:'Fraunces',serif; font-size:1.4rem; font-weight:700; color:{INK}; margin-bottom:0.4rem;">{name}</div>
        <div style="font-family:'Fraunces',serif; font-style:italic; font-size:1rem; color:{INK}; margin-bottom:0.6rem;">{question}</div>
        <div style="font-family:Inter,sans-serif; font-size:0.9rem; color:#4A4740; line-height:1.5;">{detail}</div>
    </div>
    """


def gate_pipeline_diagram(gate_statuses: dict) -> str:
    """Sequential checkpoint diagram - structurally true to the content (binary
    gates evaluated in fixed order, stopping at first FAIL), not decoration."""
    symbol = {"pass": "check", "fail": "x", "pending": "...", "unvalidated": "?"}
    display_symbol = {"pass": "\u2713", "fail": "\u2715", "pending": "\u2026", "unvalidated": "?"}
    color = {"pass": PASS_TEXT, "fail": FAIL_TEXT, "pending": "#B8B4A4", "unvalidated": GOLD}

    segments = []
    for i in range(5):
        status = gate_statuses.get(i, "pending")
        segments.append(f"""
        <div style="display:flex; flex-direction:column; align-items:center; flex:1;">
            <div style="width:48px; height:48px; border-radius:50%; background:{color[status]};
                        color:white; display:flex; align-items:center; justify-content:center;
                        font-family:'Fraunces', serif; font-weight:700; font-size:20px;">
                {display_symbol[status]}
            </div>
            <div style="font-family:'Inter', sans-serif; font-size:11px; letter-spacing:0.08em;
                        margin-top:8px; color:{INK}; text-transform:uppercase;">GATE {i}</div>
        </div>
        """)
        if i < 4:
            segments.append('<div style="flex:0.3; height:2px; background:#DDD8C6; align-self:center; margin-bottom:24px;"></div>')

    return f'<div style="display:flex; align-items:flex-start; padding:1rem 0;">{"".join(segments)}</div>'


def logo_header():
    """
    Consistent branding row (icon + wordmark + tagline) at the top of every
    page - Streamlit's native top navigation (position="top") renders its
    own bar automatically and can't have custom content injected above it
    from the entry-point script, so this sits just below that nav bar,
    approximating the reference's two-tier header within that constraint.
    """
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; padding:1rem 0 0.5rem 0;">
        <div style="width:40px; height:40px; border-radius:8px; background:{DARK};
                    display:flex; align-items:center; justify-content:center;
                    font-size:20px;">⚗️</div>
        <div>
            <div style="font-family:'Fraunces', serif; font-weight:700; font-size:1.3rem; color:{INK}; line-height:1.1;">Code Nutrition</div>
            <div style="font-family:'IBM Plex Mono', monospace; font-size:0.65rem; letter-spacing:0.1em;
                        color:#6B6858; text-transform:uppercase;">Automated Verification Pipeline</div>
        </div>
    </div>
    <hr style="margin-top:0.5rem;">
    """, unsafe_allow_html=True)


def pull_quote(text: str) -> str:
    """
    Italic serif callout with a gold left border - matches the reference's
    single-memorable-insight treatment (e.g. "The gates are sequential
    because a product that misstates its claim portfolio is not made safer
    by passing a potency test."). Reserved for the one insight worth a
    reader pausing on, not general body copy - matching the reference's own
    restraint in using it sparingly.
    """
    return f"""
    <div style="border-left:3px solid {GOLD}; padding:0.4rem 0 0.4rem 1.5rem; margin:1.5rem 0;">
        <div style="font-family:'Fraunces', serif; font-style:italic; font-size:1.3rem;
                    color:{INK}; line-height:1.5;">
            {text}
        </div>
    </div>
    """


def numbered_steps(steps: list) -> str:
    """
    Numbered process cards (01, 02, 03...) in amber, hairline-bordered cream
    cards - matches the reference's "how a brand earns the mark" pathway
    treatment. steps: list of (title, description) tuples.
    """
    cards = "".join(f"""
    <div style="background:{CARD}; border:1px solid #DDD8C6; border-radius:8px;
                padding:1.2rem 1.4rem; margin-bottom:0.8rem;">
        <div style="font-family:'IBM Plex Mono', monospace; font-size:0.85rem; color:{GOLD};
                    font-weight:600; margin-bottom:0.2rem;">{i+1:02d}</div>
        <div style="font-family:'Fraunces', serif; font-weight:700; font-size:1.1rem;
                    color:{INK}; margin-bottom:0.3rem;">{title}</div>
        <div style="font-family:'Inter', sans-serif; font-size:0.92rem; color:#4A4740; line-height:1.5;">
            {description}
        </div>
    </div>
    """ for i, (title, description) in enumerate(steps))
    return cards
