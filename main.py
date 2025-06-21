# main.py
import os
import base64
import json
import logging
import asyncio
import websockets
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-bridge")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
VOICE_ID = os.getenv("VOICE_ID")


async def handle_ws(websocket):
    logger.info("TeleCMI WebSocket connected")

    # Connect to ElevenLabs WebSocket
    elevenlabs_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(elevenlabs_url, headers=headers) as eleven_ws:

            async def forward_telecmi_to_elevenlabs():
                async for msg in websocket:
                    logger.debug("Message from TeleCMI: %s", msg)
                    try:
                        data = json.loads(msg)
                        if data.get("event") == "media":
                            audio_chunk = data.get("media", {}).get("payload")
                            if audio_chunk:
                                await eleven_ws.send_json({
                                    "user_audio_chunk": audio_chunk
                                })
                        elif data.get("event") == "start":
                            logger.info("Stream started: %s", data.get("start", {}).get("streamSid"))
                        elif data.get("event") == "stop":
                            logger.info("Stream stopped")
                            await eleven_ws.close()
                            break
                    except Exception as e:
                        logger.error("Error parsing TeleCMI message: %s", e)

            async def forward_elevenlabs_to_telecmi():
                async for msg in eleven_ws:
                    if msg.type.name == "TEXT":
                        message = json.loads(msg.data)
                        if message.get("type") == "audio":
                            audio_base64 = message.get("audio_event", {}).get("audio_base_64")
                            if audio_base64:
                                await websocket.send(json.dumps({
                                    "event": "media",
                                    "streamSid": "voice_sid_123",  # Replace with actual or dynamic SID
                                    "media": {"payload": audio_base64}
                                }))
                        elif message.get("type") == "interruption":
                            await websocket.send(json.dumps({
                                "event": "clear",
                                "streamSid": "voice_sid_123"
                            }))
                    elif msg.type.name == "CLOSE":
                        break

            await asyncio.gather(
                forward_telecmi_to_elevenlabs(),
                forward_elevenlabs_to_telecmi()
            )


async def main():
    logger.info("Starting WebSocket server on port 10000...")
    async with websockets.serve(handle_ws, "0.0.0.0", 10000):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
