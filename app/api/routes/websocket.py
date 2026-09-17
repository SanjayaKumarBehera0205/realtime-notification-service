from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.realtime.manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/notifications")
async def notification_socket(websocket: WebSocket, token: str) -> None:
    try:
        user_id = decode_access_token(token)
        with SessionLocal() as db:
            if db.get(User, user_id) is None:
                raise ValueError("Unknown user")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user_id, websocket)
    await websocket.send_json({"event": "connected", "user_id": user_id})
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
