import pytest
from unittest.mock import MagicMock
from src.core.logic.person_matcher import PersonMatcher

class MockPerson:
    def __init__(self, id, name):
        self.id = id
        self.name = name

@pytest.fixture
def matcher():
    controller = MagicMock()
    return PersonMatcher(controller)

def test_normalize_name(matcher):
    assert matcher.normalize_name("Pãulo Sérgio Junior") == "PAULO SERGIO JUNIOR"
    assert matcher.normalize_name("  ROBERTO   CARLOS  ") == "ROBERTO CARLOS"
    assert matcher.normalize_name("") == ""

def test_match_or_create_exact(matcher):
    person = MockPerson(1, "Paulo Sergio")
    matcher.person_controller.get_all.return_value = [person]
    matcher.preload_cache()
    
    result = matcher.match_or_create("Paulo Sergio")
    assert result.id == 1
    matcher.person_controller.create_person.assert_not_called()

def test_match_or_create_fuzzy(matcher):
    person_a = MockPerson(1, "Persona A Alpha")
    matcher.person_controller.get_all.return_value = [person_a]
    matcher.preload_cache()
    
    # 1. Fuzzy match (score >= 90)
    result = matcher.match_or_create("Persona Alpha", strict_match=False)
    assert result.id == 1
    
    # 2. Strict match with DIFFERENT name to avoid cache hit
    # and force it to check the fuzzy matching list
    new_p = MockPerson(2, "Persona Beta")
    matcher.person_controller.create_person.return_value = new_p
    
    # "Persona Beta" vs "Persona A Alpha" will have low score
    result = matcher.match_or_create("Persona Beta", strict_match=True)
    assert result.id == 2
    assert result.name == "Persona Beta"
    
def test_strict_match_avoids_fuzzy(matcher):
    person_a = MockPerson(1, "Jose Silva")
    matcher.person_controller.get_all.return_value = [person_a]
    matcher.preload_cache()
    
    # Jose da Silva vs Jose Silva is high score (~90) but not 100
    new_p = MockPerson(2, "Jose da Silva")
    matcher.person_controller.create_person.return_value = new_p
    
    # With strict_match=True, it should NOT match "Jose Silva" and should CREATE "Jose da Silva"
    result = matcher.match_or_create("Jose da Silva", strict_match=True)
    assert result.id == 2
    matcher.person_controller.create_person.assert_called()
