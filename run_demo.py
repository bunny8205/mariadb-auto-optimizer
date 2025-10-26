

# Suppress pandas warnings for DB-API connections
import warnings

warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy connectable.*')

print("✅ Packages installed and warnings suppressed!")

# Import the optimizer and required libraries
import sys
import os
import time

sys.path.append('..')  # Add parent directory to path

try:
    from mariadb_autoopt import optimize_once
    from mariadb_autoopt.magic import optimize_and_show

    print("✅ MariaDB Auto-Optimizer imported successfully!")
except ImportError as e:
    print(f"⚠️ Could not import mariadb_autoopt: {e}")
    print("💡 Make sure the package is installed and path is correct")

import pymysql
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

print("✅ Libraries imported successfully!")


# ---------------------------------------------
# 🔹 SMART AUTO-OPTIMIZER DECISION ENGINE
# ---------------------------------------------
def detect_table_size(conn, table_name="sales"):
    """Detect total row count and classify table size"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            rows = cursor.fetchone()[0]
        if rows < 100_000:
            return "small", rows
        elif rows < 1_000_000:
            return "medium", rows
        else:
            return "large", rows
    except Exception as e:
        print(f"⚠️ Could not detect table size: {e}")
        return "unknown", 0


def detect_query_type(query):
    """Infer query type from SQL keywords"""
    q = query.lower()
    if "join" in q:
        return "join"
    elif "group by" in q:
        return "aggregation"
    elif "where" in q:
        return "filter"
    else:
        return "simple"


def choose_optimization_strategy(conn, query):
    """Select optimization mode based on table size and query type"""
    size_label, rows = detect_table_size(conn)
    query_type = detect_query_type(query)

    print(f"\n📊 Table Size: {rows:,} rows ({size_label})")
    print(f"🔍 Query Type: {query_type}")

    if size_label == "small":
        print("🎓 Mode: Educational Optimization (analysis only)")
        return "analyze_only"
    elif size_label == "medium" and query_type in ["filter", "aggregation"]:
        print("⚙️ Mode: Balanced Optimization (light indexes)")
        return "light_indexes"
    elif size_label == "large" or query_type == "join":
        print("🔥 Mode: Full Optimization (composite indexes, aggressive tuning)")
        return "full_optimize"
    else:
        print("ℹ️ Defaulting to light optimization")
        return "light_indexes"


# Query cache for performance
query_cache = {}


# Enhanced database connection with retry logic
def connect_to_database(max_retries=3):
    """Connect to database with comprehensive error handling and retry logic"""
    for attempt in range(max_retries):
        try:
            conn = pymysql.connect(
                host='localhost',
                user='autoopt_user',
                password='rn8205',
                database='test_autoopt',
                autocommit=True,
                connect_timeout=10,
                charset='utf8mb4'
            )
            print("✅ Connected to database successfully!")

            # Test the connection and get server info
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                print(f"📊 Database Version: {version}")

                # Get server status
                cursor.execute("SHOW STATUS LIKE 'Uptime'")
                uptime = cursor.fetchone()[1]
                print(f"⏰ Server Uptime: {int(uptime) // 3600} hours")

            return conn

        except pymysql.OperationalError as e:
            print(f"❌ Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("\n💡 Troubleshooting tips:")
                print("   • Check if MariaDB/MySQL is running: sudo systemctl status mysql")
                print("   • Verify credentials and database exists")
                print("   • Check firewall settings")
                print("   • Ensure user has proper permissions")
                return None


# Connect to database
conn = connect_to_database()
if not conn:
    print("❌ Cannot continue without database connection")
    exit(1)


# Enhanced sample data creation with progress tracking
def create_enhanced_sample_data(conn):
    """Create comprehensive sample data with realistic distributions"""
    print("🔄 Creating enhanced sample database...")

    try:
        with conn.cursor() as cursor:
            # Drop and recreate tables for clean state
            cursor.execute("DROP TABLE IF EXISTS sales, products, users")

            # Create products table
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS products
                           (
                               product_id
                               INT
                               PRIMARY
                               KEY,
                               product_name
                               VARCHAR
                           (
                               100
                           ),
                               category VARCHAR
                           (
                               50
                           ),
                               price DECIMAL
                           (
                               10,
                               2
                           ),
                               created_date DATE
                               )
                           """)

            # Create users table
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS users
                           (
                               user_id
                               INT
                               PRIMARY
                               KEY,
                               username
                               VARCHAR
                           (
                               50
                           ),
                               region VARCHAR
                           (
                               50
                           ),
                               signup_date DATE
                               )
                           """)

            # Create main sales table
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS sales
                           (
                               sale_id
                               INT
                               AUTO_INCREMENT
                               PRIMARY
                               KEY,
                               product_id
                               INT,
                               user_id
                               INT,
                               order_date
                               DATE,
                               amount
                               DECIMAL
                           (
                               10,
                               2
                           ),
                               category VARCHAR
                           (
                               50
                           ),
                               region VARCHAR
                           (
                               50
                           ),
                               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                               )
                           """)

            # Insert sample products
            products = []
            categories = ['Electronics', 'Clothing', 'Books', 'Home', 'Sports']
            for i in range(100):
                category = categories[i % len(categories)]
                products.append((
                    i + 1,
                    f"Product {i + 1}",
                    category,
                    round(np.random.uniform(10, 500), 2),
                    '2020-01-01'
                ))

            cursor.executemany(
                "INSERT INTO products (product_id, product_name, category, price, created_date) VALUES (%s, %s, %s, %s, %s)",
                products
            )

            # Insert sample users
            users = []
            regions = ['North', 'South', 'East', 'West', 'Central']
            for i in range(1000):
                region = regions[i % len(regions)]
                users.append((
                    i + 1,
                    f"user{i + 1}",
                    region,
                    '2020-01-01'
                ))

            cursor.executemany(
                "INSERT INTO users (user_id, username, region, signup_date) VALUES (%s, %s, %s, %s)",
                users
            )

            # Insert initial sales data
            print("📊 Generating initial sales data...")
            sales_data = []
            base_date = pd.Timestamp('2020-01-01')

            for i in range(50000):  # Start with 50k rows
                product_id = np.random.randint(1, 101)
                user_id = np.random.randint(1, 1001)
                days_offset = np.random.randint(0, 1460)  # 4 years range
                order_date = base_date + pd.Timedelta(days=days_offset)
                amount = round(np.random.uniform(20, 1000), 2)
                category = categories[product_id % len(categories)]
                region = regions[user_id % len(regions)]

                sales_data.append((
                    product_id,
                    user_id,
                    order_date.strftime('%Y-%m-%d'),
                    amount,
                    category,
                    region
                ))

                # Batch insert for efficiency
                if len(sales_data) >= 1000:
                    cursor.executemany(
                        "INSERT INTO sales (product_id, user_id, order_date, amount, category, region) VALUES (%s, %s, %s, %s, %s, %s)",
                        sales_data
                    )
                    sales_data = []
                    print(f"   {i + 1}/50000 records inserted...")

            # Insert any remaining records
            if sales_data:
                cursor.executemany(
                    "INSERT INTO sales (product_id, user_id, order_date, amount, category, region) VALUES (%s, %s, %s, %s, %s, %s)",
                    sales_data
                )

            conn.commit()
            print("✅ Enhanced sample database created successfully!")
            return True

    except Exception as e:
        print(f"❌ Failed to create sample data: {e}")
        return False


# Create sample database with test data (if needed)
try:
    # Check if sales table exists and has data
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'test_autoopt' AND table_name = 'sales'")
        table_exists = cursor.fetchone()[0] > 0

        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM sales")
            row_count = cursor.fetchone()[0]
            if row_count > 0:
                print(f"✅ Sales table exists with {row_count:,} rows")
            else:
                print("🔄 Sales table exists but is empty. Creating sample data...")
                create_enhanced_sample_data(conn)
        else:
            print("🔄 Creating enhanced sample database...")
            create_enhanced_sample_data(conn)

except Exception as e:
    print(f"⚠️ Sample data setup issue: {e}")
    print("Creating fresh sample database...")
    create_enhanced_sample_data(conn)

# 💡 STEP 1: EXPAND DATASET FOR DRAMATIC PERFORMANCE DEMO
print("\n📈 EXPANDING DATASET FOR PERFORMANCE DEMO...")
print("=" * 50)

try:
    # First check current row count and table size
    size_label, current_count = detect_table_size(conn)
    print(f"📊 Current table size: {current_count:,} rows ({size_label})")

    # Smart dataset expansion based on current size
    if size_label == "small":
        expansion_factor = 8  # 8x more rows for small tables
        batches = 3
    elif size_label == "medium":
        expansion_factor = 4  # 4x more rows for medium tables
        batches = 2
    else:
        expansion_factor = 2  # 2x more rows for large tables
        batches = 1

    print(f"💾 Expanding data by {expansion_factor}x in {batches} batches...")

    for i in range(batches):
        with conn.cursor() as cursor:
            cursor.execute("""
                           INSERT INTO sales (product_id, user_id, order_date, amount, category, region)
                           SELECT product_id,
                                  user_id,
                                  DATE_ADD(order_date, INTERVAL FLOOR(RAND() * 365*2) DAY) as order_date,
                                  amount * (0.8 + RAND() * 0.4)                            as amount,
                                  #                                                           Vary amounts slightly
                    category, region
                           FROM sales
                           """)
            conn.commit()
            print(f"   Batch {i + 1}/{batches} completed...")

    # Check final row count
    size_label, final_count = detect_table_size(conn)
    print(f"✅ Dataset expanded! Table now has {final_count:,} rows ({size_label}).")
    print(f"📈 Increased by {final_count - current_count:,} rows ({(final_count / current_count):.1f}x larger)")

except Exception as e:
    print(f"⚠️ Could not expand dataset: {e}")
    print("Continuing with existing data...")

# Optional: Smart sampling for very large datasets
size_label, rows = detect_table_size(conn)
if size_label == "large" and rows > 2_000_000:
    print(f"⚡ Table very large ({rows:,} rows). Creating optimized demo table...")
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS sales_demo")
            cursor.execute("CREATE TABLE sales_demo AS SELECT * FROM sales LIMIT 500000")
            cursor.execute("CREATE INDEX idx_demo_category ON sales_demo(category)")
            cursor.execute("CREATE INDEX idx_demo_date ON sales_demo(order_date)")
        conn.commit()
        print("✅ Created optimized demo table 'sales_demo' with 500k rows.")
    except Exception as e:
        print(f"⚠️ Could not create demo table: {e}")

# Check what tables we have
print("\n📊 DATABASE TABLES:")
tables = pd.read_sql("SHOW TABLES", conn)
print(tables)

# Check current indexes on sales table
print("\n🔍 CURRENT INDEXES ON SALES TABLE:")
try:
    indexes = pd.read_sql("SHOW INDEX FROM sales", conn)
    if indexes.empty:
        print("✅ No indexes found (perfect for our demo!)")
        print("   This means our queries will be slow initially.")
    else:
        print(f"📋 Found {len(indexes)} existing indexes:")
        display(indexes[['Table', 'Key_name', 'Column_name', 'Seq_in_index']].head(10))
except Exception as e:
    print(f"ℹ️ Could not check indexes: {e}")

# Preview sample data
print("\n📈 SAMPLE SALES DATA (first 5 rows):")
sample_data = pd.read_sql("SELECT * FROM sales LIMIT 5", conn)
display(sample_data)

# Check data statistics
print("\n📊 DATA STATISTICS:")
stats = pd.read_sql("""
                    SELECT COUNT(*)                   as total_records,
                           MIN(order_date)            as earliest_date,
                           MAX(order_date)            as latest_date,
                           COUNT(DISTINCT product_id) as unique_products,
                           COUNT(DISTINCT category)   as unique_categories,
                           COUNT(DISTINCT region)     as unique_regions,
                           AVG(amount)                as avg_amount,
                           MAX(amount)                as max_amount
                    FROM sales
                    """, conn)
display(stats)

# Setup connection for magic commands
import __main__

__main__.conn = conn  # Make conn available in main namespace

# Load the magic extension
try:
    %reload_ext
    mariadb_autoopt.magic
    print("✅ Magic setup complete! You can now use:")
    print("   %%mariadb_opt conn=conn auto_apply=False")
    print("   YOUR SQL QUERY")
except:
    print("⚠️ Magic extension not available, continuing with core optimizer...")

# 🚀 DEFINITIVE WORKING SOLUTION - NO MAGIC REQUIRED
print("\n" + "🚀" * 20)
print("🚀 MARIA DB AUTO-OPTIMIZER - INTELLIGENT ADAPTIVE DEMO")
print("🚀" * 20)

from mariadb_autoopt.core import optimize_once
import matplotlib.pyplot as plt
import pandas as pd


def run_optimizer_demo(conn, query, description, auto_apply=False):
    """Run complete optimizer demo with intelligent adaptive optimization"""
    print(f"\n🎯 {description}")
    print("-" * 50)
    print(f"📝 Query: {query[:100]}..." if len(query) > 100 else f"📝 Query: {query}")

    # Check cache first
    if query in query_cache:
        print("⚡ Using cached query performance results...")
        return query_cache[query]

    # Smart strategy selection
    strategy = choose_optimization_strategy(conn, query)
    auto_apply = strategy in ["light_indexes", "full_optimize"]

    # Run optimization with adaptive mode
    print(f"🧠 Running optimizer in '{strategy}' mode...")
    result = optimize_once(conn, query, auto_apply=auto_apply, verbose=True)

    # Display results
    print(f"\n📊 RESULTS:")
    print(f"⏱️  Execution Time: {result['before_time']:.3f} seconds")
    print(f"📈 Rows Returned: {result['before_rows']}")

    if result['explain_df'] is not None:
        print(f"\n🔍 EXPLAIN Analysis ({result['explain_mode']}):")
        display(result['explain_df'])

    # Show suggested indexes
    if result['suggestions']:
        print(f"\n💡 SUGGESTED OPTIMIZATIONS:")
        for i, suggestion in enumerate(result['suggestions'], 1):
            print(f"   {i}. {suggestion}")
    else:
        print("\n✅ Query already efficient — no optimization needed!")

    print(f"\n💡 OPTIMIZATION ANALYSIS:")
    print(result['explanation'])

    # Show optimization results if applied
    if result['after_time'] is not None:
        print(f"\n🚀 OPTIMIZATION RESULTS:")
        print(f"   Before: {result['before_time']:.3f}s")
        print(f"   After:  {result['after_time']:.3f}s")

        improvement = ((result['before_time'] - result['after_time']) / result['before_time']) * 100
        print(f"   Improvement: {improvement:.1f}% faster!")

        # Performance rating
        if improvement > 90:
            rating = "🏆 PHENOMENAL!"
        elif improvement > 70:
            rating = "🎯 EXCELLENT!"
        elif improvement > 50:
            rating = "⭐ GREAT!"
        elif improvement > 20:
            rating = "👍 GOOD!"
        else:
            rating = "📈 MODEST"

        print(f"   Performance Rating: {rating}")

        # Create visualization
        plt.figure(figsize=(8, 4))
        times = [result['before_time'], result['after_time']]
        labels = ['Before', 'After']
        colors = ['#ff6b6b', '#51cf66']

        bars = plt.bar(labels, times, color=colors, alpha=0.8)
        plt.ylabel('Execution Time (seconds)', fontweight='bold')
        plt.title(f'Performance: Before vs After Optimization\n{improvement:.1f}% Improvement - {rating}',
                  fontweight='bold')

        # Add value labels
        for bar, time_val in zip(bars, times):
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                     f'{time_val:.3f}s', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        plt.show()

    # Cache the result
    query_cache[query] = result
    return result


# 🧹 STEP 2: DROP EXISTING INDEXES TO SIMULATE UNOPTIMIZED DATABASE
print("\n" + "🧹" * 20)
print("🧹 STEP 2: DROPPING EXISTING INDEXES")
print("🧹" * 20)

print("Clearing all existing indexes to simulate unoptimized database...")
try:
    with conn.cursor() as cursor:
        # Get all indexes except PRIMARY
        cursor.execute("""
                       SELECT INDEX_NAME
                       FROM information_schema.STATISTICS
                       WHERE TABLE_SCHEMA = 'test_autoopt'
                         AND TABLE_NAME = 'sales'
                         AND INDEX_NAME != 'PRIMARY'
                       """)
        indexes_to_drop = [row[0] for row in cursor.fetchall()]

        if indexes_to_drop:
            print(f"🗑️  Dropping {len(indexes_to_drop)} existing indexes: {', '.join(indexes_to_drop)}")
            for index_name in indexes_to_drop:
                cursor.execute(f"ALTER TABLE sales DROP INDEX IF EXISTS `{index_name}`")
            conn.commit()
            print("✅ All existing indexes removed!")
        else:
            print("✅ No existing indexes found (perfect for demo!)")

except Exception as e:
    print(f"⚠️ Could not drop indexes: {e}")
    print("Continuing with demo...")

# DEMO 1: Slow query without optimization
print("\n" + "🔍" * 20)
print("🔍 DEMO 1: INTELLIGENT QUERY ANALYSIS")
print("🔍" * 20)

# 🐢 STEP 3: ADAPTIVE QUERY THAT SCALES ACROSS TABLE SIZES
query1 = """
         SELECT category, region, COUNT(*) AS num_orders, SUM(amount) AS total_sales
         FROM sales
         WHERE order_date BETWEEN '2023-01-01' AND '2025-10-01'
           AND amount > 200
         GROUP BY category, region
         ORDER BY total_sales DESC LIMIT 20; \
         """

result1 = run_optimizer_demo(conn, query1, "Smart analysis of aggregation query", auto_apply=False)

# DEMO 2: Apply optimizations and see improvement
print("\n" + "⚡" * 20)
print("⚡ DEMO 2: ADAPTIVE OPTIMIZATION APPLICATION")
print("⚡" * 20)

# ⚡ STEP 4: APPLY OPTIMIZATIONS WITH INTELLIGENT STRATEGY
result2 = run_optimizer_demo(conn, query1, "Applying intelligent optimizations", auto_apply=True)

# DEMO 3: Different query patterns
print("\n" + "📊" * 20)
print("📊 DEMO 3: MULTI-PATTERN QUERY ANALYSIS")
print("📊" * 20)

query3 = """
         SELECT category, \
                region, \
                AVG(amount) as avg_amount, \
                COUNT(*)    as order_count, \
                SUM(amount) as total_revenue
         FROM sales
         WHERE order_date >= '2023-01-01'
           AND amount > 100
           AND category IN ('Electronics', 'Clothing')
         GROUP BY category, region
         ORDER BY avg_amount DESC LIMIT 15 \
         """

result3 = run_optimizer_demo(conn, query3, "Complex multi-filter aggregation query", auto_apply=False)

# DEMO 4: Join query for advanced optimization
print("\n" + "🔄" * 20)
print("🔄 DEMO 4: JOIN QUERY OPTIMIZATION")
print("🔄" * 20)

query4 = """
         SELECT p.category, \
                u.region, \
                COUNT(*)      as total_orders, \
                AVG(s.amount) as avg_order_value
         FROM sales s
                  JOIN products p ON s.product_id = p.product_id
                  JOIN users u ON s.user_id = u.user_id
         WHERE s.order_date BETWEEN '2023-01-01' AND '2024-01-01'
           AND p.price > 100
         GROUP BY p.category, u.region
         ORDER BY total_orders DESC LIMIT 10; \
         """

result4 = run_optimizer_demo(conn, query4, "Multi-table join optimization", auto_apply=False)

# DEMO 5: Check created indexes
print("\n" + "🗂️" * 20)
print("🗂️ DEMO 5: INTELLIGENT INDEX MANAGEMENT")
print("🗂️" * 20)

print("📊 Indexes created by smart auto-optimizer:")
indexes = pd.read_sql("""
                      SELECT TABLE_NAME,
                             INDEX_NAME,
                             COLUMN_NAME,
                             SEQ_IN_INDEX,
                             INDEX_TYPE,
                             CASE
                                 WHEN INDEX_NAME = 'PRIMARY' THEN 'System'
                                 WHEN NON_UNIQUE = 0 THEN 'Unique'
                                 ELSE 'Performance'
                                 END as index_purpose
                      FROM information_schema.STATISTICS
                      WHERE TABLE_SCHEMA = 'test_autoopt'
                        AND TABLE_NAME = 'sales'
                      ORDER BY INDEX_NAME, SEQ_IN_INDEX
                      """, conn)

if indexes.empty:
    print("❌ No indexes created yet.")
    print("💡 Run a query with auto_apply=True to create indexes!")
else:
    print(f"✅ Found {len(indexes)} intelligently created indexes:")
    display(indexes)

# DEMO 6: Performance comparison
print("\n" + "📈" * 20)
print("📈 DEMO 6: ADAPTIVE PERFORMANCE COMPARISON")
print("📈" * 20)

# 📈 STEP 5: COMPARE BEFORE/AFTER FOR DRAMATIC RESULTS
print("🔄 Running original query again to measure improvement...")
result_final = optimize_once(conn, query1, auto_apply=False, verbose=False)

print("📊 FINAL PERFORMANCE COMPARISON:")
print(f"🕒 Initial time: {result1['before_time']:.3f} seconds")
print(f"⚡ Final time:   {result_final['before_time']:.3f} seconds")

improvement = ((result1['before_time'] - result_final['before_time']) / result1['before_time']) * 100

if improvement > 0:
    print(f"🚀 OVERALL IMPROVEMENT: {improvement:.1f}% faster!")

    # Performance rating
    if improvement > 90:
        rating = "🏆 PHENOMENAL!"
    elif improvement > 70:
        rating = "🎯 EXCELLENT!"
    elif improvement > 50:
        rating = "⭐ GREAT!"
    else:
        rating = "👍 GOOD!"

    print(f"📊 PERFORMANCE RATING: {rating}")

    # Final visualization
    plt.figure(figsize=(10, 6))
    times = [result1['before_time'], result_final['before_time']]
    labels = ['Before\nOptimization', 'After\nOptimization']
    colors = ['#ff6b6b', '#51cf66']

    bars = plt.bar(labels, times, color=colors, alpha=0.8, width=0.6)
    plt.ylabel('Execution Time (seconds)', fontweight='bold')
    plt.title(f'MariaDB Auto-Optimizer: {improvement:.1f}% Performance Improvement\nIntelligent Adaptive Optimization',
              fontsize=14, fontweight='bold', pad=20)

    # Add value labels
    for bar, time_val in zip(bars, times):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f'{time_val:.3f}s', ha='center', va='bottom', fontweight='bold', fontsize=12)

    # Add improvement annotation
    plt.annotate(f'{improvement:.1f}% Faster!\n{rating}',
                 xy=(1, result_final['before_time']),
                 xytext=(1.3, result_final['before_time'] + (result1['before_time'] - result_final['before_time']) / 2),
                 arrowprops=dict(arrowstyle='->', color='green', lw=2),
                 fontsize=12, fontweight='bold', color='green',
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.7))

    plt.tight_layout()
    plt.show()
else:
    print("ℹ️ No significant improvement detected.")
    print("💡 The optimizer determined indexes weren't needed for this table size/query")

# Show final database stats
print("\n📊 FINAL DATABASE STATISTICS:")
final_stats = pd.read_sql("""
                          SELECT (SELECT COUNT(*) FROM sales) as total_rows,
                                 (SELECT COUNT(*)
                                  FROM information_schema.STATISTICS
                                  WHERE TABLE_SCHEMA = 'test_autoopt'
                                    AND TABLE_NAME = 'sales') as total_indexes,
                                 (SELECT DATA_LENGTH + INDEX_LENGTH
                                  FROM information_schema.TABLES
                                  WHERE TABLE_SCHEMA = 'test_autoopt'
                                    AND TABLE_NAME = 'sales') as total_size_bytes,
                                 (SELECT ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2)
                                  FROM information_schema.TABLES
                                  WHERE TABLE_SCHEMA = 'test_autoopt'
                                    AND TABLE_NAME = 'sales') as total_size_mb
                          """, conn)
display(final_stats)

# Show optimization summary
print("\n🎯 OPTIMIZATION STRATEGY SUMMARY:")
size_label, rows = detect_table_size(conn)
print(f"📊 Final Table Size: {rows:,} rows ({size_label})")
print(f"💾 Query Cache: {len(query_cache)} queries cached")
print(f"⚡ Performance Improvement: {improvement:.1f}% faster")

# Close database connection
conn.close()
print("✅ Database connection closed.")
print("\n🎊 INTELLIGENT DEMO COMPLETED SUCCESSFULLY!")
print("🎉 Thank you for using MariaDB Auto-Optimizer!")
print("🤖 Your queries are now intelligently optimized! 🚀")