import streamlit as st
import pymysql
import pandas as pd
import time
import os

from mariadb_autoopt import core, optimizer  # ✅ Use your existing modules

# --- Database Connection Setup ---
DB_HOST = os.getenv("AUTOOPT_DB_HOST", "serverless-us-central1.sysp0000.db2.skysql.com")
DB_PORT = int(os.getenv("AUTOOPT_DB_PORT", "4038"))
DB_USER = os.getenv("AUTOOPT_DB_USER", "dbpgf17821108")
DB_PASS = os.getenv("AUTOOPT_DB_PASS", "Rn@08022005")
DB_NAME = os.getenv("AUTOOPT_DB_NAME", "autoopt_db")

# --- Connect Function ---
def get_connection():
    try:
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASS, database=DB_NAME, ssl={'ssl': {}}
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# --- Streamlit UI ---
st.set_page_config(page_title="MariaDB Auto-Optimizer Demo", layout="wide")
st.title("⚙️ MariaDB Auto-Optimizer — Query Performance Comparison")
st.caption("Run queries below to compare Normal vs Optimized Execution")

# --- Query Input ---
default_query = "SELECT COUNT(*) FROM airports;"
query = st.text_area("Enter your SQL Query:", value=default_query, height=150)

if st.button("🚀 Run Query Comparison"):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        
        # --- Run Normal Execution ---
        start = time.time()
        try:
            cur.execute(query)
            result_normal = cur.fetchall()
            elapsed_normal = time.time() - start
            df_normal = pd.DataFrame(result_normal)
        except Exception as e:
            st.error(f"Error in normal execution: {e}")
            conn.close()
            st.stop()
        
        # --- Run Optimized Execution (simulate via your optimizer) ---
        start = time.time()
        try:
            optimized_query = optimizer.optimize_query(query)  # Your existing logic
            cur.execute(optimized_query)
            result_opt = cur.fetchall()
            elapsed_opt = time.time() - start
            df_opt = pd.DataFrame(result_opt)
        except Exception as e:
            st.error(f"Error in optimized execution: {e}")
            conn.close()
            st.stop()

        conn.close()

        # --- Results ---
        st.subheader("📊 Execution Comparison")
        st.write(f"**Normal Execution Time:** {elapsed_normal:.4f} sec")
        st.write(f"**Optimized Execution Time:** {elapsed_opt:.4f} sec")

        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(df_normal, use_container_width=True)
            st.caption("Normal Query Result")
        with col2:
            st.dataframe(df_opt, use_container_width=True)
            st.caption("Optimized Query Result")

        st.success("✅ Comparison complete!")
