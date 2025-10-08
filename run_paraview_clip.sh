#!/bin/bash
# ParaView Clipping Wrapper - Vereinfacht die Nutzung

# Konfiguration
INPUT_FILE="input/Kanalströmung/Kanalstroemung.encas"
OUTPUT_DIR="output"
OUTPUT_NAME="Kanalstroemung_clipped_paraview"
NUM_PROCESSES=1  # Anzahl CPU-Kerne für parallele Verarbeitung

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

echo "========================================"
echo "🚀 ParaView Parallel Clipping"
echo "========================================"
echo "Input:     $INPUT_FILE"
echo "Output:    $OUTPUT_DIR/$OUTPUT_NAME"
echo "Prozesse:  $NUM_PROCESSES"
echo "========================================"
echo ""

# Prüfe ob Input existiert
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ ERROR: Input-Datei nicht gefunden: $INPUT_FILE"
    exit 1
fi

# Erstelle Output-Verzeichnis
mkdir -p "$OUTPUT_DIR"

# Starte Clipping
echo "🔪 Starte Clipping..."
echo ""

# Wähle Ausführungsmodus
if [ "$NUM_PROCESSES" -gt 1 ] && command -v mpirun &> /dev/null; then
    # Parallel mit MPI
    echo "✓ MPI gefunden - nutze $NUM_PROCESSES Prozesse (parallel)"
    mpirun --oversubscribe -np $NUM_PROCESSES pvbatch paraview_clip.py \
        --input "$INPUT_FILE" \
        --output "$OUTPUT_DIR" \
        --name "$OUTPUT_NAME" \
        --type plane \
        --origin "0,0,0" \
        --normal "1,0,0"
else
    # Serial (ohne MPI)
    echo "⚠️  Nutze 1 Prozess (serial)"
    echo ""
    pvbatch paraview_clip.py \
        --input "$INPUT_FILE" \
        --output "$OUTPUT_DIR" \
        --name "$OUTPUT_NAME" \
        --type plane \
        --origin "0,0,0" \
        --normal "1,0,0"
fi

# Prüfe Erfolg
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✅ ERFOLGREICH!"
    echo "========================================"
    echo "Output: $OUTPUT_DIR/$OUTPUT_NAME/"
    ls -lh "$OUTPUT_DIR/$OUTPUT_NAME/"
else
    echo ""
    echo "❌ FEHLER beim Clipping!"
    exit 1
fi
