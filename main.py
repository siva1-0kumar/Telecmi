# main.py

import asyncio
import websockets
import base64
import json
import requests
import os
from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv

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
    print("WebSocket connected")

    try:
        async with websockets.connect(
            f"wss://api.elevenlabs.io/v1/agents/{ELEVENLABS_AGENT_ID}/stream",
            extra_headers={"xi-api-key": ELEVENLABS_API_KEY},
            max_size=2**24
        ) as eleven_ws:

            async def receive_from_telecmi():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await eleven_ws.send(data)
                except Exception as e:
                    print(f"Error receiving from TeleCMI: {e}")

            async def receive_from_elevenlabs():
                try:
                    while True:
                        data = await eleven_ws.recv()
                        if isinstance(data, bytes):
                            await websocket.send_bytes(data)
                        else:
                            print("Received non-bytes from ElevenLabs:", data)
                except Exception as e:
                    print(f"Error receiving from ElevenLabs: {e}")

            await asyncio.gather(
                receive_from_telecmi(),
                receive_from_elevenlabs()
            )
    except Exception as e:
        print(f"WebSocket connection error: {e}")

@app.get("/trigger-call")
def trigger_call():
    url = "https://api.telecmi.com/v1/call"
    headers = {"Content-Type": "application/json"}
    payload = {
        "app_id": TELECMI_APP_ID,
        "secret": TELECMI_SECRET,
        "from": TELECMI_PHONE,
        "to": TELECMI_PHONE,
        "websocket_url": "wss://tele2-2.onrender.com/ws",
        "stream_direction": "bidirectional",
        "event_url": "https://your-callback-url.com/event",
        "play": [
            {
                "text": "Hello, this is ElevenLabs AI speaking with you over TeleCMI.",
                "voice": "Rachel"
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    print("Call trigger response:", response.status_code, response.text)
    return response.json()



