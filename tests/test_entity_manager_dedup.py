from unittest.mock import MagicMock, patch

from src.core.logic.entity_manager import EntityManager


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


@patch("src.core.logic.entity_manager.CampusController")
@patch("src.core.logic.entity_manager.KnowledgeAreaController")
@patch("src.core.logic.entity_manager.RoleController")
@patch("src.core.logic.entity_manager.UniversityController")
@patch("src.core.logic.entity_manager.EducationTypeController")
@patch("src.core.logic.entity_manager.AcademicEducationController")
@patch("src.core.logic.entity_manager.ArticleController")
@patch("src.core.logic.entity_manager.OrganizationController")
def test_entity_manager_matches_canonical_campus_and_knowledge_area(
    MockOrgCtrl,
    MockArticleCtrl,
    MockAcademicEduCtrl,
    MockEduTypeCtrl,
    MockUniCtrl,
    MockRoleCtrl,
    MockKaCtrl,
    MockCampusCtrl,
):
    MockCampusCtrl.return_value.get_all.return_value = [
        Obj(id=10, name="Campus Serra", organization_id=1)
    ]
    MockKaCtrl.return_value.get_all.return_value = [
        Obj(id=20, name="Engenharia Elétrica")
    ]

    manager = EntityManager(MagicMock(), MagicMock())

    assert manager.resolve_campus("campus serra", 1) == 10
    assert manager.ensure_knowledge_area("Engenharia Eletrica") == 20
