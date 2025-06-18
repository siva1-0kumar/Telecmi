
import asyncio
import websockets
import base64
import json
import requests
import os
from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
from starlette.responses import JSONResponse

load_dotenv()

TELECMI_APP_ID = os.getenv("TELECMI_APP_ID")
TELECMI_SECRET = os.getenv("TELECMI_SECRET")
TELECMI_PHONE = os.getenv("TELECMI_PHONE")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket connected from TeleCMI")

    try:
        async with websockets.connect(
            f"wss://api.elevenlabs.io/v1/agents/{ELEVENLABS_AGENT_ID}/stream",
            extra_headers={"xi-api-key": ELEVENLABS_API_KEY},
            max_size=2**24
        ) as eleven_ws:

            async def receive_from_telecmi():
                while True:
                    try:
                        data = await websocket.receive_text()
                        message = json.loads(data)
                        if message.get("type") == "media":
                            audio_base64 = message.get("media", {}).get("payload")
                            if audio_base64:
                                audio_bytes = base64.b64decode(audio_base64)
                                await eleven_ws.send(audio_bytes)
                    except Exception as e:
                        print(f"[❌] TeleCMI receive error: {e}")
                        break

            async def receive_from_elevenlabs():
                while True:
                    try:
                        data = await eleven_ws.recv()
                        if isinstance(data, bytes):
                            audio_base64 = base64.b64encode(data).decode("utf-8")
                            await websocket.send_text(json.dumps({
                                "type": "media",
                                "media": {
                                    "payload": audio_base64
                                }
                            }))
                        else:
                            print("[⚠️] Non-bytes message from ElevenLabs:", data)
                    except Exception as e:
                        print(f"[❌] ElevenLabs receive error: {e}")
                        break

            await asyncio.gather(
                receive_from_telecmi(),
                receive_from_elevenlabs()
            )

    except Exception as e:
        print(f"[❌] WebSocket session failed: {e}")

@app.get("/trigger-call")
def trigger_call():
    print("⚙️ Triggering TeleCMI call...")

    if not all([TELECMI_APP_ID, TELECMI_SECRET, TELECMI_PHONE]):
        return JSONResponse(status_code=500, content={"error": "Missing TeleCMI env variables"})

    url = "https://api.telecmi.com/v1/call"
    headers = {"Content-Type": "application/json"}
    payload = {
        "app_id": TELECMI_APP_ID,
        "secret": TELECMI_SECRET,
        "from": TELECMI_PHONE,
        "to": TELECMI_PHONE,
        "websocket_url": "wss://telecmi.onrender.com/ws",
        "stream_direction": "bidirectional",
        "event_url": "https://your-callback-url.com/event",  # Optional
        "play": [
            {
                "text": "Hello, this is ElevenLabs AI speaking with you over TeleCMI.",
                "voice": "Rachel"
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        print("📞 Call trigger response:", response.status_code, response.text)
        return response.json()
    except Exception as e:
        print(f"[❌] Failed to trigger call: {e}")
        return JSONResponse(status_code=500, content={"error": "Call trigger failed"})
