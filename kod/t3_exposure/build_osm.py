import json
import sys
import time
from collections import Counter
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmium
import pyogrio
import shapely
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    ATTRACTOR_AREAS_FILE,
    ATTRACTORS_FILE,
    CRS,
    GRAPH_FILE,
    OUT,
    PBF,
    RAIL_FILE,
    bbox_with_margin,
    in_bbox,
    to_2180,
)

WALK_HIGHWAYS = {
    "footway", "path", "pedestrian", "steps", "living_street", "residential", "service",
    "unclassified", "tertiary", "tertiary_link", "secondary", "secondary_link", "primary",
    "primary_link", "trunk", "trunk_link", "track", "cycleway", "bridleway", "corridor",
    "platform", "road", "elevator",
}
RAIL_BARRIERS = {"rail", "light_rail", "narrow_gauge", "subway", "preserved"}
FOOT_OK = {"yes", "designated", "permissive"}
PUBLIC_ROADS = {
    "residential", "living_street", "unclassified", "tertiary", "tertiary_link", "secondary",
    "secondary_link", "primary", "primary_link", "trunk", "trunk_link",
}
NODE_KEYS = ("railway", "crossing", "hazard", "access", "foot", "informal", "crossing:barrier", "name")
WAY_KEYS = ("highway", "railway", "bridge", "tunnel", "layer", "foot", "access", "informal", "name", "service", "usage")
AREA_KEYS = ("landuse", "leisure", "amenity", "shop", "office", "man_made", "railway", "public_transport", "highway")
SPORT = {"sports_centre", "stadium", "pitch", "swimming_pool", "fitness_centre", "track", "sports_hall"}
SCHOOL = {"school", "kindergarten", "college", "university"}


def walkable(tags):
    hw = tags.get("highway")
    is_platform = tags.get("railway") == "platform" or tags.get("public_transport") == "platform"
    if hw not in WALK_HIGHWAYS and not is_platform:
        return False
    foot = tags.get("foot")
    if foot in ("no", "use_sidepath"):
        return False
    if tags.get("access") in ("no", "private") and foot not in FOOT_OK:
        return False
    if tags.get("motorroad") == "yes" and foot not in FOOT_OK:
        return False
    return True


def grade_separated(tags):
    return tags.get("bridge", "no") != "no" or tags.get("tunnel", "no") != "no"


def layer(tags):
    try:
        return int(float(tags.get("layer", "0").split(";")[0]))
    except ValueError:
        return 0


def legal_crossing(tags):
    if tags.get("railway") not in ("crossing", "level_crossing"):
        return False
    if tags.get("crossing") in ("no", "informal"):
        return False
    if tags.get("access") in ("no", "private") or tags.get("foot") == "no":
        return False
    if tags.get("hazard") == "illegal_crossing" or tags.get("informal") == "yes":
        return False
    return True


def categorize(tags):
    railway = tags.get("railway")
    pt = tags.get("public_transport")
    if railway in ("station", "halt") or (pt == "station" and tags.get("train") == "yes"):
        return "station", railway or pt
    if pt == "platform" or tags.get("highway") == "bus_stop" or railway in ("platform", "tram_stop"):
        return "stop", railway or tags.get("highway") or pt
    if tags.get("amenity") in SCHOOL:
        return "school", tags["amenity"]
    if "shop" in tags or tags.get("amenity") == "marketplace":
        return "shop", tags.get("shop", "marketplace")
    if tags.get("landuse") == "allotments":
        return "allotments", "allotments"
    if tags.get("leisure") == "park":
        return "park", "park"
    if tags.get("leisure") in SPORT:
        return "sport", tags["leisure"]
    if tags.get("landuse") in ("industrial", "commercial") or "office" in tags or tags.get("man_made") == "works":
        return "workplace", tags.get("landuse") or ("office" if "office" in tags else "works")
    if tags.get("landuse") == "residential":
        return "residential", "residential"
    return None


def project(lon, lat):
    return to_2180.transform(lon, lat)


def read_pbf(box):
    nodes, walk_ways, rail_ways, node_attr, area_attr = {}, [], [], [], []
    wkb = osmium.geom.WKBFactory()
    fp = (
        osmium.FileProcessor(str(PBF))
        .with_locations()
        .with_areas(osmium.filter.KeyFilter(*AREA_KEYS))
        .with_filter(osmium.filter.EmptyTagFilter())
    )
    for obj in fp:
        if obj.is_node():
            lat, lon = obj.location.lat, obj.location.lon
            if not in_bbox(lat, lon, box):
                continue
            tags = dict(obj.tags)
            kept = {k: tags[k] for k in NODE_KEYS if k in tags}
            if kept:
                nodes[obj.id] = kept
            cat = categorize(tags)
            if cat:
                node_attr.append(("n", obj.id, cat[0], cat[1], tags.get("name"), lon, lat))
        elif obj.is_way():
            tags = dict(obj.tags)
            is_walk = walkable(tags)
            is_rail = tags.get("railway") in RAIL_BARRIERS
            if not (is_walk or is_rail):
                continue
            refs, coords = [], []
            for nr in obj.nodes:
                if nr.location.valid():
                    refs.append(nr.ref)
                    coords.append((nr.location.lon, nr.location.lat))
            if len(refs) < 2 or not any(in_bbox(la, lo, box) for lo, la in coords):
                continue
            record = (obj.id, refs, coords, {k: tags[k] for k in WAY_KEYS if k in tags})
            if is_walk:
                walk_ways.append(record)
            if is_rail:
                rail_ways.append(record)
        elif obj.is_area():
            tags = dict(obj.tags)
            cat = categorize(tags)
            if not cat:
                continue
            try:
                geom = shapely.from_wkb(wkb.create_multipolygon(obj))
            except RuntimeError:
                continue
            rep = geom.representative_point()
            if not in_bbox(rep.y, rep.x, box):
                continue
            kind = "w" if obj.from_way() else "r"
            area_attr.append((kind, obj.orig_id(), cat[0], cat[1], tags.get("name"), geom))
    return nodes, walk_ways, rail_ways, node_attr, area_attr


def build_rails(rail_ways):
    rows = []
    for way_id, refs, coords, tags in rail_ways:
        xy = [project(lon, lat) for lon, lat in coords]
        sep = grade_separated(tags)
        for i in range(len(refs) - 1):
            rows.append({
                "way_id": way_id, "u": refs[i], "v": refs[i + 1], "railway": tags.get("railway"),
                "service": tags.get("service"), "usage": tags.get("usage"),
                "grade_separated": sep, "layer": layer(tags),
                "geometry": LineString([xy[i], xy[i + 1]]),
            })
    return gpd.GeoDataFrame(rows, crs=CRS)


def find_blocks(walk_ways, rails, node_tags, coords_of):
    at_grade = rails[~rails["grade_separated"]]
    rail_nodes = set(at_grade["u"]) | set(at_grade["v"])
    contact_highways = {}
    for _, refs, _, tags in walk_ways:
        for r in refs:
            if r in rail_nodes:
                contact_highways.setdefault(r, set()).add(tags.get("highway") or tags.get("railway") or "platform")
    contacts = set(contact_highways)
    inferred = {
        n for n in contacts
        if not node_tags.get(n) and contact_highways[n] & PUBLIC_ROADS
    }
    blocked_nodes = {n for n in contacts if not legal_crossing(node_tags.get(n, {})) and n not in inferred}

    seg_way, seg_a, seg_b, seg_geom, seg_sep, seg_layer = [], [], [], [], [], []
    for idx, (_, refs, _, tags) in enumerate(walk_ways):
        sep, lay = grade_separated(tags), layer(tags)
        for i in range(len(refs) - 1):
            seg_way.append(idx)
            seg_a.append(refs[i])
            seg_b.append(refs[i + 1])
            seg_geom.append(LineString([coords_of[refs[i]], coords_of[refs[i + 1]]]))
            seg_sep.append(sep)
            seg_layer.append(lay)
    tree = shapely.STRtree(at_grade.geometry.values)
    walk_idx, rail_idx = tree.query(np.array(seg_geom, dtype=object), predicate="intersects")
    rail_u, rail_v, rail_layer = at_grade["u"].values, at_grade["v"].values, at_grade["layer"].values
    blocked_segments, inferred_segments = set(), set()
    for w, r in zip(walk_idx, rail_idx):
        if seg_sep[w] or seg_layer[w] != rail_layer[r]:
            continue
        if {seg_a[w], seg_b[w]} & {rail_u[r], rail_v[r]}:
            continue
        key = (seg_way[w], seg_a[w], seg_b[w])
        if walk_ways[seg_way[w]][3].get("highway") in PUBLIC_ROADS:
            inferred_segments.add(key)
        else:
            blocked_segments.add(key)

    legal = contacts - blocked_nodes
    stats = {
        "rail_walk_contact_nodes": len(contacts),
        "legal_crossing_nodes": len(legal),
        "legal_inferred_untagged_road_crossings": len(inferred),
        "blocked_contact_nodes": len(blocked_nodes),
        "blocked_untagged_contacts": sum(1 for n in blocked_nodes if "railway" not in node_tags.get(n, {})),
        "blocked_geometric_crossings": len(blocked_segments),
        "legal_inferred_geometric_road_crossings": len(inferred_segments),
    }
    return blocked_nodes, blocked_segments, legal, inferred, contact_highways, stats


def split_pieces(walk_ways, blocked_nodes, blocked_segments):
    pieces = []
    for idx, (way_id, refs, _, tags) in enumerate(walk_ways):
        current = []
        for i, ref in enumerate(refs):
            if ref in blocked_nodes:
                if len(current) > 1:
                    pieces.append((way_id, current, tags))
                current = []
                continue
            if current and (idx, current[-1], ref) in blocked_segments:
                if len(current) > 1:
                    pieces.append((way_id, current, tags))
                current = []
            current.append(ref)
        if len(current) > 1:
            pieces.append((way_id, current, tags))
    return pieces


def build_edges(pieces, coords_of, legal_nodes):
    use = Counter()
    for _, refs, _ in pieces:
        use.update(refs)
    edges = []
    for way_id, refs, tags in pieces:
        start = 0
        for i in range(1, len(refs)):
            if i == len(refs) - 1 or use[refs[i]] > 1 or refs[i] in legal_nodes:
                part = refs[start:i + 1]
                if part[0] != part[-1] or len(part) > 2:
                    line = LineString([coords_of[r] for r in part])
                    edges.append({
                        "u": part[0], "v": part[-1], "way_id": way_id,
                        "highway": tags.get("highway") or tags.get("railway") or "platform",
                        "grade_separated": grade_separated(tags),
                        "length": line.length, "geometry": line,
                    })
                start = i
    edges = gpd.GeoDataFrame(edges, crs=CRS)
    edges = edges[edges["u"] != edges["v"]]
    return edges


def build_nodes(edges, coords_of, node_tags, legal_nodes):
    ids = np.unique(np.concatenate([edges["u"].values, edges["v"].values]))
    rows = []
    for n in ids:
        tags = node_tags.get(n, {})
        rows.append({
            "node_id": int(n), "legal_rail_crossing": n in legal_nodes,
            "railway": tags.get("railway"), "geometry": Point(coords_of[n]),
        })
    return gpd.GeoDataFrame(rows, crs=CRS)


def write_attractors(node_attr, area_attr):
    points, areas = [], []
    for kind, osm_id, cat, sub, name, lon, lat in node_attr:
        points.append({"osm": f"{kind}{osm_id}", "category": cat, "subtype": sub, "name": name,
                       "area_m2": 0.0, "geometry": Point(lon, lat)})
    for kind, osm_id, cat, sub, name, geom in area_attr:
        g2180 = shapely.transform(geom, lambda a: np.column_stack(to_2180.transform(a[:, 0], a[:, 1])))
        rep = geom.representative_point()
        points.append({"osm": f"{kind}{osm_id}", "category": cat, "subtype": sub, "name": name,
                       "area_m2": round(g2180.area, 1), "geometry": rep})
        areas.append({"osm": f"{kind}{osm_id}", "category": cat, "subtype": sub, "name": name,
                      "area_m2": round(g2180.area, 1), "geometry": g2180})
    pts = gpd.GeoDataFrame(points, crs="EPSG:4326")
    if ATTRACTORS_FILE.exists():
        ATTRACTORS_FILE.unlink()
    pyogrio.write_dataframe(pts, ATTRACTORS_FILE, driver="GeoJSON")
    pyogrio.write_dataframe(gpd.GeoDataFrame(areas, crs=CRS), ATTRACTOR_AREAS_FILE, layer="areas")
    return pts["category"].value_counts().to_dict()


def main():
    t0 = time.time()
    box = bbox_with_margin()
    node_tags, walk_ways, rail_ways, node_attr, area_attr = read_pbf(box)
    t1 = time.time()
    print(f"read pbf {t1 - t0:.0f}s: walk_ways={len(walk_ways)} rail_ways={len(rail_ways)} "
          f"node_attr={len(node_attr)} area_attr={len(area_attr)}")

    coords_of = {}
    for _, refs, coords, _ in walk_ways:
        for ref, (lon, lat) in zip(refs, coords):
            if ref not in coords_of:
                coords_of[ref] = project(lon, lat)

    OUT.mkdir(parents=True, exist_ok=True)
    rails = build_rails(rail_ways)
    blocked_nodes, blocked_segments, legal_nodes, inferred, contact_highways, stats = find_blocks(
        walk_ways, rails, node_tags, coords_of)
    pieces = split_pieces(walk_ways, blocked_nodes, blocked_segments)
    edges = build_edges(pieces, coords_of, legal_nodes)
    nodes = build_nodes(edges, coords_of, node_tags, legal_nodes)

    contacts = gpd.GeoDataFrame(
        [{"node_id": int(n), "status": "blocked" if n in blocked_nodes else "inferred_legal" if n in inferred else "legal",
          "highways": ";".join(sorted(contact_highways[n])),
          **{k: node_tags.get(n, {}).get(k) for k in ("railway", "crossing", "hazard")},
          "geometry": Point(coords_of[n])} for n in contact_highways],
        crs=CRS,
    )
    for f in (GRAPH_FILE, RAIL_FILE):
        if f.exists():
            f.unlink()
    pyogrio.write_dataframe(edges, GRAPH_FILE, layer="edges")
    pyogrio.write_dataframe(nodes, GRAPH_FILE, layer="nodes")
    pyogrio.write_dataframe(rails, RAIL_FILE, layer="rail_segments")
    pyogrio.write_dataframe(contacts, RAIL_FILE, layer="walk_rail_contacts")
    cats = write_attractors(node_attr, area_attr)

    stats.update({
        "edges": len(edges), "nodes": len(nodes), "rail_segments": len(rails),
        "walk_km": round(edges["length"].sum() / 1000, 1), "attractors": cats,
        "runtime_s": round(time.time() - t0, 1), "source": PBF.name,
    })
    (OUT / "build_osm_stats.json").write_text(json.dumps(stats, indent=2, default=int))
    print(json.dumps(stats, indent=2, default=int))


if __name__ == "__main__":
    main()
