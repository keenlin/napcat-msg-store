"""SQLite 数据库操作。"""

import aiosqlite
import time
from pathlib import Path
from typing import Optional, AsyncIterator

from .models import Message

DDL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    time INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    sender_name TEXT DEFAULT '',
    sender_card TEXT DEFAULT '',
    group_id INTEGER,
    peer_id INTEGER NOT NULL,
    message_type TEXT NOT NULL,
    sub_type TEXT DEFAULT '',
    msg_seq INTEGER DEFAULT 0,
    raw_message TEXT DEFAULT '',
    raw_json TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_message_id ON messages(message_id);
CREATE INDEX IF NOT EXISTS idx_peer_time ON messages(peer_id, time);
CREATE INDEX IF NOT EXISTS idx_time ON messages(time);
CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_group ON messages(group_id);
"""

INSERT_SQL = """
INSERT OR IGNORE INTO messages
    (message_id, time, sender_id, sender_name, sender_card,
     group_id, peer_id, message_type, sub_type, msg_seq,
     raw_message, raw_json)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)

    async def init(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.executescript(DDL)
            await db.commit()

    async def insert(self, msg: Message):
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute(INSERT_SQL, (
                msg.message_id, msg.time, msg.sender_id, msg.sender_name,
                msg.sender_card, msg.group_id, msg.peer_id, msg.message_type,
                msg.sub_type, msg.msg_seq, msg.raw_message, msg.raw_json,
            ))
            await db.commit()

    async def count(self) -> int:
        async with aiosqlite.connect(str(self.db_path)) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM messages")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_stats(self) -> dict:
        async with aiosqlite.connect(str(self.db_path)) as db:
            total = await self.count()

            # Top groups
            cursor = await db.execute(
                "SELECT group_id, COUNT(*) as cnt FROM messages "
                "WHERE message_type='group' AND group_id IS NOT NULL "
                "GROUP BY group_id ORDER BY cnt DESC LIMIT 10"
            )
            groups = [{"group_id": row[0], "count": row[1]} async for row in cursor]

            # Last message time
            cursor = await db.execute("SELECT MAX(time) FROM messages")
            row = await cursor.fetchone()
            last_ts = row[0] if row and row[0] else 0

            return {
                "total_messages": total,
                "top_groups": groups,
                "last_message_time": last_ts,
                "last_message_iso": time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(last_ts)
                ) if last_ts else None,
            }

    async def query(
        self,
        peer_id: Optional[int] = None,
        since: Optional[int] = None,
        until: Optional[int] = None,
        sender_id: Optional[int] = None,
        message_type: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        conditions = []
        params: list = []

        if peer_id is not None:
            conditions.append("peer_id = ?")
            params.append(peer_id)
        if since is not None:
            conditions.append("time >= ?")
            params.append(since)
        if until is not None:
            conditions.append("time < ?")
            params.append(until)
        if sender_id is not None:
            conditions.append("sender_id = ?")
            params.append(sender_id)
        if message_type:
            conditions.append("message_type = ?")
            params.append(message_type)
        if keyword:
            conditions.append("raw_message LIKE ?")
            params.append(f"%{keyword}%")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM messages {where} ORDER BY time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
