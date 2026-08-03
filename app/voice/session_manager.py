import asyncio
from fastapi import WebSocket
from google import genai
from google.genai import types
import os
import dotenv

dotenv.load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

MODEL = "gemini-2.5-flash"  # TODO: Make this configurable from app config
client = genai.Client()

class GeminiSessionManager:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.audio_in_queue = asyncio.Queue()
        self.audio_out_queue = asyncio.Queue()
        self.session = None
    
    async def run(self): 
        config = types.LiveConnectConfig(
            response_modalities=[types.ResponseModalities.AUDIO],
            system_instruction=types.Content(
                parts=[types.Part(text="You are a helpful, brief AI assistant.")]
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
            await self.session.send_realtime_input(audio = types.Blob(mime_type="audio/pcm;",data=audio_data))

    async def _receive_loop(self):
        while True:
            response = await self.session.receive_audio()
            await self.audio_out_queue.put(response)

    async def _send_audio_out_loop(self):
        while True:
            audio_data = await self.audio_out_queue.get()
            await self.websocket.send_audio(audio_data)