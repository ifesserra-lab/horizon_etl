"""Helpers for creating researchers across inconsistent library versions."""

from typing import Optional

from loguru import logger
from sqlalchemy import text


def create_researcher_with_resume_fallback(
    researcher_ctrl,
    *,
    name: str,
    identification_id: Optional[str] = None,
    emails: Optional[list[str]] = None,
):
    """Create a researcher, tolerating controller/service signature mismatches.

    Some `research-domain` controller versions still forward `resume=None` to
    an `eo-lib` service implementation that no longer accepts that keyword.
    When that specific mismatch happens, call the underlying service method
    without `resume`, then ensure the joined-table `researchers` row exists.
    """

    try:
        return researcher_ctrl.create_researcher(
            name=name,
            emails=emails,
            identification_id=identification_id,
        )
    except TypeError as exc:
        if "resume" not in str(exc):
            raise

        logger.warning(
            f"Falling back to direct Researcher creation for '{name}' due to controller/service signature mismatch."
        )
        researcher = researcher_ctrl._service.create_with_details(
            name=name,
            emails=emails,
            identification_id=identification_id,
        )
        _ensure_researcher_row(researcher_ctrl, researcher.id)

        try:
            return researcher_ctrl.get_by_id(researcher.id)
        except Exception:
            return researcher


def _ensure_researcher_row(researcher_ctrl, person_id: Optional[int]) -> None:
    """Backfill joined-table inheritance row when only `persons` was inserted."""
    if not person_id:
        return

    try:
        session = researcher_ctrl._service._repository._session
        exists = session.execute(
            text("SELECT 1 FROM researchers WHERE id = :rid"),
            {"rid": person_id},
        ).scalar()
        if not exists:
            session.execute(
                text("INSERT INTO researchers (id) VALUES (:rid)"),
                {"rid": person_id},
            )
            session.commit()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
        raise
