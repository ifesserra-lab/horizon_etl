from typing import Any, Optional

from libbase.services.generic_service import GenericService

from src.tracking.entities import SourceRecord


class SourceRecordService(GenericService[SourceRecord]):
    def create_source_record(
        self,
        *,
        ingestion_run_id: int,
        source_system: str,
        source_entity_type: str,
        payload_hash: str,
        source_record_id: Optional[str] = None,
        source_file: Optional[str] = None,
        source_path: Optional[str] = None,
        raw_payload_json: Optional[Any] = None,
    ) -> SourceRecord:
        record = SourceRecord(
            ingestion_run_id=ingestion_run_id,
            source_system=source_system,
            source_entity_type=source_entity_type,
            source_record_id=source_record_id,
            source_file=source_file,
            source_path=source_path,
            raw_payload_json=raw_payload_json,
            payload_hash=payload_hash,
        )
        self.create(record)
        return record
