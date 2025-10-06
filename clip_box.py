#!/usr/bin/env python3
"""
EnSight Box Clipping Tool - CLI Version
"""

import sys
from pathlib import Path
from ensight_clip import EnSightClipper

def main():
    if len(sys.argv) != 8:
        print("Usage: python3 clip_box.py <input.encas> <xmin> <xmax> <ymin> <ymax> <zmin> <zmax>")
        print("Example: python3 clip_box.py input/Kanalströmung/Kanalstroemung.encas -0.025 0.025 -0.025 0.025 0.0 0.5")
        sys.exit(1)

    input_file = sys.argv[1]
    box_bounds = [float(x) for x in sys.argv[2:8]]

    print(f"Input: {input_file}")
    print(f"Box bounds: {box_bounds}")

    # Create clipper
    clipper = EnSightClipper(input_file)
    clipper.read_ensight()

    # Clip with box
    clipper.clip_with_box(box_bounds)

    # Write output
    output_dir = Path(__file__).parent / "output"
    clipper.write_ensight(str(output_dir), "clipped_box")

    print("Done!")

if __name__ == "__main__":
    main()
