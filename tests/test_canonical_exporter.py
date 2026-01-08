from unittest.mock import MagicMock, patch
from src.core.logic.canonical_exporter import CanonicalDataExporter
from src.core.ports.export_sink import IExportSink

def test_export_all_orchestrates_exports():
    # Arrange
    mock_sink = MagicMock(spec=IExportSink)
    
    with patch('src.core.logic.canonical_exporter.OrganizationController') as MockOrgCtrl, \
         patch('src.core.logic.canonical_exporter.CampusController') as MockCampCtrl, \
         patch('src.core.logic.canonical_exporter.KnowledgeAreaController') as MockKaCtrl, \
         patch('src.core.logic.canonical_exporter.ResearcherController') as MockResearcherCtrl:
        
        # Mock Instances
        mock_org_instance = MockOrgCtrl.return_value
        mock_camp_instance = MockCampCtrl.return_value
        mock_ka_instance = MockKaCtrl.return_value
        mock_researcher_instance = MockResearcherCtrl.return_value
        
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
        
        exporter = CanonicalDataExporter(sink=mock_sink)
        
        # Act
        with patch('os.makedirs') as mock_makedirs:
             exporter.export_all("data/exports")
             
             # Assert
             mock_makedirs.assert_called_once()
             
             # Verify Sink Calls
             # Should be called 4 times
             assert mock_sink.export.call_count == 4
             
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
             assert args[0] == [{"id": 1000, "name": "Researcher1"}]
             assert "researchers_canonical.json" in args[1]
