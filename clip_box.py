#!/usr/bin/env pvbatch
"""
EnSight Box Clipper - Schneidet eine Box aus EnSight-Daten
Verwendet globalen Ursprung (0,0,0) als Referenz
"""

from paraview.simple import *
import argparse
import time
from datetime import datetime
from pathlib import Path
import sys


def parse_args():
    """Parse Kommandozeilenargumente"""
    parser = argparse.ArgumentParser(
        description='Schneidet eine Box aus EnSight-Daten aus',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Standard 10m × 10m × 10m Box
  pvbatch clip_box.py

  # Eigene Box-Dimensionen
  pvbatch clip_box.py --xmin=-5 --xmax=8 --ymin=-3 --ymax=3 --zmin=-2 --zmax=2

  # Nur in X-Richtung beschränken
  pvbatch clip_box.py --xmin=-2 --xmax=5
        """
    )

    parser.add_argument('-i', '--input',
                        default='input/aircraft_aoa138_pp830/Referenzmodell_AoA138_PP830_ensight.case',
                        help='EnSight case Datei (default: aircraft dataset)')

    parser.add_argument('-o', '--output-dir',
                        default='output',
                        help='Ausgabeverzeichnis (default: output)')

    # Box-Grenzen relativ zum globalen Ursprung (0,0,0)
    parser.add_argument('--xmin', type=float, default=-5.0,
                        help='Minimale X-Grenze vom Ursprung (default: -5m)')
    parser.add_argument('--xmax', type=float, default=5.0,
                        help='Maximale X-Grenze vom Ursprung (default: +5m)')

    parser.add_argument('--ymin', type=float, default=-5.0,
                        help='Minimale Y-Grenze vom Ursprung (default: -5m)')
    parser.add_argument('--ymax', type=float, default=5.0,
                        help='Maximale Y-Grenze vom Ursprung (default: +5m)')

    parser.add_argument('--zmin', type=float, default=-5.0,
                        help='Minimale Z-Grenze vom Ursprung (default: -5m)')
    parser.add_argument('--zmax', type=float, default=5.0,
                        help='Maximale Z-Grenze vom Ursprung (default: +5m)')

    parser.add_argument('--export-ensight', action='store_true',
                        help='Exportiere auch als EnSight Gold Format')

    return parser.parse_args()


def clip_box(input_file, xmin, xmax, ymin, ymax, zmin, zmax, output_dir, export_ensight=False):
    """
    Hauptfunktion zum Clippen der Box
    """
    print("="*70)
    print("ENSIGHT BOX CLIPPER")
    print("="*70)

    start = time.time()

    # Box-Dimensionen berechnen
    box_width = xmax - xmin
    box_height = ymax - ymin
    box_depth = zmax - zmin
    box_center_x = (xmin + xmax) / 2.0
    box_center_y = (ymin + ymax) / 2.0
    box_center_z = (zmin + zmax) / 2.0

    print(f"\nBox-Konfiguration:")
    print(f"  X: [{xmin:.1f}m, {xmax:.1f}m] -> Breite: {box_width:.1f}m")
    print(f"  Y: [{ymin:.1f}m, {ymax:.1f}m] -> Höhe: {box_height:.1f}m")
    print(f"  Z: [{zmin:.1f}m, {zmax:.1f}m] -> Tiefe: {box_depth:.1f}m")
    print(f"  Zentrum: ({box_center_x:.1f}, {box_center_y:.1f}, {box_center_z:.1f})")
    print(f"  Volumen: {box_width:.1f}m × {box_height:.1f}m × {box_depth:.1f}m")

    # 1. LADE ENSIGHT DATEN
    print(f"\nLade EnSight Datei...")
    print(f"  Datei: {input_file}")

    if not Path(input_file).exists():
        print(f"FEHLER: Datei nicht gefunden: {input_file}")
        sys.exit(1)

    reader = EnSightReader(CaseFileName=input_file)
    reader.UpdatePipeline()

    # Info über geladene Daten
    info = reader.GetDataInformation()
    original_points = info.GetNumberOfPoints()
    original_cells = info.GetNumberOfCells()

    print(f"  Geladen: {original_points:,} Punkte, {original_cells:,} Zellen")
    print(f"  Zeit: {time.time()-start:.1f}s")

    # 2. CLIP MIT BOX
    print(f"\nSchneide Box aus...")

    clip = Clip(Input=reader)
    clip.ClipType = 'Box'

    # Position = Startpunkt der Box (untere linke Ecke)
    # Length = Ausdehnung in positive Richtung
    clip.ClipType.Position = [xmin, ymin, zmin]
    clip.ClipType.Length = [box_width, box_height, box_depth]
    clip.ClipType.Rotation = [0.0, 0.0, 0.0]

    # Wichtig: Invert=1 behält das Innere der Box
    clip.Invert = 1
    clip.Crinkleclip = 1

    clip.UpdateVTKObjects()
    clip.UpdatePipeline()

    current = clip

    print(f"  Geclippt ({time.time()-start:.1f}s)")

    # 3. MERGE BLOCKS & TETRAHEDRALIZE
    print(f"\nOptimiere Mesh...")

    merge = MergeBlocks(Input=current)
    merge.UpdatePipeline()

    tetra = Tetrahedralize(Input=merge)
    tetra.UpdatePipeline()

    # Info über geclippte Daten
    info = tetra.GetDataInformation()
    clipped_points = info.GetNumberOfPoints()
    clipped_cells = info.GetNumberOfCells()

    print(f"  Optimiert: {clipped_points:,} Punkte, {clipped_cells:,} Zellen")
    print(f"  Reduktion: {(1 - clipped_points/original_points)*100:.1f}% Punkte, "
          f"{(1 - clipped_cells/original_cells)*100:.1f}% Zellen")

    # 4. SPEICHERN
    print(f"\nSpeichere Ergebnisse...")

    # Erstelle Output-Verzeichnis mit Zeitstempel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    box_name = f"box_{box_width:.0f}x{box_height:.0f}x{box_depth:.0f}m"
    output_path = Path(output_dir) / f"{box_name}_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    # Speichere direkt als EnSight (PRIMÄR)
    if export_ensight:
        print(f"\nExportiere EnSight Gold (direkt)...")
        ensight_case = str(output_path / "clipped.case")

        try:
            # Verwende EnSightWriter direkt
            writer = CreateWriter(ensight_case, tetra)
            writer.UpdatePipeline()
            del writer

            print(f"  ✓ EnSight: {ensight_case}")
        except Exception as e:
            print(f"  ✗ EnSight-Export fehlgeschlagen: {e}")

    # Optional: Speichere auch als VTU (für Backup/ParaView)
    print(f"\nSpeichere VTU...")
    vtu_file = str(output_path / "clipped.vtu")
    try:
        SaveData(vtu_file, proxy=tetra)
        print(f"  ✓ VTU: {vtu_file}")
    except Exception as e:
        print(f"  ✗ VTU-Export fehlgeschlagen: {e}")
        print(f"    (EnSight ist trotzdem verfügbar)")

    # Fertig
    print(f"\nFertig!")
    print(f"  Gesamtzeit: {time.time()-start:.1f}s")
    print(f"  Output: {output_path}")
    print(f"\nÖffnen mit:")
    print(f"  paraview {vtu_file}")

    if export_ensight:
        case_file = output_path / "clipped.case"
        if case_file.exists():
            print(f"  paraview {case_file}")
        else:
            print(f"  (EnSight .case Datei wurde nicht erstellt)")

    print("="*70)

    return str(output_path)


def main():
    """Haupteinsprungspunkt"""
    args = parse_args()

    # Führe Clipping aus
    output_path = clip_box(
        input_file=args.input,
        xmin=args.xmin,
        xmax=args.xmax,
        ymin=args.ymin,
        ymax=args.ymax,
        zmin=args.zmin,
        zmax=args.zmax,
        output_dir=args.output_dir,
        export_ensight=args.export_ensight
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())