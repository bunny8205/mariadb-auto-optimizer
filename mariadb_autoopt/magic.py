from IPython.core.magic import register_cell_magic
from IPython.display import display
import matplotlib.pyplot as plt
import shlex


def register_magic():
    """Register the Jupyter cell magic."""

    @register_cell_magic
    def mariadb_opt(line, cell):
        """
        MariaDB Auto-Optimizer Cell Magic

        Usage:
        %%mariadb_opt conn=conn auto_apply=False
        SELECT * FROM table WHERE condition;
        """
        try:
            # Parse arguments
            args = {}
            for token in shlex.split(line):
                if '=' in token:
                    key, value = token.split('=', 1)
                    args[key] = value

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

            # Import here to avoid circular imports
            from mariadb_autoopt.core import optimize_once

            # Run optimization
            result = optimize_once(conn, cell.strip(), auto_apply=auto_apply)

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

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("\n💡 Make sure you have:")
            print("   - A MariaDB connection variable (default: 'conn')")
            print("   - The query is valid SQL")
            print("   - You have necessary permissions")


# Alternative function-based approach
def optimize_and_show(conn, query, auto_apply=False):
    """Function-based alternative to cell magic."""
    from mariadb_autoopt.core import optimize_once
    result = optimize_once(conn, query, auto_apply=auto_apply)

    print("📊 Optimization Results:")
    print(f"Before: {result['before_time']:.3f}s")

    if result['after_time']:
        print(f"After:  {result['after_time']:.3f}s")
        improvement = ((result['before_time'] - result['after_time']) / result['before_time']) * 100
        print(f"Improvement: {improvement:.1f}%")

    print(f"\n{result['explanation']}")
    return result