import pytest
from unittest.mock import MagicMock, patch
from src.flows.ingest_lattes_projects import ingest_file_task
from src.core.domain.academic_education import AcademicEducation

@pytest.fixture
def mock_entity_manager():
    manager = MagicMock()
    # Mock ensure methods if needed, though mostly used for projects
    manager.ensure_initiative_type.return_value = MagicMock(id=1)
    manager.ensure_organization.return_value = 1
    manager.ensure_roles.return_value = {"Researcher": MagicMock(id=1)}
    return manager

@pytest.fixture
def mock_researcher_controller():
    with patch("src.flows.ingest_lattes_projects.ResearcherController") as mock:
        yield mock

@pytest.fixture
def mock_education_controller():
    with patch("src.flows.ingest_lattes_projects.AcademicEducationController") as mock:
        yield mock

@pytest.fixture
def mock_lattes_parser():
    with patch("src.flows.ingest_lattes_projects.LattesParser") as mock:
        yield mock

def test_ingest_academic_education(mock_entity_manager, mock_researcher_controller, mock_education_controller, mock_lattes_parser):
    # Setup Mocks
    mock_edu_ctrl_instance = mock_education_controller.return_value
    mock_parser_instance = mock_lattes_parser.return_value
    
    # Mock Researcher
    mock_researcher = MagicMock()
    mock_researcher.id = 123
    mock_researcher.brand_id = "1234567890"
    mock_researcher_controller.return_value.get_all.return_value = [mock_researcher]
    
    # Mock Parser Output
    mock_parser_instance.parse_research_projects.return_value = []
    mock_parser_instance.parse_extension_projects.return_value = []
    mock_parser_instance.parse_development_projects.return_value = []
    
    mock_education_data = [
        {
            "degree": "Doutorado",
            "institution": "UFES",
            "course_name": "Ciência da Computação",
            "start_year": 2018,
            "end_year": 2022
        }
    ]
    mock_parser_instance.parse_academic_education.return_value = mock_education_data

    # Mock JSON loading (we need to patch built-in open/json.load or use a real file)
    # Easiest is to point to a dummy file and mock json.load
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        with patch("json.load") as mock_json_load:
            mock_json_load.return_value = {"nome": "Test Researcher", "idLattes": "1234567890"}
            
            # Execute
            ingest_file_task("dummy_path/1234567890.json", mock_entity_manager)
            
            # Assert
            # Check if parse_academic_education was called
            mock_parser_instance.parse_academic_education.assert_called_once()
            
            # Check if create was called on controller
            assert mock_edu_ctrl_instance.create.call_count == 1
            created_edu = mock_edu_ctrl_instance.create.call_args[0][0]
            
            assert isinstance(created_edu, AcademicEducation)
            assert created_edu.researcher_id == 123
            assert created_edu.degree == "Doutorado"
            assert created_edu.institution == "UFES"
            assert created_edu.start_year == 2018
            assert created_edu.end_year == 2022
