# ───────────────────────────────────────────────────────────────
# app.py  ·  Solar Rooftop/Hybrid System Sizer  ·  July‑2025
# ----------------------------------------------------------------
# • Streamlit front‑end for the earlier CLI sizing script
# • City‑specific GHI, grid tariff & export rate
# • Height‑based panel recommendation
# • Simple pay‑back calculation
# ----------------------------------------------------------------
import streamlit as st
from dataclasses import dataclass
import re

# ───────────────────────────────────────────────────────────────
# 1.  CITY‑WISE SOLAR & TARIFF DATA (update as tariffs change)
# ───────────────────────────────────────────────────────────────
CITY_SOLAR_DATA = {
    "pune":           {"grid_tariff": 6.85, "export_rate": 3.90, "ghi": 5.5},
    "mumbai":         {"grid_tariff": 6.85, "export_rate": 3.90, "ghi": 5.0},
    "delhi":          {"grid_tariff": 5.50, "export_rate": 5.50, "ghi": 5.3},
    "bangalore":      {"grid_tariff": 7.00, "export_rate": 3.82, "ghi": 5.1},
    "hyderabad":      {"grid_tariff": 6.65, "export_rate": 3.15, "ghi": 5.4},
    "chennai":        {"grid_tariff": 5.80, "export_rate": 3.15, "ghi": 5.3},
    "kolkata":        {"grid_tariff": 6.10, "export_rate": 3.15, "ghi": 4.5},
    "jaipur":         {"grid_tariff": 6.50, "export_rate": 3.10, "ghi": 5.7},
    "ahmedabad":      {"grid_tariff": 6.10, "export_rate": 2.25, "ghi": 5.8},
    "surat":          {"grid_tariff": 6.10, "export_rate": 2.25, "ghi": 5.6},
    "coimbatore":     {"grid_tariff": 5.80, "export_rate": 3.15, "ghi": 5.2},
    "lucknow":        {"grid_tariff": 7.10, "export_rate": 3.82, "ghi": 5.2},
    "gurgaon":        {"grid_tariff": 6.00, "export_rate": 5.50, "ghi": 5.3},
    "vadodara":       {"grid_tariff": 6.10, "export_rate": 2.25, "ghi": 5.7},
    "nagpur":         {"grid_tariff": 6.85, "export_rate": 3.90, "ghi": 5.6},
    "visakhapatnam":  {"grid_tariff": 5.80, "export_rate": 3.15, "ghi": 5.1},
    "indore":         {"grid_tariff": 7.00, "export_rate": 3.90, "ghi": 5.5},
    "bhubaneswar":    {"grid_tariff": 6.10, "export_rate": 3.90, "ghi": 5.2},
    "varanasi":       {"grid_tariff": 7.10, "export_rate": 3.82, "ghi": 5.1},
    "default":        {"grid_tariff": 6.85, "export_rate": 3.90, "ghi": 5.0},
}

# ───────────────────────────────────────────────────────────────
# 2.  COST & TECH CONSTANTS
# ───────────────────────────────────────────────────────────────
APPLIANCE_P_RATED = {
    "AC 1.5 ton": 1600, "Fridge": 150, "TV": 120, "Fan": 60,
    "Light (LED)": 15, "Washing Machine": 500,
    "Laptop": 60, "Monitor": 30, "Other": 100,
}
DEFAULT_DUTY_HOURS = {
    "AC 1.5 ton": 6, "Fridge": 24, "TV": 4, "Fan": 8,
    "Light (LED)": 6, "Washing Machine": 0.5,
    "Laptop": 4, "Monitor": 4, "Other": 4,
}
DERATE_FACTOR              = 0.80
PANEL_COST_PER_KW          = 45_000
INVERTER_COSTS             = {"grid": 12_000, "hybrid": 20_000, "offgrid": 18_000}
BATTERY_COST_PER_KWH       = 13_000
SUBSIDY_FLAT_KW            = 3
SUBSIDY_PER_KW_FIRST3      = 26_000

# Height‑based module lookup (same JSON as earlier, trimmed for brevity)
PANEL_BY_HEIGHT = [
    {"floor_height_m":"3-15","optimal_panel_type":"Mono PERC / Bifacial",
     "recommended_companies":["LONGi","JA Solar","Jinko"],"typical_wattage_w":490,
     "typical_dimensions_mm":"2000 x 1134 x 32"},
    {"floor_height_m":"16-30","optimal_panel_type":"Half-cut Mono PERC / TOPCon",
     "recommended_companies":["Trina","Jinko","Canadian Solar"],"typical_wattage_w":535,
     "typical_dimensions_mm":"2278 x 1134 x 35"},
    {"floor_height_m":"31-45","optimal_panel_type":"TOPCon / HJT",
     "recommended_companies":["LONGi","JA Solar","Trina"],"typical_wattage_w":575,
     "typical_dimensions_mm":"2384 x 1096 x 35"},
    {"floor_height_m":"46-60","optimal_panel_type":"HJT / Bifacial (reinforced)",
     "recommended_companies":["LONGi","JA Solar","Canadian Solar"],"typical_wattage_w":600,
     "typical_dimensions_mm":"2384 x 1134 x 35"},
    {"floor_height_m":"61-75","optimal_panel_type":"HJT / CdTe Thin-film",
     "recommended_companies":["First Solar","Trina"],"typical_wattage_w":565,
     "typical_dimensions_mm":"2200 x 1190 x 35"},
    {"floor_height_m":"76-90","optimal_panel_type":"CdTe Thin-film / Reinforced HJT",
     "recommended_companies":["First Solar","LONGi"],"typical_wattage_w":565,
     "typical_dimensions_mm":"2200 x 1190 x 38"},
]

# ───────────────────────────────────────────────────────────────
# 3.  DATACLASSES
# ───────────────────────────────────────────────────────────────
@dataclass
class SolarDesign:
    pv_kw: float
    pv_cost: float
    roof_area_m2: float
    inverter_kw: float
    inverter_type: str
    inverter_cost: float
    battery_kwh: float
    battery_cost: float
    payback_years: float

@dataclass
class PanelRecommendation:
    panel_type: str
    brands: list[str]
    wattage_w: int
    size_mm: str

# ───────────────────────────────────────────────────────────────
# 4.  CORE LOGIC FUNCTIONS
# ───────────────────────────────────────────────────────────────
def recommend_panel_by_floor_height(height_m: float) -> PanelRecommendation:
    selected = PANEL_BY_HEIGHT[0]
    for rec in PANEL_BY_HEIGHT:
        lo, hi = map(float, re.split(r"-", rec["floor_height_m"]))
        if lo <= height_m <= hi:
            selected = rec
            break
    else:
        if height_m > float(PANEL_BY_HEIGHT[-1]["floor_height_m"].split('-')[1]):
            selected = PANEL_BY_HEIGHT[-1]
    return PanelRecommendation(selected["optimal_panel_type"],
                               selected["recommended_companies"],
                               selected["typical_wattage_w"],
                               selected["typical_dimensions_mm"])

def size_battery(outage_hours_week: float, daily_kwh: float) -> float:
    return round(daily_kwh * (outage_hours_week / 168) * 1.2, 1)

def compute_design(daily_kwh: float, ghi: float, outage_hours: float,
                   grid_tariff: float, inverter_type: str) -> SolarDesign:
    pv_kw = round((daily_kwh / ghi) / DERATE_FACTOR, 1)
    subsidy = min(pv_kw, SUBSIDY_FLAT_KW) * SUBSIDY_PER_KW_FIRST3 / SUBSIDY_FLAT_KW
    pv_cost = pv_kw * PANEL_COST_PER_KW - subsidy
    inv_kw = pv_kw
    inv_cost = inv_kw * INVERTER_COSTS[inverter_type]
    batt_kwh = size_battery(outage_hours, daily_kwh)
    batt_cost = batt_kwh * BATTERY_COST_PER_KWH
    annual_savings = daily_kwh * 365 * grid_tariff
    payback = round((pv_cost + inv_cost + batt_cost) / annual_savings, 1) if annual_savings else 0
    return SolarDesign(pv_kw, pv_cost, pv_kw*7.0, inv_kw, inverter_type,
                       inv_cost, batt_kwh, batt_cost, payback)

# ───────────────────────────────────────────────────────────────
# 5.  STREAMLIT UI
# ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Indian Solar Sizing Tool", layout="wide")
st.title("🔆 Indian Solar Sizing Tool (2025)")

# --- Sidebar Inputs ---
st.sidebar.header("Load Details")
appliance_qty = {}
for appl in APPLIANCE_P_RATED:
    appliance_qty[appl] = st.sidebar.number_input(
        f"{appl}", min_value=0, step=1, value=0
    )

st.sidebar.header("Site & System")
city = st.sidebar.selectbox("Select City", list(CITY_SOLAR_DATA.keys())[:-1], index=0)
outage = st.sidebar.slider("Weekly Grid Outage (hours)", 0, 168, 4, step=1)
inv_type = st.sidebar.radio("Inverter Type", ["grid", "hybrid", "offgrid"], index=1)
roof_height = st.sidebar.number_input("Roof Height (m)", value=10.0, min_value=0.0)

if st.sidebar.button("Calculate System"):
    # ----- 1. Daily kWh  -----
    total_kwh = sum(
        qty * APPLIANCE_P_RATED[appl] * DEFAULT_DUTY_HOURS[appl] / 1000
        for appl, qty in appliance_qty.items()
    )

    # ----- 2. City data -----
    city_data = CITY_SOLAR_DATA.get(city, CITY_SOLAR_DATA["default"])
    ghi = city_data["ghi"]
    grid_tariff = city_data["grid_tariff"]
    export_rate = city_data["export_rate"]

    # ----- 3. Design -----
    design = compute_design(total_kwh, ghi, outage, grid_tariff, inv_type)

    # ----- 4. Panel Recommendation -----
    panel_rec = recommend_panel_by_floor_height(roof_height)

    # ================= Results =================
    st.subheader("Results")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Daily Energy Need", f"{total_kwh:.1f} kWh/day")
        st.metric("PV Array Size", f"{design.pv_kw:.1f} kWp")
        st.metric("Battery Size", f"{design.battery_kwh:.1f} kWh")
        st.metric("Simple Pay‑back", f"{design.payback_years} years")

    with col2:
        st.metric("CapEx (≈)", f"₹{(design.pv_cost+design.inverter_cost+design.battery_cost)/1e5:.2f} L")
        st.metric("GHI", f"{ghi} kWh/m²·day")
        st.metric("Grid Tariff", f"₹{grid_tariff}/kWh")
        st.metric("Net‑Meter Export Rate", f"₹{export_rate}/kWh")

    st.markdown("### Cost Breakdown")
    cost_table = {
        "Component": ["PV Array", "Inverter", "Battery"],
        "Cost (₹ lakhs)": [design.pv_cost/1e5, design.inverter_cost/1e5, design.battery_cost/1e5],
    }
    st.table(cost_table)

    st.markdown("### Recommended Module (based on height)")
    st.write(f"**Type:** {panel_rec.panel_type}")
    st.write(f"**Brands:** {', '.join(panel_rec.brands)}")
    st.write(f"**Power class:** ~{panel_rec.wattage_w} W")
    st.write(f"**Size:** {panel_rec.size_mm} mm")

else:
    st.info("👈 Enter inputs in the sidebar and hit **Calculate System**")

# ───────────────────────────────────────────────────────────────
# 6.  FOOTER
# ───────────────────────────────────────────────────────────────
st.write("---")
st.caption("Built with Streamlit · July 2025")
