
import pytest
import os
import json
from unittest.mock import MagicMock, patch
from src.flows.ingest_lattes_advisorships import ingest_advisorships_file_task
from eo_lib import InitiativeController
from research_domain.domain.entities.advisorship import Advisorship, AdvisorshipType

@pytest.fixture
def mock_managers():
    entity_manager = MagicMock()
    linker = MagicMock()
    
    # Mock Ensure Organization
    entity_manager.ensure_organization.return_value = 1
    
    # Mock Ensure Type
    mock_type = MagicMock()
    mock_type.id = 10
    entity_manager.ensure_initiative_type.return_value = mock_type
    
    return entity_manager, linker

@pytest.fixture
def mock_lattes_data(tmp_path):
    data = {
        "informacoes_pessoais": {
            "nome_completo": "Test Researcher",
            "id_lattes": "1234567890123456"
        },
        "dados_complementares": {
            "orientacoes_concluidas": [
                {
                    "natureza": "Mestrado",
                    "tipo": "MESTRADO",
                    "titulo": "Test Master Thesis",
                    "nome_do_orientado": "Student A",
                    "ano": "2023",
                    "nome_instituicao": "Test Univ"
                }
            ]
        }
    }
    
    file_path = tmp_path / "1234567890123456.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    
    return str(file_path)

@patch("src.flows.ingest_lattes_advisorships.ResearcherController")
@patch("src.flows.ingest_lattes_advisorships.InitiativeController")
@patch("src.flows.ingest_lattes_advisorships.get_run_logger")
@patch("src.flows.ingest_lattes_advisorships.PostgresClient")  # Mock DB interaction
def test_ingest_advisorships_file_task(
    MockDBClient, MockLogger, MockInitiativeCtrl, MockResearcherCtrl, 
    mock_managers, mock_lattes_data
):
    entity_manager, linker = mock_managers
    
    # Setup Returns
    mock_res_ctrl = MockResearcherCtrl.return_value
    mock_res = MagicMock()
    mock_res.name = "Test Researcher"
    mock_res.brand_id = "1234567890123456"
    mock_res_ctrl.get_all.return_value = [mock_res]
    
    mock_init_ctrl = MockInitiativeCtrl.return_value

    # Mock DB Session
    mock_session = MagicMock()
    MockDBClient.return_value.get_session.return_value = mock_session
    mock_session.execute.return_value.scalar.return_value = None # No duplicate
    
    # Run Function
    ingest_advisorships_file_task.fn(mock_lattes_data, entity_manager, linker)
    
    # Verify Create call
    assert mock_init_ctrl.create.called
    
    created_obj = mock_init_ctrl.create.call_args[0][0]
    assert isinstance(created_obj, Advisorship)
    assert created_obj.name == "Test Master Thesis"
    assert created_obj.status == "Concluded"
    
    # Verify Linker call
    assert linker.add_members_to_initiative_team.called
    project_data_arg = linker.add_members_to_initiative_team.call_args[0][1]
    assert project_data_arg["coordinator_name"] == "Test Researcher"
    assert "Student A" in project_data_arg["student_names"]

