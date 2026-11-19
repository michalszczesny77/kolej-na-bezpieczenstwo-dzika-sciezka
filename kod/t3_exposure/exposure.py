import json
import sys
import time
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Point, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from context import attractors, population, track_frame

CELL_AREA_M2 = 250.0 * 250.0
SIDE_RADIUS_M = 500.0
POP_RADII_M = (500.0, 1000.0)
AREA_CATEGORIES = ("residential", "allotments", "park", "workplace", "school", "sport")
CATEGORIES = ("station", "stop", "school", "shop", "allotments", "park", "sport", "workplace", "residential")


def half_plane(center, tangent, normal, sign, size=5000.0):
    t, n = tangent * size, normal * size * sign
    return Polygon([center - t, center + t, center + t + n, center - t + n])


def population_in(geom):
    pop = population()
    idx = pop["tree"].query(geom, predicate="intersects")
    if len(idx) == 0:
        return 0.0
    cells = pop["grid"].geometry.values[idx]
    share = shapely.area(shapely.intersection(cells, geom)) / CELL_AREA_M2
    return float(np.sum(pop["grid"]["pop"].values[idx] * share))


def exposure(lat, lon):
    frame = track_frame(lat, lon)
    c, t, n = frame["center"], frame["tangent"], frame["normal"]
    center = Point(c)
    disc = center.buffer(SIDE_RADIUS_M, quad_segs=32)
    sides = {"a": disc.intersection(half_plane(c, t, n, 1)), "b": disc.intersection(half_plane(c, t, n, -1))}

    result = {"lat": lat, "lon": lon, "side_a_azimuth_deg": frame["side_a_azimuth_deg"],
              "track_distance_m": frame["track_distance_m"], "rail_way_id": frame["rail_way_id"]}
    for r in POP_RADII_M:
        result[f"pop_{int(r)}m"] = round(population_in(center.buffer(r, quad_segs=32)), 1)
    for side, geom in sides.items():
        result[f"pop_500m_{side}"] = round(population_in(geom), 1)

    att = attractors()
    idx = att["point_tree"].query(disc, predicate="intersects")
    pts = att["points"].iloc[idx]
    xy = np.column_stack([pts.geometry.x.values, pts.geometry.y.values])
    side_of = np.where((xy - c) @ n >= 0, "a", "b")
    counts = {cat: {"a": 0, "b": 0} for cat in CATEGORIES}
    for cat, side in zip(pts["category"].values, side_of):
        counts[cat][side] += 1
    result["attractors_500m"] = counts

    areas = {cat: {"a": 0.0, "b": 0.0} for cat in AREA_CATEGORIES}
    idx = att["area_tree"].query(disc, predicate="intersects")
    polys = att["areas"].iloc[idx]
    for cat in AREA_CATEGORIES:
        geoms = polys.geometry.values[polys["category"].values == cat]
        if len(geoms) == 0:
            continue
        merged = shapely.union_all(geoms)
        for side, geom in sides.items():
            areas[cat][side] = merged.intersection(geom).area
    result["area_m2_500m"] = {cat: {s: round(v) for s, v in sv.items()} for cat, sv in areas.items()}
    return result


def main():
    from detour import TEST_POINTS
    points = TEST_POINTS
    if len(sys.argv) == 3:
        points = [(float(sys.argv[1]), float(sys.argv[2]))]
    t0 = time.time()
    population(), attractors()
    print(f"load {time.time() - t0:.1f}s", file=sys.stderr)
    for lat, lon in points:
        t1 = time.time()
        r = exposure(lat, lon)
        r["runtime_s"] = round(time.time() - t1, 3)
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
