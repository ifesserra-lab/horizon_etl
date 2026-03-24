from typing import Any, Optional

from libbase.services.generic_service import GenericService

from src.tracking.entities import EntityChangeLog


class EntityChangeLogService(GenericService[EntityChangeLog]):
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
        change_log = EntityChangeLog(
            ingestion_run_id=ingestion_run_id,
            source_record_id=source_record_id,
            canonical_entity_type=canonical_entity_type,
            canonical_entity_id=canonical_entity_id,
            operation=operation,
            changed_fields_json=changed_fields_json,
            before_json=before_json,
            after_json=after_json,
            reason=reason,
        )
        self.create(change_log)
        return change_log
