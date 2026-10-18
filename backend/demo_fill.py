import sys
from backend.app.db import pool


def main():
    ward_id, count = int(sys.argv[1]), int(sys.argv[2])
    with pool.connection() as conn:
        admin = conn.execute(
            "SELECT id FROM users WHERE role = 'hospital_admin' LIMIT 1"
        ).fetchone()
        beds = conn.execute(
            "SELECT id FROM beds WHERE ward_id = %s AND status = 'available' "
            "ORDER BY id LIMIT %s",
            (ward_id, count),
        ).fetchall()
        for n, b in enumerate(beds, 1):
            p = conn.execute(
                "INSERT INTO patients (name, age, gender) VALUES (%s, %s, %s) RETURNING id",
                (f"Demo Patient {b['id']}", 30 + n, "Other"),
            ).fetchone()
            conn.execute(
                "INSERT INTO admissions (patient_id, bed_id) VALUES (%s, %s)",
                (p["id"], b["id"]),
            )
            conn.execute(
                "UPDATE beds SET status = 'occupied', version = version + 1 WHERE id = %s",
                (b["id"],),
            )
            conn.execute(
                "INSERT INTO bed_events (bed_id, old_status, new_status, changed_by) "
                "VALUES (%s, 'available', 'occupied', %s)",
                (b["id"], admin["id"]),
            )
    print(f"Admitted {len(beds)} demo patients to ward {ward_id}")


if __name__ == "__main__":
    main()