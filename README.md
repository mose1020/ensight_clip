# EnSight Box Clipper

Ein einfaches Tool zum Ausschneiden von Boxen aus EnSight-Datensätzen mit ParaView.

## Installation

### Voraussetzungen

- ParaView (mit pvbatch)
- Python 3.x
- VTK Python-Bindings (normalerweise mit ParaView installiert)

### Setup

```bash
# Repository klonen
git clone <repository-url>
cd ensight_clip

# Skripte ausführbar machen
chmod +x clip_box.py run_clip.sh
```

## Verwendung

Das Tool verwendet den **globalen Ursprung (0,0,0)** als Referenzpunkt. Sie können die Box-Grenzen in positive (+) und negative (-) Richtung vom Ursprung aus definieren.

### Einfache Verwendung

```bash
# Standard 10m × 10m × 10m Box (±5m in alle Richtungen)
./run_clip.sh

# Oder direkt mit pvbatch
pvbatch clip_box.py
```

### Box-Grenzen anpassen

Sie können die Box-Grenzen mit den Argumenten `--xmin`, `--xmax`, `--ymin`, `--ymax`, `--zmin`, `--zmax` festlegen:

```bash
# Box von -2m bis +5m in X-Richtung
./run_clip.sh --xmin -2 --xmax 5

# Große Box: 20m × 20m × 10m
./run_clip.sh --xmin -10 --xmax 10 --ymin -10 --ymax 10 --zmin -5 --zmax 5

# Asymmetrische Box
./run_clip.sh --xmin -3 --xmax 7 --ymin -2 --ymax 2 --zmin -1 --zmax 4
```

### Weitere Optionen

```bash
# Hilfe anzeigen
./run_clip.sh --help

# Mit EnSight Gold Export
./run_clip.sh --export-ensight

# Andere Input-Datei verwenden
./run_clip.sh -i input/other_dataset.case
```

## Ausgabe

Die geclippten Daten werden im `output/` Verzeichnis gespeichert:
- VTU-Format (immer)
- EnSight Gold Format (optional mit `--export-ensight`)

Dateiname: `box_[Breite]x[Höhe]x[Tiefe]m_[Zeitstempel]/`

## Beispiele

### Kleine Box um den Ursprung
```bash
./run_clip.sh --xmin -1 --xmax 1 --ymin -1 --ymax 1 --zmin -1 --zmax 1
```
Erstellt eine 2m × 2m × 2m Box.

### Box in positive X-Richtung
```bash
./run_clip.sh --xmin 0 --xmax 10
```
Box von 0 bis 10m in X, Standard (±5m) in Y und Z.

### Box in negative X-Richtung
```bash
./run_clip.sh --xmin -10 --xmax 0
```
Box von -10 bis 0m in X, Standard (±5m) in Y und Z.

## Dateien

- `clip_box.py` - Hauptskript für das Box-Clipping (optimiert)
- `clip_box_lowmem.py` - Low-Memory Version für sehr große Boxen
- `run_clip.sh` - Bash-Wrapper für einfache Ausführung
- `run_clip_background.sh` - Führt Clipping im Hintergrund aus
- `check_clip_status.sh` - Prüft Status des Hintergrund-Prozesses
- `stop_clip.sh` - Stoppt laufenden Hintergrund-Prozess

## Speicher-Optimierung (WICHTIG für große Boxen!)

Bei großen Boxen (>10m³) kann der Arbeitsspeicher überlaufen. Hier sind Lösungen:

### Optimierte Version (Standard)
Die Standard-Version `clip_box.py` wurde optimiert:
- Kein `Tetrahedralize` mehr (spart ~30-50% RAM)
- VTU-Export übersprungen (nur EnSight wird gespeichert)
- Explizites Cleanup der Pipeline-Objekte

```bash
# Normale Verwendung mit Optimierungen
pvbatch clip_box.py --xmin=-10 --xmax=5 --ymin=-10 --ymax=10 --zmin=-5 --zmax=5
```

### Low-Memory Version (für extreme Fälle)
Für sehr große Boxen (15×20×10m oder größer):

```bash
# Verwendet clip_box_lowmem.py
pvbatch clip_box_lowmem.py --xmin=-10 --xmax=5 --ymin=-10 --ymax=10 --zmin=-5 --zmax=5
```

**Unterschiede:**
- `Crinkleclip=0` (exaktere aber weniger speicherintensive Clipping-Methode)
- Sofortiges Löschen von Zwischenergebnissen
- Python Garbage Collection nach jedem Schritt
- NUR EnSight-Export (kein VTU)

### WSL Memory Limit erhöhen

Falls trotzdem nicht genug RAM:

1. Erstelle/Editiere `%USERPROFILE%\.wslconfig` (auf Windows):
```ini
[wsl2]
memory=96GB
swap=32GB
processors=16
```

2. WSL neustarten:
```bash
wsl --shutdown
```

### Weitere Tipps

- **Monitoring**: Speicherverbrauch überwachen mit `htop` oder `free -h`
- **Chunking**: Große Box in mehrere kleinere Boxen aufteilen
- **Server-Version**: Auf Server mit mehr RAM ausführen

## Hinweise

- Der Ursprung (0,0,0) ist der Referenzpunkt für alle Box-Definitionen
- Negative Werte (-x) bedeuten Ausdehnung in negative Richtung vom Ursprung
- Positive Werte (+x) bedeuten Ausdehnung in positive Richtung vom Ursprung
- Die Box wird immer als Quader mit parallelen Kanten zu den Koordinatenachsen erstellt

## Lizenz

MIT