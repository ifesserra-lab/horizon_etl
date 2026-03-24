from unittest.mock import MagicMock, patch

from src.core.logic.canonical_exporter import CanonicalDataExporter
from src.core.ports.export_sink import IExportSink


def test_export_all_orchestrates_exports():
    # Arrange
    mock_sink = MagicMock(spec=IExportSink)

    with (
        patch(
            "src.core.logic.canonical_exporter.OrganizationController"
        ) as MockOrgCtrl,
        patch("src.core.logic.canonical_exporter.CampusController") as MockCampCtrl,
        patch(
            "src.core.logic.canonical_exporter.KnowledgeAreaController"
        ) as MockKaCtrl,
        patch(
            "src.core.logic.canonical_exporter.ResearcherController"
        ) as MockResearcherCtrl,
        patch(
            "src.core.logic.canonical_exporter.InitiativeController"
        ) as MockInitCtrl,
        patch(
            "src.core.logic.canonical_exporter.ResearchGroupController"
        ) as MockRGCtrl,
        patch(
            "eo_lib.TeamController"
        ) as MockTeamCtrl,
    ):


        # Mock Instances
        mock_org_instance = MockOrgCtrl.return_value
        mock_camp_instance = MockCampCtrl.return_value
        mock_ka_instance = MockKaCtrl.return_value
        mock_researcher_instance = MockResearcherCtrl.return_value
        mock_init_instance = MockInitCtrl.return_value
        mock_rg_instance = MockRGCtrl.return_value
        mock_team_instance = MockTeamCtrl.return_value

        # Mock Data (Simple objects or dicts)
        # Using objects with to_dict for completeness
        mock_org = MagicMock()
        mock_org.to_dict.return_value = {"id": 1, "name": "Org1"}
        mock_org_instance.get_all.return_value = [mock_org]

        mock_camp = MagicMock()
        mock_camp.to_dict.return_value = {"id": 10, "name": "Campus1"}
        mock_camp_instance.get_all.return_value = [mock_camp]

        mock_ka = MagicMock()
        mock_ka.to_dict.return_value = {"id": 100, "name": "Area1"}
        mock_ka_instance.get_all.return_value = [mock_ka]

        mock_researcher = MagicMock()
        mock_researcher.to_dict.return_value = {"id": 1000, "name": "Researcher1"}
        mock_researcher_instance.get_all.return_value = [mock_researcher]
        
        # Mock Initiative Data
        mock_init = MagicMock()
        mock_init.id = 500
        mock_init.name = "Init1"
        # Need dates for isoformat call
        from datetime import datetime
        mock_init.start_date = datetime(2023, 1, 1)
        mock_init.end_date = datetime(2023, 12, 31)
        mock_init.initiative_type_id = 1
        mock_init.organization_id = 1
        mock_init.parent_id = None
        mock_init.status = "active"
        mock_init.status = "active"
        mock_init.description = "desc"
        mock_init.metadata = {
            "external_partner": "Partner A",
            "external_research_group": "Group B",
        }
        
        mock_init_instance.get_all.return_value = [mock_init]
        mock_init_instance.list_initiative_types.return_value = [{"id": 1, "name": "Type1"}]
        mock_init_instance.get_teams.return_value = [{"id": 90}]
        
        # Mock Team
        mock_team_member = MagicMock()
        mock_team_member.person_id = 99
        mock_team_member.person.name = "Person1"
        mock_team_member.role.name = "Role1"
        mock_team_member.start_date = datetime(2023, 1, 1)
        mock_team_member.end_date = None
        mock_team_instance.get_members.return_value = [mock_team_member]
        
        # Mock RG
        mock_rg = MagicMock()
        mock_rg.id = 90
        mock_rg.name = "RG1"
        mock_rg_instance.get_all.return_value = [mock_rg]

        exporter = CanonicalDataExporter(sink=mock_sink)

        # Act
        with patch("os.makedirs") as mock_makedirs:
            exporter.export_all("data/exports")

            # Assert
            mock_makedirs.assert_called_once()

            # Verify Sink Calls
            # Includes canonical exports plus the parallel tracking exports.
            assert mock_sink.export.call_count == 12

            # Check call args to verify content
            calls = mock_sink.export.call_args_list

            # Organization export
            args, _ = calls[0]
            assert args[0] == [{"id": 1, "name": "Org1"}]
            assert "organizations_canonical.json" in args[1]

            # Campus export
            args, _ = calls[1]
            assert args[0] == [{"id": 10, "name": "Campus1"}]
            assert "campuses_canonical.json" in args[1]

            # Knowledge Area export
            args, _ = calls[2]
            assert args[0] == [{"id": 100, "name": "Area1"}]
            assert "knowledge_areas_canonical.json" in args[1]

            # Researcher export
            args, _ = calls[3]
            assert args[0] == [
                {
                    "id": 1000,
                    "name": "Researcher1",
                    "initiatives": [],
                    "research_groups": [],
                    "knowledge_areas": [],
                    "academic_education": [],
                    "articles": [],
                    "advisorships": [],
                }
            ]
            assert "researchers_canonical.json" in args[1]

            # Researchers tracking export
            args, _ = calls[4]
            assert args[0] == []
            assert "researchers_tracking.json" in args[1]


def test_export_researchers_tracking_builds_parallel_payload():
    mock_sink = MagicMock(spec=IExportSink)

    with (
        patch("src.core.logic.canonical_exporter.OrganizationController"),
        patch("src.core.logic.canonical_exporter.CampusController"),
        patch("src.core.logic.canonical_exporter.KnowledgeAreaController"),
        patch("src.core.logic.canonical_exporter.ResearcherController"),
        patch("src.core.logic.canonical_exporter.InitiativeController"),
    ):
        exporter = CanonicalDataExporter(sink=mock_sink)

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class FakeSession:
        def execute(self, statement, params=None):
            statement_text = getattr(statement, "text", str(statement))
            if "FROM entity_matches" in statement_text and "JOIN source_records sr" not in statement_text:
                return FakeResult([{"entity_id": 2981}])
            if "FROM entity_matches em" in statement_text:
                return FakeResult(
                    [
                        {
                            "entity_id": 2981,
                            "source_system": "lattes",
                            "source_entity_type": "researcher_profile",
                            "source_record_id": "8400407353673370",
                            "source_file": "data/lattes_json/00_Paulo.json",
                            "source_path": "$.dados_gerais",
                            "match_strategy": "lattes_id_exact",
                            "match_confidence": 1,
                            "matched_at": "2026-03-23T10:00:00",
                        }
                    ]
                )
            if "FROM attribute_assertions aa" in statement_text:
                return FakeResult(
                    [
                        {
                            "entity_id": 2981,
                            "attribute_name": "resume",
                            "value_json": {"text": "Resumo atualizado"},
                            "value_hash": "abc123",
                            "is_selected": 1,
                            "selection_reason": "preferred_lattes_resume",
                            "asserted_at": "2026-03-23T10:01:00",
                            "source_record_pk": 77,
                            "source_system": "lattes",
                            "source_entity_type": "researcher_profile",
                            "source_record_id": "8400407353673370",
                            "source_file": "data/lattes_json/00_Paulo.json",
                            "source_path": "$.resumo_cv",
                        }
                    ]
                )
            if "FROM entity_change_logs ecl" in statement_text:
                return FakeResult(
                    [
                        {
                            "entity_id": 2981,
                            "operation": "create",
                            "changed_fields_json": ["name", "resume"],
                            "before_json": None,
                            "after_json": {"id": 2981},
                            "reason": "lattes researcher import",
                            "changed_at": "2026-03-23T10:02:00",
                            "run_id": 12,
                            "run_source_system": "lattes",
                            "flow_name": "ingest_lattes_projects",
                            "run_status": "completed",
                            "source_record_pk": 77,
                            "source_record_system": "lattes",
                            "source_entity_type": "researcher_profile",
                            "source_record_id": "8400407353673370",
                            "source_file": "data/lattes_json/00_Paulo.json",
                            "source_path": "$.dados_gerais",
                        }
                    ]
                )
            return FakeResult([])

    exporter._has_tracking_schema = lambda: True
    exporter._get_session = lambda: FakeSession()

    exporter.export_researchers_tracking("output/researchers_tracking.json")

    mock_sink.export.assert_called_once()
    exported_data, output_path = mock_sink.export.call_args[0]

    assert output_path == "output/researchers_tracking.json"
    assert exported_data[0]["entity_type"] == "researcher"
    assert exported_data[0]["entity_id"] == 2981
    assert exported_data[0]["sources"] == ["lattes"]
    assert exported_data[0]["attributes"]["resume"]["selected_from"] == "lattes"
    assert exported_data[0]["created_by"]["operation"] == "create"
    assert exported_data[0]["last_updated_by"]["flow_name"] == "ingest_lattes_projects"
