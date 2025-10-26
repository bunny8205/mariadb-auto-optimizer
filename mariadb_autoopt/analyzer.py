import pandas as pd
import sqlparse
import re
import warnings


def run_explain(conn, query):
    """Run EXPLAIN (or EXPLAIN ANALYZE if available) and return results as a DataFrame."""
    # Try EXPLAIN ANALYZE then fallback to EXPLAIN
    last_err = None
    for prefix in ("EXPLAIN ANALYZE ", "EXPLAIN "):
        try:
            q = prefix + query
            # Suppress pandas warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy connectable.*')
                df = pd.read_sql_query(q, conn)
            return df, prefix.strip()
        except Exception as e:
            last_err = e
    raise last_err


# Rest of the file remains the same...
def parse_tables_from_query(query):
    """Extract table names from SQL query."""
    parsed = sqlparse.parse(query)[0]
    tables = set()
    for token in parsed.tokens:
        if token.ttype is None and token.value:
            txt = token.value.upper()
            # Look for table names after FROM/JOIN
            for m in re.finditer(r'\b(FROM|JOIN)\s+([`"\']?)(\w+)\2', txt):
                tables.add(m.group(3))
    return list(tables)


def analyze_explain_df(explain_df, explain_kind):
    """Return list of issues. explain_df is output of EXPLAIN/EXPLAIN ANALYZE as DataFrame."""
    issues = []

    if explain_df is None or explain_df.empty:
        return ["No EXPLAIN output available"]

    # Common column names in MariaDB EXPLAIN
    for _, row in explain_df.iterrows():
        # Check 'type' column (access type)
        access_type = row.get('type') or row.get('select_type') or ''
        extra = row.get('Extra') or row.get('extra') or ''
        rows = row.get('rows') or row.get('Rows') or 0

        access_type = str(access_type).upper()
        extra = str(extra).upper()

        # Detect full table scans
        if access_type == 'ALL':
            issues.append("Full table scan detected (type=ALL). Consider adding indexes on WHERE/JOIN columns.")

        # Detect filesort
        if 'FILESORT' in extra:
            issues.append("Filesort detected - ORDER BY may need an index.")

        # Detect temporary tables
        if 'USING TEMPORARY' in extra:
            issues.append("Temporary table detected - GROUP BY may need optimization.")

        # Detect no matching rows
        if 'IMPOSSIBLE WHERE' in extra:
            issues.append("Impossible WHERE condition detected.")

    return list(dict.fromkeys(issues))  # Remove duplicates