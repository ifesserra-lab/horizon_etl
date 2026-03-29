import hashlib
import json
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Iterable, Optional

from sqlalchemy.exc import IntegrityError

from src.tracking.context import current_ingestion_run_id, current_source_system
from src.tracking.controllers import (
    AttributeAssertionController,
    EntityChangeLogController,
    EntityMatchController,
    IngestionRunController,
    SourceRecordController,
)


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TrackingRecorder:
    def __init__(self):
        self._ingestion_run_controller_cls = IngestionRunController
        self._source_record_controller_cls = SourceRecordController
        self._entity_match_controller_cls = EntityMatchController
        self._attribute_assertion_controller_cls = AttributeAssertionController
        self._entity_change_log_controller_cls = EntityChangeLogController

    @contextmanager
    def _controller(self, controller_cls):
        controller = controller_cls()
        session = controller._service._repository._session
        try:
            yield controller
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def run_context(self, *, source_system: str, flow_name: str, notes: Optional[str] = None):
        with self._controller(self._ingestion_run_controller_cls) as controller:
            run = controller.create_run(
                source_system=source_system,
                flow_name=flow_name,
                notes=notes,
            )
            run_id = run.id
        run_token = current_ingestion_run_id.set(run_id)
        source_token = current_source_system.set(source_system)
        try:
            yield SimpleNamespace(id=run_id, source_system=source_system, flow_name=flow_name)
            with self._controller(self._ingestion_run_controller_cls) as controller:
                controller.finalize_run(run_id, status="success")
        except Exception as exc:
            with self._controller(self._ingestion_run_controller_cls) as controller:
                controller.finalize_run(run_id, status="failed", notes=str(exc))
            raise
        finally:
            current_ingestion_run_id.reset(run_token)
            current_source_system.reset(source_token)

    def has_active_run(self) -> bool:
        return current_ingestion_run_id.get() is not None

    def record_source_record(
        self,
        *,
        source_entity_type: str,
        payload: Any,
        source_record_id: Optional[str] = None,
        source_file: Optional[str] = None,
        source_path: Optional[str] = None,
    ):
        run_id = current_ingestion_run_id.get()
        source_system = current_source_system.get()
        if not run_id or not source_system:
            return None

        payload_hash = stable_hash(payload)
        with self._controller(self._source_record_controller_cls) as controller:
            try:
                return controller.create_source_record(
                    ingestion_run_id=run_id,
                    source_system=source_system,
                    source_entity_type=source_entity_type,
                    source_record_id=source_record_id,
                    source_file=source_file,
                    source_path=source_path,
                    raw_payload_json=payload,
                    payload_hash=payload_hash,
                )
            except IntegrityError:
                session = controller._service._repository._session
                session.rollback()
                return (
                    session.query(controller._service._repository._entity_type)
                    .filter_by(
                        ingestion_run_id=run_id,
                        source_system=source_system,
                        source_entity_type=source_entity_type,
                        source_record_id=source_record_id,
                        payload_hash=payload_hash,
                    )
                    .first()
                )

    def record_entity_match(
        self,
        *,
        source_record_id: Optional[int],
        canonical_entity_type: str,
        canonical_entity_id: int,
        match_strategy: str,
        match_confidence: Optional[float] = None,
    ):
        if not source_record_id:
            return None
        with self._controller(self._entity_match_controller_cls) as controller:
            try:
                return controller.create_match(
                    source_record_id=source_record_id,
                    canonical_entity_type=canonical_entity_type,
                    canonical_entity_id=canonical_entity_id,
                    match_strategy=match_strategy,
                    match_confidence=match_confidence,
                )
            except IntegrityError:
                session = controller._service._repository._session
                session.rollback()
                return None

    def record_attribute_assertions(
        self,
        *,
        source_record_id: Optional[int],
        canonical_entity_type: str,
        canonical_entity_id: int,
        selected_attributes: dict[str, Any],
        selection_reason: str,
    ) -> None:
        if not source_record_id:
            return
        for attribute_name, value in selected_attributes.items():
            with self._controller(self._attribute_assertion_controller_cls) as controller:
                try:
                    controller.create_assertion(
                        source_record_id=source_record_id,
                        canonical_entity_type=canonical_entity_type,
                        canonical_entity_id=canonical_entity_id,
                        attribute_name=attribute_name,
                        value_hash=stable_hash(value),
                        value_json=_json_safe(value),
                        is_selected=True,
                        selection_reason=selection_reason,
                    )
                except IntegrityError:
                    session = controller._service._repository._session
                    session.rollback()

    def record_change(
        self,
        *,
        source_record_id: Optional[int],
        canonical_entity_type: str,
        canonical_entity_id: int,
        operation: str,
        changed_fields: Iterable[str],
        before: Optional[dict[str, Any]] = None,
        after: Optional[dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> None:
        run_id = current_ingestion_run_id.get()
        if not run_id:
            return
        with self._controller(self._entity_change_log_controller_cls) as controller:
            controller.create_change_log(
                ingestion_run_id=run_id,
                source_record_id=source_record_id,
                canonical_entity_type=canonical_entity_type,
                canonical_entity_id=canonical_entity_id,
                operation=operation,
                changed_fields_json=_json_safe(list(changed_fields)),
                before_json=_json_safe(before),
                after_json=_json_safe(after),
                reason=reason,
            )


tracking_recorder = TrackingRecorder()
