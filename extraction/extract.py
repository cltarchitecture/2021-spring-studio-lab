import argparse
from collections import Counter
import csv
import sys
from time import perf_counter
from cubicasa import Cubicasa, ROOM_TYPES, FIXTURE_TYPES


def limit(gen, max):
    count = 0
    for item in gen:
        if count < max:
            yield item
            count += 1
        else:
            break

def get_headers():
    headers = [
        "path",
        "type",
        "classes",
        "floor_index",
        "num_sides",
        "area",
        "proportion_floor_area",
        "perimeter",
        "compactness",
        "num_adjacent_walls",
        "proportion_exterior_walls",
        "num_adjacent_railings",
        "proportion_exterior_railings",
        "num_railings_to_outside",
        "num_adjacent_rooms",
        "num_connected_rooms",
        "num_doors",
        "num_windows",
        "num_fixtures",
    ]

    for t in ROOM_TYPES:
        headers.append("open_to_" + t)
        headers.append("doors_to_" + t)

    for t in FIXTURE_TYPES:
        headers.append("contains_" + t)

    return headers

def process(model):
    try:

        for floor_index, floor in enumerate(model.floors):

            floor.find_objects()
            floor.find_adjacencies()
            floor.find_inside()
            floor_area = floor.area()

            for room in floor.rooms:

                adjacent_rooms = Counter()
                for r in room.adjacent_rooms():
                    adjacent_rooms[r.simple_type] += 1

                connected_rooms = Counter()
                for r in room.connected_rooms():
                    type = r.simple_type if r is not None else "Outside"
                    connected_rooms[type] += 1

                fixture_types = Counter()
                for fixture in room.fixtures:
                    fixture_types[fixture.simple_type] += 1

                room_area = room.polygon.area()
                proportion_floor_area = room_area / floor_area if floor_area > 0 else 0

                num_walls = len(room.adjacent_walls())
                num_exterior_walls = len(room.adjacent_exterior_walls())
                proportion_exterior_walls = num_exterior_walls / num_walls if num_walls > 0 else 0

                num_railings = len(room.adjacent_railings())
                num_exterior_railings = 0
                for railing in room.adjacent_railings():
                    if len(railing.rooms_opposite(room)) == 0:
                        num_exterior_railings += 1
                proportion_exterior_railings = num_exterior_railings / num_railings if num_railings > 0 else 0


                data = [
                    model.path,
                    room.simple_type,
                    room.full_type,
                    floor_index,
                    room.num_edges(),
                    room_area,
                    proportion_floor_area,
                    room.polygon.perimeter(),
                    room.polygon.isoperimetric_quotient(),
                    num_walls,
                    proportion_exterior_walls,
                    num_railings,
                    proportion_exterior_railings,
                    sum(adjacent_rooms.values()),
                    sum(connected_rooms.values()),
                    len(room.doors),
                    len(room.windows),
                    len(room.fixtures),
                ]

                for t in ROOM_TYPES:
                    data.append(adjacent_rooms[t])
                    data.append(connected_rooms[t])

                for t in FIXTURE_TYPES:
                    data.append(fixture_types[t])

                yield data

    except Exception as e:
        print("Error when processing {}".format(m.path), file=sys.stderr)
        raise




parser = argparse.ArgumentParser()
parser.add_argument("basepath", metavar="CUBICASA_PATH", help="The path to the cubicasa5k folder")
parser.add_argument("-l", "--limit", type=int, help="The maximum number of plans to process")
parser.add_argument("-p", "--plan", help="The relative path to a specific plan to process")
args = parser.parse_args()

start_time = perf_counter()
c = Cubicasa(args.basepath)
w = csv.writer(sys.stdout)
w.writerow(get_headers())

if args.plan is not None:
    m = c.get_model(args.plan)
    for data in process(m):
        w.writerow(data)

else:
    iterator = c.models()
    if args.limit is not None:
        iterator = limit(iterator, args.limit)

    for m in iterator:
        for data in process(m):
            w.writerow(data)


elapsed = perf_counter() - start_time
minutes = int(elapsed // 60)
seconds = elapsed % 60
print("Completed in {:02d}:{:07.4f}".format(minutes, seconds), file=sys.stderr)
