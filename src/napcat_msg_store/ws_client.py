"""WebSocket 客户端：连接 NapCat OneBot v11 并接收消息事件。"""

import asyncio
import json
import logging
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed

from .config import Settings
from .database import Database
from .models import Message

logger = logging.getLogger("napcat-msg-store.ws")


class WebSocketClient:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings
        self.self_id: Optional[int] = None
        self._running = False
        self._reconnect_count = 0

    @property
    def connected(self) -> bool:
        return self._running

    async def connect(self):
        """Main loop: connect and re-connect on failure."""
        url = self.settings.napcat_ws_url
        token = self.settings.napcat_token
        extra_headers = {}
        if token:
            extra_headers["Authorization"] = f"Bearer {token}"

        while True:
            try:
                logger.info(f"Connecting to {url} ...")
                async with websockets.connect(
                    url,
                    extra_headers=extra_headers,
                    ping_interval=30,
                    ping_timeout=10,
                    max_size=2**23,  # 8MB
                ) as ws:
                    self._running = True
                    self._reconnect_count = 0
                    logger.info("WebSocket connected")

                    async for raw in ws:
                        try:
                            await self._handle(raw)
                        except Exception:
                            logger.exception("Error handling message")
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                self._running = False
                self._reconnect_count += 1
                delay = min(
                    self.settings.reconnect_min_delay
                    * (self.settings.reconnect_factor ** (self._reconnect_count - 1)),
                    self.settings.reconnect_max_delay,
                )
                logger.warning(
                    f"Disconnected ({e}), reconnecting in {delay:.1f}s "
                    f"(attempt {self._reconnect_count})"
                )
                await asyncio.sleep(delay)
            except Exception:
                self._running = False
                logger.exception("Unexpected error, reconnecting in 5s")
                await asyncio.sleep(5)

    async def _handle(self, raw: str):
        """Handle a single WebSocket message."""
        data = json.loads(raw)

        # Capture self_id from meta_event lifecycle
        if data.get("post_type") == "meta_event":
            if data.get("meta_event_type") == "lifecycle":
                self.self_id = data.get("self_id")
                logger.info(f"Lifecycle event: self_id={self.self_id}")
            return

        # Only process message events
        if data.get("post_type") != "message":
            return

        self_id = self.self_id or 0
        msg = Message.from_onebot_event(data, self_id)
        await self.db.insert(msg)

        preview = msg.raw_message[:80].replace("\n", " ")
        logger.debug(
            f"[{msg.message_type}] {msg.sender_name}({msg.sender_id}): {preview}"
        )
