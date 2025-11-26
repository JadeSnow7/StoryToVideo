#!/bin/bash
# 1. 加载 .env 变量
set -a
source .env
set +a

# 2. 启动 FRPS (后台运行)
echo "Starting FRPS..."
./frps -c frps.toml &
FRPS_PID=$!

# 3. 等待 2 秒
sleep 2

# 4. 启动 FRPC Visitor (后台运行)
echo "Starting FRPC Visitor..."
./frpc -c frpc_visitor.toml &
FRPC_PID=$!

echo "Both services started (PIDs: $FRPS_PID, $FRPC_PID)."

# 5. 等待进程结束（保持脚本运行，否则容器/脚本会立刻退出）
wait $FRPS_PID $FRPC_PID