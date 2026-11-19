import json
import math
import sys
import time

import geopandas as gpd
import numpy as np
import requests
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from common import DATA_DIR, OUT_DIR, ROOT, in_bbox, to_2180, to_4326

sys.path.insert(0, str(ROOT / "t1_candidates"))
from build_candidates import (grade_separated, intersection_points, is_set, load_crossing_nodes,  # noqa: E402
                              load_highways, load_rails)

SPACING_M = 60
THIN_M = 45
POP_RADIUS_M = 500
OVERPASS = "https://overpass-api.de/api/interpreter"


def official_points():
    rails = load_rails()
    highways = load_highways()
    official_nodes, _ = load_crossing_nodes()
    pts = [(Point(to_2180(lon, lat)), f"railway={tags['railway']}") for lat, lon, tags in official_nodes.values()]
    rail_list = list(rails.values())
    tree = STRtree([r["line"] for r in rail_list])
    for hw in highways.values():
        for idx in tree.query(hw["line"], predicate="intersects"):
            rail = rail_list[idx]
            if not (grade_separated(hw["tags"]) or grade_separated(rail["tags"])):
                continue
            kind = "underpass" if is_set(rail["tags"].get("bridge")) or is_set(hw["tags"].get("tunnel")) else "overpass"
            shared = [Point(to_2180(*hw["coords"][n])) for n in set(hw["nodes"]) & set(rail["nodes"])]
            for p in intersection_points(hw["line"].intersection(rail["line"])):
                if not any(p.distance(s) < 1 for s in shared):
                    pts.append((p, kind))
    return pts, rails


def bearing_deg(line, dist):
    a = line.interpolate(max(dist - 15, 0))
    b = line.interpolate(min(dist + 15, line.length))
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x))


def nearest_bearing(pt, lines, tree):
    idx = tree.nearest(pt)
    line = lines[idx]
    return bearing_deg(line, line.project(pt)), pt.distance(line)


def scan_points():
    rail = gpd.read_file(DATA_DIR / "rail_hazard.geojson").to_crs("EPSG:2180")
    samples = []
    for geom, usage, line_no in zip(rail.geometry, rail["usage"], rail["line_no"]):
        n = max(int(geom.length // SPACING_M), 0)
        for k in range(n + 1):
            d = min(SPACING_M / 2 + k * SPACING_M, geom.length)
            p = geom.interpolate(d)
            samples.append((p, bearing_deg(geom, d), usage, line_no))
    kept, tree_pts = [], []
    grid = {}
    for p, brg, usage, line_no in samples:
        key = (int(p.x // THIN_M), int(p.y // THIN_M))
        near = [q for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in grid.get((key[0] + dx, key[1] + dy), [])]
        if any(p.distance(q) < THIN_M for q in near):
            continue
        grid.setdefault(key, []).append(p)
        kept.append((p, brg, usage, line_no))
    pop = gpd.read_file(DATA_DIR / "exposure" / "population_grid250.gpkg")
    cent = pop.geometry.centroid
    cx, cy, cpop = np.array(cent.x), np.array(cent.y), pop["pop"].to_numpy(dtype=float)
    ctree = STRtree(list(cent))
    rows = []
    for p, brg, usage, line_no in kept:
        lon, lat = to_4326(p.x, p.y)
        if not in_bbox(lat, lon):
            continue
        idx = ctree.query(p.buffer(POP_RADIUS_M))
        d = np.hypot(cx[idx] - p.x, cy[idx] - p.y)
        rows.append({"lat": lat, "lon": lon, "x": p.x, "y": p.y, "bearing": brg, "usage": usage,
                     "line_no": line_no, "pop500": float(cpop[idx][d <= POP_RADIUS_M].sum())})
    return rows


def fetch_pl_rails(points, cache_name="pl_hazard_rails.json"):
    cache = DATA_DIR / "raw" / "ortho_meta" / cache_name
    if cache.exists():
        return json.loads(cache.read_text())
    parts = "".join(f"way[railway~\"^(rail|light_rail|narrow_gauge)$\"](around:60,{lat:.6f},{lon:.6f});" for lat, lon in points)
    query = f"[out:json][timeout:120];({parts});out geom;"
    for attempt in range(4):
        r = requests.post(OVERPASS, data={"data": query}, headers={"User-Agent": "dzika-sciezka-research/1.0"}, timeout=180)
        if r.ok:
            cache.write_bytes(r.content)
            return r.json()
        time.sleep(10 * (attempt + 1))
    r.raise_for_status()


def pl_hazard_points():
    dump = json.loads((DATA_DIR / "raw" / "osm_illegal_crossing_PL.json").read_text())
    near = {int(e["tags"]["id"]) for e in dump["elements"] if e["type"] == "r" and "rail" in e["tags"]["rail"].split(";")
            and int(e["tags"]["n"]) > 0}
    pts = []
    for el in dump["elements"]:
        if el["type"] not in ("node", "way") or el.get("tags", {}).get("hazard") != "illegal_crossing" or el["id"] not in near:
            continue
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lon = el.get("lon", el.get("center", {}).get("lon"))
        pts.append((f"{el['type']}/{el['id']}", lat, lon, el["tags"]))
    return pts


def dedupe(items, dist):
    kept = []
    for it in items:
        if all(math.dist((it["x"], it["y"]), (k["x"], k["y"])) > dist for k in kept):
            kept.append(it)
    return kept


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    off, rails = official_points()
    (OUT_DIR / "official_points.json").write_text(json.dumps([[p.x, p.y, k] for p, k in off]))
    print(f"official points: {len(off)}")

    osm_lines = [r["line"] for r in rails.values() if r["tags"].get("railway") in ("rail", "light_rail", "narrow_gauge")]
    osm_tree = STRtree(osm_lines)

    cand = json.loads((DATA_DIR / "candidates.geojson").read_text())["features"]
    positives = []
    for f in cand:
        pr = f["properties"]
        x, y = to_2180(pr["lon"], pr["lat"])
        brg, d = nearest_bearing(Point(x, y), osm_lines, osm_tree)
        positives.append({"tile_id": f"pos_{pr['id']}", "src": "t1_candidate", "ref": pr["id"], "lat": pr["lat"],
                          "lon": pr["lon"], "x": x, "y": y, "bearing": brg, "rail_dist": d})

    pl = pl_hazard_points()
    pl_rails = fetch_pl_rails([(lat, lon) for _, lat, lon, _ in pl])
    pl_lines = [LineString([to_2180(g["lon"], g["lat"]) for g in el["geometry"]]) for el in pl_rails["elements"]
                if el["type"] == "way" and len(el.get("geometry", [])) >= 2]
    pl_tree = STRtree(pl_lines)
    pl_items = []
    for ref, lat, lon, tags in pl:
        x, y = to_2180(lon, lat)
        brg, d = nearest_bearing(Point(x, y), pl_lines, pl_tree)
        pl_items.append({"tile_id": f"pos_{ref.replace('/', '')}", "src": "osm_hazard_pl", "ref": ref, "lat": lat,
                         "lon": lon, "x": x, "y": y, "bearing": brg, "rail_dist": d, "in_bbox": in_bbox(lat, lon)})
    pl_items = [p for p in dedupe(pl_items, 25)
                if not any(math.dist((p["x"], p["y"]), (q["x"], q["y"])) <= 25 for q in positives)]
    print(f"PL hazard points near rail: {len(pl)}, after 25 m dedupe and T1 overlap removal: {len(pl_items)}")
    positives += pl_items

    scan = scan_points()
    for i, s in enumerate(scan):
        s["tile_id"] = f"scan_{i:05d}"
    pops = np.array([s["pop500"] for s in scan])
    print(f"scan points after thinning (bbox): {len(scan)}")
    for thr in (0, 50, 100, 200, 300, 500, 800, 1000):
        print(f"  pop500 >= {thr}: {(pops >= thr).sum()}")
    (OUT_DIR / "positives_index.json").write_text(json.dumps(positives, indent=0))
    (OUT_DIR / "scan_all_index.json").write_text(json.dumps(scan))


if __name__ == "__main__":
    main()
