#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, WebSocket

from anyio import Lock
from pycrdt import Channel
from pycrdt.websocket import WebsocketServer, exception_logger

from backend.common.security.jwt import jwt_authentication
from backend.database.db_pg import async_db_session
from backend.app.admin.crud.crud_user import user_dao

router = APIRouter()

# 全局单例，在 lifespan 中启动/停止
websocket_server = WebsocketServer(
    auto_clean_rooms=True,
    exception_handler=exception_logger,
)

# 光标颜色池，按 user_id 取模分配
_CURSOR_COLORS = [
    '#F44336', '#E91E63', '#9C27B0', '#3F51B5',
    '#2196F3', '#00BCD4', '#4CAF50', '#FF9800',
    '#FF5722', '#607D8B', '#8BC34A', '#FFC107',
]


def _cursor_color(user_id: int) -> str:
    return _CURSOR_COLORS[user_id % len(_CURSOR_COLORS)]


class _FastAPIChannel(Channel):
    """将 FastAPI WebSocket 适配为 pycrdt Channel 协议。"""

    def __init__(self, websocket: WebSocket, path: str):
        self._websocket = websocket
        self._path = path
        self._send_lock = Lock()

    @property
    def path(self) -> str:
        return self._path

    async def send(self, message: bytes) -> None:
        async with self._send_lock:
            await self._websocket.send_bytes(message)

    async def recv(self) -> bytes:
        data = await self._websocket.receive_bytes()
        return bytes(data)

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return await self.recv()
        except Exception:
            raise StopAsyncIteration()


@router.websocket('/{doc_id}')
async def collab_websocket(websocket: WebSocket, doc_id: int):
    """
    Y.js 协同编辑 WebSocket 端点。

    认证：通过查询参数传递 JWT Token，例：
        ws://host/api/v1/sys/collab/42?token=<jwt>
    """
    token = websocket.query_params.get('token')
    if not token:
        await websocket.close(code=4001, reason='Missing token')
        return

    try:
        user_id = await jwt_authentication(token)
    except Exception:
        await websocket.close(code=4001, reason='Invalid or expired token')
        return

    await websocket.accept()

    channel = _FastAPIChannel(websocket, path=str(doc_id))
    await websocket_server.serve(channel)
