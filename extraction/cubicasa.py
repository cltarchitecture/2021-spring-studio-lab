from collections import namedtuple
from functools import cached_property
from io import StringIO
import math
import os.path
import re

from geometry import LineSegment, Polygon, Point
import svgelements


id_pattern = re.compile("\s+id=\".*?\"", re.IGNORECASE)
display_none_pattern = re.compile("display\s*:\s*none\s*;", re.IGNORECASE)
whitespace = re.compile("\s+")

CLOSE_EDGE_TOLERANCE = 1.0
ROOM_TYPES = [
    "Alcove",
    "Attic",
    "Basement",
    "Bath",
    "Bedroom",
    "CarPort",
    "Closet",
    "Den",
    "Dining",
    "DraughtLobby",
    "DressingRoom",
    "Elevated",
    "Entry",
    "Garage",
    "Hall",
    "Kitchen",
    "Library",
    "LivingRoom",
    "Office",
    "Other",
    "Outdoor",
    "RecreationRoom",
    "Room",
    "Sauna",
    "Storage",
    "TechnicalRoom",
    "Undefined",
    "UserDefined",
    "Utility",
]

fixture_type_suffixes = re.compile("(Corner|High|Left|Low|Mid|Right|Round(Left|Right)?|Small|Triangle|2)$")
fixture_type_prefixes = re.compile("^(Corner|Double|Integrated|Gas|Wood|High|Round|Side)")

FIXTURE_TYPES = [
    "BaseCabinet",
    "Bathtub",
    "Chimney",
    "Closet",
    "CoatCloset",
    "CoatRack",
    "CounterTop",
    "Dishwasher",
    "ElectricalAppliance",
    "Fan",
    "Fireplace",
    "GEA",
    "Heater",
    "Housing",
    "Jacuzzi",
    "PlaceForFireplace",
    "Refrigerator",
    "SaunaBench",
    "SaunaStove",
    "Shower",
    "ShowerCab",
    "ShowerPlatform",
    "ShowerScreen",
    "Sink",
    "SpaceForAppliance",
    "Stove",
    "Toilet",
    "TumbleDryer",
    "Urinal",
    "WallCabinet",
    "WashingMachine",
    "WaterTap",
]

def simplify_fixture_type(classes):
    if classes[0] == "ElectricalAppliance" and len(classes) > 1:
        t = classes[1]
    else:
        t = classes[0]

    t = re.sub(fixture_type_prefixes, "", t)
    t = re.sub(fixture_type_suffixes, "", t)
    return t if t in FIXTURE_TYPES else "Other"


def get_classes(element):
    if svgelements.SVG_ATTR_CLASS in element.values:
        class_str = element.values[svgelements.SVG_ATTR_CLASS]
        return re.split(whitespace, class_str.strip())
    else:
        return []





class PlanObject:

    def __init__(self, container, index):
        self.container = container
        self.index = index
        self.adjacencies = AdjacencyList()

    def __repr__(self):
        return "{} {}".format(self.__class__.__name__, self.index)

    @property
    def polygon_element(self):
        return self.container[0]

    @cached_property
    def polygon(self):
        e = self.polygon_element

        if isinstance(e, svgelements.Rect):
            svg_points = [
                Point(e.x, e.y),
                Point(e.x + e.width, e.y),
                Point(e.x + e.width, e.y + e.height),
                Point(e.x, e.y + e.height)
            ]

        elif isinstance(e, svgelements.Circle):
            svg_points = [Point(e.cx, e.cy)]

        elif isinstance(self.polygon_element, svgelements.Path):
            svg_points = list(self.polygon_element.as_points())

        else:
            svg_points = self.polygon_element.points

        # Make sure we don't have any duplicate points
        unique_points = []
        previous_point = svg_points[-1]
        for point in svg_points:
            if point != previous_point:
                unique_points.append(point)
                previous_point = point

        return Polygon(unique_points)

    def num_edges(self):
        return len(self.polygon.edges)

    @cached_property
    def edges(self):
        return self.polygon.edges

    @property
    def eligible_edges(self):
        """Returns a list of edges that are eligible for adjacency checks."""
        return self.edges

    @property
    def eligible_edges_with_indexes(self):
        """Returns a list of edges that are eligible for adjacency checks along with their indexes in the main edges list."""
        return enumerate(self.edges)

    @property
    def edges_without_adjacencies(self):
        """Returns a list of eligible edges that have no known adjacencies."""
        edges = dict(self.eligible_edges_with_indexes)
        for adj in self.adjacencies.values():
            for edge_info in adj:
                if edge_info.self_edge_index in edges:
                    edges[edge_info.self_edge_index] = None
        return list(filter(lambda x: x is not None, edges.values()))



    def add_adjacency(self, object, self_edge_index, object_edge_index, intersection):
        self.adjacencies.add(object, AdjacencyInfo(self_edge_index, object_edge_index, intersection))

    def find_adjacencies(self, other_objects):
        for self_edge_index, self_edge in self.eligible_edges_with_indexes:
            for object in other_objects:
                for object_edge_index, object_edge in object.eligible_edges_with_indexes:
                    intersection = self_edge.intersect(object_edge)

                    if isinstance(intersection, LineSegment):
                        self.add_adjacency(object, self_edge_index, object_edge_index, intersection)
                        object.add_adjacency(self, object_edge_index, self_edge_index, intersection)


    def find_close(self, other_objects, tolerance):
        loose_edges = self.edges_without_adjacencies
        for self_edge in loose_edges:
            self_edge_index = self.edges.index(self_edge)
            for object in other_objects:
                for object_edge_index, object_edge in object.eligible_edges_with_indexes:

                    if self_edge.is_close(object_edge, tolerance):

                        # closest_to_start = object_edge.closest_to_point(self_edge.start)
                        # closest_to_end = object_edge.closest_to_point(self_edge.end)
                        # intersection = LineSegment(closest_to_start, closest_to_end)

                        self.add_adjacency(object, self_edge_index, object_edge_index, None)
                        object.add_adjacency(self, object_edge_index, self_edge_index, None)

    def adjacencies_by_type(self, cls):
        return list(filter(lambda obj: isinstance(obj, cls), self.adjacencies.keys()))




AdjacencyInfo = namedtuple('AdjacencyInfo', ["self_edge_index", "object_edge_index", "intersection"])

class AdjacencyList(dict):

    def add(self, object, info):
        if object not in self:
            self[object] = []
        self[object].append(info)

    def filter(self, fn):
        matches = AdjacencyList()
        for object, info_list in self.items():
            for info_item in info_list:
                if fn(object, info_item):
                    matches.add(object, info_item)
        return matches

    def by_edge(self, edge_index):
        return self.filter(lambda object, info: info.self_edge_index == edge_index)



class Room(PlanObject):

    def __init__(self, container, index):
        super().__init__(container, index)
        self.doors = set()
        self.windows = set()
        self.fixtures = set()

    def __repr__(self):
        return "Room {} ({})".format(self.index, self.simple_type)

    @cached_property
    def types(self):
        classes = get_classes(self.container)
        return classes[1:] if len(classes) > 1 else []

    @property
    def full_type(self):
        return " ".join(self.types)

    @property
    def simple_type(self):
        return self.types[0] if self.types[0] in ROOM_TYPES else "Other"

    @property
    def is_outdoor(self):
        return self.types[0] == "Outdoor"

    def adjacent_walls(self):
        return self.adjacencies_by_type(Wall)

    def adjacent_exterior_walls(self):
        return list(filter(lambda w: w.is_exterior, self.adjacent_walls()))

    def adjacent_railings(self):
        return self.adjacencies_by_type(Railing)

    def adjacent_rooms(self):
        return self.adjacencies_by_type(Room)

    def connected_rooms(self):
        return list(map(lambda d: d.rooms[1] if d.rooms[0] == self else d.rooms[0], self.doors))






class Divider(PlanObject):

    @property
    def eligible_edges(self):
        """Returns a list of edges that are eligible for adjacency checks.

        Most walls have exactly 4 edges.  The 0th and 2nd edges represent the faces of the wall and must be checked for
        adjacencies to rooms.  The 1st and 3rd edges represent the ends of the wall and do not need to be checked.  If a
        wall has fewer than 4 edges, it is considered degenerate and will not be checked at all.
        """
        if len(self.edges) == 4:
            return [self.edges[0], self.edges[2]]
        return []

    @property
    def eligible_edges_with_indexes(self):
        """Returns a list of edges that are eligible for adjacency checks along with their indexes in the main edges list."""
        return list(map(lambda e: (self.edges.index(e), e), self.eligible_edges))

    def rooms_opposite(self, room):
        """Returns a list of rooms adjacent to the opposite side of the wall/railing from the given room."""
        if room in self.adjacencies:
            room_side = self.adjacencies[room][0].self_edge_index
            other_side = 0 if room_side == 2 else 2
            return self.adjacencies.filter(lambda obj, info: isinstance(obj, Room) and info.self_edge_index == other_side)





class Railing(Divider):
    pass


class Wall(Divider):

    def __init__(self, container, index):
        super().__init__(container, index)
        self.openings = []

        for child in container:
            if isinstance(child, svgelements.Group):
                object_type = get_classes(child)[0]
                if object_type == "Door":
                    self.openings.append(Door(self, child, len(self.openings)))
                elif object_type == "Window":
                    self.openings.append(Window(self, child, len(self.openings)))

    @property
    def is_exterior(self):
        return "External" in get_classes(self.container)

    def add_adjacency(self, object, self_edge_index, object_edge_index, intersection):
        super().add_adjacency(object, self_edge_index, object_edge_index, intersection)

        if isinstance(object, Room):
            for opening in self.openings:
                opening.check_adjacencies(object, object_edge_index)



class WallOpening(PlanObject):

    def __init__(self, wall, container, index):
        super().__init__(container, index)
        self.wall = wall
        self.rooms = [None, None]

        # The open sides of the wall opening polygon always have indicies 0 and 2.
        # They also match up with wall indices 0 and 2.

    def __repr__(self):
        return "{} in {}".format(super().__repr__(), self.wall)

    def check_adjacencies(self, room, room_edge_index):
        room_edge = room.edges[room_edge_index]
        for self_edge_index in [0, 2]:
            self_edge = self.edges[self_edge_index]
            if self_edge.is_close(room_edge, CLOSE_EDGE_TOLERANCE):
                self.add_adjacency(room, self_edge_index // 2)


class Door(WallOpening):

    def add_adjacency(self, room, edge_index):
        self.rooms[edge_index] = room
        room.doors.add(self)


class Window(WallOpening):

    def add_adjacency(self, room, edge_index):
        self.rooms[edge_index] = room
        room.windows.add(self)


class Fixture(PlanObject):

    def __init__(self, container, index):
        super().__init__(container, index)
        self.rooms = {}

    def __repr__(self):
        return "Fixture {} ({})".format(self.index, self.type)

    @property
    def polygon_element(self):
        for child in self.container:
            if isinstance(child, svgelements.Group):
            # if "#BoundaryPolygon" in get_classes(child):
                return child[0]

        # for child in self.container:
        # 	if "InnerPolygon" in get_classes(child):
        # 		return child[0]

        print(self.container.values)
        print(self.container.bbox())
        print(self.container[0].bbox())
        raise Exception("Boundary polygon not found")

    @cached_property
    def types(self):
        classes = get_classes(self.container)
        return classes[1:] if len(classes) > 1 else []

    @property
    def full_type(self):
        return " ".join(self.types)

    @property
    def simple_type(self):
        return simplify_fixture_type(self.types)

    def add_room(self, room, vertex):
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(vertex)
        room.fixtures.add(self)

    def find_rooms(self, rooms):
        for vertex in self.polygon.vertices:
            self._find_room(rooms, vertex)

    def _find_room(self, rooms, vertex):
        for room in self.rooms:
            if room.polygon.contains_point(vertex):
                self.add_room(room, vertex)
                return

        for room in rooms:
            if room not in self.rooms and room.polygon.contains_point(vertex):
                self.add_room(room, vertex)
                break


class Stair:

    def __init__(self, container, index):
        self.container = container
        self.index = index
        self.flights = []
        self.windings = []

    def __repr__(self):
        return "Stair {}".format(self.index)


class StairFlight(PlanObject):
    pass


class StairWinding(PlanObject):
    pass








def find_children_by_class(parent, class_name):
    try:
        return list(filter(lambda child: class_name in get_classes(child), parent))
    except:
        return []


class PlanObjectList(list):

    def __init__(self, object_class, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.object_class = object_class

    def add(self, object):
        self.append(self.object_class(object, len(self)))


class Model:

    def __init__(self, file):
        self.document = svgelements.SVG.parse(file)
        self.model = find_children_by_class(self.document, "Model")[0]
        self.floors = []

        for child in find_children_by_class(self.model, "Floor"):
            self.floors.append(Floor(child))


class Floor:

    def __init__(self, container):
        self.container = container
        self.rooms = PlanObjectList(Room)
        self.walls = PlanObjectList(Wall)
        self.railings = PlanObjectList(Railing)
        self.fixtures = PlanObjectList(Fixture)

    def find_objects(self):
        plan = find_children_by_class(self.container, "Floorplan")[0]

        for child in plan:
            if isinstance(child, svgelements.Group):
                object_type = get_classes(child)[0]

                if object_type == "Space":
                    self.rooms.add(child)

                elif object_type == "Wall":
                    self.walls.add(child)

                elif object_type == "Railing":
                    self.railings.add(child)

                elif object_type == "FixedFurniture":
                    self.fixtures.add(child)

                elif object_type == "FixedFurnitureSet":
                    for grandchild in child:
                        self.fixtures.add(grandchild)

    def area(self):
        """Returns the total area of the floor."""
        area = 0

        for room in self.rooms:
            area += room.polygon.area()

        for wall in self.walls:
            area += wall.polygon.area()

        return area


    def find_adjacencies(self):

        # Find adjacent edges
        for room_index, room in enumerate(self.rooms):
            room.find_adjacencies(self.walls)
            room.find_adjacencies(self.railings)
            room.find_adjacencies(self.rooms[room_index+1:])

        # Check for missing adjacencies
        for room_index, room in enumerate(self.rooms):
            if len(room.edges_without_adjacencies) > 0:
                room.find_close(self.walls, CLOSE_EDGE_TOLERANCE)
                room.find_close(self.railings, CLOSE_EDGE_TOLERANCE)
                room.find_close(self.rooms[room_index+1:], CLOSE_EDGE_TOLERANCE)

    def find_inside(self):
        for fixture in self.fixtures:
            fixture.find_rooms(self.rooms)




class Cubicasa:

    def __init__(self, basepath):
        self.basepath = basepath

    def get_model(self, *path):
        model_path = os.path.join(self.basepath, *path, "model.svg")
        with open(model_path) as file:
            contents = file.read()

            # Strip out all id attributes
            contents = re.sub(id_pattern, " ", contents)

            # Strip out all "display: none" styles -- they cause svgelements to ignore
            contents = re.sub(display_none_pattern, " ", contents)

            # Some models have invalid <path> data that causes svgelements to ignore the affected elements
            # See high_quality_architectural/10074/model.svg for examples
            contents = contents.replace("LNaN,NaN", "")

            model = Model(StringIO(contents))
            model.path = model_path
            return model

    def paths(self):
        parent_folders = [ f.name for f in os.scandir(self.basepath) if f.is_dir()]
        for p in parent_folders:
            path = os.path.join(self.basepath, p)
            child_folders = [ f.name for f in os.scandir(path) if f.is_dir() ]
            for c in child_folders:
                yield (p, c)

    def models(self):
        for path in self.paths():
            yield self.get_model(*path)
