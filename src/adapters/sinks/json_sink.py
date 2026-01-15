import json
import os
from typing import Any, List

from loguru import logger
from pydantic import BaseModel

from src.core.ports.export_sink import IExportSink


class JsonSink(IExportSink):
    def export(self, data: List[Any], path: str) -> None:
        """
        Exports data to a JSON file.

        Args:
            data: List of Pydantic models or SQLAlchemy objects.
            path: Destination file path.
        """
        try:
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            # Internal serializer helper
            def serialize(obj):
                if isinstance(obj, dict):
                    return obj

                if isinstance(obj, BaseModel):
                    return obj.model_dump(mode="json")

                # Check for SQLAlchemy model (has __table__)
                if hasattr(obj, "__table__"):
                    # Serialize columns
                    result = {
                        c.name: getattr(obj, c.name) for c in obj.__table__.columns
                    }

                    # Attempt to include specific relationships requested (Leaders/Members)
                    # This is brittle if session is closed, but we try.
                    # Commonly for reports we want specific fields.
                    # For now, let's just do columns to be safe and compatible.
                    # If user needs relationships, accessing them here might fail if detached.
                    # We will add a 'try' block for common relationships if we want to risk it,
                    # but typically standard columns are safer.
                    return result

                if hasattr(obj, "__dict__"):
                    return obj.__dict__

                return str(obj)

            json_data = [serialize(item) for item in data]

            with open(path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)

            logger.info(f"Successfully exported {len(data)} items to {path}")

        except Exception as e:
            logger.error(f"Failed to export data to {path}: {e}")
            raise e
