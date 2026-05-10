"""消息数据模型。"""

from dataclasses import dataclass, field
from typing import Optional
import json
import time as _time


@dataclass
class Message:
    message_id: int
    time: int                    # Unix timestamp (seconds)
    sender_id: int
    sender_name: str = ""
    sender_card: str = ""
    group_id: Optional[int] = None
    peer_id: int = 0             # group_id for group msg, sender_id for private
    message_type: str = ""       # "group" / "private"
    sub_type: str = ""
    msg_seq: int = 0
    raw_message: str = ""
    raw_json: str = ""           # full JSON for future re-processing

    @classmethod
    def from_onebot_event(cls, event: dict, self_id: int) -> "Message":
        """Parse a OneBot v11 message event into a Message."""
        sender = event.get("sender", {})
        msg_type = event.get("message_type", "")
        group_id = event.get("group_id")
        sender_id = event.get("user_id", 0)

        peer_id = group_id if msg_type == "group" else sender_id

        # Handle raw_message: if it's a JSON array string, keep as-is
        raw_message = event.get("raw_message", "")
        if not raw_message:
            # Try to extract text from message segments
            msg_segments = event.get("message", [])
            if isinstance(msg_segments, list):
                parts = []
                for seg in msg_segments:
                    if seg.get("type") == "text":
                        parts.append(seg.get("data", {}).get("text", ""))
                    elif seg.get("type") == "image":
                        parts.append("[图片]")
                    elif seg.get("type") == "record":
                        parts.append("[语音]")
                    elif seg.get("type") == "file":
                        parts.append(f"[文件:{seg.get('data',{}).get('name','')}]")
                raw_message = "".join(parts)

        return cls(
            message_id=event.get("message_id", 0),
            time=event.get("time", int(_time.time())),
            sender_id=sender_id,
            sender_name=sender.get("nickname", ""),
            sender_card=sender.get("card", ""),
            group_id=group_id,
            peer_id=peer_id,
            message_type=msg_type,
            sub_type=event.get("sub_type", ""),
            msg_seq=event.get("message_seq", 0),
            raw_message=raw_message,
            raw_json=json.dumps(event, ensure_ascii=False),
        )
