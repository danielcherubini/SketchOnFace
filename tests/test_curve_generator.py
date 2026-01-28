"""Tests for core/curve_generator.py."""

import pytest

from core.curve_generator import (
    _create_line_geometry,
    _create_spline_geometry,
)


class TestCreateLineGeometry:
    """Tests for _create_line_geometry function."""

    def test_valid_line(self, mock_point_3d_factory):
        """Two distinct points should create a Line3D."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(1, 1, 1),
        ]

        result = _create_line_geometry(points)

        assert result is not None
        assert result.startPoint.x == 0
        assert result.endPoint.x == 1

    def test_same_point(self, mock_point_3d_factory):
        """Two identical points should return None."""
        points = [
            mock_point_3d_factory(5, 5, 5),
            mock_point_3d_factory(5, 5, 5),
        ]

        result = _create_line_geometry(points)

        assert result is None

    def test_close_points_below_tolerance(self, mock_point_3d_factory):
        """Points closer than tolerance should return None."""
        # POINT_COINCIDENCE_TOLERANCE is 0.0001 (0.1 micron)
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(0.00005, 0.00005, 0.00005),
        ]

        result = _create_line_geometry(points)

        # Distance is sqrt(3) * 0.00005 ≈ 0.000087 < 0.0001
        assert result is None

    def test_close_points_above_tolerance(self, mock_point_3d_factory):
        """Points farther than tolerance should create Line3D."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(0.001, 0, 0),
        ]

        result = _create_line_geometry(points)

        assert result is not None

    def test_insufficient_points(self, mock_point_3d_factory):
        """Less than 2 points should return None."""
        single_point = [mock_point_3d_factory(0, 0, 0)]

        result = _create_line_geometry(single_point)

        assert result is None

    def test_empty_points(self):
        """Empty points list should return None."""
        result = _create_line_geometry([])
        assert result is None

    def test_uses_first_and_last_points(self, mock_point_3d_factory):
        """Should use first and last points from list."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(5, 5, 5),  # Middle point ignored
            mock_point_3d_factory(10, 10, 10),
        ]

        result = _create_line_geometry(points)

        assert result is not None
        assert result.startPoint.x == 0
        assert result.startPoint.y == 0
        assert result.startPoint.z == 0
        assert result.endPoint.x == 10
        assert result.endPoint.y == 10
        assert result.endPoint.z == 10


class TestCreateSplineGeometry:
    """Tests for _create_spline_geometry function."""

    def test_two_points_degree_1(self, mock_point_3d_factory):
        """Two points should create degree 1 spline."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(1, 1, 1),
        ]

        result = _create_spline_geometry(points, is_closed=False)

        assert result is not None
        assert result.degree == 1
        assert len(result.controlPoints) == 2
        # For degree 1 with 2 control points: need 2+1+1=4 knots
        assert len(result.knots) == 4
        # Knots should be [0, 0, 1, 1] for degree 1
        assert result.knots == [0.0, 0.0, 1.0, 1.0]

    def test_three_points_degree_2(self, mock_point_3d_factory):
        """Three points should create degree 2 spline."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(1, 1, 0),
            mock_point_3d_factory(2, 0, 0),
        ]

        result = _create_spline_geometry(points, is_closed=False)

        assert result is not None
        assert result.degree == 2
        assert len(result.controlPoints) == 3
        # For degree 2 with 3 control points: need 3+2+1=6 knots
        assert len(result.knots) == 6

    def test_four_points_degree_3(self, mock_point_3d_factory):
        """Four points should create degree 3 (cubic) spline."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(1, 1, 0),
            mock_point_3d_factory(2, 1, 0),
            mock_point_3d_factory(3, 0, 0),
        ]

        result = _create_spline_geometry(points, is_closed=False)

        assert result is not None
        assert result.degree == 3
        assert len(result.controlPoints) == 4
        # For degree 3 with 4 control points: need 4+3+1=8 knots
        assert len(result.knots) == 8

    def test_ten_points_degree_capped_at_3(self, mock_point_3d_factory):
        """Many points should still use degree 3 (maximum)."""
        points = [mock_point_3d_factory(i, i % 2, 0) for i in range(10)]

        result = _create_spline_geometry(points, is_closed=False)

        assert result is not None
        assert result.degree == 3  # Capped at 3
        assert len(result.controlPoints) == 10
        # For degree 3 with 10 control points: need 10+3+1=14 knots
        assert len(result.knots) == 14

    def test_closed_spline(self, mock_point_3d_factory):
        """Closed flag should be passed to the spline."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(1, 1, 0),
            mock_point_3d_factory(2, 0, 0),
        ]

        result = _create_spline_geometry(points, is_closed=True)

        assert result is not None
        assert result.isClosed is True

    def test_open_spline(self, mock_point_3d_factory):
        """Open flag should be passed to the spline."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(1, 1, 0),
            mock_point_3d_factory(2, 0, 0),
        ]

        result = _create_spline_geometry(points, is_closed=False)

        assert result is not None
        assert result.isClosed is False

    def test_insufficient_points(self, mock_point_3d_factory):
        """Less than 2 points should return None."""
        points = [mock_point_3d_factory(0, 0, 0)]

        result = _create_spline_geometry(points, is_closed=False)

        assert result is None

    def test_empty_points(self):
        """Empty points list should return None."""
        result = _create_spline_geometry([], is_closed=False)
        assert result is None

    def test_knot_vector_structure(self, mock_point_3d_factory):
        """Verify knot vector follows proper NURBS structure."""
        # With 5 points and degree 3: need 5+3+1=9 knots
        points = [mock_point_3d_factory(i, 0, 0) for i in range(5)]

        result = _create_spline_geometry(points, is_closed=False)

        assert result is not None
        knots = result.knots

        # First (degree+1) knots should be 0
        for i in range(result.degree + 1):
            assert knots[i] == 0.0

        # Last (degree+1) knots should be 1
        for i in range(result.degree + 1):
            assert knots[-(i + 1)] == 1.0

        # Internal knots should be in [0, 1] and non-decreasing
        for i in range(len(knots) - 1):
            assert knots[i] <= knots[i + 1]

    def test_large_point_set(self, mock_point_3d_factory):
        """Large number of points should work correctly."""
        points = [mock_point_3d_factory(i, i * 0.1, 0) for i in range(100)]

        result = _create_spline_geometry(points, is_closed=False)

        assert result is not None
        assert result.degree == 3
        assert len(result.controlPoints) == 100
        # For degree 3 with 100 control points: need 100+3+1=104 knots
        assert len(result.knots) == 104


class TestKnotVectorGeneration:
    """Focused tests on knot vector generation logic."""

    def test_degree_1_knots(self, mock_point_3d_factory):
        """Degree 1 spline should have knots [0,0,1,1]."""
        points = [mock_point_3d_factory(0, 0, 0), mock_point_3d_factory(1, 0, 0)]
        result = _create_spline_geometry(points, is_closed=False)

        assert result.knots == [0.0, 0.0, 1.0, 1.0]

    def test_degree_2_knots(self, mock_point_3d_factory):
        """Degree 2 spline should have proper clamped knot vector."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(1, 0, 0),
            mock_point_3d_factory(2, 0, 0),
        ]
        result = _create_spline_geometry(points, is_closed=False)

        # For n=3, d=2: need n+d+1=6 knots
        assert len(result.knots) == 6
        # First 3 should be 0, last 3 should be 1
        assert result.knots[:3] == [0.0, 0.0, 0.0]
        assert result.knots[3:] == [1.0, 1.0, 1.0]

    def test_degree_3_uniform_knots(self, mock_point_3d_factory):
        """Degree 3 spline with 6 points should have uniform internal knots."""
        points = [mock_point_3d_factory(i, 0, 0) for i in range(6)]
        result = _create_spline_geometry(points, is_closed=False)

        # For n=6, d=3: need 6+3+1=10 knots
        assert len(result.knots) == 10

        # First 4 should be 0
        assert result.knots[:4] == [0.0, 0.0, 0.0, 0.0]

        # Last 4 should be 1
        assert result.knots[6:] == [1.0, 1.0, 1.0, 1.0]

        # Internal knots (index 4, 5) should be evenly spaced
        assert result.knots[4] == pytest.approx(1 / 3, rel=0.01)
        assert result.knots[5] == pytest.approx(2 / 3, rel=0.01)
