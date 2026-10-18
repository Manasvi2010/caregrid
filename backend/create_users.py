from backend.app.db import pool
from backend.app.auth import hash_pw

users = [
    ("Nurse Asha", "nurse@caregrid.com", "nurse123", "nurse", 1),
    ("Ward Admin Ravi", "wardadmin@caregrid.com", "admin123", "ward_admin", 1),
    ("Hospital Admin Meena", "admin@caregrid.com", "admin123", "hospital_admin", None),
]

with pool.connection() as conn:
    for name, email, pw, role, ward in users:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, role, ward_id) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (email) DO NOTHING",
            (name, email, hash_pw(pw), role, ward),
        )
print("Users created")