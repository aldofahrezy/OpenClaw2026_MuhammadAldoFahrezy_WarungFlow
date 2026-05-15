#!/usr/bin/env bash
# Quick start WarungFlow on this VPS (foreground or background).
set -euo pipefail
cd "$(dirname "$0")/.."
export WARUNGFLOW_ENV="${WARUNGFLOW_ENV:-production}"
export PAYMENT_MODE="${PAYMENT_MODE:-mock}"
export LLM_MODE="${LLM_MODE:-mock}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

PORT="${PORT:-8501}"
if systemctl is-active --quiet warungflow 2>/dev/null; then
  echo "warungflow.service is already running. Use: sudo systemctl status warungflow"
  echo "Live URL: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_VPS_IP'):${PORT}"
  exit 0
fi
if ss -tln | grep -q ":${PORT} "; then
  echo "Port ${PORT} is in use. Stop the other process or use: sudo systemctl restart warungflow"
  exit 1
fi
echo "Starting WarungFlow on 0.0.0.0:${PORT}"
exec .venv/bin/streamlit run app.py \
  --server.port="${PORT}" \
  --server.address=0.0.0.0 \
  --server.headless=true
