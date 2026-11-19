from pathlib import Path

from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
RAW_OSM = ROOT.parent / "dane" / "raw" / "t3_osm"
RAW_GUS = ROOT.parent / "dane" / "raw" / "t3_gus"
OUT = ROOT.parent / "dane" / "exposure"

BBOX = (50.95, 16.75, 51.30, 17.35)
MARGIN_DEG = 0.02

PBF = RAW_OSM / "dolnoslaskie-261113.osm.pbf"
GUS_GRID = RAW_GUS / "grid250" / "NSP2021_TOT_GRID250m.gpkg"

GRAPH_FILE = OUT / "walk_graph.gpkg"
RAIL_FILE = OUT / "rail_barriers.gpkg"
POPULATION_FILE = OUT / "population_grid250.gpkg"
ATTRACTORS_FILE = OUT / "attractors.geojson"
ATTRACTOR_AREAS_FILE = OUT / "attractor_areas.gpkg"

CRS = "EPSG:2180"

to_2180 = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
to_4326 = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)


def bbox_with_margin():
    s, w, n, e = BBOX
    return s - MARGIN_DEG, w - MARGIN_DEG, n + MARGIN_DEG, e + MARGIN_DEG


def in_bbox(lat, lon, box):
    s, w, n, e = box
    return s <= lat <= n and w <= lon <= e
