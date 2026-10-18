from backend.app.db import pool

POINTS = 36          # one reading every 10 minutes = 6 hours
STEP_MIN = 10
RISE = 60            # how many percentage points occupancy climbs over the period


def main():
    with pool.connection() as conn:
        wards = conn.execute(
            "SELECT w.id, count(b.id) AS total, "
            "count(b.id) FILTER (WHERE b.status = 'occupied') AS occupied "
            "FROM wards w JOIN beds b ON b.ward_id = w.id GROUP BY w.id"
        ).fetchall()
        conn.execute("DELETE FROM occupancy_snapshots")
        for w in wards:
            end = w["occupied"] * 100 / w["total"]
            start = max(0.0, end - RISE)
            for i in range(POINTS):
                pct = start + (end - start) * i / (POINTS - 1)
                if i < POINTS - 1:
                    pct += ((i * 7) % 5) - 2          # small repeatable wobble
                count = max(0, min(w["total"], round(w["total"] * pct / 100)))
                conn.execute(
                    "INSERT INTO occupancy_snapshots (ward_id, taken_at, occupied_count, total) "
                    "VALUES (%s, now() - make_interval(mins => %s), %s, %s)",
                    (w["id"], (POINTS - 1 - i) * STEP_MIN, count, w["total"]),
                )
    print("Synthetic occupancy history created for", len(wards), "wards")


if __name__ == "__main__":
    main()