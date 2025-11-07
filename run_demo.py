# Install required packages
import subprocess
import sys


def install_packages():
    packages = ['pandas', 'sqlparse', 'pymysql', 'matplotlib', 'seaborn', 'numpy']
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


install_packages()

# Suppress pandas warnings for DB-API connections
import warnings

warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy connectable.*')

print("✅ Packages installed and warnings suppressed!")

# Import the optimizer and required libraries
import os
import time
import json
import hashlib
import statistics
import re

sys.path.append('..')  # Add parent directory to path

try:
    from mariadb_autoopt.connector import AutoOptimizer, OptimizationResult

    print("✅ MariaDB Auto-Optimizer Connector imported successfully!")
except ImportError as e:
    print(f"❌ Could not import mariadb_autoopt: {e}")
    print("📦 Make sure the package is installed and path is correct")

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

print("✅ Libraries imported successfully!")


# ---------------------------------------------
# 🔹 ENHANCED VISUALIZATION FUNCTIONS
# ---------------------------------------------

def create_statistical_comparison(before_stats, after_stats, improvement, rating, improvement_text):
    """Create visualization with statistical comparison"""
    plt.figure(figsize=(12, 6))

    # Before optimization box plot
    plt.subplot(1, 2, 1)
    bp_before = plt.boxplot(before_stats['times'], positions=[1], widths=0.6, patch_artist=True)
    plt.setp(bp_before['boxes'], facecolor='#ff6b6b', alpha=0.7)
    plt.setp(bp_before['medians'], color='red', linewidth=2)

    # After optimization box plot
    bp_after = plt.boxplot(after_stats['times'], positions=[2], widths=0.6, patch_artist=True)
    plt.setp(bp_after['boxes'], facecolor='#51cf66', alpha=0.7)
    plt.setp(bp_after['medians'], color='darkgreen', linewidth=2)

    plt.xticks([1, 2], ['Before\nOptimization', 'After\nOptimization'])
    plt.ylabel('Execution Time (seconds)', fontweight='bold')
    plt.title('Statistical Performance Comparison\n(Box plots show 3 runs each)', fontweight='bold')
    plt.grid(True, alpha=0.3)

    # Add individual data points
    for i, time_val in enumerate(before_stats['times']):
        plt.plot(1 + np.random.normal(0, 0.05), time_val, 'ro', alpha=0.6)
    for i, time_val in enumerate(after_stats['times']):
        plt.plot(2 + np.random.normal(0, 0.05), time_val, 'go', alpha=0.6)

    # Improvement bar chart
    plt.subplot(1, 2, 2)
    times = [before_stats['median'], after_stats['median']]
    labels = ['Before\n(median)', 'After\n(median)']

    # Use green if faster, red if slower
    if improvement > 0:
        colors = ['#ff6b6b', '#51cf66']
    else:
        colors = ['#ff6b6b', '#ff9999']

    bars = plt.bar(labels, times, color=colors, alpha=0.8, width=0.6)
    plt.ylabel('Execution Time (seconds)', fontweight='bold')
    plt.title(f'Median Performance: {improvement_text}\n{rating}', fontweight='bold')

    # Add value labels
    for bar, time_val in zip(bars, times):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f'{time_val:.3f}s', ha='center', va='bottom', fontweight='bold')

    # Add improvement annotation
    if improvement > 0:
        annotation_color = 'green'
    else:
        annotation_color = 'red'

    plt.annotate(f'{improvement_text}!',
                 xy=(1, after_stats['median']),
                 xytext=(1.3, after_stats['median'] + (before_stats['median'] - after_stats['median']) / 2),
                 arrowprops=dict(arrowstyle='->', color=annotation_color, lw=2),
                 fontsize=12, fontweight='bold', color=annotation_color)

    plt.tight_layout()
    plt.show()


def create_performance_summary(results):
    """Create overall performance summary visualization"""
    if not results:
        print("No results to visualize")
        return

    valid_results = [r for r in results if r and r.accepted]

    if not valid_results:
        print("No successful optimizations to visualize")
        return

    # Prepare data for visualization
    query_names = [f"Query {i + 1}" for i in range(len(valid_results))]
    improvements = [r.improvement_percent for r in valid_results]
    before_times = [r.baseline_time for r in valid_results]
    after_times = [r.optimized_time for r in valid_results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Improvement percentages
    colors = ['#51cf66' if imp > 0 else '#ff6b6b' for imp in improvements]
    bars = ax1.bar(query_names, improvements, color=colors, alpha=0.8)
    ax1.set_ylabel('Improvement (%)', fontweight='bold')
    ax1.set_title('Performance Improvement by Query', fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # Add value labels on bars
    for bar, imp in zip(bars, improvements):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2., height + (1 if height >= 0 else -3),
                 f'{imp:.1f}%', ha='center', va='bottom' if height >= 0 else 'top',
                 fontweight='bold', color='black' if abs(height) > 10 else 'white')

    # Execution times comparison
    x = np.arange(len(query_names))
    width = 0.35
    ax2.bar(x - width / 2, before_times, width, label='Before', color='#ff6b6b', alpha=0.8)
    ax2.bar(x + width / 2, after_times, width, label='After', color='#51cf66', alpha=0.8)
    ax2.set_ylabel('Execution Time (seconds)', fontweight='bold')
    ax2.set_title('Execution Time Comparison', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(query_names)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


# ---------------------------------------------
# 🔹 DATASET LOADING FUNCTIONS
# ---------------------------------------------

def load_openflights_dataset(data_path="data/"):
    """Load OpenFlights dataset using pandas"""
    print("📂 Loading OpenFlights dataset files...")

    try:
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

        print("✅ OpenFlights dataset loaded successfully!")
        print(f"   Airports: {len(airports):,} records")
        print(f"   Airlines: {len(airlines):,} records")
        print(f"   Routes: {len(routes):,} records")

        # Convert NaN to None for MySQL compatibility
        print("🔧 Converting NaN values to None for MySQL compatibility...")
        airports = airports.where(pd.notnull(airports), None)
        airlines = airlines.where(pd.notnull(airlines), None)
        routes = routes.where(pd.notnull(routes), None)

        # Additional safe string handling
        airports = airports.astype(object).where(pd.notnull(airports), None)
        airlines = airlines.astype(object).where(pd.notnull(airlines), None)
        routes = routes.astype(object).where(pd.notnull(routes), None)

        print("✅ NaN to None conversion completed!")

        return airports, airlines, routes

    except Exception as e:
        print(f"❌ Error loading OpenFlights dataset: {e}")
        print("📁 Make sure the data files are in the correct path: data/")
        return None, None, None


def create_database_tables(optimizer):
    """Create OpenFlights database tables"""
    print("🗄️ Creating MariaDB tables for OpenFlights...")

    try:
        # Use the optimizer's connection to create tables
        optimizer.run_query("DROP TABLE IF EXISTS routes, airports, airlines")

        # Create airports table
        optimizer.run_query("""
                            CREATE TABLE IF NOT EXISTS airports
                            (
                                airport_id
                                INT
                                PRIMARY
                                KEY,
                                name
                                VARCHAR
                            (
                                255
                            ),
                                city VARCHAR
                            (
                                100
                            ),
                                country VARCHAR
                            (
                                100
                            ),
                                iata VARCHAR
                            (
                                10
                            ),
                                icao VARCHAR
                            (
                                10
                            ),
                                latitude DOUBLE,
                                longitude DOUBLE,
                                altitude INT,
                                timezone FLOAT,
                                dst VARCHAR
                            (
                                10
                            ),
                                tz_database_time_zone VARCHAR
                            (
                                100
                            ),
                                type VARCHAR
                            (
                                50
                            ),
                                source VARCHAR
                            (
                                50
                            )
                                )
                            """)

        # Create airlines table
        optimizer.run_query("""
                            CREATE TABLE IF NOT EXISTS airlines
                            (
                                airline_id
                                INT
                                PRIMARY
                                KEY,
                                name
                                VARCHAR
                            (
                                255
                            ),
                                alias VARCHAR
                            (
                                255
                            ),
                                iata VARCHAR
                            (
                                10
                            ),
                                icao VARCHAR
                            (
                                10
                            ),
                                callsign VARCHAR
                            (
                                255
                            ),
                                country VARCHAR
                            (
                                100
                            ),
                                active VARCHAR
                            (
                                5
                            )
                                )
                            """)

        # Create routes table
        optimizer.run_query("""
                            CREATE TABLE IF NOT EXISTS routes
                            (
                                id
                                INT
                                AUTO_INCREMENT
                                PRIMARY
                                KEY,
                                airline
                                VARCHAR
                            (
                                10
                            ),
                                airline_id INT,
                                source_airport VARCHAR
                            (
                                10
                            ),
                                source_airport_id INT,
                                dest_airport VARCHAR
                            (
                                10
                            ),
                                dest_airport_id INT,
                                codeshare VARCHAR
                            (
                                10
                            ),
                                stops INT,
                                equipment VARCHAR
                            (
                                255
                            )
                                )
                            """)

        print("✅ OpenFlights tables created successfully!")
        return True

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False


def insert_dataframe_to_database(optimizer, df, table_name, batch_size=1000):
    """FIXED: Insert DataFrame data into MariaDB table using direct connection"""
    if df.empty:
        print(f"⚠️ DataFrame for {table_name} is empty")
        return 0

    try:
        total_rows = len(df)
        print(f"📥 Inserting {total_rows:,} rows into {table_name}...")

        # Get column names
        columns = df.columns.tolist()
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)

        # Use the optimizer's direct connection for batch inserts
        conn = optimizer.conn
        inserted_count = 0

        with conn.cursor() as cursor:
            # Batch insert for performance
            for i in range(0, total_rows, batch_size):
                batch = df.iloc[i:i + batch_size]
                batch_data = [tuple(row) for row in batch.itertuples(index=False)]

                # Create insert query for this batch
                insert_sql = f"INSERT IGNORE INTO {table_name} ({column_names}) VALUES ({placeholders})"

                # Execute batch insert with parameterized query
                cursor.executemany(insert_sql, batch_data)
                inserted_count += len(batch_data)

                if i + batch_size < total_rows:
                    print(f"   {min(i + batch_size, total_rows):,}/{total_rows:,} rows inserted...")

            conn.commit()

        print(f"✅ Successfully inserted {inserted_count:,} rows into {table_name}")
        return inserted_count

    except Exception as e:
        print(f"❌ Error inserting data into {table_name}: {e}")
        if 'conn' in locals():
            conn.rollback()
        return 0


def show_database_statistics(optimizer):
    """Show comprehensive database statistics"""
    print("\n📊 OPENFLIGHTS DATABASE STATISTICS:")
    print("=" * 50)

    try:
        # Table sizes
        print("📈 TABLE SIZES:")
        for table in ["airports", "airlines", "routes"]:
            result = optimizer.run_query(f"SELECT COUNT(*) FROM {table}")
            count = result[0][0] if result else 0
            print(f"   {table}: {count:,} rows")

        # Airport statistics
        print("\n🏢 AIRPORT STATISTICS:")
        airport_stats = optimizer.run_query("""
                                            SELECT COUNT(*)                as total_airports,
                                                   COUNT(DISTINCT country) as countries,
                                                   COUNT(DISTINCT city)    as cities
                                            FROM airports
                                            """)
        if airport_stats:
            print(f"   Total Airports: {airport_stats[0][0]:,}")
            print(f"   Countries: {airport_stats[0][1]:,}")
            print(f"   Cities: {airport_stats[0][2]:,}")

        # Airline statistics
        print("\n✈️ AIRLINE STATISTICS:")
        airline_stats = optimizer.run_query("""
                                            SELECT COUNT(*)                                      as total_airlines,
                                                   COUNT(DISTINCT country)                       as countries,
                                                   SUM(CASE WHEN active = 'Y' THEN 1 ELSE 0 END) as active_airlines
                                            FROM airlines
                                            """)
        if airline_stats:
            print(f"   Total Airlines: {airline_stats[0][0]:,}")
            print(f"   Countries: {airline_stats[0][1]:,}")
            print(f"   Active Airlines: {airline_stats[0][2]:,}")

        # Route statistics
        print("\n🛣️ ROUTE STATISTICS:")
        route_stats = optimizer.run_query("""
                                          SELECT COUNT(*)                          as total_routes,
                                                 COUNT(DISTINCT source_airport_id) as source_airports,
                                                 COUNT(DISTINCT dest_airport_id)   as dest_airports,
                                                 AVG(stops)                        as avg_stops,
                                                 COUNT(DISTINCT airline_id)        as airlines
                                          FROM routes
                                          """)
        if route_stats:
            print(f"   Total Routes: {route_stats[0][0]:,}")
            print(f"   Source Airports: {route_stats[0][1]:,}")
            print(f"   Destination Airports: {route_stats[0][2]:,}")
            print(f"   Average Stops: {route_stats[0][3]:.2f}")
            print(f"   Airlines Operating: {route_stats[0][4]:,}")

    except Exception as e:
        print(f"⚠️ Error showing statistics: {e}")


# ---------------------------------------------
# 🔹 DEMO QUERIES (since they might not be in the connector)
# ---------------------------------------------

DEMO_QUERIES = {
    "Complex Aggregation": """
                           SELECT a.country,
                                  a.city,
                                  COUNT(*)                     as total_routes,
                                  COUNT(DISTINCT r.airline_id) as unique_airlines,
                                  AVG(r.stops)                 as avg_stops
                           FROM routes r
                                    JOIN airports a ON r.source_airport_id = a.airport_id
                                    JOIN airlines al ON r.airline_id = al.airline_id
                           WHERE a.country IN ('United States', 'China', 'Germany', 'United Kingdom', 'France')
                             AND al.active = 'Y'
                             AND r.stops <= 2
                           GROUP BY a.country, a.city
                           HAVING total_routes > 5
                           ORDER BY total_routes DESC LIMIT 50
                           """,

    "Large Dataset Analysis": """
                              SELECT al.name                               as airline_name,
                                     al.country,
                                     COUNT(*)                              as total_routes,
                                     (SELECT COUNT(*)
                                      FROM routes r2
                                      WHERE r2.airline_id = al.airline_id
                                        AND r2.stops = 0)                  as direct_routes,
                                     (SELECT COUNT(DISTINCT r3.dest_airport_id)
                                      FROM routes r3
                                      WHERE r3.airline_id = al.airline_id) as unique_destinations
                              FROM routes r
                                       JOIN airlines al ON r.airline_id = al.airline_id
                              WHERE al.active = 'Y'
                              GROUP BY al.airline_id, al.name, al.country
                              HAVING total_routes > 20
                              ORDER BY total_routes DESC LIMIT 30
                              """,

    "Cross-Table Analysis": """
                            SELECT src.country                  as source_country,
                                   dest.country                 as dest_country,
                                   COUNT(*)                     as route_count,
                                   COUNT(DISTINCT r.airline_id) as airlines_operating,
                                   MIN(r.stops)                 as min_stops,
                                   MAX(r.stops)                 as max_stops
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
                                LIMIT 25
                            """
}


# ---------------------------------------------
# 🔹 MAIN DEMO EXECUTION
# ---------------------------------------------

def run_complete_demo():
    """Run the complete MariaDB Auto-Optimizer demo"""
    print("🚀 MARIA DB AUTO-OPTIMIZER - OPENFLIGHTS REAL-WORLD DEMO")
    print("=" * 60)

    # Initialize the AutoOptimizer
    print("\n🔌 INITIALIZING AUTO-OPTIMIZER CONNECTOR...")
    try:
        optimizer = AutoOptimizer(
            host='localhost',
            user='autoopt_user',
            password='rn8205',
            database='test_autoopt',
            port=3306
        )
        print("✅ AutoOptimizer initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize AutoOptimizer: {e}")
        return

    # Step 1: Load dataset
    print("\n" + "=" * 50)
    print("STEP 1: LOADING OPENFLIGHTS DATASET")
    print("=" * 50)

    airports, airlines, routes = load_openflights_dataset("data/")
    if airports is None:
        print("❌ Cannot continue without dataset")
        return

    # Show sample data
    print("\n📋 SAMPLE DATA PREVIEW:")
    print("Airports:")
    print(airports.head(2))
    print("\nAirlines:")
    print(airlines.head(2))
    print("\nRoutes:")
    print(routes.head(2))

    # Step 2: Create database tables
    print("\n" + "=" * 50)
    print("STEP 2: CREATING DATABASE TABLES")
    print("=" * 50)

    if not create_database_tables(optimizer):
        print("❌ Cannot continue without database tables")
        return

    # Step 3: Insert data
    print("\n" + "=" * 50)
    print("STEP 3: INSERTING DATA INTO DATABASE")
    print("=" * 50)

    print("🗂️ Inserting OpenFlights data into MariaDB...")
    airports_inserted = insert_dataframe_to_database(optimizer, airports, "airports")
    airlines_inserted = insert_dataframe_to_database(optimizer, airlines, "airlines")
    routes_inserted = insert_dataframe_to_database(optimizer, routes, "routes")

    print(f"\n✅ DATA INSERTION SUMMARY:")
    print(f"   Airports: {airports_inserted:,} rows")
    print(f"   Airlines: {airlines_inserted:,} rows")
    print(f"   Routes: {routes_inserted:,} rows")

    # Show database statistics
    show_database_statistics(optimizer)

    # Step 4: Run optimization demos
    print("\n" + "=" * 50)
    print("STEP 4: RUNNING OPTIMIZATION DEMOS")
    print("=" * 50)

    demo_results = []

    # Demo 1: Complex aggregation with multiple joins
    print("\n🔍 DEMO 1: COMPLEX AGGREGATION WITH MULTIPLE JOINS")
    print("-" * 50)

    query1 = DEMO_QUERIES["Complex Aggregation"]
    print(f"📝 Query: {query1[:100]}...")

    try:
        result1 = optimizer.optimize_query(query1, improvement_threshold=0.10)
        demo_results.append(result1)

        print(f"✅ Baseline: {result1.baseline_time:.3f}s")
        print(f"✅ Optimized: {result1.optimized_time:.3f}s")
        print(f"📈 Improvement: {result1.improvement_percent:.1f}%")
        print(f"🔧 Indexes created: {len(result1.created_indexes)}")
        print(f"🎯 Accepted: {result1.accepted}")

        # Create visualization for this query
        create_statistical_comparison(
            result1.baseline_stats,
            result1.optimized_stats,
            result1.improvement_percent,
            "ACCEPTED" if result1.accepted else "REJECTED",
            f"{result1.improvement_percent:.1f}% faster"
        )

    except Exception as e:
        print(f"❌ Demo 1 failed: {e}")
        demo_results.append(None)

    # Demo 2: Large dataset analysis with subquery
    print("\n🔍 DEMO 2: LARGE DATASET ANALYSIS WITH SUBQUERY")
    print("-" * 50)

    query2 = DEMO_QUERIES["Large Dataset Analysis"]
    print(f"📝 Query: {query2[:100]}...")

    try:
        result2 = optimizer.optimize_query(query2, improvement_threshold=0.10)
        demo_results.append(result2)

        print(f"✅ Baseline: {result2.baseline_time:.3f}s")
        print(f"✅ Optimized: {result2.optimized_time:.3f}s")
        print(f"📈 Improvement: {result2.improvement_percent:.1f}%")
        print(f"🔧 Indexes created: {len(result2.created_indexes)}")
        print(f"🎯 Accepted: {result2.accepted}")

        # Create visualization for this query
        create_statistical_comparison(
            result2.baseline_stats,
            result2.optimized_stats,
            result2.improvement_percent,
            "ACCEPTED" if result2.accepted else "REJECTED",
            f"{result2.improvement_percent:.1f}% faster"
        )

    except Exception as e:
        print(f"❌ Demo 2 failed: {e}")
        demo_results.append(None)

    # Demo 3: Cross-table analysis with complex filtering
    print("\n🔍 DEMO 3: CROSS-TABLE ANALYSIS WITH COMPLEX FILTERING")
    print("-" * 50)

    query3 = DEMO_QUERIES["Cross-Table Analysis"]
    print(f"📝 Query: {query3[:100]}...")

    try:
        result3 = optimizer.optimize_query(query3, improvement_threshold=0.10)
        demo_results.append(result3)

        print(f"✅ Baseline: {result3.baseline_time:.3f}s")
        print(f"✅ Optimized: {result3.optimized_time:.3f}s")
        print(f"📈 Improvement: {result3.improvement_percent:.1f}%")
        print(f"🔧 Indexes created: {len(result3.created_indexes)}")
        print(f"🎯 Accepted: {result3.accepted}")

        # Create visualization for this query
        create_statistical_comparison(
            result3.baseline_stats,
            result3.optimized_stats,
            result3.improvement_percent,
            "ACCEPTED" if result3.accepted else "REJECTED",
            f"{result3.improvement_percent:.1f}% faster"
        )

    except Exception as e:
        print(f"❌ Demo 3 failed: {e}")
        demo_results.append(None)

    # Step 5: Show optimization summary
    print("\n" + "=" * 50)
    print("STEP 5: OPTIMIZATION SUMMARY")
    print("=" * 50)

    # Show created indexes
    print("\n🔧 INTELLIGENTLY CREATED INDEXES:")
    try:
        # Use direct SQL to get indexes since get_current_indexes might not be implemented
        index_query = """
                      SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX
                      FROM information_schema.STATISTICS
                      WHERE TABLE_SCHEMA = 'test_autoopt'
                        AND TABLE_NAME IN ('routes', 'airports', 'airlines')
                        AND INDEX_NAME != 'PRIMARY'
                      ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX \
                      """
        current_indexes = optimizer.run_query(index_query)
        if not current_indexes:
            print("   No indexes were kept (all below improvement threshold)")
        else:
            print(f"   Found {len(current_indexes)} optimized indexes:")
            for idx in current_indexes:
                print(f"     {idx[0]}.{idx[1]} on {idx[2]} (position: {idx[3]})")
    except Exception as e:
        print(f"⚠️ Could not fetch indexes: {e}")

    # Calculate overall performance
    valid_results = [r for r in demo_results if r and r.accepted]

    if valid_results:
        total_improvement = sum(r.improvement_percent for r in valid_results)
        avg_improvement = total_improvement / len(valid_results)

        print(f"\n📊 OVERALL OPTIMIZATION RESULTS:")
        print(f"   • Successful optimizations: {len(valid_results)}/{len(demo_results)}")
        print(f"   • Average improvement: {avg_improvement:.1f}%")

        # Performance rating
        if avg_improvement > 50:
            rating = "🏆 PHENOMENAL!"
        elif avg_improvement > 30:
            rating = "🎯 EXCELLENT!"
        elif avg_improvement > 15:
            rating = "⭐ GREAT!"
        elif avg_improvement > 5:
            rating = "👍 GOOD!"
        else:
            rating = "⚠️ NEEDS WORK"

        print(f"   • Performance Rating: {rating}")

        # Show individual results
        print("\n📈 INDIVIDUAL QUERY RESULTS:")
        for i, result in enumerate(demo_results, 1):
            if result:
                status = "ACCEPTED" if result.accepted else "REJECTED (below threshold)"
                print(f"   Query {i}: {result.improvement_percent:.1f}% improvement - {status}")
            else:
                print(f"   Query {i}: FAILED")

        # Create overall performance summary visualization
        create_performance_summary(demo_results)

    else:
        print("\n⚠️ No successful optimizations to compare")
        print("   All queries were either too fast or optimizations didn't meet threshold")

    # Final database statistics
    print("\n" + "=" * 50)
    print("FINAL DATABASE STATISTICS")
    print("=" * 50)

    try:
        final_stats = optimizer.run_query("""
                                          SELECT (SELECT COUNT(*) FROM routes)                            as total_routes,
                                                 (SELECT COUNT(*) FROM airports)                          as total_airports,
                                                 (SELECT COUNT(*) FROM airlines)                          as total_airlines,
                                                 (SELECT COUNT(*)
                                                  FROM information_schema.STATISTICS
                                                  WHERE TABLE_SCHEMA = 'test_autoopt'
                                                    AND TABLE_NAME IN ('routes', 'airports', 'airlines')) as total_indexes
                                          """)

        if final_stats:
            stats = final_stats[0]
            print(f"📈 Final Database State:")
            print(f"   • Total Routes: {stats[0]:,}")
            print(f"   • Total Airports: {stats[1]:,}")
            print(f"   • Total Airlines: {stats[2]:,}")
            print(f"   • Total Indexes: {stats[3]}")

    except Exception as e:
        print(f"⚠️ Could not fetch final statistics: {e}")

    # Show data volume check
    print("\n🔍 DATA VOLUME ANALYSIS:")
    try:
        for table in ["routes", "airports", "airlines"]:
            result = optimizer.run_query(f"SELECT COUNT(*) FROM {table}")
            count = result[0][0] if result else 0
            size_category = "LARGE" if count > 100000 else "MEDIUM" if count > 10000 else "SMALL"
            print(f"   {table}: {count:,} rows ({size_category})")
    except Exception as e:
        print(f"⚠️ Could not analyze data volume: {e}")

    # Cleanup and close
    print("\n🧹 CLEANING UP...")
    try:
        # Clean up all created indexes using direct SQL
        for table in ["routes", "airports", "airlines"]:
            index_query = f"""
                SELECT INDEX_NAME
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = 'test_autoopt'
                AND TABLE_NAME = '{table}'
                AND INDEX_NAME != 'PRIMARY'
            """
            indexes = optimizer.run_query(index_query)
            if indexes:
                for index in indexes:
                    index_name = index[0]
                    try:
                        optimizer.run_query(f"ALTER TABLE {table} DROP INDEX IF EXISTS `{index_name}`")
                        print(f"   Dropped index: {table}.{index_name}")
                    except Exception as e:
                        print(f"   ⚠️ Could not drop index {index_name}: {e}")

        optimizer.close()
        print("✅ Database connection closed")

    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

    print("\n🎉 OPENFLIGHTS REAL-WORLD DEMO COMPLETED SUCCESSFULLY!")
    print("🚀 Thank you for using MariaDB Auto-Optimizer Connector!")
    print("💡 Now with fixed data insertion and enhanced visualizations!")


# ---------------------------------------------
# 🔹 MAIN EXECUTION
# ---------------------------------------------

if __name__ == "__main__":
    # Run the complete demo
    run_complete_demo()
