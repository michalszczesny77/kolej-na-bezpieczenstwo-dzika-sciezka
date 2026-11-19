import csv
import math
import random
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

DATA_DIR = Path(__file__).resolve().parents[2] / "dane"
OUT_DIR = DATA_DIR / "t1_ortho_check"
WMS = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution"
HALF_SIDE_M = 150
SIZE_PX = 800


def bbox_around(lat, lon):
    dlat = HALF_SIDE_M / 111320
    dlon = HALF_SIDE_M / (111320 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def fetch_crop(row, attempts=4):
    lat, lon = float(row["lat"]), float(row["lon"])
    path = OUT_DIR / f"{row['id']}_{lat:.5f}_{lon:.5f}.jpg"
    if path.exists():
        return path
    params = {
        "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap", "LAYERS": "Raster", "STYLES": "",
        "SRS": "EPSG:4326", "BBOX": ",".join(f"{v:.7f}" for v in bbox_around(lat, lon)),
        "WIDTH": SIZE_PX, "HEIGHT": SIZE_PX, "FORMAT": "image/jpeg",
    }
    for attempt in range(attempts):
        try:
            r = requests.get(WMS, params=params, headers={"User-Agent": "dzika-sciezka-research/1.0"}, timeout=120)
            if r.ok and r.headers.get("Content-Type", "").startswith("image"):
                path.write_bytes(r.content)
                img = Image.open(path).convert("RGB")
                draw = ImageDraw.Draw(img)
                c, rad = SIZE_PX // 2, 18
                draw.ellipse([c - rad, c - rad, c + rad, c + rad], outline=(255, 0, 0), width=3)
                img.save(path, quality=90)
                return path
            print(f"{row['id']}: HTTP {r.status_code} {r.headers.get('Content-Type')}", file=sys.stderr)
        except requests.RequestException as exc:
            print(f"{row['id']}: {exc}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    return None


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    source = sys.argv[3] if len(sys.argv) > 3 else None
    rows = list(csv.DictReader(open(DATA_DIR / "candidates.csv", encoding="utf-8")))
    if source:
        rows = [r for r in rows if source in r["sources"].split(";")]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for row in random.Random(seed).sample(rows, min(n, len(rows))):
        path = fetch_crop(row)
        print(row["id"], row["sources"], row["highway_types"], row["rail_service"] or row["rail_usage"],
              f"off={row['nearest_official_m']}m {row['nearest_official_type']}", path)
