import psycopg2

try:
    conn = psycopg2.connect("postgresql://prefect:prefect@localhost:5433/prefect")
    print("Connection successful to Prefect DB on 5433")
    conn.close()
except Exception as e:
    print(f"Connection failed to Prefect DB on 5433: {e}")
