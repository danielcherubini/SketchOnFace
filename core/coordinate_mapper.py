# Coordinate Mapper - Map 2D sketch coordinates to 3D surface using arc-length parameterization

import adsk.core
import adsk.fusion
from dataclasses import dataclass
from typing import List, Tuple

from .surface_analyzer import SurfaceInfo
from .sketch_parser import PointSequence


@dataclass
class MappedSequence:
    """A sequence of 3D points mapped onto a surface."""
    points: List[adsk.core.Point3D]
    is_closed: bool
    source_type: str


def map_to_surface(point_sequences: List[PointSequence],
                   surface_info: SurfaceInfo,
                   scale_x: float = 1.0,
                   scale_y: float = 1.0,
                   offset: float = 0.0) -> List[MappedSequence]:
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

    for seq in point_sequences:
        points_3d = []

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
                offset
            )

            if point_3d is not None:
                points_3d.append(point_3d)

        if points_3d:
            mapped.append(MappedSequence(
                points=points_3d,
                is_closed=seq.is_closed,
                source_type=seq.source_type
            ))

    return mapped


def _get_bounds(sequences: List[PointSequence]) -> Tuple[float, float, float, float]:
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


def _map_point(x: float,
               y: float,
               surface_info: SurfaceInfo,
               total_width: float,
               total_height: float,
               offset: float) -> adsk.core.Point3D:
    """
    Map a single 2D point to 3D surface coordinates.

    Uses arc-length parameterization along the reference edge for X,
    and linear mapping along V for Y.
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
    # This is the key API call that handles non-uniform curves (ovals)
    edge_eval = surface_info.ref_edge_evaluator
    success, u_param = edge_eval.getParameterAtLength(
        surface_info.ref_edge_param_start,
        arc_length
    )

    if not success:
        # Fallback: linear interpolation
        t = arc_length / surface_info.ref_edge_length if surface_info.ref_edge_length > 0 else 0
        u_param = surface_info.ref_edge_param_start + t * (
            surface_info.ref_edge_param_end - surface_info.ref_edge_param_start
        )

    # Map Y to V parameter
    # Normalize y to [v_min, v_max]
    if total_height > 0:
        v_ratio = y / total_height
    else:
        v_ratio = 0.0

    v_ratio = max(0.0, min(v_ratio, 1.0))
    v_param = surface_info.v_min + v_ratio * (surface_info.v_max - surface_info.v_min)

    # Now we need to map edge parameter to surface U parameter
    # Get the point on the edge at this parameter
    _, edge_point = edge_eval.getPointAtParameter(u_param)

    # Find corresponding UV on the surface
    # Use the surface evaluator to get closest point parameters
    surf_eval = surface_info.evaluator
    success, uv_point = surf_eval.getParameterAtPoint(edge_point)

    if success:
        # Use the U from edge mapping, but override V with our height mapping
        uv_mapped = adsk.core.Point2D.create(uv_point.x, v_param)
    else:
        # Fallback: direct parameter mapping
        u_ratio = arc_length / surface_info.ref_edge_length if surface_info.ref_edge_length > 0 else 0
        u_mapped = surface_info.u_min + u_ratio * (surface_info.u_max - surface_info.u_min)
        uv_mapped = adsk.core.Point2D.create(u_mapped, v_param)

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
                point_3d.z + normal.z * offset
            )

    return point_3d
