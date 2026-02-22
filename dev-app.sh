#!/bin/bash

# xMixing Development Starter
# This script starts all components in development mode and shows logs.

echo "🚀 Starting xMixing in DEVELOPMENT mode..."

# Start MQTT Bridge (Separated)
echo "🌉 Starting Scale and Scanner Readers..."
source ./x02-BackEnd/.venv/bin/activate
python3 -u ./x09-LocalMqtt/x01-EquipmentRead/scale_read.py > bridge.log 2>&1 &
python3 -u ./x09-LocalMqtt/x01-EquipmentRead/scanner_read.py >> bridge.log 2>&1 &

# Start Backend
echo "⚙️ Starting Backend (FastAPI)..."
cd x02-BackEnd/x0201-fastAPI
PORT=8001 python3 main.py > ../../backend.log 2>&1 &
cd ../..

# Start Frontend
echo "💻 Starting Frontend (Nuxt)..."
cd x01-FrontEnd/x0101-xMixing_Nuxt
npm run dev > ../../frontend.log 2>&1 &
cd ../..

echo "✅ All services started in dev mode."
echo "------------------------------------------------"
echo "Backend: http://localhost:8001/docs"
echo "Frontend: http://localhost:3000"
echo "------------------------------------------------"
echo "Use './status-app.sh' to check status"
echo "Use './stop-app.sh' to stop all services"
echo "------------------------------------------------"
echo "👀 To see logs, run: tail -f backend.log frontend.log bridge.log"
