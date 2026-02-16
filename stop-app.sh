#!/bin/bash

# xMixing Application Stopper
# This script stops all components of the xMixing system using PM2.

echo "🛑 Stopping xMixing Application Suite..."

echo "🛑 Stopping xMixing Application processes..."

pkill -f "mqtt_bridge.py"
pkill -f "python3 main.py"
pkill -f "nuxt"
pkill -f "pm2"

echo "🐳 Stopping Docker Infrastructure..."
cd x09-LocalMqtt
docker-compose stop
cd ..

echo "✅ All services stopped."
