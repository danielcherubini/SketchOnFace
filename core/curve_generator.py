# Curve Generator - Create 3D sketch curves from mapped points

import adsk.core
import adsk.fusion


def generate(mapped_sequences, app):
    """
    Generate 3D sketch curves from mapped point sequences.

    Args:
        mapped_sequences: List of 3D point sequences from coordinate mapper
        app: Fusion 360 application reference

    Returns:
        The created Sketch object containing the wrapped curves.

    """
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError("No active Fusion 360 design")

    root_comp = design.rootComponent

    # Create a new sketch
    # Using XY construction plane as base (sketch will contain 3D curves)
    sketch = root_comp.sketches.add(root_comp.xYConstructionPlane)
    sketch.name = "WrappedSketch"
    sketch.isComputeDeferred = True  # Defer recompute for performance

    try:
        for seq in mapped_sequences:
            if len(seq.points) == 0:
                continue

            if len(seq.points) == 1:
                # Single point
                _create_point(sketch, seq.points[0])
            elif seq.source_type == "SketchLine" and len(seq.points) == 2:
                # Line with only 2 points - create as line or arc
                _create_line_or_arc(sketch, seq.points)
            else:
                # Multiple points - create fitted spline
                _create_spline(sketch, seq.points, seq.is_closed)

    finally:
        sketch.isComputeDeferred = False  # Re-enable compute

    return sketch


def _create_point(sketch, point):
    """Create a sketch point."""
    sketch.sketchPoints.add(point)


def _create_line_or_arc(sketch, points):
    """
    Create a line or arc from two points.
    For wrapped geometry, a straight line becomes an arc on curved surfaces.
    """
    if len(points) < 2:
        return

    start = points[0]
    end = points[-1]

    # Check if points are essentially the same
    if start.distanceTo(end) < 0.0001:  # 0.1 micron tolerance
        return

    # Create as a line (the points are already on the surface)
    sketch.sketchCurves.sketchLines.addByTwoPoints(start, end)


def _create_spline(sketch, points, is_closed):
    """Create a fitted spline through the points."""
    if len(points) < 2:
        return

    # Create point collection
    point_collection = adsk.core.ObjectCollection.create()
    for pt in points:
        point_collection.add(pt)

    # Create fitted spline
    spline = sketch.sketchCurves.sketchFittedSplines.add(point_collection)

    if spline and is_closed:
        spline.isClosed = True
