
import sqlite3

db_path = "db/horizon.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

ids = (7, 74, 768)

print("--- Gustavo Records Details ---")
cursor.execute(f"SELECT id, name, email FROM persons WHERE id IN {ids};")
for row in cursor.fetchall():
    print(row)

# Also check person_emails table if it exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person_emails';")
if cursor.fetchone():
    print("\n--- Person Emails Table ---")
    cursor.execute(f"SELECT person_id, email FROM person_emails WHERE person_id IN {ids};")
    for row in cursor.fetchall():
        print(row)

conn.close()
