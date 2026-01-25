import os

from eo_lib.domain.base import Base
from eo_lib.infrastructure.database.postgres_client import PostgresClient
from sqlalchemy import text

# Try to load .env for local configuration
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Also import eo_lib entities
from eo_lib.domain.entities import (
    Organization,
    OrganizationalUnit,
    Person,
    PersonEmail,
    Role,
    Team,
    TeamMember,
)

from research_domain import (
    Campus,
    CampusController,
    KnowledgeArea,
    KnowledgeAreaController,
    Researcher,
    ResearcherController,
    ResearchGroup,
    ResearchGroupController,
    RoleController,
    University,
    UniversityController,
)
from sqlalchemy import Table, Column, Integer, ForeignKey, DateTime

# Extension: Add start_date to ResearchGroup for fundamental metadata
if not hasattr(ResearchGroup, "start_date"):
    ResearchGroup.start_date = Column(DateTime, nullable=True)

# Manually define missing junction table for Research Domain extension
initiative_knowledge_areas = Table(
    "initiative_knowledge_areas",
    Base.metadata,
    Column("initiative_id", Integer, ForeignKey("initiatives.id"), primary_key=True),
    Column("area_id", Integer, ForeignKey("knowledge_areas.id"), primary_key=True),
)


def setup_database():
    """Initializes the database by dropping and recreating all tables."""
    storage_type = os.getenv("STORAGE_TYPE", "memory").lower()
    if storage_type not in ["postgres", "db"]:
        print(f"Skipping database initialization (STORAGE_TYPE is '{storage_type}').")
        return

    print("Initializing Database Tables...")
    client = PostgresClient()

    # Force drop all tables via CASCADE to handle constraints
    try:
        with client._engine.connect() as conn:
            print("Performing forced cleanup (DROP SCHEMA public CASCADE)...")
            # For SQLite, DROP SCHEMA isn't supported the same way, but let's see how PostgresClient handles it or if we need to adjust.
            # actually, using sqlite://, DROP SCHEMA might fail.
            # But let's try running the user's code first.
            if "sqlite" not in str(client._engine.url):
                conn.execute(text("DROP SCHEMA public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
                conn.commit()
            else:
                print("SQLite detected, skipping schema drop.")
                # For SQLite, we might want to just drop tables or rely on create_all?
                # create_all doesn't drop.
                # But let's verify if the file runs as is.
    except Exception as e:
        print(f"Note: Error during forced cleanup (ignored): {e}")

    print("Recreating all tables via Base.metadata...")
    Base.metadata.create_all(client._engine)
    print("Database tables initialized successfully.")


def run_demo():
    print("--- Starting ResearchDomain Advanced Demo ---")
    setup_database()

    try:
        # 1. Initialize Controllers
        uni_ctrl = UniversityController()
        campus_ctrl = CampusController()
        researcher_ctrl = ResearcherController()
        group_ctrl = ResearchGroupController()
        area_ctrl = KnowledgeAreaController()
        role_ctrl = RoleController()

        # 2. Create University and Campus
        ifes = uni_ctrl.create_university(
            name="Instituto Federal do Espirito Santo", short_name="IFES"
        )
    except Exception as e:
        print(f"Error during demo execution: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_demo()
