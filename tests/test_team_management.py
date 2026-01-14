import pytest
from unittest.mock import MagicMock, patch
import unicodedata
import re
from src.core.logic.project_loader import ProjectLoader

# Mock classes for controllers
class MockPerson:
    def __init__(self, id, name):
        self.id = id
        self.name = name

class MockTeam:
    def __init__(self, id, name):
        self.id = id
        self.name = name

@pytest.fixture
def project_loader():
    with patch('src.core.logic.project_loader.PostgresClient'), \
         patch('src.core.logic.project_loader.InitiativeController'), \
         patch('src.core.logic.project_loader.TeamController'), \
         patch('src.core.logic.project_loader.PersonController'):
        
        # Mock the mapping strategy
        mock_strategy = MagicMock()
        loader = ProjectLoader(mapping_strategy=mock_strategy)
        
        # Override controllers with our mocks if needed, 
        # but the loader already instantiated them in __init__ using the patches.
        return loader

def test_normalize_name(project_loader):
    """Test the name normalization logic."""
    assert project_loader._normalize_name("Pãulo Sérgio Junior") == "PAULO SERGIO JUNIOR"
    assert project_loader._normalize_name("Maria-Aparecida Santos!") == "MARIA APARECIDA SANTOS"
    assert project_loader._normalize_name("  ROBERTO   CARLOS  ") == "ROBERTO CARLOS"
    assert project_loader._normalize_name("") == ""
    assert project_loader._normalize_name(None) == ""

def test_get_or_create_person_exact_match(project_loader):
    """Test person identification with exact normalized match."""
    person1 = MockPerson(1, "Paulo Sergio Junior")
    project_loader._persons_cache["Paulo Sergio Junior"] = person1
    
    # Matching with different case and accents
    result = project_loader._get_or_create_person("pãulo sérgio junior")
    
    assert result.id == 1
    project_loader.person_controller.create_person.assert_not_called()

def test_get_or_create_person_fuzzy_match(project_loader):
    """Test person identification with fuzzy match (reordered name)."""
    person1 = MockPerson(1, "Paulo Sergio Junior")
    project_loader._persons_cache["Paulo Sergio Junior"] = person1
    
    # Reordered name "Junior Paulo Sergio" should be 100 score in token_sort_ratio
    result = project_loader._get_or_create_person("Junior Paulo Sergio")
    
    assert result.id == 1
    project_loader.person_controller.create_person.assert_not_called()

def test_get_or_create_person_new_creation(project_loader):
    """Test creating a new person when no match is found."""
    project_loader._persons_cache = {}
    mock_new_person = MockPerson(99, "Novo Usuario")
    project_loader.person_controller.create_person.return_value = mock_new_person
    
    result = project_loader._get_or_create_person("Novo Usuario")
    
    assert result.id == 99
    project_loader.person_controller.create_person.assert_called_with(name="Novo Usuario")

def test_create_initiative_team_idempotent(project_loader):
    """Test that team creation is idempotent based on name."""
    initiative = MagicMock()
    initiative.name = "Projeto Teste"
    initiative.id = 10
    
    existing_team = MockTeam(5, "Projeto Teste")
    project_loader.team_controller.list_teams.return_value = [existing_team]
    
    project_loader._create_initiative_team(initiative, {"coordinator_name": None})
    
    # Should not call create_team if it exists
    project_loader.team_controller.create_team.assert_not_called()
    # Should still assign
    project_loader.controller.assign_team.assert_called_with(10, 5)

@patch('src.core.logic.project_loader.PostgresClient')
def test_ensure_roles_exist(mock_pg_client, project_loader):
    """Test that mandatory roles are ensured to exist."""
    session = MagicMock()
    mock_pg_client.return_value.get_session.return_value = session
    
    # Mock no roles exist
    session.query.return_value.filter_by.return_value.first.return_value = None
    
    project_loader._ensure_roles_exist()
    
    assert session.add.call_count == 3 # Coordinator, Researcher, Student
    session.commit.assert_called_once()
