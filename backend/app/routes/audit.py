from datetime import date, timedelta
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query
from backend.app.db import pool
from backend.app.auth import require_role

router = APIRouter(tags=["audit"])

staff = require_role("ward_admin", "hospital_admin")


@router.get("/audit/filters")
def audit_filters(user=Depends(staff)):
    with pool.connection() as conn:
        if user["role"] == "hospital_admin":
            wards = conn.execute("SELECT id, name FROM wards ORDER BY id").fetchall()
            users = conn.execute("SELECT id, name FROM users ORDER BY name").fetchall()
        else:
            wards = conn.execute(
                "SELECT id, name FROM wards WHERE id = %s", (user["ward"],)
            ).fetchall()
            users = conn.execute(
                "SELECT id, name FROM users WHERE ward_id = %s ORDER BY name", (user["ward"],)
            ).fetchall()
    return {"wards": wards, "users": users}


@router.get("/audit")
def list_audit(
    ward_id: Optional[int] = None,
    user_id: Optional[int] = None,
    new_status: Optional[Literal["available", "occupied", "cleaning", "reserved"]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(staff),
):
    where = ["TRUE"]
    params = []

    # Ward admins are always limited to their own ward
    if user["role"] != "hospital_admin":
        where.append("b.ward_id = %s")
        params.append(user["ward"])
    elif ward_id is not None:
        where.append("b.ward_id = %s")
        params.append(ward_id)

    if user_id is not None:
        where.append("e.changed_by = %s")
        params.append(user_id)
    if new_status:
        where.append("e.new_status = %s")
        params.append(new_status)
    if date_from:
        where.append("e.changed_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("e.changed_at < %s")
        params.append(date_to + timedelta(days=1))

    where_sql = " AND ".join(where)
    base = (
        "FROM bed_events e "
        "JOIN beds b ON b.id = e.bed_id "
        "JOIN wards w ON w.id = b.ward_id "
        "JOIN users u ON u.id = e.changed_by "
        "WHERE " + where_sql
    )

    with pool.connection() as conn:
        total = conn.execute("SELECT count(*) AS n " + base, params).fetchone()["n"]
        items = conn.execute(
            "SELECT e.id, e.changed_at, w.name AS ward, b.bed_number, "
            "       e.old_status, e.new_status, u.name AS user_name, u.role AS user_role "
            + base +
            " ORDER BY e.changed_at DESC, e.id DESC LIMIT %s OFFSET %s",
            params + [page_size, (page - 1) * page_size],
        ).fetchall()

    pages = max(1, -(-total // page_size))
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}