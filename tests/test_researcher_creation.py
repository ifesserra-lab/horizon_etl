from unittest.mock import MagicMock

import pytest

from src.core.logic.researcher_creation import create_researcher_with_resume_fallback


def test_create_researcher_with_resume_fallback_uses_controller_when_supported():
    controller = MagicMock()
    created = MagicMock()
    controller.create_researcher.return_value = created

    result = create_researcher_with_resume_fallback(
        controller,
        name="Alice",
        identification_id="alice@ifes.edu.br",
        emails=["alice@ifes.edu.br"],
    )

    assert result is created
    controller.create_researcher.assert_called_once_with(
        name="Alice",
        identification_id="alice@ifes.edu.br",
        emails=["alice@ifes.edu.br"],
    )
    controller.create.assert_not_called()


def test_create_researcher_with_resume_fallback_uses_direct_create_on_resume_mismatch():
    controller = MagicMock()
    controller.create_researcher.side_effect = TypeError(
        "create_with_details() got an unexpected keyword argument 'resume'"
    )
    created = MagicMock()
    created.id = 42
    created.name = "Alice"
    created.identification_id = "alice@ifes.edu.br"
    created.emails = [MagicMock(email="alice@ifes.edu.br")]
    controller._service.create_with_details.return_value = created
    exists_check = MagicMock()
    exists_check.scalar.return_value = False
    controller._service._repository._session.execute.side_effect = [
        exists_check,
        MagicMock(),
    ]
    controller.get_by_id.return_value = created

    result = create_researcher_with_resume_fallback(
        controller,
        name="Alice",
        identification_id="alice@ifes.edu.br",
        emails=["alice@ifes.edu.br"],
    )

    assert result is created
    controller._service.create_with_details.assert_called_once_with(
        name="Alice",
        emails=["alice@ifes.edu.br"],
        identification_id="alice@ifes.edu.br",
    )
    session = controller._service._repository._session
    assert session.execute.call_count == 2
    session.commit.assert_called_once()
    controller.create.assert_not_called()


def test_create_researcher_with_resume_fallback_does_not_swallow_unrelated_type_error():
    controller = MagicMock()
    controller.create_researcher.side_effect = TypeError("wrong positional arg")

    with pytest.raises(TypeError, match="wrong positional arg"):
        create_researcher_with_resume_fallback(
            controller,
            name="Alice",
            identification_id="alice@ifes.edu.br",
            emails=["alice@ifes.edu.br"],
        )

    controller.create.assert_not_called()


def test_create_researcher_with_resume_fallback_retries_without_emails_on_personemail_mismatch():
    controller = MagicMock()
    controller.create_researcher.side_effect = [
        Exception(
            "Attempting to flush an item of type <class 'research_domain.domain.entities.researcher.Researcher'> "
            'as a member of collection "PersonEmail.person". Expected an object of type '
            "<class 'eo_lib.domain.entities.person.Person'>"
        ),
        MagicMock(id=77),
    ]
    controller.get_by_id.return_value = MagicMock(id=77)

    session = controller._service._repository._session
    session.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=False)),
        MagicMock(),
        MagicMock(scalar=MagicMock(return_value=False)),
        MagicMock(),
    ]

    result = create_researcher_with_resume_fallback(
        controller,
        name="Alice",
        identification_id="alice@ifes.edu.br",
        emails=["alice@ifes.edu.br"],
    )

    assert result is controller.get_by_id.return_value
    assert controller.create_researcher.call_args_list[0].kwargs == {
        "name": "Alice",
        "emails": ["alice@ifes.edu.br"],
        "identification_id": "alice@ifes.edu.br",
    }
    assert controller.create_researcher.call_args_list[1].kwargs == {
        "name": "Alice",
        "emails": None,
        "identification_id": "alice@ifes.edu.br",
    }
    session.rollback.assert_called_once()
    assert session.execute.call_count == 4
    assert session.commit.call_count == 2
