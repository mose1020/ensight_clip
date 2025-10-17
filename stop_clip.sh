#!/bin/bash
# stop_clip.sh - Stoppt den laufenden clip_box.py Prozess

PID_FILE="clip_box.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Kein laufender Prozess gefunden (keine $PID_FILE)"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stoppe Prozess $PID..."
    kill "$PID"

    # Warte auf Beendigung
    sleep 2

    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Prozess reagiert nicht, erzwinge Beendigung..."
        kill -9 "$PID"
    fi

    echo "✓ Prozess gestoppt"
    rm "$PID_FILE"
else
    echo "Prozess $PID läuft nicht mehr"
    rm "$PID_FILE"
fi
