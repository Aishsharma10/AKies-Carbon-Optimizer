import streamlit as st
import plotly.graph_objects as go
from fpdf import FPDF
import searoute as sr
import folium
from streamlit_folium import st_folium
import airportsdata
import pycountry
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import datetime

# --- DATABASES & CACHING ---
@st.cache_data
def load_data():
    raw = airportsdata.load('IATA')
    by_country = {}
    for iata, info in raw.items():
        if info['iata'] and info['country']:
            try:
                c_name = pycountry.countries.get(alpha_2=info['country']).name
                if c_name not in by_country: by_country[c_name] = []
                by_country[c_name].append(f"{info['city']} ({iata})")
            except: continue
    return raw, by_country

AIRPORTS_RAW, AIRPORTS_BY_COUNTRY = load_data()

PORTS = {
    "India": {"Mumbai Port": [72.85, 18.95], "Mundra": [69.70, 22.75]},
    "Germany": {"Hamburg Port": [9.95, 53.53], "Bremerhaven": [8.58, 53.54]},
    "UAE": {"Jebel Ali": [55.02, 24.99]},
    "Singapore": {"Port of Singapore": [103.85, 1.29]},
    "USA": {"New York": [-74.00, 40.71], "Los Angeles": [-118.24, 33.74]}
}

# --- LOGIC ENGINES ---
def get_emissions(mode, weight, dist):
    factors = {"truck": 0.105, "air": 0.602, "sea": 0.012, "rail": 0.028}
    return (weight / 1000) * dist * factors.get(mode, 0.1)

def get_approx_cost(mode, weight, dist):
    rates = {"truck": 0.15, "air": 1.20, "sea": 0.05, "rail": 0.08}
    return (weight / 1000) * dist * rates.get(mode, 0.1)

# --- UI CONFIG ---
st.set_page_config(page_title="AKies Global Optimizer", layout="wide")
geolocator = Nominatim(user_agent="akies_final_build_v6")

if 'route' not in st.session_state: st.session_state.route = []
if 'current_loc' not in st.session_state: st.session_state.current_loc = None

# --- SIDEBAR: SEQUENTIAL LEG MANAGER ---
with st.sidebar:
    st.header("🏁 Leg Manager")
    if st.button("🔄 Reset Route"):
        st.session_state.route = []
        st.session_state.current_loc = None
        st.rerun()

    if st.session_state.current_loc is None:
        st.subheader("Set Origin")
        o_type = st.radio("Type", ["City", "Port", "Airport"])
        if o_type == "Port":
            c = st.selectbox("Country", list(PORTS.keys()), key="oc")
            p = st.selectbox("Port", list(PORTS[c].keys()), key="op")
            coords, name = PORTS[c][p], p
        elif o_type == "Airport":
            c = st.selectbox("Country", sorted(AIRPORTS_BY_COUNTRY.keys()), key="oac")
            a = st.selectbox("Airport", AIRPORTS_BY_COUNTRY[c], key="oaa")
            iata = a.split('(')[1].split(')')[0]
            coords, name = [AIRPORTS_RAW[iata]['lon'], AIRPORTS_RAW[iata]['lat']], a
        else:
            loc_str = st.text_input("Enter City/Address")
            loc = geolocator.geocode(loc_str) if loc_str else None
            coords, name = ([loc.longitude, loc.latitude], loc_str) if loc else (None, None)

        if st.button("Confirm Origin") and coords:
            st.session_state.current_loc = {"coords": coords, "name": name}
            st.rerun()
    else:
        st.write(f"📍 **From:** {st.session_state.current_loc['name']}")
        mode = st.selectbox("Mode", ["sea", "air", "truck", "rail"])
        weight = st.number_input("Weight (kg)", value=1000.0)
        d_type = st.radio("Destination", ["City", "Port", "Airport"])
        
        if d_type == "Port":
            c = st.selectbox("Dest Country", list(PORTS.keys()))
            p = st.selectbox("Dest Port", list(PORTS[c].keys()))
            d_coords, d_name = PORTS[c][p], p
        elif d_type == "Airport":
            c = st.selectbox("Dest Country", sorted(AIRPORTS_BY_COUNTRY.keys()))
            a = st.selectbox("Dest Airport", AIRPORTS_BY_COUNTRY[c])
            iata = a.split('(')[1].split(')')[0]
            d_coords, d_name = [AIRPORTS_RAW[iata]['lon'], AIRPORTS_RAW[iata]['lat']], a
        else:
            d_str = st.text_input("Enter Destination City")
            loc = geolocator.geocode(d_str) if d_str else None
            d_coords, d_name = ([loc.longitude, loc.latitude], d_str) if loc else (None, None)

        if st.button("➕ Add Leg") and d_coords:
            p1, p2 = st.session_state.current_loc['coords'], d_coords
            if mode == "sea":
                r = sr.searoute(p1, p2, units='km')
                dist, path = round(r.properties['length'], 2), [[c[1], c[0]] for c in r.geometry.coordinates]
            else:
                dist = round(geodesic((p1[1], p1[0]), (p2[1], p2[0])).km * (1.2 if mode != 'air' else 1.0), 2)
                path = [[p1[1], p1[0]], [p2[1], p2[0]]]

            st.session_state.route.append({
                "from": st.session_state.current_loc['name'], "to": d_name,
                "mode": mode, "weight": weight, "dist": dist, "path": path,
                "opt_mode": "sea" if dist > 500 else "rail"
            })
            st.session_state.current_loc = {"coords": d_coords, "name": d_name}
            st.rerun()

# --- 5. MAIN PAGE ---
st.title("🚛 AKies Carbon & Cost Optimizer")

if st.session_state.route:
    total_co2 = sum(get_emissions(s['mode'], s['weight'], s['dist']) for s in st.session_state.route)
    total_cost = sum(get_approx_cost(s['mode'], s['weight'], s['dist']) for s in st.session_state.route)
    total_opt_co2 = sum(get_emissions(s['opt_mode'], s['weight'], s['dist']) for s in st.session_state.route)
    total_opt_cost = sum(get_approx_cost(s['opt_mode'], s['weight'], s['dist']) for s in st.session_state.route)
    
    col_map, col_stats = st.columns([1.5, 1])

    with col_map:
        m = folium.Map(location=[20, 0], zoom_start=2)
        for s in st.session_state.route:
            color = {"sea": "blue", "air": "red", "truck": "green", "rail": "orange"}[s['mode']]
            folium.PolyLine(s['path'], color=color, weight=4).add_to(m)
        st_folium(m, width=700, height=400)

    with col_stats:
        max_v = max(total_co2 * 1.5, 500)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = total_co2,
            number = {'suffix': " kg CO2e"},
            gauge = {
                'axis': {'range': [0, max_v], 'tickwidth': 2, 'tickcolor': "black", 'dtick': max_v/4},
                'bar': {'color': "#1e293b"},
                'steps': [
                    {'range': [0, total_opt_co2], 'color': "#22c55e", 'name': "Optimal"},
                    {'range': [total_opt_co2, max_v], 'color': "#ef4444", 'name': "High"}
                ],
                'threshold': {'line': {'color': "black", 'width': 4}, 'value': total_co2}
            }
        ))
        st.plotly_chart(fig, use_container_width=True)
        st.metric("Total Actual Cost", f"${total_cost:,.2f}")
        st.success(f"Optimal Footprint Available: **{total_opt_co2:.2f} kg CO2e**")

    # --- 6. AUDIT PDF ---
    st.divider()
    if st.button("📄 Generate Audit Report"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(190, 10, "AKies Logistics Carbon & Cost Audit", ln=1, align='C')
        pdf.ln(10)
        
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(190, 10, f"Actual Footprint: {total_co2:.2f} kg CO2e", ln=1)
        pdf.cell(190, 10, f"Actual Project Cost: ${total_cost:,.2f}", ln=1)
        pdf.ln(10)

        # Main Table Header
        pdf.set_font("Helvetica", 'B', 9)
        pdf.cell(40, 10, "Route", 1)
        pdf.cell(25, 10, "Actual Mode", 1)
        pdf.cell(25, 10, "Optimal Mode", 1)
        pdf.cell(25, 10, "Dist (km)", 1)
        pdf.cell(35, 10, "Carbon (kg)", 1)
        pdf.cell(40, 10, "Cost (USD)", 1, 1)

        pdf.set_font("Helvetica", '', 8)
        for s in st.session_state.route:
            leg_em = get_emissions(s['mode'], s['weight'], s['dist'])
            leg_cost = get_approx_cost(s['mode'], s['weight'], s['dist'])
            pdf.cell(40, 10, f"{s['from'][:20]}", 1)
            pdf.cell(25, 10, s['mode'].upper(), 1)
            pdf.cell(25, 10, s['opt_mode'].upper(), 1)
            pdf.cell(25, 10, f"{s['dist']}", 1)
            pdf.cell(35, 10, f"{leg_em:.2f}", 1)
            pdf.cell(40, 10, f"${leg_cost:.2f}", 1, 1)

        # NEW SECTION: OPTIMIZED STRATEGY
        pdf.ln(15)
        pdf.set_font("Helvetica", 'B', 13)
        pdf.set_text_color(34, 197, 94) # Green text
        pdf.cell(190, 10, "AKies Smart Optimization Strategy (AI-Recommended)", ln=1)
        pdf.set_text_color(0, 0, 0) # Back to black
        
        pdf.set_font("Helvetica", '', 11)
        pdf.multi_cell(190, 8, f"By switching to the optimized modes suggested above, you can achieve a total carbon footprint of {total_opt_co2:.2f} kg CO2e and a total project cost of ${total_opt_cost:,.2f}.")
        
        pdf.ln(5)
        pdf.set_font("Helvetica", 'B', 11)
        savings_co2 = total_co2 - total_opt_co2
        savings_cost = total_cost - total_opt_cost
        pdf.cell(190, 10, f"Potential Carbon Savings: {savings_co2:.2f} kg CO2e", ln=1)
        pdf.cell(190, 10, f"Potential Financial Savings: ${savings_cost:,.2f}", ln=1)

        pdf_bytes = bytes(pdf.output()) 
        st.download_button("📥 Download Final Report", data=pdf_bytes, file_name="AKies_Audit.pdf", mime="application/pdf")

    # DELETE LIST
    st.subheader("Journey Breakdown")
    for i, s in enumerate(st.session_state.route):
        c1, c2 = st.columns([5, 1])
        c1.info(f"**Leg {i+1}**: {s['from']} -> {s['to']} ({s['mode'].upper()})")
        if c2.button("🗑️", key=f"del_{i}"):
            st.session_state.route.pop(i)
            st.rerun()
else:
    st.info("Set your Starting Point in the sidebar.")
