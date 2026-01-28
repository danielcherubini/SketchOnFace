"""Mock classes for Fusion 360 adsk.* modules.

These mocks allow testing the core modules without having Fusion 360 installed.
"""

import math
from types import SimpleNamespace

# =============================================================================
# adsk.core mocks
# =============================================================================


class Point2D:
    """Mock for adsk.core.Point2D."""

    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    @staticmethod
    def create(x, y):
        return Point2D(x, y)

    def copy(self):
        return Point2D(self.x, self.y)

    def __repr__(self):
        return f"Point2D({self.x}, {self.y})"


class Point3D:
    """Mock for adsk.core.Point3D."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    @staticmethod
    def create(x, y, z):
        return Point3D(x, y, z)

    def copy(self):
        return Point3D(self.x, self.y, self.z)

    def distanceTo(self, other):
        return math.sqrt(
            (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2
        )

    def __repr__(self):
        return f"Point3D({self.x}, {self.y}, {self.z})"


class Vector3D:
    """Mock for adsk.core.Vector3D."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    @staticmethod
    def create(x, y, z):
        return Vector3D(x, y, z)

    def copy(self):
        return Vector3D(self.x, self.y, self.z)

    @property
    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        length = self.length
        if length > 0:
            self.x /= length
            self.y /= length
            self.z /= length
        return True

    def __repr__(self):
        return f"Vector3D({self.x}, {self.y}, {self.z})"


class Line3D:
    """Mock for adsk.core.Line3D."""

    def __init__(self, start_point=None, end_point=None):
        self.startPoint = start_point or Point3D()
        self.endPoint = end_point or Point3D()

    @staticmethod
    def create(start, end):
        return Line3D(start, end)

    def __repr__(self):
        return f"Line3D({self.startPoint}, {self.endPoint})"


class NurbsCurve3D:
    """Mock for adsk.core.NurbsCurve3D."""

    def __init__(self):
        self.controlPoints = []
        self.degree = 3
        self.knots = []
        self.isClosed = False

    @staticmethod
    def createNonRational(control_points, degree, knots, is_closed):
        curve = NurbsCurve3D()
        curve.controlPoints = list(control_points)
        curve.degree = degree
        curve.knots = list(knots)
        curve.isClosed = is_closed
        return curve

    def __repr__(self):
        return f"NurbsCurve3D(degree={self.degree}, points={len(self.controlPoints)})"


class ObjectCollection:
    """Mock for adsk.core.ObjectCollection."""

    def __init__(self):
        self._items = []

    @staticmethod
    def create():
        return ObjectCollection()

    def add(self, item):
        self._items.append(item)

    def item(self, index):
        return self._items[index]

    @property
    def count(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __repr__(self):
        return f"ObjectCollection({len(self._items)} items)"


# =============================================================================
# adsk.fusion mocks
# =============================================================================


class TemporaryBRepManager:
    """Mock for adsk.fusion.TemporaryBRepManager."""

    _instance = None

    @staticmethod
    def get():
        if TemporaryBRepManager._instance is None:
            TemporaryBRepManager._instance = TemporaryBRepManager()
        return TemporaryBRepManager._instance

    def createWireFromCurves(self, curves):
        # Return a mock wire body and edge map
        wire_body = SimpleNamespace(curves=curves)
        edge_map = []
        return wire_body, edge_map


class Design:
    """Mock for adsk.fusion.Design."""

    def __init__(self):
        self.rootComponent = None

    @staticmethod
    def cast(product):
        if product is None:
            return None
        return Design()


# =============================================================================
# Module-level namespaces to mimic adsk.core and adsk.fusion
# =============================================================================


core = SimpleNamespace(
    Point2D=Point2D,
    Point3D=Point3D,
    Vector3D=Vector3D,
    Line3D=Line3D,
    NurbsCurve3D=NurbsCurve3D,
    ObjectCollection=ObjectCollection,
)


fusion = SimpleNamespace(
    TemporaryBRepManager=TemporaryBRepManager,
    Design=Design,
)
