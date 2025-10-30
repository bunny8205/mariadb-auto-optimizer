import os
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
import streamlit as st
import pymysql
import pandas as pd
import time
import os
import sys
import re
import warnings

# Suppress pandas warnings
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy connectable.*')

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

def get_query_time(conn, query):
    """Get single query execution time"""
    start_time = time.time()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            cursor.fetchall()
        return time.time() - start_time
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return float('inf')

def should_optimize_query(conn, query, threshold_seconds=0.05):
    """Check if query is slow enough to benefit from optimization"""
    baseline_time = get_query_time(conn, query)
    return baseline_time > threshold_seconds

def validate_improvement(baseline_time, optimized_time, threshold=0.10):
    """Validate if optimization actually helped (10% improvement threshold)"""
    if optimized_time >= baseline_time:
        return False
    improvement = (baseline_time - optimized_time) / baseline_time
    return improvement >= threshold

def drop_all_indexes(conn):
    """Drop all existing indexes to simulate unoptimized database (like run_demo.py)"""
    try:
        with conn.cursor() as cursor:
            # Drop indexes from all OpenFlights tables
            for table in ["routes", "airports", "airlines"]:
                cursor.execute(f"""
                    SELECT INDEX_NAME
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = %s
                    AND INDEX_NAME != 'PRIMARY'
                """, (DB_NAME, table))
                indexes_to_drop = [row[0] for row in cursor.fetchall()]

                if indexes_to_drop:
                    st.info(f"  Dropping {len(indexes_to_drop)} indexes from {table}: {', '.join(indexes_to_drop)}")
                    for index_name in indexes_to_drop:
                        cursor.execute(f"ALTER TABLE {table} DROP INDEX IF EXISTS `{index_name}`")
                else:
                    st.info(f" No existing indexes found on {table} (perfect for demo!)")

            conn.commit()
            st.success("✅ All existing indexes removed!")
            return True

    except Exception as e:
        st.error(f"❌ Could not drop indexes: {e}")
        return False

def create_smart_indexes_for_query(conn, query):
    """Enhanced index creation matching your local demo"""
    created_indexes = []
    query_lower = query.lower()
    
    # Use the same alias resolution as your local demo
    table_aliases = {}
    alias_patterns = [
        r'from\s+(\w+)\s+(\w+)',
        r'join\s+(\w+)\s+(\w+)', 
        r'from\s+(\w+)\s+as\s+(\w+)',
        r'join\s+(\w+)\s+as\s+(\w+)'
    ]
    
    for pattern in alias_patterns:
        matches = re.finditer(pattern, query_lower)
        for match in matches:
            table_name, alias = match.groups()
            table_aliases[alias] = table_name
    
    # Extract columns with proper alias resolution
    actual_columns = []
    column_patterns = [
        r'where\s+(\w+)\.(\w+)\s*[=<>!]',
        r'join\s+\w+\s+on\s+(\w+)\.(\w+)\s*=\s*\w+\.\w+',
        r'group by\s+(\w+)\.(\w+)',
        r'order by\s+(\w+)\.(\w+)',
        r'on\s+(\w+)\.(\w+)\s*=\s*\w+\.\w+'
    ]
    
    for pattern in column_patterns:
        matches = re.finditer(pattern, query_lower)
        for match in matches:
            table_ref, column = match.groups()
            # Resolve alias
            actual_table = table_aliases.get(table_ref, table_ref)
            
            # Map aliases to real tables
            if actual_table in ['r', 'routes']:
                actual_table = 'routes'
            elif actual_table in ['a', 'airports']:
                actual_table = 'airports'  
            elif actual_table in ['al', 'airlines']:
                actual_table = 'airlines'
            elif actual_table in ['src', 'source']:
                actual_table = 'airports'
            elif actual_table in ['dest', 'destination']:
                actual_table = 'airports'
            elif actual_table in ['r2', 'r3', 'r4', 'r5']:
                continue  # Skip subquery aliases
            
            # Only include real tables
            if actual_table in ['routes', 'airports', 'airlines']:
                actual_columns.append((actual_table, column))
    
    # Remove duplicates
    actual_columns = list(set(actual_columns))
    
    if actual_columns:
        st.info(f"🔍 Found indexable columns: {actual_columns}")
    
    # Group by table and create indexes (matching your local strategy)
    columns_by_table = {}
    for table, column in actual_columns:
        if table not in columns_by_table:
            columns_by_table[table] = []
        if column not in columns_by_table[table]:
            columns_by_table[table].append(column)
    
    # Create indexes matching your successful local strategy
    for table, columns in columns_by_table.items():
        if not columns:
            continue
            
        st.write(f"**Creating indexes for table `{table}`:**")
        
        # Create composite indexes for 2+ columns (like local demo)
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
            if column in ['country', 'city', 'active', 'airline_id', 'source_airport_id', 
                         'dest_airport_id', 'stops', 'name', 'airport_id']:
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

def display_performance_comparison(baseline_stats, optimized_stats, improvement_validated=True):
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
        if improvement > 0 and improvement_validated:
            st.metric(
                "Improvement",
                f"{improvement:.1f}%",
                delta=f"🎉 {improvement:.1f}% faster"
            )
        elif improvement > 0:
            st.metric(
                "Improvement", 
                f"{improvement:.1f}%",
                delta=f"⚠️ {improvement:.1f}% faster (below threshold)",
                delta_color="off"
            )
        else:
            st.metric(
                "Performance",
                f"{abs(improvement):.1f}%",
                delta=f"⚠️ {abs(improvement):.1f}% slower",
                delta_color="inverse"
            )
    
    # Performance rating
    if improvement > 50 and improvement_validated:
        rating = "🏆 PHENOMENAL!"
        color = "green"
    elif improvement > 30 and improvement_validated:
        rating = "🎯 EXCELLENT!"
        color = "green" 
    elif improvement > 15 and improvement_validated:
        rating = "⭐ GREAT!"
        color = "blue"
    elif improvement > 5 and improvement_validated:
        rating = "👍 GOOD!"
        color = "blue"
    elif improvement > 0:
        rating = "⚡ MINIMAL (below threshold)"
        color = "gray"
    else:
        rating = "📉 REGRESSION"
        color = "red"
    
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

def check_data_volume(conn):
    """Check if tables have sufficient data for optimization"""
    table_counts = {}
    for table in ["routes", "airports", "airlines"]:
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
        except Exception as e:
            st.error(f"Error checking {table}: {e}")
    
    return table_counts

def load_openflights_data(conn):
    """Load COMPLETE OpenFlights dataset like run_demo.py"""
    try:
        # Set data path - adjust as needed for your Streamlit deployment
        data_path = "data/"  # You may need to adjust this path
        
        st.write("📥 Loading OpenFlights dataset files...")
        
        # Load .dat files using Pandas (EXACTLY like run_demo.py)
        airports = pd.read_csv(data_path + "airports.dat",
                               header=None,
                               names=[
                                   "airport_id", "name", "city", "country",
                                   "iata", "icao", "latitude", "longitude",
                                   "altitude", "timezone", "dst", "tz_database_time_zone",
                                   "type", "source"
                               ],
                               na_values="\\N")

        airlines = pd.read_csv(data_path + "airlines.dat",
                               header=None,
                               names=[
                                   "airline_id", "name", "alias", "iata",
                                   "icao", "callsign", "country", "active"
                               ],
                               na_values="\\N")

        routes = pd.read_csv(data_path + "routes.dat",
                             header=None,
                             names=[
                                 "airline", "airline_id", "source_airport",
                                 "source_airport_id", "dest_airport",
                                 "dest_airport_id", "codeshare",
                                 "stops", "equipment"
                             ],
                             na_values="\\N")

        st.success("✅ OpenFlights dataset loaded successfully!")
        st.write(f"- Airports: {len(airports):,} records")
        st.write(f"- Airlines: {len(airlines):,} records") 
        st.write(f"- Routes: {len(routes):,} records")

        # CRITICAL FIX: Replace NaN with None (important for MySQL) - EXACTLY like run_demo.py
        st.write("🔧 Converting NaN values to None for MySQL compatibility...")
        airports = airports.where(pd.notnull(airports), None)
        airlines = airlines.where(pd.notnull(airlines), None)
        routes = routes.where(pd.notnull(routes), None)

        # Additional safe string handling
        airports = airports.astype(object).where(pd.notnull(airports), None)
        airlines = airlines.astype(object).where(pd.notnull(airlines), None)
        routes = routes.astype(object).where(pd.notnull(routes), None)

        st.success("✅ NaN to None conversion completed!")

        # Create tables (EXACTLY like run_demo.py)
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

        st.success("✅ OpenFlights tables created successfully!")

        # Insert data using batch processing (EXACTLY like run_demo.py)
        def insert_dataframe_to_table(conn, df, table_name, batch_size=1000):
            """Insert DataFrame data into MariaDB table with batch processing"""
            if df.empty:
                st.warning(f"DataFrame for {table_name} is empty")
                return 0

            try:
                with conn.cursor() as cursor:
                    total_rows = len(df)
                    st.write(f"Inserting {total_rows:,} rows into {table_name}...")

                    # Get column names
                    columns = df.columns.tolist()
                    placeholders = ', '.join(['%s'] * len(columns))
                    column_names = ', '.join(columns)

                    insert_sql = f"INSERT IGNORE INTO {table_name} ({column_names}) VALUES ({placeholders})"

                    # Batch insert for performance
                    inserted_count = 0
                    progress_bar = st.progress(0)
                    for i in range(0, total_rows, batch_size):
                        batch = df.iloc[i:i + batch_size]
                        batch_data = [tuple(row) for row in batch.itertuples(index=False)]

                        cursor.executemany(insert_sql, batch_data)
                        inserted_count += len(batch_data)

                        # Update progress
                        progress = min(i + batch_size, total_rows) / total_rows
                        progress_bar.progress(progress)

                        if i + batch_size < total_rows:
                            st.write(f"   {min(i + batch_size, total_rows):,}/{total_rows:,} rows inserted...")

                    conn.commit()
                    st.success(f"✅ Successfully inserted {inserted_count:,} rows into {table_name}")
                    return inserted_count

            except Exception as e:
                st.error(f"Error inserting data into {table_name}: {e}")
                conn.rollback()
                return 0

        # Insert all three datasets
        st.write("🗂️ Inserting data into database...")
        airports_inserted = insert_dataframe_to_table(conn, airports, "airports")
        airlines_inserted = insert_dataframe_to_table(conn, airlines, "airlines")
        routes_inserted = insert_dataframe_to_table(conn, routes, "routes")

        st.success("🎉 OpenFlights data loaded successfully!")
        st.write(f"**Data Insertion Summary:**")
        st.write(f"- Airports: {airports_inserted:,} rows")
        st.write(f"- Airlines: {airlines_inserted:,} rows") 
        st.write(f"- Routes: {routes_inserted:,} rows")

        return True

    except Exception as e:
        st.error(f"❌ Error loading OpenFlights dataset: {e}")
        st.info("💡 Make sure the data files are in the correct path: data/")
        return False

# --- Demo Queries ---
DEMO_QUERIES = {
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
        HAVING total_routes > 5
        ORDER BY total_routes DESC 
        LIMIT 50;
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
        HAVING total_routes > 20
        ORDER BY total_routes DESC 
        LIMIT 30;
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
        HAVING route_count > 10
        ORDER BY route_count DESC
        LIMIT 25;
    """
}

# --- Streamlit UI ---
st.set_page_config(page_title="MariaDB Auto-Optimizer Demo", layout="wide")
st.title("⚙️ MariaDB Auto-Optimizer — Complete OpenFlights Demo")
st.caption("Uses COMPLETE OpenFlights dataset with real index optimization like local demo")

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

# Check database status
conn = None
try:
    conn = get_connection()
    if conn:
        db_ready = check_database_tables(conn)
        # Check data volume
        table_counts = check_data_volume(conn)
    else:
        db_ready = False
        table_counts = {}
finally:
    safe_close_connection(conn)

if not db_ready:
    st.warning("⚠️ Database tables not found. Please load the complete OpenFlights dataset first.")
    if st.sidebar.button("🔄 Load Complete OpenFlights Dataset"):
        conn = get_connection()
        if conn:
            try:
                with st.spinner("Loading COMPLETE OpenFlights dataset (this may take a minute)..."):
                    if load_openflights_data(conn):
                        st.success("✅ Complete OpenFlights dataset loaded successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to load OpenFlights dataset")
            finally:
                safe_close_connection(conn)
else:
    st.sidebar.success("✅ Database ready with OpenFlights data!")
    # Show data volume in sidebar
    st.sidebar.write("**Data Volume:**")
    for table, count in table_counts.items():
        st.sidebar.write(f"- {table}: {count:,} rows")

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
            drop_all_indexes(conn)
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing indexes: {e}")
        finally:
            safe_close_connection(conn)

# Main execution logic
if run_comparison or show_suggestions:
    if not db_ready:
        st.error("❌ Please load the complete OpenFlights dataset first using the sidebar button.")
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
            
            # STEP 1: DROP ALL EXISTING INDEXES (EXACTLY like run_demo.py)
            st.write("**🔧 Step 1: Preparing Database**")
            with st.spinner("Dropping all existing indexes to simulate unoptimized database..."):
                drop_all_indexes(conn)
            
            # Check if optimization is worthwhile
            st.write("**🔍 Step 2: Pre-optimization Analysis**")
            if not should_optimize_query(conn, query, threshold_seconds=0.01):  # 10ms threshold like local demo
                st.warning("⚡ Query is already fast (< 10ms) - optimization may not provide significant benefits")
                proceed_anyway = st.checkbox("Proceed with optimization anyway", value=True)
                if not proceed_anyway:
                    st.stop()
            
            # Step 3: Baseline performance
            st.write("**📊 Step 3: Baseline Performance**")
            with st.spinner("Running baseline performance (without indexes)..."):
                clear_database_cache(conn)
                baseline_stats = run_query_with_timing(conn, query, num_runs=3)
                
                if not baseline_stats:
                    st.error("❌ Baseline execution failed")
                    st.stop()
                
                st.write(f"**Baseline Performance (median):** {baseline_stats['median']:.3f}s")
            
            # Step 4: Create indexes
            st.write("**🔧 Step 4: Creating Optimized Indexes**")
            with st.spinner("Creating optimized indexes..."):
                created_indexes = create_smart_indexes_for_query(conn, query)
                
                if not created_indexes:
                    st.warning("No indexes created for this query")
                    # Continue to show baseline results only
                    st.info("Showing baseline results only - no optimization performed")
                    st.stop()
            
            # Step 5: Optimized performance
            st.write("**📊 Step 5: Optimized Performance**")
            with st.spinner("Running optimized performance (with indexes)..."):
                clear_database_cache(conn)
                optimized_stats = run_query_with_timing(conn, query, num_runs=3)
                
                if not optimized_stats:
                    st.error("❌ Optimized execution failed")
                    # Clean up indexes but don't stop the app
                    if created_indexes:
                        cleanup_indexes(conn, created_indexes)
                    st.stop()
            
            # Step 6: Validate improvement
            improvement_validated = validate_improvement(
                baseline_stats['median'], 
                optimized_stats['median'], 
                threshold=0.10
            )
            
            if improvement_validated:
                st.success(f"✅ Optimization validated! Improvement meets 10% threshold")
            else:
                improvement = ((baseline_stats['median'] - optimized_stats['median']) / baseline_stats['median']) * 100
                if improvement > 0:
                    st.warning(f"⚠️ Improvement ({improvement:.1f}%) below 10% threshold - indexes will be cleaned up")
                else:
                    st.error(f"📉 Performance regression ({abs(improvement):.1f}% slower) - indexes will be cleaned up")
            
            # Step 7: Display results
            st.write("**📈 Step 6: Performance Comparison**")
            display_performance_comparison(baseline_stats, optimized_stats, improvement_validated)
            
            # Step 8: Show created indexes and handle cleanup
            st.subheader("🔧 Created Indexes")
            if created_indexes:
                for idx in created_indexes:
                    st.code(f"✓ {idx}", language="text")
                
                # Handle index cleanup based on validation
                if improvement_validated:
                    keep_indexes = st.checkbox("Keep these indexes for future queries", value=True)
                    if not keep_indexes:
                        with st.spinner("Cleaning up indexes..."):
                            cleanup_indexes(conn, created_indexes)
                            st.info("Indexes cleaned up")
                else:
                    with st.spinner("Cleaning up indexes (improvement below threshold)..."):
                        cleanup_indexes(conn, created_indexes)
                        st.info("Indexes cleaned up due to insufficient improvement")
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
    "This demo uses the COMPLETE OpenFlights dataset with real performance "
    "optimization. The system drops all indexes before each run and creates "
    "strategic indexes based on query patterns."
)

# --- Optimization Strategy Info ---
with st.sidebar.expander("🔧 Optimization Strategy"):
    st.write("""
    **Complete OpenFlights Demo:**
    - ✅ Loads ALL OpenFlights data (airports.dat, airlines.dat, routes.dat)
    - ✅ Drops ALL indexes before each run (like local demo)
    - ✅ Uses 10ms optimization threshold
    - ✅ 10% improvement validation
    - ✅ Batch data insertion with progress
    
    **Smart Optimization Features:**
    - ✅ Table alias resolution
    - ✅ Composite index creation  
    - ✅ Single-column indexes for key columns
    - ✅ Automatic index cleanup
    
    **Expected Results:**
    - Complex queries: 50-90% improvement
    - Medium queries: 20-50% improvement  
    - Fast queries: Minimal improvement
    """)
