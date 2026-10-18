# CareGrid

Every bed, every ward, live on one grid.

A real-time hospital bed management system built with FastAPI, PostgreSQL,
WebSockets and vanilla JavaScript. **All data in this project is synthetic.**

![CI](https://github.com/yourname/caregrid/actions/workflows/ci.yml/badge.svg)

## Features

- JWT login with three roles: nurse, ward admin, hospital admin
- Live bed grid: changes appear on every open dashboard via WebSockets, with auto-reconnect
- Admit, transfer and discharge patients; transfers are a single database transaction
- Optimistic locking (version column) so simultaneous edits get a 409, not a silent overwrite
- Valid status transitions enforced on the server; ward permissions enforced per role
- Audit log with filters and pagination
- Occupancy chart per ward and a banner at 90% or more
- Occupancy forecast (scikit-learn linear regression) that only assists staff
- Automated tests, including a 20-writer concurrency test, run by GitHub Actions

## Tech stack

Python, FastAPI, PostgreSQL (hand-written SQL), WebSockets, HTML, CSS,
JavaScript, Chart.js, scikit-learn, Docker, GitHub Actions

## Run with Docker

```
docker compose up --build
docker compose exec app python -m backend.create_users
```

Open http://localhost:8000 and log in with `nurse@caregrid.com` / `nurse123`
or `admin@caregrid.com` / `admin123` (demo accounts, synthetic data only).

## Run locally

1. Create a PostgreSQL database and load `backend/sql/schema.sql` then `backend/sql/seed.sql`
2. Copy `.env.example` to `.env` and fill it in
3. `pip install -r backend/requirements.txt`
4. `python -m backend.create_users`
5. `uvicorn backend.app.main:app --reload`

API docs are at `/docs`. Run the tests with `pytest`.

## Design notes

- **Concurrency:** `UPDATE ... WHERE id = %s AND version = %s`; zero rows means 409
- **Transfers:** both beds are locked in id order with `SELECT ... FOR UPDATE` to avoid deadlocks
- **Live updates:** broadcast only after the database commit, filtered by ward
- **Limit:** the WebSocket manager is in-memory, so it needs Redis pub/sub to scale past one server instance

## Screenshots

(add a dashboard screenshot and a short GIF of two windows syncing)