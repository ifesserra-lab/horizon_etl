from typing import Optional
from eo_lib.domain.base import Base
from sqlalchemy import Column, Integer, String
from research_domain.domain.mixins import SerializableMixin

class EducationType(Base, SerializableMixin):
    """
    Education Type Model (e.g., Graduation, Master, Doctorate).
    """
    __tablename__ = "education_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    def __init__(self, name: str, id: Optional[int] = None, **kwargs):
        self.id = id
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, EducationType):
            return False
        return self.id == other.id and self.name == other.name
