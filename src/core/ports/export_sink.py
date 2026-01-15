from abc import ABC, abstractmethod
from typing import Any, List


class IExportSink(ABC):
    @abstractmethod
    def export(self, data: List[Any], path: str) -> None:
        """
        Exports a list of domain entities (Pydantic models or others) to a file.

        Args:
            data: List of objects to export.
            path: Destination file path.
        """
        pass
