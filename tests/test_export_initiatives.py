import pytest
from unittest.mock import MagicMock, patch
from src.core.logic.canonical_exporter import CanonicalDataExporter

# Mock Entities
class MockInitiative:
    def __init__(self, id, name, status, initiative_type_id=None):
        self.id = id
        self.name = name
        self.status = status
        self.initiative_type_id = initiative_type_id

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "initiative_type_id": self.initiative_type_id
        }

class MockInitiativeType:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }

@pytest.fixture
def mock_sink():
    return MagicMock()

@pytest.fixture
def exporter(mock_sink):
    # Mocking Controllers inside CanonicalDataExporter initialization
    with patch('src.core.logic.canonical_exporter.OrganizationController'), \
         patch('src.core.logic.canonical_exporter.CampusController'), \
         patch('src.core.logic.canonical_exporter.KnowledgeAreaController'), \
         patch('src.core.logic.canonical_exporter.ResearcherController'):
         
        exporter = CanonicalDataExporter(sink=mock_sink)
        
        # Inject mocks for new controllers that will be added
        exporter.initiative_ctrl = MagicMock()
        exporter.initiative_type_ctrl = MagicMock()
        
        return exporter

def test_export_initiatives(exporter, mock_sink):
    # Setup
    mock_data = [
        MockInitiative(1, "Project A", "Ongoing", 10),
        MockInitiative(2, "Project B", "Completed", 10)
    ]
    exporter.initiative_ctrl.get_all.return_value = mock_data

    # Execute
    exporter.export_initiatives("output/initiatives.json")

    # Verify
    exporter.initiative_ctrl.get_all.assert_called_once()
    mock_sink.export.assert_called_once()
    
    exported_data = mock_sink.export.call_args[0][0]
    output_path = mock_sink.export.call_args[0][1]
    
    assert len(exported_data) == 2
    assert exported_data[0]['name'] == "Project A"
    assert output_path == "output/initiatives.json"

def test_export_initiative_types(exporter, mock_sink):
    # Setup
    mock_data = [
        MockInitiativeType(10, "Research Project"),
        MockInitiativeType(11, "Extension Project")
    ]
    exporter.initiative_type_ctrl.get_all.return_value = mock_data

    # Execute
    exporter.export_initiative_types("output/types.json")

    # Verify
    exporter.initiative_type_ctrl.get_all.assert_called_once()
    mock_sink.export.assert_called_once()
    
    exported_data = mock_sink.export.call_args[0][0]
    
    assert len(exported_data) == 2
    assert exported_data[0]['name'] == "Research Project"

