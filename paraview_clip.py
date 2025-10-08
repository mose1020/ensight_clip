#!/usr/bin/env python3
"""
ParaView Batch Clipping Script - PARALLEL VERSION
Deutlich schneller als VTK durch MPI-Parallelisierung

Usage:
    # Serial (1 Prozess):
    pvbatch paraview_clip.py

    # Parallel (8 Prozesse):
    mpirun -np 8 pvbatch paraview_clip.py

    # Mit custom Parametern:
    mpirun -np 8 pvbatch paraview_clip.py --input input.encas --output output --bounds "0,1,0,1,0,1"
"""

from paraview.simple import *
from paraview import servermanager
import sys
import os
import argparse
from pathlib import Path
import time

# ParaView Fortschrittsanzeige
paraview.simple._DisableFirstRenderCameraReset()


def log(msg, rank=0):
    """Logging nur von Prozess 0"""
    from paraview import servermanager
    pm = servermanager.vtkProcessModule.GetProcessModule()
    if pm.GetPartitionId() == rank:
        print(msg, flush=True)


def get_rank():
    """Aktuellen MPI-Rang ermitteln"""
    from paraview import servermanager
    pm = servermanager.vtkProcessModule.GetProcessModule()
    return pm.GetPartitionId()


def get_num_ranks():
    """Anzahl MPI-Prozesse ermitteln"""
    from paraview import servermanager
    pm = servermanager.vtkProcessModule.GetProcessModule()
    return pm.GetNumberOfLocalPartitions()


def clip_ensight_box(input_file, output_dir, bounds, clip_type='box', base_name='clipped'):
    """
    Clippt EnSight-Datei mit ParaView (parallel)

    Args:
        input_file: EnSight .case oder .encas Datei
        output_dir: Output-Verzeichnis
        bounds: [xmin, xmax, ymin, ymax, zmin, zmax]
        clip_type: 'box', 'plane', oder 'sphere'
        base_name: Basis-Name für Output
    """
    rank = get_rank()
    num_ranks = get_num_ranks()

    if rank == 0:
        print("=" * 70)
        print("🚀 ParaView Parallel Clipping")
        print("=" * 70)
        print(f"📊 MPI Prozesse: {num_ranks}")
        print(f"📂 Input:  {input_file}")
        print(f"📂 Output: {output_dir}")
        print(f"📐 Bounds: {bounds}")
        print("=" * 70)

    start_time = time.time()

    # === 1. EnSight-Datei lesen ===
    log("\n📖 Lese EnSight-Datei...")
    reader = EnSightReader(CaseFileName=input_file)
    reader.UpdatePipeline()

    # Info über geladene Daten
    if rank == 0:
        data_info = reader.GetDataInformation()
        print(f"  ✓ Geladen")
        print(f"  📊 Punkte: {data_info.GetNumberOfPoints():,}")
        print(f"  📊 Zellen: {data_info.GetNumberOfCells():,}")
        print(f"  📊 Arrays: {[reader.PointData.GetArray(i).Name for i in range(reader.PointData.GetNumberOfArrays())]}")

    # === 2. Clipping ===
    log("\n🔪 Führe Clipping aus...")

    if clip_type == 'box':
        clip = Clip(Input=reader)
        clip.ClipType = 'Box'
        clip.ClipType.Bounds = bounds
        clip.Invert = 1  # Keep inside
        clip.Crinkleclip = 0

    elif clip_type == 'plane':
        clip = Clip(Input=reader)
        clip.ClipType = 'Plane'
        clip.ClipType.Origin = bounds[0:3]  # [x, y, z]
        clip.ClipType.Normal = bounds[3:6]  # [nx, ny, nz]
        clip.Invert = 0

    elif clip_type == 'sphere':
        clip = Clip(Input=reader)
        clip.ClipType = 'Sphere'
        clip.ClipType.Center = bounds[0:3]  # [x, y, z]
        clip.ClipType.Radius = bounds[3]  # radius
        clip.Invert = 1  # Keep inside

    else:
        raise ValueError(f"Unbekannter clip_type: {clip_type}")

    # Update Pipeline (hier passiert das eigentliche Clipping)
    clip.UpdatePipeline()

    # MergeBlocks um MultiBlockDataSet in UnstructuredGrid zu konvertieren
    merge = MergeBlocks(Input=clip)
    merge.UpdatePipeline()

    if rank == 0:
        merge_info = merge.GetDataInformation()
        elapsed = time.time() - start_time
        print(f"  ✓ Clipping abgeschlossen ({elapsed:.1f}s)")
        print(f"  📊 Ergebnis Punkte: {merge_info.GetNumberOfPoints():,}")
        print(f"  📊 Ergebnis Zellen: {merge_info.GetNumberOfCells():,}")

    # === 3. Output schreiben ===
    log("\n💾 Schreibe Output...")

    output_path = Path(output_dir) / base_name
    output_path.mkdir(parents=True, exist_ok=True)

    # EnSight Gold Format
    output_file = str(output_path / f"{base_name}.case")

    # LegacyEnSightWriter für vollständigen EnSight-Output
    writer = servermanager.writers.EnSightWriter(Input=merge)
    writer.FileName = output_file
    writer.UpdatePipeline()

    if rank == 0:
        # Rename .case zu .encas (ParaView schreibt .0.case)
        output_dir_path = Path(output_file).parent
        case_files = list(output_dir_path.glob("*.case"))
        if case_files:
            for case_file in case_files:
                encas_file = case_file.with_suffix('.encas')
                case_file.rename(encas_file)
            log(f"  ✓ Geschrieben: {base_name}.encas + zugehörige Dateien (.geo, .pressure, .velocity, etc.)")

    # === Fertig ===
    total_time = time.time() - start_time

    if rank == 0:
        print("\n" + "=" * 70)
        print("✅ CLIPPING ERFOLGREICH")
        print("=" * 70)
        print(f"⏱️  Gesamtzeit: {total_time:.1f}s")
        print(f"🚀 Speedup durch {num_ranks} Prozesse")
        print("=" * 70)


def clip_ensight_plane(input_file, output_dir, origin, normal, base_name='clipped'):
    """Clippt mit Ebene"""
    bounds = list(origin) + list(normal)
    clip_ensight_box(input_file, output_dir, bounds, clip_type='plane', base_name=base_name)


def clip_ensight_sphere(input_file, output_dir, center, radius, base_name='clipped'):
    """Clippt mit Kugel"""
    bounds = list(center) + [radius]
    clip_ensight_box(input_file, output_dir, bounds, clip_type='sphere', base_name=base_name)


def main():
    """Main Function - kann mit Argumenten aufgerufen werden"""
    parser = argparse.ArgumentParser(
        description='ParaView Parallel EnSight Clipping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Serial:
  pvbatch paraview_clip.py

  # Parallel (8 Prozesse):
  mpirun -np 8 pvbatch paraview_clip.py

  # Custom Parameter:
  mpirun -np 8 pvbatch paraview_clip.py --input data.encas --bounds "0,1,0,1,0,1"

  # Plane Clip:
  pvbatch paraview_clip.py --type plane --origin "0,0,0" --normal "1,0,0"
        """
    )

    parser.add_argument('--input', default='input/Kanalströmung/Kanalstroemung_fixed.encas',
                        help='Input EnSight .case/.encas file')
    parser.add_argument('--output', default='output',
                        help='Output directory')
    parser.add_argument('--name', default='clipped_paraview',
                        help='Output base name')
    parser.add_argument('--type', default='plane', choices=['box', 'plane', 'sphere'],
                        help='Clipping type')

    # Box Clipping
    parser.add_argument('--bounds',
                        help='Box bounds: "xmin,xmax,ymin,ymax,zmin,zmax"')

    # Plane Clipping
    parser.add_argument('--origin', default='0,0,0',
                        help='Plane origin: "x,y,z"')
    parser.add_argument('--normal', default='1,0,0',
                        help='Plane normal: "nx,ny,nz"')

    # Sphere Clipping
    parser.add_argument('--center',
                        help='Sphere center: "x,y,z"')
    parser.add_argument('--radius', type=float,
                        help='Sphere radius')

    args = parser.parse_args()

    # Nur von Rank 0 ausgeben
    if get_rank() == 0:
        print(f"\n🔧 Konfiguration:")
        print(f"  Type: {args.type}")

    # Input-Datei prüfen
    input_path = Path(args.input)
    if not input_path.exists():
        if get_rank() == 0:
            print(f"❌ Input-Datei nicht gefunden: {input_path}")
            print(f"   Aktuelles Verzeichnis: {Path.cwd()}")
        sys.exit(1)

    # Clipping ausführen
    try:
        if args.type == 'box':
            if not args.bounds:
                if get_rank() == 0:
                    print("❌ --bounds erforderlich für Box-Clipping")
                sys.exit(1)
            bounds = [float(x) for x in args.bounds.split(',')]
            if len(bounds) != 6:
                if get_rank() == 0:
                    print("❌ --bounds muss 6 Werte haben: xmin,xmax,ymin,ymax,zmin,zmax")
                sys.exit(1)
            clip_ensight_box(str(input_path), args.output, bounds, 'box', args.name)

        elif args.type == 'plane':
            origin = [float(x) for x in args.origin.split(',')]
            normal = [float(x) for x in args.normal.split(',')]
            clip_ensight_plane(str(input_path), args.output, origin, normal, args.name)

        elif args.type == 'sphere':
            if not args.center or not args.radius:
                if get_rank() == 0:
                    print("❌ --center und --radius erforderlich für Sphere-Clipping")
                sys.exit(1)
            center = [float(x) for x in args.center.split(',')]
            clip_ensight_sphere(str(input_path), args.output, center, args.radius, args.name)

    except Exception as e:
        if get_rank() == 0:
            print(f"\n❌ FEHLER: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
