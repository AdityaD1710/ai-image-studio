from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, job_id: str, ws: WebSocket):
        await ws.accept()
        self.active[job_id] = ws

    def disconnect(self, job_id: str):
        self.active.pop(job_id, None)

    async def send_progress(self, job_id: str, stage: str, pct: int):
        ws = self.active.get(job_id)
        if ws:
            await ws.send_json({"stage": stage, "progress": pct})

manager = ConnectionManager()