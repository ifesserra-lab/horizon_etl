from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from eo_lib.domain.base import Base
from libbase.infrastructure.sql_repository import GenericSqlRepository
from src.tracking.entities import (
    AttributeAssertion,
    EntityChangeLog,
    EntityMatch,
    IngestionRun,
    SourceRecord,
)
from src.tracking.services import (
    AttributeAssertionService,
    EntityChangeLogService,
    EntityMatchService,
    IngestionRunService,
    SourceRecordService,
)


def test_tracking_domain_entities_persist_end_to_end():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()

    run_service = IngestionRunService(GenericSqlRepository(session, IngestionRun))
    source_service = SourceRecordService(GenericSqlRepository(session, SourceRecord))
    match_service = EntityMatchService(GenericSqlRepository(session, EntityMatch))
    assertion_service = AttributeAssertionService(
        GenericSqlRepository(session, AttributeAssertion)
    )
    change_log_service = EntityChangeLogService(
        GenericSqlRepository(session, EntityChangeLog)
    )

    run = run_service.create_run(source_system="lattes", flow_name="ingest_lattes")
    record = source_service.create_source_record(
        ingestion_run_id=run.id,
        source_system="lattes",
        source_entity_type="researcher",
        source_record_id="8400407353673370",
        source_file="00_Paulo.json",
        source_path="data/lattes_json/00_Paulo.json",
        raw_payload_json={"nome": "Paulo"},
        payload_hash="hash-1",
    )
    entity_match = match_service.create_match(
        source_record_id=record.id,
        canonical_entity_type="researcher",
        canonical_entity_id=2981,
        match_strategy="lattes_id_exact",
        match_confidence=1.0,
    )
    assertion = assertion_service.create_assertion(
        source_record_id=record.id,
        canonical_entity_type="researcher",
        canonical_entity_id=2981,
        attribute_name="resume",
        value_hash="hash-resume",
        value_json={"resume": "texto"},
        is_selected=True,
        selection_reason="lattes_preferred",
    )
    change_log = change_log_service.create_change_log(
        ingestion_run_id=run.id,
        source_record_id=record.id,
        canonical_entity_type="researcher",
        canonical_entity_id=2981,
        operation="update",
        changed_fields_json=["resume"],
        before_json={"resume": None},
        after_json={"resume": "texto"},
        reason="Updated from Lattes",
    )
    finalized = run_service.finalize_run(run.id, status="success")

    assert run.id is not None
    assert record.id is not None
    assert entity_match.id is not None
    assert assertion.id is not None
    assert change_log.id is not None
    assert finalized.status == "success"
    assert finalized.finished_at is not None
