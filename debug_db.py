
from sqlalchemy import text
from eo_lib.infrastructure.database.postgres_client import PostgresClient

def delete_initiative(init_id):
    client = PostgresClient()
    session = client.get_session()
    print(f"--- Deleting Initiative {init_id} ---")
    try:
        session.execute(text("DELETE FROM initiative_teams WHERE initiative_id = :id"), {"id": init_id})
        session.execute(text("DELETE FROM advisorships WHERE id = :id"), {"id": init_id})
        session.execute(text("DELETE FROM initiatives WHERE id = :id"), {"id": init_id})
        session.commit()
        print("Deleted.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()

def check_initiative(init_id):
    client = PostgresClient()
    session = client.get_session()
    
    print(f"--- Checking Initiative {init_id} ---")
    
    # Check Initiative
    res = session.execute(text("SELECT id, name FROM initiatives WHERE id = :id"), {"id": init_id}).fetchone()
    if not res:
        print("Initiative not found.")
        return
    print(f"Initiative: {res[0]} - {res[1]}")
    
    # Check Advisorship Specifics
    # Try to select all columns or specific ones likely to exist
    try:
        adv_res = session.execute(text("SELECT id, supervisor_id, student_id FROM advisorships WHERE id = :id"), {"id": init_id}).fetchone()
        if adv_res:
            print(f"Advisorship Table: ID={adv_res[0]}, SupervisorID={adv_res[1]}, StudentID={adv_res[2]}")
        else:
            print("No entry in 'advisorships' table (might be just an initiative?)")
    except Exception as e:
        print(f"Error checking advisorships table: {e}")

    # Check Link
    links = session.execute(text("SELECT team_id FROM initiative_teams WHERE initiative_id = :id"), {"id": init_id}).fetchall()
    print(f"Linked Teams Count: {len(links)}")
    
    for link in links:
        tid = link[0]
        team = session.execute(text("SELECT id, name FROM teams WHERE id = :tid"), {"tid": tid}).fetchone()
        print(f"  Team: {team[0]} - {team[1]}")
        
        members = session.execute(text("SELECT person_id, role_id FROM team_members WHERE team_id = :tid"), {"tid": tid}).fetchall()
        print(f"  Members Count: {len(members)}")
        for m in members:
            p = session.execute(text("SELECT name FROM persons WHERE id = :pid"), {"pid": m[0]}).fetchone()
            r = session.execute(text("SELECT name FROM roles WHERE id = :rid"), {"rid": m[1]}).fetchone()
            p_name = p[0] if p else "Unknown"
            r_name = r[0] if r else "Unknown"
            print(f"    - {p_name} ({r_name})")

def find_initiative_by_name(name_part):
    client = PostgresClient()
    session = client.get_session()
    print(f"--- Searching for '{name_part}' ---")
    res = session.execute(text("SELECT id, name FROM initiatives WHERE name LIKE :name"), {"name": f"%{name_part}%"}).fetchall()
    for r in res:
        print(f"Found: {r[0]} - {r[1]}")
        check_initiative(r[0])

if __name__ == "__main__":
    delete_initiative(881)
    find_initiative_by_name("RECONHECIMENTO DE COMANDOS DE VOZ")
