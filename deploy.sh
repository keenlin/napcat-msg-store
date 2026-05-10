#!/bin/bash
# napcat-msg-store 首次部署脚本
# 从旧 NapCat 容器迁移数据到新 docker-compose 管理的命名卷
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo " napcat-msg-store 部署脚本 v0.1.0"
echo "=========================================="

# Step 1: 检查旧容器
if docker ps --format '{{.Names}}' | grep -q "^napcat$"; then
    echo "[1/6] 停止旧 NapCat 容器..."
    docker stop napcat
fi

# Step 2: 迁移旧匿名卷数据到新命名卷
OLD_NC_VOL=$(docker volume ls -q | grep -E '236e5d40626022f3860611c783bf0b7c3277535ed1806728c55b3e7ec4bb051d' | head -1)
OLD_QQ_VOL=$(docker volume ls -q | grep -E '27e4e841927b1139cc6ea5c7423642a6b5c26c111f138aa6e74b884e9511243a' | head -1)

if [ -n "$OLD_NC_VOL" ]; then
    echo "[2/6] 迁移 NapCat 配置卷: $OLD_NC_VOL -> napcat_config_v1"
    docker volume create napcat_config_v1 2>/dev/null || true
    docker run --rm \
        -v "${OLD_NC_VOL}:/from:ro" \
        -v napcat_config_v1:/to \
        alpine cp -a /from/. /to/
    echo "  ✓ napcat_config_v1 迁移完成"
fi

if [ -n "$OLD_QQ_VOL" ]; then
    echo "[3/6] 迁移 QQ 数据卷: $OLD_QQ_VOL -> napcat_qq_data_v1"
    docker volume create napcat_qq_data_v1 2>/dev/null || true
    docker run --rm \
        -v "${OLD_QQ_VOL}:/from:ro" \
        -v napcat_qq_data_v1:/to \
        alpine cp -a /from/. /to/
    echo "  ✓ napcat_qq_data_v1 迁移完成"
fi

# Step 3: 移除旧容器（可选，保留镜像）
echo "[4/6] 清理旧容器..."
docker rm napcat 2>/dev/null || true

# Step 4: 构建 msg-store 镜像
echo "[5/6] 构建 napcat-msg-store 镜像..."
docker compose build msg-store

# Step 5: 拉取 NapCat 镜像
echo "  拉取 NapCat 最新镜像..."
docker pull mlikiowa/napcat-docker:latest

# Step 6: 启动
echo "[6/6] 启动 docker compose..."
docker compose up -d

echo ""
echo "=========================================="
echo " 部署完成！"
echo "=========================================="
echo ""
echo "服务状态查看: docker compose ps"
echo "日志: docker compose logs -f"
echo ""
echo "端点:"
echo "  NapCat HTTP API: http://localhost:3000"
echo "  NapCat WebUI:    http://localhost:6099"
echo "  msg-store API:   http://localhost:8788"
echo "    /health  - 健康检查"
echo "    /stats   - 统计信息"
echo "    /messages - 消息查询"
echo ""
echo "迁移后务必检查 NapCat 登录状态："
echo "  docker logs napcat | tail -20"
echo "  如果显示二维码，需扫码重新登录"
