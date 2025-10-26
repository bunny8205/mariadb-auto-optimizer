import pymysql
import random
from datetime import datetime, timedelta


def create_sample_database(host='localhost', user='autoopt_user', password='rn8205', database='test_autoopt'):
    """Create sample database with test data."""
    try:
        # Connect to MySQL/MariaDB
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            autocommit=True
        )

        with conn.cursor() as cursor:
            # Create database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            cursor.execute(f"USE {database}")

            # Create sales table
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS sales
                           (
                               id
                               INT
                               AUTO_INCREMENT
                               PRIMARY
                               KEY,
                               product_id
                               INT,
                               user_id
                               INT,
                               order_date
                               DATE,
                               amount
                               DECIMAL
                           (
                               10,
                               2
                           ),
                               category VARCHAR
                           (
                               50
                           ),
                               region VARCHAR
                           (
                               50
                           )
                               )
                           """)

            # Clear existing data
            cursor.execute("TRUNCATE TABLE sales")

            # Insert sample data
            print("Generating sample data...")
            categories = ['Electronics', 'Clothing', 'Books', 'Home', 'Sports']
            regions = ['North', 'South', 'East', 'West']

            data = []
            for i in range(100000):  # 100k records
                product_id = random.randint(1, 100)
                user_id = random.randint(1, 5000)
                days_ago = random.randint(1, 365 * 3)  # Last 3 years
                order_date = datetime.now() - timedelta(days=days_ago)
                amount = round(random.uniform(10, 1000), 2)
                category = random.choice(categories)
                region = random.choice(regions)

                data.append((product_id, user_id, order_date, amount, category, region))

                # Insert in batches
                if len(data) >= 1000:
                    cursor.executemany(
                        "INSERT INTO sales (product_id, user_id, order_date, amount, category, region) VALUES (%s, %s, %s, %s, %s, %s)",
                        data
                    )
                    data = []
                    print(f"Inserted {i + 1} records...")

            # Insert remaining records
            if data:
                cursor.executemany(
                    "INSERT INTO sales (product_id, user_id, order_date, amount, category, region) VALUES (%s, %s, %s, %s, %s, %s)",
                    data
                )

            print("Sample database created successfully!")

            # Show table info
            cursor.execute("""
                           SELECT COUNT(*)        as total_rows,
                                  MIN(order_date) as earliest_date,
                                  MAX(order_date) as latest_date
                           FROM sales
                           """)
            info = cursor.fetchone()
            print(f"Total rows: {info[0]:,}")
            print(f"Date range: {info[1]} to {info[2]}")

        return conn

    except Exception as e:
        print(f"Error creating sample database: {e}")
        return None


def main():
    """Main function to set up demo database."""
    print("MariaDB Auto-Optimizer - Sample Data Setup")
    print("=" * 50)

    # Get connection details
    host = input("Enter host (default: localhost): ") or "localhost"
    user = input("Enter username (default: root): ") or "root"
    password = input("Enter password: ")
    database = input("Enter database name (default: test_autoopt): ") or "test_autoopt"

    conn = create_sample_database(host, user, password, database)

    if conn:
        print("\n✅ Sample database setup complete!")
        print(f"📊 You can now test the optimizer with queries like:")
        print("""
              SELECT product_id, SUM(amount) as total
              FROM sales
              WHERE order_date BETWEEN '2022-01-01' AND '2022-12-31'
              GROUP BY product_id
              ORDER BY total DESC LIMIT 10;
              """)
        conn.close()


if __name__ == "__main__":
    main()