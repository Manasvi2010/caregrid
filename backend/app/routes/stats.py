from fastapi import APIRouter, Depends
from backend.app.db import pool
from backend.app.auth import current_user

router = APIRouter(tags=["stats"])


@router.get("/stats/occupancy")
def occupancy(user=Depends(current_user)):
    sql = (
        "SELECT w.id AS ward_id, w.name, count(b.id) AS total, "
        "  count(b.id) FILTER (WHERE b.status = 'occupied') AS occupied, "
        "  count(b.id) FILTER (WHERE b.status = 'available') AS available, "
        "  count(b.id) FILTER (WHERE b.status = 'cleaning') AS cleaning, "
        "  count(b.id) FILTER (WHERE b.status = 'reserved') AS reserved "
        "FROM wards w LEFT JOIN beds b ON b.ward_id = w.id "
    )
    params = ()
    if user["role"] != "hospital_admin":
        sql += "WHERE w.id = %s "
        params = (user["ward"],)
    sql += "GROUP BY w.id, w.name ORDER BY w.id"

    with pool.connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    for r in rows:
        r["pct"] = round(r["occupied"] * 100 / r["total"], 1) if r["total"] else 0
    return rows