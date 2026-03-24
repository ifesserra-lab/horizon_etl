from typing import Any, Optional

from libbase.controllers.generic_controller import GenericController

from src.tracking.entities import EntityChangeLog
from src.tracking.service_factory import TrackingServiceFactory
from src.tracking.services import EntityChangeLogService


class EntityChangeLogController(GenericController[EntityChangeLog]):
    def __init__(self, service: Optional[EntityChangeLogService] = None):
        super().__init__(
            service or TrackingServiceFactory.create_entity_change_log_service()
        )

    def create_change_log(
        self,
        *,
        ingestion_run_id: int,
        canonical_entity_type: str,
        canonical_entity_id: int,
        operation: str,
        source_record_id: Optional[int] = None,
        changed_fields_json: Optional[Any] = None,
        before_json: Optional[Any] = None,
        after_json: Optional[Any] = None,
        reason: Optional[str] = None,
    ) -> EntityChangeLog:
        return self._service.create_change_log(
            ingestion_run_id=ingestion_run_id,
            canonical_entity_type=canonical_entity_type,
            canonical_entity_id=canonical_entity_id,
            operation=operation,
            source_record_id=source_record_id,
            changed_fields_json=changed_fields_json,
            before_json=before_json,
            after_json=after_json,
            reason=reason,
        )
