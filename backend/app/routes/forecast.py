import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sklearn.linear_model import LinearRegression
from backend.app.db import pool
from backend.app.auth import current_user

router = APIRouter(tags=["forecast"])

MIN_POINTS = 6        # need some history before predicting
THRESHOLD = 90.0      # alert level in percent
HORIZON_MIN = 180     # look 3 hours ahead


def _fmt_minutes(m):
    m = int(round(m))
    if m < 60:
        return f"{m} minutes"
    return f"{m // 60}h {m % 60}m"


def compute_forecast(points):
    """points: list of (minutes_since_first, occupancy_percent), oldest first."""
    if len(points) < MIN_POINTS:
        return {"status": "not_enough_data", "message": "Not enough history for a forecast yet"}

    X = np.array([[p[0]] for p in points])
    y = np.array([p[1] for p in points])
    model = LinearRegression().fit(X, y)

    slope = float(model.coef_[0])               # percent per minute
    last_t = points[-1][0]
    current = float(y[-1])
    fitted_now = float(model.predict([[last_t]])[0])
    predicted = float(model.predict([[last_t + HORIZON_MIN]])[0])
    predicted = max(0.0, min(100.0, predicted))

    result = {
        "current_pct": round(current, 1),
        "predicted_pct_3h": round(predicted, 1),
        "slope_per_hour": round(slope * 60, 2),
        "minutes_to_threshold": None,
    }

    if current >= THRESHOLD:
        result["status"] = "above"
        result["message"] = f"Already at {result['current_pct']}% occupancy"
    elif slope > 0:
        minutes_to = max(0.0, (THRESHOLD - fitted_now) / slope)
        if minutes_to <= HORIZON_MIN:
            result["status"] = "warning"
            result["minutes_to_threshold"] = round(minutes_to)
            result["message"] = f"Likely to pass 90% in about {_fmt_minutes(minutes_to)}"
        else:
            result["status"] = "ok"
            result["message"] = f"Not expected to pass 90% in the next 3 hours (about {result['predicted_pct_3h']}%)"
    else:
        result["status"] = "ok"
        result["message"] = "Occupancy is flat or falling"
    return result


def take_snapshots():
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO occupancy_snapshots (ward_id, occupied_count, total) "
            "SELECT w.id, count(b.id) FILTER (WHERE b.status = 'occupied'), count(b.id) "
            "FROM wards w JOIN beds b ON b.ward_id = w.id GROUP BY w.id"
        )


@router.get("/forecast/{ward_id}")
def forecast(ward_id: int, user=Depends(current_user)):
    if user["role"] != "hospital_admin" and ward_id != user["ward"]:
        raise HTTPException(403, "You can only view your own ward")
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT taken_at, occupied_count, total FROM occupancy_snapshots "
            "WHERE ward_id = %s AND total > 0 AND taken_at > now() - interval '6 hours' "
            "ORDER BY taken_at",
            (ward_id,),
        ).fetchall()

    points = []
    if rows:
        t0 = rows[0]["taken_at"]
        points = [
            ((r["taken_at"] - t0).total_seconds() / 60, r["occupied_count"] * 100 / r["total"])
            for r in rows
        ]
    result = compute_forecast(points)
    result["ward_id"] = ward_id
    return result