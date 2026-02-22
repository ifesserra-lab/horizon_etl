
import sqlite3

db_path = "db/horizon.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Initiative Types ---")
cursor.execute("SELECT id, name FROM initiative_types;")
for row in cursor.fetchall():
    print(row)

print("\n--- Identifying Type of 338 ---")
cursor.execute("SELECT name, initiative_type_id FROM initiatives WHERE id = 338;")
name, type_id = cursor.fetchone()
print(f"Initiative 338: Name='{name}', TypeID={type_id}")

print(f"\n--- Checking if another ID has this name ---")
cursor.execute("SELECT id, initiative_type_id FROM initiatives WHERE name = ?;", (name,))
for row in cursor.fetchall():
    print(row)

conn.close()
