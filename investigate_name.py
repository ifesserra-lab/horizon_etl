
import sqlite3

db_path = "db/horizon.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

name = 'Estudo e Implementação do Protocolo OPC UA como Camada de Comunicação para Dispositivos IoT'

print(f"--- Searching for Initiatives with name: '{name}' ---")
cursor.execute("SELECT id, initiative_type_id, parent_id FROM initiatives WHERE name = ?;", (name,))
for row in cursor.fetchall():
    print(row)

print("\n--- Checking for parents that have this name ---")
cursor.execute("SELECT id, name FROM initiatives WHERE name = ? AND id IN (SELECT DISTINCT parent_id FROM initiatives WHERE parent_id IS NOT NULL);", (name,))
for row in cursor.fetchall():
    print(row)

conn.close()
