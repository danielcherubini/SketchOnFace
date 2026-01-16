# Coordinate Mapper - Map 2D sketch coordinates to 3D surface using arc-length parameterization

import adsk.core
import adsk.fusion


class MappedSequence:
    """A sequence of 3D points mapped onto a surface."""

    def __init__(self, points, is_closed, source_type):
        self.points = points  # List of Point3D
        self.is_closed = is_closed
        self.source_type = source_type


def map_to_surface(
    point_sequences, surface_info, scale_x=1.0, scale_y=1.0, offset=0.0, debug_ui=None
):
    """
    Map 2D point sequences onto a 3D surface.

    Args:
        point_sequences: List of 2D point sequences from sketch parser
        surface_info: Surface analysis results
        scale_x: Scale factor for X (wrap) direction
        scale_y: Scale factor for Y (height) direction
        offset: Distance to offset from surface along normal

    Returns:
        List of MappedSequence with 3D points.

    """
    mapped = []

    # Get bounding box of all input points to normalize coordinates
    x_min, x_max, y_min, y_max = _get_bounds(point_sequences)
    x_range = x_max - x_min if x_max != x_min else 1.0
    y_range = y_max - y_min if y_max != y_min else 1.0

    if debug_ui:
        debug_ui.messageBox(
            f"Bounds: x=[{x_min:.2f}, {x_max:.2f}], y=[{y_min:.2f}, {y_max:.2f}]\nRange: {x_range:.2f} x {y_range:.2f}\nEdge length: {surface_info.ref_edge_length:.2f}"
        )

    for seq in point_sequences:
        points_3d = []

        if debug_ui:
            debug_ui.messageBox(
                f"Sequence type: {seq.source_type}\nPoints: {len(seq.points)}\nFirst point: {seq.points[0] if seq.points else 'none'}"
            )

        for x, y in seq.points:
            # Apply scaling
            x_scaled = (x - x_min) * scale_x
            y_scaled = (y - y_min) * scale_y

            # Map to surface
            point_3d = _map_point(
                x_scaled,
                y_scaled,
                surface_info,
                x_range * scale_x,
                y_range * scale_y,
                offset,
                debug_ui,
            )

            if point_3d is not None:
                points_3d.append(point_3d)

        if debug_ui:
            debug_ui.messageBox(f"Mapped {len(points_3d)} of {len(seq.points)} points")

        if points_3d:
            mapped.append(MappedSequence(points_3d, seq.is_closed, seq.source_type))

    return mapped


def _get_bounds(sequences):
    """Get bounding box of all points in sequences."""
    x_coords = []
    y_coords = []

    for seq in sequences:
        for x, y in seq.points:
            x_coords.append(x)
            y_coords.append(y)

    if not x_coords:
        return 0.0, 1.0, 0.0, 1.0

    return min(x_coords), max(x_coords), min(y_coords), max(y_coords)


def _map_point(x, y, surface_info, total_width, total_height, offset, debug_ui=None):
    """
    Map a single 2D point to 3D surface coordinates.

    Uses arc-length parameterization along the reference edge for X (wrap direction),
    and linear mapping for Y (height direction).

    Note: Surface UV parameterization varies - V might be circumference, U might be height.
    We detect this by checking which parameter range matches the edge length.
    """
    # Calculate arc length for this X position
    # Normalize x to [0, edge_length]
    if total_width > 0:
        arc_length = (x / total_width) * surface_info.ref_edge_length
    else:
        arc_length = 0.0

    # Clamp to valid range
    arc_length = max(0.0, min(arc_length, surface_info.ref_edge_length))

    # Use arc-length parameterization to find position along edge
    edge_eval = surface_info.ref_edge_evaluator
    success, edge_param = edge_eval.getParameterAtLength(
        surface_info.ref_edge_param_start, arc_length
    )

    if not success:
        if debug_ui:
            debug_ui.messageBox(
                f"getParameterAtLength failed for arc_length={arc_length}"
            )
        # Fallback: linear interpolation
        t = (
            arc_length / surface_info.ref_edge_length
            if surface_info.ref_edge_length > 0
            else 0
        )
        edge_param = surface_info.ref_edge_param_start + t * (
            surface_info.ref_edge_param_end - surface_info.ref_edge_param_start
        )

    # Get the point on the edge at this parameter
    _, edge_point = edge_eval.getPointAtParameter(edge_param)

    # Find corresponding UV on the surface for this edge point
    surf_eval = surface_info.evaluator
    success, uv_at_edge = surf_eval.getParameterAtPoint(edge_point)

    if not success:
        return None

    # Determine which surface parameter (U or V) corresponds to the wrap direction
    # by checking which one varies along the edge
    # The parameter that stays constant is the height direction

    # Calculate height ratio
    if total_height > 0:
        height_ratio = y / total_height
    else:
        height_ratio = 0.0
    height_ratio = max(0.0, min(height_ratio, 1.0))

    # Check if V range looks like circumference (roughly 2*pi range like -pi to pi)
    v_range = surface_info.v_max - surface_info.v_min
    u_range = surface_info.u_max - surface_info.u_min

    # If V range is close to 2*pi (~6.28), V is circumference, U is height
    # Otherwise assume U is circumference, V is height
    import math

    if abs(v_range - 2 * math.pi) < 1.0:
        # V is circumference (wrap), U is height
        # Use V from edge mapping (wrap position), map Y to U (height)
        u_param = surface_info.u_min + height_ratio * u_range
        v_param = uv_at_edge.y  # V from edge = wrap position
    else:
        # Standard: U is circumference (wrap), V is height
        u_param = uv_at_edge.x  # U from edge = wrap position
        v_param = surface_info.v_min + height_ratio * v_range

    uv_mapped = adsk.core.Point2D.create(u_param, v_param)

    # Get 3D point on surface
    success, point_3d = surf_eval.getPointAtParameter(uv_mapped)

    if not success:
        return None

    # Apply offset along surface normal if specified
    if offset != 0.0:
        success, normal = surf_eval.getNormalAtParameter(uv_mapped)
        if success:
            point_3d = adsk.core.Point3D.create(
                point_3d.x + normal.x * offset,
                point_3d.y + normal.y * offset,
                point_3d.z + normal.z * offset,
            )

    return point_3d
