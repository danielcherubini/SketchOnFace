"""Pytest configuration and fixtures.

IMPORTANT: This file must inject the adsk mocks BEFORE any core modules are imported.
The Fusion 360 API (adsk.*) is only available inside Fusion 360, so we mock it here.
"""

import sys
from types import SimpleNamespace

# Import our mock classes
from tests.mocks import adsk_mock

# Create mock adsk module structure and inject into sys.modules
# This MUST happen before any imports of core modules
mock_adsk = SimpleNamespace()
mock_adsk.core = adsk_mock.core
mock_adsk.fusion = adsk_mock.fusion

sys.modules["adsk"] = mock_adsk
sys.modules["adsk.core"] = mock_adsk.core
sys.modules["adsk.fusion"] = mock_adsk.fusion


# =============================================================================
# Pytest fixtures
# =============================================================================

import pytest  # noqa: E402 (must be after mock injection)

from core.sketch_parser import PointSequence  # noqa: E402


@pytest.fixture
def point_sequence_factory():
    """Factory fixture to create PointSequence objects."""

    def _create(points, is_closed=False, source_type="test"):
        return PointSequence(points, is_closed, source_type)

    return _create


@pytest.fixture
def mock_point_3d_factory():
    """Factory fixture to create Point3D objects."""

    def _create(x, y, z):
        return adsk_mock.Point3D.create(x, y, z)

    return _create


@pytest.fixture
def mock_point_2d_factory():
    """Factory fixture to create Point2D objects."""

    def _create(x, y):
        return adsk_mock.Point2D.create(x, y)

    return _create
