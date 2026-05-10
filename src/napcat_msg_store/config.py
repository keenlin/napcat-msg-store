"""配置：从环境变量读取。"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    napcat_ws_url: str = field(
        default_factory=lambda: os.getenv("NAPCAT_WS_URL", "ws://localhost:3000")
    )
    napcat_token: str = field(
        default_factory=lambda: os.getenv("NAPCAT_ACCESS_TOKEN", "")
    )
    db_path: str = field(
        default_factory=lambda: os.getenv("DB_PATH", "/app/data/msg.db")
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("PORT", "8788"))
    )
    reconnect_min_delay: float = 1.0
    reconnect_max_delay: float = 60.0
    reconnect_factor: float = 2.0


settings = Settings()
