import os
import asyncio
import websockets
import logging
from fastapi import FastAPI
from dotenv import load_dotenv
import aiohttp
import json

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-bridge")

# FastAPI app for Render
app = FastAPI()

# ElevenLabs config
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# WebSocket handler
async def handle_connection(websocket):
    logger.info("🔌 New WebSocket connection established")
    async with aiohttp.ClientSession() as session:
        try:
            async for message in websocket:
                logger.info("🎤 Received audio message from TeleCMI")

                # Simulate response: Here you would call speech-to-text, generate a reply, then TTS
                text_response = "Hello! This is ElevenLabs speaking."
                logger.info(f"🤖 AI Response Text: {text_response}")

                # ElevenLabs TTS API
                tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
                headers = {
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                }
                payload = {
                    "text": text_response,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.5
                    }
                }

                async with session.post(tts_url, headers=headers, json=payload) as tts_response:
                    if tts_response.status == 200:
                        audio_data = await tts_response.read()
                        await websocket.send(audio_data)
                        logger.info("📤 Sent TTS audio back to TeleCMI")
                    else:
                        logger.error(f"❌ ElevenLabs TTS failed with status: {tts_response.status}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 WebSocket connection closed")


@app.on_event("startup")
async def start_websocket_server():
    logger.info("🚀 Starting WebSocket server on port 10000...")

    async def server():
        async with websockets.serve(handle_connection, "0.0.0.0", 10000):
            await asyncio.Future()  # Run forever

    asyncio.create_task(server())
