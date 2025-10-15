#!/bin/bash
#
# EnSight Box Clipper - Ausführungsskript
#
# Verwendung:
#   ./run_clip.sh                              # Standard 10x10x10m Box
#   ./run_clip.sh --xmin -2 --xmax 5          # Eigene X-Grenzen
#   ./run_clip.sh --help                       # Hilfe anzeigen
#

# Prüfe ob pvbatch verfügbar ist
if ! command -v pvbatch &> /dev/null; then
    echo "FEHLER: pvbatch nicht gefunden!"
    echo "Bitte ParaView installieren oder Pfad setzen."
    exit 1
fi

# Führe clip_box.py mit allen übergebenen Argumenten aus
pvbatch clip_box.py "$@"