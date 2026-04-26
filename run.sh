#!/usr/bin/env bash
set -e

DB="${1:-databases/agentcy.db}"
ROLES="${2:-roles.json}"
PORT="${3:-9001}"

cd "$(dirname "$0")"

if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

export AGENTCY_LOGS_DIR="${AGENTCY_LOGS_DIR:-$(pwd)/agent_logs}"
mkdir -p "$AGENTCY_LOGS_DIR"

echo "Starting Agentcy at http://localhost:${PORT}"
exec "$PYTHON" main.py ui "$DB" "$ROLES" "$PORT"
