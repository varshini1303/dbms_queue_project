import json
from datetime import datetime, timedelta
from typing import List
from fastapi import WebSocket


class QueueManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.recent_updates: List[dict] = [
            {
                "id": "up-1",
                "text": "Your token A108 is approaching. Please plan to arrive soon.",
                "timestamp": (datetime.utcnow() - timedelta(minutes=2)).strftime("%I:%M %p"),
            },
            {
                "id": "up-2",
                "text": "Your estimated wait changed by 5 minutes.",
                "timestamp": (datetime.utcnow() - timedelta(minutes=6)).strftime("%I:%M %p"),
            },
            {
                "id": "up-3",
                "text": "A108 was successfully reserved for 10:30 AM.",
                "timestamp": (datetime.utcnow() - timedelta(minutes=14)).strftime("%I:%M %p"),
            },
        ]

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

    def add_update(self, text: str):
        update = {
            "id": f"up-{int(datetime.utcnow().timestamp())}",
            "text": text,
            "timestamp": datetime.utcnow().strftime("%I:%M %p"),
        }
        self.recent_updates.insert(0, update)
        if len(self.recent_updates) > 10:
            self.recent_updates.pop()
        return update


queue_manager = QueueManager()
