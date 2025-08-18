#!/bin/bash

# Find the PID of the UVicorn process running on port 8000
PID=$(sudo lsof -t -i:8000)

if [ -n "$PID" ]; then
    # Kill the UVicorn process using the PID
    sudo kill -9 $PID
    echo "Stopped UVicorn process with PID: $PID"
else
    echo "No UVicorn process found running on port 8000"
fi

source venv/bin/activate
# Start UVicorn in background mode
nohup uvicorn main:app --reload > uvicorn.log 2>&1 &
echo "Started UVicorn in background."
#dont use this