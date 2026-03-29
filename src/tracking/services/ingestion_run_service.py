from datetime import UTC, datetime
from typing import Optional

from libbase.services.generic_service import GenericService

from src.tracking.entities import IngestionRun


class IngestionRunService(GenericService[IngestionRun]):
    def create_run(
        self,
        *,
        source_system: str,
        flow_name: str,
        status: str = "running",
        input_snapshot_hash: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> IngestionRun:
        run = IngestionRun(
            source_system=source_system,
            flow_name=flow_name,
            status=status,
            input_snapshot_hash=input_snapshot_hash,
            notes=notes,
        )
        self.create(run)
        return run

    def finalize_run(
        self,
        run_id: int,
        *,
        status: str,
        finished_at: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> IngestionRun:
        run = self.get_by_id(run_id)
        if not run:
            raise ValueError(f"IngestionRun {run_id} not found")
        run.status = status
        run.finished_at = finished_at or datetime.now(UTC)
        if notes is not None:
            run.notes = notes
        self.update(run)
        return run
