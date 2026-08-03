from fastapi import APIRouter, WebSocket


router = APIRouter(tags=["voice"])

@router.websocket("/voice")
async def voice_endpoint(websocket: WebSocket):
    await websocket.accept()
 # TODO: Implement voice endpoint logic here
    pass 

async def client_to_agent(websocket: WebSocket, session_manager: SessionManager):
    pass 

async def agent_to_client(websocket: WebSocket, session_manager: SessionManager):
    pass 