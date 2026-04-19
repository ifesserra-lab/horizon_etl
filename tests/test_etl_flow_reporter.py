import sqlite3
from pathlib import Path

from src.core.logic.etl_flow_reporter import ETLFlowReporter


def test_etl_flow_reporter_records_entity_deltas_and_writes_files(tmp_path: Path):
    db_path = tmp_path / "audit.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE persons (id INTEGER PRIMARY KEY, name TEXT, identification_id TEXT);
        CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE knowledge_areas (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE person_emails (id INTEGER PRIMARY KEY, person_id INTEGER, email TEXT);
        CREATE TABLE organizations (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE organizational_units (id INTEGER PRIMARY KEY, name TEXT, organization_id INTEGER);
        CREATE TABLE roles (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE initiative_types (id INTEGER PRIMARY KEY, name TEXT);
        """
    )
    conn.commit()
    conn.close()

    reporter = ETLFlowReporter(
        db_path=str(db_path),
        output_dir=str(tmp_path),
        run_name="sample_etl_run",
    )

    def runner():
        with sqlite3.connect(db_path) as local_conn:
            local_conn.execute("INSERT INTO persons (id, name) VALUES (1, 'Pessoa')")
            local_conn.commit()

    reporter.run_step(
        step_name="sample_step",
        runner=runner,
        source_probe=lambda: {
            "origin": "sample_origin",
            "files": ["sample.csv"],
            "extracted_counts": {"rows": 1},
        },
    )
    json_path, md_path = reporter.write()

    assert json_path.exists()
    assert md_path.exists()
    assert json_path.name.startswith("sample_etl_run_")
    assert md_path.name.startswith("sample_etl_run_")
    assert (tmp_path / "sample_etl_run.json").exists()
    assert (tmp_path / "sample_etl_run.md").exists()
    content = md_path.read_text(encoding="utf-8")
    assert "sample_step" in content
    assert "sample_origin" in content
    assert "persons" in content


def test_etl_flow_reporter_records_warnings_by_source(tmp_path: Path):
    db_path = tmp_path / "audit.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE persons (id INTEGER PRIMARY KEY, name TEXT, identification_id TEXT);
        CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE knowledge_areas (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE person_emails (id INTEGER PRIMARY KEY, person_id INTEGER, email TEXT);
        CREATE TABLE organizations (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE organizational_units (id INTEGER PRIMARY KEY, name TEXT, organization_id INTEGER);
        CREATE TABLE roles (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE initiative_types (id INTEGER PRIMARY KEY, name TEXT);
        """
    )
    conn.commit()
    conn.close()

    reporter = ETLFlowReporter(
        db_path=str(db_path),
        output_dir=str(tmp_path),
        run_name="warning_run",
    )

    def runner():
        with sqlite3.connect(db_path) as local_conn:
            local_conn.executemany(
                "INSERT INTO persons (id, name) VALUES (?, ?)",
                [
                    (1, "ui-button"),
                    (2, "Maria Silva"),
                    (3, "Maria  Silva"),
                ],
            )
            local_conn.commit()

    reporter.run_step(step_name="cnpq_sync", runner=runner)
    json_path, md_path = reporter.write()

    report = json_path.read_text(encoding="utf-8")
    content = md_path.read_text(encoding="utf-8")

    assert '"warnings_by_source"' in report
    assert "cnpq_placeholder_member_name" in report
    assert "duplicate_count_increased" in report
    assert "## Warnings por Fonte" in content
    assert "cnpq_placeholder_member_name" in content
