from unittest.mock import MagicMock

import pytest

from src.core.logic.team_synchronizer import TeamSynchronizer


class MockMember:
    def __init__(self, person_id, role_id, start_date=None):
        self.person_id = person_id
        self.role_id = role_id
        self.start_date = start_date


@pytest.fixture
def synchronizer():
    controller = MagicMock()
    roles_cache = {"Coordinator": MagicMock(id=1), "Researcher": MagicMock(id=2)}
    return TeamSynchronizer(controller, roles_cache)


def test_synchronize_members_removes_obsolete(synchronizer):
    team_id = 100
    person_a = MagicMock(id=1)

    # DB has members A and B
    member_a = MockMember(person_id=1, role_id=1)
    member_b = MockMember(person_id=2, role_id=2)
    synchronizer.team_controller.get_members.return_value = [member_a, member_b]

    # Source only has A
    members_to_sync = [(person_a, "Coordinator", None)]

    synchronizer.synchronize_members(team_id, members_to_sync)

    # Should call add_member (idempotency check happens inside, but here we just check if it was attempted)
    # Actually, in this test get_members returns A, so add_member should NOT be called for A.

    # Should call remove_member for B
    synchronizer.team_controller.remove_member.assert_called_with(
        team_id=team_id, person_id=2, role_id=2
    )


def test_add_member_if_new_idempotency(synchronizer):
    team_id = 100
    person = MagicMock(id=1)
    role_obj = synchronizer.roles_cache["Coordinator"]

    # Already exists
    synchronizer.team_controller.get_members.return_value = [MockMember(1, 1)]

    synchronizer._add_member_if_new(team_id, person, role_obj, "Coordinator", 1, None)

    synchronizer.team_controller.add_member.assert_not_called()

    # New member
    synchronizer.team_controller.get_members.return_value = []
    synchronizer._add_member_if_new(team_id, person, role_obj, "Coordinator", 1, None)
    synchronizer.team_controller.add_member.assert_called()
