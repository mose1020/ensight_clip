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
import warnings
import threading
import yaml

# ParaView Fortschrittsanzeige
paraview.simple._DisableFirstRenderCameraReset()


class ProgressMonitor:
    """Timer-basierter Fortschritts-Monitor (aktualisiert alle 0.5s)"""
    def __init__(self, name="Operation", update_interval=0.5):
        self.name = name
        self.update_interval = update_interval
        self.start_time = time.time()
        self.running = False
        self.thread = None
        self.progress = 0.0
        self.lock = threading.Lock()

    def _monitor_loop(self):
        """Überwachungs-Loop im Thread"""
        iteration = 0
        while self.running:
            elapsed = time.time() - self.start_time
            with self.lock:
                current_progress = self.progress

            # Schätze ETA wenn Fortschritt vorhanden
            if current_progress > 0.001:
                eta = (elapsed / current_progress) * (1.0 - current_progress)
                eta_str = f"ETA: {eta:>7.0f}s"
            else:
                # Zeige Heartbeat bei 0% damit User sieht dass es läuft
                heartbeat = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                eta_str = f"{heartbeat[iteration % len(heartbeat)]} läuft..."

            percent = current_progress * 100.0
            print(f"  ⏳ {self.name}: {percent:6.2f}% | {elapsed:7.1f}s | {eta_str}", flush=True)

            iteration += 1
            time.sleep(self.update_interval)

    def start(self):
        """Start monitoring"""
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def update_progress(self, progress):
        """Update Fortschritt (0.0 bis 1.0)"""
        with self.lock:
            self.progress = progress

    def stop(self):
        """Stop monitoring"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=2.0)
            elapsed = time.time() - self.start_time
            print(f"  ✓ {self.name}: 100.00% | {elapsed:7.1f}s | Fertig      ", flush=True)


class ProgressObserver:
    """VTK Progress Observer - setzt ProgressMonitor-Werte"""
    def __init__(self, monitor):
        self.monitor = monitor

    def __call__(self, obj, event):
        """Wird von VTK bei Progress-Events aufgerufen"""
        progress = obj.GetProgress()
        if self.monitor:
            self.monitor.update_progress(progress)


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


def load_config(config_file='config.yaml'):
    """
    Lädt Konfiguration aus YAML-Datei

    Args:
        config_file: Pfad zur config.yaml

    Returns:
        dict mit Konfigurationsparametern
    """
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Config-Datei nicht gefunden: {config_file}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Aktive Konfiguration auswählen
    active_name = config.get('active_config', 'flieger')
    if active_name not in config.get('configs', {}):
        raise ValueError(f"Aktive Konfiguration '{active_name}' nicht in config.yaml gefunden!")

    active_config = config['configs'][active_name]

    # Füge globale Einstellungen hinzu
    active_config['num_processes'] = config.get('num_processes', 4)
    active_config['timeout'] = config.get('timeout', 3600)
    active_config['config_name'] = active_name

    return active_config


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
    log("\n📖 [1/4] Lese EnSight-Datei...")
    reader = EnSightReader(CaseFileName=input_file)

    # Progress Monitor für Reader
    reader_monitor = None
    if rank == 0:
        reader_monitor = ProgressMonitor("Lese EnSight", update_interval=0.5)
        reader_observer = ProgressObserver(reader_monitor)
        reader.SMProxy.AddObserver('ProgressEvent', reader_observer)
        reader_monitor.start()

    # OPTIMIERUNG: Für bessere parallele Verarbeitung
    reader.UpdatePipeline()

    if rank == 0 and reader_monitor:
        reader_monitor.stop()

    if num_ranks > 1:
        # Bei MPI: Nutze RedistributeDataSet für bessere Lastverteilung
        log(f"  ⚡ MPI Parallelisierung aktiv ({num_ranks} Prozesse)")

    # Info über geladene Daten
    if rank == 0:
        data_info = reader.GetDataInformation()
        print(f"  ✓ Geladen")
        print(f"  📊 Punkte: {data_info.GetNumberOfPoints():,}")
        print(f"  📊 Zellen: {data_info.GetNumberOfCells():,}")
        print(f"  📊 Arrays: {[reader.PointData.GetArray(i).Name for i in range(reader.PointData.GetNumberOfArrays())]}")

        # Mesh Bounds auslesen
        mesh_bounds = data_info.GetBounds()
        print(f"\n  📐 Mesh Bounds:")
        print(f"     X: [{mesh_bounds[0]:.3f}, {mesh_bounds[1]:.3f}]")
        print(f"     Y: [{mesh_bounds[2]:.3f}, {mesh_bounds[3]:.3f}]")
        print(f"     Z: [{mesh_bounds[4]:.3f}, {mesh_bounds[5]:.3f}]")

        # === BOUNDING BOX VALIDIERUNG ===
        if clip_type == 'box':
            log("\n🔍 [2/4] Validiere Bounding Box...")
            clip_xmin, clip_xmax = bounds[0], bounds[1]
            clip_ymin, clip_ymax = bounds[2], bounds[3]
            clip_zmin, clip_zmax = bounds[4], bounds[5]

            mesh_xmin, mesh_xmax = mesh_bounds[0], mesh_bounds[1]
            mesh_ymin, mesh_ymax = mesh_bounds[2], mesh_bounds[3]
            mesh_zmin, mesh_zmax = mesh_bounds[4], mesh_bounds[5]

            # Prüfe Überlappung
            has_overlap = (
                clip_xmin < mesh_xmax and clip_xmax > mesh_xmin and
                clip_ymin < mesh_ymax and clip_ymax > mesh_ymin and
                clip_zmin < mesh_zmax and clip_zmax > mesh_zmin
            )

            if not has_overlap:
                print("\n" + "=" * 70)
                print("⚠️  WARNUNG: Bounding Box liegt AUSSERHALB des Meshes!")
                print("=" * 70)
                print(f"  Clip Box: X[{clip_xmin:.3f}, {clip_xmax:.3f}] "
                      f"Y[{clip_ymin:.3f}, {clip_ymax:.3f}] Z[{clip_zmin:.3f}, {clip_zmax:.3f}]")
                print(f"  Mesh:     X[{mesh_xmin:.3f}, {mesh_xmax:.3f}] "
                      f"Y[{mesh_ymin:.3f}, {mesh_ymax:.3f}] Z[{mesh_zmin:.3f}, {mesh_zmax:.3f}]")
                print("\n  ❌ Ergebnis wird LEER sein!")
                print("=" * 70 + "\n")
            else:
                # Prüfe ob Box komplett innerhalb liegt
                fully_inside = (
                    clip_xmin >= mesh_xmin and clip_xmax <= mesh_xmax and
                    clip_ymin >= mesh_ymin and clip_ymax <= mesh_ymax and
                    clip_zmin >= mesh_zmin and clip_zmax <= mesh_zmax
                )

                if fully_inside:
                    print("  ✓ Bounding Box liegt VOLLSTÄNDIG im Mesh")
                else:
                    print("  ⚠️  Bounding Box liegt TEILWEISE ausserhalb des Meshes")
                    print("     (Nur überlappender Bereich wird geclippt)")

                # Berechne Überlappungsvolumen (als Indikator)
                overlap_x = min(clip_xmax, mesh_xmax) - max(clip_xmin, mesh_xmin)
                overlap_y = min(clip_ymax, mesh_ymax) - max(clip_ymin, mesh_ymin)
                overlap_z = min(clip_zmax, mesh_zmax) - max(clip_zmin, mesh_zmin)

                clip_vol = (clip_xmax - clip_xmin) * (clip_ymax - clip_ymin) * (clip_zmax - clip_zmin)
                overlap_vol = overlap_x * overlap_y * overlap_z
                overlap_pct = (overlap_vol / clip_vol * 100) if clip_vol > 0 else 0

                print(f"  📊 Überlappung: {overlap_pct:.1f}% der Clip-Box")

    # === 2. Clipping ===
    log("\n🔪 [3/4] Führe Clipping aus...")

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

    # Progress Monitor für Clipping
    clip_monitor = None
    if rank == 0:
        clip_monitor = ProgressMonitor("Clipping", update_interval=0.5)
        clip_observer = ProgressObserver(clip_monitor)
        clip.SMProxy.AddObserver('ProgressEvent', clip_observer)
        clip_monitor.start()

    # OPTIMIERUNG: Clipping mit optimierten Settings
    clip.UpdatePipeline()

    if rank == 0 and clip_monitor:
        clip_monitor.stop()

    # MergeBlocks um MultiBlockDataSet in UnstructuredGrid zu konvertieren
    merge = MergeBlocks(Input=clip)
    merge.MergePoints = 1  # Merge duplicate points für kleinere Dateien

    # Progress Monitor für Merging
    merge_monitor = None
    if rank == 0:
        merge_monitor = ProgressMonitor("Merge Blocks", update_interval=0.5)
        merge_observer = ProgressObserver(merge_monitor)
        merge.SMProxy.AddObserver('ProgressEvent', merge_observer)
        merge_monitor.start()

    merge.UpdatePipeline()

    if rank == 0 and merge_monitor:
        merge_monitor.stop()

    # MPI: ParaView verteilt Daten automatisch über Prozesse
    if num_ranks > 1:
        log(f"  ⚡ Daten werden parallel über {num_ranks} Prozesse verarbeitet")

    if rank == 0:
        merge_info = merge.GetDataInformation()
        elapsed = time.time() - start_time
        print(f"  ✓ Clipping abgeschlossen ({elapsed:.1f}s)")
        print(f"  📊 Ergebnis Punkte: {merge_info.GetNumberOfPoints():,}")
        print(f"  📊 Ergebnis Zellen: {merge_info.GetNumberOfCells():,}")

    # === 3. Output schreiben ===
    log("\n💾 [4/4] Schreibe Output...")

    output_path = Path(output_dir) / base_name
    output_path.mkdir(parents=True, exist_ok=True)

    # EnSight Gold Format
    output_file = str(output_path / f"{base_name}.case")

    # LegacyEnSightWriter für vollständigen EnSight-Output
    if rank == 0:
        print("  💾 Schreibe EnSight-Dateien...")
        print("  ℹ️  Hinweis: 'No BlockID' Warnungen sind harmlos und können ignoriert werden")

    writer = servermanager.writers.EnSightWriter(Input=merge)
    writer.FileName = output_file

    # Progress Monitor für Writer
    writer_monitor = None
    if rank == 0:
        writer_monitor = ProgressMonitor("Schreibe Datei", update_interval=0.5)
        writer_observer = ProgressObserver(writer_monitor)
        writer.SMProxy.AddObserver('ProgressEvent', writer_observer)
        writer_monitor.start()

    writer.UpdatePipeline()

    if rank == 0 and writer_monitor:
        writer_monitor.stop()

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
  # Mit config.yaml (empfohlen):
  mpirun -np 4 pvbatch paraview_clip.py --config config.yaml

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

    # YAML Config Datei (optional)
    parser.add_argument('--config', default=None,
                        help='YAML Config-Datei (z.B. config.yaml)')

    parser.add_argument('--input', default=None,
                        help='Input EnSight .case/.encas file')
    parser.add_argument('--output', default=None,
                        help='Output directory')
    parser.add_argument('--name', default=None,
                        help='Output base name')
    parser.add_argument('--type', default=None, choices=['box', 'plane', 'sphere'],
                        help='Clipping type')

    # Box Clipping
    parser.add_argument('--bounds',
                        help='Box bounds: "xmin,xmax,ymin,ymax,zmin,zmax"')

    # Plane Clipping
    parser.add_argument('--origin', default=None,
                        help='Plane origin: "x,y,z"')
    parser.add_argument('--normal', default=None,
                        help='Plane normal: "nx,ny,nz"')

    # Sphere Clipping
    parser.add_argument('--center',
                        help='Sphere center: "x,y,z"')
    parser.add_argument('--radius', type=float,
                        help='Sphere radius')

    args = parser.parse_args()

    # === YAML Config laden (wenn --config angegeben) ===
    if args.config:
        try:
            config = load_config(args.config)
            if get_rank() == 0:
                print(f"\n📋 Lade Konfiguration: {config['config_name']}")

            # Config-Werte als Defaults verwenden (können durch CLI-Args überschrieben werden)
            if args.input is None:
                args.input = config.get('input_file')
            if args.output is None:
                args.output = config.get('output_dir', 'output')
            if args.name is None:
                args.name = config.get('output_name', 'clipped')
            if args.type is None:
                args.type = config.get('clip_type', 'box')

            # Bounds/Origin/Normal/Center/Radius aus Config
            if args.type == 'box' and not args.bounds:
                bounds_list = config.get('bounds')
                if bounds_list:
                    args.bounds = ','.join(map(str, bounds_list))

            elif args.type == 'plane':
                if not args.origin:
                    origin_list = config.get('origin')
                    if origin_list:
                        args.origin = ','.join(map(str, origin_list))
                if not args.normal:
                    normal_list = config.get('normal')
                    if normal_list:
                        args.normal = ','.join(map(str, normal_list))

            elif args.type == 'sphere':
                if not args.center:
                    center_list = config.get('center')
                    if center_list:
                        args.center = ','.join(map(str, center_list))
                if not args.radius:
                    args.radius = config.get('radius')

        except Exception as e:
            if get_rank() == 0:
                print(f"❌ Fehler beim Laden der Config: {e}")
            sys.exit(1)

    # === Fallback auf Defaults wenn nichts angegeben ===
    if args.input is None:
        args.input = 'input/Kanalströmung/Kanalstroemung_fixed.encas'
    if args.output is None:
        args.output = 'output'
    if args.name is None:
        args.name = 'clipped_paraview'
    if args.type is None:
        args.type = 'plane'
    if args.origin is None:
        args.origin = '0,0,0'
    if args.normal is None:
        args.normal = '1,0,0'

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
