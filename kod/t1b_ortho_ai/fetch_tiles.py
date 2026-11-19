import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image

from common import FETCH_PX, OUT_DIR, TILE_DIR, WMS, fetch_bbox, tile_path

POP_MIN = 50
WORKERS = 4
HEADERS = {"User-Agent": "dzika-sciezka-research/1.0"}
session = requests.Session()


def get_with_retry(params, expect_image, attempts=5):
    for attempt in range(attempts):
        try:
            r = session.get(WMS, params=params, headers=HEADERS, timeout=90)
            ctype = r.headers.get("Content-Type", "")
            if r.ok and (ctype.startswith("image") if expect_image else "html" in ctype or "text" in ctype):
                return r.content
            print(f"HTTP {r.status_code} {ctype}", file=sys.stderr)
            if 400 <= r.status_code < 500:
                return None
        except requests.RequestException as exc:
            print(f"error: {exc}", file=sys.stderr)
        time.sleep(2 ** attempt * 2)
    return None


def fetch_tile(item):
    path = tile_path(item["tile_id"])
    if path.exists():
        return item["tile_id"], True
    params = {"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap", "LAYERS": "Raster", "STYLES": "",
              "SRS": "EPSG:4326", "BBOX": ",".join(f"{v:.7f}" for v in fetch_bbox(item["lat"], item["lon"])),
              "WIDTH": FETCH_PX, "HEIGHT": FETCH_PX, "FORMAT": "image/jpeg"}
    content = get_with_retry(params, expect_image=True)
    if content is None:
        return item["tile_id"], False
    img = Image.open(io.BytesIO(content))
    img.verify()
    if img.size != (FETCH_PX, FETCH_PX):
        return item["tile_id"], False
    tmp = path.with_suffix(".part")
    tmp.write_bytes(content)
    tmp.rename(path)
    return item["tile_id"], True


def feature_info(lat, lon):
    lon0, lat0, lon1, lat1 = fetch_bbox(lat, lon, 50)
    params = {"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetFeatureInfo", "LAYERS": "Raster",
              "QUERY_LAYERS": "Raster", "STYLES": "", "SRS": "EPSG:4326", "BBOX": f"{lon0:.7f},{lat0:.7f},{lon1:.7f},{lat1:.7f}",
              "WIDTH": 400, "HEIGHT": 400, "X": 200, "Y": 200, "INFO_FORMAT": "text/html", "FEATURE_COUNT": 10}
    content = get_with_retry(params, expect_image=False)
    if content is None:
        return None
    text = content.decode("utf-8", errors="replace")
    rows = [[re.sub(r"<.*?>", "", c).strip() for c in re.findall(r"<t[hd]>(.*?)</t[hd]>", r, re.S)]
            for r in re.findall(r"<tr>(.*?)</tr>", text, re.S)]
    if len(rows) < 2:
        return None
    head = rows[0]
    recs = [dict(zip(head, r)) for r in rows[1:]]
    recs = [r for r in recs if r.get("zorder", "Null") != "Null" and r.get("aktualnosc", "Null") != "Null"]
    if not recs:
        return None
    top = max(recs, key=lambda r: int(r["zorder"]))
    return {"aktualnosc": top["aktualnosc"], "seria": top["seria"], "rozdz_m": top["rozdz"].replace(",", "."),
            "projekt": top["projekt"], "godlo": top["name"]}


def run(items):
    TILE_DIR.mkdir(parents=True, exist_ok=True)
    t0, failed = time.time(), []
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = [pool.submit(fetch_tile, it) for it in items]
        for n, fut in enumerate(as_completed(futures), 1):
            tid, ok = fut.result()
            if not ok:
                failed.append(tid)
            if n % 200 == 0:
                print(f"{n}/{len(items)} {time.time() - t0:.0f}s failed={len(failed)}", flush=True)
    print(f"done {len(items)} in {time.time() - t0:.0f}s, failed {len(failed)}: {failed[:20]}")


if __name__ == "__main__":
    positives = json.loads((OUT_DIR / "positives_index.json").read_text())
    scan_all = json.loads((OUT_DIR / "scan_all_index.json").read_text())
    scan = [s for s in scan_all if s["pop500"] >= POP_MIN]
    (OUT_DIR / "scan_index.json").write_text(json.dumps(scan))
    print(f"positives {len(positives)}, scan {len(scan)} (pop500 >= {POP_MIN})")
    run(positives + scan)
