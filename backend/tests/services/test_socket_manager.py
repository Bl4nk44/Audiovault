"""Tests covering socket_manager.py lines 17, 22, 25."""

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_socket_manager_emit():
    from app.services.socket_manager import SocketManager

    manager = SocketManager()
    manager.sio.emit = AsyncMock()
    await manager.emit("test_event", {"key": "val"}, room="room1")
    manager.sio.emit.assert_called_once_with("test_event", {"key": "val"}, room="room1")


@pytest.mark.asyncio
async def test_socket_manager_emit_no_room():
    from app.services.socket_manager import SocketManager

    manager = SocketManager()
    manager.sio.emit = AsyncMock()
    await manager.emit("ping", {})
    manager.sio.emit.assert_called_once_with("ping", {}, room=None)


@pytest.mark.asyncio
async def test_socket_connect_handler():
    from app.services.socket_manager import SocketManager

    manager = SocketManager()
    # Trigger the registered connect handler directly via socketio internals
    connect_fn = manager.sio.handlers.get("/", {}).get("connect")
    assert connect_fn is not None
    await connect_fn("sid_abc", {}, None)


@pytest.mark.asyncio
async def test_socket_disconnect_handler():
    from app.services.socket_manager import SocketManager

    manager = SocketManager()
    disconnect_fn = manager.sio.handlers.get("/", {}).get("disconnect")
    assert disconnect_fn is not None
    await disconnect_fn("sid_abc")
