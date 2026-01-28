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
            # Should be called 8 times (Org, Campus, KA, Researcher, Initiatives, InitiativeTypes, Advisorships, Fellowships)
            assert mock_sink.export.call_count == 8

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
                }
            ]
            assert "researchers_canonical.json" in args[1]
