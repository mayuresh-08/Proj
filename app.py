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
    layout="centered",
    initial_sidebar_state="collapsed"
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

# --- CUSTOM HACKATHON THEME ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #091510 0%, #10251d 55%, #0b1c15 100%);
        color: #e8f5e9;
    }
    .block-container,
    div[data-testid="stMainBlockContainer"] {
        padding-top: 2.8rem !important;
    }
    .hero-box {
        background: linear-gradient(120deg, #1b4332, #2d6a4f);
        padding: 1.3rem 1.8rem;
        border-radius: 16px;
        border: 1px solid #52b788;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }
    .hero-box h1 {
        margin: 0;
        color: #ffffff;
        font-size: 2rem;
    }
    .hero-box p {
        margin: 0.3rem 0 0 0;
        color: #d8f3dc;
        font-size: 1rem;
    }
    .step-badge {
        display: inline-block;
        background-color: #2d6a4f;
        color: #d8f3dc;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
        border: 1px solid #52b788;
    }
    .tip-card {
        background: rgba(27, 67, 50, 0.65);
        border-left: 5px solid #52b788;
        border-top: 1px solid #40916c;
        border-right: 1px solid #40916c;
        border-bottom: 1px solid #40916c;
        padding: 1rem 1.2rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .tip-emoji {
        font-size: 2.3rem;
        background: rgba(82, 183, 136, 0.2);
        padding: 0.6rem;
        border-radius: 12px;
        min-width: 60px;
        text-align: center;
    }
    .guide-row {
        background: rgba(45, 106, 79, 0.25);
        border: 1px solid #40916c;
        border-radius: 10px;
        padding: 0.7rem 0.9rem;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }
    .guide-icon {
        font-size: 1.8rem;
        min-width: 40px;
        text-align: center;
    }
    .score-card {
        background: rgba(27, 67, 50, 0.65);
        border: 1px solid #40916c;
        border-radius: 14px;
        padding: 1rem 1.3rem;
        margin: 0.6rem 0 0.4rem 0;
        display: flex;
        align-items: center;
        gap: 1.2rem;
    }
    .score-num {
        font-size: 3rem;
        font-weight: 800;
        line-height: 1;
        min-width: 130px;
        text-align: center;
    }
    .score-num span {
        font-size: 1.1rem;
        font-weight: 600;
        color: #b7e4c7;
    }
    .score-label {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
    }
    .score-sub {
        font-size: 0.9rem;
        color: #b7e4c7;
        margin-top: 0.2rem;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(27, 67, 50, 0.6);
        border: 1px solid #40916c;
        padding: 14px;
        border-radius: 12px;
    }
    div.stFormSubmitButton > button,
    div.stDownloadButton > button,
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #2d6a4f, #40916c);
        color: white;
        font-weight: 700;
        border-radius: 10px;
        border: 1px solid #74c69d;
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
        "bullets": [
            "Switch to **LED bulbs** & **5-star appliances**",
            "Turn off idle devices at the plug",
            "Explore **rooftop solar** panels"
        ]
    },
    "Cooking gas": {
        "emoji": "🔥",
        "bullets": [
            "Use a **pressure cooker** to cut gas time",
            "Always **cover pots** while cooking",
            "Switch partially to **induction cooking**"
        ]
    },
    "Commute": {
        "emoji": "🚆",
        "bullets": [
            "Shift daily trips to **Metro, Bus, or Carpool**",
            "**Walk or cycle** for trips under 3 km",
            "Combine errands into one route"
        ]
    },
    "Flights": {
        "emoji": "✈️",
        "bullets": [
            "Take an **overnight train** for trips under 500 km",
            "Combine work & personal trips",
            "Choose direct flights over layovers"
        ]
    },
    "Food": {
        "emoji": "🥗",
        "bullets": [
            "Add **2–3 plant-based days** per week",
            "Buy **local & seasonal** produce",
            "Plan portions to **cut food waste**"
        ]
    },
    "Shopping": {
        "emoji": "♻️",
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


# --- POP-UP BEGINNER GUIDE (CRISP BULLETS + EMOJI SIDE CARDS) ---
@_dialog("🌿 EcoSync — 30-Second Guide")
def show_onboarding_popup():
    st.markdown("**Rough estimates are totally fine!** Just fill 3 quick steps:")

    st.markdown("""
    <div class="guide-row">
        <div class="guide-icon">🏠</div>
        <div>
            <b>Step 1: Home Energy</b><br>
            • Monthly electricity units (check power bill)<br>
            • Monthly LPG cylinders & household size
        </div>
    </div>
    <div class="guide-row">
        <div class="guide-icon">🚆</div>
        <div>
            <b>Step 2: Travel & Flights</b><br>
            • Main daily ride & weekly km<br>
            • Round-trip flights taken per year
        </div>
    </div>
    <div class="guide-row">
        <div class="guide-icon">🥗</div>
        <div>
            <b>Step 3: Food & Shopping</b><br>
            • Diet style & waste recycling habit<br>
            • Monthly spend on clothes & gadgets
        </div>
    </div>
    """, unsafe_allow_html=True)

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

# ---------- TOP NAVIGATION BAR (very top of the site): Calculator | Methodology | Sources | Guide ----------
top1, top2, top3, top4 = st.columns([1.3, 1.4, 1.1, 0.9])
with top1:
    if st.button(
        "🧮 Calculator",
        key="top_calc",
        type="primary" if section == "calculator" else "secondary",
        **BTN
    ):
        target = st.session_state.get("last_calc_page", "input")
        if target in ("results", "simulator") and not has_results:
            target = "input"
        st.session_state["page"] = target
        st.rerun()
with top2:
    if st.button(
        "📐 Methodology",
        key="top_method",
        type="primary" if section == "methodology" else "secondary",
        **BTN
    ):
        st.session_state["page"] = "methodology"
        st.rerun()
with top3:
    if st.button(
        "🔗 Sources",
        key="top_sources",
        type="primary" if section == "sources" else "secondary",
        **BTN
    ):
        st.session_state["page"] = "sources"
        st.rerun()
with top4:
    if st.button("❓ Guide", key="top_guide", **BTN):
        show_onboarding_popup()

# ---------- HERO ----------
st.markdown("""
<div class="hero-box">
    <h1>🌿 EcoSync</h1>
    <p>Measure • Analyze • Simulate Your Personal Carbon Footprint</p>
</div>
""", unsafe_allow_html=True)

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

st.divider()

# ==============================================================================
# PAGE 1: LIFESTYLE INPUT PAGE
# ==============================================================================
if st.session_state["page"] == "input":
    inp = st.session_state["inputs"]

    with st.form("ecosync_input_form"):
        st.markdown('<span class="step-badge">1 OF 3 • HOME & ENERGY</span>', unsafe_allow_html=True)
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

        st.divider()
        st.markdown('<span class="step-badge">2 OF 3 • TRAVEL & FLIGHTS</span>', unsafe_allow_html=True)
        mode_options = list(TRANSPORT_MAP.keys())
        mode = st.radio(
            "🚦 Primary daily travel mode",
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

        st.divider()
        st.markdown('<span class="step-badge">3 OF 3 • DIET & SHOPPING</span>', unsafe_allow_html=True)
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
        st.success(f"🎉 **Eco-Champion!** Your footprint (**{total:,.0f} kg/yr**) beats the India average ({INDIA_AVERAGE:,} kg/yr).")
    else:
        st.warning(f"📢 **Heads Up:** You are at **{ratio}x** the India average ({INDIA_AVERAGE:,} kg/yr). See your top 3 fixes below!")

    # Top KPI Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("🌍 Yearly Footprint", f"{total:,.0f} kg", f"{total / 1000:.2f} tonnes CO₂", delta_color="off")
    m2.metric("🇮🇳 vs. India Avg", f"{ratio}x", f"Avg: {INDIA_AVERAGE:,} kg", delta_color="off")
    m3.metric("🌳 Forest Offset", f"{trees:,} trees", "needed per year", delta_color="off")

    # Sustainability Score
    st.markdown(f"""
    <div class="score-card">
        <div class="score-num" style="color: {score_color};">{score}<span>/100</span></div>
        <div>
            <div class="score-label">🏅 Sustainability Score — {score_label}</div>
            <div class="score-sub">100 = zero emissions • 50 = India average • 0 = 2× India average or more</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(int(score))

    st.markdown("### 📊 Emissions Breakdown (kg CO₂ / year)")
    st.bar_chart(categories_df(categories), color="#52b788")

    with st.expander("📋 View Exact Table & Percentages"):
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
    st.markdown("### 💡 Top 3 High-Impact Recommendations")
    sorted_cats = sorted(categories, key=categories.get, reverse=True)[:3]

    for rank, name in enumerate(sorted_cats, start=1):
        kg = categories[name]
        if kg > 0:
            emoji = CATEGORY_META[name]["emoji"]
            bullets_html = "".join([f"<li>{b}</li>" for b in CATEGORY_META[name]["bullets"]])
            st.markdown(f"""
            <div class="tip-card">
                <div class="tip-emoji">{emoji}</div>
                <div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: #b7e4c7;">
                        #{rank} {name} — {kg:,.0f} kg CO₂/yr ({kg / total * 100:.0f}%)
                    </div>
                    <ul style="margin: 0.35rem 0 0 1.1rem; padding: 0; color: #e8f5e9; font-size: 0.95rem;">
                        {bullets_html}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Download Report (end of results)
    st.divider()
    st.markdown("### 📥 Download Your Emission Report")
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

    st.markdown("### ⚡ EcoSync What-If Action Simulator")
    st.caption("Toggle greener habits below to see how much CO₂ you save instantly!")

    metro_key = "🚆 Train/Metro"
    veg_key = "🥗 Vegetarian"
    recycle_key = "🌱 Most"
    can_metro = TRANSPORT_MAP[metro_key] < TRANSPORT_MAP[base_inp["mode"]]
    can_veg = DIET_MAP[veg_key] < DIET_MAP[base_inp["diet"]]
    can_recycle = RECYCLE_MAP[recycle_key] < RECYCLE_MAP[base_inp["recycle"]]

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

    st.divider()
    s1, s2, s3 = st.columns(3)
    s1.metric("📉 New Footprint", f"{sim_total:,.0f} kg", f"-{saved_kg:,.0f} kg saved", delta_color="inverse")
    s2.metric("🌱 Reduction", f"{reduction_pct:.1f}%", "lower emissions", delta_color="off")
    s3.metric("🌳 Trees Equivalent", f"+{saved_trees:,} trees", "planted per year", delta_color="off")

    t1, t2 = st.columns(2)
    t1.metric("🏅 Current Score", f"{base_score}/100", score_band(base_score)[0], delta_color="off")
    t2.metric("🏅 Simulated Score", f"{sim_score}/100", f"{score_gain:+d} pts", delta_color="normal")

    st.markdown("#### Before vs. After Comparison (kg CO₂/yr)")
    comparison_df = pd.DataFrame(
        {
            "Current Lifestyle": list(base_res["categories"].values()),
            "EcoSync Simulated": list(sim_cats.values()),
        },
        index=list(base_res["categories"].keys()),
    )
    st.bar_chart(comparison_df)

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
