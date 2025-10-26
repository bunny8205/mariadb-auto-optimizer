"""
MariaDB Auto-Optimizer - Automatic query optimization for MariaDB in Pandas/Jupyter workflows.
"""

__version__ = "0.1.0"
__author__ = "Om"

from .core import timed_query, optimize_once
from .analyzer import run_explain, analyze_explain_df, parse_tables_from_query
from .optimizer import suggest_indexes, explanation_from_issues
from .magic import register_magic

# Auto-register magic when imported in Jupyter
try:
    register_magic()
except Exception:
    # This might fail outside Jupyter, which is fine
    pass