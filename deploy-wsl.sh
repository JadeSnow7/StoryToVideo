#!/bin/bash
# StoryToVideo WSL2 Docker Deployment Script
# Usage: ./deploy-wsl.sh [start|stop|logs|status|pull-model]

set -e

COMPOSE_FILE="docker-compose.wsl.yml"
PROJECT_NAME="storytovideo"

case "$1" in
    start)
        echo "🚀 Starting StoryToVideo services..."
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d --build
        echo "✅ Services started!"
        echo ""
        echo "Endpoints:"
        echo "  - Server:  http://localhost:8080"
        echo "  - Gateway: http://localhost:8000"
        echo "  - MinIO:   http://localhost:9001 (console)"
        ;;
    
    stop)
        echo "🛑 Stopping StoryToVideo services..."
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down
        echo "✅ Services stopped!"
        ;;
    
    logs)
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f ${2:-}
        ;;
    
    status)
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
        ;;
    
    pull-model)
        echo "📥 Pulling LLM model (qwen2.5:0.5b)..."
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d ollama
        sleep 5
        docker exec -it storytovideo-ollama ollama pull qwen2.5:0.5b
        echo "✅ Model pulled successfully!"
        ;;
    
    health)
        echo "🏥 Health Check..."
        echo -n "Gateway: "
        curl -s http://localhost:8000/health || echo "❌ Not responding"
        echo ""
        echo -n "Server:  "
        curl -s http://localhost:8080/v1/api/health || echo "❌ Not responding"
        echo ""
        ;;
    
    *)
        echo "Usage: $0 {start|stop|logs|status|pull-model|health}"
        echo ""
        echo "Commands:"
        echo "  start       - Start all services"
        echo "  stop        - Stop all services"
        echo "  logs [svc]  - View logs (optional: specify service)"
        echo "  status      - Show service status"
        echo "  pull-model  - Pull Ollama LLM model"
        echo "  health      - Check service health"
        exit 1
        ;;
esac
