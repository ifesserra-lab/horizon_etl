from abc import ABC, abstractmethod
from typing import List, Any

class ISink(ABC):
    @abstractmethod
    def load(self, data: List[Any]) -> None:
        """Persiste dados cuidando de Upserts/Deduplicação."""
        pass
