import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BBOX = (50.95, 16.75, 51.30, 17.35)
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
USER_AGENT = "dzika-sciezka-research/1.0"
OUT_DIR = Path(__file__).resolve().parents[2] / "dane" / "raw" / "osm_rail_wro"

QUERY = """
[out:json][timeout:300];
(
  way["railway"~"^(rail|disused|construction)$"]({s},{w},{n},{e});
)->.rails;
.rails out body geom;
rel(bw.rails)["route"~"^(railway|tracks)$"];
out body;
(
  node["railway"="milestone"]({s},{w},{n},{e});
  node["railway"~"^(station|halt|junction|crossover|service_station|spur_junction|site)$"]({s},{w},{n},{e});
  node["public_transport"="station"]["train"="yes"]({s},{w},{n},{e});
);
out body;
"""


def run_query(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    last_error = None
    for endpoint in ENDPOINTS:
        for attempt in range(4):
            try:
                req = urllib.request.Request(endpoint, data=data, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=360) as resp:
                    return json.loads(resp.read())
            except Exception as exc:
                last_error = exc
                wait = 10 * 2**attempt
                print(f"{endpoint} attempt {attempt + 1} failed: {exc}; retry in {wait}s", file=sys.stderr)
                time.sleep(wait)
    raise RuntimeError(f"all Overpass endpoints failed: {last_error}")


def main():
    s, w, n, e = BBOX
    result = run_query(QUERY.format(s=s, w=w, n=n, e=e))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "overpass_rail_wro.json"
    out.write_text(json.dumps(result))
    counts = {}
    for el in result["elements"]:
        counts[el["type"]] = counts.get(el["type"], 0) + 1
    print(out, counts, result.get("osm3s", {}).get("timestamp_osm_base"))


if __name__ == "__main__":
    main()
