# main.py
import asyncio
import websockets
import json
import os
import base64
import logging
import aiohttp
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-bridge")

async def handle_connection(websocket):
    logger.info("[TeleCMI] New WebSocket call session connected")

    # Connect to ElevenLabs Conversational AI
    elevenlabs_ws = await websockets.connect(
        f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}",
        extra_headers={"xi-api-key": ELEVENLABS_API_KEY},
    )

    async def from_telecmi_to_elevenlabs():
        try:
            async for message in websocket:
                logger.debug("[TeleCMI] --> Audio")
                try:
                    data = json.loads(message)
                    if data.get("event") == "media" and data.get("media"):
                        audio_chunk = {
                            "user_audio_chunk": data["media"]["payload"]
                        }
                        await elevenlabs_ws.send(json.dumps(audio_chunk))
                except Exception as e:
                    logger.error(f"Error processing TeleCMI message: {e}")
        except Exception as e:
            logger.warning(f"[TeleCMI] Disconnected: {e}")

    async def from_elevenlabs_to_telecmi():
        try:
            async for msg in elevenlabs_ws:
                logger.debug("[ElevenLabs] --> Audio")
                try:
                    response = json.loads(msg)
                    if response.get("type") == "audio":
                        audio_base64 = response["audio_event"]["audio_base_64"]
                        await websocket.send(json.dumps({
                            "event": "media",
                            "media": {
                                "payload": audio_base64
                            }
                        }))
                    elif response.get("type") == "interruption":
                        await websocket.send(json.dumps({"event": "clear"}))
                    elif response.get("type") == "ping":
                        await elevenlabs_ws.send(json.dumps({
                            "type": "pong",
                            "event_id": response["ping_event"]["event_id"]
                        }))
                except Exception as e:
                    logger.error(f"Error processing ElevenLabs message: {e}")
        except Exception as e:
            logger.warning(f"[ElevenLabs] Disconnected: {e}")

    await asyncio.gather(
        from_telecmi_to_elevenlabs(),
        from_elevenlabs_to_telecmi()
    )

    await elevenlabs_ws.close()
    logger.info("[Session] Closed")

async def main():
    logger.info(f"Starting WebSocket server on port {PORT}...")
    async with websockets.serve(handle_connection, "0.0.0.0", PORT, subprotocols=["telecmi"]):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
