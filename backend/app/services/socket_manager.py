import socketio
from typing import Any

class SocketManager:
    def __init__(self):
        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self.app = socketio.ASGIApp(self.sio)

    async def emit(self, event: str, data: Any, room: str = None):
        await self.sio.emit(event, data, room=room)

socket_manager = SocketManager()
