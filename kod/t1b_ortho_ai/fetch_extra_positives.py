import json
import time

import requests

from common import DATA_DIR

OVERPASS = "https://overpass-api.de/api/interpreter"
CITIES = {
    "warszawa": (52.10, 20.85, 52.37, 21.27),
    "krakow": (49.97, 19.79, 50.13, 20.10),
    "lodz": (51.68, 19.35, 51.86, 19.62),
    "poznan": (52.33, 16.78, 52.50, 17.08),
    "trojmiasto": (54.30, 18.42, 54.58, 18.80),
    "katowice": (50.15, 18.85, 50.35, 19.20),
    "szczecin": (53.35, 14.45, 53.50, 14.67),
    "lublin": (51.18, 22.45, 51.30, 22.65),
}


def query(bbox):
    b = ",".join(str(v) for v in bbox)
    return (f"[out:json][timeout:180];"
            f"way[highway~\"^(path|footway|track)$\"][informal=yes]({b})->.p;node(w.p)->.pn;"
            f"way[railway=rail][!bridge][!tunnel]({b})->.r;node(w.r)->.rn;"
            f"node.pn.rn[!railway];out;")


def main():
    out_path = DATA_DIR / "raw" / "ortho_meta" / "osm_informal_rail_nodes_PL_cities.json"
    result = json.loads(out_path.read_text()) if out_path.exists() else {}
    for name, bbox in CITIES.items():
        if name in result:
            continue
        for attempt in range(4):
            r = requests.post(OVERPASS, data={"data": query(bbox)}, headers={"User-Agent": "dzika-sciezka-research/1.0"}, timeout=240)
            if r.ok:
                data = r.json()
                result[name] = {"osm_base": data.get("osm3s", {}).get("timestamp_osm_base"), "elements": data["elements"]}
                print(name, len(data["elements"]))
                break
            print(name, "HTTP", r.status_code)
            time.sleep(15 * (attempt + 1))
        out_path.write_text(json.dumps(result))
        time.sleep(5)


if __name__ == "__main__":
    main()
