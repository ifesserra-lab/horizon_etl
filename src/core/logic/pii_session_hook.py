"""
LGPD enforcement: SQLAlchemy before_flush hook.

Automatically anonymizes PII attributes on any ORM object before it is
written to the database. This ensures LGPD compliance regardless of which
code path triggers the write — no individual call site needs to remember to
call anonymize_person_data().

Register once at startup via install_lgpd_session_hooks().
"""

from sqlalchemy import event
from sqlalchemy.orm import Session

from src.core.logic.pii_anonymizer import PII_COLUMN_REGISTRY, anonymize_field

_PII_ATTRS: frozenset[str] = frozenset(PII_COLUMN_REGISTRY)
_installed = False


def _anonymize_orm_obj(obj: object) -> None:
    for attr in _PII_ATTRS:
        if not hasattr(obj, attr):
            continue
        raw = getattr(obj, attr)
        if raw is None:
            continue
        field_type = PII_COLUMN_REGISTRY[attr]
        anon = anonymize_field(raw, field_type)
        if anon != raw:
            setattr(obj, attr, anon)


def _before_flush(session: Session, flush_context, instances) -> None:
    for obj in list(session.new) + list(session.dirty):
        _anonymize_orm_obj(obj)


def install_lgpd_session_hooks() -> None:
    global _installed
    if _installed:
        return
    event.listen(Session, "before_flush", _before_flush)
    _installed = True
