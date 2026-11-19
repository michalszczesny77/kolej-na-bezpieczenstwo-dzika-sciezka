import csv
import datetime
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import openpyxl
from pyproj import Transformer
from shapely.geometry import LineString, Point, box, mapping
from shapely import transform
from shapely.ops import substring
from shapely.strtree import STRtree

BBOX = (50.95, 16.75, 51.30, 17.35)
DATA = Path(__file__).resolve().parents[2] / "dane"
RAW = DATA / "raw"
ANNEX_DIR = RAW / "plk_regulamin_sieci_2025_2026"
GTFS_DIR = RAW / "gtfs_polish_trains" / "extracted"
OSM_FILE = RAW / "osm_rail_wro" / "overpass_rail_wro.json"
OUT_GEOJSON = DATA / "rail_hazard.geojson"
OUT_CSV = DATA / "rail_hazard_lines.csv"
OUT_DIAG = DATA / "t2_diagnostics.json"

ANNEX_FILES = {
    "lines": "ZAL_1_Reg_25-26_v41_publ.xlsx",
    "speeds": "N_ZAL_2.1_20252026_20261008065031.xlsx",
    "points": "N_ZAL_2.6_20252026_20261008065041.xlsx",
    "catenary": "N_ZAL_2.12_20252026_20261008065033.xlsx",
}
WEEKDAY = "20261118"
SATURDAY = "20261121"
CHUNK_M = 100.0
MILESTONE_SNAP_M = 20.0
MAX_ANCHOR_GAP_M = 1500.0
SHAPE_STEP_M = 25.0
SHAPE_SNAP_M = 8.0
SHAPE_GAP_KM = 1.5
SHAPE_MIN_SAMPLES = 8
SHAPE_PAD_KM = 0.3
CORRIDOR_RADIUS_M = 30.0
VALIDATION_RADIUS_M = 150.0
SRC_SPEED = "PLK Regulamin sieci 2025/2026 zal. 2.1 (stan 25.10.2026)"
SRC_CATENARY = "PLK Regulamin sieci 2025/2026 zal. 2.12 (stan 25.10.2026)"
SRC_TRAINS = "GTFS PolishTrains (dane PLK API), {day}, dopasowanie shapes do OSM"

to_2180 = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True).transform
to_4326 = Transformer.from_crs("EPSG:2180", "EPSG:4326", always_xy=True).transform


def reproject(geom, func):
    return transform(geom, lambda xy: np.column_stack(func(xy[:, 0], xy[:, 1])))


def line_number(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def annex_rows(key, sheet_suffix="dane"):
    wb = openpyxl.load_workbook(ANNEX_DIR / ANNEX_FILES[key], read_only=True, data_only=True)
    sheet = next(ws for ws in wb.worksheets if ws.title.endswith(sheet_suffix))
    for row in sheet.iter_rows(min_row=8, values_only=True):
        if line_number(row[0]) is not None:
            yield row


def load_annexes():
    line_names = {}
    for r in annex_rows("lines"):
        line_names[line_number(r[0])] = str(r[1]).strip()
    speeds = defaultdict(list)
    for r in annex_rows("speeds"):
        speeds[line_number(r[0])].append(
            {"track": r[2], "km_from": float(r[3]), "km_to": float(r[4]),
             "v_emu": int(r[5] or 0), "v_wagon": int(r[6] or 0), "v_freight": int(r[7] or 0)}
        )
    points = defaultdict(list)
    for r in annex_rows("points"):
        points[line_number(r[0])].append(
            {"name": str(r[3]).strip(), "kind": r[2], "km": float(r[4]), "platform": r[5] == "TAK"}
        )
    catenary = defaultdict(list)
    for r in annex_rows("catenary"):
        catenary[line_number(r[0])].append({"track": r[2], "km_from": float(r[3]), "km_to": float(r[4])})
    return line_names, speeds, points, catenary


def load_osm():
    elements = json.loads(OSM_FILE.read_text())["elements"]
    ways = [e for e in elements if e["type"] == "way"]
    nodes = [e for e in elements if e["type"] == "node"]
    running = [
        w for w in ways
        if w["tags"].get("railway") == "rail" and "service" not in w["tags"] and len(w.get("geometry", [])) >= 2
    ]
    return running, nodes


def way_lines(way):
    refs = [line_number(r) for r in way["tags"].get("ref", "").split(";")]
    return [r for r in refs if r is not None]


def chunk_way(way):
    s, w, n, e = BBOX
    clipped = LineString([(p["lon"], p["lat"]) for p in way["geometry"]]).intersection(box(w, s, e, n))
    parts = [g for g in getattr(clipped, "geoms", [clipped]) if isinstance(g, LineString) and not g.is_empty]
    chunks = []
    for part in parts:
        geom = reproject(part, to_2180)
        count = max(1, math.ceil(geom.length / CHUNK_M))
        step = geom.length / count
        chunks += [substring(geom, i * step, (i + 1) * step) for i in range(count)]
    return chunks


def load_gtfs_stations():
    coords = {}
    with open(GTFS_DIR / "stops.txt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["location_type"] == "1":
                coords.setdefault(r["stop_name"], (float(r["stop_lon"]), float(r["stop_lat"])))
    return coords


def build_anchors(points, nodes, gtfs_coords, chunks):
    osm_named = defaultdict(list)
    for n in nodes:
        name = n["tags"].get("name")
        if name and n["tags"].get("railway") != "milestone":
            osm_named[name].append((n["lon"], n["lat"]))
    anchors = defaultdict(list)
    for line, pts in points.items():
        for p in pts:
            lonlat = gtfs_coords.get(p["name"]) if p["platform"] else None
            source = "gtfs_stop"
            if lonlat is None and len(osm_named.get(p["name"], [])) == 1:
                lonlat, source = osm_named[p["name"]][0], "osm_node"
            if lonlat is None:
                continue
            x, y = to_2180(*lonlat)
            anchors[line].append({"km": p["km"], "xy": (x, y), "source": source, "name": p["name"]})

    tree = STRtree([c["geom"] for c in chunks])
    for n in nodes:
        if n["tags"].get("railway") != "milestone":
            continue
        raw = n["tags"].get("railway:position:exact") or n["tags"].get("railway:position")
        try:
            km = float(raw.replace(",", "."))
        except (AttributeError, ValueError):
            continue
        pt = Point(to_2180(n["lon"], n["lat"]))
        near = tree.query(pt.buffer(MILESTONE_SNAP_M))
        lines = {tuple(chunks[i]["lines"]) for i in near if chunks[i]["geom"].distance(pt) <= MILESTONE_SNAP_M}
        if len(lines) == 1 and len(next(iter(lines))) == 1:
            line = next(iter(lines))[0]
            anchors[line].append({"km": km, "xy": (pt.x, pt.y), "source": "osm_milestone", "name": f"node/{n['id']}"})
    return {line: clean_anchors(a) for line, a in anchors.items()}


def clean_anchors(anchors):
    anchors = sorted(anchors, key=lambda a: a["km"])
    changed = True
    while changed and len(anchors) >= 3:
        changed = False
        for i, a in enumerate(anchors):
            ratios = []
            for j in (i - 1, i + 1):
                if 0 <= j < len(anchors):
                    b = anchors[j]
                    dist = math.dist(a["xy"], b["xy"])
                    allowed = abs(a["km"] - b["km"]) * 1000 * 1.15 + 600
                    ratios.append(dist > allowed)
            if ratios and all(ratios):
                anchors.pop(i)
                changed = True
                break
    return anchors


def km_at(anchors, xy):
    if len(anchors) < 2:
        return None, None
    p = Point(xy)
    best = None
    for a, b in zip(anchors, anchors[1:]):
        if a["km"] == b["km"]:
            continue
        seg = LineString([a["xy"], b["xy"]])
        d = seg.distance(p)
        if best is None or d < best[0]:
            best = (d, a, b, seg)
    if best is None:
        return None, None
    d, a, b, seg = best
    ax, ay = a["xy"]
    bx, by = b["xy"]
    length2 = (bx - ax) ** 2 + (by - ay) ** 2
    t = ((xy[0] - ax) * (bx - ax) + (xy[1] - ay) * (by - ay)) / length2
    if (t < 0 and a is not anchors[0]) or (t > 1 and b is not anchors[-1]):
        t = min(max(t, 0.0), 1.0)
    return a["km"] + t * (b["km"] - a["km"]), d


def covering(rows, km, track=None, tolerance=0.05):
    hits = [r for r in rows if (track is None or r["track"] == track) and r["km_from"] - tolerance <= km <= r["km_to"] + tolerance]
    return hits


def osm_track(way):
    ref = way["tags"].get("railway:track_ref", "")
    return {"1": "N", "2": "P"}.get(ref)


def active_services(day):
    services = set()
    with open(GTFS_DIR / "calendar_dates.txt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["date"] == day and r["exception_type"] == "1":
                services.add(r["service_id"])
    return services


def regional_trips(stop_names, stop_coords):
    rail_routes = set()
    with open(GTFS_DIR / "routes.txt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["route_type"] == "2":
                rail_routes.add(r["route_id"])
    trips = {}
    with open(GTFS_DIR / "trips.txt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["route_id"] in rail_routes:
                trips[r["trip_id"]] = {"service": r["service_id"], "route": r["route_id"], "shape": r["shape_id"], "stops": []}
    with open(GTFS_DIR / "stop_times.txt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            trip = trips.get(r["trip_id"])
            if trip is not None:
                trip["stops"].append((int(r["stop_sequence"]), stop_names[r["stop_id"]], float(r["shape_dist_traveled"] or 0)))
    s, w, n, e = BBOX
    margin = 0.15
    result = {}
    for tid, trip in trips.items():
        trip["stops"].sort()
        inside = any(
            s - margin <= stop_coords[name][1] <= n + margin and w - margin <= stop_coords[name][0] <= e + margin
            for _, name, _ in trip["stops"] if name in stop_coords
        )
        if inside:
            result[tid] = trip
    return result


def station_calls(trips, services, stop_coords):
    s, w, n, e = BBOX
    calls = Counter()
    for trip in trips.values():
        if trip["service"] not in services:
            continue
        for name in {name for _, name, _ in trip["stops"]}:
            lon, lat = stop_coords.get(name, (0, 0))
            if s <= lat <= n and w <= lon <= e:
                calls[name] += 1
    return calls


def validate_counts(chunks, calls, stop_coords):
    tree = STRtree([c["geom"] for c in chunks])
    rows = []
    for name, count in calls.items():
        pt = Point(to_2180(*stop_coords[name]))
        near = [chunks[i] for i in tree.query(pt.buffer(VALIDATION_RADIUS_M))]
        counted = [c["rec"]["trains"] for c in near if c["rec"]["trains"] is not None]
        rows.append({"stop": name, "calls": count, "max_trains_nearby": max(counted) if counted else None})
    rows.sort(key=lambda r: r["stop"])
    checked = [r for r in rows if r["max_trains_nearby"] is not None]
    ok = [r for r in checked if r["max_trains_nearby"] >= r["calls"]]
    return {"stops": len(rows), "checked": len(checked), "trains_ge_calls": len(ok),
            "violations": [r for r in checked if r["max_trains_nearby"] < r["calls"]], "rows": rows}


def count_at(intervals, km):
    return sum(1 for lo, hi in intervals if lo - 0.01 <= km <= hi + 0.01)


def load_shapes(shape_ids):
    s, w, n, e = BBOX
    margin = 0.02
    shapes = defaultdict(list)
    with open(GTFS_DIR / "shapes.txt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["shape_id"] in shape_ids:
                shapes[r["shape_id"]].append((int(r["shape_pt_sequence"]), float(r["shape_pt_lon"]), float(r["shape_pt_lat"])))
    result = {}
    for sid, pts in shapes.items():
        pts.sort()
        runs, current = [], []
        for _, lon, lat in pts:
            if s - margin <= lat <= n + margin and w - margin <= lon <= e + margin:
                current.append(to_2180(lon, lat))
            elif current:
                runs.append(current)
                current = []
        if current:
            runs.append(current)
        result[sid] = [r for r in runs if len(r) >= 2]
    return result


def shape_coverage(shapes, chunks):
    tree = STRtree([c["geom"] for c in chunks])
    coverage = {}
    for sid, runs in shapes.items():
        kms = defaultdict(list)
        touched = Counter()
        for run in runs:
            line = LineString(run)
            n = max(2, math.ceil(line.length / SHAPE_STEP_M) + 1)
            samples = [line.interpolate(i / (n - 1), normalized=True) for i in range(n)]
            nearest = tree.nearest(samples)
            for pt, idx in zip(samples, nearest):
                c = chunks[idx]
                if c["geom"].distance(pt) > SHAPE_SNAP_M:
                    continue
                for ln in c["lines"]:
                    touched[ln] += 1
                    if ln in c["kms"]:
                        kms[ln].append(c["kms"][ln][0])
        intervals = {}
        for ln, values in kms.items():
            values.sort()
            merged = [[values[0], values[0]]]
            for v in values[1:]:
                if v - merged[-1][1] <= SHAPE_GAP_KM:
                    merged[-1][1] = v
                else:
                    merged.append([v, v])
            intervals[ln] = [(lo - SHAPE_PAD_KM, hi + SHAPE_PAD_KM) for lo, hi in merged if hi - lo >= 0.2 or len(values) >= 3]
        coverage[sid] = {"intervals": intervals, "lines": {ln for ln, k in touched.items() if k >= SHAPE_MIN_SAMPLES}}
    return coverage


def corridor_counts(chunks, shapes, trips, services):
    per_shape = Counter(t["shape"] for t in trips.values() if t["service"] in services)
    geoms, owners = [], []
    for sid, runs in shapes.items():
        for run in runs:
            geoms.append(LineString(run))
            owners.append(sid)
    tree = STRtree(geoms)
    mids = [c["geom"].interpolate(0.5, normalized=True) for c in chunks]
    hits = defaultdict(set)
    for chunk_idx, geom_idx in zip(*tree.query(mids, predicate="dwithin", distance=CORRIDOR_RADIUS_M)):
        hits[chunk_idx].add(owners[geom_idx])
    return [sum(per_shape[sid] for sid in hits.get(i, ())) for i in range(len(chunks))]


def shape_counts(trips, coverage, services):
    per_line, per_line_any = defaultdict(list), Counter()
    for trip in trips.values():
        if trip["service"] not in services or trip["shape"] not in coverage:
            continue
        cov = coverage[trip["shape"]]
        for ln, ivs in cov["intervals"].items():
            per_line[ln].extend(ivs)
        for ln in cov["lines"]:
            per_line_any[ln] += 1
    return per_line, per_line_any


def main():
    line_names, speeds, points, catenary = load_annexes()
    running, nodes = load_osm()
    chunks = []
    for way in running:
        for geom in chunk_way(way):
            chunks.append({"way": way, "geom": geom, "lines": way_lines(way)})

    gtfs_coords = load_gtfs_stations()
    anchors = build_anchors(points, nodes, gtfs_coords, chunks)
    for c in chunks:
        mid = c["geom"].interpolate(0.5, normalized=True)
        c["kms"] = {}
        for line in c["lines"]:
            km, gap = km_at(anchors.get(line, []), (mid.x, mid.y))
            if km is not None and gap <= MAX_ANCHOR_GAP_M:
                c["kms"][line] = (km, gap)

    stop_names, stop_coords = {}, {}
    with open(GTFS_DIR / "stops.txt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            stop_names[r["stop_id"]] = r["stop_name"]
            stop_coords.setdefault(r["stop_name"], (float(r["stop_lon"]), float(r["stop_lat"])))
    trips = regional_trips(stop_names, stop_coords)
    shapes = load_shapes({t["shape"] for t in trips.values()})
    coverage = shape_coverage(shapes, chunks)
    weekday, saturday = active_services(WEEKDAY), active_services(SATURDAY)
    wd_shape, wd_any = shape_counts(trips, coverage, weekday)
    sat_shape, sat_any = shape_counts(trips, coverage, saturday)
    wd_corridor = corridor_counts(chunks, shapes, trips, weekday)
    sat_corridor = corridor_counts(chunks, shapes, trips, saturday)


    for i, c in enumerate(chunks):
        way, tags = c["way"], c["way"]["tags"]
        track = osm_track(way)
        rec = {"km": None, "km_gap_m": None, "vmax": None, "vmax_wagon": None, "vmax_freight": None,
               "vmax_source": None, "tracks": None, "tracks_source": None, "electrified": None,
               "electrified_source": None, "trains": None, "trains_sat": None, "trains_source": None}
        lines, kms = c["lines"], c["kms"]
        if lines and len(kms) == len(lines):
            rec["km"] = round(kms[lines[0]][0], 3)
            rec["km_gap_m"] = round(max(g for _, g in kms.values()))
            v, vw, vf, ntracks, electrified, trains, trains_sat = [], [], [], [], [], [], []
            for line, (km, _) in kms.items():
                hits = covering(speeds[line], km, track) or covering(speeds[line], km)
                if not hits:
                    hits = covering(speeds[line], km, tolerance=0.3)
                v += [max(h["v_emu"], h["v_wagon"]) for h in hits]
                vw += [h["v_wagon"] for h in hits]
                vf += [h["v_freight"] for h in hits]
                track_set = {h["track"] for h in covering(speeds[line], km)}
                if track_set:
                    ntracks.append(len(track_set))
                electrified.append(bool(covering(catenary[line], km, tolerance=0.1)))
                trains.append(count_at(wd_shape.get(line, []), km))
                trains_sat.append(count_at(sat_shape.get(line, []), km))
            if v:
                rec.update(vmax=max(v), vmax_wagon=max(vw), vmax_freight=max(vf), vmax_source=SRC_SPEED)
            if ntracks:
                rec.update(tracks=max(ntracks), tracks_source=SRC_SPEED)
            rec.update(electrified=any(electrified), electrified_source=SRC_CATENARY)
            rec.update(trains=max(trains), trains_sat=max(trains_sat), trains_source=SRC_TRAINS.format(day=WEEKDAY))
        elif lines:
            line_speeds = [max(r["v_emu"], r["v_wagon"]) for line in lines for r in speeds.get(line, [])]
            if line_speeds and len(set(line_speeds)) == 1:
                rec.update(vmax=line_speeds[0], vmax_source=SRC_SPEED + ", jednolita na calej linii")
            elif line_speeds:
                rec.update(vmax=max(line_speeds), vmax_source=SRC_SPEED + ", maksimum linii (km nieznany)")
            rec.update(trains=max(wd_any.get(line, 0) for line in lines),
                       trains_sat=max(sat_any.get(line, 0) for line in lines),
                       trains_source=SRC_TRAINS.format(day=WEEKDAY) + ", pociagi dotykajace linii (km nieznany)")
        if rec["vmax"] is None and tags.get("maxspeed", "").isdigit():
            rec.update(vmax=int(tags["maxspeed"]), vmax_source="OSM maxspeed")
        if rec["electrified"] is None and "electrified" in tags:
            rec.update(electrified=tags["electrified"] not in ("no", ""), electrified_source="OSM electrified")
        if rec["tracks"] is None and tags.get("tracks", "").isdigit():
            rec.update(tracks=int(tags["tracks"]), tracks_source="OSM tracks")
        rec["corridor"], rec["corridor_sat"] = wd_corridor[i], sat_corridor[i]
        osm_speed = tags.get("maxspeed")
        rec["osm_maxspeed"] = int(osm_speed) if osm_speed and osm_speed.isdigit() else None
        c["rec"] = rec

    diag = validate_counts(chunks, station_calls(trips, weekday, stop_coords), stop_coords)
    features = merge_chunks(chunks, line_names)
    write_outputs(features, chunks, line_names, anchors, diag, trips)


ATTR_KEYS = ("vmax", "vmax_wagon", "vmax_freight", "vmax_source", "tracks", "tracks_source", "electrified",
             "electrified_source", "trains", "trains_sat", "trains_source", "corridor", "corridor_sat")


def merge_chunks(chunks, line_names):
    features = []
    by_way = defaultdict(list)
    for c in chunks:
        by_way[c["way"]["id"]].append(c)
    for way_id, parts in by_way.items():
        group = [parts[0]]
        for c in parts[1:]:
            contiguous = c["geom"].coords[0] == group[-1]["geom"].coords[-1]
            if contiguous and all(c["rec"][k] == group[-1]["rec"][k] for k in ATTR_KEYS):
                group.append(c)
            else:
                features.append(make_feature(group, line_names))
                group = [c]
        features.append(make_feature(group, line_names))
    return features


def make_feature(group, line_names):
    way = group[0]["way"]
    coords = list(group[0]["geom"].coords)
    for c in group[1:]:
        coords += list(c["geom"].coords)[1:]
    geom = reproject(LineString(coords), to_4326)
    rec = group[0]["rec"]
    kms = [c["rec"]["km"] for c in group if c["rec"]["km"] is not None]
    lines = group[0]["lines"]
    props = {
        "line_no": ";".join(str(x) for x in lines) or None,
        "line_name": ";".join(line_names.get(x, "") for x in lines) or None,
        "km_from": round(min(kms), 3) if kms else None,
        "km_to": round(max(kms), 3) if kms else None,
        "km_gap_m": max((c["rec"]["km_gap_m"] for c in group if c["rec"]["km_gap_m"] is not None), default=None),
        "track": {"N": "N (tor 1)", "P": "P (tor 2)"}.get(osm_track(way)),
        "vmax_kmh": rec["vmax"],
        "vmax_wagon_kmh": rec["vmax_wagon"],
        "vmax_freight_kmh": rec["vmax_freight"],
        "vmax_source": rec["vmax_source"],
        "osm_maxspeed": rec["osm_maxspeed"],
        "trains_per_day": rec["trains"],
        "trains_per_day_sat": rec["trains_sat"],
        "trains_source": rec["trains_source"],
        "trains_per_day_corridor": rec["corridor"],
        "trains_per_day_corridor_sat": rec["corridor_sat"],
        "freight_trains_per_day": None,
        "freight_source": None,
        "tracks": rec["tracks"],
        "tracks_source": rec["tracks_source"],
        "electrified": rec["electrified"],
        "electrified_source": rec["electrified_source"],
        "usage": way["tags"].get("usage"),
        "osm_way_ids": [way["id"]],
        "length_m": round(sum(c["geom"].length for c in group), 1),
    }
    return {"type": "Feature", "geometry": mapping(geom), "properties": props}


def write_outputs(features, chunks, line_names, anchors, diag, trips):
    fc = {"type": "FeatureCollection", "name": "rail_hazard", "features": features}
    OUT_GEOJSON.write_text(json.dumps(fc, ensure_ascii=False))

    total = sum(c["geom"].length for c in chunks)
    with_speed = sum(c["geom"].length for c in chunks if c["rec"]["vmax"] is not None)
    with_plk_speed = sum(c["geom"].length for c in chunks if (c["rec"]["vmax_source"] or "").startswith("PLK"))
    with_km_speed = sum(c["geom"].length for c in chunks if c["rec"]["vmax_source"] == SRC_SPEED)
    with_trains = sum(c["geom"].length for c in chunks if c["rec"]["trains"] is not None)
    with_km_trains = sum(c["geom"].length for c in chunks if c["rec"]["trains_source"] == SRC_TRAINS.format(day=WEEKDAY))
    agree = [(abs(c["rec"]["vmax"] - c["rec"]["osm_maxspeed"]), c["geom"].length) for c in chunks
             if c["rec"]["vmax_source"] == SRC_SPEED and c["rec"]["osm_maxspeed"]]
    agree_len = sum(w for _, w in agree)

    rows = []
    by_line = defaultdict(list)
    for c in chunks:
        by_line[";".join(str(x) for x in c["lines"]) or "brak"].append(c)
    for key, cs in sorted(by_line.items(), key=lambda kv: (len(kv[0]), kv[0])):
        length = sum(c["geom"].length for c in cs)
        v = [c["rec"]["vmax"] for c in cs if c["rec"]["vmax"] is not None]
        t = [c["rec"]["trains"] for c in cs if c["rec"]["trains"] is not None]
        ts = [c["rec"]["trains_sat"] for c in cs if c["rec"]["trains_sat"] is not None]
        tr = [c["rec"]["tracks"] for c in cs if c["rec"]["tracks"] is not None]
        el = [c for c in cs if c["rec"]["electrified"]]
        kms = [c["rec"]["km"] for c in cs if c["rec"]["km"] is not None]
        first = cs[0]["lines"]
        rows.append({
            "line_no": key,
            "line_name": ";".join(line_names.get(x, "") for x in first),
            "track_length_km_in_bbox": round(length / 1000, 2),
            "km_min": round(min(kms), 2) if kms else None,
            "km_max": round(max(kms), 2) if kms else None,
            "vmax_min_kmh": min(v) if v else None,
            "vmax_max_kmh": max(v) if v else None,
            "vmax_lenweighted_kmh": round(weighted(cs, "vmax")) if v else None,
            "trains_per_day_min": min(t) if t else None,
            "trains_per_day_max": max(t) if t else None,
            "trains_per_day_sat_max": max(ts) if ts else None,
            "trains_per_day_corridor_max": max(c["rec"]["corridor"] for c in cs),
            "tracks": "/".join(str(x) for x in sorted(set(tr))) if tr else None,
            "electrified_share": round(sum(c["geom"].length for c in el) / length, 2),
            "share_km_known": round(sum(c["geom"].length for c in cs if c["rec"]["km"] is not None) / length, 2),
            "anchors": len(anchors.get(first[0], [])) if len(first) == 1 else None,
            "vmax_source": Counter(c["rec"]["vmax_source"] for c in cs).most_common(1)[0][0],
            "trains_source": Counter(c["rec"]["trains_source"] for c in cs).most_common(1)[0][0],
        })
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "features": len(features),
        "running_track_km": round(total / 1000, 2),
        "share_vmax_any": round(with_speed / total, 3),
        "share_vmax_plk": round(with_plk_speed / total, 3),
        "share_vmax_plk_by_km": round(with_km_speed / total, 3),
        "share_trains_any": round(with_trains / total, 3),
        "share_trains_by_km": round(with_km_trains / total, 3),
        "osm_maxspeed_compared_km": round(agree_len / 1000, 1),
        "osm_maxspeed_equal_share": round(sum(w for d, w in agree if d == 0) / agree_len, 3) if agree else None,
        "osm_maxspeed_within_10_share": round(sum(w for d, w in agree if d <= 10) / agree_len, 3) if agree else None,
        "trips_considered": len(trips),
        "validation_station_calls": diag,
        "anchors_per_line": {str(k): Counter(a["source"] for a in v) for k, v in anchors.items() if any(k == l for c in chunks for l in c["lines"])},
    }
    OUT_DIAG.write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=list))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("validation_station_calls", "anchors_per_line")}, indent=1))
    print("validation", {k: diag[k] for k in ("stops", "checked", "trains_ge_calls")}, diag["violations"])


def weighted(cs, key):
    pairs = [(c["rec"][key], c["geom"].length) for c in cs if c["rec"][key] is not None]
    return sum(v * w for v, w in pairs) / sum(w for _, w in pairs)


if __name__ == "__main__":
    sys.exit(main())
