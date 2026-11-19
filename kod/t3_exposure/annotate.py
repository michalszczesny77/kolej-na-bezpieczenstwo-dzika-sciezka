import argparse
import sys
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detour import detour
from exposure import exposure

DETOUR_FIELDS = ("straight_m", "walk_m", "detour_m", "ratio", "reachable", "tracks_crossed",
                 "offset_a_m", "offset_b_m", "access_a_m", "access_b_m")


def flatten(det, exp):
    row = {f"detour_{k}": det.get(k) for k in DETOUR_FIELDS}
    row["side_a_azimuth_deg"] = det["side_a_azimuth_deg"]
    row["detour_reason"] = det.get("reason")
    used = det.get("crossing_used") or {}
    row["legal_crossing_lat"] = used.get("lat")
    row["legal_crossing_lon"] = used.get("lon")
    row["legal_crossing_type"] = used.get("type")
    for k in ("pop_500m", "pop_1000m", "pop_500m_a", "pop_500m_b"):
        row[k] = exp[k]
    for cat, sides in exp["attractors_500m"].items():
        for side, v in sides.items():
            row[f"n_{cat}_{side}"] = v
    for cat, sides in exp["area_m2_500m"].items():
        for side, v in sides.items():
            row[f"area_{cat}_{side}"] = v
    return row


def annotate(src, dst):
    points = gpd.read_file(src).to_crs("EPSG:4326")
    rows = []
    for geom in points.geometry:
        lat, lon = geom.y, geom.x
        try:
            rows.append(flatten(detour(lat, lon), exposure(lat, lon)))
        except ValueError as e:
            rows.append({"detour_reason": str(e)})
    extra = pd.DataFrame(rows, index=points.index)
    extra.columns = [f"{c}_t3" if c in points.columns else c for c in extra.columns]
    out = gpd.GeoDataFrame(pd.concat([points, extra], axis=1), geometry="geometry", crs="EPSG:4326")
    if Path(dst).exists():
        Path(dst).unlink()
    pyogrio.write_dataframe(out, dst, driver="GeoJSON")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    args = ap.parse_args()
    t0 = time.time()
    out = annotate(args.src, args.dst)
    print(f"{len(out)} points in {time.time() - t0:.1f}s -> {args.dst}")


if __name__ == "__main__":
    main()
