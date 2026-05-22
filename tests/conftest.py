import pytest


@pytest.fixture
def captured_game_id() -> int:
    """Regulation game with shift data."""
    return 2024020001


@pytest.fixture
def captured_game_id_shootout() -> int:
    """Shootout game with shift data."""
    return 2024020022


@pytest.fixture
def captured_score_date() -> str:
    return "2024-10-08"
