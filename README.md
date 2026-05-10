# napcat-msg-store

持久化存储 NapCat (QQ) 聊天消息到 SQLite 数据库。

通过 WebSocket 连接 NapCat OneBot v11，**实时接收**群聊和私聊消息，存入 SQLite，并提供 HTTP API 查询历史记录。

## 为什么需要这个工具？

NapCat 的 OneBot HTTP API (`get_group_msg_history`) 只能获取 QQ 内存中缓存的最近几十条消息。一旦消息被挤出内存，再也查不到。

`napcat-msg-store` 在消息到达的瞬间就存到 SQLite，**一条都不会丢**。你可以：
- 定时任务查询今天的群消息（不用依赖 NapCat 的内存缓存）
- 统计某个群一周的消息量
- 按关键词回溯历史聊天记录
- 导出为 JSON 做进一步分析

## 架构

```
┌─────────────────────────────────────┐
│         docker compose              │
│                                     │
│  ┌─────────────┐    ┌─────────────┐ │
│  │   napcat    │    │ msg-store   │ │
│  │             │◄───│             │ │
│  │  HTTP :3000 │    │  HTTP :8788 │ │
│  │   WS :3000  │    │  SQLite DB  │ │
│  │  WebUI:6099 │    │             │ │
│  └─────────────┘    └─────────────┘ │
│       ↑                    ↑        │
│  napcat-data/        msg_data/      │
│  (QQ 登录态)        (消息数据库)    │
└─────────────────────────────────────┘
```

## 快速开始

### 前置条件

- 已有一个运行中的 NapCat Docker 容器（`mlikiowa/napcat-docker`）
- NapCat 已扫码登录 QQ，且 OneBot HTTP API 已启用（端口 3000，`enableWebsocket: true`）
- Docker + Docker Compose

### 部署

```bash
git clone https://github.com/vvtommy/napcat-msg-store.git
cd napcat-msg-store

# 迁移旧容器数据 + 启动新 docker compose
chmod +x deploy.sh
./deploy.sh
```

部署脚本会自动：
1. 停止旧 NapCat 容器
2. 迁移匿名卷数据到新的命名卷（保留 QQ 登录态，无需重新扫码）
3. 构建 msg-store 镜像
4. 用 docker compose 同时启动 NapCat 和 msg-store

### 验证

```bash
# 查看服务状态
docker compose ps

# 健康检查
curl http://localhost:8788/health
# {"status": "ok", "uptime_seconds": 123.4, "messages_stored": 567, "ws_connected": true}

# 查看统计
curl http://localhost:8788/stats
```

## HTTP API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查，返回存储消息数、WS 连接状态 |
| `/stats` | GET | 统计信息：总消息数、活跃群聊排名 |
| `/messages` | GET | 查询消息，支持 `?peer_id=xxx&since=1700000000&limit=100` |
| `/peers` | GET | 活跃会话列表 |

## 环境变量

msg-store 容器支持以下环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `NAPCAT_WS_URL` | `ws://localhost:3000` | NapCat WebSocket 地址 |
| `NAPCAT_ACCESS_TOKEN` | (空) | NapCat access token（与 HTTP API 共用） |
| `DB_PATH` | `/app/data/msg.db` | SQLite 数据库路径 |
| `PORT` | `8788` | HTTP API 端口 |

## 开发

```bash
# 创建虚拟环境
uv venv
source .venv/bin/activate

# 安装依赖
uv pip install -e ".[dev]"

# 本地运行（需要本地 NapCat 在 localhost:3000）
napcat-msg-store

# 运行测试
pytest
```

## 数据库结构

```sql
messages (
    id, message_id, time, sender_id, sender_name, sender_card,
    group_id, peer_id, message_type, sub_type, msg_seq,
    raw_message, raw_json, created_at
)
```

`peer_id` = `group_id`（群聊）或 `sender_id`（私聊），方便统一查询。

## 技术栈

- Python 3.13 + uv
- websockets（异步 WebSocket 客户端，指数退避重连）
- aiohttp（HTTP API 服务）
- aiosqlite（异步 SQLite）
- Docker multi-stage build

## License

MIT
