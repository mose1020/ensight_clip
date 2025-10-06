# EnSight Clipper - Interactive 3D Clipping Tool

Interaktives Python-Tool zum Zuschneiden von EnSight-Dateien mit 3D-Vorschau.

## Features

- ✅ **Interaktive 3D-Visualisierung** mit VTK
- ✅ **Echtzeit-Vorschau** des zugeschnittenen Bereichs
- ✅ **3 Clip-Typen**: Ebene, Quader, Kugel
- ✅ **Variable Visualisierung**: Einfärbung nach Druck, Geschwindigkeit, etc.
- ✅ **Export**: Speichert .encas + .xml + alle Strömungsgrößen

## Installation

```bash
# Virtual Environment erstellen (falls noch nicht vorhanden)
python3 -m venv .venv

# Aktivieren
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

## Verwendung

### GUI Version (Empfohlen)

```bash
source .venv/bin/activate
python ensight_clip_gui.py
```

**GUI Bedienung:**

1. **Datei laden**:
   - Klick auf "Load EnSight File" oder
   - Die Kanalströmung wird automatisch geladen

2. **Clip-Typ wählen**:
   - **Plane**: Schnitt mit einer Ebene
     - Origin: Position der Ebene im Raum
     - Normal: Richtungsvektor der Ebene
     - Preset-Buttons: X, Y, Z für Standard-Achsen
     - Invert: Andere Seite behalten

   - **Box**: Schnitt mit einem Quader
     - X, Y, Z Min/Max: Begrenzungen des Quaders

   - **Sphere**: Schnitt mit einer Kugel
     - Center: Mittelpunkt der Kugel
     - Radius: Kugelradius

3. **Visualisierung**:
   - "Show Original": Original-Geometrie als Wireframe
   - "Show Clipped": Zugeschnittener Bereich (solid)
   - "Color by Variable": Einfärbung nach Strömungsgröße

4. **Speichern**:
   - "Save Clipped Data" → Ausgabeverzeichnis wählen
   - Basisname eingeben
   - Alle Dateien werden gespeichert (.encas, .xml, .geo, .scl*, .vel)

**Maus-Navigation:**
- **Drehen**: Linke Maustaste + Ziehen
- **Verschieben**: Mittlere Maustaste + Ziehen
- **Zoom**: Mausrad oder Rechte Maustaste + Ziehen
- **Reset View**: Button "Reset View"

### CLI Version

```bash
source .venv/bin/activate
python ensight_clip.py
```

Die CLI-Version nutzt vordefinierte Parameter aus dem Code (Zeilen 217-234).

## Projekt-Struktur

```
ensight_clip/
├── input/
│   └── Kanalströmung/
│       ├── Kanalstroemung.encas    # Input Case-Datei
│       ├── Kanalstroemung.geo      # Geometrie
│       ├── Kanalstroemung.scl*     # Skalare Größen
│       ├── Kanalstroemung.vel      # Geschwindigkeit
│       └── Kanalstroemung.xml      # Metadata
├── output/                          # Ausgabeverzeichnis
│   └── Kanalstroemung_clipped/     # Unterordner für jeden Clip
│       ├── Kanalstroemung_clipped.encas
│       ├── Kanalstroemung_clipped.xml
│       ├── Kanalstroemung_clipped.0.00000.geo
│       └── Kanalstroemung_clipped.0.00000_n.*
├── .venv/                          # Virtual Environment
├── ensight_clip_gui.py             # GUI Version ⭐
├── ensight_clip.py                 # CLI Version
├── ensight_clip_gui.spec           # PyInstaller Konfiguration
├── requirements.txt                # Python-Abhängigkeiten
├── BUILD_WINDOWS_EXE.md            # Anleitung für Windows .exe
└── README.md                       # Diese Datei
```

## Windows .exe erstellen

Siehe [BUILD_WINDOWS_EXE.md](BUILD_WINDOWS_EXE.md) für eine detaillierte Anleitung zum Erstellen einer ausführbaren Windows .exe-Datei.

## Abhängigkeiten

- **numpy** ≥ 1.21.0 - Numerische Berechnungen
- **vtk** ≥ 9.2.0 - 3D-Visualisierung und EnSight I/O
- **PyQt5** ≥ 5.15.0 - GUI Framework
- **pyinstaller** ≥ 6.0.0 - Executable Builder (optional)

## Beispiel-Workflow

1. GUI starten: `python ensight_clip_gui.py`
2. Kanalströmung wird automatisch geladen
3. Clip-Typ "Plane" wählen
4. Normal auf Z-Achse setzen (Button "Z")
5. Origin Z-Wert anpassen (z.B. 0.5 für Mitte)
6. In 3D-View das Ergebnis begutachten
7. Optional: "Color by Variable" → "velocity" wählen
8. "Save Clipped Data" klicken
9. Ausgabeverzeichnis wählen (z.B. `output/`)
10. Basisname eingeben (z.B. `Kanalstroemung_clipped`)
11. Die Dateien werden in einem Unterordner gespeichert: `output/Kanalstroemung_clipped/`

## Tipps

- **Plane Clipping**: Am besten für 2D-Schnitte durch das Modell
- **Box Clipping**: Ideal zum Extrahieren eines rechteckigen Bereichs
- **Sphere Clipping**: Gut für radiale Bereiche um einen Punkt

- Die Vorschau zeigt:
  - **Grau (Wireframe)**: Original-Geometrie
  - **Rot (Solid)**: Zugeschnittener Bereich

- Alle Strömungsgrößen (pressure, velocity, turbulence) werden automatisch mitgeschnitten

## Troubleshooting

**GUI startet nicht:**
```bash
# PyQt5 neu installieren
pip install --force-reinstall PyQt5
```

**"No display" Fehler:**
```bash
# X11 Display für WSL einrichten oder
# Auf Windows/Mac GUI ausführen
```

**Datei nicht gefunden:**
- Sicherstellen, dass `input/Kanalströmung/Kanalstroemung.encas` existiert
- Oder über "Load EnSight File" manuell laden

## Autor

Erstellt mit Claude Code
