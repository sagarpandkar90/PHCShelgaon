import psycopg2
import streamlit as st

# Load credentials from secrets.toml
db = st.secrets["postgres"]

try:
    # Connect to Supabase PostgreSQL via Transaction Pooler
    conn = psycopg2.connect(
        host=db["host"],
        port=db["port"],
        dbname=db["dbname"],
        user=db["user"],
        password=db["password"],
        sslmode="require"  # Required for Supabase
    )

    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()

    print("✅ Connected to Supabase PostgreSQL")
    print("PostgreSQL version:", version)

    cur.close()
    conn.close()

except Exception as e:
    print("❌ Connection failed!")
    print(e)
