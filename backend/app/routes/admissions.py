from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.app.db import pool
from backend.app.auth import current_user
from backend.app.ws import manager

router = APIRouter(tags=["admissions"])

FREE = ("available", "reserved")


class AdmitIn(BaseModel):
    patient_name: str = Field(min_length=1, max_length=100)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[str] = Field(default=None, max_length=20)
    bed_id: int
    version: int


class TransferIn(BaseModel):
    to_bed_id: int
    to_version: int


class DischargeIn(BaseModel):
    version: int


def check_ward(user, ward_id):
    if user["role"] != "hospital_admin" and ward_id != user["ward"]:
        raise HTTPException(403, "You can only edit beds in your own ward")


def log_event(conn, bed_id, old, new, user):
    conn.execute(
        "INSERT INTO bed_events (bed_id, old_status, new_status, changed_by) "
        "VALUES (%s, %s, %s, %s)",
        (bed_id, old, new, int(user["sub"])),
    )


def bed_payload(conn, bed_id):
    return conn.execute(
        "SELECT b.id, b.ward_id, b.bed_number, b.status, b.version, "
        "       p.name AS patient_name, a.id AS admission_id "
        "FROM beds b "
        "LEFT JOIN admissions a ON a.bed_id = b.id AND a.discharged_at IS NULL "
        "LEFT JOIN patients p ON p.id = a.patient_id "
        "WHERE b.id = %s",
        (bed_id,),
    ).fetchone()


@router.post("/admissions")
def admit(body: AdmitIn, user=Depends(current_user)):
    with pool.connection() as conn:
        bed = conn.execute(
            "SELECT id, ward_id, status, version FROM beds WHERE id = %s FOR UPDATE",
            (body.bed_id,),
        ).fetchone()
        if not bed:
            raise HTTPException(404, "Bed not found")
        check_ward(user, bed["ward_id"])
        if bed["version"] != body.version:
            raise HTTPException(409, "Bed was changed by someone else. Refresh and try again")
        if bed["status"] not in FREE:
            raise HTTPException(400, f"Cannot admit to a bed that is {bed['status']}")

        patient = conn.execute(
            "INSERT INTO patients (name, age, gender) VALUES (%s, %s, %s) RETURNING id",
            (body.patient_name.strip(), body.age, body.gender),
        ).fetchone()
        conn.execute(
            "INSERT INTO admissions (patient_id, bed_id) VALUES (%s, %s)",
            (patient["id"], bed["id"]),
        )
        conn.execute(
            "UPDATE beds SET status = 'occupied', version = version + 1 WHERE id = %s",
            (bed["id"],),
        )
        log_event(conn, bed["id"], bed["status"], "occupied", user)
        result = bed_payload(conn, bed["id"])

    manager.broadcast_threadsafe(dict(result))
    return result


@router.post("/admissions/{admission_id}/transfer")
def transfer(admission_id: int, body: TransferIn, user=Depends(current_user)):
    with pool.connection() as conn:
        adm = conn.execute(
            "SELECT id, bed_id FROM admissions "
            "WHERE id = %s AND discharged_at IS NULL FOR UPDATE",
            (admission_id,),
        ).fetchone()
        if not adm:
            raise HTTPException(404, "Active admission not found")
        if adm["bed_id"] == body.to_bed_id:
            raise HTTPException(400, "Patient is already in that bed")

        # Lock both beds in id order, so two transfers can never deadlock
        rows = conn.execute(
            "SELECT id, ward_id, status, version FROM beds "
            "WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
            ([adm["bed_id"], body.to_bed_id],),
        ).fetchall()
        beds = {r["id"]: r for r in rows}
        old = beds.get(adm["bed_id"])
        new = beds.get(body.to_bed_id)
        if not new:
            raise HTTPException(404, "Target bed not found")

        check_ward(user, old["ward_id"])
        check_ward(user, new["ward_id"])
        if new["version"] != body.to_version:
            raise HTTPException(409, "Target bed was changed by someone else. Refresh and try again")
        if new["status"] not in FREE:
            raise HTTPException(400, f"Target bed is {new['status']}")

        # All of these succeed together or are rolled back together
        conn.execute("UPDATE admissions SET bed_id = %s WHERE id = %s", (new["id"], adm["id"]))
        conn.execute(
            "UPDATE beds SET status = 'cleaning', version = version + 1 WHERE id = %s",
            (old["id"],),
        )
        conn.execute(
            "UPDATE beds SET status = 'occupied', version = version + 1 WHERE id = %s",
            (new["id"],),
        )
        log_event(conn, old["id"], old["status"], "cleaning", user)
        log_event(conn, new["id"], new["status"], "occupied", user)
        old_payload = bed_payload(conn, old["id"])
        new_payload = bed_payload(conn, new["id"])

    manager.broadcast_threadsafe(dict(old_payload))
    manager.broadcast_threadsafe(dict(new_payload))
    return {"from": old_payload, "to": new_payload}


@router.post("/admissions/{admission_id}/discharge")
def discharge(admission_id: int, body: DischargeIn, user=Depends(current_user)):
    with pool.connection() as conn:
        adm = conn.execute(
            "SELECT id, bed_id FROM admissions "
            "WHERE id = %s AND discharged_at IS NULL FOR UPDATE",
            (admission_id,),
        ).fetchone()
        if not adm:
            raise HTTPException(404, "Active admission not found")
        bed = conn.execute(
            "SELECT id, ward_id, status, version FROM beds WHERE id = %s FOR UPDATE",
            (adm["bed_id"],),
        ).fetchone()
        check_ward(user, bed["ward_id"])
        if bed["version"] != body.version:
            raise HTTPException(409, "Bed was changed by someone else. Refresh and try again")

        conn.execute("UPDATE admissions SET discharged_at = now() WHERE id = %s", (adm["id"],))
        conn.execute(
            "UPDATE beds SET status = 'cleaning', version = version + 1 WHERE id = %s",
            (bed["id"],),
        )
        log_event(conn, bed["id"], bed["status"], "cleaning", user)
        result = bed_payload(conn, bed["id"])

    manager.broadcast_threadsafe(dict(result))
    return result