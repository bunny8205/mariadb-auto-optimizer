"""
MariaDB Auto-Optimizer - Intelligent Query Optimization for MariaDB
A machine learning-powered tool that automatically optimizes SQL queries
by analyzing query patterns and creating strategic indexes.
"""

__version__ = "1.0.0"
__author__ = "MariaDB Auto-Optimizer Team"
__description__ = "Intelligent SQL query optimization for MariaDB"

from .core import DatabaseManager, QueryOptimizer, optimize_once
from .analyzer import QueryAnalyzer, PerformanceTracker
from .optimizer import IndexOptimizer, QueryRewriter
from .utils import DataLoader, VisualizationEngine
from .connector import AutoOptimizer, OptimizationResult, AppConfig

__all__ = [
    # Core functionality
    'DatabaseManager',
    'QueryOptimizer',
    'optimize_once',

    # Analysis components
    'QueryAnalyzer',
    'PerformanceTracker',

    # Optimization components
    'IndexOptimizer',
    'QueryRewriter',

    # Utility components
    'DataLoader',
    'VisualizationEngine',

    # NEW: Connector for integration and reusable library
    'AutoOptimizer',
    'OptimizationResult',
    'AppConfig'
]
