#!/bin/bash
# run_clip_background.sh - Startet clip_box.py im Hintergrund
# Verwendung: ./run_clip_background.sh [Parameter für clip_box.py]
# Beispiel: ./run_clip_background.sh --xmin=-10 --xmax=10

PID_FILE="clip_box.pid"

# Prüfe ob bereits ein Prozess läuft
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "WARNUNG: Prozess läuft bereits (PID: $OLD_PID)"
        echo "Stoppe zuerst mit: ./stop_clip.sh"
        exit 1
    else
        # Alte PID-Datei entfernen
        rm "$PID_FILE"
    fi
fi

echo "Starte clip_box.py im Hintergrund..."
echo "Logs werden geschrieben nach: logs/clip_box_*.log"

# Starte pvbatch im Hintergrund
# Output wird nach /dev/null umgeleitet da logging in Datei erfolgt
nohup pvbatch clip_box.py "$@" > /dev/null 2>&1 &
PID=$!

# Speichere PID
echo $PID > "$PID_FILE"

echo "✓ Prozess gestartet (PID: $PID)"
echo ""
echo "Status prüfen mit: ./check_clip_status.sh"
echo "Logs ansehen mit:  tail -f logs/clip_box_*.log"
