# Sketch Parser - Extract 2D points from sketch geometry

import math


class PointSequence:
    """A sequence of 2D points representing a curve."""

    def __init__(self, points, is_closed, source_type):
        self.points = points  # List of (x, y) tuples
        self.is_closed = is_closed
        self.source_type = source_type  # Original geometry type for reference


def parse(sketch_curves):
    """
    Parse sketch entities into point sequences.

    Args:
        sketch_curves: List of sketch entities (curves, points)

    Returns:
        List of PointSequence objects, one per input curve.

    """
    sequences = []

    for entity in sketch_curves:
        obj_type = entity.objectType

        if obj_type == "adsk::fusion::SketchFittedSpline":
            seq = _parse_fitted_spline(entity)
        elif obj_type == "adsk::fusion::SketchLine":
            seq = _parse_line(entity)
        elif obj_type == "adsk::fusion::SketchArc":
            seq = _parse_arc(entity)
        elif obj_type == "adsk::fusion::SketchCircle":
            seq = _parse_circle(entity)
        elif obj_type == "adsk::fusion::SketchPoint":
            seq = _parse_point(entity)
        elif obj_type == "adsk::fusion::SketchFixedSpline":
            seq = _parse_fixed_spline(entity)
        else:
            # Skip unsupported types
            continue

        if seq is not None:
            sequences.append(seq)

    return sequences


def _parse_fitted_spline(spline):
    """Extract fit points from a fitted spline."""
    points = []
    fit_points = spline.fitPoints

    for i in range(fit_points.count):
        pt = fit_points.item(i).geometry
        points.append((pt.x, pt.y))

    return PointSequence(points, spline.isClosed, "SketchFittedSpline")


def _parse_fixed_spline(spline):
    """Sample points along a fixed spline."""
    points = []
    geometry = spline.geometry  # NurbsCurve3D

    evaluator = geometry.evaluator
    _, param_start, param_end = evaluator.getParameterExtents()

    # Sample along the spline
    num_samples = 20
    param_step = (param_end - param_start) / num_samples

    for i in range(num_samples + 1):
        param = param_start + i * param_step
        _, pt = evaluator.getPointAtParameter(param)
        points.append((pt.x, pt.y))

    return PointSequence(points, spline.isClosed, "SketchFixedSpline")


def _parse_line(line, num_samples=20):
    """Sample points along a line for proper surface wrapping."""
    start = line.startSketchPoint.geometry
    end = line.endSketchPoint.geometry

    # Sample multiple points along the line so it wraps correctly
    points = []
    for i in range(num_samples + 1):
        t = i / num_samples
        x = start.x + t * (end.x - start.x)
        y = start.y + t * (end.y - start.y)
        points.append((x, y))

    return PointSequence(points, False, "SketchLine")


def _parse_arc(arc):
    """Sample points along an arc."""
    points = []
    geometry = arc.geometry  # Arc3D

    evaluator = geometry.evaluator
    _, param_start, param_end = evaluator.getParameterExtents()

    # Sample based on arc length
    num_samples = max(10, int(abs(param_end - param_start) * 10))
    param_step = (param_end - param_start) / num_samples

    for i in range(num_samples + 1):
        param = param_start + i * param_step
        _, pt = evaluator.getPointAtParameter(param)
        points.append((pt.x, pt.y))

    return PointSequence(points, False, "SketchArc")


def _parse_circle(circle):
    """Sample points around a circle."""
    points = []
    center = circle.centerSketchPoint.geometry
    radius = circle.radius

    num_samples = 36  # Every 10 degrees

    for i in range(num_samples):
        angle = 2 * math.pi * i / num_samples
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        points.append((x, y))

    return PointSequence(points, True, "SketchCircle")


def _parse_point(point):
    """Extract a single point."""
    pt = point.geometry

    return PointSequence([(pt.x, pt.y)], False, "SketchPoint")
