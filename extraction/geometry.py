from collections import namedtuple
from dataclasses import dataclass
from functools import cached_property, reduce
import math

# import sys


ABS_TOL = 0.01

def isclose(a, b):
    return math.isclose(a, b, abs_tol=ABS_TOL)


Point = namedtuple("Point", ["x", "y"])


@dataclass(repr=False, eq=False, order=False, frozen=True)
class Line:
    """Represents an infinite line in two-dimensional space."""

    a: float
    b: float
    c: float

    def __repr__(self):
        return "{}({}x + {}y + {})".format(self.__class__.__name__, self.a, self.b, self.c)

    def __eq__(self, other):
        return isclose(self.slope, other.slope) and isclose(self.intercept, other.intercept)

    @cached_property
    def slope(self):
        """Returns the slope of the line."""
        if self.is_vertical:
            return math.inf
        return -self.a / self.b

    @cached_property
    def perpendicular_slope(self):
        """Returns the slope of a line perpendicular to this one."""
        if self.is_horizontal:
            return math.inf
        return self.b / self.a

    @cached_property
    def intercept(self):
        """Returns the value of y when x = 0."""
        if self.is_vertical:
            return math.nan
        return -self.c / self.b

    @cached_property
    def is_horizontal(self):
        """Returns true if the line is horizontal."""
        return self.a == 0

    @cached_property
    def is_vertical(self):
        """Returns true if the line is vertical."""
        return self.b == 0

    def solve_for_y(self, x):
        if self.is_vertical:
            return math.inf if x == -self.c else math.nan
        return (self.a * x + self.c) / -self.b

    def contains_point(self, point):
        """Returns true if the line passes through the given point."""
        return isclose(self.a * point.x + self.b * point.y + self.c, 0)

    def contains_segment(self, segment):
        """Returns true if the given line segment is part of the line."""
        return self.contains_point(segment.start) and self.contains_point(segment.end)

    def distance_to_point(self, point):
        """Returns the closest distance between the line and the given point."""
        return abs(self.a * point.x + self.b * point.y + c) / math.hypot(self.a, self.b)

    def closest_to_point(self, point):
        """Returns the closest point on the line to the given point."""
        perpendicular = Line.through_point(point, self.perpendicular_slope)
        closest = self.intersect(perpendicular)

        # if not closest:
        # 	print("Uh-oh! No intersection found")
        # 	print(self)
        # 	print(perpendicular)
        # 	sys.exit()


        # if not self.contains_point(closest):
        # 	print("Uh-oh! Intersection is not on original line")
        # 	print(self)
        # 	print(perpendicular)
        # 	print(closest)
        # 	print(self.solve_for_x(closest.x))
        # 	sys.exit()



        return closest

    def intersect(self, other):
        """Returns the point at which this line and another line intersect, or None if the lines are parallel."""
        nx = self.b * other.c - other.b * self.c
        ny = self.c * other.a - other.c * self.a
        d = self.a * other.b - other.a * self.b

        if d != 0:
            return Point(nx / d, ny / d)

    @classmethod
    def through_points(cls, point1, point2):
        if point1 == point2:
            raise Exception("Points must be unique")
        a = point1.y - point2.y
        b = point2.x - point1.x
        c = point1.x * point2.y - point2.x * point1.y
        return cls(a, b, c)

    @classmethod
    def through_point(cls, point, slope):
        if math.isinf(slope):
            dx, dy = 0, 1
        else:
            dx, dy = 1, 1 * slope

        other_point = Point(point.x + dx, point.y + dy)
        return cls.through_points(point, other_point)


@dataclass(repr=False, order=False, frozen=True)
class LineSegment:
    """Represents a line segment in two-dimensional space."""

    start: "The point where the segment begins"
    end: "The point where the segment ends"

    def __repr__(self):
        return "{}({} -> {})".format(self.__class__.__name__, self.start, self.end)

    @cached_property
    def x(self):
        return Domain(self.start.x, self.end.x)

    @cached_property
    def y(self):
        return Domain(self.start.y, self.end.y)

    @cached_property
    def length(self):
        return math.dist(self.start, self.end)

    @cached_property
    def midpoint(self):
        x = (self.start.x + self.end.x) / 2
        y = (self.start.y + self.end.y) / 2
        return Point(x, y)

    @cached_property
    def line(self):
        """Returns the line on which this segment lies."""
        return Line.through_points(self.start, self.end)

    def reverse(self):
        return self.__class__(self.end, self.start)

    def position(self, point):
        px = self.x.position(point.x)
        py = self.y.position(point.y)

        if math.isinf(px):
            return py
        if math.isinf(py):
            return px
        if isclose(px, py):
            return px

        # Point is not on the line

    def _is_in_range(self, point):
        return self.x.contains(point.x) and self.y.contains(point.y)

    def contains_point(self, point):
        """Returns true if the given point lies on this line segment."""
        return self.line.contains_point(point) and self._is_in_range(point)

    def contains_segment(self, other):
        """Returns true if the given line segment lies entirely on this line segment."""
        return (
            self.line.contains_segment(other) and
            self._is_in_range(other.start) and
            self._is_in_range(other.end)
        )

    def distance_to_point(self, point):
        """Returns the closest distance between the line segment and the given point."""
        closest = self.closest_to_point(point)
        return math.dist(point, closest)

    def closest_to_point(self, point):
        """Returns the closest point on the line segment to the given point."""
        closest = self.line.closest_to_point(point)
        position = self.position(closest)

        # if not closest:
        # 	print("Uh-oh! No intersection found")
        # 	print(self.line)
        # 	print(perpendicular)
        # 	sys.exit()

        # if not self.line.contains_point(closest):
        # 	print("Uh-oh! Intersection is not on original line")
        # 	print(self.line)
        # 	#print(perpendicular)
        # 	print(closest)
        # 	print(self.line.solve_for_x(closest.x))
        # 	sys.exit()



        if position is None:
            raise Exception("The closest point on a line is somehow not on that line")
        if position < 0:
            return self.start
        if position > 1:
            return self.end

        return closest

    def intersect(self, other):
        """Returns a point or line segment representing the intersection of this line segment and another line segment."""
        if self.line == other.line:
            endpoints = []
            pairs = [
                (self, other.start),
                (self, other.end),
                (other, self.start),
                (other, self.end)
            ]

            for edge, point in pairs:
                if edge.contains_point(point):
                    endpoints.append(point)
                    if len(endpoints) == 2:
                        return LineSegment(*endpoints)

        else:
            intersect_point = self.line.intersect(other.line)
            if intersect_point and other._is_in_range(intersect_point):
                return intersect_point

        return None

    def is_close(self, other, tolerance):
        close_points = 0
        pairs = [
            (self, other.start),
            (self, other.end),
            (other, self.start),
            (other, self.end)
        ]

        for edge, point in pairs:
            if edge.distance_to_point(point) < tolerance:
                close_points += 1
                if close_points == 2:
                    return True

        return False



@dataclass(frozen=True)
class Domain:

    start: "The value at which the domain starts"
    end: "The value at which the domain ends"

    @cached_property
    def min(self):
        return min(self.start, self.end)

    @cached_property
    def max(self):
        return max(self.start, self.end)

    @cached_property
    def length(self):
        return self.max - self.min

    def contains(self, value):
        """Returns true if the domain contains the given value."""
        return (
            (value >= self.min and value <= self.max) or
            isclose(value, self.min) or
            isclose(value, self.max)
        )

    def position(self, value):
        """Returns a number between 0 and 1 that indicates how far the given
        value is between the range's start and end values."""
        if self.end == self.start:
            return math.inf if self.contains(value) else -math.inf
        return (value - self.start) / (self.end - self.start)


@dataclass(repr=False, eq=False, order=False, frozen=True)
class Polygon:
    """Represents a polygon in two-dimensional space."""

    vertices: list

    @cached_property
    def pairs_of_vertices(self):
        pairs = []
        for i in range(0, len(self.vertices)-1):
            pairs.append((self.vertices[i], self.vertices[i+1]))
        pairs.append((self.vertices[-1], self.vertices[0]))
        return pairs

    @cached_property
    def edges(self):
        """Returns a list of the polygon's edges."""
        return list(map(lambda p: LineSegment(*p), self.pairs_of_vertices))

    # Adapted from https://www.geeksforgeeks.org/area-of-a-polygon-with-given-n-ordered-vertices/
    def area(self):
        """Returns the area of the polygon."""
        return abs(reduce(lambda a, p: a + (p[0].x + p[1].x) * (p[0].y - p[1].y), self.pairs_of_vertices, 0.0) / 2.0)

    def perimeter(self):
        """Returns the perimeter of the polygon."""
        return reduce(lambda d, p: d + math.dist(*p), self.pairs_of_vertices, 0.0)

    def isoperimetric_quotient(self):
        """Returns the isoperimetric quotient of the polygon, a measure of its compactness."""
        return 4 * math.pi * self.area() / self.perimeter() ** 2

    def longest_diagonal(self):
        """Returns the longest distance between any two of the polygon's vertices."""
        distances = []
        for i, p1 in enumerate(self.vertices):
            for p2 in self.vertices[i+1:]:
                distances.append(math.dist(p1, p2))
        return max(distances)

    def contains_point(self, point):
        """Returns true if the given point lies within the polygon."""
        crossings = 0

        for edge in self.edges:
            y = edge.line.solve_for_y(point.x)

            if not math.isnan(y) and not math.isinf(y) and y >= point.y:
                py = edge.position(Point(point.x, y))

                if py >= 0 and py < 1:
                    crossings += 1

        return crossings % 2 == 1
