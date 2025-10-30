import streamlit as st
import pymysql
import pandas as pd
import time
import os
import sys

# Add the parent directory to path to import your optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mariadb_autoopt import optimizer  # ✅ Use your existing modules

# --- Database Connection Setup ---
DB_HOST = os.getenv("AUTOOPT_DB_HOST", "serverless-us-central1.sysp0000.db2.skysql.com")
DB_PORT = int(os.getenv("AUTOOPT_DB_PORT", "4038"))
DB_USER = os.getenv("AUTOOPT_DB_USER", "dbpgf17821108")
DB_PASS = os.getenv("AUTOOPT_DB_PASS", "Rn@08022005")
DB_NAME = os.getenv("AUTOOPT_DB_NAME", "autoopt_db")

# --- Connect Function ---
def get_connection():
    try:
        conn = pymysql.connect(
            host=DB_HOST, 
            port=DB_PORT, 
            user=DB_USER,
            password=DB_PASS, 
            database=DB_NAME, 
            ssl={'ssl': {}},
            connect_timeout=10
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

def setup_database_tables(conn):
    """Set up the OpenFlights database tables with correct schema"""
    try:
        with conn.cursor() as cursor:
            # Drop existing tables if they exist
            cursor.execute("DROP TABLE IF EXISTS routes, airports, airlines")

            # Create airports table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS airports (
                    airport_id INT PRIMARY KEY,
                    name VARCHAR(255),
                    city VARCHAR(100),
                    country VARCHAR(100),
                    iata VARCHAR(10),
                    icao VARCHAR(10),
                    latitude DOUBLE,
                    longitude DOUBLE,
                    altitude INT,
                    timezone FLOAT,
                    dst VARCHAR(10),
                    tz_database_time_zone VARCHAR(100),
                    type VARCHAR(50),
                    source VARCHAR(50)
                )
            """)

            # Create airlines table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS airlines (
                    airline_id INT PRIMARY KEY,
                    name VARCHAR(255),
                    alias VARCHAR(255),
                    iata VARCHAR(10),
                    icao VARCHAR(10),
                    callsign VARCHAR(255),
                    country VARCHAR(100),
                    active VARCHAR(5)
                )
            """)

            # Create routes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    airline VARCHAR(10),
                    airline_id INT,
                    source_airport VARCHAR(10),
                    source_airport_id INT,
                    dest_airport VARCHAR(10),
                    dest_airport_id INT,
                    codeshare VARCHAR(10),
                    stops INT,
                    equipment VARCHAR(255)
                )
            """)

            conn.commit()
            return True
    except Exception as e:
        st.error(f"❌ Error creating tables: {e}")
        return False

def load_sample_data(conn):
    """Load minimal sample data for demo purposes"""
    try:
        with conn.cursor() as cursor:
            # Clear existing data
            cursor.execute("DELETE FROM routes")
            cursor.execute("DELETE FROM airlines")
            cursor.execute("DELETE FROM airports")
            
            # Insert sample airports
            cursor.execute("""
                INSERT IGNORE INTO airports (airport_id, name, city, country, iata, icao) VALUES
                (1, 'John F Kennedy International', 'New York', 'United States', 'JFK', 'KJFK'),
                (2, 'Los Angeles International', 'Los Angeles', 'United States', 'LAX', 'KLAX'),
                (3, 'Heathrow Airport', 'London', 'United Kingdom', 'LHR', 'EGLL'),
                (4, 'Charles de Gaulle Airport', 'Paris', 'France', 'CDG', 'LFPG'),
                (5, 'Frankfurt Airport', 'Frankfurt', 'Germany', 'FRA', 'EDDF'),
                (6, 'Tokyo Haneda Airport', 'Tokyo', 'Japan', 'HND', 'RJTT'),
                (7, 'Sydney Airport', 'Sydney', 'Australia', 'SYD', 'YSSY'),
                (8, 'Beijing Capital International', 'Beijing', 'China', 'PEK', 'ZBAA')
            """)
            
            # Insert sample airlines
            cursor.execute("""
                INSERT IGNORE INTO airlines (airline_id, name, country, active, iata, icao) VALUES
                (1, 'American Airlines', 'United States', 'Y', 'AA', 'AAL'),
                (2, 'Delta Air Lines', 'United States', 'Y', 'DL', 'DAL'),
                (3, 'British Airways', 'United Kingdom', 'Y', 'BA', 'BAW'),
                (4, 'Air France', 'France', 'Y', 'AF', 'AFR'),
                (5, 'Lufthansa', 'Germany', 'Y', 'LH', 'DLH'),
                (6, 'Japan Airlines', 'Japan', 'Y', 'JL', 'JAL'),
                (7, 'Qantas', 'Australia', 'Y', 'QF', 'QFA'),
                (8, 'Air China', 'China', 'Y', 'CA', 'CCA')
            """)
            
            # Insert sample routes
            cursor.execute("""
                INSERT IGNORE INTO routes (airline_id, source_airport_id, dest_airport_id, stops) VALUES
                (1, 1, 3, 0), (1, 1, 4, 0), (1, 2, 3, 1),
                (2, 1, 5, 0), (2, 2, 6, 1),
                (3, 3, 1, 0), (3, 3, 2, 0), (3, 3, 7, 1),
                (4, 4, 1, 0), (4, 4, 8, 0),
                (5, 5, 2, 0), (5, 5, 6, 0),
                (6, 6, 3, 1), (6, 6, 7, 0),
                (7, 7, 1, 1), (7, 7, 4, 0),
                (8, 8, 2, 0), (8, 8, 5, 0)
            """)

            conn.commit()
            return True
    except Exception as e:
        st.error(f"❌ Error loading sample data: {e}")
        return False

def check_database_ready(conn):
    """Check if database has the required tables and data"""
    try:
        with conn.cursor() as cursor:
            # Check if tables exist
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = %s AND table_name IN ('airports', 'airlines', 'routes')
            """, (DB_NAME,))
            table_count = cursor.fetchone()[0]
            
            if table_count == 3:
                # Check if data exists
                cursor.execute("SELECT COUNT(*) FROM routes")
                route_count = cursor.fetchone()[0]
                return route_count > 0
            return False
    except Exception as e:
        st.error(f"❌ Error checking database: {e}")
        return False

# --- Demo Queries ---
DEMO_QUERIES = {
    "Simple Count": "SELECT COUNT(*) as total_airports FROM airports;",
    "Airlines by Country": """
        SELECT country, COUNT(*) as airline_count 
        FROM airlines 
        WHERE active = 'Y' 
        GROUP BY country 
        ORDER BY airline_count DESC;
    """,
    "Complex Aggregation": """
        SELECT a.country, 
               a.city, 
               COUNT(*) as total_routes, 
               COUNT(DISTINCT r.airline_id) as unique_airlines, 
               AVG(r.stops) as avg_stops
        FROM routes r
        JOIN airports a ON r.source_airport_id = a.airport_id
        JOIN airlines al ON r.airline_id = al.airline_id
        WHERE a.country IN ('United States', 'China', 'Germany', 'United Kingdom', 'France')
          AND al.active = 'Y'
          AND r.stops <= 2
        GROUP BY a.country, a.city
        HAVING total_routes > 1
        ORDER BY total_routes DESC 
        LIMIT 10;
    """,
    "Large Dataset Analysis": """
        SELECT al.name as airline_name, 
               al.country, 
               COUNT(*) as total_routes, 
               (SELECT COUNT(*) 
                FROM routes r2 
                WHERE r2.airline_id = al.airline_id 
                  AND r2.stops = 0) as direct_routes, 
               (SELECT COUNT(DISTINCT r3.dest_airport_id) 
                FROM routes r3 
                WHERE r3.airline_id = al.airline_id) as unique_destinations
        FROM routes r
        JOIN airlines al ON r.airline_id = al.airline_id
        WHERE al.active = 'Y'
        GROUP BY al.airline_id, al.name, al.country
        HAVING total_routes > 1
        ORDER BY total_routes DESC 
        LIMIT 10;
    """,
    "Cross-Table Analysis": """
        SELECT src.country as source_country, 
               dest.country as dest_country, 
               COUNT(*) as route_count, 
               COUNT(DISTINCT r.airline_id) as airlines_operating, 
               MIN(r.stops) as min_stops, 
               MAX(r.stops) as max_stops
        FROM routes r
        JOIN airports src ON r.source_airport_id = src.airport_id
        JOIN airports dest ON r.dest_airport_id = dest.airport_id
        JOIN airlines al ON r.airline_id = al.airline_id
        WHERE src.country != dest.country
          AND al.active = 'Y'
          AND src.country IN ('United States', 'China', 'Germany')
          AND dest.country IN ('United Kingdom', 'France', 'Japan', 'Australia')
        GROUP BY src.country, dest.country
        HAVING route_count > 0
        ORDER BY route_count DESC
        LIMIT 10;
    """
}

# --- Streamlit UI ---
st.set_page_config(page_title="MariaDB Auto-Optimizer Demo", layout="wide")
st.title("⚙️ MariaDB Auto-Optimizer — Query Performance Comparison")
st.caption("Run queries below to compare Normal vs Optimized Execution")

# --- Database Setup Section ---
st.sidebar.header("Database Setup")

# Check if database is ready
conn = get_connection()
if conn:
    db_ready = check_database_ready(conn)
    conn.close()
else:
    db_ready = False

if not db_ready:
    st.warning("⚠️ Database not initialized. Please set up the database first.")
    if st.sidebar.button("🔄 Initialize Database & Load Sample Data"):
        conn = get_connection()
        if conn:
            with st.spinner("Setting up database tables and loading sample data..."):
                if setup_database_tables(conn) and load_sample_data(conn):
                    st.success("✅ Database initialized successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to initialize database")
            conn.close()
else:
    st.sidebar.success("✅ Database ready!")

# --- Query Selection ---
st.sidebar.header("Query Selection")
selected_query = st.sidebar.selectbox(
    "Choose a demo query:",
    list(DEMO_QUERIES.keys())
)

# --- Query Input ---
default_query = DEMO_QUERIES[selected_query]
query = st.text_area("Enter your SQL Query:", value=default_query, height=200)

col1, col2 = st.columns(2)
with col1:
    run_comparison = st.button("🚀 Run Query Comparison", disabled=not db_ready)
with col2:
    show_suggestions = st.button("💡 Show Optimization Suggestions Only")

if run_comparison or show_suggestions:
    if not db_ready:
        st.error("❌ Please initialize the database first using the sidebar button.")
        st.stop()
    
    conn = get_connection()
    if not conn:
        st.stop()
    
    try:
        if show_suggestions:
            # Just show optimization suggestions
            st.subheader("🔍 Optimization Suggestions")
            suggestions = optimizer.suggest_indexes(query)
            if suggestions:
                st.write("**Recommended Indexes:**")
                for i, suggestion in enumerate(suggestions, 1):
                    st.code(suggestion, language="sql")
            else:
                st.info("No optimization suggestions for this query.")
        
        if run_comparison:
            # Run full comparison
            cur = conn.cursor()
            
            # --- Run Normal Execution ---
            st.subheader("📊 Execution Comparison")
            
            with st.spinner("Running normal execution..."):
                start = time.time()
                try:
                    cur.execute(query)
                    result_normal = cur.fetchall()
                    elapsed_normal = time.time() - start
                    df_normal = pd.DataFrame(result_normal)
                    
                    # Get column names for better display
                    if cur.description:
                        columns = [desc[0] for desc in cur.description]
                        df_normal.columns = columns
                except Exception as e:
                    st.error(f"❌ Error in normal execution: {e}")
                    conn.close()
                    st.stop()
            
            # --- Run Optimized Execution ---
            with st.spinner("Running optimized execution..."):
                start = time.time()
                try:
                    optimized_query = optimizer.optimize_query(query)
                    cur.execute(optimized_query)
                    result_opt = cur.fetchall()
                    elapsed_opt = time.time() - start
                    df_opt = pd.DataFrame(result_opt)
                    
                    # Get column names for better display
                    if cur.description:
                        columns_opt = [desc[0] for desc in cur.description]
                        df_opt.columns = columns_opt
                except Exception as e:
                    st.error(f"❌ Error in optimized execution: {e}")
                    conn.close()
                    st.stop()

            # --- Display Results ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Normal Execution Time", f"{elapsed_normal:.4f}s")
                st.dataframe(df_normal, use_container_width=True)
                st.caption("Normal Query Result")
                
                # Show original query
                with st.expander("View Original Query"):
                    st.code(query, language="sql")
            
            with col2:
                st.metric("Optimized Execution Time", f"{elapsed_opt:.4f}s")
                st.dataframe(df_opt, use_container_width=True)
                st.caption("Optimized Query Result")
                
                # Show optimized query with suggestions
                with st.expander("View Optimized Query"):
                    st.code(optimized_query, language="sql")
                
                # Calculate improvement
                if elapsed_normal > 0:
                    improvement = ((elapsed_normal - elapsed_opt) / elapsed_normal) * 100
                    if improvement > 0:
                        st.success(f"✅ Performance improved by {improvement:.1f}%")
                    elif improvement < 0:
                        st.warning(f"⚠️ Performance decreased by {abs(improvement):.1f}%")
                    else:
                        st.info("⚡ No performance change")

            st.success("✅ Comparison complete!")
    
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
    finally:
        conn.close()
