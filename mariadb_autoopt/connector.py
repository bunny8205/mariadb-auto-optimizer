"""
MariaDB Auto-Optimizer Connector
Reusable library for adaptive query optimization
"""

import pymysql
import time
import re
import pandas as pd
import warnings
import statistics
from contextlib import contextmanager
from functools import lru_cache
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import threading

# Suppress pandas warnings
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy connectable.*')


@dataclass
class OptimizationResult:
    """Result of query optimization"""
    baseline_time: float
    optimized_time: float
    improvement_percent: float
    created_indexes: List[str]
    accepted: bool
    baseline_stats: Dict[str, Any]
    optimized_stats: Dict[str, Any]
    query: str


@dataclass
class AppConfig:
    """Application configuration"""
    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str
    optimization_threshold: float = 0.01  # Match run_demo.py
    improvement_threshold: float = 0.10
    num_runs: int = 3


class AutoOptimizer:
    """
    MariaDB Auto-Optimizer Connector

    A reusable library for adaptive query optimization that can be integrated
    into any Python application or used as a standalone optimizer.

    Example:
        >>> from mariadb_autoopt.connector import AutoOptimizer
        >>> opt = AutoOptimizer(host, user, password, database, port)
        >>> result = opt.optimize_query("SELECT * FROM routes WHERE stops > 0")
        >>> print(f"Improvement: {result.improvement_percent:.1f}%")
    """

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        """
        Initialize the MariaDB Auto-Optimizer

        Args:
            host: Database host
            user: Database username
            password: Database password
            database: Database name
            port: Database port (default: 3306)
        """
        self.config = AppConfig(
            db_host=host,
            db_port=port,
            db_user=user,
            db_pass=password,
            db_name=database
        )
        self._connection_local = threading.local()

    @contextmanager
    def _get_connection(self):
        """Get or create a persistent database connection (auto-reconnect safe)."""
        try:
            # Check if connection exists and is open
            if not hasattr(self._connection_local, 'conn') or self._connection_local.conn is None:
                self._connection_local.conn = self._create_connection()
            else:
                try:
                    if not self._connection_local.conn.open:
                        self._connection_local.conn = self._create_connection()
                except Exception:
                    # Handle case where conn is partially closed
                    self._connection_local.conn = self._create_connection()

            conn = self._connection_local.conn
            yield conn

        except Exception as e:
            # Force reconnection next time if this one breaks
            self._connection_local.conn = None
            raise ConnectionError(f"Connection context failed: {e}")

    def _create_connection(self):
        """Create new database connection"""
        try:
            conn = pymysql.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                user=self.config.db_user,
                password=self.config.db_pass,
                database=self.config.db_name,
                connect_timeout=10,
                autocommit=True,
                charset='utf8mb4'
            )
            return conn
        except Exception as e:
            raise ConnectionError(f"Database connection failed: {e}")

    @property
    def conn(self):
        """Direct connection access with automatic recovery."""
        if not hasattr(self._connection_local, 'conn') or not self._connection_local.conn:
            self._connection_local.conn = self._create_connection()
        else:
            try:
                if not self._connection_local.conn.open:
                    self._connection_local.conn = self._create_connection()
            except Exception:
                self._connection_local.conn = self._create_connection()
        return self._connection_local.conn

    def run_query(self, query: str) -> List[Tuple]:
        """
        Execute query and return results

        Args:
            query: SQL query to execute

        Returns:
            List of tuples containing query results
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()

    def explain_query(self, query: str) -> pd.DataFrame:
        """
        Show query execution plan

        Args:
            query: SQL query to explain

        Returns:
            DataFrame with execution plan details
        """
        with self._get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(f"EXPLAIN {query}")
                    result = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return pd.DataFrame(result, columns=columns)
            except Exception as e:
                raise Exception(f"Could not explain query: {e}")

    def clear_database_cache(self) -> bool:
        """Clear database cache for consistent benchmarking - IDENTICAL TO run_demo.py"""
        with self._get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("FLUSH TABLES")
                    cursor.execute("RESET QUERY CACHE")
                return True
            except Exception as e:
                warnings.warn(f"Could not clear cache: {e}")
                return False

    def run_query_multiple_times(self, query: str, num_runs: int = None, clear_cache: bool = False) -> Dict[str, Any]:
        """IDENTICAL TO run_demo.py: Run query multiple times and return statistical results"""
        if num_runs is None:
            num_runs = self.config.num_runs

        times = []

        with self._get_connection() as conn:
            for i in range(num_runs):
                if clear_cache and i == 0:
                    self.clear_database_cache()

                start_time = time.time()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(query)
                        results = cursor.fetchall()
                    end_time = time.time()
                    execution_time = end_time - start_time
                    times.append(execution_time)
                except Exception as e:
                    raise Exception(f"Error in run {i + 1}: {e}")

        if times:
            return {
                'times': times,
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'min': min(times),
                'max': max(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                'rows': len(results) if 'results' in locals() else 0
            }
        return None

    def get_query_time(self, query: str) -> float:
        """Get single query execution time"""
        with self._get_connection() as conn:
            start_time = time.time()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    cursor.fetchall()
                return time.time() - start_time
            except Exception as e:
                raise Exception(f"Error executing query: {e}")

    def should_optimize_query(self, query: str, threshold_seconds: float = None) -> bool:
        """Check if query is slow enough to benefit from optimization"""
        if threshold_seconds is None:
            threshold_seconds = self.config.optimization_threshold

        baseline_time = self.get_query_time(query)
        return baseline_time > threshold_seconds

    def validate_improvement(self, baseline_time: float, optimized_time: float, threshold: float = None) -> bool:
        """Validate if optimization actually helped - IDENTICAL TO run_demo.py"""
        if threshold is None:
            threshold = self.config.improvement_threshold

        if optimized_time >= baseline_time:
            return False  # No improvement or got worse

        improvement = (baseline_time - optimized_time) / baseline_time
        return improvement >= threshold  # At least threshold improvement

    def drop_all_indexes(self) -> bool:
        """Drop all existing indexes to simulate unoptimized database - IDENTICAL TO run_demo.py"""
        with self._get_connection() as conn:
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
                        """, (self.config.db_name, table))
                        indexes_to_drop = [row[0] for row in cursor.fetchall()]

                        if indexes_to_drop:
                            print(f"  Dropping {len(indexes_to_drop)} indexes from {table}: {', '.join(indexes_to_drop)}")
                            for index_name in indexes_to_drop:
                                cursor.execute(f"ALTER TABLE {table} DROP INDEX IF EXISTS `{index_name}`")
                        else:
                            print(f" No existing indexes found on {table} (perfect for demo!)")

                return True

            except Exception as e:
                warnings.warn(f"Could not drop indexes: {e}")
                return False

    def get_actual_columns_from_query(self, query: str) -> List[Tuple[str, str]]:
        """IDENTICAL TO run_demo.py: Enhanced column extraction with table alias resolution"""
        actual_columns = []
        query_lower = query.lower()

        # First, map table aliases to real table names
        table_aliases = {}

        # Pattern to find table aliases: "FROM table alias" or "JOIN table alias"
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

        # Now extract columns with proper table resolution
        column_patterns = [
            r'where\s+(\w+)\.(\w+)\s*[=<>!]',
            r'join\s+\w+\s+on\s+(\w+)\.(\w+)\s*=\s*\w+\.\w+',
            r'group by\s+(\w+)\.(\w+)',
            r'order by\s+(\w+)\.(\w+)',
            r'having\s+\w+\s+[=<>!]\s*\w+\.(\w+)',
            r'select.*?(\w+)\.(\w+)\s+as',
            r'on\s+(\w+)\.(\w+)\s*=\s*\w+\.\w+'
        ]

        for pattern in column_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                table_ref, column = match.groups()

                # Resolve alias to real table name
                actual_table = table_aliases.get(table_ref, table_ref)

                # Only include if it's a real table (not a subquery alias)
                real_tables = ['routes', 'airports', 'airlines', 'r', 'a', 'al', 'src', 'dest']
                if actual_table in real_tables:
                    # Map common aliases to real tables
                    if actual_table == 'r':
                        actual_table = 'routes'
                    elif actual_table == 'a':
                        actual_table = 'airports'
                    elif actual_table == 'al':
                        actual_table = 'airlines'
                    elif actual_table == 'src':
                        actual_table = 'airports'
                    elif actual_table == 'dest':
                        actual_table = 'airports'

                    actual_columns.append((actual_table, column))

        # Remove duplicates and return
        return list(set(actual_columns))

    def create_smart_indexes(self, query: str) -> List[str]:
        """IDENTICAL TO run_demo.py: Create indexes based on actual query patterns with table validation"""
        actual_columns = self.get_actual_columns_from_query(query)
        created_indexes = []

        print(f" Found {len(actual_columns)} relevant columns in query")

        if not actual_columns:
            print("    No indexable columns found in query")
            return created_indexes

        # Group columns by table
        columns_by_table = {}
        for table, column in actual_columns:
            if table not in columns_by_table:
                columns_by_table[table] = []
            if column not in columns_by_table[table]:
                columns_by_table[table].append(column)

        # Validate tables exist and get their actual columns
        valid_tables = {}
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                for table in columns_by_table.keys():
                    try:
                        cursor.execute(f"SHOW COLUMNS FROM {table}")
                        valid_columns = [row[0] for row in cursor.fetchall()]
                        valid_tables[table] = valid_columns
                        print(f"    Table {table} has {len(valid_columns)} columns")
                    except Exception as e:
                        print(f"    Table {table} doesn't exist: {e}")

        # Create strategic indexes only for valid tables/columns
        for table, columns in columns_by_table.items():
            if table not in valid_tables:
                print(f"    Skipping {table} - table not found")
                continue

            valid_columns = [col for col in columns if col in valid_tables[table]]

            if not valid_columns:
                print(f"   No valid columns found for table {table}")
                continue

            print(f"    Creating indexes for {table}: {valid_columns}")

            # Create composite index for multiple columns
            if len(valid_columns) >= 2:
                idx_name = f"idx_{table}_composite_{'_'.join(valid_columns[:2])}"
                composite_cols = ', '.join(valid_columns[:2])
                sql = f"CREATE INDEX {idx_name} ON {table} ({composite_cols})"

                try:
                    with self._get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute(sql)
                    created_indexes.append(idx_name)
                    print(f"    Created composite index: {idx_name}")
                except Exception as e:
                    if "Duplicate key name" not in str(e):
                        print(f"   ️ Failed to create index {idx_name}: {e}")

            # Also create single-column indexes for important columns
            for column in valid_columns:
                if column in ['country', 'city', 'stops', 'active', 'source_airport_id', 'dest_airport_id', 'airline_id']:
                    idx_name = f"idx_{table}_{column}"
                    sql = f"CREATE INDEX {idx_name} ON {table} ({column})"

                    try:
                        with self._get_connection() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute(sql)
                        created_indexes.append(idx_name)
                        print(f"    Created single-column index: {idx_name}")
                    except Exception as e:
                        if "Duplicate key name" not in str(e):
                            print(f"    Failed to create index {idx_name}: {e}")

        return created_indexes

    def enhanced_optimization_strategy(self, query: str) -> str:
        """IDENTICAL TO run_demo.py: Enhanced strategy that focuses on actual performance bottlenecks"""
        size_label, rows = self.detect_table_size("routes")
        query_type = self.detect_query_type(query)
        cost = self.get_query_cost(query)

        print(f"\n Table Size: {rows:,} rows ({size_label})")
        print(f" Query Type: {query_type}")
        print(f" Estimated Query Cost: {cost:.1f}")

        # More conservative strategy
        if size_label == "small" or cost < 50:
            print(" Mode: Analysis Only (query already efficient)")
            return "analyze_only"
        elif query_type == "join" and rows > 10000:
            print(" Mode: Join Optimization (focus on foreign keys)")
            return "join_optimize"
        elif query_type == "aggregation" and "GROUP BY" in query.upper():
            print(" Mode: Aggregation Optimization (group by indexes)")
            return "aggregation_optimize"
        elif cost > 1000:
            print(" Mode: Critical Optimization (high-cost query)")
            return "critical_optimize"
        else:
            print("⚡ Mode: Selective Optimization (targeted indexes)")
            return "selective_optimize"

    def detect_table_size(self, table_name: str = "routes") -> Tuple[str, int]:
        """IDENTICAL TO run_demo.py: Detect total row count and classify table size"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    rows = cursor.fetchone()[0]

            # Dynamic thresholds based on typical performance characteristics
            if rows < 50_000:
                return "small", rows
            elif rows < 500_000:
                return "medium", rows
            else:
                return "large", rows
        except Exception as e:
            print(f" Could not detect table size: {e}")
            return "unknown", 0

    def detect_query_type(self, query: str) -> str:
        """IDENTICAL TO run_demo.py: Infer query type from SQL keywords"""
        q = query.lower()
        if "join" in q:
            return "join"
        elif "group by" in q:
            return "aggregation"
        elif "where" in q:
            return "filter"
        else:
            return "simple"

    def get_query_cost(self, query: str) -> float:
        """IDENTICAL TO run_demo.py: Get query cost from MariaDB's optimizer estimates"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Try to get cost from EXPLAIN FORMAT=JSON
                    cursor.execute(f"EXPLAIN FORMAT=JSON {query}")
                    result = cursor.fetchone()
                    if result and result[0]:
                        import json
                        explain_data = json.loads(result[0])
                        cost = explain_data.get('query_block', {}).get('cost_info', {}).get('query_cost', None)
                        if cost:
                            return float(cost)
        except Exception as e:
            print(f" Could not get query cost: {e}")

        # Fallback: estimate cost based on table size and query complexity
        size_label, rows = self.detect_table_size()
        base_cost = rows / 1000  # Simple heuristic

        # Adjust based on query complexity
        if "join" in query.lower():
            base_cost *= 2
        if "group by" in query.lower():
            base_cost *= 1.5
        if "order by" in query.lower():
            base_cost *= 1.2

        return base_cost

    def optimize_query(self, query: str, improvement_threshold: float = None) -> OptimizationResult:
        """
        Main optimization method - UPDATED TO MATCH run_demo.py LOGIC EXACTLY

        Args:
            query: SQL query to optimize
            improvement_threshold: Minimum improvement required (default: 0.10 = 10%)

        Returns:
            OptimizationResult with performance metrics and created indexes
        """
        if improvement_threshold is None:
            improvement_threshold = self.config.improvement_threshold

        print("🚀 Starting query optimization...")

        # Step 1: Use enhanced strategy (like run_demo.py)
        strategy = self.enhanced_optimization_strategy(query)

        if strategy == "analyze_only":
            print(" Analysis only - no indexes created")
            baseline_stats = self.run_query_multiple_times(query, num_runs=3, clear_cache=True)
            return OptimizationResult(
                baseline_time=baseline_stats['median'],
                optimized_time=baseline_stats['median'],
                improvement_percent=0,
                created_indexes=[],
                accepted=False,
                baseline_stats=baseline_stats,
                optimized_stats=baseline_stats,
                query=query
            )

        # Step 2: Baseline performance with cache clearing
        print("📊 Step 2: Measuring baseline performance...")
        baseline_stats = self.run_query_multiple_times(query, num_runs=3, clear_cache=True)

        # Only optimize if query is slow enough to benefit (adjustable threshold)
        if baseline_stats['median'] < self.config.optimization_threshold:
            print(f"⚡ Query already fast (<{self.config.optimization_threshold}s) - skipping optimization")
            return OptimizationResult(
                baseline_time=baseline_stats['median'],
                optimized_time=baseline_stats['median'],
                improvement_percent=0,
                created_indexes=[],
                accepted=False,
                baseline_stats=baseline_stats,
                optimized_stats=baseline_stats,
                query=query
            )

        print(f" Baseline (median): {baseline_stats['median']:.3f}s")

        # Step 3: Create smart indexes
        print("🔧 Step 3: Creating optimized indexes...")
        created_indexes = self.create_smart_indexes(query)

        if not created_indexes:
            print(" No relevant indexes to create")
            return OptimizationResult(
                baseline_time=baseline_stats['median'],
                optimized_time=baseline_stats['median'],
                improvement_percent=0,
                created_indexes=[],
                accepted=False,
                baseline_stats=baseline_stats,
                optimized_stats=baseline_stats,
                query=query
            )

        # Step 4: Optimized performance with cache clearing
        print("📊 Step 4: Measuring optimized performance...")
        optimized_stats = self.run_query_multiple_times(query, num_runs=3, clear_cache=True)

        print(f" Optimized (median): {optimized_stats['median']:.3f}s")

        # Step 5: Calculate improvement
        improvement_percent = ((baseline_stats['median'] - optimized_stats['median']) / baseline_stats['median']) * 100

        # Validate improvement (identical to run_demo.py)
        accepted = self.validate_improvement(baseline_stats['median'], optimized_stats['median'], improvement_threshold)

        if accepted:
            print(f" VALIDATED: {improvement_percent:.1f}% improvement")
        else:
            print(f"  INSUFFICIENT: {improvement_percent:.1f}% improvement (below threshold)")
            # Roll back indexes
            self.cleanup_indexes(created_indexes)
            created_indexes = []

        print("✅ Optimization complete!")

        return OptimizationResult(
            baseline_time=baseline_stats['median'],
            optimized_time=optimized_stats['median'] if accepted else baseline_stats['median'],
            improvement_percent=improvement_percent if accepted else 0,
            created_indexes=created_indexes,
            accepted=accepted,
            baseline_stats=baseline_stats,
            optimized_stats=optimized_stats,
            query=query
        )

    def cleanup_indexes(self, index_list: List[str]) -> None:
        """Clean up created indexes - IDENTICAL TO run_demo.py"""
        if not index_list:
            return

        print(f"\n🧹 Cleaning up {len(index_list)} indexes...")
        with self._get_connection() as conn:
            for index_spec in index_list:
                try:
                    # Extract table and index name
                    if "idx_" in index_spec:
                        parts = index_spec.split('_')
                        table = parts[1] if len(parts) > 1 else None
                        if table:
                            with conn.cursor() as cursor:
                                cursor.execute(f"ALTER TABLE {table} DROP INDEX IF EXISTS `{index_spec}`")
                            print(f"    Cleaned up: {index_spec}")
                except Exception as e:
                    print(f"   ️ Failed to clean up {index_spec}: {e}")

    @lru_cache(maxsize=32)
    def check_data_volume(self) -> Dict[str, int]:
        """Check if tables have sufficient data for optimization (cached)"""
        table_counts = {}
        with self._get_connection() as conn:
            for table in ["routes", "airports", "airlines"]:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_counts[table] = count
                except Exception as e:
                    raise Exception(f"Error checking {table}: {e}")

        return table_counts

    def get_current_indexes(self) -> pd.DataFrame:
        """Get current database indexes"""
        with self._get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                                   SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX
                                   FROM information_schema.STATISTICS
                                   WHERE TABLE_SCHEMA = %s
                                     AND TABLE_NAME IN ('routes', 'airports', 'airlines')
                                     AND INDEX_NAME != 'PRIMARY'
                                   ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
                                   """, (self.config.db_name,))

                    indexes = cursor.fetchall()
                    return pd.DataFrame(indexes, columns=['Table', 'Index', 'Column', 'Position'])
            except Exception as e:
                raise Exception(f"Error fetching indexes: {e}")

    def close(self):
        """Close connection safely."""
        if hasattr(self._connection_local, 'conn') and self._connection_local.conn:
            try:
                self._connection_local.conn.close()
            except Exception:
                pass
            self._connection_local.conn = None

    # Demo queries identical to run_demo.py
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
