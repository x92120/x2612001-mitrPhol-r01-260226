#!/bin/bash

# xMixing Application Status
# This script shows the status of all components using PM2.

echo "📊 xMixing Application Status:"
echo "------------------------------------------------"

# Check MQTT Bridge
if ps aux | grep -v grep | grep -q "mqtt_bridge.py"; then
    echo "🟢 MQTT Bridge: RUNNING"
else
    echo "🔴 MQTT Bridge: STOPPED"
fi

# Check Backend
if lsof -i :8001 > /dev/null; then
    echo "🟢 Backend (Port 8001): RUNNING"
else
    echo "🔴 Backend (Port 8001): STOPPED"
fi

# Check Frontend
if lsof -i :3000 > /dev/null; then
    echo "🟢 Frontend (Port 3000): RUNNING"
else
    echo "🔴 Frontend (Port 3000): STOPPED"
fi

# Check Docker
echo "------------------------------------------------"
echo "🐳 Docker Infrastructure:"
cd x09-LocalMqtt && docker-compose ps && cd ..
echo "------------------------------------------------"
