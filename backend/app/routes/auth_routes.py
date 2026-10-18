from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.db import pool
from backend.app.auth import check_pw, make_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginIn):
    with pool.connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = %s", (body.email,)
        ).fetchone()
    if not user or not check_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    return {"access_token": make_token(user), "role": user["role"]}