"""
MariaDB Auto-Optimizer Connector
Reusable library for adaptive query optimization
"""

import pymysql
import time
import re
import pandas as pd
import warnings
from contextlib import contextmanager
from functools import lru_cache
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import threading

# Import your existing modules
from . import optimizer
from . import analyzer
from . import core

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
    baseline_stats: Dict[str, float]
    optimized_stats: Dict[str, float]
    query: str


@dataclass
class AppConfig:
    """Application configuration"""
    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str
    optimization_threshold: float = 0.05
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
        """Get database connection with pooling"""
        if not hasattr(self._connection_local, 'conn') or not self._connection_local.conn.open:
            self._connection_local.conn = self._create_connection()
        try:
            yield self._connection_local.conn
        except Exception:
            self._connection_local.conn = None
            raise

    def _create_connection(self):
        """Create new database connection"""
        try:
            conn = pymysql.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                user=self.config.db_user,
                password=self.config.db_pass,
                database=self.config.db_name,
                ssl={'ssl': {}},
                connect_timeout=10,
                autocommit=True
            )
            return conn
        except Exception as e:
            raise ConnectionError(f"Database connection failed: {e}")

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
        """Clear database cache for consistent benchmarking"""
        with self._get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("FLUSH TABLES")
                    cursor.execute("RESET QUERY CACHE")
                return True
            except Exception as e:
                warnings.warn(f"Could not clear cache: {e}")
                return False

    def run_query_with_timing(self, query: str, num_runs: int = None) -> Dict[str, Any]:
        """Run query multiple times and return statistical results"""
        if num_runs is None:
            num_runs = self.config.num_runs

        times = []

        with self._get_connection() as conn:
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
                    raise Exception(f"Error in run {i + 1}: {e}")

        if times:
            return {
                'times': times,
                'median': sorted(times)[len(times) // 2],
                'mean': sum(times) / len(times),
                'min': min(times),
                'max': max(times)
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
        """Validate if optimization actually helped"""
        if threshold is None:
            threshold = self.config.improvement_threshold

        if optimized_time >= baseline_time:
            return False
        improvement = (baseline_time - optimized_time) / baseline_time
        return improvement >= threshold

    def drop_all_indexes(self) -> bool:
        """Drop all existing indexes to simulate unoptimized database - IDENTICAL TO STREAMLIT"""
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
                            print(f" No existing indexes found on {table}")

                return True

            except Exception as e:
                raise Exception(f"Could not drop indexes: {e}")

    def create_smart_indexes_for_query(self, query: str) -> List[str]:
        """EXACT SAME IMPLEMENTATION AS STREAMLIT APP"""
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
            print(f"🔍 Found indexable columns: {actual_columns}")

        # Group by table and create indexes (matching your local strategy)
        columns_by_table = {}
        for table, column in actual_columns:
            if table not in columns_by_table:
                columns_by_table[table] = []
            if column not in columns_by_table[table]:
                columns_by_table[table].append(column)

        # Create indexes matching your successful local strategy
        with self._get_connection() as conn:
            for table, columns in columns_by_table.items():
                if not columns:
                    continue

                print(f"**Creating indexes for table `{table}`:**")

                # Create composite indexes for 2+ columns (like local demo)
                if len(columns) >= 2:
                    idx_name = f"idx_{table}_composite_{'_'.join(columns[:2])}"
                    composite_cols = ', '.join(columns[:2])
                    sql = f"CREATE INDEX {idx_name} ON {table} ({composite_cols})"

                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(sql)
                        created_indexes.append(idx_name)
                        print(f"✓ Composite index: `{idx_name}`")
                    except Exception as e:
                        if "Duplicate key name" not in str(e):
                            warnings.warn(f"Failed to create index {idx_name}: {e}")

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
                            print(f"✓ Single-column index: `{idx_name}`")
                        except Exception as e:
                            if "Duplicate key name" not in str(e):
                                warnings.warn(f"Failed to create index {idx_name}: {e}")

        return created_indexes

    def optimize_query(self, query: str, improvement_threshold: float = None) -> OptimizationResult:
        """
        Main optimization method - automatically optimizes a query
        IDENTICAL LOGIC TO STREAMLIT APP

        Args:
            query: SQL query to optimize
            improvement_threshold: Minimum improvement required (default: 0.10 = 10%)

        Returns:
            OptimizationResult with performance metrics and created indexes
        """
        if improvement_threshold is None:
            improvement_threshold = self.config.improvement_threshold

        print("🚀 Starting query optimization...")

        # Step 1: Drop all existing indexes
        print("🔧 Step 1: Preparing database (dropping existing indexes)...")
        self.drop_all_indexes()

        # Step 2: Baseline performance
        print("📊 Step 2: Measuring baseline performance...")
        self.clear_database_cache()
        baseline_stats = self.run_query_with_timing(query)

        # Step 3: Create indexes
        print("🔧 Step 3: Creating optimized indexes...")
        created_indexes = self.create_smart_indexes_for_query(query)

        # Step 4: Optimized performance
        print("📊 Step 4: Measuring optimized performance...")
        self.clear_database_cache()
        optimized_stats = self.run_query_with_timing(query)

        # Step 5: Calculate improvement
        improvement_percent = ((baseline_stats['median'] - optimized_stats['median']) / baseline_stats['median']) * 100
        accepted = self.validate_improvement(baseline_stats['median'], optimized_stats['median'], improvement_threshold)

        print("✅ Optimization complete!")

        return OptimizationResult(
            baseline_time=baseline_stats['median'],
            optimized_time=optimized_stats['median'],
            improvement_percent=improvement_percent,
            created_indexes=created_indexes,
            accepted=accepted,
            baseline_stats=baseline_stats,
            optimized_stats=optimized_stats,
            query=query
        )

    def cleanup_indexes(self, index_list: List[str]) -> None:
        """Clean up created indexes - IDENTICAL TO STREAMLIT"""
        if not index_list:
            return

        with self._get_connection() as conn:
            for index_spec in index_list:
                try:
                    if "idx_" in index_spec:
                        parts = index_spec.split('_')
                        table = parts[1] if len(parts) > 1 else None
                        if table:
                            with conn.cursor() as cursor:
                                cursor.execute(f"ALTER TABLE {table} DROP INDEX IF EXISTS `{index_spec}`")
                            print(f"Cleaned up: {index_spec}")
                except Exception as e:
                    warnings.warn(f"Failed to clean up {index_spec}: {e}")

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
        """Close connection"""
        if hasattr(self._connection_local, 'conn') and self._connection_local.conn:
            self._connection_local.conn.close()
            self._connection_local.conn = None

    # Demo queries identical to Streamlit app
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