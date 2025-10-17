#!/usr/bin/env pvbatch
"""
EnSight Box Clipper - Vereinfachte Version für High-RAM-Systeme

Schneidet eine Box aus EnSight-Daten.
"""

from paraview.simple import *
import argparse
import time
import logging
from datetime import datetime
from pathlib import Path
import sys
import warnings
import os

# Unterdrücke VTK/ParaView Warnings
warnings.filterwarnings('ignore')
os.environ['VTK_SILENCE_GET_VOID_POINTER_WARNINGS'] = '1'

import vtk
vtk.vtkObject.GlobalWarningDisplayOff()
vtk_output_window = vtk.vtkFileOutputWindow()
vtk_output_window.SetFileName('/dev/null')
vtk.vtkOutputWindow.SetInstance(vtk_output_window)


def format_number(num):
    """Formatiere Zahlen lesbar (z.B. 62.1M statt 62134485)"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def setup_logging():
    """Setup Logging-System (Datei + Console)"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"clip_box_{timestamp}.log"

    logger = logging.getLogger('clip_box')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Datei + Console Handler
    for handler in [
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]:
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.info(f"Logging: {log_file}")
    return logger


def get_system_info():
    """Lese System-Ressourcen aus /proc/meminfo"""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
            mem_info = {}
            for line in lines:
                if 'MemTotal' in line:
                    mem_info['total_gb'] = int(line.split()[1]) / (1024 * 1024)
                elif 'MemAvailable' in line:
                    mem_info['available_gb'] = int(line.split()[1]) / (1024 * 1024)
            return mem_info
    except:
        return {'total_gb': 8.0, 'available_gb': 8.0}


def should_tetrahedralize(box_volume, available_ram_gb):
    """
    Entscheide ob Tetrahedralisierung sinnvoll ist

    Einfache Regel: Bei >40GB RAM und Box <5000m³ → JA
    """
    if available_ram_gb >= 40:
        return box_volume <= 5000
    elif available_ram_gb >= 20:
        return box_volume <= 2000
    else:
        return box_volume <= 500


def parse_args():
    """Parse Kommandozeilenargumente"""
    parser = argparse.ArgumentParser(
        description='Schneidet eine Box aus EnSight-Daten',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  pvbatch clip_box.py
  pvbatch clip_box.py --xmin=-5 --xmax=8 --ymin=-3 --ymax=3
  pvbatch clip_box.py --force-tetra
  ./run_clip_background.sh --xmin=-10 --xmax=10
        """
    )

    parser.add_argument('-i', '--input',
                        default='input/aircraft_aoa138_pp830/Referenzmodell_AoA138_PP830_ensight.case',
                        help='EnSight case Datei')
    parser.add_argument('-o', '--output-dir', default='output',
                        help='Ausgabeverzeichnis')

    # Box-Grenzen
    parser.add_argument('--xmin', type=float, default=-5.0, help='Min X (default: -5m)')
    parser.add_argument('--xmax', type=float, default=5.0, help='Max X (default: +5m)')
    parser.add_argument('--ymin', type=float, default=-5.0, help='Min Y (default: -5m)')
    parser.add_argument('--ymax', type=float, default=5.0, help='Max Y (default: +5m)')
    parser.add_argument('--zmin', type=float, default=-5.0, help='Min Z (default: -5m)')
    parser.add_argument('--zmax', type=float, default=5.0, help='Max Z (default: +5m)')

    # Processing-Optionen
    parser.add_argument('--force-tetra', action='store_true',
                        help='Erzwinge Tetrahedralisierung')
    parser.add_argument('--no-tetra', action='store_true',
                        help='Überspringe Tetrahedralisierung')
    parser.add_argument('--exact-clip', action='store_true',
                        help='Exakte Schnitte (LANGSAM!)')

    return parser.parse_args()


def clip_box(logger, input_file, xmin, xmax, ymin, ymax, zmin, zmax,
             output_dir, force_tetra=False, no_tetra=False, exact_clip=False):
    """
    Hauptfunktion: Clippe Box aus EnSight-Daten

    Workflow:
    1. Lade EnSight Daten
    2. Clippe Box
    3. Bereinige Mesh (CleantoGrid)
    4. Optional: Tetrahedralisiere
    5. Merge Blocks
    6. Exportiere als EnSight Gold
    """
    logger.info("="*70)
    logger.info("ENSIGHT BOX CLIPPER")
    logger.info("="*70)

    start_time = time.time()

    # System-Info
    mem_info = get_system_info()
    logger.info(f"System: {mem_info['total_gb']:.0f}GB RAM ({mem_info['available_gb']:.0f}GB verfügbar)")

    # Box-Info
    box_width = xmax - xmin
    box_height = ymax - ymin
    box_depth = zmax - zmin
    box_volume = box_width * box_height * box_depth
    logger.info(f"Box: {box_width:.0f}x{box_height:.0f}x{box_depth:.0f}m = {box_volume:.0f}m³")
    logger.info(f"Box-Position: X[{xmin:.1f}, {xmax:.1f}] Y[{ymin:.1f}, {ymax:.1f}] Z[{zmin:.1f}, {zmax:.1f}]")

    # Entscheide über Tetrahedralisierung
    use_tetra = should_tetrahedralize(box_volume, mem_info['available_gb'])
    if force_tetra:
        use_tetra = True
    if no_tetra:
        use_tetra = False
    logger.info(f"Tetrahedralisierung: {'JA' if use_tetra else 'NEIN'}")
    logger.info("")

    # 1. LADE ENSIGHT
    logger.info(f"Lade: {input_file}")
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {input_file}")

    step_time = time.time()
    reader = EnSightReader(CaseFileName=input_file)
    reader.UpdatePipeline()

    info = reader.GetDataInformation()
    original_points = info.GetNumberOfPoints()
    original_cells = info.GetNumberOfCells()
    logger.info(f"  Geladen: {format_number(original_points)} Punkte, {format_number(original_cells)} Zellen ({time.time()-step_time:.1f}s)")

    # 2. CLIPPE BOX
    logger.info("Clippe Box...")
    if exact_clip:
        logger.warning("  EXACT CLIP aktiviert - kann STUNDEN dauern!")

    step_time = time.time()
    clip = Clip(Input=reader)
    clip.ClipType = 'Box'
    clip.ClipType.Position = [xmin, ymin, zmin]
    clip.ClipType.Length = [box_width, box_height, box_depth]
    clip.ClipType.Rotation = [0.0, 0.0, 0.0]
    clip.Invert = 1
    clip.Crinkleclip = 0 if exact_clip else 1
    clip.UpdatePipeline()

    info = clip.GetDataInformation()
    clipped_points = info.GetNumberOfPoints()
    clipped_cells = info.GetNumberOfCells()
    logger.info(f"  Geclippt: {format_number(clipped_points)} Punkte, {format_number(clipped_cells)} Zellen ({time.time()-step_time:.1f}s)")

    current = clip

    # 3. BEREINIGE MESH
    logger.info("Bereinige Mesh (CleantoGrid)...")
    step_time = time.time()
    clean = CleantoGrid(Input=current)
    clean.UpdatePipeline()

    info = clean.GetDataInformation()
    clean_cells = info.GetNumberOfCells()
    logger.info(f"  Bereinigt: {format_number(clean_cells)} Zellen ({time.time()-step_time:.1f}s)")

    Delete(current)
    current = clean

    # 4. OPTIONAL: TETRAHEDRALISIERE
    if use_tetra:
        logger.info("Tetrahedralisiere...")
        step_time = time.time()

        tetra = Tetrahedralize(Input=current)
        tetra.UpdatePipeline()

        info = tetra.GetDataInformation()
        tetra_cells = info.GetNumberOfCells()
        logger.info(f"  Tetrahedralisiert: {format_number(tetra_cells)} Tetraeder ({time.time()-step_time:.1f}s)")

        Delete(current)
        current = tetra

    # 5. MERGE BLOCKS
    logger.info("Merge Blocks...")
    step_time = time.time()
    merge = MergeBlocks(Input=current)
    merge.UpdatePipeline()

    Delete(current)

    info = merge.GetDataInformation()
    final_points = info.GetNumberOfPoints()
    final_cells = info.GetNumberOfCells()
    logger.info(f"  Final: {format_number(final_points)} Punkte, {format_number(final_cells)} Zellen ({time.time()-step_time:.1f}s)")

    # Reduktion berechnen
    if original_points > 0 and original_cells > 0:
        reduction_pts = (1 - final_points/original_points) * 100
        reduction_cls = (1 - final_cells/original_cells) * 100
        logger.info(f"  Reduktion: {reduction_pts:.1f}% Punkte, {reduction_cls:.1f}% Zellen")

    # 6. EXPORTIERE
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    box_name = f"box_{box_width:.0f}x{box_height:.0f}x{box_depth:.0f}m"
    output_path = Path(output_dir) / f"{box_name}_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exportiere: {output_path}")
    ensight_case = str(output_path / "clipped.case")

    step_time = time.time()
    writer = CreateWriter(ensight_case, merge)
    writer.UpdatePipeline()
    del writer
    logger.info(f"  Export erfolgreich ({time.time()-step_time:.1f}s)")

    # FERTIG
    total_time = time.time() - start_time
    logger.info("")
    logger.info("="*70)
    logger.info("ERFOLGREICH!")
    logger.info(f"Zeit: {total_time:.1f}s ({total_time/60:.1f} min)")
    logger.info(f"Output: {output_path}")
    logger.info(f"Öffnen: paraview {ensight_case}")
    logger.info("="*70)

    # Cleanup
    Delete(merge)
    Delete(reader)

    return str(output_path)


def main():
    """Haupteinsprungspunkt"""
    logger = setup_logging()

    try:
        args = parse_args()

        clip_box(
            logger=logger,
            input_file=args.input,
            xmin=args.xmin, xmax=args.xmax,
            ymin=args.ymin, ymax=args.ymax,
            zmin=args.zmin, zmax=args.zmax,
            output_dir=args.output_dir,
            force_tetra=args.force_tetra,
            no_tetra=args.no_tetra,
            exact_clip=args.exact_clip
        )
        return 0

    except Exception as e:
        logger.error(f"FEHLER: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
