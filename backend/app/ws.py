import asyncio
import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.auth import SECRET

router = APIRouter()


class Manager:
    def __init__(self):
        self.clients = {}   # websocket -> token claims (role, ward)
        self.loop = None

    async def connect(self, ws: WebSocket, claims: dict):
        await ws.accept()
        self.loop = asyncio.get_running_loop()
        self.clients[ws] = claims

    def disconnect(self, ws: WebSocket):
        self.clients.pop(ws, None)

    async def broadcast(self, data: dict):
        for ws, claims in list(self.clients.items()):
            # Hospital admins see every ward; others only their own
            if claims["role"] != "hospital_admin" and claims["ward"] != data["ward_id"]:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                self.clients.pop(ws, None)

    def broadcast_threadsafe(self, data: dict):
        # The bed endpoint runs in a worker thread, so hand the job to the event loop
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.broadcast(data), self.loop)


manager = Manager()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    # Browsers can't send headers on a WebSocket, so the token comes in the URL
    try:
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        await ws.close(code=4401)
        return
    await manager.connect(ws, claims)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)