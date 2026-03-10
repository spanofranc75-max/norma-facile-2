#!/bin/bash
set -e

echo "=== Installing frontend dependencies ==="
cd /app/frontend
npm install
npm run build

echo "=== Starting backend ==="
cd /app/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
