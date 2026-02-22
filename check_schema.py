
import sqlite3

db_path = "db/horizon.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Researchers Table Schema ---")
cursor.execute("PRAGMA table_info(researchers);")
for row in cursor.fetchall():
    print(row)

print("\n--- Persons Table Schema ---")
cursor.execute("PRAGMA table_info(persons);")
for row in cursor.fetchall():
    print(row)

conn.close()
