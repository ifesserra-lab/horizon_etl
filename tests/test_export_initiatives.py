from unittest.mock import MagicMock, patch

import pytest

from src.core.logic.canonical_exporter import CanonicalDataExporter


# Mock Entities
class MockInitiative:
    def __init__(self, id, name, status, initiative_type_id=None):
        self.id = id
        self.name = name
        self.status = status
        self.initiative_type_id = initiative_type_id
        self.description = None
        self.start_date = None
        self.end_date = None
        self.organization_id = None
        self.parent_id = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "initiative_type_id": self.initiative_type_id,
            "description": self.description,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "organization_id": self.organization_id,
            "parent_id": self.parent_id,
        }


class MockInitiativeType:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def to_dict(self):
        return {"id": self.id, "name": self.name}


@pytest.fixture
def mock_sink():
    return MagicMock()


@pytest.fixture
def exporter(mock_sink):
    # Mocking Controllers inside CanonicalDataExporter initialization
    with (
        patch("src.core.logic.canonical_exporter.OrganizationController") as mock_org_ctrl,
        patch("src.core.logic.canonical_exporter.CampusController"),
        patch("src.core.logic.canonical_exporter.KnowledgeAreaController"),
        patch("src.core.logic.canonical_exporter.ResearcherController"),
        patch("src.core.logic.canonical_exporter.InitiativeController") as mock_init_ctrl,
    ):

        exporter = CanonicalDataExporter(sink=mock_sink)
        exporter.initiative_ctrl = mock_init_ctrl.return_value
        exporter.org_ctrl = mock_org_ctrl.return_value

        return exporter


def test_export_initiatives(exporter, mock_sink):
    # Setup
    from datetime import datetime

    mock_data = [
        MockInitiative(1, "Project A", "Ongoing", 10),
    ]
    mock_data[0].description = "Description A"
    mock_data[0].start_date = datetime(2024, 1, 1)
    mock_data[0].end_date = datetime(2025, 1, 1)
    mock_data[0].organization_id = 100
    mock_data[0].parent_id = None

    exporter.initiative_ctrl.get_all.return_value = mock_data

    # Mock Initiative Types
    mock_type = MockInitiativeType(10, "Research Project")
    mock_type.description = "Type Description"
    exporter.initiative_ctrl.list_initiative_types.return_value = [mock_type]

    # Mock Organizations
    mock_org = MagicMock()
    mock_org.id = 100
    mock_org.name = "Organization X"
    mock_org.short_name = "ORG-X"
    exporter.org_ctrl.get_all.return_value = [mock_org]

    # Mock Teams and Members
    exporter.initiative_ctrl.get_teams.return_value = [{"id": 50}]

    mock_member = MagicMock()
    mock_member.person_id = 200
    mock_member.person.name = "Person A"
    mock_member.role.name = "Coordinator"
    mock_member.start_date = datetime(2024, 1, 1)
    mock_member.end_date = None

    with patch("eo_lib.TeamController") as mock_team_ctrl:
        mock_team_ctrl.return_value.get_members.return_value = [mock_member]

        # Execute
        exporter.export_initiatives("output/initiatives.json")

    # Verify
    exporter.initiative_ctrl.get_all.assert_called_once()
    mock_sink.export.assert_called_once()

    exported_data = mock_sink.export.call_args[0][0]
    assert len(exported_data) == 1
    item = exported_data[0]

    assert item["id"] == 1
    assert item["initiative_type"]["name"] == "Research Project"
    assert item["organization"]["name"] == "Organization X"
    assert item["organization"]["short_name"] == "ORG-X"
    assert len(item["team"]) == 1
    assert item["team"][0]["person_name"] == "Person A"
    assert item["team"][0]["role"] == "Coordinator"
    assert item["team"][0]["start_date"] == "2024-01-01T00:00:00"


def test_export_initiative_types(exporter, mock_sink):
    # Setup
    mock_data = [
        MockInitiativeType(10, "Research Project"),
    ]
    exporter.initiative_ctrl.list_initiative_types.return_value = mock_data

    # Execute
    exporter.export_initiative_types("output/types.json")

    # Verify
    exporter.initiative_ctrl.list_initiative_types.assert_called_once()
    mock_sink.export.assert_called_once()
