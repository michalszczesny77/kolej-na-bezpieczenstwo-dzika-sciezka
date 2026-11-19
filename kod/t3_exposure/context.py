import sys
from functools import lru_cache
from pathlib import Path

import networkx as nx
import numpy as np
import pyogrio
import shapely
from shapely.geometry import Point
from shapely.ops import linemerge

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    ATTRACTOR_AREAS_FILE,
    ATTRACTORS_FILE,
    CRS,
    GRAPH_FILE,
    POPULATION_FILE,
    RAIL_FILE,
    to_2180,
    to_4326,
)

MAX_TRACK_DISTANCE_M = 60.0
TANGENT_HALF_SPAN_M = 25.0
MIN_COMPONENT_NODES = 200


@lru_cache(maxsize=1)
def rails():
    segs = pyogrio.read_dataframe(RAIL_FILE, layer="rail_segments")
    at_grade = segs[~segs["grade_separated"].astype(bool)].reset_index(drop=True)
    lines = {}
    for way_id, group in segs.groupby("way_id", sort=False):
        lines[way_id] = linemerge(list(group.geometry.values))
    return {
        "segments": segs,
        "tree": shapely.STRtree(segs.geometry.values),
        "at_grade_geoms": at_grade.geometry.values,
        "at_grade_way_ids": at_grade["way_id"].values,
        "at_grade_tree": shapely.STRtree(at_grade.geometry.values),
        "way_lines": lines,
    }


@lru_cache(maxsize=1)
def graph():
    edges = pyogrio.read_dataframe(GRAPH_FILE, layer="edges")
    edges = edges.sort_values("length").drop_duplicates(["u", "v"]).reset_index(drop=True)
    g = nx.Graph()
    for i, (u, v, length) in enumerate(zip(edges["u"].values, edges["v"].values, edges["length"].values)):
        if g.has_edge(u, v):
            continue
        g.add_edge(int(u), int(v), length=float(length), idx=i)
    nodes = pyogrio.read_dataframe(GRAPH_FILE, layer="nodes")
    legal = set(nodes.loc[nodes["legal_rail_crossing"].astype(bool), "node_id"].astype(int))
    main_nodes = set()
    for comp in nx.connected_components(g):
        if len(comp) >= MIN_COMPONENT_NODES:
            main_nodes |= comp
    in_main = edges["u"].isin(main_nodes).values
    snappable = ~edges["grade_separated"].astype(bool).values & in_main
    return {
        "g": g,
        "edges": edges,
        "geoms": edges.geometry.values,
        "tree": shapely.STRtree(edges.geometry.values),
        "snap_tree": shapely.STRtree(edges.geometry.values[snappable]),
        "snap_index": np.flatnonzero(snappable),
        "legal_nodes": legal,
    }


@lru_cache(maxsize=1)
def population():
    grid = pyogrio.read_dataframe(POPULATION_FILE, layer="grid250")
    grid = grid[grid["pop"] > 0].reset_index(drop=True)
    return {"grid": grid, "tree": shapely.STRtree(grid.geometry.values)}


@lru_cache(maxsize=1)
def attractors():
    pts = pyogrio.read_dataframe(ATTRACTORS_FILE).to_crs(CRS)
    areas = pyogrio.read_dataframe(ATTRACTOR_AREAS_FILE, layer="areas")
    areas = areas.assign(geometry=shapely.make_valid(areas.geometry.values))
    return {
        "points": pts,
        "point_tree": shapely.STRtree(pts.geometry.values),
        "areas": areas,
        "area_tree": shapely.STRtree(areas.geometry.values),
    }


def to_xy(lat, lon):
    return to_2180.transform(lon, lat)


def to_latlon(x, y):
    lon, lat = to_4326.transform(x, y)
    return lat, lon


def crosses_rail(geom):
    return len(rails()["tree"].query(geom, predicate="intersects")) > 0


def distance_to_rail(point):
    r = rails()
    idx = r["at_grade_tree"].nearest(point)
    return point.distance(r["at_grade_geoms"][idx])


def track_frame(lat, lon):
    r = rails()
    p = Point(to_xy(lat, lon))
    idx = r["tree"].nearest(p)
    seg = r["segments"].iloc[idx]
    dist = p.distance(seg.geometry)
    if dist > MAX_TRACK_DISTANCE_M:
        raise ValueError(f"no railway within {MAX_TRACK_DISTANCE_M:.0f} m of ({lat}, {lon}); nearest is {dist:.0f} m")
    line = r["way_lines"][seg["way_id"]]
    if line.geom_type != "LineString":
        line = seg.geometry
    s = line.project(p)
    a = line.interpolate(max(s - TANGENT_HALF_SPAN_M, 0.0))
    b = line.interpolate(min(s + TANGENT_HALF_SPAN_M, line.length))
    t = np.array([b.x - a.x, b.y - a.y])
    t /= np.linalg.norm(t)
    normal = np.array([-t[1], t[0]])
    center = line.interpolate(s)
    azimuth = float(np.degrees(np.arctan2(normal[0], normal[1])) % 360)
    return {
        "center": np.array([center.x, center.y]),
        "tangent": t,
        "normal": normal,
        "side_a_azimuth_deg": round(azimuth, 1),
        "track_distance_m": round(dist, 1),
        "rail_way_id": int(seg["way_id"]),
        "railway": seg["railway"],
    }
