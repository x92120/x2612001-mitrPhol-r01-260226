#!/bin/bash

# xMixing Application Starter
# This script starts all components of the xMixing system using PM2.

echo "🚀 Starting xMixing Application Suite..."

# Check if pm2 is installed
if ! command -v pm2 &> /dev/null
then
    echo "PM2 not found. Installing locally..."
    npm install pm2
    export PATH=$PATH:./node_modules/.bin
fi

# Start Docker Infrastructure (RabbitMQ, Node-Red)
echo "🐳 Starting Docker Infrastructure..."
cd x09-LocalMqtt
docker-compose up -d
cd ..

# Start the application using ecosystem config in production mode
pm2 start ecosystem.config.js --env production

echo "✅ All services are being started."
echo "------------------------------------------------"
pm2 status
echo "------------------------------------------------"
echo "Use './status-app.sh' to check status"
echo "Use './stop-app.sh' to stop all services"
