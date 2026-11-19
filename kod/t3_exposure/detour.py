import json
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import substring

sys.path.insert(0, str(Path(__file__).resolve().parent))
from context import crosses_rail, distance_to_rail, graph, rails, to_latlon, track_frame

OFFSET_M = 30.0
OFFSET_STEP_M = 10.0
MAX_OFFSET_M = 300.0
MIN_CLEARANCE_M = 8.0
SNAP_RADIUS_M = 300.0
SNAP_CANDIDATES = 4

TEST_POINTS = [
    (51.1334333, 16.9452154),
    (51.1096478, 16.9952301),
    (51.1207612, 16.9526030),
    (51.0645342, 17.0118731),
    (51.1156206, 16.9877950),
]


def snap(p):
    gr = graph()
    found = gr["snap_tree"].query(p.buffer(SNAP_RADIUS_M))
    if len(found) == 0:
        return []
    idx = gr["snap_index"][found]
    geoms = gr["geoms"][idx]
    cands = []
    for k in np.argsort(shapely.distance(geoms, p)):
        geom = geoms[k]
        along = geom.project(p)
        q = geom.interpolate(along)
        if crosses_rail(LineString([p, q])):
            continue
        row = gr["edges"].iloc[idx[k]]
        cands.append({"edge": int(idx[k]), "u": int(row["u"]), "v": int(row["v"]), "point": q,
                      "along": along, "access_m": p.distance(q), "length": geom.length})
        if len(cands) == SNAP_CANDIDATES:
            break
    return cands


def side_point(center, normal, sign):
    d = OFFSET_M
    while d <= MAX_OFFSET_M:
        p = Point(center + sign * d * normal)
        if distance_to_rail(p) >= MIN_CLEARANCE_M:
            cands = snap(p)
            if cands:
                return p, d, cands
        d += OFFSET_STEP_M
    return Point(center + sign * OFFSET_M * normal), None, []


def tracks_crossed(line):
    r = rails()
    hits = r["at_grade_tree"].query(line, predicate="intersects")
    return len(set(r["at_grade_way_ids"][hits]))


def add_virtual(g, name, cands):
    for i, c in enumerate(cands):
        for node, along in ((c["u"], c["along"]), (c["v"], c["length"] - c["along"])):
            w = c["access_m"] + along
            if not g.has_edge(name, node) or g[name][node]["length"] > w:
                g.add_edge(name, node, length=w, cand=i)


def add_direct(g, cands_a, cands_b):
    for i, ca in enumerate(cands_a):
        for j, cb in enumerate(cands_b):
            if ca["edge"] != cb["edge"]:
                continue
            w = ca["access_m"] + cb["access_m"] + abs(ca["along"] - cb["along"])
            if not g.has_edge("A", "B") or g["A"]["B"]["length"] > w:
                g.add_edge("A", "B", length=w, cand=(i, j))


def oriented_edge_coords(edge_idx, start_node):
    gr = graph()
    coords = list(gr["geoms"][edge_idx].coords)
    if int(gr["edges"]["u"].values[edge_idx]) != start_node:
        coords.reverse()
    return coords


def snap_to_node(c, node):
    geom = graph()["geoms"][c["edge"]]
    if node == c["u"]:
        return list(substring(geom, 0, c["along"]).coords)[::-1]
    return list(substring(geom, c["along"], geom.length).coords)


def path_geometry(g, path, cands_a, cands_b, a, b):
    if path == ["A", "B"]:
        i, j = g["A"]["B"]["cand"]
        geom = graph()["geoms"][cands_a[i]["edge"]]
        mid = list(substring(geom, cands_a[i]["along"], cands_b[j]["along"]).coords)
        return LineString([a.coords[0], *mid, b.coords[0]]), cands_a[i], cands_b[j]
    ca = cands_a[g["A"][path[1]]["cand"]]
    cb = cands_b[g[path[-2]]["B"]["cand"]]
    coords = [a.coords[0], *snap_to_node(ca, path[1])]
    for u, v in zip(path[1:-2], path[2:-1]):
        coords.extend(oriented_edge_coords(g.edges[u, v]["idx"], u)[1:])
    coords.extend(snap_to_node(cb, path[-2])[::-1][1:])
    coords.append(b.coords[0])
    return LineString(coords), ca, cb


def crossing_used(line, center):
    r = rails()
    segs = r["segments"]
    hits = r["tree"].query(line, predicate="intersects")
    best = None
    for h in hits:
        inter = shapely.intersection(segs.geometry.values[h], line)
        if inter.is_empty:
            continue
        p = inter.centroid
        dist = p.distance(Point(center))
        if best is None or dist < best[0]:
            best = (dist, p, bool(segs["grade_separated"].values[h]))
    if best is None:
        return None
    dist, p, rail_lifted = best
    gr = graph()
    edges = gr["edges"]
    near_legal = False
    for i in gr["tree"].query(p.buffer(1.0)):
        geom = gr["geoms"][i]
        for end, node in ((geom.coords[0], edges["u"].values[i]), (geom.coords[-1], edges["v"].values[i])):
            if Point(end).distance(p) < 1.0 and int(node) in gr["legal_nodes"]:
                near_legal = True
    kind = "level_crossing" if near_legal and not rail_lifted else "grade_separated"
    lat, lon = to_latlon(p.x, p.y)
    return {"lat": round(lat, 7), "lon": round(lon, 7), "type": kind, "distance_from_point_m": round(dist, 1)}


def to_wkt_4326(line):
    return shapely.to_wkt(
        shapely.transform(line, lambda xy: np.array([to_latlon(x, y)[::-1] for x, y in xy])),
        rounding_precision=7,
    )


def detour(lat, lon, with_path=False):
    frame = track_frame(lat, lon)
    a, off_a, cands_a = side_point(frame["center"], frame["normal"], 1)
    b, off_b, cands_b = side_point(frame["center"], frame["normal"], -1)
    straight = a.distance(b)
    result = {"lat": lat, "lon": lon, "straight_m": round(straight, 1), "offset_a_m": off_a,
              "offset_b_m": off_b, "tracks_crossed": tracks_crossed(LineString([a, b])),
              "side_a_azimuth_deg": frame["side_a_azimuth_deg"],
              "track_distance_m": frame["track_distance_m"], "rail_way_id": frame["rail_way_id"],
              "walk_m": None, "detour_m": None, "ratio": None, "reachable": False}
    if not cands_a or not cands_b:
        side = "A" if not cands_a else "B"
        result["reason"] = f"no legal walkable edge within {SNAP_RADIUS_M:.0f} m on side {side}"
        return result

    g = graph()["g"]
    try:
        add_virtual(g, "A", cands_a)
        add_virtual(g, "B", cands_b)
        add_direct(g, cands_a, cands_b)
        walk, path = nx.bidirectional_dijkstra(g, "A", "B", weight="length")
        line, ca, cb = path_geometry(g, path, cands_a, cands_b, a, b)
    except nx.NetworkXNoPath:
        result["reason"] = "sides not connected in legal walk network"
        return result
    finally:
        g.remove_nodes_from(["A", "B"])

    result.update({"walk_m": round(walk, 1), "detour_m": round(walk - straight, 1),
                   "ratio": round(walk / straight, 2), "reachable": True,
                   "access_a_m": round(ca["access_m"], 1), "access_b_m": round(cb["access_m"], 1),
                   "crossing_used": crossing_used(line, frame["center"])})
    if with_path:
        result["path_wkt_4326"] = to_wkt_4326(line)
    return result


def main():
    points = TEST_POINTS
    if len(sys.argv) == 3:
        points = [(float(sys.argv[1]), float(sys.argv[2]))]
    t0 = time.time()
    graph(), rails()
    print(f"load {time.time() - t0:.1f}s", file=sys.stderr)
    for lat, lon in points:
        t1 = time.time()
        r = detour(lat, lon)
        r["runtime_s"] = round(time.time() - t1, 3)
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
