#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PROJECT_NAME="${PROJECT_NAME:-storytovideo}"

usage() {
  cat <<EOF
Usage: $0 {up|down|restart|ps|logs|health}

Environment:
  COMPOSE_FILE   Compose file path (default: docker-compose.yml)
  PROJECT_NAME   Compose project name (default: storytovideo)

Notes:
  - This deployment assumes Ollama runs on the host (not in Docker).
  - Set OLLAMA_HOST in your .env if needed (default: http://host.docker.internal:11434).
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd docker

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin not found. Install docker-compose-plugin." >&2
  exit 1
fi

case "${1:-}" in
  up)
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d --build
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    ;;
  down)
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    ;;
  restart)
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d --build
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    ;;
  ps)
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    ;;
  logs)
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f "${2:-}"
    ;;
  health)
    echo -n "Gateway: "
    curl -fsS --max-time 3 http://127.0.0.1:8000/health >/dev/null && echo "ok" || echo "fail"
    echo -n "Server:  "
    curl -fsS --max-time 3 http://127.0.0.1:8080/v1/api/health >/dev/null && echo "ok" || echo "fail"
    ;;
  *)
    usage
    exit 1
    ;;
esac
