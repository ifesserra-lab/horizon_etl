from abc import ABC, abstractmethod
from typing import Any, List


class ISource(ABC):
    @abstractmethod
    def extract(self) -> List[Any]:
        """
        Executes the extraction process.
        Returns a list of raw data (or paths to data) extracted from the source.
        """
        pass
