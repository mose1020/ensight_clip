#!/bin/bash
# ParaView Clipping Wrapper - Nutzt config.yaml
#
# KONFIGURATION:
# - Bearbeite config.yaml um Einstellungen zu ändern
# - Wähle aktive Config in config.yaml mit "active_config"
# - Setze num_processes in config.yaml für Multi-Core

# ============================================================================
# KONFIGURATION
# ============================================================================
CONFIG_FILE="config.yaml"   # Config-Datei
# ============================================================================

# Fehlerbehandlung
set -e
trap 'echo "❌ Skript wurde abgebrochen!"; exit 1' INT TERM

# Prüfe ob config.yaml existiert
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ ERROR: $CONFIG_FILE nicht gefunden!"
    echo ""
    echo "Bitte erstelle eine config.yaml Datei mit der Konfiguration."
    exit 1
fi

# Lese Konfiguration aus YAML (mit Python)
NUM_PROCESSES=$(python3 -c "import yaml; c=yaml.safe_load(open('$CONFIG_FILE')); print(c.get('num_processes', 4))")
TIMEOUT=$(python3 -c "import yaml; c=yaml.safe_load(open('$CONFIG_FILE')); print(c.get('timeout', 3600))")
ACTIVE_CONFIG=$(python3 -c "import yaml; c=yaml.safe_load(open('$CONFIG_FILE')); print(c.get('active_config', 'flieger'))")
INPUT_FILE=$(python3 -c "import yaml; c=yaml.safe_load(open('$CONFIG_FILE')); ac=c['configs'][c.get('active_config', 'flieger')]; print(ac['input_file'])")
OUTPUT_DIR=$(python3 -c "import yaml; c=yaml.safe_load(open('$CONFIG_FILE')); ac=c['configs'][c.get('active_config', 'flieger')]; print(ac['output_dir'])")
OUTPUT_NAME=$(python3 -c "import yaml; c=yaml.safe_load(open('$CONFIG_FILE')); ac=c['configs'][c.get('active_config', 'flieger')]; print(ac['output_name'])")

# Prüfe ob ParaView installiert ist
if ! command -v pvbatch &> /dev/null; then
    echo "❌ ERROR: pvbatch nicht gefunden!"
    echo ""
    echo "ParaView muss installiert sein. Installation:"
    echo ""
    echo "  Ubuntu/Debian:"
    echo "    sudo apt install paraview"
    echo ""
    echo "  macOS (Homebrew):"
    echo "    brew install --cask paraview"
    echo ""
    echo "  Windows/Manual:"
    echo "    https://www.paraview.org/download/"
    echo ""
    exit 1
fi

# Prüfe ob timeout verfügbar ist
if ! command -v timeout &> /dev/null; then
    echo "⚠️  WARNING: 'timeout' command nicht gefunden - kein Timeout aktiv"
    TIMEOUT_CMD=""
else
    TIMEOUT_CMD="timeout ${TIMEOUT}"
fi

echo "========================================"
echo "🚀 ParaView Parallel Clipping"
echo "========================================"
echo "Config:    $ACTIVE_CONFIG (aus $CONFIG_FILE)"
echo "Input:     $INPUT_FILE"
echo "Output:    $OUTPUT_DIR/$OUTPUT_NAME"
echo "Prozesse:  $NUM_PROCESSES CPU-Kerne"
echo "Timeout:   ${TIMEOUT}s"
echo "========================================"
echo ""

# Prüfe ob Input existiert
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ ERROR: Input-Datei nicht gefunden: $INPUT_FILE"
    exit 1
fi

# Erstelle Output-Verzeichnis
mkdir -p "$OUTPUT_DIR"

# Log-Datei
LOG_FILE="${OUTPUT_DIR}/${OUTPUT_NAME}_log.txt"
echo "📝 Log-Datei: $LOG_FILE"
echo ""

# Starte Clipping
echo "🔪 Starte Clipping..."
echo ""

# Exit code variable
EXIT_CODE=0

# Wähle Ausführungsmodus
if [ "$NUM_PROCESSES" -gt 1 ] && command -v mpirun &> /dev/null; then
    # Parallel mit MPI
    echo "✓ MPI gefunden - nutze $NUM_PROCESSES Prozesse (parallel)"
    set +e
    $TIMEOUT_CMD mpirun --oversubscribe -np $NUM_PROCESSES pvbatch paraview_clip.py \
        --config "$CONFIG_FILE" 2>&1 | grep -v "No BlockID was found" | tee "$LOG_FILE"
    EXIT_CODE=$?
    set -e
else
    # Serial (ohne MPI)
    echo "⚠️  Nutze 1 Prozess (serial)"
    echo ""
    set +e
    $TIMEOUT_CMD pvbatch paraview_clip.py \
        --config "$CONFIG_FILE" 2>&1 | grep -v "No BlockID was found" | tee "$LOG_FILE"
    EXIT_CODE=$?
    set -e
fi

# Prüfe Erfolg
echo ""
if [ $EXIT_CODE -eq 124 ]; then
    echo "========================================"
    echo "⏱️  TIMEOUT nach ${TIMEOUT}s!"
    echo "========================================"
    echo "Das Skript wurde nach ${TIMEOUT}s abgebrochen."
    echo "Erhöhe TIMEOUT oder prüfe Log: $LOG_FILE"
    exit 124
elif [ $EXIT_CODE -eq 0 ]; then
    echo "========================================"
    echo "✅ ERFOLGREICH!"
    echo "========================================"
    echo "Output: $OUTPUT_DIR/$OUTPUT_NAME/"
    if [ -d "$OUTPUT_DIR/$OUTPUT_NAME/" ]; then
        ls -lh "$OUTPUT_DIR/$OUTPUT_NAME/"
    else
        echo "⚠️  Output-Verzeichnis wurde nicht erstellt"
        echo "Prüfe Log: $LOG_FILE"
    fi
else
    echo "========================================"
    echo "❌ FEHLER beim Clipping (Exit Code: $EXIT_CODE)"
    echo "========================================"
    echo "Prüfe Log: $LOG_FILE"
    exit $EXIT_CODE
fi
