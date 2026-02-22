
import sqlite3

db_path = "db/horizon.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

initiative_id = 338

print(f"--- Initiative {initiative_id} Details ---")
cursor.execute("""
    SELECT i.id, i.name, it.name as type_name, it.id as type_id
    FROM initiatives i
    JOIN initiative_types it ON i.initiative_type_id = it.id
    WHERE i.id = ?;
""", (initiative_id,))
row = cursor.fetchone()
if row:
    print(f"ID: {row[0]}")
    print(f"Name: {row[1]}")
    print(f"Type: {row[2]} (ID: {row[3]})")
else:
    print("Initiative not found.")

print(f"\n--- Checking Advisorships table for ID {initiative_id} ---")
cursor.execute("SELECT * FROM advisorships WHERE id = ?;", (initiative_id,))
row = cursor.fetchone()
if row:
    print("Found in advisorships table.")
else:
    print("NOT found in advisorships table.")

print(f"\n--- Searching for other initiatives with the same name ---")
if row:
    name = row[1]
    cursor.execute("SELECT id, name, initiative_type_id FROM initiatives WHERE name = ?;", (name,))
    for r in cursor.fetchall():
        print(r)

conn.close()
