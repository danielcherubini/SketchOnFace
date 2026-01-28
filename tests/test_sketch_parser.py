"""Tests for core/sketch_parser.py."""

import math
from types import SimpleNamespace

import pytest

from core.sketch_parser import (
    CIRCLE_SAMPLES,
    DEFAULT_LINE_SAMPLES,
    PointSequence,
    _parse_circle,
    _parse_line,
)


class TestPointSequence:
    """Tests for PointSequence class."""

    def test_construction(self):
        """Test PointSequence construction and attribute access."""
        points = [(0, 0), (1, 1), (2, 2)]
        seq = PointSequence(points, is_closed=True, source_type="SketchCircle")

        assert seq.points == points
        assert seq.is_closed is True
        assert seq.source_type == "SketchCircle"

    def test_construction_empty(self):
        """Test PointSequence with empty points."""
        seq = PointSequence([], is_closed=False, source_type="SketchLine")

        assert seq.points == []
        assert seq.is_closed is False
        assert seq.source_type == "SketchLine"

    def test_construction_various_types(self):
        """Test PointSequence with different source types."""
        types = [
            "SketchLine",
            "SketchCircle",
            "SketchArc",
            "SketchFittedSpline",
            "SketchFixedSpline",
            "SketchPoint",
        ]
        for source_type in types:
            seq = PointSequence([(0, 0)], False, source_type)
            assert seq.source_type == source_type


class TestParseCircle:
    """Tests for _parse_circle function."""

    def _create_mock_circle(self, center_x, center_y, radius):
        """Create a mock SketchCircle object."""
        center_point = SimpleNamespace(x=center_x, y=center_y)
        center_sketch_point = SimpleNamespace(geometry=center_point)

        return SimpleNamespace(
            centerSketchPoint=center_sketch_point,
            radius=radius,
        )

    def test_unit_circle_at_origin(self):
        """Unit circle at origin should have 36 points at distance 1."""
        circle = self._create_mock_circle(0, 0, 1)
        result = _parse_circle(circle)

        assert len(result.points) == CIRCLE_SAMPLES
        assert result.is_closed is True
        assert result.source_type == "SketchCircle"

        # All points should be at distance 1 from origin
        for x, y in result.points:
            distance = math.sqrt(x**2 + y**2)
            assert distance == pytest.approx(1.0, abs=1e-10)

    def test_circle_at_offset(self):
        """Circle at offset position should have points centered at that position."""
        circle = self._create_mock_circle(5, 5, 2)
        result = _parse_circle(circle)

        assert len(result.points) == CIRCLE_SAMPLES

        # All points should be at distance 2 from center (5, 5)
        for x, y in result.points:
            distance = math.sqrt((x - 5) ** 2 + (y - 5) ** 2)
            assert distance == pytest.approx(2.0, abs=1e-10)

    def test_circle_closed_flag(self):
        """Circles should always be marked as closed."""
        circle = self._create_mock_circle(0, 0, 1)
        result = _parse_circle(circle)
        assert result.is_closed is True

    def test_circle_sample_count(self):
        """Circle should have exactly CIRCLE_SAMPLES points."""
        circle = self._create_mock_circle(0, 0, 1)
        result = _parse_circle(circle)
        assert len(result.points) == 36  # CIRCLE_SAMPLES

    def test_circle_points_evenly_distributed(self):
        """Points should be evenly distributed around circle."""
        circle = self._create_mock_circle(0, 0, 1)
        result = _parse_circle(circle)

        # First point should be at angle 0 (right side)
        assert result.points[0][0] == pytest.approx(1.0, abs=1e-10)
        assert result.points[0][1] == pytest.approx(0.0, abs=1e-10)

        # Point at 1/4 of the way should be at angle 90 degrees (top)
        quarter_idx = CIRCLE_SAMPLES // 4
        assert result.points[quarter_idx][0] == pytest.approx(0.0, abs=1e-10)
        assert result.points[quarter_idx][1] == pytest.approx(1.0, abs=1e-10)

    def test_large_radius_circle(self):
        """Large radius circle should work correctly."""
        circle = self._create_mock_circle(0, 0, 100)
        result = _parse_circle(circle)

        # All points should be at distance 100 from origin
        for x, y in result.points:
            distance = math.sqrt(x**2 + y**2)
            assert distance == pytest.approx(100.0, abs=1e-9)

    def test_small_radius_circle(self):
        """Small radius circle should work correctly."""
        circle = self._create_mock_circle(0, 0, 0.001)
        result = _parse_circle(circle)

        # All points should be at distance 0.001 from origin
        for x, y in result.points:
            distance = math.sqrt(x**2 + y**2)
            assert distance == pytest.approx(0.001, abs=1e-13)


class TestParseLine:
    """Tests for _parse_line function."""

    def _create_mock_line(self, start_x, start_y, end_x, end_y):
        """Create a mock SketchLine object."""
        start_point = SimpleNamespace(x=start_x, y=start_y)
        end_point = SimpleNamespace(x=end_x, y=end_y)
        start_sketch_point = SimpleNamespace(geometry=start_point)
        end_sketch_point = SimpleNamespace(geometry=end_point)

        return SimpleNamespace(
            startSketchPoint=start_sketch_point,
            endSketchPoint=end_sketch_point,
        )

    def test_horizontal_line(self):
        """Horizontal line should have all points with y=0."""
        line = self._create_mock_line(0, 0, 10, 0)
        result = _parse_line(line)

        assert len(result.points) == DEFAULT_LINE_SAMPLES + 1
        assert result.is_closed is False
        assert result.source_type == "SketchLine"

        # All points should have y=0
        for _x, y in result.points:
            assert y == 0

        # X should range from 0 to 10
        assert result.points[0][0] == 0
        assert result.points[-1][0] == 10

    def test_vertical_line(self):
        """Vertical line should have all points with x=0."""
        line = self._create_mock_line(0, 0, 0, 10)
        result = _parse_line(line)

        assert len(result.points) == DEFAULT_LINE_SAMPLES + 1

        # All points should have x=0
        for x, _y in result.points:
            assert x == 0

        # Y should range from 0 to 10
        assert result.points[0][1] == 0
        assert result.points[-1][1] == 10

    def test_diagonal_line(self):
        """Diagonal line should have points along the diagonal."""
        line = self._create_mock_line(0, 0, 10, 10)
        result = _parse_line(line)

        assert len(result.points) == DEFAULT_LINE_SAMPLES + 1

        # All points should be on the diagonal (x == y)
        for x, y in result.points:
            assert x == pytest.approx(y)

        # Should span from (0,0) to (10,10)
        assert result.points[0] == (0, 0)
        assert result.points[-1] == (10, 10)

    def test_custom_samples(self):
        """Custom sample count should produce correct number of points."""
        line = self._create_mock_line(0, 0, 10, 0)
        result = _parse_line(line, num_samples=5)

        # num_samples=5 should produce 6 points (including endpoints)
        assert len(result.points) == 6

        # Check evenly spaced
        expected_x = [0, 2, 4, 6, 8, 10]
        for i, (x, y) in enumerate(result.points):
            assert x == pytest.approx(expected_x[i])
            assert y == 0

    def test_line_not_closed(self):
        """Lines should always be marked as not closed."""
        line = self._create_mock_line(0, 0, 10, 10)
        result = _parse_line(line)
        assert result.is_closed is False

    def test_negative_coordinates(self):
        """Line with negative coordinates should work correctly."""
        line = self._create_mock_line(-5, -10, 5, 10)
        result = _parse_line(line)

        # Should start at (-5, -10) and end at (5, 10)
        assert result.points[0] == (-5, -10)
        assert result.points[-1] == (5, 10)

    def test_reverse_direction(self):
        """Line going in reverse direction should work correctly."""
        line = self._create_mock_line(10, 10, 0, 0)
        result = _parse_line(line)

        # Should start at (10, 10) and end at (0, 0)
        assert result.points[0] == (10, 10)
        assert result.points[-1] == (0, 0)

    def test_point_interpolation(self):
        """Points should be linearly interpolated along the line."""
        line = self._create_mock_line(0, 0, 20, 10)
        result = _parse_line(line, num_samples=2)

        # 3 points: start, middle, end
        assert len(result.points) == 3
        assert result.points[0] == (0, 0)
        assert result.points[1] == (10, 5)
        assert result.points[2] == (20, 10)
