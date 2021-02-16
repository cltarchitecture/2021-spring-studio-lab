from collections import Counter
from datetime import timedelta
import csv
import os.path
import sys
from time import perf_counter
from xml.dom.minidom import parse

from cubicasa import Cubicasa


start_time = perf_counter()
object_type = sys.argv[1]
c = Cubicasa(sys.argv[2])
types = Counter()

for path in c.paths():
    path = os.path.join(c.basepath, *path, "model.svg")

    try:
        model = parse(path)
        for group in model.getElementsByTagName("g"):
            classes = group.getAttribute("class").strip().split()
            if len(classes) >= 1 and classes[0] == object_type:
                t = " ".join(classes[1:])
                types[t] += 1

    except:
        print("Error while processing {}".format(path), file=sys.stderr)
        raise

writer = csv.writer(sys.stdout)
writer.writerow(["Type of "+object_type, "Frequency"])
for type, freq in types.items():
    writer.writerow([type, freq])

elapsed = timedelta(seconds = perf_counter() - start_time)
print("Completed in {}".format(elapsed), file=sys.stderr)
