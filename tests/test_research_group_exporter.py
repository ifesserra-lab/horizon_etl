import pytest
from unittest.mock import MagicMock, patch
from src.core.logic.research_group_exporter import ResearchGroupExporter
from src.core.ports.export_sink import IExportSink

def test_exporter_fetches_and_exports():
    # Arrange
    mock_sink = MagicMock(spec=IExportSink)
    
    with patch('src.core.logic.research_group_exporter.ResearchGroupController') as MockCtrl:
        mock_ctrl_instance = MockCtrl.return_value
        mock_groups = ["Group1", "Group2"] # Mocking return as list of objects
        mock_ctrl_instance.get_all.return_value = mock_groups
        
        exporter = ResearchGroupExporter(sink=mock_sink)
        
        # Act
        exporter.export_all("output.json")
        
        # Assert
        mock_ctrl_instance.get_all.assert_called_once()
        mock_sink.export.assert_called_once_with(mock_groups, "output.json")

def test_exporter_handles_empty_list():
    # Arrange
    mock_sink = MagicMock(spec=IExportSink)
    
    with patch('src.core.logic.research_group_exporter.ResearchGroupController') as MockCtrl:
        mock_ctrl_instance = MockCtrl.return_value
        mock_ctrl_instance.get_all.return_value = []
        
        exporter = ResearchGroupExporter(sink=mock_sink)
        
        # Act
        exporter.export_all("output.json")
        
        # Assert
        mock_ctrl_instance.get_all.assert_called_once()
        mock_sink.export.assert_not_called()
