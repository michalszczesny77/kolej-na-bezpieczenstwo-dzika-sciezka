import sys
from pathlib import Path

import pyogrio
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CRS, GUS_GRID, OUT, POPULATION_FILE, bbox_with_margin


def main():
    s, w, n, e = bbox_with_margin()
    t = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
    xs, ys = t.transform([w, e, w, e], [s, s, n, n])
    grid = pyogrio.read_dataframe(GUS_GRID, bbox=(min(xs), min(ys), max(xs), max(ys)))
    grid = grid.rename(columns={"TOT": "pop"})[["code", "pop", "geometry"]]
    grid = grid.to_crs(CRS)
    OUT.mkdir(parents=True, exist_ok=True)
    pyogrio.write_dataframe(grid, POPULATION_FILE, layer="grid250")
    print(f"cells={len(grid)} populated={(grid['pop'] > 0).sum()} total_pop={int(grid['pop'].sum())}")


if __name__ == "__main__":
    main()
