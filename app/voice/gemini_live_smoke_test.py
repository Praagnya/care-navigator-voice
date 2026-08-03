import asyncio
from google import genai
from google.genai import types

# 1. Initialize client (reads GEMINI_API_KEY from environment)
client = genai.Client()

# Specify a Live API compatible model
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

async def main():
    # 2. Set up session configuration
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO], # 'AUDIO' or 'TEXT'
        system_instruction=types.Content(
            parts=[types.Part(text="You are a helpful, brief AI assistant.")]
        ),
    )

    # 3. Connect using client.aio.live.connect
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("Live session opened successfully!")

        # Send an initial message
        await session.send_realtime_input(text="Hello Gemini, are you connected?")

        # Listen for responses from the server
        async for response in session.receive():
            server_content = response.server_content
            if server_content and server_content.model_turn:
                for part in server_content.model_turn.parts:
                    if part.text:
                        print("Gemini:", part.text)
                    elif part.inline_data:
                        # Raw audio bytes returned from Gemini
                        audio_data = part.inline_data.data
                        print(f"Received audio chunk ({len(audio_data)} bytes)")

            # Exit loop once the current turn finishes
            if server_content and server_content.turn_complete:
                print("\nTurn completed.")
                break

if __name__ == "__main__":
    asyncio.run(main())