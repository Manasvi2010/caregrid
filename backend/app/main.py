import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.app.routes.auth_routes import router as auth_router
from backend.app.routes.wards import router as wards_router
from backend.app.routes.beds import router as beds_router
from backend.app.routes.admissions import router as admissions_router
from backend.app.routes.stats import router as stats_router
from backend.app.routes.audit import router as audit_router
from backend.app.routes.forecast import router as forecast_router, take_snapshots
from backend.app.ws import router as ws_router

SNAPSHOT_SECONDS = int(os.getenv("SNAPSHOT_SECONDS", "300"))


async def snapshot_loop():
    # Saves each ward's occupancy every few minutes (history for the forecast)
    while True:
        try:
            await asyncio.to_thread(take_snapshots)
        except Exception as e:
            print("snapshot failed:", e)
        await asyncio.sleep(SNAPSHOT_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(snapshot_loop())
    yield
    task.cancel()


app = FastAPI(title="CareGrid", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(wards_router)
app.include_router(beds_router)
app.include_router(admissions_router)
app.include_router(stats_router)
app.include_router(audit_router)
app.include_router(forecast_router)
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Must stay LAST so API routes, /ws and /docs take priority
FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")