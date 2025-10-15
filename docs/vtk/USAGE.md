# EnSight Clipper - Verwendung

## Überblick

Werkzeug zum Clippen von EnSight-Dateien mit Fortschrittsanzeige und Speicheroptimierung.

## Wichtige Dateien

- **ensight_clip.py** - Hauptmodul mit allen Features
- **ensight_clip_gui.py** - Grafische Oberfläche (PyQt5)
- **test_flieger.py** - Test-Skript für Flieger-Datensatz

## Features

✅ **Fortschrittsanzeige** mit Zeitschätzung und Speicherverbrauch
✅ **Speicheroptimierung** für große Datensätze (automatische Vorfilterung)
✅ **Drei Clipping-Modi**: Box, Ebene, Kugel
✅ **Automatische XML-Metadaten** Erstellung

## Verwendung

### Als Python-Modul:

```python
from ensight_clip import EnSightClipper

# Clipper erstellen
clipper = EnSightClipper("input/data.case")

# Daten einlesen
clipper.read_ensight()
bounds = clipper.get_bounds()

# Box-Clipping (speicheroptimiert)
box_bounds = [-1, 1, -1, 1, -1, 1]
clipper.clip_with_box(box_bounds, use_prefilter=True)

# Ausgabe schreiben
clipper.write_ensight("output", "clipped_data")
```

### Als Kommandozeilen-Tool:

```bash
# Flieger-Datensatz clippen
python3 test_flieger.py

# Kanalströmung clippen
python3 ensight_clip.py
```

### Mit GUI:

```bash
python3 ensight_clip_gui.py
```

## Parameter

### `clip_with_box(bounds, use_prefilter=True)`
- **bounds**: `[xmin, xmax, ymin, ymax, zmin, zmax]`
- **use_prefilter**: Bei `True` wird Speicher durch Vorfilterung gespart (empfohlen für große Datensätze)

### `clip_with_plane(origin, normal, invert=False)`
- **origin**: Punkt auf der Ebene `[x, y, z]`
- **normal**: Normalenvektor `[nx, ny, nz]`
- **invert**: Kehrt Clipping-Richtung um

### `clip_with_sphere(center, radius)`
- **center**: Kugelmittelpunkt `[x, y, z]`
- **radius**: Kugelradius

## Tipps

### Bei Speicherproblemen:
- Verwende `use_prefilter=True` (Standard)
- Schließe andere Programme
- Verwende kleinere Clipping-Region
- Nutze Rechner mit mehr RAM

### Für beste Performance:
- `use_prefilter=False` bei ausreichend RAM (>16 GB)
- `use_prefilter=True` bei begrenztem RAM (<8 GB)

## Output

Das Tool erstellt:
- `.encas` - EnSight Case-Datei
- `.geo` - Geometrie
- Variablen-Dateien (Druck, Geschwindigkeit, etc.)
- `.xml` - Metadaten mit Units
