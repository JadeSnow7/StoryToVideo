# StoryToVideo Windows Deployment Script
# 在 PowerShell 中运行

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    [Parameter(Position=1)]
    [string]$Service = ""
)

# 配置
$PROJECT_DIR = $PSScriptRoot
if (-not $PROJECT_DIR) { $PROJECT_DIR = Get-Location }
$COMPOSE_FILE = "docker-compose.wsl.yml"

function Write-Step {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Check-DockerEnv {
    Write-Step "检查 Docker 环境"
    
    try {
        $null = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
            return $false
        }
        Write-Host "Docker 正在运行" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "Docker 未安装或未运行" -ForegroundColor Red
        return $false
    }
}

function Pull-Model {
    Write-Step "拉取 LLM 模型 (qwen2.5:0.5b)"
    docker compose -f $COMPOSE_FILE up -d ollama
    Start-Sleep -Seconds 5
    docker exec storytovideo-ollama ollama pull qwen2.5:0.5b
    Write-Host "模型拉取完成" -ForegroundColor Green
}

function Start-All {
    Write-Step "启动所有服务"
    docker compose -f $COMPOSE_FILE up -d --build
    Write-Host "服务启动完成" -ForegroundColor Green
    Write-Host "Server:  http://localhost:8080"
    Write-Host "Gateway: http://localhost:8000"
    Write-Host "MinIO:   http://localhost:9001"
}

function Stop-All {
    Write-Step "停止所有服务"
    docker compose -f $COMPOSE_FILE down
    Write-Host "服务已停止" -ForegroundColor Green
}

function Show-Status {
    Write-Step "服务状态"
    docker compose -f $COMPOSE_FILE ps
}

function Show-Logs {
    param([string]$Svc)
    if ($Svc) {
        docker compose -f $COMPOSE_FILE logs -f $Svc
    } else {
        docker compose -f $COMPOSE_FILE logs -f
    }
}

function Health-Check {
    Write-Step "健康检查"
    
    Write-Host -NoNewline "Gateway: "
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "FAIL" -ForegroundColor Red
    }
    
    Write-Host -NoNewline "Server:  "
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8080/v1/api/health" -UseBasicParsing -TimeoutSec 5
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "FAIL" -ForegroundColor Red
    }
}

function Show-Help {
    Write-Host @"

StoryToVideo Docker 部署工具

用法: .\deploy-windows.ps1 <命令>

命令:
  check       - 检查 Docker 环境
  pull-model  - 拉取 Ollama LLM 模型
  start       - 启动所有服务
  stop        - 停止所有服务
  status      - 查看服务状态
  logs [服务] - 查看日志
  health      - 健康检查
  full        - 完整部署流程

"@
}

# 主逻辑
Set-Location $PROJECT_DIR

switch ($Command) {
    "check" { Check-DockerEnv }
    "pull-model" { 
        if (Check-DockerEnv) { Pull-Model }
    }
    "start" { 
        if (Check-DockerEnv) { Start-All }
    }
    "stop" { Stop-All }
    "status" { Show-Status }
    "logs" { Show-Logs $Service }
    "health" { Health-Check }
    "full" {
        if (Check-DockerEnv) {
            Pull-Model
            Start-All
            Write-Host "`n等待服务启动..." -ForegroundColor Yellow
            Start-Sleep -Seconds 30
            Health-Check
        }
    }
    default { Show-Help }
}
