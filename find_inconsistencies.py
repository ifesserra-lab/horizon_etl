
import sqlite3

db_path = "db/horizon.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the last warning's ID from logs or just find initiatives with type 2 missing from advisorships
print("--- Initiatives with Type 2 (Advisorship) missing from advisorships table ---")
cursor.execute("""
    SELECT i.id, i.name, i.initiative_type_id
    FROM initiatives i
    LEFT JOIN advisorships a ON i.id = a.id
    WHERE i.initiative_type_id = 2 AND a.id IS NULL;
""")
for row in cursor.fetchall():
    print(row)

print("\n--- Summary of Initiative Types for all initiatives ---")
cursor.execute("""
    SELECT it.name, count(*)
    FROM initiatives i
    JOIN initiative_types it ON i.initiative_type_id = it.id
    GROUP BY it.name;
""")
for row in cursor.fetchall():
    print(row)

conn.close()
