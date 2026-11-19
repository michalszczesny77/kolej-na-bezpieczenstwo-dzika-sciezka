import csv
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, MultiPoint, Point
from shapely.strtree import STRtree

from fetch_osm import BBOX, RAW_DIR, fetch, fetch_highway_tiles

DATA_DIR = RAW_DIR.parent
LINK_SCRIPT = Path(__file__).resolve().parents[1] / "puwg_geoportal_link.py"

SHARED_NODE_HIGHWAYS = {"path", "footway", "track", "steps", "cycleway", "service", "unclassified", "residential", "bridleway"}
INTERSECTION_HIGHWAYS = {"path", "footway", "track"}
STUB_HIGHWAYS = {"path", "footway", "track"}
VEHICLE_HIGHWAYS = {"service", "unclassified", "residential"}
SIDING_SERVICES = {"spur", "yard", "siding", "crossover"}
IGNORED_HIGHWAYS = {"construction", "proposed", "abandoned", "razed", "platform", "disused", "planned"}

INFORMAL_MAX_DIST = 15
INFORMAL_ON_OFFICIAL_DIST = 5
OFFICIAL_EXCLUSION_DIST = 30
STUB_RAIL_DIST = 10
STUB_PAIR_MAX_DIST = 60
STUB_PLATFORM_DIST = 10
DEDUPE_DIST = 25
SOURCE_PRIORITY = ["hazard_tag", "shared_node", "informal_tag", "geometric_intersection", "deadend_stubs"]

to_2180 = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True).transform
to_4326 = Transformer.from_crs("EPSG:2180", "EPSG:4326", always_xy=True).transform


def is_set(value):
    return value is not None and value not in ("no", "0")


def grade_separated(tags):
    return (is_set(tags.get("bridge")) or is_set(tags.get("tunnel")) or tags.get("layer", "0") != "0"
            or tags.get("level", "0") != "0")


def siding(tags):
    return tags.get("service") in SIDING_SERVICES or tags.get("usage") == "industrial"


def project_line(geometry):
    return LineString([to_2180(p["lon"], p["lat"]) for p in geometry])


def in_bbox(lat, lon):
    return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]


def load_rails():
    data = fetch("wro_rails")
    rails, line_refs = {}, defaultdict(set)
    for el in data["elements"]:
        if el["type"] == "relation":
            for m in el.get("members", []):
                if m["type"] == "way" and el["tags"].get("ref"):
                    line_refs[m["ref"]].add(el["tags"]["ref"])
    for el in data["elements"]:
        if el["type"] == "way" and len(el.get("geometry", [])) >= 2:
            rails[el["id"]] = {
                "tags": el["tags"],
                "nodes": el["nodes"],
                "line": project_line(el["geometry"]),
                "line_refs": sorted(line_refs.get(el["id"], [])),
            }
    return rails


def load_highways():
    highways = {}
    for path in fetch_highway_tiles():
        for el in json.loads(path.read_text())["elements"]:
            if el["type"] != "way" or el["id"] in highways or len(el.get("geometry", [])) < 2:
                continue
            if el["tags"].get("highway") in IGNORED_HIGHWAYS or el["tags"].get("area") == "yes":
                continue
            highways[el["id"]] = {
                "tags": el["tags"],
                "nodes": el["nodes"],
                "coords": {n: (g["lon"], g["lat"]) for n, g in zip(el["nodes"], el["geometry"])},
                "line": project_line(el["geometry"]),
            }
    return highways


def load_platforms():
    lines = [project_line(el["geometry"]) for el in fetch("wro_platforms")["elements"]
             if el["type"] == "way" and len(el.get("geometry", [])) >= 2]
    return STRtree(lines)


def load_crossing_nodes():
    official, hazard = {}, {}
    for el in fetch("wro_crossings_hazard")["elements"]:
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lon = el.get("lon", el.get("center", {}).get("lon"))
        if lat is None:
            continue
        key = (el["type"], el["id"])
        if el["tags"].get("hazard") == "illegal_crossing":
            hazard[key] = (lat, lon, el["tags"])
        elif el["tags"].get("railway") in ("crossing", "level_crossing"):
            official[key] = (lat, lon, el["tags"])
    dump = json.loads((RAW_DIR / "osm_illegal_crossing_PL.json").read_text())
    for el in dump["elements"]:
        if el.get("tags", {}).get("hazard") != "illegal_crossing":
            continue
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lon = el.get("lon", el.get("center", {}).get("lon"))
        if lat is not None and in_bbox(lat, lon):
            hazard.setdefault((el["type"], el["id"]), (lat, lon, el["tags"]))
    return official, hazard


def intersection_points(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == "Point":
        return [geom]
    if geom.geom_type in ("MultiPoint", "GeometryCollection"):
        return [p for g in geom.geoms for p in intersection_points(g)]
    if geom.geom_type in ("LineString", "MultiLineString"):
        return [geom.interpolate(0.5, normalized=True)]
    return []


def build():
    rails = load_rails()
    highways = load_highways()
    official_nodes, hazard_nodes = load_crossing_nodes()
    platform_tree = load_platforms()

    rail_ids = list(rails)
    rail_tree = STRtree([rails[r]["line"] for r in rail_ids])
    rail_node_ids = {n for r in rails.values() for n in r["nodes"]}

    official = []
    for (typ, oid), (lat, lon, tags) in official_nodes.items():
        official.append((Point(to_2180(lon, lat)), f"railway={tags['railway']}", f"{typ}/{oid}"))

    for hid, hw in highways.items():
        for idx in rail_tree.query(hw["line"], predicate="intersects"):
            rail = rails[rail_ids[idx]]
            if not (grade_separated(hw["tags"]) or grade_separated(rail["tags"])):
                continue
            if is_set(rail["tags"].get("bridge")) or is_set(hw["tags"].get("tunnel")):
                kind = "underpass"
            elif hw["tags"].get("highway") in ("footway", "path", "steps", "cycleway") and is_set(hw["tags"].get("bridge")):
                kind = "footbridge"
            else:
                kind = "overpass"
            shared_pts = [Point(to_2180(*hw["coords"][n])) for n in set(hw["nodes"]) & set(rail["nodes"])]
            for p in intersection_points(hw["line"].intersection(rail["line"])):
                if not any(p.distance(s) < 1 for s in shared_pts):
                    official.append((p, kind, f"way/{hid}"))
    official_tree = STRtree([o[0] for o in official])

    def nearest_official(pt):
        idx = official_tree.nearest(pt)
        return official[idx], pt.distance(official[idx][0])

    def near_official(pt, dist):
        return len(official_tree.query(pt.buffer(dist), predicate="intersects")) > 0

    raw = []

    def add(pt, source, osm_ids, extra=None):
        raw.append({"pt": pt, "sources": {source}, "osm_ids": set(osm_ids), "highway": set(extra or [])})

    for key, (lat, lon, tags) in hazard_nodes.items():
        add(Point(to_2180(lon, lat)), "hazard_tag", [f"{key[0]}/{key[1]}"], [tags.get("highway", "")])

    official_node_ids = {oid for (typ, oid) in official_nodes if typ == "node"}
    node_rail_ways = defaultdict(list)
    for rid, rail in rails.items():
        for n in rail["nodes"]:
            node_rail_ways[n].append(rid)
    shared_seen = set()
    for hid, hw in highways.items():
        if hw["tags"].get("highway") not in SHARED_NODE_HIGHWAYS:
            continue
        for n in hw["nodes"]:
            if n not in rail_node_ids or n in official_node_ids:
                continue
            if hw["tags"]["highway"] in VEHICLE_HIGHWAYS and all(siding(rails[r]["tags"]) for r in node_rail_ways[n]):
                continue
            if grade_separated(hw["tags"]) or any(grade_separated(rails[r]["tags"]) for r in node_rail_ways[n]):
                continue
            lon, lat = hw["coords"][n]
            if near_official(Point(to_2180(lon, lat)), OFFICIAL_EXCLUSION_DIST):
                continue
            if n in shared_seen:
                continue
            shared_seen.add(n)
            add(Point(to_2180(lon, lat)), "shared_node", [f"node/{n}", f"way/{hid}"] + [f"way/{r}" for r in node_rail_ways[n]], [hw["tags"]["highway"]])

    for hid, hw in highways.items():
        if hw["tags"].get("informal") != "yes":
            continue
        line = hw["line"]
        hits = []
        for idx in rail_tree.query(line, predicate="intersects"):
            if grade_separated(hw["tags"]) or grade_separated(rails[rail_ids[idx]]["tags"]):
                continue
            hits.extend((p, rail_ids[idx]) for p in intersection_points(line.intersection(rails[rail_ids[idx]]["line"]))
                        if not near_official(p, INFORMAL_ON_OFFICIAL_DIST))
        if not hits:
            for end in (Point(line.coords[0]), Point(line.coords[-1])):
                idx = rail_tree.nearest(end)
                if end.distance(rails[rail_ids[idx]]["line"]) <= INFORMAL_MAX_DIST and not near_official(end, OFFICIAL_EXCLUSION_DIST):
                    hits.append((end, rail_ids[idx]))
        for p, rid in hits:
            add(p, "informal_tag", [f"way/{hid}", f"way/{rid}"], [hw["tags"]["highway"]])

    for hid, hw in highways.items():
        if hw["tags"].get("highway") not in INTERSECTION_HIGHWAYS or grade_separated(hw["tags"]):
            continue
        hw_nodes = set(hw["nodes"])
        for idx in rail_tree.query(hw["line"], predicate="intersects"):
            rid = rail_ids[idx]
            rail = rails[rid]
            if grade_separated(rail["tags"]):
                continue
            shared = hw_nodes & set(rail["nodes"])
            shared_pts = [Point(to_2180(*hw["coords"][n])) for n in shared]
            for p in intersection_points(hw["line"].intersection(rail["line"])):
                if any(p.distance(s) < 1 for s in shared_pts):
                    continue
                if near_official(p, OFFICIAL_EXCLUSION_DIST):
                    continue
                add(p, "geometric_intersection", [f"way/{hid}", f"way/{rid}"], [hw["tags"]["highway"]])

    node_use = Counter(n for hw in highways.values() for n in hw["nodes"])
    stubs = []
    for hid, hw in highways.items():
        if hw["tags"].get("highway") not in STUB_HIGHWAYS or grade_separated(hw["tags"]) or hw["nodes"][0] == hw["nodes"][-1]:
            continue
        for n in (hw["nodes"][0], hw["nodes"][-1]):
            if node_use[n] != 1 or n in rail_node_ids:
                continue
            pt = Point(to_2180(*hw["coords"][n]))
            if len(platform_tree.query(pt.buffer(STUB_PLATFORM_DIST), predicate="intersects")):
                continue
            idx = rail_tree.nearest(pt)
            if pt.distance(rails[rail_ids[idx]]["line"]) <= STUB_RAIL_DIST:
                stubs.append((pt, hid, n))
    stub_tree = STRtree([s[0] for s in stubs])
    paired = set()
    for i, (pt, hid, n) in enumerate(stubs):
        for j in stub_tree.query(pt.buffer(STUB_PAIR_MAX_DIST), predicate="intersects"):
            if j <= i or stubs[j][1] == hid or (i, j) in paired:
                continue
            other = stubs[j][0]
            link = LineString([pt, other])
            crossed = [rail_ids[k] for k in rail_tree.query(link, predicate="intersects")
                       if not grade_separated(rails[rail_ids[k]]["tags"])]
            if not crossed:
                continue
            mid = link.interpolate(0.5, normalized=True)
            if near_official(mid, OFFICIAL_EXCLUSION_DIST):
                continue
            paired.add((i, j))
            ids = [f"way/{hid}", f"node/{n}", f"way/{stubs[j][1]}", f"node/{stubs[j][2]}"] + [f"way/{r}" for r in crossed]
            add(mid, "deadend_stubs", ids, [highways[hid]["tags"]["highway"], highways[stubs[j][1]]["tags"]["highway"]])

    raw = [c for c in raw if in_bbox(*reversed(to_4326(c["pt"].x, c["pt"].y)))]
    per_source = Counter(next(iter(c["sources"])) for c in raw)
    clusters = dedupe(raw)

    features, rows = [], []
    for i, c in enumerate(sorted(clusters, key=lambda c: (-c["pt"].y, c["pt"].x)), start=1):
        if c["sources"] == {"geometric_intersection"}:
            continue
        pt = c["pt"]
        lon, lat = to_4326(pt.x, pt.y)
        ridx = rail_tree.nearest(pt)
        rid = rail_ids[ridx]
        rtags = rails[rid]["tags"]
        (opt, okind, oid), odist = nearest_official(pt)
        props = {
            "id": f"T1-{i:04d}",
            "lat": round(lat, 7),
            "lon": round(lon, 7),
            "sources": ";".join(s for s in SOURCE_PRIORITY if s in c["sources"]),
            "n_sources": len(c["sources"]),
            "osm_ids": ";".join(sorted(c["osm_ids"])),
            "highway_types": ";".join(sorted(h for h in c["highway"] if h)),
            "rail_way_id": rid,
            "rail_dist_m": round(pt.distance(rails[rid]["line"]), 1),
            "rail_ref": rtags.get("ref", ""),
            "rail_line_refs": ";".join(rails[rid]["line_refs"]),
            "rail_name": rtags.get("name", ""),
            "rail_usage": rtags.get("usage", ""),
            "rail_service": rtags.get("service", ""),
            "rail_maxspeed": rtags.get("maxspeed", ""),
            "rail_electrified": rtags.get("electrified", ""),
            "rail_tracks": rtags.get("tracks", ""),
            "nearest_official_m": round(odist, 1),
            "nearest_official_type": okind,
            "nearest_official_osm": oid,
            "geoportal_url": geoportal_link(lat, lon),
        }
        rows.append(props)
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [props["lon"], props["lat"]]}, "properties": props})

    (DATA_DIR / "candidates.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False))
    with open(DATA_DIR / "candidates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print("raw per source:", dict(per_source))
    print("clusters containing source:", dict(Counter(s for r in rows for s in r["sources"].split(";"))))
    print("total after dedupe:", len(rows))
    print("official crossing points:", Counter(o[1] for o in official))


def dedupe(raw):
    tree = STRtree([c["pt"] for c in raw])
    parent = list(range(len(raw)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, c in enumerate(raw):
        for j in tree.query(c["pt"].buffer(DEDUPE_DIST), predicate="intersects"):
            if j != i and c["pt"].distance(raw[j]["pt"]) <= DEDUPE_DIST:
                parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(len(raw)):
        groups[find(i)].append(raw[i])
    clusters = []
    for members in groups.values():
        best = min(SOURCE_PRIORITY.index(s) for m in members for s in m["sources"])
        anchor = [m["pt"] for m in members if SOURCE_PRIORITY[best] in m["sources"]]
        pt = anchor[0] if len(anchor) == 1 else MultiPoint(anchor).centroid
        clusters.append({
            "pt": pt,
            "sources": set().union(*(m["sources"] for m in members)),
            "osm_ids": set().union(*(m["osm_ids"] for m in members)),
            "highway": set().union(*(m["highway"] for m in members)),
        })
    return clusters


def geoportal_link(lat, lon):
    out = subprocess.run(["python3", str(LINK_SCRIPT), f"{lat:.7f}", f"{lon:.7f}"], capture_output=True, text=True, check=True)
    return out.stdout.strip()


if __name__ == "__main__":
    build()
