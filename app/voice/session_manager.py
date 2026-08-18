import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types
from app.config import get_settings
from app.voice.tool_declarations import TOOL_DECLARATIONS
from app.voice.tool_router import route_tool_call


# config from app config
MODEL = get_settings().gemini_model
API_KEY = get_settings().gemini_api_key

client = genai.Client(api_key=API_KEY)

class GeminiSessionManager:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.audio_in_queue = asyncio.Queue()
        self.audio_out_queue = asyncio.Queue()
        self.session = None
    
    async def run(self): 
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
            system_instruction=types.Content(
                parts=[types.Part(text="You are a helpful, brief AI assistant who only talks about healthcare and hospitals.")]
            ),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                )
            ),
        )

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            self.session = session
            await asyncio.gather(
                self._send_audio_loop(),
                self._receive_loop(),
                self._send_audio_out_loop(),
            )

    async def _send_audio_loop(self):
        while True:
            audio_data = await self.audio_in_queue.get()
            await self.session.send_realtime_input(audio = types.Blob(mime_type="audio/pcm;rate=16000",data=audio_data))

    async def _receive_loop(self):
        while True:
            async for response in self.session.receive():
                server_content = response.server_content
                if server_content and server_content.model_turn:
                    for part in server_content.model_turn.parts:
                        if part.text:
                            await self.websocket.send_text(part.text)
                        elif part.inline_data:
                            await self.audio_out_queue.put(part.inline_data.data)
                if server_content and server_content.interrupted:
                    await self.websocket.send_text("__interrupted__")
                    while not self.audio_out_queue.empty():
                        self.audio_out_queue.get_nowait()
                if server_content and server_content.turn_complete:
                    while not self.audio_in_queue.empty():
                        self.audio_in_queue.get_nowait()
                    await self.websocket.send_text("__turn_complete__")
                if response.tool_call:
                    await route_tool_call(response.tool_call, self.session)

    async def _send_audio_out_loop(self):
        while True:
            try:
                audio_data = await self.audio_out_queue.get()
                await self.websocket.send_bytes(audio_data)
            except WebSocketDisconnect:
                break