"""Minimal, dependency-free schema migrations for the canonical SQLite database.

The project does not (yet) use Alembic. This module keeps schema changes out of
business logic: each migration is applied at most once and recorded in a
``schema_migrations`` table. ``ALTER TABLE ... ADD COLUMN`` is guarded so it is
idempotent even against databases where the column was already added by the
previous runtime-DDL stopgap.

Run at pipeline/app start, or lazily via ``ProjectEnrichmentLoader.ensure_schema``.
"""

from typing import List, Tuple

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# (id, SQL). Order matters; ids are immutable once shipped.
MIGRATIONS: List[Tuple[str, str]] = [
    (
        "0001_initiatives_enrichment_json",
        "ALTER TABLE initiatives ADD COLUMN enrichment_json TEXT",
    ),
]


def _applied_ids(session) -> set:
    session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(id TEXT PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
    )
    return {row[0] for row in session.execute(text("SELECT id FROM schema_migrations"))}


def run_migrations(session) -> int:
    """Applies pending migrations. Returns the number applied. Commits its own work."""
    applied = _applied_ids(session)
    count = 0
    for migration_id, sql in MIGRATIONS:
        if migration_id in applied:
            continue
        try:
            session.execute(text(sql))
        except OperationalError as exc:
            # ADD COLUMN on an already-migrated DB (legacy runtime DDL) is fine.
            if "duplicate column" not in str(exc).lower():
                session.rollback()
                raise
        session.execute(
            text("INSERT OR IGNORE INTO schema_migrations (id) VALUES (:id)"),
            {"id": migration_id},
        )
        count += 1
        logger.info("Applied migration {}", migration_id)
    session.commit()
    return count
