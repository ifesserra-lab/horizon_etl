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
        patch("src.core.logic.canonical_exporter.OrganizationController"),
        patch("src.core.logic.canonical_exporter.CampusController"),
        patch("src.core.logic.canonical_exporter.KnowledgeAreaController"),
        patch("src.core.logic.canonical_exporter.ResearcherController"),
    ):

        exporter = CanonicalDataExporter(sink=mock_sink)

        # Inject mocks for new controllers that will be added
        exporter.initiative_ctrl = MagicMock()
        exporter.initiative_type_ctrl = MagicMock()

        return exporter


def test_export_initiatives(exporter, mock_sink):
    # Setup
    from datetime import datetime

    mock_data = [
        MockInitiative(1, "Project A", "Ongoing", 10),
        MockInitiative(2, "Project B", "Completed", 10),
    ]
    # Add additional attributes to mock
    mock_data[0].description = "Description A"
    mock_data[0].start_date = datetime(2024, 1, 1)
    mock_data[0].end_date = datetime(2025, 1, 1)
    mock_data[0].organization_id = None
    mock_data[0].parent_id = None

    mock_data[1].description = "Description B"
    mock_data[1].start_date = datetime(2024, 6, 1)
    mock_data[1].end_date = None
    mock_data[1].organization_id = None
    mock_data[1].parent_id = None

    exporter.initiative_ctrl.get_all.return_value = mock_data

    # Execute
    exporter.export_initiatives("output/initiatives.json")

    # Verify
    exporter.initiative_ctrl.get_all.assert_called_once()
    mock_sink.export.assert_called_once()

    exported_data = mock_sink.export.call_args[0][0]
    output_path = mock_sink.export.call_args[0][1]

    assert len(exported_data) == 2
    assert exported_data[0]["id"] == 1
    assert exported_data[0]["name"] == "Project A"
    assert exported_data[0]["status"] == "Ongoing"
    assert exported_data[0]["description"] == "Description A"
    assert exported_data[0]["start_date"] == "2024-01-01T00:00:00"
    assert exported_data[0]["end_date"] == "2025-01-01T00:00:00"
    assert exported_data[0]["initiative_type_id"] == 10
    assert output_path == "output/initiatives.json"


def test_export_initiative_types(exporter, mock_sink):
    # Setup
    mock_data = [
        MockInitiativeType(10, "Research Project"),
        MockInitiativeType(11, "Extension Project"),
    ]
    exporter.initiative_ctrl.list_initiative_types.return_value = mock_data

    # Execute
    exporter.export_initiative_types("output/types.json")

    # Verify
    exporter.initiative_ctrl.list_initiative_types.assert_called_once()
    mock_sink.export.assert_called_once()

    exported_data = mock_sink.export.call_args[0][0]

    assert len(exported_data) == 2
    assert exported_data[0]["name"] == "Research Project"
