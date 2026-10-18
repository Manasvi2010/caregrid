from backend.app.routes.beds import ALLOWED


def test_available_cannot_jump_to_occupied():
    assert "occupied" not in ALLOWED["available"]


def test_occupied_has_no_manual_exit():
    assert ALLOWED["occupied"] == set()


def test_cleaning_only_goes_to_available():
    assert ALLOWED["cleaning"] == {"available"}


def test_reserved_can_be_released():
    assert "available" in ALLOWED["reserved"]