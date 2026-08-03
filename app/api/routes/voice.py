from fastapi import APIRouter, WebSocket


router = APIRouter(tags=["voice"])

@router.websocket("/voice")
async def voice_endpoint(websocket: WebSocket):
    await websocket.accept()
    # create session manager 
    # run client_to_agent and agent_to_client coroutines
    # handle errors and disconnects
    # close websocket
    pass 

async def client_to_agent(websocket: WebSocket, session_manager: SessionManager):
    try:
        while True:
            message = await websocket.receive_text()
            await session_manager.client_to_agent(message)
    except WebSocketDisconnect:
        await session_manager.client_to_agent_disconnect()

async def agent_to_client(websocket: WebSocket, session_manager: SessionManager):
    pass 