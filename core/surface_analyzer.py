# Surface Analyzer - Extract surface properties for coordinate mapping

import adsk.core
import adsk.fusion

# Surface height calculation sampling resolution
DEFAULT_HEIGHT_SAMPLES = (
    10  # Number of samples along V direction for height calculation
)


class SurfaceInfo:
    """Container for analyzed surface properties."""

    def __init__(
        self,
        face,
        evaluator,
        u_min,
        u_max,
        v_min,
        v_max,
        ref_edge,
        ref_edge_evaluator,
        ref_edge_length,
        ref_edge_param_start,
        ref_edge_param_end,
        surface_height,
    ):
        self.face = face
        self.evaluator = evaluator
        self.u_min = u_min
        self.u_max = u_max
        self.v_min = v_min
        self.v_max = v_max
        self.ref_edge = ref_edge
        self.ref_edge_evaluator = ref_edge_evaluator
        self.ref_edge_length = ref_edge_length
        self.ref_edge_param_start = ref_edge_param_start
        self.ref_edge_param_end = ref_edge_param_end
        self.surface_height = surface_height  # Physical height in V direction


def analyze(face, ref_edge=None):
    """
    Analyze a surface face and extract properties needed for coordinate mapping.

    Args:
        face: The BRepFace to analyze
        ref_edge: Optional reference edge for wrap direction. Auto-detects longest if None.

    Returns:
        SurfaceInfo with surface evaluator, bounds, and reference edge info.

    """
    evaluator = face.evaluator

    # Get parametric bounds
    try:
        param_range = evaluator.parametricRange()
    except Exception as e:
        raise RuntimeError(
            f"Failed to get parametric range from face. "
            f"The selected face may not be valid for wrapping. Error: {e}"
        )
    u_min = param_range.minPoint.x
    u_max = param_range.maxPoint.x
    v_min = param_range.minPoint.y
    v_max = param_range.maxPoint.y

    # Find reference edge (auto-detect longest if not specified)
    if ref_edge is None:
        ref_edge = _find_longest_edge(face)

    # Get edge evaluator and properties
    ref_edge_evaluator = ref_edge.evaluator
    _, param_start, param_end = ref_edge_evaluator.getParameterExtents()

    # Use edge.length property for more accurate length (in cm)
    ref_edge_length = ref_edge.length

    # Calculate physical surface height
    # Sample at u_min edge from v_min to v_max
    surface_height = _calculate_surface_height(evaluator, u_min, v_min, v_max)

    return SurfaceInfo(
        face=face,
        evaluator=evaluator,
        u_min=u_min,
        u_max=u_max,
        v_min=v_min,
        v_max=v_max,
        ref_edge=ref_edge,
        ref_edge_evaluator=ref_edge_evaluator,
        ref_edge_length=ref_edge_length,
        ref_edge_param_start=param_start,
        ref_edge_param_end=param_end,
        surface_height=surface_height,
    )


def _find_longest_edge(face):
    """Find the longest edge of the face for reference direction."""
    longest_edge = None
    max_length = 0.0

    for edge in face.edges:
        # Use edge.length property for accurate length
        length = edge.length

        if length > max_length:
            max_length = length
            longest_edge = edge

    return longest_edge


def _calculate_surface_height(
    evaluator, u, v_min, v_max, samples=DEFAULT_HEIGHT_SAMPLES
):
    """
    Calculate physical height of surface along V direction.
    Uses sampling to handle curved surfaces.
    """
    total_length = 0.0
    v_step = (v_max - v_min) / samples

    prev_point = None
    for i in range(samples + 1):
        v = v_min + i * v_step
        uv_point = adsk.core.Point2D.create(u, v)
        _, point = evaluator.getPointAtParameter(uv_point)

        if prev_point is not None:
            # Add distance between consecutive points
            total_length += prev_point.distanceTo(point)

        prev_point = point

    return total_length
