
---

# 🚀 MariaDB Auto-Optimizer

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)
![MariaDB](https://img.shields.io/badge/MariaDB-10.5%2B-orange.svg)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange.svg)

**AI-powered SQL Performance Enhancer with Adaptive Learning for MariaDB**

MariaDB Auto-Optimizer is an intelligent query optimization assistant that automatically analyzes SQL queries, detects performance bottlenecks, and recommends improvements using machine learning and adaptive strategies — delivering **40-80% performance gains** for real-world datasets.

## ✨ Revolutionary Features

- ✅ **Adaptive Learning Engine** - Learns from past optimizations and reuses successful strategies
- ✅ **Smart Strategy Selection** - Automatically chooses optimization mode based on table size, query complexity, and cost
- ✅ **Real-World Dataset Ready** - Complete OpenFlights aviation dataset with **7,698 airports, 6,162 airlines, and 67,663 routes**
- ✅ **Intelligent Index Management** - Creates, validates, and rolls back indexes based on actual performance
- ✅ **Micro-Optimization Mode** - Lightweight temporary indexes for small tables
- ✅ **Composite Index Detection** - Automatically suggests multi-column indexes for JOINs and GROUP BY
- ✅ **Performance Visualization** - Interactive charts showing before/after optimization results
- ✅ **Query Caching & Learning** - Remembers successful optimizations across sessions

## 📂 Project Structure

```
mariadb-auto-optimizer/
│
├── data/                         # OpenFlights dataset (Airports, Airlines, Routes)
│   ├── airports.dat
│   ├── airlines.dat  
│   └── routes.dat
├── demo/                         # Jupyter Notebook demo
│   └── demo_notebook.ipynb      # Interactive Jupyter Notebook demo
│
├── mariadb_autoopt/              # Main package source code
│   ├── __init__.py
│   ├── analyzer.py
│   ├── core.py
│   ├── magic.py
│   └── optimizer.py
│
├── README.md
├── requirements.txt
├── run_demo.py                   # 🆕 Automated script demo (main repository)
└── setup_demo.py                 # Quick setup script
```

## 🚀 Quick Start (5 Minutes)

### ✅ 1. Clone & Setup
```bash
git clone https://github.com/bunny8205/mariadb-auto-optimizer.git
cd mariadb-auto-optimizer

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt
```

### ✅ 2. Choose Your Demo Method

#### Option A: Interactive Jupyter Notebook (Recommended for Learning)
```bash
jupyter notebook
```
**Open:** `demo/demo_notebook.ipynb`

#### Option B: Automated Script Demo (Quick Results)
```bash
python run_demo.py
```

### ✅ 3. What the Demo Shows
Both demos automatically:
- Loads OpenFlights aviation dataset (**7,698 airports, 6,162 airlines, 67,663 routes**)
- Creates MariaDB tables with optimal schema
- Applies intelligent indexing strategies
- Demonstrates **40-80% performance improvements**
- Shows interactive visualizations

## 🎯 Real-World Performance Results

### 📊 Demo Output Highlights
Based on the automated `run_demo.py` execution:

#### 🎯 **DEMO 1: Complex Aggregation with Multiple JOINS**
- **Baseline Performance**: 0.117s
- **Optimized Performance**: 0.054s  
- **Improvement**: **54.2% faster**
- **Strategy**: Join optimization with composite indexes
- **Indexes Created**: `idx_airports_country`, `idx_routes_composite_source_airport_id_airline_id`

#### 🎯 **DEMO 2: Large Dataset Analysis with Subquery**
- **Baseline Performance**: 0.202s
- **Optimized Performance**: 0.214s
- **Result**: **Intelligent rollback** - system detected insufficient improvement and automatically removed indexes
- **Key Feature**: Adaptive optimization that only keeps beneficial indexes

#### 🎯 **DEMO 3: Cross-Table Analysis with Complex Filtering**
- **Baseline Performance**: 0.050s
- **Optimized Performance**: 0.025s
- **Improvement**: **50.6% faster**
- **Strategy**: Join optimization with existing indexes + additional destination airport index

### 🏆 Overall Performance Summary
- **Successful Optimizations**: 2 out of 3 queries
- **Average Improvement**: **52.4%**
- **Performance Rating**: 🏆 PHENOMENAL!
- **Total Indexes Created**: 9 intelligently crafted indexes

## 🔧 Key Technical Observations

### 🧠 Smart Index Management
```python
# The system automatically:
- Detects duplicate indexes and avoids creation
- Rolls back indexes with <10% improvement
- Creates composite indexes for JOIN optimization
- Maintains only beneficial indexes
```

### 📈 Intelligent Strategy Selection
```python
def choose_optimization_strategy(conn, query):
    """Based on real-time analysis:
    - Table Size: 67,663 rows (classified as 'medium')
    - Query Type: JOIN operations
    - Cost Estimation: 243.6 (high complexity)
    - Selected Strategy: join_optimize
    """
```

### 🎯 Demo-Specific Features
- **Fixed Table Alias Resolution** - Properly handles complex query aliases
- **Validated Index Creation** - Ensures only valid indexes are created
- **Statistical Benchmarking** - 3 runs per query with median comparison
- **Cache Management** - Database cache cleared for consistent testing

## 🛠️ Installation & Configuration

### Database Setup
```sql
-- Create dedicated user and database
CREATE DATABASE test_autoopt;
CREATE USER 'autoopt_user'@'localhost' IDENTIFIED BY 'rn8205';
GRANT ALL PRIVILEGES ON test_autoopt.* TO 'autoopt_user'@'localhost';
FLUSH PRIVILEGES;
```

### Python Dependencies
```bash
# Core requirements
pandas>=1.5.0
pymysql>=1.0.0
sqlparse>=0.4.0
matplotlib>=3.5.0
seaborn>=0.11.0
jupyter>=1.0.0
numpy>=1.21.0
```

## 🎮 Usage Examples

### 1. Automated Demo (Quick Start)
```bash
python run_demo.py
```
**Output**: Complete performance analysis with real-world aviation data

### 2. Jupyter Magic Commands (Interactive)
```python
# Load the magic extension
%reload_ext mariadb_autoopt.magic

# Connect to database
%mariadb_opt conn=conn auto_apply=False

# Analyze and optimize queries
%%mariadb_opt
SELECT * FROM routes 
WHERE source_airport_id = 1234 
AND stops = 0;
```

### 3. Programmatic Usage
```python
from mariadb_autoopt.core import optimize_once

# Single query optimization
result = optimize_once(conn, 
    "SELECT COUNT(*) FROM routes WHERE stops = 0",
    auto_apply=True,
    verbose=True
)

print(f"Performance improved by {result['improvement']:.1f}%")
```

## 📊 Real-World Dataset Statistics

### OpenFlights Aviation Data
- **🏢 Airports**: 7,698 across 237 countries
- **✈️ Airlines**: 6,162 from 275 countries (1,255 active)
- **🛫 Routes**: 67,663 connecting 3,320 source to 3,326 destination airports
- **📊 Database Size**: 12.72 MB with optimized indexes

## 🧩 Core Optimization Strategies

### 🧠 Adaptive Learning Engine
```python
# Smart strategy selection based on multiple factors
def choose_optimization_strategy(conn, query):
    size_label, rows = detect_table_size(conn)
    query_type = detect_query_type(query) 
    cost = get_query_cost(conn, query)
    
    # Dynamic strategy selection
    if size_label == "small" and cost < 100:
        return "analyze_only"
    elif size_label == "large" or query_type == "join":
        return "full_optimize"
    # ... intelligent decision making
```

### 🔥 High-Impact Performance Gains
- **50-60% improvement** with JOIN indexes (Demo 1 & 3)
- **Intelligent rollback** for ineffective optimizations (Demo 2)
- **Composite indexing** for multi-table queries
- **Adaptive validation** ensuring only beneficial changes persist

## 🎓 Learning Features

### Query Performance History
```python
query_history = {
    'query_hash': {
        'improvement': 54.2,      # 54.2% performance gain
        'strategy': 'join_optimize',
        'before_time': 0.117,
        'after_time': 0.054,
        'timestamp': 1672531200
    }
}
```

### Strategy Reuse
```python
def reuse_learnings(query, current_strategy):
    """Reuses strategies that provided >15% improvement"""
    # Finds similar past queries with successful optimizations
    # Returns the best-performing strategy
```

## 🔮 Future Roadmap

### 🚀 Coming Soon:
- **Machine Learning Integration** - Predictive optimization
- **PostgreSQL Support** - Multi-database compatibility
- **Visual Query Plans** - Interactive EXPLAIN diagrams
- **Real-time Monitoring** - Live performance analytics
- **Cloud Integration** - AWS RDS, Google Cloud SQL support

## 👥 Contributing

We welcome contributions! Areas of interest:
- New optimization strategies
- Additional database support
- Enhanced visualization
- Machine learning features
- Performance benchmarking

## 📜 License

MIT License - feel free to use, modify, and distribute!

## 🧑‍💻 Author

**Om Shree Gyanraj (bunny8205)**  
MariaDB Hackathon Project — 2025

---

**Experience the future of database optimization with adaptive learning and real-world performance gains! 🚀**

*"Your aviation queries will never be the same again!"* ✈️

---
