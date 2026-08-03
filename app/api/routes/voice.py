from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.voice.session_manager import GeminiSessionManager
import asyncio


router = APIRouter(tags=["voice"])

@router.websocket("/voice")
async def voice_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_manager = GeminiSessionManager(websocket)
    try:
        await asyncio.gather(
            session_manager.run(),
            client_to_agent(websocket, session_manager),
        )
    except WebSocketDisconnect:
        pass

async def client_to_agent(websocket: WebSocket, session_manager: GeminiSessionManager):
    while True:
        message = await websocket.receive_bytes()
        await session_manager.audio_in_queue.put(message)
