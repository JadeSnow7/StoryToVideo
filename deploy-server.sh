#!/bin/bash
set -e

REMOTE_HOST="106.54.188.236"
REMOTE_USER="snow"
REMOTE_PASS="0"
REMOTE_DIR="/home/snow/StoryToVideo"

echo "=== StoryToVideo Server 部署脚本 ==="

# Step 1: 检查 sshpass
if ! command -v sshpass &> /dev/null; then
    echo "错误: 请先安装 sshpass"
    exit 1
fi

# SSH 命令封装
SSH_CMD="sshpass -p '$REMOTE_PASS' ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST"
SCP_CMD="sshpass -p '$REMOTE_PASS' scp -o StrictHostKeyChecking=no -r"

echo "1. 测试 SSH 连接..."
eval "$SSH_CMD 'echo SSH 连接成功'"

# Step 2: 安装 Docker (如果未安装)
echo "2. 检查/安装 Docker..."
eval "$SSH_CMD 'if ! command -v docker &> /dev/null; then
    echo \"正在安装 Docker...\"
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \$VERSION_CODENAME) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker $USER
    echo \"Docker 安装完成\"
else
    echo \"Docker 已安装\"
fi'"

# Step 3: 创建远程目录
echo "3. 创建远程目录..."
eval "$SSH_CMD 'mkdir -p $REMOTE_DIR'"

# Step 4: 复制文件
echo "4. 复制项目文件到远程服务器..."
eval "$SCP_CMD server $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"
eval "$SCP_CMD frp $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"
eval "$SCP_CMD docker-compose.server.yml $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

# Step 5: 使用 Docker config
echo "5. 切换到 Docker 配置..."
eval "$SSH_CMD 'cd $REMOTE_DIR/server/config && cp config.docker.yaml config.yaml'"

# Step 6: 开放防火墙端口
echo "6. 配置防火墙..."
eval "$SSH_CMD 'sudo ufw allow 7000/tcp || true
sudo ufw allow 8080/tcp || true
sudo ufw allow 9000/tcp || true
sudo ufw allow 9001/tcp || true
sudo ufw allow 18000/tcp || true
echo \"防火墙配置完成\"'"

# Step 7: 启动服务
echo "7. 启动 Docker 服务..."
eval "$SSH_CMD 'cd $REMOTE_DIR && docker compose -f docker-compose.server.yml up -d --build'"

echo ""
echo "=== 部署完成 ==="
echo "Go Server: http://$REMOTE_HOST:8080"
echo "MinIO Console: http://$REMOTE_HOST:9001"
echo "FRP Server: $REMOTE_HOST:7000"
