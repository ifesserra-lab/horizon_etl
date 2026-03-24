import os
import sqlite3
import sys

sys.path.append(os.getcwd())


SAFE_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_roles_name ON roles(name)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_initiative_types_name ON initiative_types(name)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_organizations_name ON organizations(name)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_person_emails_lower_email ON person_emails(lower(email))",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_org_units_name_org ON organizational_units(name, organization_id)",
    "CREATE INDEX IF NOT EXISTS ix_teams_lower_name ON teams(lower(name))",
    "CREATE INDEX IF NOT EXISTS ix_knowledge_areas_lower_name ON knowledge_areas(lower(name))",
    "CREATE INDEX IF NOT EXISTS ix_persons_lower_name ON persons(lower(name))",
    "CREATE INDEX IF NOT EXISTS ix_initiatives_lower_name ON initiatives(lower(name))",
]


def main():
    conn = sqlite3.connect("db/horizon.db")
    try:
        cur = conn.cursor()
        for stmt in SAFE_INDEXES:
            cur.execute(stmt)
        conn.commit()
        print("Database hardening indexes created successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
