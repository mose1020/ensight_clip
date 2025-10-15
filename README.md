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

- `clip_box.py` - Hauptskript für das Box-Clipping
- `run_clip.sh` - Bash-Wrapper für einfache Ausführung
- `vtu_to_ensight_gold.py` - Optional: Konvertiert VTU zu EnSight Gold ASCII

## Hinweise

- Der Ursprung (0,0,0) ist der Referenzpunkt für alle Box-Definitionen
- Negative Werte (-x) bedeuten Ausdehnung in negative Richtung vom Ursprung
- Positive Werte (+x) bedeuten Ausdehnung in positive Richtung vom Ursprung
- Die Box wird immer als Quader mit parallelen Kanten zu den Koordinatenachsen erstellt

## Lizenz

MIT