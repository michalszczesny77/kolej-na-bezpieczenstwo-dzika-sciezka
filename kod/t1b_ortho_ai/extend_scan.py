import json
import math

from common import DATA_DIR, OUT_DIR, in_bbox, to_2180
from fetch_tiles import run


def validation_events():
    feats = json.loads((DATA_DIR / "validation.geojson").read_text())["features"]
    events = []
    for f in feats:
        p = f["properties"]
        if p.get("use_for_validation") is True and p.get("precision") in ("exact", "approx") and f["geometry"]:
            lon, lat = f["geometry"]["coordinates"]
            x, y = to_2180(lon, lat)
            events.append({"id": p["id"], "lat": lat, "lon": lon, "x": x, "y": y, "radius": float(p["uncertainty_m"]),
                           "precision": p["precision"], "in_bbox": in_bbox(lat, lon)})
    return events


if __name__ == "__main__":
    scan = json.loads((OUT_DIR / "scan_index.json").read_text())
    scan_all = json.loads((OUT_DIR / "scan_all_index.json").read_text())
    have = {s["tile_id"] for s in scan}
    events = validation_events()
    added = [s for s in scan_all if s["tile_id"] not in have
             and any(e["in_bbox"] and math.dist((s["x"], s["y"]), (e["x"], e["y"])) <= e["radius"] + 60 for e in events)]
    print(f"events {len(events)} (in bbox {sum(e['in_bbox'] for e in events)}), extra scan tiles {len(added)}")
    scan += added
    (OUT_DIR / "scan_index.json").write_text(json.dumps(scan))
    (OUT_DIR / "validation_events.json").write_text(json.dumps(events))
    run(added)
