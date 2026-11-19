import json

from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from build_index import dedupe, fetch_pl_rails, nearest_bearing
from common import DATA_DIR, OUT_DIR, in_bbox, to_2180
from fetch_tiles import run

if __name__ == "__main__":
    raw = json.loads((DATA_DIR / "raw" / "ortho_meta" / "osm_informal_rail_nodes_PL_cities.json").read_text())
    pts = [(city, el) for city, block in raw.items() for el in block["elements"] if el["type"] == "node"]
    rails = fetch_pl_rails([(el["lat"], el["lon"]) for _, el in pts], "extra_positive_rails.json")
    lines = [LineString([to_2180(g["lon"], g["lat"]) for g in el["geometry"]]) for el in rails["elements"]
             if el["type"] == "way" and len(el.get("geometry", [])) >= 2]
    tree = STRtree(lines)
    items = []
    for city, el in pts:
        x, y = to_2180(el["lon"], el["lat"])
        brg, d = nearest_bearing(Point(x, y), lines, tree)
        items.append({"tile_id": f"xpos_node{el['id']}", "src": f"osm_informal_{city}", "ref": f"node/{el['id']}",
                      "lat": el["lat"], "lon": el["lon"], "x": x, "y": y, "bearing": brg, "rail_dist": d,
                      "in_bbox": in_bbox(el["lat"], el["lon"])})
    items = dedupe(items, 25)
    (OUT_DIR / "extra_positives_index.json").write_text(json.dumps(items, indent=0))
    print(f"nodes {len(pts)}, after 25 m dedupe {len(items)}")
    run(items)
