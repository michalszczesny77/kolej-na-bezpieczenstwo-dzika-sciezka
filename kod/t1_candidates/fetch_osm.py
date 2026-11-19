import json
import sys
import time
from pathlib import Path

import requests

BBOX = (50.95, 16.75, 51.30, 17.35)
RAW_DIR = Path(__file__).resolve().parents[2] / "dane" / "raw"
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
HEADERS = {"User-Agent": "dzika-sciezka-research/1.0"}

RAIL_FILTER = '"^(rail|light_rail|narrow_gauge)$"'

QUERIES = {
    "wro_rails": f"""
[out:json][timeout:600][bbox:{{bbox}}];
way[railway~{RAIL_FILTER}]->.rails;
.rails out body geom;
rel(bw.rails)[route=railway];
out body;
""",
    "wro_platforms": """
[out:json][timeout:300][bbox:{bbox}];
(
  way[railway=platform];
  way[public_transport=platform][train=yes];
  way[public_transport=platform][railway];
);
out tags geom;
""",
    "wro_crossings_hazard": """
[out:json][timeout:600][bbox:{bbox}];
(
  node[railway~"^(crossing|level_crossing)$"];
  way[railway~"^(crossing|level_crossing)$"];
);
out center tags;
nwr[hazard=illegal_crossing];
out center tags;
""",
}


def run_query(query, attempts=8):
    delay = 10
    for attempt in range(attempts):
        endpoint = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            r = requests.post(endpoint, data={"data": query}, headers=HEADERS, timeout=1000)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                data = r.json()
                remark = data.get("remark", "")
                if "runtime error" in remark or "timed out" in remark:
                    print(f"{endpoint}: remark {remark[:200]}", file=sys.stderr)
                else:
                    return data
            else:
                print(f"{endpoint}: HTTP {r.status_code}", file=sys.stderr)
        except requests.RequestException as exc:
            print(f"{endpoint}: {exc}", file=sys.stderr)
        time.sleep(delay)
        delay = min(delay * 2, 120)
    raise RuntimeError("Overpass failed on all attempts")


HIGHWAY_TILE_QUERY = """
[out:json][timeout:300][bbox:{bbox}];
way[highway];
out body geom;
"""
TILE_LAT = 0.07
TILE_LON = 0.10


def tiles():
    lat0, lon0, lat1, lon1 = BBOX
    lat = lat0
    while lat < lat1 - 1e-9:
        lon = lon0
        while lon < lon1 - 1e-9:
            yield (round(lat, 4), round(lon, 4), round(min(lat + TILE_LAT, lat1), 4), round(min(lon + TILE_LON, lon1), 4))
            lon += TILE_LON
        lat += TILE_LAT


def fetch_highway_tiles(force=False):
    tile_dir = RAW_DIR / "wro_highways_tiles"
    tile_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for tile in tiles():
        path = tile_dir / ("hw_" + "_".join(str(v) for v in tile) + ".json")
        if force or not path.exists():
            data = run_query(HIGHWAY_TILE_QUERY.replace("{bbox}", ",".join(str(v) for v in tile)))
            path.write_text(json.dumps(data))
            print(f"saved {path.name} ({len(data['elements'])} elements)")
        paths.append(path)
    return paths


def fetch(name, force=False):
    path = RAW_DIR / f"{name}.json"
    if path.exists() and not force:
        return json.loads(path.read_text())
    bbox = ",".join(str(v) for v in BBOX)
    query = QUERIES[name].replace("{bbox}", bbox)
    data = run_query(query)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    print(f"saved {path} ({len(data['elements'])} elements)")
    return data


if __name__ == "__main__":
    force = "--force" in sys.argv
    for name in QUERIES:
        fetch(name, force=force)
    fetch_highway_tiles(force=force)
