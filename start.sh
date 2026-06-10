#!/bin/sh
# Start FastAPI backend on port 8000 (internal)
uvicorn src.app:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready before starting frontend
echo "Waiting for backend..."
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "Backend ready!"
    break
  fi
  sleep 1
done

# Start Next.js frontend on PORT (Cloud Run's port, default 8080)
cd frontend
API_URL=http://localhost:8000 PORT=${PORT:-8080} HOSTNAME=0.0.0.0 node server.js
