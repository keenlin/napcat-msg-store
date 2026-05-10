"""napcat-msg-store — 持久化存储 NapCat (QQ) 消息到 SQLite。

通过 WebSocket 连接 NapCat OneBot v11，实时接收群聊和私聊消息，
存入 SQLite 数据库，并提供 HTTP API 查询。

Usage:
    python -m napcat_msg_store.main
"""

import asyncio
import logging
import signal
import sys

from .config import settings
from .database import Database
from .ws_client import WebSocketClient
from .server import start_server

logger = logging.getLogger("napcat-msg-store")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


async def main():
    logger.info("Starting napcat-msg-store v0.1.0")
    logger.info(f"WebSocket URL: {settings.napcat_ws_url}")
    logger.info(f"DB path: {settings.db_path}")
    logger.info(f"HTTP port: {settings.port}")

    db = Database(settings.db_path)
    await db.init()
    logger.info(f"Database initialized ({settings.db_path})")

    ws_client = WebSocketClient(db, settings)

    # Run WS and HTTP server concurrently
    ws_task = asyncio.create_task(ws_client.connect())
    server_task = asyncio.create_task(start_server(db, ws_client, settings.port))

    # Wait for shutdown signal
    stop = asyncio.Event()

    def _handler():
        logger.info("Shutting down...")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    await stop.wait()

    ws_task.cancel()
    server_task.cancel()
    try:
        await asyncio.gather(ws_task, server_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    logger.info("Shutdown complete")


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
