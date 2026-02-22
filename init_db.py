from sqlalchemy import create_engine
from eo_lib.domain.base import Base
import os
import sys

# Ensure all entities are imported so metadata knows about them
try:
    from research_domain.domain import entities
    from research_domain.domain.entities.researcher import Researcher
    from research_domain.domain.entities.advisorship import Advisorship
    from research_domain.domain.entities.publication import Publication
except ImportError as e:
    print(f"Warning: Could not import some entities for schema discovery: {e}")

def init_db():
    db_path = "sqlite:///db/horizon.db"
    print(f"Initializing SQLite Database at {db_path}...")
    engine = create_engine(db_path)
    
    # This will create all tables defined in Base.metadata
    Base.metadata.create_all(engine)
    print("Database Schema Initialized Successfully.")

if __name__ == "__main__":
    # Ensure directory exists
    os.makedirs("db", exist_ok=True)
    init_db()
