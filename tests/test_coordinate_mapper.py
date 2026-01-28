"""Tests for core/coordinate_mapper.py."""

import math

import pytest

from core.coordinate_mapper import (
    MappedSequence,
    _fix_seam_discontinuity,
    _get_bounds,
)


class TestMappedSequence:
    """Tests for MappedSequence class."""

    def test_construction(self, mock_point_3d_factory):
        """Test MappedSequence construction and attribute access."""
        points = [
            mock_point_3d_factory(0, 0, 0),
            mock_point_3d_factory(1, 1, 1),
        ]
        seq = MappedSequence(points, is_closed=True, source_type="SketchCircle")

        assert seq.points == points
        assert seq.is_closed is True
        assert seq.source_type == "SketchCircle"

    def test_construction_empty(self):
        """Test MappedSequence with empty points."""
        seq = MappedSequence([], is_closed=False, source_type="SketchLine")

        assert seq.points == []
        assert seq.is_closed is False


class TestGetBounds:
    """Tests for _get_bounds function."""

    def test_empty_sequences(self):
        """Empty sequences should return default bounds (0,1,0,1)."""
        result = _get_bounds([])
        assert result == (0.0, 1.0, 0.0, 1.0)

    def test_single_point(self, point_sequence_factory):
        """Single point should return that point as both min and max."""
        seq = point_sequence_factory([(5, 10)])
        result = _get_bounds([seq])
        assert result == (5, 5, 10, 10)

    def test_multiple_points_single_sequence(self, point_sequence_factory):
        """Multiple points should return actual min/max."""
        seq = point_sequence_factory([(0, 0), (10, 20)])
        result = _get_bounds([seq])
        assert result == (0, 10, 0, 20)

    def test_negative_coordinates(self, point_sequence_factory):
        """Negative coordinates should be handled correctly."""
        seq = point_sequence_factory([(-5, -10), (5, 10)])
        result = _get_bounds([seq])
        assert result == (-5, 5, -10, 10)

    def test_multiple_sequences(self, point_sequence_factory):
        """Multiple sequences should combine their bounds."""
        seq1 = point_sequence_factory([(0, 0), (5, 5)])
        seq2 = point_sequence_factory([(10, 10), (15, 20)])
        result = _get_bounds([seq1, seq2])
        assert result == (0, 15, 0, 20)

    def test_mixed_positive_negative(self, point_sequence_factory):
        """Mix of positive and negative coordinates."""
        seq = point_sequence_factory([(-10, -5), (0, 0), (3, 7)])
        result = _get_bounds([seq])
        assert result == (-10, 3, -5, 7)

    def test_all_same_x(self, point_sequence_factory):
        """All points have same X coordinate (vertical line)."""
        seq = point_sequence_factory([(5, 0), (5, 10), (5, 5)])
        result = _get_bounds([seq])
        assert result == (5, 5, 0, 10)

    def test_all_same_y(self, point_sequence_factory):
        """All points have same Y coordinate (horizontal line)."""
        seq = point_sequence_factory([(0, 5), (10, 5), (5, 5)])
        result = _get_bounds([seq])
        assert result == (0, 10, 5, 5)


class TestFixSeamDiscontinuity:
    """Tests for _fix_seam_discontinuity function."""

    def test_no_previous_point(self):
        """First point (no previous) should return unchanged."""
        result = _fix_seam_discontinuity(0.5, None, 6.28)
        assert result == 0.5

    def test_normal_progression(self):
        """Normal progression without seam crossing."""
        result = _fix_seam_discontinuity(0.6, 0.5, 6.28)
        assert result == 0.6

    def test_backward_jump_crosses_seam(self):
        """Backward jump >50% of range should add wrap_range."""
        # Simulates going from near 2π to near 0 (wrapping around)
        result = _fix_seam_discontinuity(0.1, 5.0, 6.28)
        assert result == pytest.approx(0.1 + 6.28)

    def test_forward_jump_crosses_seam(self):
        """Forward jump >50% of range should subtract wrap_range."""
        # Simulates going from near 0 to near 2π (wrapping backwards)
        result = _fix_seam_discontinuity(5.0, 0.1, 6.28)
        assert result == pytest.approx(5.0 - 6.28)

    def test_exactly_at_half_no_change(self):
        """Jump of exactly 50% should not trigger adjustment."""
        # 3.14 - 0 = 3.14, which is exactly 50% of 6.28
        result = _fix_seam_discontinuity(3.14, 0.0, 6.28)
        assert result == 3.14

    def test_just_under_half_no_change(self):
        """Jump just under 50% should not trigger adjustment."""
        result = _fix_seam_discontinuity(3.0, 0.0, 6.28)
        assert result == 3.0

    def test_just_over_half_backward_triggers(self):
        """Backward jump just over 50% should trigger adjustment."""
        # prev=5.0, current=1.5, diff=3.5 > 3.14 (50% of 6.28)
        result = _fix_seam_discontinuity(1.5, 5.0, 6.28)
        assert result == pytest.approx(1.5 + 6.28)

    def test_just_over_half_forward_triggers(self):
        """Forward jump just over 50% should trigger adjustment."""
        # current=4.5, prev=1.0, diff=3.5 > 3.14 (50% of 6.28)
        result = _fix_seam_discontinuity(4.5, 1.0, 6.28)
        assert result == pytest.approx(4.5 - 6.28)

    def test_small_wrap_range(self):
        """Test with smaller wrap range."""
        # wrap_range=2.0, half=1.0
        # backward jump: prev=1.8, current=0.2, diff=1.6 > 1.0
        result = _fix_seam_discontinuity(0.2, 1.8, 2.0)
        assert result == pytest.approx(0.2 + 2.0)

    def test_2pi_wrap_range(self):
        """Test with exactly 2*pi wrap range (common for cylinders)."""
        wrap_range = 2 * math.pi
        # Crossing seam from 6.0 to 0.5 radians
        result = _fix_seam_discontinuity(0.5, 6.0, wrap_range)
        assert result == pytest.approx(0.5 + wrap_range)

    def test_zero_wrap_range(self):
        """Zero wrap range should handle edge case."""
        # With wrap_range=0, half is 0, so any difference triggers
        # but the adjustment is 0, so result stays the same
        result = _fix_seam_discontinuity(0.5, 0.3, 0.0)
        assert result == 0.5

    def test_consecutive_normal_progression(self):
        """Multiple consecutive calls without seam crossing."""
        wrap_range = 6.28
        prev = None

        # Simulate normal progression
        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        for val in values:
            result = _fix_seam_discontinuity(val, prev, wrap_range)
            assert result == val  # No adjustment needed
            prev = result
