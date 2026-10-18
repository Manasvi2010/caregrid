from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.app.routes.auth_routes import router as auth_router
from backend.app.routes.wards import router as wards_router
from backend.app.routes.beds import router as beds_router
from backend.app.ws import router as ws_router

app = FastAPI(title="CareGrid")
app.include_router(auth_router)
app.include_router(wards_router)
app.include_router(beds_router)
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Must stay LAST so API routes, /ws and /docs take priority
FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")