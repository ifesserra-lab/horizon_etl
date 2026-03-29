from unittest.mock import MagicMock

from src.core.logic.team_synchronizer import TeamSynchronizer


class MockTeam:
    def __init__(self, team_id, name):
        self.id = team_id
        self.name = name


def test_ensure_team_matches_canonical_name():
    team_controller = MagicMock()
    team_controller.get_all.return_value = [MockTeam(1, "Conecta FAPES")]
    synchronizer = TeamSynchronizer(team_controller, roles_cache={})

    team = synchronizer.ensure_team("Conecta Fapes", "desc")

    assert team.id == 1
    team_controller.create_team.assert_not_called()
