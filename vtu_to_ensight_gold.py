#!/usr/bin/env python3
"""
VTU to EnSight Gold Converter
Converts VTK/VTU files to EnSight Gold format (Binary or ASCII)
"""

import sys
import struct
from pathlib import Path
import vtk
from vtk.util import numpy_support
import numpy as np
import argparse


def write_ensight_gold_geometry_binary(filename, grid):
    """
    Writes geometry in EnSight Gold BINARY format (fast!)
    """
    print(f"  📝 Schreibe Geometrie (binär): {filename}")

    with open(filename, 'wb') as f:
        # Header (C Binary format)
        f.write(b'C Binary'.ljust(80))
        f.write(b'Generated from VTU - Binary'.ljust(80))
        f.write(b'node id assign'.ljust(80))
        f.write(b'element id assign'.ljust(80))

        # Get points
        points = grid.GetPoints()
        n_points = points.GetNumberOfPoints()
        n_cells = grid.GetNumberOfCells()

        print(f"    ✓ Punkte: {n_points:,}")
        print(f"    ✓ Zellen: {n_cells:,}")

        # Part header
        f.write(b'part'.ljust(80))
        f.write(struct.pack('>i', 1))  # Part number (big-endian int)
        f.write(b'Volume'.ljust(80))

        # Write coordinates
        f.write(b'coordinates'.ljust(80))
        f.write(struct.pack('>i', n_points))

        # Extract coordinates as numpy arrays (fast!)
        coords = numpy_support.vtk_to_numpy(points.GetData())

        # Write X, Y, Z coordinates (big-endian float32)
        for dim in range(3):
            f.write(coords[:, dim].astype('>f4').tobytes())

        # Count cell types
        cell_type_counts = {}
        cell_type_lists = {}

        for i in range(n_cells):
            cell = grid.GetCell(i)
            cell_type = cell.GetCellType()

            if cell_type not in cell_type_counts:
                cell_type_counts[cell_type] = 0
                cell_type_lists[cell_type] = []

            cell_type_counts[cell_type] += 1
            cell_type_lists[cell_type].append(i)

        # Map VTK cell types to EnSight element types
        vtk_to_ensight = {
            vtk.VTK_TETRA: ('tetra4', 4),
            vtk.VTK_HEXAHEDRON: ('hexa8', 8),
            vtk.VTK_WEDGE: ('penta6', 6),
            vtk.VTK_PYRAMID: ('pyramid5', 5),
            vtk.VTK_TRIANGLE: ('tria3', 3),
            vtk.VTK_QUAD: ('quad4', 4),
        }

        # Write each cell type
        for vtk_type, count in cell_type_counts.items():
            if vtk_type in vtk_to_ensight:
                ensight_name, n_nodes = vtk_to_ensight[vtk_type]
                f.write(ensight_name.encode().ljust(80))
                f.write(struct.pack('>i', count))

                # Collect connectivity for all cells of this type
                connectivity = []
                for cell_id in cell_type_lists[vtk_type]:
                    cell = grid.GetCell(cell_id)
                    point_ids = cell.GetPointIds()
                    for j in range(n_nodes):
                        connectivity.append(point_ids.GetId(j) + 1)  # 1-based

                # Write as binary (big-endian int32)
                conn_array = np.array(connectivity, dtype='>i4')
                f.write(conn_array.tobytes())

                print(f"    ✓ {ensight_name}: {count:,} Zellen")


def write_ensight_gold_geometry(filename, grid):
    """
    Writes geometry in EnSight Gold ASCII format
    """
    print(f"  📝 Schreibe Geometrie (ASCII): {filename}")

    with open(filename, 'w') as f:
        # Header
        f.write("EnSight Gold Geometry File\n")
        f.write("Generated from VTU by vtu_to_ensight_gold.py\n")
        f.write("node id assign\n")
        f.write("element id assign\n")

        # Get points
        points = grid.GetPoints()
        n_points = points.GetNumberOfPoints()

        # Get cells
        n_cells = grid.GetNumberOfCells()

        print(f"    ✓ Punkte: {n_points:,}")
        print(f"    ✓ Zellen: {n_cells:,}")

        # Part header
        f.write("part\n")
        f.write(f"{1:>10d}\n")
        f.write("Volume\n")

        # Write coordinates
        f.write("coordinates\n")
        f.write(f"{n_points:>10d}\n")

        # Write X coordinates
        for i in range(n_points):
            point = points.GetPoint(i)
            f.write(f"{point[0]:>12.5e}\n")

        # Write Y coordinates
        for i in range(n_points):
            point = points.GetPoint(i)
            f.write(f"{point[1]:>12.5e}\n")

        # Write Z coordinates
        for i in range(n_points):
            point = points.GetPoint(i)
            f.write(f"{point[2]:>12.5e}\n")

        # Count cell types
        cell_type_counts = {}
        cell_type_lists = {}

        for i in range(n_cells):
            cell = grid.GetCell(i)
            cell_type = cell.GetCellType()

            if cell_type not in cell_type_counts:
                cell_type_counts[cell_type] = 0
                cell_type_lists[cell_type] = []

            cell_type_counts[cell_type] += 1
            cell_type_lists[cell_type].append(i)

        # Map VTK cell types to EnSight element types
        vtk_to_ensight = {
            vtk.VTK_TETRA: ('tetra4', 4),
            vtk.VTK_HEXAHEDRON: ('hexa8', 8),
            vtk.VTK_WEDGE: ('penta6', 6),
            vtk.VTK_PYRAMID: ('pyramid5', 5),
            vtk.VTK_TRIANGLE: ('tria3', 3),
            vtk.VTK_QUAD: ('quad4', 4),
        }

        # Write each cell type
        for vtk_type, count in cell_type_counts.items():
            if vtk_type in vtk_to_ensight:
                ensight_name, n_nodes = vtk_to_ensight[vtk_type]
                f.write(f"{ensight_name}\n")
                f.write(f"{count:>10d}\n")

                # Write connectivity (1-based indexing)
                for cell_id in cell_type_lists[vtk_type]:
                    cell = grid.GetCell(cell_id)
                    point_ids = cell.GetPointIds()
                    for j in range(n_nodes):
                        f.write(f"{point_ids.GetId(j) + 1:>10d}")
                        if (j + 1) % 10 == 0:
                            f.write("\n")
                    if n_nodes % 10 != 0:
                        f.write("\n")

                print(f"    ✓ {ensight_name}: {count:,} Zellen")


def write_ensight_gold_scalar_binary(filename, grid, array_name):
    """
    Writes scalar variable in EnSight Gold BINARY format (fast!)
    """
    point_data = grid.GetPointData()
    array = point_data.GetArray(array_name)

    if array is None:
        print(f"  ⚠️  Variable '{array_name}' nicht gefunden")
        return False

    n_points = array.GetNumberOfTuples()
    print(f"  📝 Schreibe Skalar (binär): {filename.name} ({n_points:,} Werte)")

    with open(filename, 'wb') as f:
        # Header
        f.write(b'C Binary'.ljust(80))
        f.write(b'part'.ljust(80))
        f.write(struct.pack('>i', 1))
        f.write(b'coordinates'.ljust(80))

        # Convert to numpy and write (big-endian float32)
        values = numpy_support.vtk_to_numpy(array)
        f.write(values.astype('>f4').tobytes())

    return True


def write_ensight_gold_scalar(filename, grid, array_name):
    """
    Writes scalar variable in EnSight Gold ASCII format
    """
    point_data = grid.GetPointData()
    array = point_data.GetArray(array_name)

    if array is None:
        print(f"  ⚠️  Variable '{array_name}' nicht gefunden")
        return False

    n_points = array.GetNumberOfTuples()

    print(f"  📝 Schreibe Skalar (ASCII): {filename.name} ({n_points:,} Werte)")

    with open(filename, 'w') as f:
        # Header
        f.write("EnSight Gold Scalar Variable\n")
        f.write("part\n")
        f.write(f"{1:>10d}\n")
        f.write("coordinates\n")

        # Write values
        for i in range(n_points):
            value = array.GetValue(i)
            f.write(f"{value:>12.5e}\n")

    return True


def write_ensight_gold_vector_binary(filename, grid, array_name):
    """
    Writes vector variable in EnSight Gold BINARY format (fast!)
    """
    point_data = grid.GetPointData()
    array = point_data.GetArray(array_name)

    if array is None:
        print(f"  ⚠️  Variable '{array_name}' nicht gefunden")
        return False

    n_points = array.GetNumberOfTuples()
    n_components = array.GetNumberOfComponents()

    if n_components != 3:
        print(f"  ⚠️  Variable '{array_name}' ist kein 3D-Vektor (Komponenten: {n_components})")
        return False

    print(f"  📝 Schreibe Vektor (binär): {filename.name} ({n_points:,} Vektoren)")

    with open(filename, 'wb') as f:
        # Header
        f.write(b'C Binary'.ljust(80))
        f.write(b'part'.ljust(80))
        f.write(struct.pack('>i', 1))
        f.write(b'coordinates'.ljust(80))

        # Convert to numpy and write X, Y, Z components (big-endian float32)
        vectors = numpy_support.vtk_to_numpy(array)
        for dim in range(3):
            f.write(vectors[:, dim].astype('>f4').tobytes())

    return True


def write_ensight_gold_vector(filename, grid, array_name):
    """
    Writes vector variable in EnSight Gold ASCII format
    """
    point_data = grid.GetPointData()
    array = point_data.GetArray(array_name)

    if array is None:
        print(f"  ⚠️  Variable '{array_name}' nicht gefunden")
        return False

    n_points = array.GetNumberOfTuples()
    n_components = array.GetNumberOfComponents()

    if n_components != 3:
        print(f"  ⚠️  Variable '{array_name}' ist kein 3D-Vektor (Komponenten: {n_components})")
        return False

    print(f"  📝 Schreibe Vektor (ASCII): {filename.name} ({n_points:,} Vektoren)")

    with open(filename, 'w') as f:
        # Header
        f.write("EnSight Gold Vector Variable\n")
        f.write("part\n")
        f.write(f"{1:>10d}\n")
        f.write("coordinates\n")

        # Write X components
        for i in range(n_points):
            value = array.GetTuple3(i)
            f.write(f"{value[0]:>12.5e}\n")

        # Write Y components
        for i in range(n_points):
            value = array.GetTuple3(i)
            f.write(f"{value[1]:>12.5e}\n")

        # Write Z components
        for i in range(n_points):
            value = array.GetTuple3(i)
            f.write(f"{value[2]:>12.5e}\n")

    return True


def write_ensight_gold_case(filename, geo_filename, variables):
    """
    Writes EnSight Gold .case file
    """
    print(f"  📝 Schreibe Case-Datei: {filename}")

    with open(filename, 'w') as f:
        f.write("FORMAT\n")
        f.write("type: ensight gold\n")
        f.write("\n")
        f.write("GEOMETRY\n")
        f.write(f"model: {geo_filename}\n")
        f.write("\n")
        f.write("VARIABLE\n")

        for var_type, var_name, var_file in variables:
            if var_type == 'scalar':
                f.write(f"scalar per node: {var_name} {var_file}\n")
            elif var_type == 'vector':
                f.write(f"vector per node: {var_name} {var_file}\n")

        f.write("\n")


def convert_vtu_to_ensight_gold(vtu_file, output_prefix, binary=True):
    """
    Converts VTU file to EnSight Gold format (Binary or ASCII)
    """
    vtu_path = Path(vtu_file)
    if not vtu_path.exists():
        print(f"❌ Fehler: VTU-Datei nicht gefunden: {vtu_file}")
        return False

    format_str = "Binary (SCHNELL)" if binary else "ASCII (langsam)"
    print(f"\n{'='*70}")
    print(f"🔄 VTU → EnSight Gold {format_str} Konverter")
    print(f"{'='*70}")
    print(f"📂 Input:  {vtu_file}")
    print(f"📂 Output: {output_prefix}.*")
    print(f"{'='*70}\n")

    # Read VTU file
    print(f"📖 Lade VTU-Datei...")
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(str(vtu_path))
    reader.Update()
    grid = reader.GetOutput()

    n_points = grid.GetNumberOfPoints()
    n_cells = grid.GetNumberOfCells()
    print(f"  ✓ {n_points:,} Punkte geladen")
    print(f"  ✓ {n_cells:,} Zellen geladen\n")

    # Get point data arrays
    point_data = grid.GetPointData()
    n_arrays = point_data.GetNumberOfArrays()

    print(f"📊 {n_arrays} Variablen gefunden:")
    variables = []

    for i in range(n_arrays):
        array = point_data.GetArray(i)
        array_name = array.GetName()
        n_components = array.GetNumberOfComponents()

        if n_components == 1:
            var_type = "Skalar"
            variables.append(('scalar', array_name, array_name))
        elif n_components == 3:
            var_type = "Vektor"
            variables.append(('vector', array_name, array_name))
        else:
            var_type = f"{n_components}D"

        print(f"  • {array_name} ({var_type})")

    print()

    # Write geometry
    geo_filename = f"{output_prefix}.geo"
    if binary:
        write_ensight_gold_geometry_binary(geo_filename, grid)
    else:
        write_ensight_gold_geometry(geo_filename, grid)
    print()

    # Write variables
    print(f"📝 Schreibe {len(variables)} Variablen...\n")
    written_vars = []

    for var_type, var_name, var_file_base in variables:
        var_filename = Path(f"{output_prefix}_{var_name}")

        if binary:
            if var_type == 'scalar':
                success = write_ensight_gold_scalar_binary(var_filename, grid, var_name)
            elif var_type == 'vector':
                success = write_ensight_gold_vector_binary(var_filename, grid, var_name)
            else:
                success = False
        else:
            if var_type == 'scalar':
                success = write_ensight_gold_scalar(var_filename, grid, var_name)
            elif var_type == 'vector':
                success = write_ensight_gold_vector(var_filename, grid, var_name)
            else:
                success = False

        if success:
            written_vars.append((var_type, var_name, var_filename.name))

    print()

    # Write case file
    case_filename = f"{output_prefix}.case"
    geo_basename = Path(geo_filename).name
    write_ensight_gold_case(case_filename, geo_basename, written_vars)

    print(f"\n{'='*70}")
    print(f"✅ KONVERTIERUNG ABGESCHLOSSEN")
    print(f"{'='*70}")
    print(f"📂 Output:")
    print(f"  • {case_filename}")
    print(f"  • {geo_filename}")
    for _, var_name, var_file in written_vars:
        print(f"  • {output_prefix}_{var_name}")
    print(f"{'='*70}\n")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='VTU to EnSight Gold Converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Binär (SCHNELL, empfohlen):
  python3 vtu_to_ensight_gold.py clipped.vtu clipped

  # ASCII (langsam, nur für Kompatibilität):
  python3 vtu_to_ensight_gold.py clipped.vtu clipped --ascii

Erstellt:
  • clipped.case
  • clipped.geo
  • clipped_<variable_name> (für jede Variable)
        """
    )

    parser.add_argument('vtu_file', help='Input VTU file')
    parser.add_argument('output_prefix', nargs='?', default=None,
                        help='Output prefix (default: <input_stem>_ensight)')
    parser.add_argument('--ascii', action='store_true',
                        help='Use ASCII format (slow, default: binary)')

    args = parser.parse_args()

    # Determine output prefix
    if args.output_prefix is None:
        output_prefix = Path(args.vtu_file).stem + "_ensight"
    else:
        output_prefix = args.output_prefix

    # Convert
    binary = not args.ascii
    success = convert_vtu_to_ensight_gold(args.vtu_file, output_prefix, binary=binary)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
