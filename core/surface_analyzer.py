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


class FaceSegment:
    """One face in a multi-face chain."""

    def __init__(self, surface_info, arc_length_start, arc_length_end):
        self.surface_info = surface_info  # SurfaceInfo for this face
        self.arc_length_start = arc_length_start  # Position in concatenated space
        self.arc_length_end = arc_length_end


class MultiFaceSurfaceInfo:
    """Container for multi-face surface chain."""

    def __init__(self, face_segments, total_arc_length, total_height):
        self.face_segments = face_segments  # List[FaceSegment]
        self.total_arc_length = total_arc_length  # Sum of all ref edge lengths
        self.total_height = total_height  # Max height across all faces
        self.is_multi_face = True


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


def _find_shared_edge(face1, face2):
    """
    Find a shared edge between two faces.

    Returns:
        The shared edge if found, None otherwise.
    """
    for edge1 in face1.edges:
        for edge2 in face2.edges:
            if edge1.entityToken == edge2.entityToken:
                return edge1
    return None


def _find_longest_chain(adjacency, faces):
    """
    Find the longest chain of connected faces using DFS.

    For open chains (faces with degree 1), starts from an endpoint.
    For closed loops, starts from any face.

    Args:
        adjacency: Dict mapping face token -> list of connected face tokens
        faces: List of Face objects

    Returns:
        Ordered list of face tokens representing the chain
    """
    if not faces:
        return []

    # Build token-to-face mapping
    token_to_face = {face.entityToken: face for face in faces}

    # Find starting face (prefer degree-1 for open chains)
    start_token = None
    for token in adjacency:
        if len(adjacency[token]) == 1:
            start_token = token
            break

    # If no degree-1 face found (closed loop), start from first face
    if start_token is None:
        start_token = faces[0].entityToken

    # DFS to build chain
    visited = set()
    chain = []

    def dfs(token):
        visited.add(token)
        chain.append(token)

        for neighbor in adjacency.get(token, []):
            if neighbor not in visited:
                dfs(neighbor)

    dfs(start_token)
    return chain


def build_face_chain(faces, ref_edges=None):
    """
    Build a multi-face surface chain from connected faces.

    Args:
        faces: List of BRepFace objects to chain together
        ref_edges: Optional dict mapping first face -> reference edge for wrap direction

    Returns:
        MultiFaceSurfaceInfo with concatenated arc-length space

    Raises:
        RuntimeError: If faces are not connected or form invalid topology
    """
    if not faces:
        raise RuntimeError("No faces provided")

    if len(faces) == 1:
        # Single face - use standard analyze
        ref_edge = None
        if ref_edges and faces[0] in ref_edges:
            ref_edge = ref_edges[faces[0]]
        return analyze(faces[0], ref_edge)

    # Build adjacency graph
    adjacency = {face.entityToken: [] for face in faces}
    face_tokens = {face.entityToken for face in faces}

    for i, face1 in enumerate(faces):
        for face2 in faces[i+1:]:
            shared_edge = _find_shared_edge(face1, face2)
            if shared_edge:
                adjacency[face1.entityToken].append(face2.entityToken)
                adjacency[face2.entityToken].append(face1.entityToken)

    # Validate connectivity
    for token, neighbors in adjacency.items():
        if len(neighbors) == 0:
            raise RuntimeError(
                "Selected faces are not all connected. Please select adjacent faces that share edges."
            )
        if len(neighbors) > 2:
            raise RuntimeError(
                "Selected faces form a branch topology (T-junction). "
                "Please select faces that form a simple chain or loop."
            )

    # Find chain ordering
    chain_tokens = _find_longest_chain(adjacency, faces)
    token_to_face = {face.entityToken: face for face in faces}
    ordered_faces = [token_to_face[token] for token in chain_tokens]

    # Analyze each face individually
    face_segments = []
    cumulative_arc_length = 0.0
    max_height = 0.0

    for i, face in enumerate(ordered_faces):
        # Use provided ref_edge for first face only
        ref_edge = None
        if i == 0 and ref_edges and face in ref_edges:
            ref_edge = ref_edges[face]

        surface_info = analyze(face, ref_edge)

        # Create segment with cumulative arc-length bounds
        arc_length_start = cumulative_arc_length
        arc_length_end = cumulative_arc_length + surface_info.ref_edge_length

        segment = FaceSegment(surface_info, arc_length_start, arc_length_end)
        face_segments.append(segment)

        cumulative_arc_length = arc_length_end
        max_height = max(max_height, surface_info.surface_height)

    return MultiFaceSurfaceInfo(face_segments, cumulative_arc_length, max_height)
