"""HTTP API 服务：健康检查 + 消息查询。"""

import time
from typing import Optional

from aiohttp import web

from .database import Database
from .ws_client import WebSocketClient

routes = web.RouteTableDef()
_start_time = time.time()


def _uptime() -> float:
    return time.time() - _start_time


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    ws: WebSocketClient = request.app["ws_client"]
    count = await db.count()
    return web.json_response({
        "status": "ok",
        "uptime_seconds": round(_uptime(), 1),
        "messages_stored": count,
        "ws_connected": ws.connected,
    })


@routes.get("/stats")
async def stats(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    s = await db.get_stats()
    return web.json_response(s)


@routes.get("/messages")
async def messages(request: web.Request) -> web.Response:
    db: Database = request.app["db"]

    peer_id = request.query.get("peer_id")
    since = request.query.get("since")
    until = request.query.get("until")
    sender_id = request.query.get("sender_id")
    msg_type = request.query.get("type")
    keyword = request.query.get("keyword")
    limit = int(request.query.get("limit", "100"))
    offset = int(request.query.get("offset", "0"))

    rows = await db.query(
        peer_id=int(peer_id) if peer_id else None,
        since=int(since) if since else None,
        until=int(until) if until else None,
        sender_id=int(sender_id) if sender_id else None,
        message_type=msg_type,
        keyword=keyword,
        limit=min(limit, 1000),
        offset=offset,
    )
    return web.json_response({"count": len(rows), "messages": rows})


@routes.get("/peers")
async def peers(request: web.Request) -> web.Response:
    """Get list of active peers (groups and private chats) with message counts."""
    db: Database = request.app["db"]
    async with db.__class__(db.db_path)._connect() as conn:
        pass

    # Return from stats as a proxy
    s = await db.get_stats()
    return web.json_response(s.get("top_groups", []))


async def start_server(db: Database, ws_client: WebSocketClient, port: int):
    app = web.Application()
    app["db"] = db
    app["ws_client"] = ws_client
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP API listening on 0.0.0.0:{port}")

    # Keep running forever (caller manages cancellation)
    while True:
        await asyncio.sleep(3600)

import asyncio
