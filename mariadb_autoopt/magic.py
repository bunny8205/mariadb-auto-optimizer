"""
MariaDB Auto-Optimizer Jupyter Magic
Extends the official MariaDB Jupyter Kernel with adaptive SQL optimization capabilities.
"""

from IPython.core.magic import register_cell_magic
from IPython.display import display
import matplotlib.pyplot as plt
import shlex
import json

__version__ = "1.0.0"
__author__ = "Om Shree Gyanraj"
__description__ = "MariaDB Auto-Optimizer magic for adaptive SQL optimization inside Jupyter"


def register_magic():
    """Register the Jupyter cell magic."""

    @register_cell_magic
    def mariadb_opt(line, cell):
        """
        MariaDB Auto-Optimizer Cell Magic

        Usage:
        %%mariadb_opt conn=conn auto_apply=False
        SELECT * FROM table WHERE condition;

        Examples:
        %%mariadb_opt conn=my_conn
        SELECT * FROM users WHERE email = 'test@example.com';

        %%mariadb_opt conn=db auto_apply=true
        SELECT * FROM orders WHERE date > '2023-01-01';

        %%mariadb_opt conn=conn auto_apply=false config='{\"max_indexes\": 3}'
        SELECT * FROM large_table WHERE category = 'A' AND status = 'active';
        """
        # Help command
        if line.strip() in ('-h', '--help', 'help'):
            print(__doc__)
            return

        try:
            # Parse arguments
            args = {}
            config = {}
            for token in shlex.split(line):
                if '=' in token:
                    key, value = token.split('=', 1)
                    args[key] = value

            # Parse config if provided
            if 'config' in args:
                try:
                    config = json.loads(args['config'])
                except json.JSONDecodeError as e:
                    print(f"⚠️  Invalid config JSON: {args['config']}")
                    print(f"💡 Error: {str(e)}")
                    return

            # Get connection - FIXED: Use get_ipython() to access user namespace
            from IPython import get_ipython
            ipython = get_ipython()
            conn_var = args.get('conn', 'conn')
            conn = ipython.user_ns.get(conn_var)

            if conn is None:
                print(f"❌ Error: Connection variable '{conn_var}' not found in namespace")
                print("💡 Make sure you've created a database connection first")
                return

            # Get auto_apply flag
            auto_apply = args.get('auto_apply', 'false').lower() in ('true', '1', 'yes', 'y')

            print("🔗 [Integration] MariaDB Auto-Optimizer linked successfully with Jupyter Kernel environment.")

            # Import here to avoid circular imports
            from mariadb_autoopt.core import optimize_once

            # Run optimization
            result = optimize_once(conn, cell.strip(), auto_apply=auto_apply, config=config)

            print("📦 [Integration] Optimization completed — results available to MariaDB Kernel or notebook context.")

            # Display results
            print("=" * 60)
            print("📊 MARIA DB AUTO-OPTIMIZER RESULTS")
            print("=" * 60)

            print(f"\n⏱️  BASELINE PERFORMANCE")
            print(f"   Rows returned: {result['before_rows']:,}")
            print(f"   Execution time: {result['before_time']:.3f} seconds")

            if result['explain_mode']:
                print(f"\n🔍 EXPLAIN ANALYSIS ({result['explain_mode']})")
                if result['explain_df'] is not None:
                    display(result['explain_df'])

            print(f"\n📝 ANALYSIS SUMMARY")
            print(result['explanation'])

            if result['applied_indexes']:
                print(f"\n🔧 APPLIED CHANGES")
                for idx in result['applied_indexes']:
                    print(f"   • {idx}")

            # Show suggested indexes if not applied
            if result.get('suggested_indexes') and not auto_apply:
                print(f"\n💡 SUGGESTED INDEXES (not applied - use auto_apply=true to apply)")
                for idx in result['suggested_indexes']:
                    print(f"   • {idx}")

            if result['after_time'] is not None:
                print(f"\n🚀 OPTIMIZATION RESULTS")
                print(f"   Rows returned: {result['after_rows']:,}")
                print(f"   Execution time: {result['after_time']:.3f} seconds")

                improvement = ((result['before_time'] - result['after_time']) / result['before_time']) * 100
                print(f"   Performance improvement: {improvement:.1f}%")

                # Create visualization
                plt.figure(figsize=(8, 4))
                times = [result['before_time'], result['after_time']]
                labels = ['Before', 'After']
                colors = ['#ff6b6b', '#51cf66']

                bars = plt.bar(labels, times, color=colors, alpha=0.8)
                plt.ylabel('Execution Time (seconds)')
                plt.title('Query Performance: Before vs After Optimization')

                # Add value labels on bars
                for bar, time_val in zip(bars, times):
                    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                             f'{time_val:.3f}s', ha='center', va='bottom')

                plt.tight_layout()
                plt.show()

            # Optional: Query plan comparison
            if result.get('before_plan') and result.get('after_plan'):
                print(f"\n📊 QUERY PLAN COMPARISON")
                print("   Use result['before_plan'] and result['after_plan'] to analyze execution plans")

        except ImportError as e:
            print(f"❌ Missing dependency: {str(e)}")
            print("💡 Try: pip install mariadb-auto-optimizer")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("\n💡 Make sure you have:")
            print("   - A MariaDB connection variable (default: 'conn')")
            print("   - The query is valid SQL")
            print("   - You have necessary permissions")
            import traceback
            traceback.print_exc()


# Alternative function-based approach
def optimize_and_show(conn, query, auto_apply=False, config=None):
    """Function-based alternative to cell magic."""
    from mariadb_autoopt.core import optimize_once
    result = optimize_once(conn, query, auto_apply=auto_apply, config=config or {})

    print("📊 Optimization Results:")
    print(f"Before: {result['before_time']:.3f}s")

    if result['after_time']:
        print(f"After:  {result['after_time']:.3f}s")
        improvement = ((result['before_time'] - result['after_time']) / result['before_time']) * 100
        print(f"Improvement: {improvement:.1f}%")

    print(f"\n{result['explanation']}")
    return result


def load_ipython_extension(ipython):
    """
    Jupyter looks for this function to auto-load the magic
    when users run: %load_ext mariadb_autoopt.magic
    or when the extension is integrated into the MariaDB kernel.
    """
    register_magic()
    print("✅ MariaDB Auto-Optimizer magic registered successfully as %%mariadb_opt")


def auto_register():
    """
    Auto-registers the magic when imported (for MariaDB Jupyter Kernel).
    """
    try:
        from IPython import get_ipython
        ipython = get_ipython()
        if ipython:
            load_ipython_extension(ipython)
    except Exception as e:
        print(f"⚠️ Auto-registration skipped: {e}")


# Auto-register when imported in Jupyter environment
auto_register()
