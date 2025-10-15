# Windows .exe Erstellen - Anleitung

Diese Anleitung erklärt, wie Sie aus der EnSight Clipper GUI eine ausführbare Windows .exe-Datei erstellen.

## Voraussetzungen

- **Windows 10/11** (64-bit)
- **Python 3.10 oder höher** (empfohlen: Python 3.12)
  - Download: https://www.python.org/downloads/
  - ⚠️ Bei der Installation: "Add Python to PATH" aktivieren!

## Schritt-für-Schritt Anleitung

### 1. Python Installation prüfen

Öffnen Sie die **Eingabeaufforderung** (Command Prompt) oder **PowerShell** und prüfen Sie:

```powershell
python --version
```

Sollte `Python 3.10.x` oder höher anzeigen.

### 2. Projekt vorbereiten

Kopieren Sie das gesamte `ensight_clip` Verzeichnis auf Ihren Windows-Rechner.

Navigieren Sie im Terminal zum Projektordner:

```powershell
cd C:\Pfad\zum\ensight_clip
```

### 3. Virtual Environment erstellen

```powershell
# Virtual Environment erstellen
python -m venv .venv

# Virtual Environment aktivieren
.venv\Scripts\activate
```

Nach der Aktivierung sollte `(.venv)` vor Ihrer Eingabeaufforderung stehen.

### 4. Abhängigkeiten installieren

```powershell
# Alle Pakete installieren (inkl. PyInstaller)
pip install -r requirements.txt
```

Dies installiert:
- numpy
- vtk
- PyQt5
- pyinstaller

Die Installation kann 5-10 Minuten dauern (VTK ist groß).

### 5. Ausführbare Datei erstellen

```powershell
# .exe mit PyInstaller bauen
pyinstaller ensight_clip_gui.spec
```

Der Build-Prozess dauert 2-5 Minuten und zeigt viele INFO-Meldungen.

### 6. Ergebnis prüfen

Nach erfolgreichem Build finden Sie die .exe hier:

```
dist/
└── EnSight_Clipper/
    ├── EnSight_Clipper.exe     ← Die ausführbare Datei
    ├── input/                   ← Beispieldaten
    │   └── Kanalströmung/
    └── [viele DLL-Dateien]      ← Abhängigkeiten
```

### 7. Anwendung testen

```powershell
# Testen Sie die .exe
dist\EnSight_Clipper\EnSight_Clipper.exe
```

Die GUI sollte sich öffnen und die Kanalströmung automatisch laden.

## Distribution

Um die Anwendung zu verteilen:

1. **Den gesamten Ordner** `dist/EnSight_Clipper/` kopieren
2. Auf anderen Windows-Rechnern: `EnSight_Clipper.exe` ausführen
3. ⚠️ **NICHT** nur die .exe-Datei kopieren - alle DLL-Dateien werden benötigt!

### Optional: ZIP-Archiv erstellen

```powershell
# Komprimieren für einfache Verteilung
Compress-Archive -Path dist\EnSight_Clipper -DestinationPath EnSight_Clipper_Windows.zip
```

## Troubleshooting

### Problem: "python" wird nicht erkannt

**Lösung:** Python wurde nicht zum PATH hinzugefügt.

Optionen:
1. Python neu installieren mit "Add to PATH" aktiviert
2. Oder vollständigen Pfad verwenden: `C:\Python312\python.exe`

### Problem: pip install schlägt fehl

**Lösung:** pip aktualisieren

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Problem: PyInstaller erstellt keine .exe

**Lösung:** PyInstaller manuell installieren

```powershell
pip install --upgrade pyinstaller
pyinstaller ensight_clip_gui.spec
```

### Problem: .exe startet nicht / Schwarzes Fenster blinkt kurz

**Lösung:** Von Eingabeaufforderung aus starten, um Fehler zu sehen:

```powershell
cd dist\EnSight_Clipper
.\EnSight_Clipper.exe
```

Fehlermeldungen erscheinen dann im Terminal.

### Problem: "VCRUNTIME140.dll fehlt"

**Lösung:** Microsoft Visual C++ Redistributable installieren

Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

## Build-Optionen anpassen

Die Datei `ensight_clip_gui.spec` enthält die Build-Konfiguration:

- **Icon hinzufügen:** Zeile 47 ändern: `icon='pfad/zum/icon.ico'`
- **Console-Fenster anzeigen:** Zeile 41 ändern: `console=True` (für Debugging)
- **Mehr Daten einbetten:** Zeile 9-11 erweitern

Nach Änderungen erneut bauen:

```powershell
pyinstaller ensight_clip_gui.spec
```

## Bekannte Limitierungen

- ⚠️ Die .exe funktioniert **nur auf Windows**
- Die Dateigröße ist groß (~200-300 MB) wegen VTK-Bibliotheken
- Der erste Start kann 5-10 Sekunden dauern
- Antivirus-Software könnte Warnung zeigen (False Positive)

## Alternative: One-File Build

Für eine einzelne .exe-Datei (ohne DLL-Ordner), ändern Sie in `ensight_clip_gui.spec`:

Zeile 31-35 ersetzen:

```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # ← Hinzufügen
    a.zipfiles,      # ← Hinzufügen
    a.datas,         # ← Hinzufügen
    [],
    name='EnSight_Clipper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
```

Und **entfernen** Sie den `COLLECT` Block (Zeilen 50-59).

⚠️ **Nachteil:** Längere Startzeit (5-15 Sekunden), da alles entpackt werden muss.

## Support

Bei Problemen:
- Prüfen Sie die Python-Version: `python --version`
- Prüfen Sie die PyInstaller-Version: `pyinstaller --version`
- Erstellen Sie ein Issue im GitHub Repository

---

**Hinweis:** Diese Anleitung ist für **Windows**. Für Linux/Mac werden native Executables erstellt (kein .exe-Format).
