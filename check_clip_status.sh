#!/bin/bash
# check_clip_status.sh - Zeigt Status des Clipping-Prozesses

PID_FILE="clip_box.pid"

echo "========================================"
echo "Clipping Status"
echo "========================================"

if [ ! -f "$PID_FILE" ]; then
    echo "Status: Kein Prozess läuft"
    echo ""
    echo "Starten mit: ./run_clip_background.sh"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Status: ✓ Läuft (PID: $PID)"
    echo ""

    # Finde das neueste Log
    LATEST_LOG=$(ls -t logs/clip_box_*.log 2>/dev/null | head -1)

    if [ -n "$LATEST_LOG" ]; then
        echo "Letztes Log: $LATEST_LOG"
        echo ""
        echo "Letzte 10 Zeilen:"
        echo "----------------------------------------"
        tail -10 "$LATEST_LOG"
        echo "----------------------------------------"
        echo ""
        echo "Vollständiges Log: tail -f $LATEST_LOG"
    fi

    # Zeige Ressourcen-Nutzung
    echo ""
    echo "Ressourcen:"
    ps -p "$PID" -o pid,pcpu,pmem,etime,cmd
else
    echo "Status: ✗ Prozess $PID läuft nicht mehr"
    rm "$PID_FILE"

    # Zeige letztes Log
    LATEST_LOG=$(ls -t logs/clip_box_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo ""
        echo "Letztes Log: $LATEST_LOG"
        echo "Letzte 20 Zeilen:"
        echo "----------------------------------------"
        tail -20 "$LATEST_LOG"
    fi
fi

echo "========================================"
