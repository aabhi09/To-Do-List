import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import time
import folium
from streamlit_folium import folium_static
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import json
import os
import hashlib

# ================= CONFIG =================
st.set_page_config(
    page_title="Blue Horizon",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        .stApp {
            background: radial-gradient(circle at top left, #1c3b5a 0%, #001020 35%, #000814 100%) !important;
            color: #e0f0ff !important;
            font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        }
        section[data-testid="stSidebar"] {
            background: #020817 !important;
            border-right: 1px solid rgba(135, 206, 250, 0.25);
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .main-title {
            font-size: 2.4rem;
            font-weight: 700;
            background: linear-gradient(90deg, #38bdf8, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 0.04em;
        }
        .sub-title {
            color: #9ca3af;
            font-size: 0.95rem;
        }
        .glass-card {
            border-radius: 16px;
            padding: 1.1rem 1.2rem;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), rgba(15, 23, 42, 0.94));
            box-shadow: 0 18px 40px rgba(15,23,42,0.9);
        }
        .glass-soft {
            border-radius: 16px;
            padding: 1rem 1.1rem;
            border: 1px solid rgba(148, 163, 184, 0.3);
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.96), rgba(15, 23, 42, 0.90));
            box-shadow: 0 16px 30px rgba(15,23,42,0.85);
        }
        .stMetric {
            background: radial-gradient(circle at top left, rgba(59,130,246,0.20), rgba(15,23,42,0.95)) !important;
            border: 1px solid rgba(59,130,246,0.45);
            border-radius: 15px;
            padding: 12px 15px;
        }
        .stMetricLabel {
            color: #93c5fd !important;
            font-size: 0.9rem;
            font-weight: 500;
        }
        .stMetricValue {
            font-size: 1.7rem !important;
            font-weight: 700 !important;
            color: #e0f2fe !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.25rem;
            background-color: rgba(15,23,42,0.9);
            padding: 0.25rem;
            border-radius: 999px;
            border: 1px solid rgba(148,163,184,0.35);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            padding: 0.4rem 0.9rem;
            color: #9ca3af;
            font-size: 0.9rem;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: radial-gradient(circle at top left, #38bdf8, #6366f1);
            color: #0f172a;
            font-weight: 600;
        }
        .city-title {
            font-size: 1.4rem;
            font-weight: 600;
            color: #e5e7eb;
        }
        .update-caption {
            color: #9ca3af;
            font-size: 0.75rem;
        }
        .search-input > div > input {
            border-radius: 999px !important;
            border: 1px solid rgba(148,163,184,0.5) !important;
            background: rgba(15,23,42,0.85) !important;
            color: #e5e7eb !important;
        }
        .footer {
            text-align: right;
            font-size: 0.75rem;
            color: #6b7280;
            margin-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# ================= USER AUTH STORAGE =================
USER_FILE = "users.json"

def load_users():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "current_city" not in st.session_state:
    st.session_state.current_city = "Christchurch"
if "units" not in st.session_state:
    st.session_state.units = {"temp": "celsius", "wind": "kmh", "precip": "mm"}

users = load_users()

# ================= HELPERS =================
WMO_CODES = {
    0: "Clear sky ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅", 3: "Overcast ☁️",
    45: "Fog 🌫️", 48: "Depositing rime fog 🌫️",
    51: "Light drizzle 🌦️", 53: "Drizzle 🌦️", 55: "Dense drizzle 🌦️",
    61: "Slight rain 🌧️", 63: "Moderate rain 🌧️", 65: "Heavy rain 🌧️",
    71: "Slight snow ❄️", 73: "Snow ❄️", 75: "Heavy snow ❄️",
    80: "Rain showers 🌦️", 81: "Rain showers 🌦️", 82: "Violent rain showers 🌧️",
    95: "Thunderstorm ⚡", 96: "Thunderstorm with hail ⛈️", 99: "Severe thunderstorm ⛈️"
}

def get_condition(code: int):
    return WMO_CODES.get(code, f"Unknown ({code})")

@st.cache_data(ttl=1800)
def get_coordinates(city_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": city_name, "format": "json", "limit": 1}
    headers = {"User-Agent": "BlueHorizonApp/2.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=6)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", city_name)
        return None, None, None
    except Exception:
        return None, None, None

@st.cache_data(ttl=600)
def fetch_weather(lat, lon, units):
    base = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,precipitation_probability,pressure_msl",
        "hourly": "temperature_2m,weather_code,precipitation_probability,relative_humidity_2m,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,uv_index_max,precipitation_sum,sunrise,sunset,wind_speed_10m_max",
        "timezone": "auto",
        "temperature_unit": units['temp'],
        "wind_speed_unit": units['wind'],
        "precipitation_unit": units['precip'],
        "forecast_days": 7,
    }
    url = base + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                return None
            return data
        except Exception:
            if attempt < 2:
                time.sleep(1.5)
    return None

@st.cache_data(ttl=900)
def fetch_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "pm10,pm2_5,carbon_monoxide,ozone,nitrogen_dioxide,sulphur_dioxide,us_aqi",
        "timezone": "auto"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=900)
def fetch_historical(lat, lon, start_date, end_date, units):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start_date, "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
        "temperature_unit": units['temp'],
        "precipitation_unit": units['precip']
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def build_pdf_report(city, weather):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title = styles["Title"]
    normal = styles["BodyText"]
    title.textColor = "#003366"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    story.append(Paragraph("Blue Horizon Weather Report", title))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Location: {city}", normal))
    story.append(Paragraph(f"Generated: {now}", normal))
    story.append(Spacer(1, 18))

    c = weather["current"]
    u = weather["current_units"]
    story.append(Paragraph("<b>Current Conditions</b>", normal))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Temperature: {c['temperature_2m']} {u['temperature_2m']}", normal))
    story.append(Paragraph(f"Feels like: {c.get('apparent_temperature', '—')} {u['temperature_2m']}", normal))
    story.append(Paragraph(f"Humidity: {c['relative_humidity_2m']} %", normal))
    story.append(Paragraph(f"Wind: {c['wind_speed_10m']} {u['wind_speed_10m']}", normal))
    story.append(Paragraph(f"Pressure: {c.get('pressure_msl', '—')} hPa", normal))
    story.append(Paragraph(f"Condition: {get_condition(c.get('weather_code', 0))}", normal))
    story.append(Spacer(1, 18))

    d = weather["daily"]
    dates = d["time"][:5]
    story.append(Paragraph("<b>5‑Day Outlook</b>", normal))
    story.append(Spacer(1, 6))
    for i, day in enumerate(dates):
        story.append(Paragraph(
            f"{day}: "
            f"{d['temperature_2m_min'][i]}–{d['temperature_2m_max'][i]} {weather['daily_units']['temperature_2m_max']}, "
            f"Precip: {d['precipitation_sum'][i]} {weather['daily_units']['precipitation_sum']} "
            f"({get_condition(d['weather_code'][i])})",
            normal
        ))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Powered by Blue Horizon • Data source: Open‑Meteo", normal))

    doc.build(story)
    buffer.seek(0)
    return buffer
# ================= AUTH PAGE =================
if not st.session_state.logged_in:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">🌊 Blue Horizon</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Hyper‑polished, personal weather intelligence – anywhere on Earth.</div>',
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

    tab1, tab2 = st.tabs(["🔑 Sign In", "📝 Sign Up"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            if submitted:
                if username in users and users[username]["password"] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.current_city = users[username].get("last_city", "Christchurch")
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tab2:
        with st.form("signup_form"):
            new_user = st.text_input("Choose Username")
            new_pass = st.text_input("Choose Password", type="password")
            submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
            if submitted:
                if new_user in users:
                    st.error("Username already exists.")
                elif len(new_pass) < 4:
                    st.error("Password must be at least 4 characters.")
                else:
                    users[new_user] = {"password": hash_password(new_pass), "last_city": "Christchurch"}
                    save_users(users)
                    st.session_state.logged_in = True
                    st.session_state.username = new_user
                    st.session_state.current_city = "Christchurch"
                    st.success(f"Account created! Welcome, {new_user}!")
                    st.rerun()

else:
    # ================= MAIN APP TOP =================
    top_left, top_right = st.columns([3, 2])
    with top_left:
        st.markdown('<div class="main-title">🌊 Blue Horizon</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="sub-title">Hi {st.session_state.username}, here’s your live atmospheric dashboard.</div>',
            unsafe_allow_html=True
        )
    with top_right:
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.rerun()

    st.write("")

    # Search + Globe
    col_search, col_globe = st.columns([3, 2])

    with col_search:
        st.markdown('<div class="glass-soft">', unsafe_allow_html=True)
        city_input = st.text_input(
            "🔍 Where are we watching the sky today?",
            value=st.session_state.current_city,
            placeholder="e.g. Bengaluru, Tokyo, New York, Paris, Mumbai",
            key="city_input",
            help="Type a city name and press Enter"
        )
        if city_input.strip() and city_input.strip() != st.session_state.current_city:
            st.session_state.current_city = city_input.strip()
            if st.session_state.username in users:
                users[st.session_state.username]["last_city"] = st.session_state.current_city
                save_users(users)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    def create_3d_globe():
        lons = [77.59, 172.62, -74.01, 139.77, -0.13, 151.21]
        lats = [12.97, -43.53, 40.71, 35.68, 51.51, -33.87]
        labels = ["Bengaluru", "Christchurch", "New York", "Tokyo", "London", "Sydney"]

        fig = go.Figure()
        fig.add_trace(go.Scattergeo(
            lon=lons,
            lat=lats,
            text=labels,
            mode='markers+text',
            textposition="bottom center",
            marker=dict(size=10, color='#38bdf8', line=dict(width=1, color='#0f172a')),
            hovertemplate="%{text}<extra></extra>"
        ))

        fig.update_geos(
            projection_type="orthographic",
            showland=True,
            landcolor="#082f49",
            showocean=True,
            oceancolor="#020617",
            showcountries=True,
            countrycolor="#60a5fa",
            coastlinecolor="#bae6fd",
            showlakes=True,
            lakecolor="#0369a1",
            bgcolor="rgba(0,0,0,0)"
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=310,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False
        )
        return fig

    with col_globe:
        st.markdown('<div class="glass-soft">', unsafe_allow_html=True)
        st.markdown("**🌍 Live Globe**  &nbsp; *(Drag to rotate • Scroll to zoom)*")
        st.plotly_chart(create_3d_globe(), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # Sidebar units
    st.sidebar.markdown("### 🌡️ Units")
    st.session_state.units["temp"] = st.sidebar.radio("Temperature", ["celsius", "fahrenheit"], index=0)
    st.session_state.units["wind"] = st.sidebar.radio("Wind Speed", ["kmh", "mph", "ms", "kn"], index=0)
    st.session_state.units["precip"] = st.sidebar.radio("Precipitation", ["mm", "inch"], index=0)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Session**")
    st.sidebar.write(f"User: **{st.session_state.username}**")
    st.sidebar.write(f"City: **{st.session_state.current_city}**")

    st.markdown("---")
    # Geocoding + weather fetch
    lat, lon, display_name = get_coordinates(st.session_state.current_city)

    if lat is None or lon is None:
        st.error(f"Could not find city: {st.session_state.current_city}")
        st.stop()

    st.markdown(
        f'<div class="city-title">🌤️ Weather for {display_name or st.session_state.current_city}</div>',
        unsafe_allow_html=True
    )

    with st.spinner("Pulling fresh atmospheric data…"):
        weather = fetch_weather(lat, lon, st.session_state.units)

    if not weather:
        st.error("Failed to fetch weather data. Please try again in a moment.")
        st.stop()

    tabs = st.tabs(["Current", "Hourly", "Daily", "Air Quality", "Map", "Historical", "Export PDF"])

    # ---------- CURRENT ----------
    with tabs[0]:
        c = weather["current"]
        u = weather["current_units"]

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric(
            "Temperature",
            f"{c['temperature_2m']} {u['temperature_2m']}",
            f"Feels {c.get('apparent_temperature', '—')} {u['temperature_2m']}"
        )
        col_b.metric("Humidity", f"{c['relative_humidity_2m']} %")
        col_c.metric("Wind", f"{c['wind_speed_10m']} {u['wind_speed_10m']}")
        col_d.metric(
            "Rain Probability",
            f"{c.get('precipitation_probability', '—')} %"
        )

        col_e, col_f = st.columns(2)
        with col_e:
            st.metric("Pressure", f"{c.get('pressure_msl', '—')} hPa")
        with col_f:
            st.metric("Condition", get_condition(c.get("weather_code", 0)))
    
        # ========== HOURLY ==========
    with tabs[1]:
        h = weather["hourly"]

        # Build DataFrame for easier handling
        hourly_df = pd.DataFrame({
            "time": pd.to_datetime(h["time"]),
            "temperature": h["temperature_2m"],
            "precip_prob": h["precipitation_probability"],
            "humidity": h["relative_humidity_2m"],
            "wind": h["wind_speed_10m"],
            "code": h["weather_code"],
        })

        # Take next 24 hours from current time
        now_ts = pd.to_datetime(weather["current"]["time"])
        mask_24h = (hourly_df["time"] >= now_ts) & (hourly_df["time"] <= now_ts + pd.Timedelta(hours=24))
        df_24 = hourly_df.loc[mask_24h]

        col_h1, col_h2 = st.columns(2)

        # Temperature line chart
        with col_h1:
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=df_24["time"],
                y=df_24["temperature"],
                mode="lines+markers",
                name="Temperature",
                line=dict(color="#38bdf8")
            ))
            fig_temp.update_layout(
                title="Next 24 Hours – Temperature",
                xaxis_title="Time",
                yaxis_title=f"Temp ({weather['hourly_units']['temperature_2m']})",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.9)",
                font=dict(color="#e5e7eb"),
                hovermode="x unified",
                margin=dict(l=40, r=20, t=40, b=40)
            )
            st.plotly_chart(fig_temp, use_container_width=True)

        # Precipitation probability bar chart
        with col_h2:
            fig_prec = go.Figure()
            fig_prec.add_trace(go.Bar(
                x=df_24["time"],
                y=df_24["precip_prob"],
                name="Precipitation probability",
                marker_color="#22c55e"
            ))
            fig_prec.update_layout(
                title="Next 24 Hours – Rain Probability",
                xaxis_title="Time",
                yaxis_title="Probability (%)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.9)",
                font=dict(color="#e5e7eb"),
                hovermode="x unified",
                margin=dict(l=40, r=20, t=40, b=40)
            )
            st.plotly_chart(fig_prec, use_container_width=True)

        # Table view
        st.dataframe(
            df_24[["time", "temperature", "precip_prob", "humidity", "wind"]],
            use_container_width=True,
            hide_index=True
        )
        
        # ========== DAILY ==========
    with tabs[2]:
        d = weather["daily"]

        # Build DataFrame for 7‑day summary
        df_daily = pd.DataFrame({
            "date": pd.to_datetime(d["time"]),
            "t_min": d["temperature_2m_min"],
            "t_max": d["temperature_2m_max"],
            "precip": d["precipitation_sum"],
            "uv_max": d["uv_index_max"],
            "wind_max": d["wind_speed_10m_max"],
            "code": d["weather_code"],
        })

        col_d1, col_d2 = st.columns([2, 1])

        # Temperature overview chart
        with col_d1:
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Bar(
                x=df_daily["date"],
                y=df_daily["t_max"],
                name="Max Temp",
                marker_color="#f97316",
            ))
            fig_daily.add_trace(go.Bar(
                x=df_daily["date"],
                y=df_daily["t_min"],
                name="Min Temp",
                marker_color="#38bdf8",
            ))
            fig_daily.update_layout(
                barmode="group",
                title="7‑Day Temperature Overview",
                xaxis_title="Date",
                yaxis_title=f"Temp ({weather['daily_units']['temperature_2m_max']})",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.9)",
                font=dict(color="#e5e7eb"),
                margin=dict(l=40, r=20, t=40, b=40),
            )
            st.plotly_chart(fig_daily, use_container_width=True)

        # Textual daily highlights
        with col_d2:
            st.markdown("**Daily Highlights**")
            for _, row in df_daily.iterrows():
                st.write(
                    f"{row['date'].date()} – "
                    f"{row['t_min']}–{row['t_max']} {weather['daily_units']['temperature_2m_max']}, "
                    f"Precip: {row['precip']} {weather['daily_units']['precipitation_sum']}, "
                    f"UV max: {row['uv_max']}, "
                    f"{get_condition(int(row['code']))}"
                )
                
        # ========== AIR QUALITY ==========
    with tabs[3]:
        st.subheader("🌫️ Air Quality (Open‑Meteo)")

        with st.spinner("Fetching air quality…"):
            aq = fetch_air_quality(lat, lon)

        if not aq or "hourly" not in aq:
            st.warning("Air quality data is not available for this location.")
        else:
            ah = aq["hourly"]
            df_aq = pd.DataFrame({
                "time": pd.to_datetime(ah["time"]),
                "us_aqi": ah["us_aqi"],
                "pm2_5": ah["pm2_5"],
                "pm10": ah["pm10"],
                "o3": ah["ozone"],
                "no2": ah["nitrogen_dioxide"],
                "so2": ah["sulphur_dioxide"],
                "co": ah["carbon_monoxide"],
            })

            latest = df_aq.iloc[-1]

            col_aq1, col_aq2, col_aq3 = st.columns(3)
            col_aq1.metric("US AQI", f"{latest['us_aqi']:.0f}")
            col_aq2.metric("PM₂.₅ (µg/m³)", f"{latest['pm2_5']:.1f}")
            col_aq3.metric("PM₁₀ (µg/m³)", f"{latest['pm10']:.1f}")

            fig_aqi = go.Figure()
            fig_aqi.add_trace(go.Scatter(
                x=df_aq["time"],
                y=df_aq["us_aqi"],
                mode="lines",
                line=dict(color="#a855f7"),
                name="US AQI"
            ))
            fig_aqi.update_layout(
                title="US AQI – Last 48 Hours",
                xaxis_title="Time",
                yaxis_title="US AQI",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.9)",
                font=dict(color="#e5e7eb"),
                hovermode="x unified",
                margin=dict(l=40, r=20, t=40, b=40),
            )
            st.plotly_chart(fig_aqi, use_container_width=True)
            
        # ========== MAP ==========
    with tabs[4]:
        st.subheader("🗺️ Location Map")
        st.write("Drag, zoom and explore the surroundings.")

        # Create a dark-themed map centered on the selected city
        m = folium.Map(location=[lat, lon], zoom_start=10, tiles="CartoDB dark_matter")

        # Marker for the current location
        folium.Marker(
            [lat, lon],
            popup=display_name or st.session_state.current_city,
            tooltip="Current location",
            icon=folium.Icon(color="lightblue", icon="cloud")
        ).add_to(m)

        # Render the map in Streamlit
        folium_static(m, width=900, height=500)

    
    # ---------- HISTORICAL ----------
    with tabs[5]:
        st.subheader("📚 Historical Weather")

        col_hist_1, col_hist_2 = st.columns(2)
        with col_hist_1:
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            start = st.date_input("Start date", start_date, max_value=end_date)
        with col_hist_2:
            end = st.date_input("End date", end_date, min_value=start)

        if st.button("Load Historical Data"):
            with st.spinner("Fetching historical archive…"):
                hist = fetch_historical(lat, lon, start.isoformat(), end.isoformat(), st.session_state.units)

            if not hist or "daily" not in hist:
                st.error("No historical data available for this period.")
            else:
                d = hist["daily"]
                df_hist = pd.DataFrame({
                    "date": pd.to_datetime(d["time"]),
                    "t_min": d["temperature_2m_min"],
                    "t_max": d["temperature_2m_max"],
                    "precip": d["precipitation_sum"],
                })

                fig_hist = go.Figure()
                fig_hist.add_trace(go.Scatter(
                    x=df_hist["date"], y=df_hist["t_min"],
                    name="Min Temp",
                    line=dict(color="#38bdf8")
                ))
                fig_hist.add_trace(go.Scatter(
                    x=df_hist["date"], y=df_hist["t_max"],
                    name="Max Temp",
                    line=dict(color="#f97316")
                ))
                fig_hist.update_layout(
                    title="Daily Min/Max Temperature",
                    xaxis_title="Date",
                    yaxis_title=f"Temperature ({hist['daily_units']['temperature_2m_max']})",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.9)",
                    font=dict(color="#e5e7eb"),
                    hovermode="x unified",
                    margin=dict(l=40, r=20, t=40, b=40)
                )
                st.plotly_chart(fig_hist, use_container_width=True)

                fig_prec = go.Figure()
                fig_prec.add_trace(go.Bar(
                    x=df_hist["date"], y=df_hist["precip"],
                    name="Precipitation",
                    marker_color="#22c55e"
                ))
                fig_prec.update_layout(
                    title="Daily Precipitation",
                    xaxis_title="Date",
                    yaxis_title=f"Precipitation ({hist['daily_units']['precipitation_sum']})",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.9)",
                    font=dict(color="#e5e7eb"),
                    margin=dict(l=40, r=20, t=40, b=40)
                )
                st.plotly_chart(fig_prec, use_container_width=True)

    # ---------- EXPORT PDF ----------
    with tabs[6]:
        st.subheader("📄 Export Weather Report")
        st.write("Generate a polished PDF summary of the current conditions and 5‑day outlook.")

        if st.button("Generate PDF Report", type="primary"):
            with st.spinner("Rendering PDF…"):
                pdf_buffer = build_pdf_report(display_name or st.session_state.current_city, weather)

            st.download_button(
                label="⬇️ Download Report",
                data=pdf_buffer,
                file_name=f"BlueHorizon_{st.session_state.current_city.replace(' ', '_')}.pdf",
                mime="application/pdf",
            )

    # ---------- FOOTER ----------
    st.markdown(
        '<div class="footer">Last update: '
        f'{datetime.now().strftime("%Y-%m-%d %H:%M")} • Built by Aabhinav Sarkar • Data by Open‑Meteo</div>',
        unsafe_allow_html=True
    )
