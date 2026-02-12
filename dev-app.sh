#!/bin/bash

# xMixing Development Starter
# This script starts all components in development mode and shows logs.

echo "🚀 Starting xMixing in DEVELOPMENT mode..."

# Check if pm2 is installed
if ! command -v pm2 &> /dev/null
then
    export PATH=$PATH:./node_modules/.bin
fi

# Start Docker Infrastructure (RabbitMQ, Node-Red)
echo "🐳 Starting Docker Infrastructure..."
cd x09-LocalMqtt
docker-compose up -d
cd ..

# Start the application in development mode (with watch enabled for bridge)
pm2 start ecosystem.config.js --env development

echo "✅ All services started in dev mode."
echo "👀 Streaming logs... (Press Ctrl+C to stop streaming, services will continue running)"
pm2 logs
