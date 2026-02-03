from typing import Optional

from eo_lib.domain.base import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from research_domain.domain.mixins import SerializableMixin

# Association Table for Many-to-Many
academic_education_knowledge_areas = Table(
    "academic_education_knowledge_areas",
    Base.metadata,
    Column("academic_education_id", Integer, ForeignKey("academic_educations.id"), primary_key=True),
    Column("knowledge_area_id", Integer, ForeignKey("knowledge_areas.id"), primary_key=True),
)

class AcademicEducation(Base, SerializableMixin):
    """
    Academic Education History Model.
    Represents a degree or certification held by a researcher.
    """
    __tablename__ = "academic_educations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    researcher_id = Column(Integer, ForeignKey("researchers.id"), nullable=False)
    education_type_id = Column(Integer, ForeignKey("education_types.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=True)
    thesis_title = Column(String(500), nullable=True)
    
    # Institution as FK to Organization
    institution_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Advisors as FK to Researcher
    # Using string referencing to avoid circular imports during definition
    advisor_id = Column(Integer, ForeignKey("researchers.id"), nullable=True)
    co_advisor_id = Column(Integer, ForeignKey("researchers.id"), nullable=True)

    # Relationships
    education_type = relationship("EducationType")
    researcher = relationship("Researcher", foreign_keys=[researcher_id], backref="academic_educations")
    institution = relationship("Organization")
    advisor = relationship("Researcher", foreign_keys=[advisor_id])
    co_advisor = relationship("Researcher", foreign_keys=[co_advisor_id])
    
    # Many-to-Many with KnowledgeArea
    knowledge_areas = relationship(
        "KnowledgeArea",
        secondary=academic_education_knowledge_areas,
        lazy="joined"
    )

    def __init__(
        self,
        researcher_id: int,
        education_type_id: int,
        title: str,
        institution_id: int,
        start_year: int,
        end_year: Optional[int] = None,
        thesis_title: Optional[str] = None,
        advisor_id: Optional[int] = None,
        co_advisor_id: Optional[int] = None,
        id: Optional[int] = None,
        **kwargs,
    ):
        self.id = id
        self.researcher_id = researcher_id
        self.education_type_id = education_type_id
        self.title = title
        self.institution_id = institution_id
        self.start_year = start_year
        self.end_year = end_year
        self.thesis_title = thesis_title
        self.advisor_id = advisor_id
        self.co_advisor_id = co_advisor_id
        
        # Helper for unit tests (not persisted by SQLAlchemy directly like this in relationship, but useful for in-memory)
        if kwargs.get("knowledge_areas"):
            self.knowledge_areas = kwargs.get("knowledge_areas")
        elif not hasattr(self, "knowledge_areas"):
            self.knowledge_areas = []
