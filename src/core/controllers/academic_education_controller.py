from typing import Dict, List, Optional

from eo_lib.infrastructure.database.postgres_client import PostgresClient
from loguru import logger
from sqlalchemy.orm import Session

from src.core.domain.academic_education import AcademicEducation


class AcademicEducationController:
    """
    Controller for managing AcademicEducation entities.
    """

    def __init__(self, session: Optional[Session] = None):
        self._session = session
        if not self._session:
            self.client = PostgresClient()
            self._session = self.client.get_session()

    def create(self, education: AcademicEducation) -> AcademicEducation:
        """Create a new AcademicEducation record."""
        try:
            self._session.add(education)
            self._session.commit()
            logger.info(f"Created AcademicEducation for researcher {education.researcher_id}: {education.title}")
            return education
        except Exception as e:
            self._session.rollback()
            logger.error(f"Failed to create AcademicEducation: {e}")
            raise e

    def get_by_researcher(self, researcher_id: int) -> List[AcademicEducation]:
        """Get all education records for a researcher."""
        return (
            self._session.query(AcademicEducation)
            .filter(AcademicEducation.researcher_id == researcher_id)
            .all()
        )
