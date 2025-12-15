import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ============================================================================
# 🔧 CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Air Tracker - Flight Analytics",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 🗄️ DATABASE CONNECTION
# ============================================================================

@st.cache_resource
def get_connection():
    """Create database connection"""
    return sqlite3.connect('air_tracker.db', check_same_thread=False)

def get_data(query, params=None):
    """Execute SQL query and return DataFrame"""
    conn = get_connection()
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    return df

# ============================================================================
# 🎨 CUSTOM CSS STYLING
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1E88E5;
        padding: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #424242;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1E88E5;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 📊 SIDEBAR NAVIGATION
# ============================================================================

st.sidebar.title("🛩️ Navigation")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Go to:",
    ["🏠 Home Dashboard", 
     "✈️ Flight Explorer", 
     "🛩️ Aircraft Analytics",
     "🏢 Airport Location",
     "⏰ Delay Insights",
     "📊 SQL Query Results",
     "👨‍💻 About Project"]
)

st.sidebar.markdown("---")
st.sidebar.info("""
**Air Tracker v1.0**  
GUVI Project  
Aviation Data Analytics  
""")

# ============================================================================
# 🏠 PAGE 1: HOME DASHBOARD
# ============================================================================

if page == "🏠 Home Dashboard":
    st.markdown('<div class="main-header">✈️ AIR TRACKER: Flight Analytics</div>', 
                unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time Aviation Data Insights</div>', 
                unsafe_allow_html=True)
    
    # Summary Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    total_flights = get_data("SELECT COUNT(*) as count FROM flights")['count'][0]
    total_aircraft = get_data("SELECT COUNT(*) as count FROM aircraft")['count'][0]
    total_airports = get_data("SELECT COUNT(*) as count FROM airports")['count'][0]
    total_airlines = get_data("SELECT COUNT(DISTINCT airline_name) as count FROM flights")['count'][0]
    
    col1.metric("✈️ Total Flights", f"{total_flights:,}")
    col2.metric("🛩️ Aircraft", f"{total_aircraft:,}")
    col3.metric("🏢 Airports", f"{total_airports}")
    col4.metric("🏢 Airlines", f"{total_airlines}")
    
    st.markdown("---")
    
    # Key Insights in 2 columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Flight Status Distribution")
        status_data = get_data("""
            SELECT status, COUNT(*) as count 
            FROM flights 
            GROUP BY status 
            ORDER BY count DESC
        """)
        fig = px.pie(status_data, values='count', names='status', 
                     title='Flight Status Breakdown',
                     color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🏢 Top 5 Airlines by Flight Count")
        airline_data = get_data("""
            SELECT airline_name, COUNT(*) as flight_count 
            FROM flights 
            GROUP BY airline_name 
            ORDER BY flight_count DESC 
            LIMIT 5
        """)
        fig = px.bar(airline_data, x='airline_name', y='flight_count',
                     title='Busiest Airlines',
                     labels={'airline_name': 'Airline', 'flight_count': 'Flights'},
                     color='flight_count',
                     color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)
        
# ============================================================================
# ✈️ PAGE 2: FLIGHT EXPLORER
# ============================================================================

elif page == "✈️ Flight Explorer":
    st.title("✈️ Flight Explorer")
    st.markdown("Search and filter flights with detailed information")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        airlines = get_data(
            "SELECT DISTINCT airline_name FROM flights ORDER BY airline_name"
        )["airline_name"].tolist()
        selected_airline = st.selectbox("Select Airline", ["All"] + airlines)

    with col2:
        statuses = get_data(
            "SELECT DISTINCT status FROM flights ORDER BY status"
        )["status"].tolist()
        selected_status = st.selectbox("Select Status", ["All"] + statuses)

    with col3:
        airports = get_data(
            "SELECT DISTINCT iata_code FROM airports ORDER BY iata_code"
        )["iata_code"].tolist()
        selected_origin = st.selectbox("Origin Airport", ["All"] + airports)

    # Build query based on filters (no delay / actual_dep)
    query = """
        SELECT
            f.flight_number,
            f.airline_name,
            origin.iata_code AS origin,
            origin.city      AS origin_city,
            f.scheduled_dep,
            f.status
        FROM flights f
        JOIN airports origin ON f.origin_icao = origin.icao_code
        WHERE 1 = 1
    """

    params = []
    if selected_airline != "All":
        query += " AND f.airline_name = ?"
        params.append(selected_airline)
    if selected_status != "All":
        query += " AND f.status = ?"
        params.append(selected_status)
    if selected_origin != "All":
        query += " AND origin.iata_code = ?"
        params.append(selected_origin)

    query += " ORDER BY f.scheduled_dep DESC LIMIT 100"

    flights_df = get_data(query, tuple(params) if params else None)

    st.subheader(f"📋 Showing {len(flights_df)} flights")
    st.dataframe(flights_df, use_container_width=True, height=400)

    # Flight / Cancellation Statistics
    if len(flights_df) > 0:
        col1, col2, col3 = st.columns(3)

        total_flights = len(flights_df)
        canceled_count = (flights_df["status"] == "Canceled").sum()
        canceled_pct = (canceled_count / total_flights) * 100 if total_flights > 0 else 0

        col1.metric("Total Flights", total_flights)
        col2.metric("Canceled Flights", canceled_count)
        col3.metric("Canceled %", f"{canceled_pct:.1f}%")


# ============================================================================
# 🛩️ PAGE 3: AIRCRAFT ANALYTICS
# ============================================================================

elif page == "🛩️ Aircraft Analytics":
    st.title("🛩️ Aircraft Analytics")
    
    # Top Aircraft Models
    st.subheader("📊 Top 10 Aircraft Models by Flight Count")
    aircraft_stats = get_data("""
        SELECT 
            a.aircraft_model,
            a.manufacturer,
            COUNT(f.flight_id) as flight_count,
            COUNT(DISTINCT f.airline_name) as airlines_using
        FROM aircraft a
        JOIN flights f ON a.aircraft_reg = f.aircraft_reg
        GROUP BY a.aircraft_model, a.manufacturer
        ORDER BY flight_count DESC
        LIMIT 10
    """)
    
    fig = px.bar(aircraft_stats, x='aircraft_model', y='flight_count',
                 color='manufacturer',
                 title='Most Used Aircraft Models',
                 labels={'aircraft_model': 'Aircraft Model', 'flight_count': 'Number of Flights'},
                 text='flight_count')
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Table
    st.subheader("📋 Aircraft Fleet Details")
    st.dataframe(aircraft_stats, use_container_width=True)
    
    # Manufacturer Distribution
    st.subheader("🏭 Manufacturer Distribution")
    mfr_data = get_data("""
        SELECT manufacturer, COUNT(*) as aircraft_count
        FROM aircraft
        GROUP BY manufacturer
        ORDER BY aircraft_count DESC
    """)
    
    fig = px.pie(mfr_data, values='aircraft_count', names='manufacturer',
                 title='Aircraft by Manufacturer')
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# 🏢 PAGE 4: AIRPORT LOCATION
# ============================================================================

elif page == "🏢 Airport Location":
    st.title("🏢 Airport Location")
    
    # Airport selector
    airports = get_data("SELECT iata_code, name, city FROM airports ORDER BY name")
    selected_airport = st.selectbox(
        "Select Airport",
        airports['iata_code'].tolist(),
        format_func=lambda x: f"{x} - {airports[airports['iata_code']==x]['name'].values[0]}"
    )
    
    # Airport Details
    airport_info = get_data(
        "SELECT * FROM airports WHERE iata_code = ?",
        (selected_airport,)
    )
    
    if not airport_info.empty:
        st.subheader(f"📍 {airport_info['name'].values[0]}")
        col1, col2, col3 = st.columns(3)
        col1.metric("City", airport_info['city'].values[0])
        col2.metric("Country", airport_info['country'].values[0])
        col3.metric("Timezone", airport_info['timezone'].values[0])
        
        # Map
        st.subheader("🗺️ Location")
        map_data = pd.DataFrame({
            'lat': [airport_info['latitude'].values[0]],
            'lon': [airport_info['longitude'].values[0]]
        })
        st.map(map_data, zoom=10)
 
# ============================================================================
# ⏰ PAGE 5: DELAY INSIGHTS
# ============================================================================

elif page == "⏰ Delay Insights":
    st.title("⏰ Delay Insights")
    
    # Delay Statistics
    st.subheader("📊 Delay Overview")
    
    delay_stats = get_data("""
        SELECT 
            COUNT(*) as total_flights,
            SUM(CASE WHEN delay_dep > 0 THEN 1 ELSE 0 END) as delayed_flights,
            ROUND(AVG(CASE WHEN delay_dep > 0 THEN delay_dep END), 2) as avg_delay,
            MAX(delay_dep) as max_delay
        FROM flights
    """)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Flights", f"{delay_stats['total_flights'].values[0]:,}")
    col2.metric("Delayed Flights", f"{delay_stats['delayed_flights'].values[0]:,}")
    col3.metric("Avg Delay (min)", f"{delay_stats['avg_delay'].values[0]:.1f}")
    col4.metric("Max Delay (min)", f"{delay_stats['max_delay'].values[0]:.0f}")
    
    # Delay by Airport
    st.subheader("🏢 Delays by Airport")
    airport_delays = get_data("""
        SELECT 
            ap.name AS airport_name,
            ap.iata_code,
            COUNT(f.flight_id) as total_flights,
            SUM(CASE WHEN f.delay_dep > 0 THEN 1 ELSE 0 END) as delayed_flights,
            ROUND(AVG(CASE WHEN f.delay_dep > 0 THEN f.delay_dep END), 2) as avg_delay,
            ROUND((SUM(CASE WHEN f.delay_dep > 0 THEN 1 ELSE 0 END) * 100.0) / COUNT(f.flight_id), 2) as delay_percentage
        FROM airports ap
        JOIN flights f ON ap.icao_code = f.origin_icao
        GROUP BY ap.name, ap.iata_code
        HAVING total_flights > 10
        ORDER BY delay_percentage DESC
    """)
    
    fig = px.bar(airport_delays, x='iata_code', y='delay_percentage',
                 title='Delay Percentage by Airport',
                 labels={'iata_code': 'Airport', 'delay_percentage': 'Delay %'},
                 hover_data=['airport_name', 'total_flights', 'avg_delay'])
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Table
    st.subheader("📋 Detailed Delay Statistics")
    st.dataframe(airport_delays, use_container_width=True)

# ============================================================================
# 📊 PAGE 6: SQL QUERY RESULTS
# ============================================================================

elif page == "📊 SQL Query Results":
    st.title("📊 SQL Query Results")
    st.markdown("View results of all 11 GUVI required queries")
    
    query_options = {
                "1) Flights per Aircraft Model": """
            SELECT 
                a.aircraft_model,
                COUNT(f.flight_id) AS total_flights
            FROM flights f
            JOIN aircraft a ON f.aircraft_reg = a.aircraft_reg
            GROUP BY a.aircraft_model
            ORDER BY total_flights DESC
        """,
        "2) Aircraft with > 5 Flights": """
            SELECT 
                a.aircraft_reg   AS registration,
                a.aircraft_model AS model,
                a.manufacturer,
                COUNT(f.flight_id) AS flight_count
            FROM aircraft a
            JOIN flights f ON a.aircraft_reg = f.aircraft_reg
            GROUP BY a.aircraft_reg, a.aircraft_model, a.manufacturer
            HAVING COUNT(f.flight_id) > 5
            ORDER BY flight_count DESC
        """,
        "3) Airports with > 5 Outbound Flights": """
            SELECT 
                ap.name AS airport_name,
                ap.city,
                ap.country,
                COUNT(f.flight_id) AS outbound_flights
            FROM airports ap
            JOIN flights f ON ap.icao_code = f.origin_icao
            GROUP BY ap.icao_code, ap.name, ap.city, ap.country
            HAVING COUNT(f.flight_id) > 5
            ORDER BY outbound_flights DESC
        """,
        "4) Top 3 Destination Airports": """
            SELECT 
                ap.name AS airport_name,
                ap.city,
                ap.country,
                COUNT(f.flight_id) AS arriving_flights
            FROM airports ap
            JOIN flights f ON ap.icao_code = f.dest_icao
            GROUP BY ap.icao_code, ap.name, ap.city, ap.country
            ORDER BY arriving_flights DESC
            LIMIT 3
        """,
        "5) Domestic vs International (Per Flight)": """
            SELECT 
                f.flight_number,
                origin.iata_code AS origin,
                origin.country   AS origin_country,
                dest.iata_code   AS destination,
                dest.country     AS dest_country,
                CASE 
                    WHEN origin.country = dest.country THEN 'Domestic'
                    ELSE 'International'
                END AS flight_type
            FROM flights f
            LEFT JOIN airports origin ON f.origin_icao = origin.icao_code
            LEFT JOIN airports dest   ON f.dest_icao   = dest.icao_code
            WHERE origin.icao_code IS NOT NULL
               OR dest.icao_code   IS NOT NULL
            LIMIT 200
        """,
        "6) 5 Most Recent Arrivals at DEL": """
            SELECT 
                f.flight_number,
                a.aircraft_model AS aircraft,
                a.manufacturer,
                origin.name AS departure_airport,
                origin.city AS departure_city,
                f.actual_arr AS arrival_time,
                f.status
            FROM flights f
            LEFT JOIN aircraft a ON f.aircraft_reg = a.aircraft_reg
            LEFT JOIN airports origin ON f.origin_icao = origin.icao_code
            LEFT JOIN airports dest   ON f.dest_icao   = dest.icao_code
            WHERE dest.iata_code = 'DEL'
            ORDER BY f.scheduled_arr DESC
            LIMIT 5
        """,
        "7) Airports with No Arriving Flights": """
            SELECT 
                ap.iata_code,
                ap.name   AS airport_name,
                ap.city,
                ap.country
            FROM airports ap
            LEFT JOIN flights f ON ap.icao_code = f.dest_icao
            WHERE f.flight_id IS NULL
            ORDER BY ap.name
        """,
        "8) Flights by Status per Airline": """
            SELECT 
                f.airline_name,
                SUM(CASE WHEN f.status = 'Arrived'     THEN 1 ELSE 0 END) AS arrived,
                SUM(CASE WHEN f.status = 'Departed'    THEN 1 ELSE 0 END) AS departed,
                SUM(CASE WHEN f.status = 'Unknown'     THEN 1 ELSE 0 END) AS unknown,
                SUM(CASE WHEN f.status = 'Expected'    THEN 1 ELSE 0 END) AS expected,
                SUM(CASE WHEN f.status = 'Approaching' THEN 1 ELSE 0 END) AS approaching,
                SUM(CASE WHEN f.status = 'Canceled'    THEN 1 ELSE 0 END) AS canceled,
                SUM(CASE WHEN f.status = 'Delayed'     THEN 1 ELSE 0 END) AS delayed,
                COUNT(f.flight_id) AS total_flights
            FROM flights f
            GROUP BY f.airline_name
            ORDER BY total_flights DESC
        """,
        "9) All Cancelled Flights": """
            SELECT 
                f.flight_number,
                f.airline_name,
                dest.name AS destination_airport,
                dest.city AS destination_city,
                f.scheduled_dep AS scheduled_departure,
                f.status
            FROM flights f
            LEFT JOIN aircraft a ON f.aircraft_reg = a.aircraft_reg
            LEFT JOIN airports origin ON f.origin_icao = origin.icao_code
            LEFT JOIN airports dest   ON f.dest_icao   = dest.icao_code
            WHERE f.status = 'Canceled'
            ORDER BY f.scheduled_dep DESC NULLS LAST
        """,
        "10) City Pairs with > 2 Aircraft Models": """
            SELECT 
                origin.city AS origin_city,
                dest.city   AS dest_city,
                origin.iata_code AS origin_code,
                dest.iata_code   AS dest_code,
                COUNT(DISTINCT a.aircraft_model) AS aircraft_model_count,
                GROUP_CONCAT(DISTINCT a.aircraft_model) AS aircraft_models
            FROM flights f
            LEFT JOIN airports origin ON f.origin_icao = origin.icao_code
            LEFT JOIN airports dest   ON f.dest_icao   = dest.icao_code
            LEFT JOIN aircraft a      ON f.aircraft_reg = a.aircraft_reg
            GROUP BY origin.city, dest.city, origin.iata_code, dest.iata_code
            HAVING COUNT(DISTINCT a.aircraft_model) > 2
            ORDER BY aircraft_model_count DESC
            LIMIT 20
        """,
        "11) % Delayed Arrivals per Destination": """
            SELECT 
                ap.name AS airport_name,
                ap.city,
                ap.iata_code,
                COUNT(f.flight_id) AS total_arrivals,
                SUM(CASE WHEN f.status = 'Delayed' OR f.delay_arr > 0 THEN 1 ELSE 0 END)
                    AS delayed_arrivals,
                ROUND(
                    (SUM(CASE WHEN f.status = 'Delayed' OR f.delay_arr > 0 THEN 1 ELSE 0 END)
                    * 100.0) / COUNT(f.flight_id),
                    2
                ) AS delay_percentage
            FROM airports ap
            JOIN flights f ON ap.icao_code = f.dest_icao
            GROUP BY ap.icao_code, ap.name, ap.city, ap.iata_code
            HAVING COUNT(f.flight_id) > 0
            ORDER BY delay_percentage DESC
        """,
    }
    
    selected_query = st.selectbox("Select Query", list(query_options.keys()))
    
    if st.button("Execute Query"):
        with st.spinner("Executing query..."):
            result = get_data(query_options[selected_query])
            st.success(f"Query returned {len(result)} rows")
            st.dataframe(result, use_container_width=True)
            
            # Download option
            csv = result.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"{selected_query.replace(' ', '_')}.csv",
                mime="text/csv"
            )

# ============================================================================
# 👨‍💻 PAGE 7: ABOUT PROJECT
# ============================================================================

elif page == "👨‍💻 About Project":
    st.title("👨‍💻 About This Project")
    
    st.markdown("""
    ## 🎯 Air Tracker: Flight Analytics
    ### 📌 Project Overview
    **GUVI Project**  
    **Domain:** Aviation / Data Analytics
    
    ### 📊 Database Schema
    - **airports:** 12 major airports
    - **aircraft:** 2,370+ aircraft records
    - **flights:** 32,824+ flight records
        
    ### 👨‍💻 Developer Information
    **Created by:** [Rajaguru]
    
    ### 📚 Project Structure
```
    air-tracker/
    ├── app.py                 # Streamlit application
    ├── air_tracker.db        # SQLite database
    ├── data_collection.ipynb # API data extraction
    ├── requirements.txt      # Dependencies
    └── README.md            # Documentation
```
    """)
