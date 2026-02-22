
import sqlite3

db_path = "db/horizon.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Searching for Gustavo variants ---")
cursor.execute("SELECT id, name FROM persons WHERE name LIKE 'Gustavo Maia %Almeida' ORDER BY id;")
for row in cursor.fetchall():
    print(row)

conn.close()
