#!/usr/bin/env python3
"""
EnSight File Clipping Tool
Clips both geometry and flow variables from an EnSight dataset
"""

import vtk
import numpy as np
import os
import sys
from pathlib import Path


class EnSightClipper:
    """Class to handle EnSight file clipping operations"""

    def __init__(self, case_file):
        """
        Initialize the EnSight clipper

        Args:
            case_file: Path to the EnSight .case file
        """
        self.case_file = case_file
        self.reader = None
        self.clipped_data = None

    def read_ensight(self):
        """Read EnSight data"""
        print(f"Reading EnSight file: {self.case_file}")

        # Create EnSight reader
        self.reader = vtk.vtkGenericEnSightReader()
        self.reader.SetCaseFileName(self.case_file)
        self.reader.Update()

        print(f"Successfully loaded EnSight case file")
        output = self.reader.GetOutput()

        # Get information about the data
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
        print(f"Clipping with plane: origin={origin}, normal={normal}")

        # Create plane
        plane = vtk.vtkPlane()
        plane.SetOrigin(origin)
        plane.SetNormal(normal)

        # Get the output and handle multiblock
        output = self.reader.GetOutput()

        # For multiblock datasets, use vtkMultiBlockDataGroupFilter
        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            # Merge multiblock into single dataset
            merger = vtk.vtkMultiBlockDataGroupFilter()
            merger.SetInputConnection(self.reader.GetOutputPort())
            merger.Update()

            # Extract merged geometry
            extract = vtk.vtkCompositeDataGeometryFilter()
            extract.SetInputConnection(merger.GetOutputPort())
            extract.Update()

            # Create clipper
            clipper = vtk.vtkClipDataSet()
            clipper.SetInputConnection(extract.GetOutputPort())
            clipper.SetClipFunction(plane)
            clipper.SetInsideOut(invert)
            clipper.Update()
        else:
            # Create clipper for single block
            clipper = vtk.vtkClipDataSet()
            clipper.SetInputConnection(self.reader.GetOutputPort())
            clipper.SetClipFunction(plane)
            clipper.SetInsideOut(invert)
            clipper.Update()

        self.clipped_data = clipper.GetOutput()
        print(f"Clipping complete")

        return self.clipped_data

    def clip_with_box(self, bounds):
        """
        Clip data with a box

        Args:
            bounds: Box bounds [xmin, xmax, ymin, ymax, zmin, zmax]
        """
        print(f"Clipping with box: bounds={bounds}")

        # Create box implicit function
        box = vtk.vtkBox()
        box.SetBounds(bounds)

        # Get the output and handle multiblock
        output = self.reader.GetOutput()

        # For multiblock datasets, merge first
        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            # Merge multiblock into single dataset
            merger = vtk.vtkMultiBlockDataGroupFilter()
            merger.SetInputConnection(self.reader.GetOutputPort())
            merger.Update()

            # Extract merged geometry
            extract = vtk.vtkCompositeDataGeometryFilter()
            extract.SetInputConnection(merger.GetOutputPort())
            extract.Update()

            # Create clipper
            clipper = vtk.vtkClipDataSet()
            clipper.SetInputConnection(extract.GetOutputPort())
            clipper.SetClipFunction(box)
            clipper.SetInsideOut(True)  # Keep inside the box
            clipper.Update()
        else:
            # Create clipper for single block
            clipper = vtk.vtkClipDataSet()
            clipper.SetInputConnection(self.reader.GetOutputPort())
            clipper.SetClipFunction(box)
            clipper.SetInsideOut(True)  # Keep inside the box
            clipper.Update()

        self.clipped_data = clipper.GetOutput()
        print(f"Clipping complete")

        return self.clipped_data

    def clip_with_sphere(self, center, radius):
        """
        Clip data with a sphere

        Args:
            center: Sphere center [x, y, z]
            radius: Sphere radius
        """
        print(f"Clipping with sphere: center={center}, radius={radius}")

        # Create sphere implicit function
        sphere = vtk.vtkSphere()
        sphere.SetCenter(center)
        sphere.SetRadius(radius)

        # Get the output and handle multiblock
        output = self.reader.GetOutput()

        # For multiblock datasets, merge first
        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            # Merge multiblock into single dataset
            merger = vtk.vtkMultiBlockDataGroupFilter()
            merger.SetInputConnection(self.reader.GetOutputPort())
            merger.Update()

            # Extract merged geometry
            extract = vtk.vtkCompositeDataGeometryFilter()
            extract.SetInputConnection(merger.GetOutputPort())
            extract.Update()

            # Create clipper
            clipper = vtk.vtkClipDataSet()
            clipper.SetInputConnection(extract.GetOutputPort())
            clipper.SetClipFunction(sphere)
            clipper.SetInsideOut(True)  # Keep inside the sphere
            clipper.Update()
        else:
            # Create clipper for single block
            clipper = vtk.vtkClipDataSet()
            clipper.SetInputConnection(self.reader.GetOutputPort())
            clipper.SetClipFunction(sphere)
            clipper.SetInsideOut(True)  # Keep inside the sphere
            clipper.Update()

        self.clipped_data = clipper.GetOutput()
        print(f"Clipping complete")

        return self.clipped_data

    def write_ensight(self, output_dir, base_name="clipped"):
        """
        Write clipped data to EnSight format

        Args:
            output_dir: Output directory
            base_name: Base name for output files
        """
        if self.clipped_data is None:
            raise ValueError("No clipped data available. Run a clip operation first.")

        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"Writing clipped EnSight data to: {output_dir}")

        # Create EnSight writer
        writer = vtk.vtkEnSightWriter()
        writer.SetInputData(self.clipped_data)
        writer.SetFileName(str(output_path / f"{base_name}.case"))
        writer.SetPath(str(output_path))
        writer.SetBaseName(base_name)
        writer.Write()

        print(f"Successfully wrote clipped EnSight files")
        print(f"Case file: {output_path / f'{base_name}.case'}")

    def get_bounds(self):
        """Get bounds of the original dataset"""
        if self.reader is None:
            self.read_ensight()

        output = self.reader.GetOutput()

        # Handle multiblock datasets
        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            # Get bounds from first block
            block = output.GetBlock(0)
            bounds = block.GetBounds()
        else:
            bounds = [0] * 6
            output.GetBounds(bounds)

        print(f"Dataset bounds: {bounds}")
        return bounds

    def get_point_arrays(self):
        """Get list of point data arrays (flow variables)"""
        if self.reader is None:
            self.read_ensight()

        output = self.reader.GetOutput()

        # Handle multiblock datasets
        if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
            point_data = output.GetBlock(0).GetPointData()
        else:
            point_data = output.GetPointData()

        arrays = []
        for i in range(point_data.GetNumberOfArrays()):
            array_name = point_data.GetArrayName(i)
            arrays.append(array_name)

        print(f"Point data arrays: {arrays}")
        return arrays


def main():
    """Main function - clips Kanalstroemung dataset"""

    # Configuration
    print("=" * 60)
    print("EnSight File Clipping Tool - Kanalstroemung")
    print("=" * 60)

    # Default paths
    input_dir = Path(__file__).parent / "input" / "Kanalströmung"
    case_file = input_dir / "Kanalstroemung.encas"
    output_dir = Path(__file__).parent / "output"

    # Check if case file exists
    if not case_file.exists():
        print(f"\nError: Case file not found: {case_file}")
        print(f"Please ensure the file exists in: {input_dir}")
        return

    print(f"\nInput:  {case_file}")
    print(f"Output: {output_dir}")

    # Create clipper instance
    clipper = EnSightClipper(str(case_file))

    # Read data and get information
    clipper.read_ensight()
    bounds = clipper.get_bounds()
    arrays = clipper.get_point_arrays()

    print("\n" + "=" * 60)
    print("Clipping Configuration")
    print("=" * 60)

    # Example 1: Clip with a plane (active by default)
    # Modify these parameters according to your needs
    origin = [0.0, 0.0, 0.0]
    normal = [1.0, 0.0, 0.0]
    print(f"Using plane clip: origin={origin}, normal={normal}")
    clipper.clip_with_plane(origin, normal, invert=False)

    # Example 2: Clip with a box
    # Uncomment and modify to use box clipping instead
    # xmin, xmax, ymin, ymax, zmin, zmax = bounds
    # box_bounds = [xmin, xmax/2, ymin, ymax, zmin, zmax]
    # print(f"Using box clip: bounds={box_bounds}")
    # clipper.clip_with_box(box_bounds)

    # Example 3: Clip with a sphere
    # Uncomment and modify to use sphere clipping instead
    # center = [0.0, 0.0, 0.0]
    # radius = 1.0
    # print(f"Using sphere clip: center={center}, radius={radius}")
    # clipper.clip_with_sphere(center, radius)

    # Write clipped data
    clipper.write_ensight(str(output_dir), "Kanalstroemung_clipped")

    print("\n" + "=" * 60)
    print("Clipping completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
