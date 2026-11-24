import csv
import inspect
import io
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="EcoSync | Carbon Footprint & Action Engine",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- VERSION-SAFE HELPERS ---
# Newer Streamlit versions replace `use_container_width=True` with `width="stretch"`.
# This picks whichever one your installed version supports, so the app never breaks.
def _full_width(fn):
    try:
        if "width" in inspect.signature(fn).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


BTN = _full_width(st.button)
SUBMIT = _full_width(st.form_submit_button)
DL = _full_width(st.download_button)

# st.dialog (new) or st.experimental_dialog (older versions)
_dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog")


def html(markup):
    """Render HTML safely: collapses whitespace/newlines so Markdown never treats it as a code block."""
    flat = " ".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(flat, unsafe_allow_html=True)


# ==============================================================================
# ECOSYNC MODERN THEME  (glass cards • bento layout • lime accent)
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

:root {
    --bg: #060a08;
    --line: rgba(190,225,200,.12);
    --line-strong: rgba(190,225,200,.22);
    --text: #eef6f0;
    --text-2: #c3d6c9;
    --muted: #8aa092;
    --accent: #b9f56a;
    --accent-2: #5fe3a1;
    --radius: 20px;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ---------- App background ---------- */
.stApp {
    background:
        radial-gradient(900px 500px at 85% -5%, rgba(95,227,161,.13), transparent 60%),
        radial-gradient(700px 500px at -5% 25%, rgba(185,245,106,.08), transparent 60%),
        radial-gradient(600px 400px at 60% 110%, rgba(60,140,110,.10), transparent 60%),
        var(--bg);
    color: var(--text);
}
.stApp:before {
    content: "";
    position: fixed; inset: 0; pointer-events: none; opacity: .5;
    background-image: linear-gradient(rgba(255,255,255,.022) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255,255,255,.022) 1px, transparent 1px);
    background-size: 44px 44px;
    mask-image: radial-gradient(ellipse at 50% 0%, black 0%, transparent 70%);
    -webkit-mask-image: radial-gradient(ellipse at 50% 0%, black 0%, transparent 70%);
}
header[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }
div[data-testid="stDecoration"] { display: none; }

.block-container, div[data-testid="stMainBlockContainer"] {
    max-width: 1280px;
    padding: 2rem 2.5rem 4rem !important;
}

/* ---------- Typography ---------- */
h1, h2, h3, h4 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: #f4faf5 !important;
    letter-spacing: -.03em;
}
h3 { font-weight: 800 !important; font-size: 1.55rem !important; }
h4 { font-weight: 700 !important; font-size: 1.1rem !important; margin-top: 1.4rem !important; }
p, li, label, .stMarkdown { color: var(--text-2); }
small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted) !important; }
hr { border-color: var(--line) !important; margin: 1.4rem 0 !important; }
a { color: var(--accent-2) !important; text-decoration: none; }
a:hover { text-decoration: underline; }
::selection { background: rgba(185,245,106,.3); }
div[data-testid="stWidgetLabel"] p {
    color: var(--text-2) !important; font-size: .86rem; font-weight: 600;
}

/* ---------- Hero ---------- */
.hero {
    position: relative; overflow: hidden;
    border-radius: 28px;
    padding: 2.3rem 2.6rem;
    margin-bottom: 1.4rem;
    background:
        radial-gradient(420px 260px at 100% 0%, rgba(185,245,106,.22), transparent 70%),
        radial-gradient(380px 260px at 70% 120%, rgba(95,227,161,.16), transparent 70%),
        linear-gradient(120deg, #13241b 0%, #0e1b14 60%, #0c1711 100%);
    border: 1px solid rgba(185,245,106,.22);
    box-shadow: 0 30px 80px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06);
}
.hero:before {
    content: ""; position: absolute; right: -60px; top: -60px;
    width: 280px; height: 280px; border-radius: 50%;
    border: 1px solid rgba(185,245,106,.18);
    box-shadow: 0 0 0 38px rgba(185,245,106,.035), 0 0 0 80px rgba(185,245,106,.02);
}
.hero-row { display: flex; align-items: center; gap: 1.2rem; position: relative; }
.hero-logo {
    width: 64px; height: 64px; border-radius: 20px; font-size: 2rem;
    display: grid; place-items: center; flex-shrink: 0;
    background: linear-gradient(135deg, rgba(185,245,106,.25), rgba(95,227,161,.12));
    border: 1px solid rgba(185,245,106,.35);
    box-shadow: 0 10px 30px rgba(185,245,106,.12);
}
.hero h1 {
    margin: 0 !important; line-height: 1.05;
    font-size: clamp(2rem, 4vw, 3rem) !important; font-weight: 800 !important;
    background: linear-gradient(90deg, #ffffff 30%, #b9f56a 130%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent !important;
}
.hero p.tag { margin: .35rem 0 0; color: #a9c1b0; font-size: 1.02rem; }
.chips { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: 1.4rem; position: relative; }
.chip {
    display: inline-flex; align-items: center; gap: .4rem;
    padding: .38rem .8rem; border-radius: 999px;
    font-size: .76rem; font-weight: 600; color: #cfe3d4;
    background: rgba(255,255,255,.05); border: 1px solid var(--line);
    backdrop-filter: blur(6px);
}
.chip b { color: var(--accent); font-weight: 700; }

/* ---------- Cards ---------- */
.card {
    background: linear-gradient(160deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 1.3rem 1.4rem;
    box-shadow: 0 14px 40px rgba(0,0,0,.18);
}
.eyebrow {
    font-size: .68rem; font-weight: 700; letter-spacing: .14em;
    color: var(--accent); text-transform: uppercase;
}

/* Section header (icon tile + title) */
.sec-head { display: flex; align-items: center; gap: .85rem; margin: .2rem 0 1rem; }
.sec-ico {
    width: 42px; height: 42px; border-radius: 13px; font-size: 1.25rem;
    display: grid; place-items: center; flex-shrink: 0;
    background: rgba(185,245,106,.1); border: 1px solid rgba(185,245,106,.25);
}
.sec-title { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; font-size: 1.08rem; color: #f4faf5; line-height: 1.2; }
.sec-sub { font-size: .8rem; color: var(--muted); margin-top: .1rem; }
.sec-step {
    margin-left: auto; font-size: .68rem; font-weight: 700; letter-spacing: .12em;
    color: var(--accent); padding: .3rem .65rem; border-radius: 999px;
    background: rgba(185,245,106,.08); border: 1px solid rgba(185,245,106,.22);
}

/* Bordered containers (input groups) */
div[data-testid="stForm"] {
    background: transparent; border: none !important; padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: var(--radius) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sec-head) {
    background: linear-gradient(160deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
    border: 1px solid var(--line) !important;
    padding: .5rem .6rem .4rem;
    box-shadow: 0 14px 40px rgba(0,0,0,.18);
}

/* ---------- KPI tiles ---------- */
.kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: .9rem; }
.kpi {
    background: linear-gradient(160deg, rgba(255,255,255,.055), rgba(255,255,255,.02));
    border: 1px solid var(--line); border-radius: 18px; padding: 1.05rem 1.1rem;
    transition: transform .2s ease, border-color .2s ease;
}
.kpi:hover { transform: translateY(-2px); border-color: var(--line-strong); }
.kpi-ico { font-size: 1.15rem; width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center;
           background: rgba(255,255,255,.06); margin-bottom: .7rem; }
.kpi-label { font-size: .74rem; font-weight: 600; color: var(--muted); letter-spacing: .02em; }
.kpi-value { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.7rem; font-weight: 800; color: #f4faf5; line-height: 1.15; margin-top: .15rem; }
.kpi-sub { font-size: .76rem; color: var(--muted); margin-top: .2rem; }
.kpi.good .kpi-value { color: var(--accent); }
.kpi.good { border-color: rgba(185,245,106,.3); background: linear-gradient(160deg, rgba(185,245,106,.1), rgba(255,255,255,.02)); }

/* ---------- Score ring ---------- */
.score-wrap { display: flex; align-items: center; gap: 1.6rem; flex-wrap: wrap; }
.ring {
    --p: 50; --c: #74c69d;
    width: 156px; height: 156px; border-radius: 50%; flex-shrink: 0;
    display: grid; place-items: center;
    background: conic-gradient(var(--c) calc(var(--p) * 1%), rgba(255,255,255,.08) 0);
    box-shadow: 0 0 40px -8px var(--c);
}
.ring-in {
    width: 122px; height: 122px; border-radius: 50%;
    background: #0b140f; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
}
.ring-in b { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 2.7rem; font-weight: 800; line-height: 1; color: #f4faf5; }
.ring-in span { font-size: .72rem; color: var(--muted); font-weight: 600; margin-top: .15rem; }
.score-txt { flex: 1; min-width: 200px; }
.score-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.45rem; font-weight: 800; margin: .3rem 0 .45rem; }
.scale { position: relative; height: 7px; border-radius: 99px; margin: 1rem 0 .4rem;
         background: linear-gradient(90deg, #e76f51, #f4a261, #e9c46a, #74c69d, #52b788); }
.scale i { position: absolute; top: 50%; width: 16px; height: 16px; border-radius: 50%;
           background: #fff; border: 3px solid #0b140f; transform: translate(-50%, -50%);
           box-shadow: 0 0 0 2px rgba(255,255,255,.35); }
.scale-lbl { display: flex; justify-content: space-between; font-size: .7rem; color: var(--muted); font-weight: 600; }

/* ---------- Status banner ---------- */
.banner {
    display: flex; align-items: center; gap: .9rem;
    padding: 1rem 1.2rem; border-radius: 16px; margin-bottom: 1.1rem;
    font-size: .95rem; color: var(--text);
}
.banner .b-ico { font-size: 1.5rem; }
.banner.good { background: linear-gradient(100deg, rgba(185,245,106,.16), rgba(185,245,106,.04)); border: 1px solid rgba(185,245,106,.35); }
.banner.warn { background: linear-gradient(100deg, rgba(244,162,97,.16), rgba(244,162,97,.04)); border: 1px solid rgba(244,162,97,.35); }

/* ---------- Emission bars ---------- */
.bar-row { display: grid; grid-template-columns: 150px 1fr 150px; align-items: center; gap: 1rem; padding: .55rem 0; }
.bar-label { display: flex; align-items: center; gap: .6rem; font-weight: 600; font-size: .9rem; color: var(--text); }
.bar-ico { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; font-size: .95rem; }
.bar-track { height: 12px; border-radius: 99px; background: rgba(255,255,255,.06); overflow: hidden; }
.bar-fill { height: 100%; border-radius: 99px; }
.bar-val { text-align: right; font-weight: 700; font-size: .92rem; color: #f4faf5; }
.bar-val small { color: var(--muted); font-weight: 500; font-size: .74rem; }

/* Comparison bars (simulator) */
.cmp-row { padding: .6rem 0; border-bottom: 1px dashed var(--line); }
.cmp-row:last-child { border-bottom: none; }
.cmp-name { display: flex; justify-content: space-between; font-size: .88rem; font-weight: 600; color: var(--text); margin-bottom: .4rem; }
.cmp-name span { color: var(--muted); font-weight: 500; font-size: .78rem; }
.cmp-bar { height: 8px; border-radius: 99px; background: rgba(255,255,255,.05); margin: .22rem 0; overflow: hidden; }
.cmp-bar > div { height: 100%; border-radius: 99px; }
.legend { display: flex; gap: 1.2rem; font-size: .78rem; color: var(--muted); margin-bottom: .4rem; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: .35rem; vertical-align: -1px; }

/* ---------- Tip cards ---------- */
.tip {
    display: flex; gap: 1.1rem; align-items: flex-start;
    padding: 1.15rem 1.3rem; margin-bottom: .85rem; border-radius: 18px;
    background: linear-gradient(160deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
    border: 1px solid var(--line); position: relative; overflow: hidden;
    transition: transform .2s ease, border-color .2s ease;
}
.tip:hover { transform: translateX(3px); border-color: var(--line-strong); }
.tip:before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--tc, var(--accent-2)); }
.tip-rank { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800; font-size: .72rem; letter-spacing: .1em; color: var(--tc); }
.tip-emoji { font-size: 1.6rem; width: 54px; height: 54px; border-radius: 16px; display: grid; place-items: center; flex-shrink: 0;
             background: rgba(255,255,255,.06); border: 1px solid var(--line-strong); }
.tip-title { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; font-size: 1.05rem; color: #f4faf5; margin: .1rem 0 .45rem; }
.tip-title span { color: var(--muted); font-weight: 500; font-size: .85rem; }
.tip ul { margin: 0; padding-left: 1.1rem; color: var(--text-2); font-size: .9rem; line-height: 1.7; }

/* Guide dialog rows */
.guide-row { display: flex; align-items: center; gap: .9rem; padding: .85rem 1rem; margin-bottom: .6rem; border-radius: 16px;
             background: rgba(255,255,255,.04); border: 1px solid var(--line); color: var(--text-2); font-size: .9rem; line-height: 1.55; }
.guide-icon { font-size: 1.5rem; width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center; flex-shrink: 0;
              background: rgba(185,245,106,.1); border: 1px solid rgba(185,245,106,.22); }
.guide-row b { color: #f4faf5; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b130e 0%, #080e0a 100%);
    border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] > div { padding-top: 1.2rem; }
.brand { display: flex; align-items: center; gap: .7rem; margin: .2rem 0 .3rem; }
.brand-logo { width: 40px; height: 40px; border-radius: 13px; display: grid; place-items: center; font-size: 1.3rem;
              background: linear-gradient(135deg, rgba(185,245,106,.28), rgba(95,227,161,.12)); border: 1px solid rgba(185,245,106,.35); }
.brand-name { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800; font-size: 1.25rem; color: #f4faf5; line-height: 1; }
.brand-sub { font-size: .7rem; color: var(--muted); margin-top: .2rem; }
.side-label { font-size: .66rem; font-weight: 700; letter-spacing: .14em; color: var(--muted); margin: 1.2rem 0 .5rem; }
.side-foot { font-size: .72rem; color: var(--muted); line-height: 1.5; padding: .8rem .9rem; border-radius: 14px;
             background: rgba(255,255,255,.03); border: 1px solid var(--line); margin-top: .6rem; }
section[data-testid="stSidebar"] div.stButton > button {
    justify-content: flex-start; text-align: left; min-height: 2.9rem;
}

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: 14px !important;
    border: 1px solid var(--line) !important;
    font-weight: 600 !important;
    min-height: 2.8rem;
    transition: all .2s ease !important;
}
.stButton > button[kind="secondary"], .stDownloadButton > button {
    background: rgba(255,255,255,.04) !important;
    color: #dceadd !important;
}
.stButton > button[kind="secondary"]:hover, .stDownloadButton > button:hover {
    background: rgba(255,255,255,.08) !important;
    border-color: rgba(185,245,106,.55) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"],
.stFormSubmitButton > button,
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
    background: linear-gradient(110deg, #c4f77c 0%, #8fe39a 100%) !important;
    border: 1px solid rgba(255,255,255,.25) !important;
    box-shadow: 0 8px 26px rgba(150,230,110,.22), inset 0 1px 0 rgba(255,255,255,.35);
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover,
button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 34px rgba(150,230,110,.34), inset 0 1px 0 rgba(255,255,255,.35);
}
.stButton > button:disabled { opacity: .4; }

/* Dark green text on neon-green (primary) buttons */
.stButton > button[kind="primary"],
.stButton > button[kind="primary"] *,
.stFormSubmitButton > button,
.stFormSubmitButton > button *,
.stDownloadButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] *,
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primary"] *,
button[data-testid="stBaseButton-primaryFormSubmit"],
button[data-testid="stBaseButton-primaryFormSubmit"] * {
    color: #0b2415 !important;
    font-weight: 700 !important;
}
/* Light text on secondary (dark) buttons */
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-secondary"] * {
    color: #dceadd !important;
}

/* ---------- Inputs ---------- */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] > div {
    background: rgba(255,255,255,.04) !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    color: #eff8ef !important;
    transition: border-color .2s ease, box-shadow .2s ease;
}
div[data-baseweb="input"]:focus-within > div, div[data-baseweb="select"]:focus-within > div {
    border-color: rgba(185,245,106,.65) !important;
    box-shadow: 0 0 0 3px rgba(185,245,106,.12);
}
input, textarea { color: #eff8ef !important; }
div[data-baseweb="popover"], div[data-baseweb="menu"] {
    background: #121e17 !important; border: 1px solid var(--line) !important; border-radius: 12px !important;
}
div[data-testid="stNumberInput"] button { background: transparent !important; }

/* Radio -> pill chips */
div[role="radiogroup"] { gap: .55rem !important; flex-wrap: wrap; }
div[role="radiogroup"] > label {
    background: rgba(255,255,255,.035); border: 1px solid var(--line);
    padding: .5rem .95rem; border-radius: 999px; margin: 0 !important;
    transition: all .2s ease; cursor: pointer;
}
div[role="radiogroup"] > label:hover { border-color: rgba(185,245,106,.45); background: rgba(255,255,255,.06); }
div[role="radiogroup"] > label:has(input:checked) {
    background: rgba(185,245,106,.13); border-color: rgba(185,245,106,.65);
}
div[role="radiogroup"] label, div[data-testid="stCheckbox"] label { color: var(--text-2) !important; }

/* Sliders */
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: var(--accent) !important; border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px rgba(185,245,106,.18);
}
div[data-testid="stSliderThumbValue"], div[data-testid="stSliderTickBarMin"], div[data-testid="stSliderTickBarMax"] { color: var(--text-2) !important; }

/* Expander / tables / alerts */
div[data-testid="stExpander"] {
    background: rgba(255,255,255,.03); border: 1px solid var(--line) !important; border-radius: 16px;
}
div[data-testid="stDataFrame"], div[data-testid="stTable"] {
    border: 1px solid var(--line); border-radius: 14px; overflow: hidden; background: rgba(255,255,255,.02);
}
div[data-testid="stTable"] table { color: var(--text-2); }
div[data-testid="stTable"] th { background: rgba(185,245,106,.07) !important; color: var(--accent) !important; font-size: .78rem; letter-spacing: .04em; }
div[data-testid="stTable"] td { border-color: var(--line) !important; }
div[data-testid="stAlert"] { border-radius: 14px; }
div[data-testid="stCodeBlock"], pre { border-radius: 14px !important; border: 1px solid var(--line); }

/* Dialog */
div[role="dialog"] { background: #0e1712 !important; border: 1px solid var(--line-strong); border-radius: 24px !important; }

/* ---------- Mobile ---------- */
@media (max-width: 800px) {
    .block-container, div[data-testid="stMainBlockContainer"] { padding: 1.2rem 1rem 3rem !important; }
    .hero { padding: 1.5rem 1.3rem; border-radius: 22px; }
    .hero:before { display: none; }
    .hero-logo { width: 52px; height: 52px; font-size: 1.6rem; }
    .kpi-grid { grid-template-columns: 1fr; }
    .bar-row { grid-template-columns: 1fr; gap: .35rem; }
    .bar-val { text-align: left; }
    .ring { width: 132px; height: 132px; }
    .ring-in { width: 102px; height: 102px; }
    .ring-in b { font-size: 2.2rem; }
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONSTANTS & EMISSION FACTORS
# ==============================================================================
ELECTRICITY_FACTOR = 0.727   # kg CO2 per kWh (India grid average)
LPG_FACTOR = 42.6            # kg CO2 per 14.2 kg LPG cylinder
FLIGHT_FACTOR = 300          # kg CO2 per round-trip flight (avg. Indian domestic)
SHOPPING_FACTOR = 0.012      # kg CO2 per rupee spent
INDIA_AVERAGE = 2000         # kg CO2 per person per year
TREE_ABSORBS = 21            # kg CO2 absorbed per tree per year

# Sustainability Score: 100 = zero footprint, 50 = India average, 0 = 2x India average (or more)
SCORE_CEILING = 2 * INDIA_AVERAGE

# (minimum score, label, colour)
SCORE_BANDS = [
    (80, "🏆 Green Leader", "#52b788"),
    (60, "🌿 Eco-Aware", "#74c69d"),
    (40, "🌤️ Moderate Impact", "#e9c46a"),
    (20, "⚠️ High Impact", "#f4a261"),
    (0, "🚨 Critical Impact", "#e76f51"),
]

CATEGORY_META = {
    "Electricity": {
        "emoji": "⚡",
        "color": "#f5c451",
        "bullets": [
            "Switch to **LED bulbs** & **5-star appliances**",
            "Turn off idle devices at the plug",
            "Explore **rooftop solar** panels"
        ]
    },
    "Cooking gas": {
        "emoji": "🔥",
        "color": "#ff8a5b",
        "bullets": [
            "Use a **pressure cooker** to cut gas time",
            "Always **cover pots** while cooking",
            "Switch partially to **induction cooking**"
        ]
    },
    "Commute": {
        "emoji": "🚆",
        "color": "#5ec8f2",
        "bullets": [
            "Shift daily trips to **Metro, Bus, or Carpool**",
            "**Walk or cycle** for trips under 3 km",
            "Combine errands into one route"
        ]
    },
    "Flights": {
        "emoji": "✈️",
        "color": "#a78bfa",
        "bullets": [
            "Take an **overnight train** for trips under 500 km",
            "Combine work & personal trips",
            "Choose direct flights over layovers"
        ]
    },
    "Food": {
        "emoji": "🥗",
        "color": "#6ee7a8",
        "bullets": [
            "Add **2–3 plant-based days** per week",
            "Buy **local & seasonal** produce",
            "Plan portions to **cut food waste**"
        ]
    },
    "Shopping": {
        "emoji": "♻️",
        "color": "#f472b6",
        "bullets": [
            "Buy **fewer, durable** clothes & gadgets",
            "**Repair or buy refurbished** electronics",
            "Segregate & **recycle dry waste**"
        ]
    },
}

TRANSPORT_MAP = {
    "🚗 Car": 0.17,
    "🏍️ Motorbike": 0.07,
    "🚌 Bus": 0.09,
    "🚆 Train/Metro": 0.04,
    "🚶 Walk/Cycle": 0.0,
}

DIET_MAP = {
    "🥗 Vegetarian": 1.7,
    "🍛 Mixed": 2.5,
    "🍗 Non-veg most days": 3.3,
}

RECYCLE_MAP = {
    "🗑️ Almost nothing": 1.0,
    "📦 Some": 0.8,
    "🌱 Most": 0.6,
}

IST = timezone(timedelta(hours=5, minutes=30))


# ==============================================================================
# CORE LOGIC (calculation, score, reports)
# ==============================================================================
def calculate_footprint(data):
    electricity = data["kwh"] * ELECTRICITY_FACTOR * 12 / data["people"]
    cooking_gas = data["cylinders"] * LPG_FACTOR * 12 / data["people"]
    commute = data["km_per_week"] * TRANSPORT_MAP[data["mode"]] * 52
    flying = data["flights"] * FLIGHT_FACTOR
    food = DIET_MAP[data["diet"]] * 365
    shopping = data["shopping_rs"] * SHOPPING_FACTOR * 12 * RECYCLE_MAP[data["recycle"]]

    categories = {
        "Electricity": electricity,
        "Cooking gas": cooking_gas,
        "Commute": commute,
        "Flights": flying,
        "Food": food,
        "Shopping": shopping,
    }
    return categories, sum(categories.values())


def sustainability_score(total):
    """0-100 score. 100 = zero emissions, 50 = India average, 0 = 2x India average or worse."""
    raw = 100 * (1 - total / SCORE_CEILING)
    return int(round(max(0, min(100, raw))))


def score_band(score):
    """Returns (label, colour) for a score."""
    for minimum, label, colour in SCORE_BANDS:
        if score >= minimum:
            return label, colour
    return SCORE_BANDS[-1][1], SCORE_BANDS[-1][2]


def clean_label(text):
    """'🚆 Train/Metro' -> 'Train/Metro' (drops the leading emoji for reports)."""
    parts = str(text).split(" ", 1)
    return parts[1] if len(parts) == 2 else str(text)


def make_results(inputs):
    categories, total = calculate_footprint(inputs)
    score = sustainability_score(total)
    return {
        "categories": categories,
        "total": total,
        "score": score,
        "generated": datetime.now(IST).strftime("%d %b %Y, %H:%M IST"),
        "celebrated": False,
    }


def build_csv_report(inputs, res):
    """CSV (Excel / Google Sheets friendly) so the user can tally the totals themselves."""
    categories = res["categories"]
    total = res["total"]
    score = res["score"]
    label, _ = score_band(score)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Section", "Item", "Value", "Unit", "Share_%"])
    w.writerow(["Report", "App", "EcoSync - Personal Carbon Footprint Calculator", "", ""])
    w.writerow(["Report", "Generated", res.get("generated", ""), "", ""])

    # Inputs
    w.writerow(["Input", "Electricity", inputs["kwh"], "kWh/month", ""])
    w.writerow(["Input", "LPG cylinders", inputs["cylinders"], "cylinders/month", ""])
    w.writerow(["Input", "People at home", inputs["people"], "persons", ""])
    w.writerow(["Input", "Primary travel mode", clean_label(inputs["mode"]), "", ""])
    w.writerow(["Input", "Weekly distance", inputs["km_per_week"], "km/week", ""])
    w.writerow(["Input", "Round-trip flights", inputs["flights"], "flights/year", ""])
    w.writerow(["Input", "Diet", clean_label(inputs["diet"]), "", ""])
    w.writerow(["Input", "Recycling level", clean_label(inputs["recycle"]), "", ""])
    w.writerow(["Input", "Shopping spend", inputs["shopping_rs"], "INR/month", ""])

    # Emissions (these rows add up to the TOTAL row)
    for name, value in categories.items():
        share = (value / total * 100) if total > 0 else 0
        w.writerow(["Emission", name, round(value, 2), "kg CO2/year", round(share, 1)])
    w.writerow(["Emission", "TOTAL (sum of the 6 categories)", round(total, 2), "kg CO2/year",
                100.0 if total > 0 else 0.0])
    w.writerow(["Emission", "TOTAL in tonnes", round(total / 1000, 3), "tonnes CO2/year", ""])

    # Comparison & score
    w.writerow(["Benchmark", "India per-capita average", INDIA_AVERAGE, "kg CO2/year", ""])
    w.writerow(["Benchmark", "Your footprint vs India average", round(total / INDIA_AVERAGE, 2), "x", ""])
    w.writerow(["Benchmark", "Trees needed to offset", round(total / TREE_ABSORBS), "trees/year", ""])
    w.writerow(["Score", "Sustainability Score", score, "out of 100", ""])
    w.writerow(["Score", "Rating", clean_label(label), "", ""])

    # Factors used (for audit)
    w.writerow(["Factor", "Electricity", ELECTRICITY_FACTOR, "kg CO2/kWh", ""])
    w.writerow(["Factor", "LPG", LPG_FACTOR, "kg CO2/cylinder", ""])
    for mode, factor in TRANSPORT_MAP.items():
        w.writerow(["Factor", f"Travel - {clean_label(mode)}", factor, "kg CO2/km", ""])
    w.writerow(["Factor", "Flight", FLIGHT_FACTOR, "kg CO2/round trip", ""])
    for diet, factor in DIET_MAP.items():
        w.writerow(["Factor", f"Diet - {clean_label(diet)}", factor, "kg CO2/day", ""])
    w.writerow(["Factor", "Shopping", SHOPPING_FACTOR, "kg CO2/INR", ""])
    for rec, factor in RECYCLE_MAP.items():
        w.writerow(["Factor", f"Recycling - {clean_label(rec)}", factor, "multiplier", ""])

    # utf-8-sig so Excel opens it correctly
    return buf.getvalue().encode("utf-8-sig")


def build_text_report(inputs, res):
    """Human-readable, printable summary."""
    categories = res["categories"]
    total = res["total"]
    score = res["score"]
    label, _ = score_band(score)
    ratio = total / INDIA_AVERAGE

    lines = []
    lines.append("=" * 62)
    lines.append("  ECOSYNC - PERSONAL CARBON FOOTPRINT REPORT")
    lines.append("=" * 62)
    lines.append(f"Generated : {res.get('generated', '')}")
    lines.append("")
    lines.append("YOUR INPUTS")
    lines.append("-" * 62)
    lines.append(f"Electricity        : {inputs['kwh']:,.1f} kWh / month")
    lines.append(f"LPG cylinders      : {inputs['cylinders']:,.1f} / month")
    lines.append(f"People at home     : {inputs['people']}")
    lines.append(f"Travel mode        : {clean_label(inputs['mode'])}")
    lines.append(f"Weekly distance    : {inputs['km_per_week']} km")
    lines.append(f"Round-trip flights : {inputs['flights']:,.1f} / year")
    lines.append(f"Diet               : {clean_label(inputs['diet'])}")
    lines.append(f"Recycling          : {clean_label(inputs['recycle'])}")
    lines.append(f"Shopping spend     : INR {inputs['shopping_rs']:,.0f} / month")
    lines.append("")
    lines.append("EMISSIONS BREAKDOWN (kg CO2 / year)")
    lines.append("-" * 62)
    for name, value in categories.items():
        share = (value / total * 100) if total > 0 else 0
        lines.append(f"{name:<18} {value:>12,.1f} kg   {share:>5.1f}%")
    lines.append("-" * 62)
    lines.append(f"{'TOTAL':<18} {total:>12,.1f} kg   100.0%")
    lines.append(f"{'':<18} {total / 1000:>12,.3f} tonnes CO2 / year")
    lines.append("")
    lines.append("BENCHMARKS")
    lines.append("-" * 62)
    lines.append(f"India per-capita average : {INDIA_AVERAGE:,} kg CO2 / year")
    lines.append(f"You vs India average     : {ratio:.2f}x")
    lines.append(f"Trees needed to offset   : {round(total / TREE_ABSORBS):,} per year")
    lines.append("")
    lines.append(f"SUSTAINABILITY SCORE : {score} / 100  ({clean_label(label)})")
    lines.append("  Score = 100 x (1 - Total / (2 x India average)), limited to 0-100")
    lines.append("")
    lines.append("TOP 3 AREAS TO IMPROVE")
    lines.append("-" * 62)
    top3 = sorted(categories, key=categories.get, reverse=True)[:3]
    for rank, name in enumerate(top3, start=1):
        if categories[name] > 0:
            lines.append(f"#{rank} {name} ({categories[name]:,.0f} kg)")
            for b in CATEGORY_META[name]["bullets"]:
                lines.append(f"    - {b.replace('**', '')}")
    lines.append("")
    lines.append("Note: This is an estimate based on average emission factors.")
    lines.append("See the Methodology and Sources pages in the app for details.")
    lines.append("=" * 62)
    return "\n".join(lines).encode("utf-8")


def categories_df(categories):
    return pd.DataFrame(
        {"kg CO₂ / year": list(categories.values())},
        index=list(categories.keys()),
    )


# ==============================================================================
# UI COMPONENTS (HTML building blocks)
# ==============================================================================
def md_bold(text):
    """Convert **bold** markers into <b> tags for use inside raw HTML."""
    parts = text.split("**")
    return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))


def section_header(icon, title, sub="", step=""):
    step_html = f'<div class="sec-step">{step}</div>' if step else ""
    html(f"""
    <div class="sec-head">
        <div class="sec-ico">{icon}</div>
        <div><div class="sec-title">{title}</div><div class="sec-sub">{sub}</div></div>
        {step_html}
    </div>
    """)


def kpi_card(icon, label, value, sub="", good=False):
    return (
        f'<div class="kpi{" good" if good else ""}">'
        f'<div class="kpi-ico">{icon}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>'
    )


def breakdown_bars_html(categories, total):
    mx = max(categories.values()) or 1
    rows = ""
    for name, v in categories.items():
        meta = CATEGORY_META[name]
        c = meta["color"]
        share = (v / total * 100) if total > 0 else 0
        width = v / mx * 100
        rows += (
            f'<div class="bar-row">'
            f'<div class="bar-label"><span class="bar-ico" style="background:{c}22;color:{c}">{meta["emoji"]}</span>{name}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%;background:linear-gradient(90deg,{c}88,{c})"></div></div>'
            f'<div class="bar-val">{v:,.0f} <small>kg · {share:.0f}%</small></div>'
            f'</div>'
        )
    return rows


def compare_bars_html(before, after):
    mx = max(list(before.values()) + list(after.values())) or 1
    rows = (
        '<div class="legend"><span><i style="background:rgba(255,255,255,.28)"></i>Current</span>'
        '<span><i style="background:#b9f56a"></i>Simulated</span></div>'
    )
    for name in before:
        b, a = before[name], after[name]
        diff = b - a
        note = f"−{diff:,.0f} kg" if diff > 0.5 else "no change"
        rows += (
            f'<div class="cmp-row"><div class="cmp-name">{CATEGORY_META[name]["emoji"]} {name}<span>{b:,.0f} → {a:,.0f} kg · {note}</span></div>'
            f'<div class="cmp-bar"><div style="width:{b / mx * 100:.1f}%;background:rgba(255,255,255,.28)"></div></div>'
            f'<div class="cmp-bar"><div style="width:{a / mx * 100:.1f}%;background:linear-gradient(90deg,#8fe39a,#b9f56a)"></div></div></div>'
        )
    return rows


# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
if "page" not in st.session_state:
    st.session_state["page"] = "input"
if "inputs" not in st.session_state:
    st.session_state["inputs"] = {
        "kwh": 150.0,
        "cylinders": 1.0,
        "people": 4,
        "mode": "🚆 Train/Metro",
        "km_per_week": 50,
        "flights": 1.0,
        "diet": "🍛 Mixed",
        "recycle": "📦 Some",
        "shopping_rs": 2000,
    }
if "results" not in st.session_state:
    st.session_state["results"] = None


# --- POP-UP BEGINNER GUIDE ---
@_dialog("🌿 EcoSync — 30-Second Guide")
def show_onboarding_popup():
    st.markdown("**Rough estimates are totally fine!** Just fill 3 quick steps:")
    html("""
    <div class="guide-row"><div class="guide-icon">🏠</div>
        <div><b>Step 1: Home Energy</b><br>
        • Monthly electricity units (check power bill)<br>
        • Monthly LPG cylinders &amp; household size</div></div>
    <div class="guide-row"><div class="guide-icon">🚆</div>
        <div><b>Step 2: Travel &amp; Flights</b><br>
        • Main daily ride &amp; weekly km<br>
        • Round-trip flights taken per year</div></div>
    <div class="guide-row"><div class="guide-icon">🥗</div>
        <div><b>Step 3: Food &amp; Shopping</b><br>
        • Diet style &amp; waste recycling habit<br>
        • Monthly spend on clothes &amp; gadgets</div></div>
    """)
    st.caption("💡 Hover over any (?) icon for quick examples.")
    if st.button("Let's Calculate 🚀", type="primary", **BTN):
        st.session_state["seen_guide"] = True
        st.rerun()


if "seen_guide" not in st.session_state:
    st.session_state["seen_guide"] = False
    show_onboarding_popup()

# ---------- PAGE STATE (used by the nav) ----------
CALC_PAGES = ("input", "results", "simulator")
has_results = st.session_state["results"] is not None

# Safety net: result pages need results
if st.session_state["page"] in ("results", "simulator") and not has_results:
    st.session_state["page"] = "input"

current_page = st.session_state["page"]
if current_page in CALC_PAGES:
    st.session_state["last_calc_page"] = current_page
    section = "calculator"
else:
    section = current_page  # "methodology" or "sources"

# ---------- SIDEBAR NAVIGATION ----------
NAV_ITEMS = [
    # (button label, page key, needs results first?)
    ("🧮 Calculator", "input", False),
    ("📊 Results", "results", True),
    ("⚡ What-If Simulator", "simulator", True),
    ("📐 Methodology", "methodology", False),
    ("🔗 Sources", "sources", False),
]

with st.sidebar:
    html("""
    <div class="brand">
        <div class="brand-logo">🌿</div>
        <div><div class="brand-name">EcoSync</div><div class="brand-sub">Carbon Footprint Engine</div></div>
    </div>
    <div class="side-label">NAVIGATE</div>
    """)
    for label, target, needs_results in NAV_ITEMS:
        if st.button(
            label,
            key=f"side_{target}",
            type="primary" if current_page == target else "secondary",
            disabled=needs_results and not has_results,
            **BTN
        ):
            st.session_state["page"] = target
            st.rerun()
    html('<div class="side-label">HELP</div>')
    if st.button("❓ How to use", key="side_guide", **BTN):
        st.session_state["show_guide"] = True
    html('<div class="side-foot">💡 Calculate first to unlock <b>Results</b> &amp; <b>What-If</b>.<br>SUS-05 · Track T3 Sustainability</div>')

# Open the guide pop-up outside the sidebar (safer across Streamlit versions)
if st.session_state.pop("show_guide", False):
    show_onboarding_popup()

# ---------- HERO ----------
html("""
<div class="hero">
    <div class="hero-row">
        <div class="hero-logo">🌿</div>
        <div>
            <h1>EcoSync</h1>
            <p class="tag">Measure • Analyze • Simulate your personal carbon footprint</p>
        </div>
    </div>
    <div class="chips">
        <span class="chip">📐 <b>6</b> emission categories</span>
        <span class="chip">🇮🇳 India-calibrated factors</span>
        <span class="chip">⚡ Live what-if simulator</span>
        <span class="chip">📥 Downloadable report</span>
    </div>
</div>
""")

# ---------- CALCULATOR STEPS (only shown inside the Calculator section) ----------
if section == "calculator":
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button(
            "1️⃣ Input",
            key="nav_input",
            type="primary" if current_page == "input" else "secondary",
            **BTN
        ):
            st.session_state["page"] = "input"
            st.rerun()
    with nav2:
        if st.button(
            "2️⃣ Results",
            key="nav_results",
            type="primary" if current_page == "results" else "secondary",
            disabled=not has_results,
            **BTN
        ):
            st.session_state["page"] = "results"
            st.rerun()
    with nav3:
        if st.button(
            "3️⃣ What-If",
            key="nav_sim",
            type="primary" if current_page == "simulator" else "secondary",
            disabled=not has_results,
            **BTN
        ):
            st.session_state["page"] = "simulator"
            st.rerun()
    st.write("")

# ==============================================================================
# PAGE 1: LIFESTYLE INPUT PAGE
# ==============================================================================
if st.session_state["page"] == "input":
    inp = st.session_state["inputs"]

    with st.form("ecosync_input_form"):
        # ---- Step 1 ----
        with st.container(border=True):
            section_header("🏠", "Home & Energy", "Your household's monthly usage", "STEP 1 / 3")
            c1, c2, c3 = st.columns(3)
            with c1:
                kwh = st.number_input(
                    "⚡ Electricity / mo (kWh)", min_value=0.0, value=float(inp["kwh"]), step=10.0,
                    help="Check 'Units Consumed' on your monthly power bill."
                )
            with c2:
                cylinders = st.number_input(
                    "🔥 LPG cylinders / mo", min_value=0.0, value=float(inp["cylinders"]), step=0.5,
                    help="0.5 = 1 cylinder lasts 2 months."
                )
            with c3:
                people = st.number_input(
                    "👨‍👩‍👧‍👦 People at home", min_value=1, value=int(inp["people"]), step=1,
                    help="Splits home energy emissions per person."
                )

        # ---- Step 2 ----
        with st.container(border=True):
            section_header("🚦", "Travel & Flights", "How you move around", "STEP 2 / 3")
            mode_options = list(TRANSPORT_MAP.keys())
            mode = st.radio(
                "Primary daily travel mode",
                mode_options,
                index=mode_options.index(inp["mode"]),
                horizontal=True
            )
            c4, c5 = st.columns(2)
            with c4:
                km_per_week = st.slider(
                    "🛣️ Weekly distance (km)", min_value=0, max_value=500, value=int(inp["km_per_week"]), step=5,
                    help="e.g., 10 km/day × 5 days = 50 km/week."
                )
            with c5:
                flights = st.number_input(
                    "✈️ Round-trip flights / yr", min_value=0.0, value=float(inp["flights"]), step=1.0,
                    help="1 round-trip = going + returning."
                )

        # ---- Step 3 ----
        with st.container(border=True):
            section_header("🛍️", "Diet & Shopping", "What you eat and buy", "STEP 3 / 3")
            c6, c7 = st.columns(2)
            diet_options = list(DIET_MAP.keys())
            recycle_options = list(RECYCLE_MAP.keys())
            with c6:
                diet = st.selectbox("🍽️ Diet preference", diet_options, index=diet_options.index(inp["diet"]))
            with c7:
                recycle = st.selectbox("♻️ Recycling level", recycle_options, index=recycle_options.index(inp["recycle"]))

            shopping_rs = st.slider(
                "🛍️ Monthly shopping spend (₹)", min_value=0, max_value=30000, value=int(inp["shopping_rs"]), step=500,
                help="Clothes, gadgets & online orders (exclude rent & groceries)."
            )

        submitted = st.form_submit_button("Calculate & View Results →", **SUBMIT)

    if submitted:
        updated_inputs = {
            "kwh": kwh,
            "cylinders": cylinders,
            "people": int(people),
            "mode": mode,
            "km_per_week": km_per_week,
            "flights": flights,
            "diet": diet,
            "recycle": recycle,
            "shopping_rs": shopping_rs,
        }
        st.session_state["inputs"] = updated_inputs
        st.session_state["results"] = make_results(updated_inputs)
        st.session_state["page"] = "results"
        st.rerun()

# ==============================================================================
# PAGE 2: RESULTS & RECOMMENDATIONS PAGE
# ==============================================================================
elif st.session_state["page"] == "results":
    res = st.session_state["results"]
    inputs = st.session_state["inputs"]
    categories = res["categories"]
    total = res["total"]
    score = res["score"]
    score_label, score_color = score_band(score)
    ratio = round(total / INDIA_AVERAGE, 1)
    trees = round(total / TREE_ABSORBS)

    # Status Banner
    if total <= INDIA_AVERAGE:
        if not res.get("celebrated"):
            st.balloons()
            res["celebrated"] = True
        html(f"""
        <div class="banner good"><div class="b-ico">🎉</div>
        <div><b>Eco-Champion!</b> Your footprint (<b>{total:,.0f} kg/yr</b>) beats the India average
        ({INDIA_AVERAGE:,} kg/yr).</div></div>
        """)
    else:
        html(f"""
        <div class="banner warn"><div class="b-ico">📢</div>
        <div><b>Heads up:</b> you are at <b>{ratio}x</b> the India average ({INDIA_AVERAGE:,} kg/yr).
        See your top 3 fixes below.</div></div>
        """)

    # Score card + KPI tiles (bento row)
    left, right = st.columns([1.25, 1])
    with left:
        html(f"""
        <div class="card"><div class="score-wrap">
            <div class="ring" style="--p:{score}; --c:{score_color};">
                <div class="ring-in"><b>{score}</b><span>/ 100</span></div>
            </div>
            <div class="score-txt">
                <div class="eyebrow">Sustainability Score</div>
                <div class="score-title" style="color:{score_color};">{score_label}</div>
                <div style="font-size:.85rem;color:#8aa092;">100 = zero emissions · 50 = India average · 0 = 2× India average or more</div>
                <div class="scale"><i style="left:{max(2, min(98, score))}%;"></i></div>
                <div class="scale-lbl"><span>0</span><span>India avg · 50</span><span>100</span></div>
            </div>
        </div></div>
        """)
    with right:
        html(
            '<div style="display:grid;grid-template-columns:1fr;gap:.9rem;">'
            + kpi_card("🌍", "Yearly footprint", f"{total:,.0f} kg", f"{total / 1000:.2f} tonnes CO₂", good=total <= INDIA_AVERAGE)
            + '<div class="kpi-grid" style="grid-template-columns:1fr 1fr;">'
            + kpi_card("🇮🇳", "vs. India avg", f"{ratio}x", f"Avg: {INDIA_AVERAGE:,} kg")
            + kpi_card("🌳", "Forest offset", f"{trees:,}", "trees needed / year")
            + '</div></div>'
        )

    st.write("")
    with st.container(border=True):
        section_header("📊", "Emissions Breakdown", "Where your CO₂ comes from (kg CO₂ / year)")
        html(breakdown_bars_html(categories, total))

    with st.expander("📋 View exact table & percentages"):
        rows = [
            {
                "Category": f"{CATEGORY_META[k]['emoji']} {k}",
                "Yearly CO₂ (kg)": f"{v:,.0f}",
                "Share": f"{(v / total * 100) if total > 0 else 0:.1f}%"
            }
            for k, v in categories.items()
        ]
        rows.append({
            "Category": "🧮 TOTAL",
            "Yearly CO₂ (kg)": f"{total:,.0f}",
            "Share": "100.0%" if total > 0 else "0.0%",
        })
        st.table(rows)

    # Top 3 Visual Action Cards
    st.markdown("### 💡 Top 3 high-impact recommendations")
    sorted_cats = sorted(categories, key=categories.get, reverse=True)[:3]

    for rank, name in enumerate(sorted_cats, start=1):
        kg = categories[name]
        if kg > 0:
            meta = CATEGORY_META[name]
            bullets_html = "".join(f"<li>{md_bold(b)}</li>" for b in meta["bullets"])
            html(f"""
            <div class="tip" style="--tc:{meta['color']};">
                <div class="tip-emoji">{meta['emoji']}</div>
                <div>
                    <div class="tip-rank">PRIORITY #{rank}</div>
                    <div class="tip-title">{name} <span>— {kg:,.0f} kg CO₂/yr ({kg / total * 100:.0f}%)</span></div>
                    <ul>{bullets_html}</ul>
                </div>
            </div>
            """)

    # Download Report
    st.markdown("### 📥 Download your emission report")
    st.caption(
        "Tally your total yourself: the **CSV** opens in Excel / Google Sheets "
        "(category rows add up to the TOTAL row). The **TXT** is a printable summary."
    )
    stamp = datetime.now(IST).strftime("%Y%m%d_%H%M")
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "📊 Download CSV (for tally)",
            data=build_csv_report(inputs, res),
            file_name=f"ecosync_report_{stamp}.csv",
            mime="text/csv",
            key="dl_csv",
            **DL
        )
    with d2:
        st.download_button(
            "📄 Download Text Report",
            data=build_text_report(inputs, res),
            file_name=f"ecosync_report_{stamp}.txt",
            mime="text/plain",
            key="dl_txt",
            **DL
        )

    # Bottom Page Navigation Buttons
    st.divider()
    b1, b2 = st.columns(2)
    with b1:
        if st.button("← Edit My Details", key="res_edit", **BTN):
            st.session_state["page"] = "input"
            st.rerun()
    with b2:
        if st.button("⚡ Try What-If Simulator →", key="res_sim", type="primary", **BTN):
            st.session_state["page"] = "simulator"
            st.rerun()

# ==============================================================================
# PAGE 3: INTERACTIVE WHAT-IF SIMULATOR PAGE
# ==============================================================================
elif st.session_state["page"] == "simulator":
    base_inp = st.session_state["inputs"]
    base_res = st.session_state["results"]
    base_total = base_res["total"]
    base_score = base_res["score"]

    st.markdown("### ⚡ What-If Action Simulator")
    st.caption("Toggle greener habits below to see how much CO₂ you save instantly!")

    metro_key = "🚆 Train/Metro"
    veg_key = "🥗 Vegetarian"
    recycle_key = "🌱 Most"
    can_metro = TRANSPORT_MAP[metro_key] < TRANSPORT_MAP[base_inp["mode"]]
    can_veg = DIET_MAP[veg_key] < DIET_MAP[base_inp["diet"]]
    can_recycle = RECYCLE_MAP[recycle_key] < RECYCLE_MAP[base_inp["recycle"]]

    with st.container(border=True):
        section_header("🎛️", "Choose your changes", "Adjust the sliders and switches")
        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            cut_elec = st.slider("⚡ Cut electricity usage by (%)", 0, 50, 20, step=5)
            switch_metro = st.checkbox(
                "🚆 Switch daily commute to Train/Metro",
                value=can_metro,
                disabled=not can_metro,
                help=None if can_metro else "Your current travel mode is already as low or lower."
            )
            max_flights = int(base_inp["flights"])
            if max_flights >= 1:
                cut_flights = st.slider("✈️ Reduce round-trip flights by", 0, max_flights, 1)
            else:
                cut_flights = 0
                st.caption("✈️ No flights entered, nothing to reduce.")
        with sim_col2:
            veg_diet = st.checkbox(
                "🥗 Switch to a Vegetarian diet",
                value=can_veg,
                disabled=not can_veg,
                help=None if can_veg else "You already eat a vegetarian diet."
            )
            max_recycle = st.checkbox(
                "♻️ Recycle most household waste",
                value=can_recycle,
                disabled=not can_recycle,
                help=None if can_recycle else "You already recycle most waste."
            )
            cut_shopping = st.slider("🛍️ Cut monthly shopping spend by (%)", 0, 50, 15, step=5)

    # Build simulated input dictionary
    sim_inp = base_inp.copy()
    sim_inp["kwh"] = base_inp["kwh"] * (1 - cut_elec / 100)
    if switch_metro and can_metro:
        sim_inp["mode"] = metro_key
    sim_inp["flights"] = max(0.0, base_inp["flights"] - cut_flights)
    if veg_diet and can_veg:
        sim_inp["diet"] = veg_key
    if max_recycle and can_recycle:
        sim_inp["recycle"] = recycle_key
    sim_inp["shopping_rs"] = base_inp["shopping_rs"] * (1 - cut_shopping / 100)

    sim_cats, sim_total = calculate_footprint(sim_inp)
    sim_score = sustainability_score(sim_total)
    saved_kg = base_total - sim_total
    saved_trees = round(saved_kg / TREE_ABSORBS)
    reduction_pct = (saved_kg / base_total * 100) if base_total > 0 else 0
    score_gain = sim_score - base_score

    st.write("")
    html(
        '<div class="kpi-grid">'
        + kpi_card("📉", "New footprint", f"{sim_total:,.0f} kg", f"−{saved_kg:,.0f} kg saved", good=saved_kg > 0)
        + kpi_card("🌱", "Reduction", f"{reduction_pct:.1f}%", "lower emissions", good=reduction_pct > 0)
        + kpi_card("🌳", "Trees equivalent", f"+{saved_trees:,}", "planted per year")
        + '</div>'
    )
    st.write("")
    html(
        '<div class="kpi-grid" style="grid-template-columns:1fr 1fr;">'
        + kpi_card("🏅", "Current score", f"{base_score}/100", score_band(base_score)[0])
        + kpi_card("🚀", "Simulated score", f"{sim_score}/100", f"{score_gain:+d} pts · {score_band(sim_score)[0]}", good=score_gain > 0)
        + '</div>'
    )

    st.write("")
    with st.container(border=True):
        section_header("📊", "Before vs. After", "Category-by-category comparison (kg CO₂ / yr)")
        html(compare_bars_html(base_res["categories"], sim_cats))

    st.write("")
    if st.button("← Back to Results & Tips", key="sim_back", **BTN):
        st.session_state["page"] = "results"
        st.rerun()

# ==============================================================================
# PAGE 4: METHODOLOGY
# ==============================================================================
elif st.session_state["page"] == "methodology":
    st.markdown("### 📐 Methodology")
    st.caption("How EcoSync turns your daily habits into a carbon footprint and a Sustainability Score.")

    # --- 1. Problem statement alignment ---
    st.markdown("#### 🎯 1. Purpose & Problem Statement")
    st.markdown(
        "EcoSync addresses **SUS-05: Personal Carbon Footprint Calculator** (Track T3 – Sustainability). "
        "The goal is to help an ordinary person **measure** their yearly CO₂ emissions, "
        "**understand** which habits matter most, **compare** with the India average, and "
        "**act** through personalised tips and a what-if simulator."
    )
    st.markdown(
        "**Workflow:** Lifestyle inputs → Emission calculation → Sustainability Score → "
        "Top-3 recommendations → What-if simulation → Downloadable report."
    )

    # --- 2. Core method ---
    st.markdown("#### 🧮 2. Core Method")
    st.markdown(
        "EcoSync uses the standard **activity data × emission factor** approach "
        "(the basis of the GHG Protocol and IPCC inventories):"
    )
    st.code("CO₂ emissions (kg) = Activity amount × Emission factor", language="text")
    st.markdown(
        "- **Scope:** personal / household lifestyle emissions, expressed per person per year in **kg CO₂**.\n"
        "- **Six categories:** electricity, cooking gas (LPG), daily commute, flights, food, shopping.\n"
        "- **Annualisation:** monthly values × 12, weekly values × 52, daily values × 365.\n"
        "- **Household sharing:** electricity and LPG are divided by the number of people at home."
    )

    # --- 3. Formulas ---
    st.markdown("#### 📐 3. Formulas Used")
    formula_rows = [
        {
            "Category": "⚡ Electricity",
            "Formula": "kWh per month × factor × 12 ÷ people",
            "Factor": f"{ELECTRICITY_FACTOR} kg CO₂ / kWh",
        },
        {
            "Category": "🔥 Cooking gas",
            "Formula": "cylinders per month × factor × 12 ÷ people",
            "Factor": f"{LPG_FACTOR} kg CO₂ / cylinder",
        },
        {
            "Category": "🚆 Commute",
            "Formula": "km per week × mode factor × 52",
            "Factor": "see travel table below",
        },
        {
            "Category": "✈️ Flights",
            "Formula": "round trips per year × factor",
            "Factor": f"{FLIGHT_FACTOR} kg CO₂ / round trip",
        },
        {
            "Category": "🥗 Food",
            "Formula": "diet factor × 365",
            "Factor": "see diet table below",
        },
        {
            "Category": "🛍️ Shopping",
            "Formula": "monthly ₹ spend × factor × 12 × recycling multiplier",
            "Factor": f"{SHOPPING_FACTOR} kg CO₂ / ₹",
        },
    ]
    st.table(formula_rows)

    lookup_col1, lookup_col2 = st.columns(2)
    with lookup_col1:
        st.markdown("**Travel factors (kg CO₂ per km)**")
        st.table([{"Mode": clean_label(k), "Factor": v} for k, v in TRANSPORT_MAP.items()])
        st.markdown("**Recycling multiplier**")
        st.table([{"Level": clean_label(k), "Multiplier": v} for k, v in RECYCLE_MAP.items()])
    with lookup_col2:
        st.markdown("**Diet factors (kg CO₂ per day)**")
        st.table([{"Diet": clean_label(k), "Factor": v} for k, v in DIET_MAP.items()])

    # --- 4. Sustainability Score ---
    st.markdown("#### 🏅 4. Sustainability Score")
    st.markdown(
        "The score converts your yearly footprint into one easy **0–100** number "
        "(higher is better), using the India per-capita average as the reference point."
    )
    st.code(
        f"Score = 100 × (1 − Total footprint ÷ {SCORE_CEILING:,} kg)\n"
        f"        limited to the range 0 – 100\n"
        f"({SCORE_CEILING:,} kg = 2 × India average of {INDIA_AVERAGE:,} kg)",
        language="text",
    )
    st.table([
        {"Score": "80 – 100", "Rating": "🏆 Green Leader", "Meaning": "Well below the India average"},
        {"Score": "60 – 79", "Rating": "🌿 Eco-Aware", "Meaning": "Below the India average"},
        {"Score": "40 – 59", "Rating": "🌤️ Moderate Impact", "Meaning": "Around the India average"},
        {"Score": "20 – 39", "Rating": "⚠️ High Impact", "Meaning": "Well above the India average"},
        {"Score": "0 – 19", "Rating": "🚨 Critical Impact", "Meaning": "Far above the India average"},
    ])
    st.caption(
        "Examples: 0 kg → 100 • 1,000 kg → 75 • 2,000 kg (India average) → 50 • 4,000 kg or more → 0. "
        "The score is an approximate indicator for awareness, not an official certification."
    )

    # --- 5. Other indicators ---
    st.markdown("#### 🌳 5. Other Indicators")
    st.markdown(
        f"- **India average:** {INDIA_AVERAGE:,} kg CO₂ per person per year (approx. national per-capita level).\n"
        f"- **Trees needed:** total footprint ÷ {TREE_ABSORBS} kg (a commonly used estimate of the CO₂ "
        "absorbed by one mature tree per year).\n"
        "- **Recommendations:** the three categories with the highest emissions get targeted tips.\n"
        "- **What-if simulator:** re-runs the same formulas with your chosen reductions and shows "
        "the new footprint, savings and score."
    )

    # --- 6. Assumptions & limitations ---
    st.markdown("#### ⚠️ 6. Assumptions & Limitations")
    st.markdown(
        "- Emission factors are **rounded, India-oriented averages**; real values vary by state, "
        "vehicle, fuel mix and season.\n"
        "- Food and shopping use simplified per-day and per-rupee estimates.\n"
        "- Flight emissions use one average value per round trip, regardless of distance.\n"
        "- Only major lifestyle categories are counted (no water, waste-to-landfill, or home construction).\n"
        "- Results are meant for **awareness and comparison**, not for official carbon accounting."
    )

    st.divider()
    m1, m2 = st.columns(2)
    with m1:
        if st.button("← Back to Calculator", key="method_back", **BTN):
            st.session_state["page"] = st.session_state.get("last_calc_page", "input")
            st.rerun()
    with m2:
        if st.button("View Sources →", key="method_to_sources", type="primary", **BTN):
            st.session_state["page"] = "sources"
            st.rerun()

# ==============================================================================
# PAGE 5: SOURCES
# ==============================================================================
elif st.session_state["page"] == "sources":
    st.markdown("### 🔗 Sources & References")
    st.caption("Where EcoSync's method, emission factors and benchmarks come from.")
    st.markdown(
        "- **GHG Protocol** – accounting method (activity × emission factor): "
        "[ghgprotocol.org](https://ghgprotocol.org/)\n"
        "- **IPCC Emission Factor Database** – fuel (LPG) and general factors: "
        "[ipcc-nggip.iges.or.jp/EFDB](https://www.ipcc-nggip.iges.or.jp/EFDB/main.php)\n"
        "- **Central Electricity Authority (CEA), India** – CO₂ Baseline Database for the Indian power grid: "
        "[cea.nic.in](https://cea.nic.in/)\n"
        "- **UK DESNZ / DEFRA GHG Conversion Factors** – transport factors (car, bus, rail, flights): "
        "[gov.uk](https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting)\n"
        "- **Our World in Data** – India per-capita CO₂ emissions: "
        "[ourworldindata.org](https://ourworldindata.org/co2/country/india)\n"
        "- **Poore & Nemecek (2018), Science** – diet-related food emissions: "
        "[doi.org/10.1126/science.aaq0216](https://doi.org/10.1126/science.aaq0216)\n"
        "- **Bureau of Energy Efficiency (BEE), India** – appliance star ratings used in our tips: "
        "[beeindia.gov.in](https://beeindia.gov.in/)"
    )

    st.markdown("#### 🗂️ Which source supports what")
    st.table([
        {"EcoSync element": "Overall method (activity × factor)", "Reference basis": "GHG Protocol, IPCC"},
        {"EcoSync element": "⚡ Electricity factor", "Reference basis": "CEA CO₂ Baseline Database"},
        {"EcoSync element": "🔥 LPG factor", "Reference basis": "IPCC Emission Factor Database"},
        {"EcoSync element": "🚆 Travel & ✈️ flight factors", "Reference basis": "UK DESNZ / DEFRA conversion factors"},
        {"EcoSync element": "🥗 Diet factors", "Reference basis": "Poore & Nemecek (2018)"},
        {"EcoSync element": "🇮🇳 India average benchmark", "Reference basis": "Our World in Data"},
        {"EcoSync element": "💡 Appliance tips", "Reference basis": "Bureau of Energy Efficiency"},
    ])
    st.caption(
        "Factor values in EcoSync are rounded approximations informed by the sources above. "
        "For official reporting, use the latest published editions."
    )

    st.divider()
    sb1, sb2 = st.columns(2)
    with sb1:
        if st.button("← Back to Methodology", key="sources_to_method", **BTN):
            st.session_state["page"] = "methodology"
            st.rerun()
    with sb2:
        if st.button("Back to Calculator →", key="sources_back", type="primary", **BTN):
            st.session_state["page"] = st.session_state.get("last_calc_page", "input")
            st.rerun()
