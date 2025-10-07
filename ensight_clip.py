#!/usr/bin/env python3
"""
EnSight File Clipping Tool
Clips both geometry and flow variables from an EnSight dataset
Mit Fortschrittsanzeige und Speicheroptimierung
"""

import vtk
import numpy as np
import os
import sys
import shutil
from pathlib import Path
import time
import psutil
import gc
from datetime import datetime, timedelta
import signal
import traceback
import logging


def setup_logging(log_file="ensight_clip.log"):
    """Richtet Logging ein - schreibt sowohl in Datei als auch auf Console"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


class ProgressCallback:
    """Fortschrittsanzeige mit Zeitschätzung"""

    def __init__(self, name="Operation", show_memory=True):
        self.name = name
        self.last_progress = 0
        self.start_time = None
        self.show_memory = show_memory
        self.last_update_time = 0

    def __call__(self, caller, event):
        if self.start_time is None:
            self.start_time = time.time()
            print(f"\n📊 {self.name}...")
            if self.show_memory:
                mem = psutil.Process().memory_info().rss / 1024 / 1024
                print(f"  💾 Speicher: {mem:.0f} MB")

        progress = caller.GetProgress() * 100
        current_time = time.time()

        if (progress - self.last_progress > 1 or
            current_time - self.last_update_time > 0.5 or
            progress >= 100):

            elapsed = current_time - self.start_time

            if progress > 0:
                total_estimated = elapsed * (100.0 / progress)
                remaining = total_estimated - elapsed
                eta_str = str(timedelta(seconds=int(remaining)))
            else:
                eta_str = "..."

            # Fortschrittsbalken
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)

            # Farben
            if progress < 33:
                color = '\033[91m'  # Rot
            elif progress < 66:
                color = '\033[93m'  # Gelb
            else:
                color = '\033[92m'  # Grün
            reset = '\033[0m'

            # Speicherinfo
            if self.show_memory:
                mem = psutil.Process().memory_info().rss / 1024 / 1024
                mem_info = f" | 💾 {mem:.0f} MB"
            else:
                mem_info = ""

            output = f"\r  {color}{bar}{reset} {progress:5.1f}% | ⏱️  {elapsed:.1f}s | ETA: {eta_str}{mem_info}"
            print(output, end='', flush=True)

            self.last_progress = progress
            self.last_update_time = current_time

            if progress >= 100:
                print()
                print(f"  ✅ Abgeschlossen in {elapsed:.1f}s")


class EnSightClipper:
    """EnSight Clipper mit Fortschrittsanzeige und Speicheroptimierung"""

    def __init__(self, case_file, verbose=True):
        """
        Initialize the EnSight clipper

        Args:
            case_file: Path to the EnSight .case or .encas file
            verbose: Zeige detaillierte Ausgaben
        """
        self.case_file = case_file
        self.case_path = Path(case_file)
        self.reader = None
        self.clipped_data = None
        self.verbose = verbose

    def read_ensight(self):
        """Read EnSight data"""
        if self.verbose:
            print(f"Reading EnSight file: {self.case_file}")

        self.reader = vtk.vtkGenericEnSightReader()
        self.reader.SetCaseFileName(self.case_file)
        self.reader.Update()

        output = self.reader.GetOutput()

        if self.verbose:
            print(f"Successfully loaded EnSight case file")
            if hasattr(output, 'GetNumberOfBlocks'):
                print(f"Number of blocks: {output.GetNumberOfBlocks()}")

        return output

    def clip_with_plane(self, origin, normal, invert=False):
        """
        Clip data with a plane

        Args:
            origin: Plane origin point [x, y, z]
            normal: Plane normal vector [nx, ny, nz]
            invert: If True, keep the opposite side
        """
        if self.verbose:
            print(f"\n🔪 Clipping mit Ebene: origin={origin}, normal={normal}")

        plane = vtk.vtkPlane()
        plane.SetOrigin(origin)
        plane.SetNormal(normal)

        output = self.reader.GetOutput()

        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            merged_data = self._merge_blocks(output)
        else:
            merged_data = output

        clipper = vtk.vtkTableBasedClipDataSet()
        clipper.SetInputData(merged_data)
        clipper.SetClipFunction(plane)
        clipper.SetInsideOut(invert)
        clipper.SetMergeTolerance(1e-6)

        progress_cb = ProgressCallback("Plane Clipping")
        clipper.AddObserver(vtk.vtkCommand.ProgressEvent, progress_cb)

        start_time = time.time()

        try:
            # Speicher vor Clipping prüfen
            mem = psutil.virtual_memory()
            mem_available_gb = mem.available / 1024 / 1024 / 1024

            if mem_available_gb < 2.0:
                print(f"\n⚠️  WARNUNG: Nur {mem_available_gb:.1f} GB verfügbar!")
                print("   Das Clipping könnte fehlschlagen oder abbrechen.")

            clipper.Update()
            elapsed = time.time() - start_time

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ Fehler beim Clipping nach {elapsed:.1f}s:")
            print(f"   {type(e).__name__}: {e}")
            traceback.print_exc()
            raise

        self.clipped_data = clipper.GetOutput()

        if self.verbose:
            n_cells = self.clipped_data.GetNumberOfCells()
            n_points = self.clipped_data.GetNumberOfPoints()
            print(f"\n✅ Clipping abgeschlossen in {elapsed:.1f}s")
            print(f"📊 Ergebnis: {n_points:,} Punkte, {n_cells:,} Zellen")

        return self.clipped_data

    def clip_with_box(self, bounds, use_prefilter=True):
        """
        Clip data with a box - SPEICHEROPTIMIERT

        Args:
            bounds: Box bounds [xmin, xmax, ymin, ymax, zmin, zmax]
            use_prefilter: Vorfilterung zur Speicheroptimierung (empfohlen für große Datensätze)
        """
        if self.verbose:
            print("\n" + "=" * 70)
            print("🎯 BOX-CLIPPING")
            print("=" * 70)
            print(f"\n📐 Box-Grenzen:")
            print(f"  X: [{bounds[0]:.3f}, {bounds[1]:.3f}]")
            print(f"  Y: [{bounds[2]:.3f}, {bounds[3]:.3f}]")
            print(f"  Z: [{bounds[4]:.3f}, {bounds[5]:.3f}]")

        # Check available memory
        mem_available = psutil.virtual_memory().available / 1024 / 1024 / 1024
        if self.verbose:
            print(f"\n💾 Verfügbarer Speicher: {mem_available:.1f} GB")

        output = self.reader.GetOutput()

        # Prüfe ob wir Block-für-Block clippen müssen
        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            total_cells = sum(output.GetBlock(i).GetNumberOfCells()
                            for i in range(output.GetNumberOfBlocks())
                            if output.GetBlock(i))

            if self.verbose:
                print(f"\n📊 Gesamt: {total_cells:,} Zellen in {output.GetNumberOfBlocks()} Blöcken")

            # Bei sehr großen Datensätzen: Block-für-Block clippen
            if total_cells > 10_000_000:
                if self.verbose:
                    print("🔄 STRATEGIE: Block-für-Block Clipping (>10M Zellen)")
                    print("   ⚠️  Dies dauert länger aber spart Speicher")
                return self._clip_blocks_individually(output, bounds)

        # Standard-Methode für kleinere Datensätze
        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            if self.verbose:
                print("\n🔄 Führe Blöcke zusammen...")
            merged_data = self._merge_blocks(output)
        else:
            merged_data = output

        # Vorfilterung bei großen Datensätzen
        if use_prefilter and merged_data.GetNumberOfCells() > 100000:
            if self.verbose:
                print("\n🔍 Aktiviere Vorfilterung zur Speicheroptimierung...")
            merged_data = self._prefilter_region(merged_data, bounds)
            gc.collect()

        # Create box and clipper
        box = vtk.vtkBox()
        box.SetBounds(bounds)

        clipper = vtk.vtkTableBasedClipDataSet()
        clipper.SetInputData(merged_data)
        clipper.SetClipFunction(box)
        clipper.SetInsideOut(True)  # Keep inside
        clipper.SetMergeTolerance(1e-6)
        clipper.SetGenerateClippedOutput(False)

        if self.verbose:
            print("\n🔪 Führe Clipping aus...")

        progress_cb = ProgressCallback("Box Clipping", show_memory=True)
        clipper.AddObserver(vtk.vtkCommand.ProgressEvent, progress_cb)

        start_time = time.time()

        try:
            # Speicher vor Clipping prüfen
            mem = psutil.virtual_memory()
            mem_used_gb = mem.used / 1024 / 1024 / 1024
            mem_available_gb = mem.available / 1024 / 1024 / 1024

            if mem_available_gb < 2.0:
                print(f"\n⚠️  WARNUNG: Nur {mem_available_gb:.1f} GB verfügbar!")
                print("   Das Clipping könnte fehlschlagen oder abbrechen.")
                response = input("   Trotzdem fortfahren? (j/n): ")
                if response.lower() != 'j':
                    raise MemoryError("Abbruch wegen zu wenig Speicher")

            clipper.Update()
            elapsed = time.time() - start_time

        except MemoryError as e:
            print(f"\n❌ Speicherfehler: {e}")
            print("   Versuche Block-für-Block Clipping...")
            return self._clip_blocks_individually(self.reader.GetOutput(), bounds)

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ Fehler beim Clipping nach {elapsed:.1f}s:")
            print(f"   {type(e).__name__}: {e}")
            traceback.print_exc()
            raise

        self.clipped_data = clipper.GetOutput()

        if self.verbose:
            n_cells = self.clipped_data.GetNumberOfCells()
            n_points = self.clipped_data.GetNumberOfPoints()
            print("\n" + "=" * 70)
            print("✅ CLIPPING ERFOLGREICH")
            print("=" * 70)
            print(f"⏱️  Zeit: {elapsed:.1f}s")
            print(f"📊 Ergebnis: {n_points:,} Punkte, {n_cells:,} Zellen")

        return self.clipped_data

    def _clip_blocks_individually(self, output, bounds):
        """
        Clippt jeden Block einzeln - extrem speicherschonend
        """
        if self.verbose:
            print("\n🔪 Clippe Blöcke einzeln...")

        box = vtk.vtkBox()
        box.SetBounds(bounds)

        append = vtk.vtkAppendFilter()
        n_blocks = output.GetNumberOfBlocks()
        blocks_clipped = 0
        blocks_skipped = 0
        start_time = time.time()

        for block_idx in range(n_blocks):
            block = output.GetBlock(block_idx)
            if block is None or block.GetNumberOfCells() == 0:
                continue

            n_cells = block.GetNumberOfCells()

            # SCHNELLER PRE-CHECK: Liegt Block komplett außerhalb der Box?
            block_bounds = block.GetBounds()
            if not self._bounds_intersect(block_bounds, bounds):
                if self.verbose:
                    print(f"\n  📦 Block {block_idx+1}/{n_blocks}: {n_cells:,} Zellen")
                    print(f"     ⊘ Komplett außerhalb Box (übersprungen)")
                blocks_skipped += 1
                continue

            if self.verbose:
                print(f"\n  📦 Block {block_idx+1}/{n_blocks}: {n_cells:,} Zellen")
                mem = psutil.Process().memory_info().rss / 1024 / 1024
                print(f"     💾 Speicher: {mem:.0f} MB")
                print(f"     🔄 Clippe Block...")

            # Clip Block
            clipper = vtk.vtkTableBasedClipDataSet()
            clipper.SetInputData(block)
            clipper.SetClipFunction(box)
            clipper.SetInsideOut(True)
            clipper.SetMergeTolerance(1e-6)
            clipper.SetGenerateClippedOutput(False)

            # Progress-Callback für diesen Block
            progress_cb = ProgressCallback(f"Block {block_idx+1}/{n_blocks}", show_memory=True)
            clipper.AddObserver(vtk.vtkCommand.ProgressEvent, progress_cb)

            try:
                # Speicherprüfung vor jedem Block
                mem = psutil.virtual_memory()
                if mem.available < 1024 * 1024 * 1024:  # < 1GB
                    print(f"\n     ⚠️  Kritischer Speichermangel! Nur {mem.available/1024/1024:.0f} MB frei")
                    print(f"     Erzwinge Garbage Collection...")
                    gc.collect()
                    mem = psutil.virtual_memory()
                    if mem.available < 512 * 1024 * 1024:  # < 512MB
                        print(f"     ❌ Immer noch zu wenig Speicher. Breche ab.")
                        break

                block_start = time.time()
                clipper.Update()
                block_elapsed = time.time() - block_start
                clipped = clipper.GetOutput()

                if clipped.GetNumberOfCells() > 0:
                    append.AddInputData(clipped)
                    blocks_clipped += 1
                    if self.verbose:
                        print(f"     ✓ {clipped.GetNumberOfCells():,} Zellen behalten ({block_elapsed:.1f}s)")
                else:
                    if self.verbose:
                        print(f"     ⊘ Block außerhalb Box ({block_elapsed:.1f}s)")

            except MemoryError as e:
                if self.verbose:
                    print(f"     ❌ Speicherfehler: {e}")
                    print(f"     Überspringe Block {block_idx+1}")
                continue

            except Exception as e:
                if self.verbose:
                    print(f"     ⚠️  Fehler: {type(e).__name__}: {e}")
                continue

            finally:
                # Speicher freigeben
                try:
                    del clipper
                    if 'clipped' in locals():
                        del clipped
                except:
                    pass
                gc.collect()

        if blocks_clipped == 0:
            if self.verbose:
                print("\n⚠️  Keine Blöcke in Box!")
            self.clipped_data = vtk.vtkUnstructuredGrid()
            return self.clipped_data

        if self.verbose:
            print(f"\n🔧 Füge {blocks_clipped} Blöcke zusammen...")

        append.Update()
        self.clipped_data = append.GetOutput()

        elapsed = time.time() - start_time

        if self.verbose:
            n_cells = self.clipped_data.GetNumberOfCells()
            n_points = self.clipped_data.GetNumberOfPoints()
            print("\n" + "=" * 70)
            print("✅ BLOCK-BY-BLOCK CLIPPING ERFOLGREICH")
            print("=" * 70)
            blocks_processed = blocks_clipped + blocks_skipped
            print(f"⏱️  Zeit: {elapsed:.1f}s ({elapsed/blocks_processed:.1f}s/Block)")
            print(f"📊 Ergebnis: {n_points:,} Punkte, {n_cells:,} Zellen")
            print(f"📦 {blocks_clipped}/{n_blocks} Blöcke geclippt, {blocks_skipped} übersprungen")

        return self.clipped_data

    def _bounds_intersect(self, bounds1, bounds2):
        """
        Prüft ob zwei Bounding Boxes sich überschneiden
        bounds format: [xmin, xmax, ymin, ymax, zmin, zmax]
        """
        # Kein Overlap wenn eine Box komplett links, rechts, über, unter, vor oder hinter der anderen liegt
        if (bounds1[1] < bounds2[0] or  # bounds1 links von bounds2
            bounds1[0] > bounds2[1] or  # bounds1 rechts von bounds2
            bounds1[3] < bounds2[2] or  # bounds1 unter bounds2
            bounds1[2] > bounds2[3] or  # bounds1 über bounds2
            bounds1[5] < bounds2[4] or  # bounds1 vor bounds2
            bounds1[4] > bounds2[5]):   # bounds1 hinter bounds2
            return False
        return True

    def clip_with_sphere(self, center, radius):
        """
        Clip data with a sphere

        Args:
            center: Sphere center [x, y, z]
            radius: Sphere radius
        """
        if self.verbose:
            print(f"\n🔪 Clipping mit Kugel: center={center}, radius={radius}")

        sphere = vtk.vtkSphere()
        sphere.SetCenter(center)
        sphere.SetRadius(radius)

        output = self.reader.GetOutput()

        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            merged_data = self._merge_blocks(output)
        else:
            merged_data = output

        clipper = vtk.vtkTableBasedClipDataSet()
        clipper.SetInputData(merged_data)
        clipper.SetClipFunction(sphere)
        clipper.SetInsideOut(True)  # Keep inside
        clipper.SetMergeTolerance(1e-6)

        progress_cb = ProgressCallback("Sphere Clipping")
        clipper.AddObserver(vtk.vtkCommand.ProgressEvent, progress_cb)

        start_time = time.time()
        clipper.Update()
        elapsed = time.time() - start_time

        self.clipped_data = clipper.GetOutput()

        if self.verbose:
            n_cells = self.clipped_data.GetNumberOfCells()
            n_points = self.clipped_data.GetNumberOfPoints()
            print(f"\n✅ Clipping abgeschlossen in {elapsed:.1f}s")
            print(f"📊 Ergebnis: {n_points:,} Punkte, {n_cells:,} Zellen")

        return self.clipped_data

    def _merge_blocks(self, output):
        """Merge multiblock dataset"""
        append = vtk.vtkAppendDataSets()
        append.SetOutputDataSetType(vtk.VTK_UNSTRUCTURED_GRID)

        for i in range(output.GetNumberOfBlocks()):
            block = output.GetBlock(i)
            if block and block.GetNumberOfCells() > 0:
                append.AddInputData(block)

        if self.verbose:
            progress_cb = ProgressCallback("Block-Zusammenführung", show_memory=False)
            append.AddObserver(vtk.vtkCommand.ProgressEvent, progress_cb)

        append.Update()
        result = append.GetOutput()

        if self.verbose:
            print(f"  ✓ {result.GetNumberOfCells():,} Zellen zusammengeführt")

        return result

    def _prefilter_region(self, data, bounds):
        """
        Grobe Vorfilterung um Speicher zu sparen
        Nutzt erweiterte Bounds damit das finale Clipping korrekt arbeitet
        """
        # Erweitere Bounds um 50% für Vorfilterung
        extended_bounds = list(bounds)
        margin = 0.5
        for i in range(0, 6, 2):
            size = bounds[i+1] - bounds[i]
            extended_bounds[i] -= size * margin
            extended_bounds[i+1] += size * margin

        extract = vtk.vtkExtractGeometry()
        box = vtk.vtkBox()
        box.SetBounds(extended_bounds)
        extract.SetImplicitFunction(box)
        extract.SetInputData(data)
        extract.ExtractInsideOn()
        extract.Update()

        extracted = extract.GetOutput()

        if self.verbose:
            print(f"  📊 Vorfilterung: {data.GetNumberOfCells():,} → {extracted.GetNumberOfCells():,} Zellen")

        return extracted

    def write_ensight(self, output_dir, base_name="clipped"):
        """
        Write clipped data to EnSight format

        Args:
            output_dir: Output directory
            base_name: Base name for output files
        """
        if self.clipped_data is None:
            raise ValueError("No clipped data available. Run a clip operation first.")

        output_path = Path(output_dir) / base_name
        output_path.mkdir(parents=True, exist_ok=True)

        if self.verbose:
            print(f"\n📝 Schreibe EnSight-Dateien nach: {output_path}")

        # Convert to tetrahedra for EnSight compatibility
        if self.verbose:
            print("  🔺 Konvertiere für EnSight-Export...")

        tetra_filter = vtk.vtkDataSetTriangleFilter()
        tetra_filter.SetInputData(self.clipped_data)

        progress_cb = ProgressCallback("EnSight Konvertierung", show_memory=False)
        tetra_filter.AddObserver(vtk.vtkCommand.ProgressEvent, progress_cb)

        tetra_filter.Update()

        tetra_data = tetra_filter.GetOutput()

        if self.verbose:
            n_cells = tetra_data.GetNumberOfCells()
            n_points = tetra_data.GetNumberOfPoints()
            print(f"\n  📊 Nach Konvertierung: {n_points:,} Punkte, {n_cells:,} Zellen")

        # Write EnSight
        writer = vtk.vtkEnSightWriter()
        writer.SetInputData(tetra_data)
        writer.SetFileName(str(output_path / f"{base_name}.case"))
        writer.SetPath(str(output_path))
        writer.SetBaseName(base_name)
        writer.Write()

        # Rename case file
        temp_case = output_path / f"{base_name}.0.case"
        encas_file = output_path / f"{base_name}.encas"
        if temp_case.exists():
            temp_case.replace(encas_file)

        # Copy or create XML metadata
        xml_source = self.case_path.parent / f"{self.case_path.stem}.xml"
        xml_dest = output_path / f"{base_name}.xml"

        if xml_source.exists():
            shutil.copy2(xml_source, xml_dest)
        else:
            self._create_xml_from_data(xml_dest, tetra_data)

        if self.verbose:
            print(f"\n✅ Erfolgreich geschrieben")
            print(f"  📂 Case: {encas_file.name}")
            print(f"  📄 XML:  {xml_dest.name}")

    def _create_xml_from_data(self, xml_path, data):
        """Create XML metadata file from clipped data"""
        point_data = data.GetPointData()

        varlist = []
        for i in range(point_data.GetNumberOfArrays()):
            array_name = point_data.GetArrayName(i)

            # Determine units
            if 'pressure' in array_name.lower():
                units_label, units_dims = "Pa", "M/LTT"
            elif 'velocity' in array_name.lower():
                units_label, units_dims = "m s^-1", "L/T"
            elif 'turb_kinetic_energy' in array_name.lower():
                units_label, units_dims = "m^2 s^-2", "LL/TT"
            elif 'turb_diss' in array_name.lower():
                units_label, units_dims = "m^2 s^-3", "LL/TTT"
            elif 'temperature' in array_name.lower():
                units_label, units_dims = "K", "Θ"
            elif 'density' in array_name.lower():
                units_label, units_dims = "kg m^-3", "M/LLL"
            else:
                units_label, units_dims = "", ""

            varlist.append(f'      <var name ="{array_name}" ENS_UNITS_LABEL="{units_label}" ENS_UNITS_DIMS="{units_dims}"></var>')

        varlist.append('      <var name ="Coordinates" ENS_UNITS_LABEL="m" ENS_UNITS_DIMS="L"></var>')
        varlist.append('      <var name ="Time" ENS_UNITS_LABEL="s" ENS_UNITS_DIMS="T"></var>')

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<CEImetadata version="1.0">
  <vars>
    <metatags>
      <tag name="ENS_UNITS_LABEL" type="str"></tag>
      <tag name="ENS_UNITS_DIMS" type="str"></tag>
    </metatags>
    <varlist>
{chr(10).join(varlist)}
    </varlist>
  </vars>
  <case>
    <metatags>
        <tag name="ENS_UNITS_LABEL" type="flt">2.0</tag>
        <tag name="ENS_UNITS_DIMS" type="flt">1.0</tag>
        <tag name="ENS_UNITS_SYSTEM" type="flt">1.0</tag>
        <tag name="ENS_UNITS_SYSTEM_NAME" type="str">SI</tag>
    </metatags>
  </case>
</CEImetadata>
"""
        with open(xml_path, 'w') as f:
            f.write(xml_content)

    def get_bounds(self):
        """Get bounds of the dataset"""
        if self.reader is None:
            self.read_ensight()

        output = self.reader.GetOutput()

        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            all_bounds = None
            for block_idx in range(output.GetNumberOfBlocks()):
                block = output.GetBlock(block_idx)
                if block and block.GetNumberOfCells() > 0:
                    block_bounds = block.GetBounds()
                    if all_bounds is None:
                        all_bounds = list(block_bounds)
                    else:
                        all_bounds[0] = min(all_bounds[0], block_bounds[0])
                        all_bounds[1] = max(all_bounds[1], block_bounds[1])
                        all_bounds[2] = min(all_bounds[2], block_bounds[2])
                        all_bounds[3] = max(all_bounds[3], block_bounds[3])
                        all_bounds[4] = min(all_bounds[4], block_bounds[4])
                        all_bounds[5] = max(all_bounds[5], block_bounds[5])
            bounds = all_bounds if all_bounds else [0] * 6
        else:
            bounds = [0] * 6
            output.GetBounds(bounds)

        if self.verbose:
            print(f"Dataset bounds: {bounds}")

        return bounds

    def get_point_arrays(self):
        """Get list of point data arrays"""
        if self.reader is None:
            self.read_ensight()

        output = self.reader.GetOutput()

        point_data = None
        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            for block_idx in range(output.GetNumberOfBlocks()):
                block = output.GetBlock(block_idx)
                if block and block.GetNumberOfCells() > 0:
                    point_data = block.GetPointData()
                    break
        elif hasattr(output, 'GetPointData'):
            point_data = output.GetPointData()

        arrays = []
        if point_data is not None:
            for i in range(point_data.GetNumberOfArrays()):
                array_name = point_data.GetArrayName(i)
                arrays.append(array_name)

        if self.verbose:
            print(f"Point data arrays: {arrays}")

        return arrays


def signal_handler(signum, frame):
    """Handler für System-Signale"""
    signame = signal.Signals(signum).name
    print(f"\n\n⚠️  Signal {signame} ({signum}) empfangen!")
    print("Das Programm wird beendet...")
    sys.exit(1)


def main():
    """Main function - clips Kanalstroemung dataset"""

    # Signal-Handler registrieren
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Logging einrichten
    logger = setup_logging()

    print("=" * 60)
    print("EnSight File Clipping Tool")
    print("=" * 60)
    logger.info("=" * 60)
    logger.info("EnSight File Clipping Tool gestartet")
    logger.info("=" * 60)

    # Systeminfo loggen
    mem = psutil.virtual_memory()
    logger.info(f"System: {sys.platform}")
    logger.info(f"RAM Gesamt: {mem.total/1024/1024/1024:.1f} GB")
    logger.info(f"RAM Verfügbar: {mem.available/1024/1024/1024:.1f} GB")

    # Default paths
    input_dir = Path(__file__).parent / "input" / "Kanalströmung"
    case_file = input_dir / "Kanalstroemung_fixed.encas"
    output_dir = Path(__file__).parent / "output"

    if not case_file.exists():
        logger.error(f"Case file nicht gefunden: {case_file}")
        print(f"\nError: Case file not found: {case_file}")
        return

    logger.info(f"Input:  {case_file}")
    logger.info(f"Output: {output_dir}")
    print(f"\nInput:  {case_file}")
    print(f"Output: {output_dir}")

    try:
        logger.info("Starte Clipping-Prozess...")
        # Create clipper
        logger.info("Erstelle Clipper-Objekt...")
        clipper = EnSightClipper(str(case_file))

        # Read data
        logger.info("Lese EnSight-Daten...")
        print("\n📂 Lese Daten...")
        clipper.read_ensight()

        logger.info("Ermittle Bounds und Arrays...")
        bounds = clipper.get_bounds()
        arrays = clipper.get_point_arrays()
        logger.info(f"Bounds: {bounds}")
        logger.info(f"Arrays: {arrays}")

        print("\n" + "=" * 60)
        print("Clipping Configuration")
        print("=" * 60)

        # Clip with a plane
        origin = [0.0, 0.0, 0.0]
        normal = [1.0, 0.0, 0.0]
        logger.info(f"Plane Clip - Origin: {origin}, Normal: {normal}")
        print(f"Using plane clip: origin={origin}, normal={normal}")

        print("\n🔪 Starte Clipping...")
        logger.info("Starte Plane Clipping...")
        clipper.clip_with_plane(origin, normal, invert=False)
        logger.info("Plane Clipping abgeschlossen!")

        # Write output
        print("\n💾 Schreibe Ergebnis...")
        logger.info("Schreibe EnSight-Output...")
        clipper.write_ensight(str(output_dir), "Kanalstroemung_clipped")
        logger.info("EnSight-Output geschrieben!")

        print("\n" + "=" * 60)
        print("✅ Clipping completed successfully!")
        print("=" * 60)
        logger.info("=" * 60)
        logger.info("✅ Clipping erfolgreich abgeschlossen!")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("Abbruch durch Benutzer (Ctrl+C)")
        print("\n\n⚠️  Abbruch durch Benutzer (Ctrl+C)")
        sys.exit(1)

    except MemoryError as e:
        logger.error(f"SPEICHERFEHLER: {e}")
        print(f"\n\n❌ SPEICHERFEHLER:")
        print(f"   {e}")
        print(f"\n💡 Tipps:")
        print(f"   - Nutze einen Rechner mit mehr RAM")
        print(f"   - Reduziere die Datenmenge vorher")
        print(f"   - Das Programm versucht automatisch Block-für-Block Clipping")
        print(f"\n📄 Details im Logfile: ensight_clip.log")
        sys.exit(1)

    except Exception as e:
        logger.error(f"UNERWARTETER FEHLER: {type(e).__name__}: {e}")
        logger.error("Stacktrace:", exc_info=True)

        mem = psutil.virtual_memory()
        logger.error(f"RAM Verwendet: {mem.used/1024/1024/1024:.1f} GB")
        logger.error(f"RAM Verfügbar: {mem.available/1024/1024/1024:.1f} GB")

        print(f"\n\n❌ UNERWARTETER FEHLER:")
        print(f"   {type(e).__name__}: {e}")
        print(f"\n📋 Stacktrace:")
        traceback.print_exc()
        print(f"\n💾 Speicherinfo:")
        print(f"   Verwendet: {mem.used/1024/1024/1024:.1f} GB")
        print(f"   Verfügbar: {mem.available/1024/1024/1024:.1f} GB")
        print(f"   Gesamt:    {mem.total/1024/1024/1024:.1f} GB")
        print(f"\n📄 Details im Logfile: ensight_clip.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
