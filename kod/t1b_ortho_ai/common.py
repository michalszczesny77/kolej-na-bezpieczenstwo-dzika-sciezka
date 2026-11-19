import math
from pathlib import Path

from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT.parent / "dane"
OUT_DIR = DATA_DIR / "t1b"
TILE_DIR = DATA_DIR / "raw" / "ortho_tiles"
LINK_SCRIPT = ROOT / "puwg_geoportal_link.py"
BBOX = (50.95, 16.75, 51.30, 17.35)

WMS = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution"
FETCH_HALF_M = 75
FETCH_PX = 600
TILE_PX = 400

to_2180 = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True).transform
to_4326 = Transformer.from_crs("EPSG:2180", "EPSG:4326", always_xy=True).transform


def in_bbox(lat, lon):
    return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]


def fetch_bbox(lat, lon, half_m=FETCH_HALF_M):
    dlat = half_m / 111320
    dlon = half_m / (111320 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def tile_path(tile_id):
    return TILE_DIR / f"{tile_id}.jpg"
