from fastapi import APIRouter, Depends, HTTPException
from backend.app.db import pool
from backend.app.auth import current_user

router = APIRouter(tags=["wards"])


@router.get("/wards")
def list_wards(user=Depends(current_user)):
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT id, name, floor FROM wards ORDER BY id"
        ).fetchall()
    return rows


@router.get("/wards/{ward_id}/beds")
def list_beds(ward_id: int, user=Depends(current_user)):
    with pool.connection() as conn:
        ward = conn.execute(
            "SELECT id FROM wards WHERE id = %s", (ward_id,)
        ).fetchone()
        if not ward:
            raise HTTPException(404, "Ward not found")
        rows = conn.execute(
            "SELECT id, ward_id, bed_number, status, version "
            "FROM beds WHERE ward_id = %s ORDER BY id",
            (ward_id,),
        ).fetchall()
    return rows