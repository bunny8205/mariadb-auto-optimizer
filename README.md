# 🚀 MariaDB Auto-Optimizer

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)
![MariaDB](https://img.shields.io/badge/MariaDB-10.5%2B-orange.svg)

**AI-powered SQL Performance Enhancer for MariaDB**

MariaDB Auto-Optimizer is an intelligent query optimization assistant for MariaDB developers. It automatically analyzes SQL queries, detects performance bottlenecks, and recommends improvements such as indexing strategies — saving time and improving database execution efficiency.

## ✨ Key Features

- ✅ **Automated Analysis** - Detects inefficient SQL queries automatically
- ✅ **Smart Recommendations** - Suggests performance optimizations (indexes, rewrites, hints)
- ✅ **Dual Modules** - Query Analyzer & Query Optimizer for comprehensive optimization
- ✅ **Jupyter Integration** - Simple usage with magic commands in notebooks
- ✅ **Demo Dataset** - Complete OpenFlights dataset for immediate testing
- ✅ **Performance Metrics** - Benchmark and compare query improvements

## 📂 Project Structure

```
mariadb-auto-optimizer/
│
├── data/                         # OpenFlights dataset (Airports, Airlines, Routes)
├── demo/                         # Jupyter Notebook demo
│   ├── demo_notebook.ipynb
│
├── mariadb_autoopt/              # Main package source code
│   ├── __init__.py
│   ├── analyzer.py
│   ├── core.py
│   ├── magic.py
│   ├── optimizer.py
│
├── README.md
├── requirements.txt
└── setup_demo.py                 # Quick setup script
```

## 🔧 Installation & Setup

### ✅ Prerequisites
- Python 3.8 or higher
- MariaDB 10.5 or higher
- Jupyter Notebook

### ✅ Clone Repository
```bash
git clone https://github.com/bunny8205/mariadb-auto-optimizer.git
cd mariadb-auto-optimizer
```

### ✅ Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows
```

### ✅ Install Dependencies
```bash
pip install -r requirements.txt
```

### ✅ Quick Setup (Optional)
```bash
python setup_demo.py
```

## 🧪 Demo Usage (Jupyter Notebook)

### 1️⃣ Start Jupyter
```bash
jupyter notebook
```

### 2️⃣ Open Demo Notebook:
```
demo/demo_notebook.ipynb
```

### 3️⃣ Run Demo Cells to:
- Load OpenFlights dataset into MariaDB
- Initialize MariaDB optimizer
- Analyze SQL queries for performance issues
- Generate optimization recommendations
- View performance improvement metrics

### 4️⃣ Basic Usage Example:
```python
# Import the magic module
from mariadb_autoopt import magic

# Connect to your MariaDB database
%mariadb_opt connect --host localhost --user root --password your_password --database test

# Analyze and optimize a query
%mariadb_opt analyze "SELECT * FROM routes WHERE source_airport_id = 1234"
```

## 🧠 How It Works

| Module | Responsibility |
|--------|----------------|
| `analyzer.py` | Parses SQL queries and detects performance bottlenecks |
| `optimizer.py` | Generates optimization advice & index suggestions |
| `magic.py` | Notebook extension enabling `%mariadb_opt` magic command |
| `core.py` | Utility functions and database communication |

## ✅ Example Output

```
🔍 Query analyzed successfully!

📊 Performance Analysis:
→ Table: routes (250,000 rows)
→ Missing index on: source_airport_id
→ Current execution time: ~450ms

⚡ Optimization Recommendation:
→ CREATE INDEX idx_routes_source ON routes(source_airport_id);
→ Expected improvement: ~65% faster
→ Estimated new execution time: ~160ms

💡 Additional Suggestions:
→ Consider adding composite index on (source_airport_id, destination_airport_id)
→ Query can be optimized with EXISTS instead of IN for subqueries
```

## 🎯 Use Cases

- **Database Administrators** - Automated performance tuning
- **Developers** - SQL query optimization during development
- **Data Scientists** - Efficient database queries in Jupyter notebooks
- **Students** - Learning SQL performance optimization techniques
- **Researchers** - Benchmarking and analyzing index improvements

## 🚀 Advanced Features

### Magic Command Options:
```python
# Basic query analysis
%mariadb_opt analyze "SELECT * FROM table WHERE condition"

# Generate optimization plan
%mariadb_opt optimize "SELECT * FROM large_table"

# Benchmark query performance
%mariadb_opt benchmark "SELECT COUNT(*) FROM big_table"

# Get database statistics
%mariadb_opt stats
```

### Programmatic Usage:
```python
from mariadb_autoopt.analyzer import QueryAnalyzer
from mariadb_autoopt.optimizer import QueryOptimizer

analyzer = QueryAnalyzer(database_connection)
results = analyzer.analyze_query("SELECT * FROM users WHERE email = 'test@example.com'")

optimizer = QueryOptimizer()
recommendations = optimizer.generate_optimizations(results)
```

## 📌 Future Enhancements

- 🚀 Automated index creation and rollback
- 📊 Cost-based query planning
- 🔄 Support for PostgreSQL / MySQL
- 📈 Visual query plan diagrams
- 🎯 Machine learning-based optimization
- 🔍 Real-time performance monitoring

## 🧑‍💻 Author

**Om Shree Gyanraj (bunny8205)**  
MariaDB Hackathon Project — 2025

## 🤝 Contributing

We welcome contributions! Please feel free to submit pull requests, report bugs, or suggest new features.

## 📜 License

This project is licensed under the MIT License.  
Feel free to use, modify, and contribute!

---

**Keywords**: mariadb, sql-optimizer, query-performance, database-tuning, jupyter-notebook, python, sql-indexing, performance-analysis

**Topics**: mariadb, sql-optimizer, query-performance, database-tuning, jupyter-notebook, python, sql-indexing, performance-analysis, openflights-dataset, automated-optimization
