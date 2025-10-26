import time
import pandas as pd
import warnings
from .analyzer import run_explain, analyze_explain_df, parse_tables_from_query
from .optimizer import suggest_indexes, explanation_from_issues


def timed_query(conn, query, params=None):
    """Run a query using a DB-API connection and return (df, elapsed_seconds)."""
    t0 = time.time()

    # Suppress pandas warnings for DB-API connections
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy connectable.*')
        df = pd.read_sql_query(query, conn, params=params)

    elapsed = time.time() - t0
    return df, elapsed


def optimize_once(conn, query, auto_apply=False, verbose=True):
    """Run query, analyze, show suggestions, optionally apply indexes and re-run."""
    # 1. baseline run
    if verbose:
        print("Running baseline query...")

    df_before, t_before = timed_query(conn, query)

    # 2. EXPLAIN
    try:
        explain_df, explain_mode = run_explain(conn, query)
        issues = analyze_explain_df(explain_df, explain_mode)
    except Exception as e:
        explain_df, explain_mode = None, None
        issues = [f"EXPLAIN failed: {str(e)}"]

    suggestions = suggest_indexes(query)
    expl_text = explanation_from_issues(issues, suggestions)

    result = {
        "before_rows": len(df_before),
        "before_time": t_before,
        "explain_mode": explain_mode,
        "explain_df": explain_df,
        "issues": issues,
        "suggestions": suggestions,
        "explanation": expl_text,
        "after_rows": None,
        "after_time": None,
        "applied_indexes": []
    }

    # Optionally apply indexes
    if auto_apply and suggestions:
        if verbose:
            print("Applying suggested indexes...")

        applied = []
        cursor = conn.cursor()
        for s in suggestions:
            if s.strip().upper().startswith("CREATE INDEX"):
                try:
                    cursor.execute(s)
                    applied.append(s)
                    if verbose:
                        print(f"✓ Applied: {s}")
                except Exception as e:
                    error_msg = f"Failed: {s} ({e})"
                    applied.append(error_msg)
                    if verbose:
                        print(f"✗ {error_msg}")
        cursor.close()
        conn.commit()
        result['applied_indexes'] = applied

        # re-run query to measure improvement
        if verbose:
            print("Running optimized query...")
        df_after, t_after = timed_query(conn, query)
        result['after_rows'] = len(df_after)
        result['after_time'] = t_after

    return result