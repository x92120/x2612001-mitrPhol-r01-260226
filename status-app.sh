#!/bin/bash

# xMixing Application Status
# This script shows the status of all components using PM2.

# Check if pm2 is installed
if ! command -v pm2 &> /dev/null
then
    export PATH=$PATH:./node_modules/.bin
fi

pm2 status
