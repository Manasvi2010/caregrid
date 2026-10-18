from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.app.db import pool
from backend.app.auth import current_user
from backend.app.ws import manager

router = APIRouter(tags=["beds"])

ALLOWED = {
    "available": {"occupied", "reserved", "cleaning"},
    "reserved": {"occupied", "available"},
    "occupied": {"cleaning"},
    "cleaning": {"available"},
}


class StatusUpdate(BaseModel):
    status: Literal["available", "occupied", "cleaning", "reserved"]
    version: int


@router.patch("/beds/{bed_id}/status")
def update_status(bed_id: int, body: StatusUpdate, user=Depends(current_user)):
    with pool.connection() as conn:
        bed = conn.execute(
            "SELECT id, ward_id, status, version FROM beds WHERE id = %s",
            (bed_id,),
        ).fetchone()
        if not bed:
            raise HTTPException(404, "Bed not found")

        # Rule 1: permissions (hospital_admin can edit any ward)
        if user["role"] != "hospital_admin" and bed["ward_id"] != user["ward"]:
            raise HTTPException(403, "You can only edit beds in your own ward")

        # Rule 2: allowed status transitions
        if body.status not in ALLOWED[bed["status"]]:
            raise HTTPException(
                400, f"Cannot change from {bed['status']} to {body.status}"
            )

        # Rule 3: optimistic locking (only updates if version still matches)
        row = conn.execute(
            "UPDATE beds SET status = %s, version = version + 1 "
            "WHERE id = %s AND version = %s "
            "RETURNING id, ward_id, bed_number, status, version",
            (body.status, bed_id, body.version),
        ).fetchone()
        if not row:
            raise HTTPException(409, "Bed was changed by someone else. Refresh and try again")

        # Rule 4: audit log (same transaction as the update)
        conn.execute(
            "INSERT INTO bed_events (bed_id, old_status, new_status, changed_by) "
            "VALUES (%s, %s, %s, %s)",
            (bed_id, bed["status"], body.status, int(user["sub"])),
        )

    # Outside the with-block: runs only after the database commit
    manager.broadcast_threadsafe(dict(row))
    return row