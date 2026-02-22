# 🚢 AKies Global Carbon & Cost Optimizer

**A professional logistics auditing tool designed for modern, green supply chains.**

Built by a Mechanical Engineer transitioning into AI Automation, this tool allows businesses to calculate the environmental and financial impact of their global shipments.

## 🌟 Key Features
- **Multi-Modal Routing:** Supports Sea, Air, Rail, and Truck transport.
- **Sequential Logistics:** "Chain" legs together (e.g., Mumbai Port -> Hamburg Port -> Berlin Warehouse).
- **Maritime Intelligence:** Uses actual global shipping lanes to avoid landmasses in sea route calculations.
- **Carbon Audit Reports:** Generate a professional PDF breakdown of carbon emissions and approximate costs per leg.
- **AI Optimization:** Automatically suggests the greenest/cheapest transport mode for every journey segment.



## 🛠️ Tech Stack
- **Frontend:** Streamlit
- **Visualization:** Plotly (Gauges) & Folium (Interactive Maps)
- **Geospatial Data:** Geopy, Searoute, Airportsdata
- **Reporting:** FPDF2

## 🚀 How to Use
1. **Set Origin:** Choose a city, port, or airport to start your journey.
2. **Add Legs:** Select your next destination and transport mode. The tool automatically detects your previous location.
3. **Analyze:** Check the Carbon Gauge to see if your route is "Optimal" (Green) or "High Emission" (Red).
4. **Export:** Download the PDF Audit to see a detailed cost and carbon breakdown.

## 📈 Optimization Logic
The tool compares your choices against industry-standard "Green Paths":
* **Long-Haul (>500km):** Recommends Sea transport for lowest emissions.
* **Regional/Short-Haul:** Recommends Rail over Trucking for a 70% reduction in carbon footprint.

---
*Developed by [Your Name] as part of the AKies Automation Project.*
