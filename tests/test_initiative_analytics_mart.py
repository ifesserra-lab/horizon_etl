import json
import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.core.logic.mart_generator import InitiativeAnalyticsMartGenerator


@pytest.fixture
def mock_initiatives():
    # Mock some initiatives with different dates and statuses
    init1 = MagicMock()
    init1.id = "init-1"
    init1.status = "Active"
    init1.start_date = date(2022, 1, 1)
    init1.end_date = None

    init2 = MagicMock()
    init2.id = "init-2"
    init2.status = "Completed"
    init2.start_date = date(2023, 6, 1)
    init2.end_date = date(2024, 12, 31)

    init3 = MagicMock()
    init3.id = "init-3"
    init3.status = "Em execução"
    init3.start_date = date(2024, 1, 1)
    init3.end_date = date(2025, 12, 31)

    return [init1, init2, init3]


@pytest.fixture
def mock_teams():
    # Mock teams per initiative
    team1 = {"id": "team-1"}
    member1 = MagicMock()
    member1.person_id = "person-1"
    member1.role.name = "Coordinator"

    member2 = MagicMock()
    member2.person_id = "person-2"
    member2.role.name = "Student"

    return {"init-1": [team1], "team-1-members": [member1, member2]}


def test_initiative_analytics_calculation(mock_initiatives, mock_teams, tmp_path):
    output_path = str(tmp_path / "test_mart.json")

    with (
        patch("src.core.logic.mart_generator.InitiativeController") as MockInitCtrl,
        patch("src.core.logic.mart_generator.TeamController") as MockTeamCtrl,
    ):

        mock_init_instance = MockInitCtrl.return_value
        mock_init_instance.get_all.return_value = mock_initiatives
        mock_init_instance.get_teams.side_effect = lambda i_id: mock_teams.get(i_id, [])

        mock_team_instance = MockTeamCtrl.return_value
        mock_team_instance.get_members.side_effect = lambda t_id: mock_teams.get(
            f"{t_id}-members", []
        )

        generator = InitiativeAnalyticsMartGenerator()
        result = generator.generate(output_path)

        # Verify Summary
        assert result["summary"]["total_projects"] == 3
        # init1 (Active), init3 (Em execução) -> 2 active
        assert result["summary"]["active_projects"] == 2
        # person-1 and person-2 -> 2 unique participants
        assert result["summary"]["total_participants"] == 2

        # Verify Evolution
        evolution = {item["year"]: item for item in result["evolution"]}
        assert evolution["2022"]["start"] == 1
        assert evolution["2022"]["researchers"] == 1
        assert evolution["2022"]["students"] == 1

        assert evolution["2023"]["start"] == 1
        # In 2023, init-1 and init-2 are active
        # init-1: p1(C), p2(S)
        # init-2: (not mocked yet, but let's assume it was empty or same)
        assert evolution["2023"]["researchers"] >= 1

        assert evolution["2024"]["start"] == 1
        assert evolution["2024"]["end"] == 1
        assert evolution["2025"]["end"] == 1

        # Verify Composition
        # Coordinator -> researcher, Student -> student
        assert result["team_composition"]["researchers"] == 1
        assert result["team_composition"]["students"] == 1

        # Verify File exists
        assert os.path.exists(output_path)
        with open(output_path, "r") as f:
            data = json.load(f)
            assert data == result
