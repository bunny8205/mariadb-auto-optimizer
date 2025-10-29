import re


def suggest_indexes(query):
    """Produce simple index suggestions by looking for WHERE/ON/ORDER BY columns."""
    lower_query = query.lower()
    suggestions = []

    # Extract tables first
    tables = []
    from_match = re.search(r'from\s+([\w`"]+)', lower_query)
    if from_match:
        tables.append(from_match.group(1).strip(' `"'))

    # Look for columns in WHERE clause
    where_pattern = r'where\s+(.+?)(?:\s+group\s+by|\s+order\s+by|\s+limit|$)'
    where_match = re.search(where_pattern, lower_query, re.IGNORECASE | re.DOTALL)

    where_columns = set()
    if where_match:
        where_clause = where_match.group(1)
        # Extract column names from conditions
        col_matches = re.findall(r'([\w`"]+)\s*[=<>]', where_clause)
        where_columns.update([col.strip(' `"') for col in col_matches])

    # Look for JOIN conditions
    join_columns = set()
    join_matches = re.findall(r'join\s+[\w`"]+\s+on\s+([\w`".]+)\s*=', lower_query)
    for match in join_matches:
        join_columns.add(match.strip(' `"'))

    # Look for ORDER BY columns
    order_columns = set()
    order_match = re.search(r'order\s+by\s+(.+?)(?:\s+limit|\s*$)', lower_query, re.IGNORECASE | re.DOTALL)
    if order_match:
        order_clause = order_match.group(1)
        order_cols = re.findall(r'([\w`".]+)(?:\s+asc|\s+desc|,|$)', order_clause)
        order_columns.update([col.strip(' `"') for col in order_cols])

    # Look for GROUP BY columns
    group_columns = set()
    group_match = re.search(r'group\s+by\s+(.+?)(?:\s+order\s+by|\s+having|\s*$)', lower_query,
                            re.IGNORECASE | re.DOTALL)
    if group_match:
        group_clause = group_match.group(1)
        group_cols = re.findall(r'([\w`".]+)(?:\s*,|$)', group_clause)
        group_columns.update([col.strip(' `"') for col in group_cols])

    # Generate suggestions
    all_columns = where_columns | join_columns | order_columns | group_columns

    for col in all_columns:
        if '.' in col:
            table, colname = col.split('.', 1)
        else:
            table = tables[0] if tables else '<table>'
            colname = col

        # Skip if it's clearly not a column (e.g., number, function)
        if colname.isdigit() or '(' in colname or colname in ['null', 'true', 'false']:
            continue

        suggestion = f"CREATE INDEX idx_{table}_{colname.replace('.', '_')} ON {table} ({colname});"
        suggestions.append(suggestion)

    # Suggest composite indexes for WHERE + ORDER BY
    if where_columns and order_columns:
        where_cols_list = list(where_columns)[:2]  # Take up to 2 columns
        order_cols_list = list(order_columns)[:1]  # Take first ORDER BY column

        composite_cols = where_cols_list + order_cols_list
        if len(composite_cols) > 1:
            table = tables[0] if tables else '<table>'
            cols_str = ', '.join(composite_cols)
            suggestion = f"CREATE INDEX idx_{table}_composite ON {table} ({cols_str});"
            suggestions.append(suggestion)

    return suggestions[:5]  # Limit to 5 suggestions


def explanation_from_issues(issues, suggestions):
    """Generate plain English explanation from issues and suggestions."""
    lines = []

    if not issues:
        lines.append("✅ No obvious performance issues detected in EXPLAIN output.")
        lines.append("Query appears to be well-optimized at first glance.")
    else:
        lines.append("🔍 Performance issues detected:")
        for i, issue in enumerate(issues, 1):
            lines.append(f"  {i}. {issue}")

    if suggestions:
        lines.append("\n💡 Suggested optimizations:")
        for i, suggestion in enumerate(suggestions, 1):
            lines.append(f"  {i}. {suggestion}")
    elif issues:
        lines.append("\n❓ No specific index suggestions available. Consider reviewing query structure.")

    return "\n".join(lines)


def optimize_query(query: str) -> str:
    """
    Wrapper for Streamlit demo.
    Analyzes the query, suggests optimizations,
    and returns the same query (since optimizer is advisory).
    """
    try:
        # Run analysis
        suggestions = suggest_indexes(query)

        # Create a header comment showing optimization suggestions
        comment_block = "/* AUTOOPTIMIZER SUGGESTIONS:\n"
        for s in suggestions:
            comment_block += f"   {s}\n"
        comment_block += "*/\n"

        # Return original query with embedded suggestions as comment
        optimized_query = comment_block + query
        return optimized_query

    except Exception as e:
        print(f"[Error in optimize_query] {e}")
        return query
