# Curve Generator - Create 3D curves from mapped points (sketch or wire body)

import adsk.core
import adsk.fusion

# Geometric tolerance for point coincidence detection (in cm)
POINT_COINCIDENCE_TOLERANCE = 0.0001  # 0.1 micron


def generate_wire_body(mapped_sequences, app):
    """
    Generate wire body (BRepBody) from mapped point sequences.

    Uses TemporaryBRepManager to create 3D curve geometry, then converts to wire body.
    This allows using BaseFeature.updateBody() for in-place updates instead of delete/recreate.

    Args:
        mapped_sequences: List of 3D point sequences from coordinate mapper
        app: Fusion 360 application reference

    Returns:
        BRepBody wire body containing the wrapped curves, or None if no valid curves.
    """
    # Create 3D curve geometry objects
    curves = []

    for seq in mapped_sequences:
        if len(seq.points) == 0:
            continue

        # Create curve geometry based on point count and type
        if len(seq.points) == 1:
            # Single points can't be part of wire bodies - skip them
            continue
        elif len(seq.points) == 2:
            # Create Line3D from two points
            curve = _create_line_geometry(seq.points)
            if curve:
                curves.append(curve)
        else:
            # Create NurbsCurve3D (spline) from multiple points
            curve = _create_spline_geometry(seq.points, seq.is_closed)
            if curve:
                curves.append(curve)

    if not curves:
        return None

    # Create wire body from curves using TemporaryBRepManager
    temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()
    wire_body, edge_map = temp_brep_mgr.createWireFromCurves(curves)

    return wire_body


def _create_line_geometry(points):
    """Create a Line3D geometry object from two points."""
    if len(points) < 2:
        return None

    start = points[0]
    end = points[-1]

    # Check if points are essentially the same
    if start.distanceTo(end) < POINT_COINCIDENCE_TOLERANCE:
        return None

    return adsk.core.Line3D.create(start, end)


def _create_spline_geometry(points, is_closed):
    """Create a NurbsCurve3D (spline) geometry object from points."""
    if len(points) < 2:
        return None

    # For wire bodies, we need to create a temporary NurbsCurve3D
    # The best way is to fit through the points using control points
    try:
        # Convert points to arrays for NURBS curve creation
        # Use degree 3 (cubic) spline
        degree = min(3, len(points) - 1)  # Degree must be less than number of points

        # Create control points and knots for NURBS curve
        # For a simple fit through points, use the points themselves as control points
        control_points = []
        for pt in points:
            control_points.append(pt)

        # Generate uniform knot vector
        # For degree d and n+1 control points, need n+d+2 knots
        num_control_points = len(control_points)
        num_knots = num_control_points + degree + 1

        knots = []
        for i in range(num_knots):
            if i <= degree:
                knots.append(0.0)
            elif i >= num_knots - degree - 1:
                knots.append(1.0)
            else:
                knots.append((i - degree) / (num_knots - 2 * degree - 1))

        # Create NURBS curve using createNonRational
        nurbs_curve = adsk.core.NurbsCurve3D.createNonRational(
            control_points, degree, knots, is_closed
        )
        return nurbs_curve
    except Exception:
        return None


def generate(mapped_sequences, app, existing_sketch=None):
    """
    Generate 3D sketch curves from mapped point sequences.

    Args:
        mapped_sequences: List of 3D point sequences from coordinate mapper
        app: Fusion 360 application reference
        existing_sketch: Optional existing sketch to update in place (preserves downstream references)

    Returns:
        The created or updated Sketch object containing the wrapped curves.

    """
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError("No active Fusion 360 design")

    root_comp = design.rootComponent

    if existing_sketch:
        # Update existing sketch in place to preserve downstream references
        sketch = existing_sketch
        _clear_sketch(sketch)
    else:
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


def _clear_sketch(sketch):
    """
    Clear all geometry from a sketch while preserving the sketch itself.
    This allows updating a sketch in place to maintain downstream references.
    """
    # Delete all sketch curves (lines, arcs, splines, etc.)
    # Must iterate in reverse since we're deleting
    curves = sketch.sketchCurves
    for i in range(curves.count - 1, -1, -1):
        try:
            curves.item(i).deleteMe()
        except Exception:
            pass  # Some curves may be constrained or already deleted

    # Delete all sketch points (except origin-related points which can't be deleted)
    points = sketch.sketchPoints
    for i in range(points.count - 1, -1, -1):
        try:
            point = points.item(i)
            # Skip the origin point
            if not point.isFixed:
                point.deleteMe()
        except Exception:
            pass  # Some points may be constrained or already deleted


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
    if start.distanceTo(end) < POINT_COINCIDENCE_TOLERANCE:
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
