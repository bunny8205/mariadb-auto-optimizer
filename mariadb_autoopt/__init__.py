"""
MariaDB Auto-Optimizer - Adaptive SQL optimization for MariaDB in Jupyter notebooks.
Extends the official MariaDB Jupyter Kernel with intelligent query optimization capabilities.
"""

__version__ = "1.0.0"
__author__ = "Om Shree Gyanraj"
__description__ = "MariaDB Auto-Optimizer magic for adaptive SQL optimization inside Jupyter"

from .core import timed_query, optimize_once
from .analyzer import run_explain, analyze_explain_df, parse_tables_from_query
from .optimizer import suggest_indexes, explanation_from_issues
from .magic import (
    register_magic, 
    load_ipython_extension, 
    auto_register, 
    optimize_and_show
)

__all__ = [
    'timed_query',
    'optimize_once', 
    'run_explain',
    'analyze_explain_df',
    'parse_tables_from_query',
    'suggest_indexes',
    'explanation_from_issues',
    'register_magic',
    'load_ipython_extension',
    'auto_register',
    'optimize_and_show',
    '__version__',
    '__author__', 
    '__description__'
]

# Auto-register magic when imported in Jupyter using the new auto_register function
try:
    auto_register()
    print("✅ MariaDB Auto-Optimizer ready! Use %%mariadb_opt in your notebooks.")
except Exception as e:
    # This might fail outside Jupyter, which is fine
    print(f"⚠️ MariaDB Auto-Optimizer loaded (Jupyter magic not available: {e})")
