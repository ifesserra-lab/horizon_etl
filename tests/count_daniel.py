from sqlalchemy import text
from src.core.logic.canonical_exporter import CanonicalDataExporter

def count_daniel_advisorships():
    exporter = CanonicalDataExporter(sink=None)
    session = exporter.initiative_ctrl._service._repository._session
    
    # Daniel's ID is 465 (from previous debugging) or search by name
    supervisor_id = 465
    
    query = text("""
       SELECT type, COUNT(*) 
       FROM advisorships 
       WHERE supervisor_id = :sid 
       GROUP BY type
    """)
    rows = session.execute(query, {"sid": supervisor_id}).fetchall()
    
    print(f"Advisorship Counts for Supervisor ID {supervisor_id} (Daniel):")
    for r in rows:
       print(f"  {str(r[0]):<30} : {r[1]}")

if __name__ == "__main__":
    count_daniel_advisorships()
