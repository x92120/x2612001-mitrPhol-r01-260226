#!/bin/bash

# xMixing Application Stopper
# This script stops all components of the xMixing system using PM2.

echo "🛑 Stopping xMixing Application Suite..."

# Check if pm2 is installed
if ! command -v pm2 &> /dev/null
then
    export PATH=$PATH:./node_modules/.bin
fi

pm2 stop ecosystem.config.js
pm2 delete ecosystem.config.js

echo "🐳 Stopping Docker Infrastructure..."
cd x09-LocalMqtt
docker-compose stop
cd ..

echo "✅ All services stopped (Docker containers stopped but not removed)."
