from backend.app.routes.forecast import compute_forecast


def series(start, step, n=36):
    return [(i * 10, start + i * step) for i in range(n)]


def test_too_little_data():
    assert compute_forecast(series(10, 2, n=3))["status"] == "not_enough_data"


def test_rising_trend_warns():
    result = compute_forecast(series(10, 2))   # climbs 10% to 80%
    assert result["status"] == "warning"
    assert 0 <= result["minutes_to_threshold"] <= 180


def test_flat_trend_is_ok():
    assert compute_forecast(series(40, 0))["status"] == "ok"


def test_falling_trend_is_ok():
    assert compute_forecast(series(80, -1))["status"] == "ok"


def test_already_above_threshold():
    assert compute_forecast(series(60, 1))["status"] == "above"