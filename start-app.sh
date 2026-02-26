#!/bin/bash

# xMixing Application Starter
# This script starts all components of the xMixing system using PM2.

echo "🚀 Starting xMixing Application Suite..."

# Start Docker Infrastructure (RabbitMQ, Node-Red)
echo "🐳 Starting Docker Infrastructure..."
cd x09-LocalMqtt
docker compose up -d
cd ..

# Start MQTT Bridge (Separated)
echo "🌉 Starting Scale and Scanner Readers..."
source ./x02-BackEnd/.venv/bin/activate
python3 -u ./x09-LocalMqtt/x01-EquipmentRead/scale_read.py > bridge.log 2>&1 &
python3 -u ./x09-LocalMqtt/x01-EquipmentRead/scanner_read.py >> bridge.log 2>&1 &

# Start Backend
echo "⚙️ Starting Backend (FastAPI)..."
cd x02-BackEnd/x0201-fastAPI
# Using python3 -m uvicorn is often safer but main.py has the run block.
# Let's stick to the pattern but use direct python3
PORT=8001 python3 main.py > ../../backend.log 2>&1 &
cd ../..

# Start Frontend
echo "💻 Starting Frontend (Nuxt)..."
cd x01-FrontEnd/x0101-xMixing_Nuxt
# Note: npm run build should have been run before for production
npm run dev -- --host 0.0.0.0 > ../../frontend.log 2>&1 &
cd ../..

echo "✅ All services are being started."
echo "------------------------------------------------"
echo "Backend: http://localhost:8001/docs"
echo "Frontend: http://localhost:3000"
echo "------------------------------------------------"
echo "Use './status-app.sh' to check status"
echo "Use 'pkill -f python3' and 'pkill -f nuxt' to stop (or update stop-app.sh)"
