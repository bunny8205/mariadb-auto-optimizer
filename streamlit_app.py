import os
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
import streamlit as st
import pymysql
import pandas as pd
import time
import os
import sys
import re

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
            connect_timeout=10,
            autocommit=True  # Better transaction handling
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

def clear_database_cache(conn):
    """Clear database cache for consistent benchmarking"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("FLUSH TABLES")
            cursor.execute("RESET QUERY CACHE")
        return True
    except Exception as e:
        st.warning(f"Could not clear cache: {e}")
        return False

def run_query_with_timing(conn, query, num_runs=3):
    """Run query multiple times and return statistical results"""
    times = []
    
    for i in range(num_runs):
        start_time = time.time()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
            end_time = time.time()
            execution_time = end_time - start_time
            times.append(execution_time)
        except Exception as e:
            st.error(f"Error in run {i + 1}: {e}")
            return None
    
    if times:
        return {
            'times': times,
            'median': sorted(times)[len(times)//2],
            'mean': sum(times) / len(times),
            'min': min(times),
            'max': max(times)
        }
    return None

def create_smart_indexes_for_query(conn, query):
    """Create indexes based on actual query patterns (fixed alias handling)"""
    created_indexes = []
    query_lower = query.lower()
    
    # Extract columns from query using regex patterns
    column_patterns = [
        r'where\s+(\w+)\.(\w+)\s*[=<>!]',
        r'join\s+\w+\s+on\s+(\w+)\.(\w+)\s*=\s*\w+\.\w+',
        r'group by\s+(\w+)\.(\w+)',
        r'order by\s+(\w+)\.(\w+)',
        r'on\s+(\w+)\.(\w+)\s*=\s*\w+\.\w+'
    ]
    
    actual_columns = []
    for pattern in column_patterns:
        matches = re.finditer(pattern, query_lower)
        for match in matches:
            table, column = match.groups()
            
            # Map common aliases to real tables (IGNORE subquery aliases like r2, r3)
            if table in ['r', 'routes']:
                table = 'routes'
            elif table in ['a', 'airports']:
                table = 'airports'
            elif table in ['al', 'airlines']:
                table = 'airlines'
            elif table in ['src', 'source']:
                table = 'airports'
            elif table in ['dest', 'destination']:
                table = 'airports'
            # Skip subquery aliases (r2, r3, etc.) - they don't represent real tables
            elif table in ['r2', 'r3', 'r4', 'r5']:
                continue
            else:
                # If it's not a recognized alias, assume it's a real table name
                if table not in ['routes', 'airports', 'airlines']:
                    continue
                
            actual_columns.append((table, column))
    
    # Remove duplicates
    actual_columns = list(set(actual_columns))
    
    # Show what columns were found
    if actual_columns:
        st.info(f"🔍 Found indexable columns: {actual_columns}")
    
    # Group columns by table
    columns_by_table = {}
    for table, column in actual_columns:
        if table not in columns_by_table:
            columns_by_table[table] = []
        if column not in columns_by_table[table]:
            columns_by_table[table].append(column)
    
    # Create indexes for each table
    for table, columns in columns_by_table.items():
        if not columns:
            continue
            
        st.write(f"**Creating indexes for table `{table}`:**")
        
        # Create composite index for multiple columns
        if len(columns) >= 2:
            idx_name = f"idx_{table}_composite_{'_'.join(columns[:2])}"
            composite_cols = ', '.join(columns[:2])
            sql = f"CREATE INDEX {idx_name} ON {table} ({composite_cols})"
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                created_indexes.append(idx_name)
                st.success(f"✓ Composite index: `{idx_name}`")
            except Exception as e:
                if "Duplicate key name" not in str(e):
                    st.warning(f"Failed to create index {idx_name}: {e}")
        
        # Create single-column indexes for important columns
        for column in columns:
            # Only create single indexes for columns that benefit from them
            if column in ['country', 'city', 'active', 'airline_id', 'source_airport_id', 'dest_airport_id', 'stops', 'name']:
                idx_name = f"idx_{table}_{column}"
                sql = f"CREATE INDEX {idx_name} ON {table} ({column})"
                
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(sql)
                    created_indexes.append(idx_name)
                    st.success(f"✓ Single-column index: `{idx_name}`")
                except Exception as e:
                    if "Duplicate key name" not in str(e):
                        st.warning(f"Failed to create index {idx_name}: {e}")
    
    return created_indexes

def display_performance_comparison(baseline_stats, optimized_stats):
    """Display performance comparison with visual indicators"""
    improvement = ((baseline_stats['median'] - optimized_stats['median']) / baseline_stats['median']) * 100
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.metric(
            "Before Optimization", 
            f"{baseline_stats['median']:.3f}s",
            delta=None
        )
    
    with col2:
        st.metric(
            "After Optimization", 
            f"{optimized_stats['median']:.3f}s", 
            delta=None
        )
    
    with col3:
        if improvement > 0:
            st.metric(
                "Improvement",
                f"{improvement:.1f}%",
                delta=f"🎉 {improvement:.1f}% faster"
            )
        else:
            st.metric(
                "Performance",
                f"{abs(improvement):.1f}%",
                delta=f"⚠️ {abs(improvement):.1f}% slower",
                delta_color="inverse"
            )
    
    # Performance rating
    if improvement > 50:
        rating = "🏆 PHENOMENAL!"
        color = "green"
    elif improvement > 30:
        rating = "🎯 EXCELLENT!"
        color = "green" 
    elif improvement > 15:
        rating = "⭐ GREAT!"
        color = "blue"
    elif improvement > 5:
        rating = "👍 GOOD!"
        color = "blue"
    else:
        rating = "⚡ MINIMAL"
        color = "gray"
    
    st.write(f"**Performance Rating:** :{color}[{rating}]")
    
    # Show detailed timing information
    with st.expander("📊 Detailed Timing Information"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Baseline Execution:**")
            st.write(f"- Runs: {[f'{t:.3f}s' for t in baseline_stats['times']]}")
            st.write(f"- Mean: {baseline_stats['mean']:.3f}s")
            st.write(f"- Min: {baseline_stats['min']:.3f}s") 
            st.write(f"- Max: {baseline_stats['max']:.3f}s")
        
        with col2:
            st.write("**Optimized Execution:**")
            st.write(f"- Runs: {[f'{t:.3f}s' for t in optimized_stats['times']]}")
            st.write(f"- Mean: {optimized_stats['mean']:.3f}s")
            st.write(f"- Min: {optimized_stats['min']:.3f}s")
            st.write(f"- Max: {optimized_stats['max']:.3f}s")

def cleanup_indexes(conn, index_list):
    """Clean up created indexes"""
    if not index_list:
        return
    
    for index_spec in index_list:
        try:
            if "idx_" in index_spec:
                parts = index_spec.split('_')
                table = parts[1] if len(parts) > 1 else None
                if table:
                    with conn.cursor() as cursor:
                        cursor.execute(f"ALTER TABLE {table} DROP INDEX IF EXISTS `{index_spec}`")
                    st.info(f"Cleaned up: {index_spec}")
        except Exception as e:
            st.warning(f"Failed to clean up {index_spec}: {e}")

def safe_close_connection(conn):
    """Safely close connection without raising errors"""
    try:
        if conn and conn.open:
            conn.close()
    except:
        pass  # Ignore any errors during close

# --- Demo Queries ---
DEMO_QUERIES = {
    "Simple Count": "SELECT COUNT(*) as total_airports FROM airports;",
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
st.title("⚙️ MariaDB Auto-Optimizer — Real Performance Comparison")
st.caption("Run queries below to compare Normal vs Optimized Execution with ACTUAL index creation")

# --- Database Setup Section ---
st.sidebar.header("Database Setup")

def check_database_tables(conn):
    """Check if required tables exist"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = %s AND table_name IN ('airports', 'airlines', 'routes')
            """, (DB_NAME,))
            return cursor.fetchone()[0] == 3
    except Exception as e:
        st.error(f"Error checking tables: {e}")
        return False

def setup_database_tables(conn):
    """Set up the required database tables"""
    try:
        with conn.cursor() as cursor:
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
        st.error(f"Error creating tables: {e}")
        return False

def load_sample_data(conn):
    """Load minimal sample data for demo"""
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
                (8, 'Beijing Capital International', 'Beijing', 'China', 'PEK', 'ZBAA'),
                (9, 'Chicago O\'Hare International', 'Chicago', 'United States', 'ORD', 'KORD'),
                (10, 'Dubai International', 'Dubai', 'United Arab Emirates', 'DXB', 'OMDB')
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
                (8, 'Air China', 'China', 'Y', 'CA', 'CCA'),
                (9, 'Emirates', 'United Arab Emirates', 'Y', 'EK', 'UAE'),
                (10, 'United Airlines', 'United States', 'Y', 'UA', 'UAL')
            """)
            
            # Insert sample routes
            cursor.execute("""
                INSERT IGNORE INTO routes (airline_id, source_airport_id, dest_airport_id, stops) VALUES
                (1, 1, 3, 0), (1, 1, 4, 0), (1, 2, 3, 1), (1, 2, 6, 0),
                (2, 1, 5, 0), (2, 2, 6, 1), (2, 9, 3, 0),
                (3, 3, 1, 0), (3, 3, 2, 0), (3, 3, 7, 1), (3, 3, 8, 0),
                (4, 4, 1, 0), (4, 4, 8, 0), (4, 4, 9, 1),
                (5, 5, 2, 0), (5, 5, 6, 0), (5, 5, 10, 0),
                (6, 6, 3, 1), (6, 6, 7, 0), (6, 6, 9, 0),
                (7, 7, 1, 1), (7, 7, 4, 0), (7, 7, 5, 0),
                (8, 8, 2, 0), (8, 8, 5, 0), (8, 8, 10, 1),
                (9, 10, 1, 0), (9, 10, 3, 0), (9, 10, 6, 0),
                (10, 9, 4, 0), (10, 9, 7, 1), (10, 9, 8, 0)
            """)

            conn.commit()
            return True
    except Exception as e:
        st.error(f"Error loading sample data: {e}")
        return False

# Check database status
conn = None
try:
    conn = get_connection()
    if conn:
        db_ready = check_database_tables(conn)
    else:
        db_ready = False
finally:
    safe_close_connection(conn)

if not db_ready:
    st.warning("⚠️ Database tables not found. Please initialize the database first.")
    if st.sidebar.button("🔄 Initialize Database"):
        conn = get_connection()
        if conn:
            try:
                with st.spinner("Setting up database tables and loading sample data..."):
                    if setup_database_tables(conn) and load_sample_data(conn):
                        st.success("✅ Database initialized successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to initialize database")
            finally:
                safe_close_connection(conn)
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

col1, col2, col3 = st.columns(3)
with col1:
    run_comparison = st.button("🚀 Run Real Optimization", disabled=not db_ready)
with col2:
    show_suggestions = st.button("💡 Show Suggestions Only", disabled=not db_ready)
with col3:
    clear_indexes = st.button("🧹 Clear All Indexes")

if clear_indexes:
    conn = get_connection()
    if conn:
        try:
            # Drop all non-primary indexes
            with conn.cursor() as cursor:
                for table in ["routes", "airports", "airlines"]:
                    cursor.execute(f"""
                        SELECT INDEX_NAME 
                        FROM information_schema.STATISTICS 
                        WHERE TABLE_SCHEMA = %s 
                        AND TABLE_NAME = %s 
                        AND INDEX_NAME != 'PRIMARY'
                    """, (DB_NAME, table))
                    indexes = [row[0] for row in cursor.fetchall()]
                    for index in indexes:
                        cursor.execute(f"ALTER TABLE {table} DROP INDEX IF EXISTS `{index}`")
            conn.commit()
            st.success("✅ All indexes cleared!")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing indexes: {e}")
        finally:
            safe_close_connection(conn)

# Main execution logic
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
            # Run full comparison with ACTUAL index creation
            st.subheader("📊 Real Performance Comparison")
            
            # Step 1: Baseline performance
            with st.spinner("Running baseline performance (without indexes)..."):
                clear_database_cache(conn)
                baseline_stats = run_query_with_timing(conn, query, num_runs=3)
                
                if not baseline_stats:
                    st.error("❌ Baseline execution failed")
                    st.stop()
                
                st.write(f"**Baseline Performance (median):** {baseline_stats['median']:.3f}s")
            
            # Step 2: Create indexes
            created_indexes = []
            with st.spinner("Creating optimized indexes..."):
                created_indexes = create_smart_indexes_for_query(conn, query)
                
                if not created_indexes:
                    st.warning("No indexes created for this query")
                    # Continue to show baseline results only
                    st.info("Showing baseline results only - no optimization performed")
                    st.stop()
            
            # Step 3: Optimized performance
            with st.spinner("Running optimized performance (with indexes)..."):
                clear_database_cache(conn)
                optimized_stats = run_query_with_timing(conn, query, num_runs=3)
                
                if not optimized_stats:
                    st.error("❌ Optimized execution failed")
                    # Clean up indexes but don't stop the app
                    if created_indexes:
                        cleanup_indexes(conn, created_indexes)
                    st.stop()
            
            # Step 4: Display results using the new comparison function
            display_performance_comparison(baseline_stats, optimized_stats)
            
            # Step 5: Show created indexes
            st.subheader("🔧 Created Indexes")
            if created_indexes:
                for idx in created_indexes:
                    st.code(f"✓ {idx}", language="text")
                
                # Ask user if they want to keep indexes
                keep_indexes = st.checkbox("Keep these indexes for future queries", value=True)
                if not keep_indexes:
                    with st.spinner("Cleaning up indexes..."):
                        cleanup_indexes(conn, created_indexes)
                        st.info("Indexes cleaned up")
            else:
                st.info("No indexes were created")
    
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
    finally:
        safe_close_connection(conn)

# --- Current Index Status ---
st.sidebar.header("Database Status")
if st.sidebar.button("📊 Show Current Indexes"):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME IN ('routes', 'airports', 'airlines')
                    AND INDEX_NAME != 'PRIMARY'
                    ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
                """, (DB_NAME,))
                
                indexes = cursor.fetchall()
                if indexes:
                    st.sidebar.write("**Current Indexes:**")
                    df_indexes = pd.DataFrame(indexes, columns=['Table', 'Index', 'Column', 'Position'])
                    st.sidebar.dataframe(df_indexes)
                else:
                    st.sidebar.info("No indexes found")
        except Exception as e:
            st.sidebar.error(f"Error fetching indexes: {e}")
        finally:
            safe_close_connection(conn)

# --- Performance Summary ---
st.sidebar.header("About")
st.sidebar.info(
    "This demo shows real performance improvements by creating optimized indexes "
    "for your SQL queries. The system analyzes query patterns and creates strategic "
    "indexes to speed up execution."
)
