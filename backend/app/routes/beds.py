from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.app.db import pool
from backend.app.auth import current_user
from backend.app.ws import manager

router = APIRouter(tags=["beds"])

# Occupying and freeing an occupied bed go through admissions
ALLOWED = {
    "available": {"reserved", "cleaning"},
    "reserved": {"available"},
    "occupied": set(),
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

        if user["role"] != "hospital_admin" and bed["ward_id"] != user["ward"]:
            raise HTTPException(403, "You can only edit beds in your own ward")

        if body.status == "occupied":
            raise HTTPException(400, "Use Admit patient to occupy a bed")
        if bed["status"] == "occupied":
            raise HTTPException(400, "Discharge the patient to free this bed")

        if body.status not in ALLOWED[bed["status"]]:
            raise HTTPException(
                400, f"Cannot change from {bed['status']} to {body.status}"
            )

        row = conn.execute(
            "UPDATE beds SET status = %s, version = version + 1 "
            "WHERE id = %s AND version = %s "
            "RETURNING id, ward_id, bed_number, status, version",
            (body.status, bed_id, body.version),
        ).fetchone()
        if not row:
            raise HTTPException(409, "Bed was changed by someone else. Refresh and try again")

        conn.execute(
            "INSERT INTO bed_events (bed_id, old_status, new_status, changed_by) "
            "VALUES (%s, %s, %s, %s)",
            (bed_id, bed["status"], body.status, int(user["sub"])),
        )

    result = dict(row)
    result["patient_name"] = None
    result["admission_id"] = None
    manager.broadcast_threadsafe(result)
    return result