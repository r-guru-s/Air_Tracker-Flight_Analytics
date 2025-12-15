import streamlit as st
import sqlite3
import pandas as pd

# -------------------------------------------------
# DB helper
# -------------------------------------------------
def get_data(query, params=None):
    conn = sqlite3.connect("air_tracker.db")
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.set_page_config(page_title="Air Tracker – Flight Analytics", layout="wide")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Project Introduction", "Flight Explorer", "SQL Queries", "Creator Info"]
)

# ---------------------- PAGE 1: INTRO ----------------------
if page == "Project Introduction":
    st.title("✈️ Air Tracker – Flight Analytics")
    st.subheader("📊 Streamlit app for exploring flight data")
    st.write("""
This project analyzes **32,824+ flights** stored in a SQLite database (`air_tracker.db`).

**Features:**
- Explore flights by airline, status, and origin.
- See per‑aircraft and per‑airport statistics.
- Run all required GUVI SQL queries and view results.
    """)

    # Quick summary metrics
    col1, col2, col3, col4 = st.columns(4)
    total_flights = get_data("SELECT COUNT(*) AS c FROM flights")["c"][0]
    total_aircraft = get_data("SELECT COUNT(*) AS c FROM aircraft")["c"][0]
    total_airports = get_data("SELECT COUNT(*) AS c FROM airports")["c"][0]
    total_airlines = get_data(
        "SELECT COUNT(DISTINCT airline_name) AS c FROM flights"
    )["c"][0]

    col1.metric("Total flights", f"{total_flights:,}")
    col2.metric("Aircraft", f"{total_aircraft:,}")
    col3.metric("Airports", str(total_airports))
    col4.metric("Airlines", str(total_airlines))

# ---------------------- PAGE 2: FLIGHT EXPLORER ----------------------
elif page == "Flight Explorer":
    st.title("🔍 Flight Explorer")

    # Filters
    airlines = get_data(
        "SELECT DISTINCT airline_name FROM flights ORDER BY airline_name"
    )["airline_name"].tolist()
    statuses = get_data(
        "SELECT DISTINCT status FROM flights ORDER BY status"
    )["status"].tolist()

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_airline = st.selectbox("Airline", ["All"] + airlines)
    with c2:
        sel_status = st.selectbox("Status", ["All"] + statuses)
    with c3:
        origins = get_data(
            "SELECT DISTINCT origin_iata FROM flights "
            "WHERE origin_iata IS NOT NULL ORDER BY origin_iata"
        )["origin_iata"].tolist()
        sel_origin = st.selectbox("Origin airport (IATA)", ["All"] + origins)

    # Build query – only flights table so it always works
    query = """
        SELECT
            flight_number,
            airline_name,
            aircraft_reg,
            origin_iata  AS origin,
            origin_city  AS origin_city,
            dest_iata    AS destination,
            dest_city    AS dest_city,
            scheduled_dep,
            actual_dep,
            status
        FROM flights
        WHERE 1=1
    """
    params = []

    if sel_airline != "All":
        query += " AND airline_name = ?"
        params.append(sel_airline)
    if sel_status != "All":
        query += " AND status = ?"
        params.append(sel_status)
    if sel_origin != "All":
        query += " AND origin_iata = ?"
        params.append(sel_origin)

    query += " ORDER BY scheduled_dep DESC LIMIT 200"

    df = get_data(query, tuple(params) if params else None)

    st.write(f"### Showing {len(df)} flights")
    st.dataframe(df, use_container_width=True, height=450)

# ---------------------- PAGE 3: SQL QUERIES ----------------------
elif page == "SQL Queries":
    st.title("📋 SQL Query Results")

    queries = {
        "1) Total flights per aircraft model": """
            SELECT a.aircraft_model,
                   COUNT(f.flight_id) AS total_flights
            FROM flights f
            JOIN aircraft a ON f.aircraft_reg = a.aircraft_reg
            GROUP BY a.aircraft_model
            ORDER BY total_flights DESC
        """,
        "2) Aircraft with more than 5 flights": """
            SELECT a.aircraft_reg AS registration,
                   a.aircraft_model AS model,
                   a.manufacturer,
                   COUNT(f.flight_id) AS flight_count
            FROM aircraft a
            JOIN flights f ON a.aircraft_reg = f.aircraft_reg
            GROUP BY a.aircraft_reg, a.aircraft_model, a.manufacturer
            HAVING COUNT(f.flight_id) > 5
            ORDER BY flight_count DESC
        """,
        "3) Airports with >5 outbound flights": """
            SELECT ap.name,
                   ap.city,
                   COUNT(f.flight_id) AS outbound_flights
            FROM airports ap
            JOIN flights f ON ap.icao_code = f.origin_icao
            GROUP BY ap.icao_code, ap.name, ap.city
            HAVING outbound_flights > 5
            ORDER BY outbound_flights DESC
        """,
        "4) Top 3 destination airports": """
            SELECT ap.name,
                   ap.city,
                   COUNT(f.flight_id) AS arriving_flights
            FROM airports ap
            JOIN flights f ON ap.icao_code = f.dest_icao
            GROUP BY ap.icao_code, ap.name, ap.city
            ORDER BY arriving_flights DESC
            LIMIT 3
        """,
        "5) Flights labeled Domestic/International": """
            SELECT
                f.flight_number,
                origin.iata_code  AS origin,
                origin.country    AS origin_country,
                dest.iata_code    AS destination,
                dest.country      AS dest_country,
                CASE
                    WHEN origin.country = dest.country THEN 'Domestic'
                    ELSE 'International'
                END AS flight_type
            FROM flights f
            LEFT JOIN airports origin ON f.origin_icao = origin.icao_code
            LEFT JOIN airports dest   ON f.dest_icao   = dest.icao_code
            WHERE origin.icao_code IS NOT NULL
               OR dest.icao_code   IS NOT NULL
            LIMIT 50
        """,
        "6) 5 most recent arrivals at DEL": """
            SELECT
                f.flight_number,
                f.airline_name,
                f.scheduled_arr AS scheduled_arrival,
                f.actual_arr    AS actual_arrival,
                f.status
            FROM flights f
            LEFT JOIN airports dest ON f.dest_icao = dest.icao_code
            WHERE dest.iata_code = 'DEL'
            ORDER BY COALESCE(f.actual_arr, f.scheduled_arr) DESC
            LIMIT 5
        """,
        "7) Airports with no arriving flights": """
            SELECT ap.iata_code,
                   ap.name,
                   ap.city,
                   ap.country
            FROM airports ap
            LEFT JOIN flights f ON ap.icao_code = f.dest_icao
            WHERE f.flight_id IS NULL
            ORDER BY ap.name
        """,
        "8) Flight count by status for each airline": """
            SELECT
                airline_name,
                SUM(CASE WHEN status = 'Arrived'    THEN 1 ELSE 0 END) AS arrived,
                SUM(CASE WHEN status = 'Departed'   THEN 1 ELSE 0 END) AS departed,
                SUM(CASE WHEN status = 'Unknown'    THEN 1 ELSE 0 END) AS unknown,
                SUM(CASE WHEN status = 'Expected'   THEN 1 ELSE 0 END) AS expected,
                SUM(CASE WHEN status = 'Approaching'THEN 1 ELSE 0 END) AS approaching,
                SUM(CASE WHEN status = 'Canceled'   THEN 1 ELSE 0 END) AS canceled,
                SUM(CASE WHEN status = 'Delayed'    THEN 1 ELSE 0 END) AS delayed,
                COUNT(*) AS total_flights
            FROM flights
            GROUP BY airline_name
            ORDER BY total_flights DESC
        """,
        "9) All cancelled flights (basic)": """
            SELECT
                flight_number,
                airline_name,
                origin_iata AS origin,
                dest_iata   AS destination,
                scheduled_dep,
                status
            FROM flights
            WHERE status = 'Canceled'
            ORDER BY scheduled_dep DESC
            LIMIT 50
        """,
        "10) City pairs with >2 aircraft models": """
            SELECT
                origin.city AS origin_city,
                dest.city   AS dest_city,
                origin.iata_code AS origin_code,
                dest.iata_code   AS dest_code,
                COUNT(DISTINCT a.aircraft_model) AS aircraft_model_count
            FROM flights f
            LEFT JOIN aircraft a ON f.aircraft_reg = a.aircraft_reg
            LEFT JOIN airports origin ON f.origin_icao = origin.icao_code
            LEFT JOIN airports dest   ON f.dest_icao   = dest.icao_code
            GROUP BY origin.city, dest.city, origin.iata_code, dest.iata_code
            HAVING COUNT(DISTINCT a.aircraft_model) > 2
            ORDER BY aircraft_model_count DESC
            LIMIT 20
        """
    }

    name = st.selectbox("Choose a query", list(queries.keys()))
    df = get_data(queries[name])
    st.write(f"### Result – {len(df)} rows")
    st.dataframe(df, use_container_width=True)

# ---------------------- PAGE 4: CREATOR INFO ----------------------
elif page == "Creator Info":
    st.title("👨‍💻 Creator of this Project")
    st.write("""
**Developed by:** Rajaguru  
**Skills:** Python, SQL, Data Analysis, Streamlit, Pandas
""")
