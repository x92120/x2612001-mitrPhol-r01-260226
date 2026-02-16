#!/bin/bash

# xMixing Application Starter
# This script starts all components of the xMixing system using PM2.

echo "🚀 Starting xMixing Application Suite..."

# Start Docker Infrastructure (RabbitMQ, Node-Red)
echo "🐳 Starting Docker Infrastructure..."
cd x09-LocalMqtt
docker-compose up -d
cd ..

# Start MQTT Bridge
echo "🌉 Starting MQTT Bridge..."
/Users/x92120/.xMixing_venv/bin/python3 ./x09-LocalMqtt/x01-ScaleRead/mqtt_bridge.py > bridge.log 2>&1 &

# Start Backend
echo "⚙️ Starting Backend (FastAPI)..."
cd x02-BackEnd/x0201-fastAPI
PORT=8001 /Users/x92120/.xMixing_venv/bin/python3 main.py > ../../backend.log 2>&1 &
cd ../..

# Start Frontend
echo "💻 Starting Frontend (Nuxt)..."
cd x01-FrontEnd/x0101-xMixing_Nuxt
# Note: npm run build should have been run before for production
npm run dev > ../../frontend.log 2>&1 &
cd ../..

echo "✅ All services are being started."
echo "------------------------------------------------"
echo "Backend: http://localhost:8001/docs"
echo "Frontend: http://localhost:3000"
echo "------------------------------------------------"
echo "Use './status-app.sh' to check status"
echo "Use './stop-app.sh' to stop all services"
