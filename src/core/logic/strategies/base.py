from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

class OrganizationStrategy(ABC):
    @abstractmethod
    def ensure(self, uni_ctrl) -> int:
        pass

class CampusStrategy(ABC):
    @abstractmethod
    def ensure(self, campus_ctrl, campus_name: str, org_id: int) -> int:
        pass

class KnowledgeAreaStrategy(ABC):
    @abstractmethod
    def ensure(self, area_ctrl, area_name: str) -> Optional[int]:
        pass

class ResearcherStrategy(ABC):
    @abstractmethod
    def ensure(self, researcher_ctrl, name: str, email: str = None):
        pass

class RoleStrategy(ABC):
    @abstractmethod
    def ensure_leader(self, role_ctrl):
        pass

class ResearchGroupMappingStrategy(ABC):
    """Base interface for Research Group mapping strategies."""

    @abstractmethod
    def map_row(self, row: dict) -> dict:
        """
        Maps a raw row from the source into a standardized format.
        Expected keys in returned dict:
            - name (str)
            - short_name (str)
            - campus_name (str)
            - area_name (str)
            - site_url (str)
            - leaders_raw (str)
        """
        pass

    @abstractmethod
    def parse_leaders(self, leaders_str: str) -> List[Tuple[str, Optional[str]]]:
        """
        Parses a string of leaders into a list of (name, email) tuples.
        """
        pass
