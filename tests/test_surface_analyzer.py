"""Tests for core/surface_analyzer.py."""

from types import SimpleNamespace

import pytest

from core.surface_analyzer import (
    SurfaceInfo,
    _calculate_surface_height,
    _find_longest_edge,
)
from tests.mocks.adsk_mock import Point3D


class TestSurfaceInfo:
    """Tests for SurfaceInfo class."""

    def test_construction(self):
        """Test SurfaceInfo construction and attribute access."""
        # Create mock objects
        face = SimpleNamespace(name="test_face")
        evaluator = SimpleNamespace(name="test_evaluator")
        ref_edge = SimpleNamespace(name="test_edge")
        ref_edge_evaluator = SimpleNamespace(name="test_edge_evaluator")

        info = SurfaceInfo(
            face=face,
            evaluator=evaluator,
            u_min=0.0,
            u_max=1.0,
            v_min=-3.14,
            v_max=3.14,
            ref_edge=ref_edge,
            ref_edge_evaluator=ref_edge_evaluator,
            ref_edge_length=10.0,
            ref_edge_param_start=0.0,
            ref_edge_param_end=1.0,
            surface_height=5.0,
        )

        assert info.face == face
        assert info.evaluator == evaluator
        assert info.u_min == 0.0
        assert info.u_max == 1.0
        assert info.v_min == -3.14
        assert info.v_max == 3.14
        assert info.ref_edge == ref_edge
        assert info.ref_edge_evaluator == ref_edge_evaluator
        assert info.ref_edge_length == 10.0
        assert info.ref_edge_param_start == 0.0
        assert info.ref_edge_param_end == 1.0
        assert info.surface_height == 5.0

    def test_construction_with_different_bounds(self):
        """Test SurfaceInfo with various parametric bounds."""
        import math

        # Simulate a cylinder surface (V range close to 2π)
        info = SurfaceInfo(
            face=None,
            evaluator=None,
            u_min=0.0,
            u_max=5.0,
            v_min=-math.pi,
            v_max=math.pi,
            ref_edge=None,
            ref_edge_evaluator=None,
            ref_edge_length=31.4,  # 2πr for r=5
            ref_edge_param_start=0.0,
            ref_edge_param_end=2 * math.pi,
            surface_height=5.0,
        )

        # V range should be 2π
        v_range = info.v_max - info.v_min
        assert v_range == pytest.approx(2 * math.pi)


class TestFindLongestEdge:
    """Tests for _find_longest_edge function."""

    def _create_mock_edge(self, length):
        """Create a mock BRepEdge with given length."""
        return SimpleNamespace(length=length)

    def _create_mock_face(self, edges):
        """Create a mock BRepFace with given edges."""
        return SimpleNamespace(edges=edges)

    def test_single_edge(self):
        """Single edge should be returned."""
        edge = self._create_mock_edge(10.0)
        face = self._create_mock_face([edge])

        result = _find_longest_edge(face)
        assert result == edge

    def test_multiple_edges_finds_longest(self):
        """Should return the edge with maximum length."""
        edge1 = self._create_mock_edge(5.0)
        edge2 = self._create_mock_edge(15.0)
        edge3 = self._create_mock_edge(10.0)
        face = self._create_mock_face([edge1, edge2, edge3])

        result = _find_longest_edge(face)
        assert result == edge2
        assert result.length == 15.0

    def test_equal_lengths_returns_first(self):
        """Equal length edges should return first one found."""
        edge1 = self._create_mock_edge(10.0)
        edge2 = self._create_mock_edge(10.0)
        face = self._create_mock_face([edge1, edge2])

        result = _find_longest_edge(face)
        assert result == edge1

    def test_no_edges(self):
        """Empty edge list should return None."""
        face = self._create_mock_face([])

        result = _find_longest_edge(face)
        assert result is None

    def test_many_edges(self):
        """Should correctly find longest among many edges."""
        edges = [
            self._create_mock_edge(1.0),
            self._create_mock_edge(2.5),
            self._create_mock_edge(0.5),
            self._create_mock_edge(100.0),  # longest
            self._create_mock_edge(3.0),
            self._create_mock_edge(7.5),
        ]
        face = self._create_mock_face(edges)

        result = _find_longest_edge(face)
        assert result.length == 100.0

    def test_very_small_edges(self):
        """Should handle very small edge lengths."""
        edge1 = self._create_mock_edge(0.0001)
        edge2 = self._create_mock_edge(0.0002)
        face = self._create_mock_face([edge1, edge2])

        result = _find_longest_edge(face)
        assert result == edge2


class TestCalculateSurfaceHeight:
    """Tests for _calculate_surface_height function."""

    def _create_mock_evaluator(self, point_generator):
        """Create a mock evaluator that returns points from a generator function.

        Args:
            point_generator: A function(u, v) that returns (x, y, z) tuple
        """

        def get_point_at_parameter(uv_point):
            x, y, z = point_generator(uv_point.x, uv_point.y)
            return True, Point3D.create(x, y, z)

        return SimpleNamespace(getPointAtParameter=get_point_at_parameter)

    def test_flat_surface(self):
        """Flat surface (all points at same z) should have near-zero height variation."""

        # All points at z=0, x=u, y=v
        def flat_surface(u, v):
            return (u, v, 0)

        evaluator = self._create_mock_evaluator(flat_surface)

        # Calculate height along v direction at u=0, from v=0 to v=10
        result = _calculate_surface_height(
            evaluator, u=0, v_min=0, v_max=10, samples=10
        )

        # For flat surface along V, height should be 10 (just the v distance)
        assert result == pytest.approx(10.0, rel=0.01)

    def test_linear_height_cylinder(self):
        """Cylindrical surface height should match physical distance."""
        import math

        # Simulate cylinder: x=cos(v), y=sin(v), z=u
        def cylinder_surface(u, v):
            return (math.cos(v), math.sin(v), u)

        evaluator = self._create_mock_evaluator(cylinder_surface)

        # Height along u direction (the axis)
        # At v=0 (constant), from u=0 to u=5
        # Points go from (1,0,0) to (1,0,5), so height should be 5
        result = _calculate_surface_height(evaluator, u=0, v_min=0, v_max=5, samples=10)

        # On a cylinder, moving along V at fixed U traces an arc
        # Arc length = radius * angle, with radius=1 and angle=5
        expected_arc_length = 5.0  # For our setup
        assert result == pytest.approx(expected_arc_length, rel=0.05)

    def test_increasing_height(self):
        """Surface that linearly increases in Z should report correct height."""

        # Surface where z = v (linear height)
        def sloped_surface(u, v):
            return (u, 0, v)

        evaluator = self._create_mock_evaluator(sloped_surface)

        # From v=0 to v=5, the Z goes from 0 to 5
        # Points: (0,0,0), (0,0,0.5), ..., (0,0,5)
        # Distance between consecutive points is 0.5 each
        result = _calculate_surface_height(evaluator, u=0, v_min=0, v_max=5, samples=10)

        # Total height should be 5
        assert result == pytest.approx(5.0, rel=0.01)

    def test_custom_samples(self):
        """Different sample counts should still give approximately correct height."""

        def linear_surface(u, v):
            return (0, 0, v)

        evaluator = self._create_mock_evaluator(linear_surface)

        # Test with different sample counts
        result_10 = _calculate_surface_height(
            evaluator, u=0, v_min=0, v_max=10, samples=10
        )
        result_100 = _calculate_surface_height(
            evaluator, u=0, v_min=0, v_max=10, samples=100
        )

        # Both should be approximately 10
        assert result_10 == pytest.approx(10.0, rel=0.1)
        assert result_100 == pytest.approx(10.0, rel=0.01)

    def test_zero_height_range(self):
        """Zero v range should return 0 height."""

        def any_surface(u, v):
            return (u, v, v)

        evaluator = self._create_mock_evaluator(any_surface)

        result = _calculate_surface_height(evaluator, u=0, v_min=5, v_max=5, samples=10)

        # All points are the same, so total distance is 0
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_negative_v_range(self):
        """Negative to positive v range should work correctly."""

        def linear_surface(u, v):
            return (0, 0, v)

        evaluator = self._create_mock_evaluator(linear_surface)

        # From v=-5 to v=5, height should be 10
        result = _calculate_surface_height(
            evaluator, u=0, v_min=-5, v_max=5, samples=10
        )

        assert result == pytest.approx(10.0, rel=0.01)
