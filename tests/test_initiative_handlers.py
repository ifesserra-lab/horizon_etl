from datetime import datetime
from unittest.mock import MagicMock, patch

from research_domain.domain.entities import Advisorship

from src.core.logic.initiative_handlers import AdvisorshipHandler


@patch("src.core.logic.initiative_handlers.FellowshipController")
@patch("src.core.logic.initiative_handlers.AdvisorshipController")
def test_advisorship_handler_creates_members_with_base_persons(
    MockAdvisorshipController,
    MockFellowshipController,
):
    initiative_controller = MagicMock()
    person_matcher = MagicMock()
    entity_manager = MagicMock()

    student_role = MagicMock()
    student_role.id = 1
    student_role.name = "Student"

    supervisor_role = MagicMock()
    supervisor_role.id = 2
    supervisor_role.name = "Supervisor"

    entity_manager.role_controller.get_all.return_value = [
        student_role,
        supervisor_role,
    ]
    MockFellowshipController.return_value.get_all.return_value = []

    session = MagicMock()
    session.execute.return_value.scalar.return_value = None
    person_matcher.person_controller._service._repository._session = session
    initiative_controller._service._repository._session = session

    student_match = MagicMock()
    student_match.id = 11
    supervisor_match = MagicMock()
    supervisor_match.id = 12
    student_person = MagicMock()
    student_person.id = 11
    supervisor_person = MagicMock()
    supervisor_person.id = 12

    person_matcher.match_or_create.side_effect = [student_match, supervisor_match]
    session.get.side_effect = [student_person, supervisor_person]
    person_matcher.person_controller.get_by_id.side_effect = [
        student_person,
        supervisor_person,
    ]

    handler = AdvisorshipHandler(
        initiative_controller=initiative_controller,
        person_matcher=person_matcher,
        entity_manager=entity_manager,
    )

    project_data = {
        "title": "Test Advisorship",
        "student_names": ["Student A"],
        "student_emails": ["student@example.org"],
        "coordinator_name": "Supervisor B",
        "coordinator_email": "supervisor@example.org",
        "status": "active",
    }

    created = handler.create_or_update(
        project_data=project_data,
        existing_initiative=None,
        initiative_type_name="Advisorship",
        initiative_type_id=7,
        organization_id=9,
        parent_id=10,
    )

    assert isinstance(created, Advisorship)
    MockAdvisorshipController.return_value.create_advisorship.assert_not_called()
    MockAdvisorshipController.return_value.create.assert_called_once_with(created)
    assert [member.person for member in created.members] == [
        student_person,
        supervisor_person,
    ]
    assert [member.role_name for member in created.members] == [
        "Student",
        "Supervisor",
    ]
    assert created.initiative_type_id == 7
    assert created.organization_id == 9
    assert created.parent_id == 10


@patch("src.core.logic.initiative_handlers.FellowshipController")
@patch("src.core.logic.initiative_handlers.AdvisorshipController")
def test_advisorship_handler_disambiguates_title_when_name_is_already_taken(
    _MockAdvisorshipController,
    MockFellowshipController,
):
    initiative_controller = MagicMock()
    person_matcher = MagicMock()
    entity_manager = MagicMock()

    MockFellowshipController.return_value.get_all.return_value = []
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 258
    initiative_controller._service._repository._session = session
    person_matcher.person_controller._service._repository._session = session

    handler = AdvisorshipHandler(
        initiative_controller=initiative_controller,
        person_matcher=person_matcher,
        entity_manager=entity_manager,
    )

    title = handler._resolve_persisted_title(
        "Desenvolvimento de uma Bancada Didática de Baixo Custo",
        {
            "student_names": ["Ana Estudante"],
            "start_date": datetime(2019, 8, 1),
            "metadata": {"sigpesq_id": 123},
        },
    )

    assert (
        title
        == "Desenvolvimento de uma Bancada Didática de Baixo Custo | Orientacao Ana Estudante | 2019 | sigpesq 123"
    )


@patch("src.core.logic.initiative_handlers.FellowshipController")
@patch("src.core.logic.initiative_handlers.AdvisorshipController")
def test_advisorship_handler_supports_legacy_student_and_supervisor_fields(
    _MockAdvisorshipController,
    MockFellowshipController,
):
    initiative_controller = MagicMock()
    person_matcher = MagicMock()
    entity_manager = MagicMock()

    MockFellowshipController.return_value.get_all.return_value = []
    session = MagicMock()
    initiative_controller._service._repository._session = session
    person_matcher.person_controller._service._repository._session = session

    handler = AdvisorshipHandler(
        initiative_controller=initiative_controller,
        person_matcher=person_matcher,
        entity_manager=entity_manager,
    )

    class LegacyAdvisorship:
        student = None
        student_id = None
        supervisor = None
        supervisor_id = None

    initiative = LegacyAdvisorship()
    student = MagicMock()
    student.id = 11
    supervisor = MagicMock()
    supervisor.id = 12

    with patch.object(handler, "_coerce_to_person", side_effect=[student, supervisor]):
        handler._sync_advisorship_member(
            initiative,
            person=student,
            role_name="Student",
            start_date=None,
        )
        handler._sync_advisorship_member(
            initiative,
            person=supervisor,
            role_name="Supervisor",
            start_date=None,
        )

    assert initiative.student is student
    assert initiative.student_id == 11
    assert initiative.supervisor is supervisor
    assert initiative.supervisor_id == 12
