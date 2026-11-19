import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from common import OUT_DIR
from fetch_tiles import WORKERS, feature_info

CELL_M = 1000


def main():
    items = json.loads((OUT_DIR / "scan_index.json").read_text()) + json.loads((OUT_DIR / "positives_index.json").read_text())
    extra = OUT_DIR / "extra_positives_index.json"
    if extra.exists():
        items += json.loads(extra.read_text())
    cells = {}
    for it in items:
        cells.setdefault((int(it["x"] // CELL_M), int(it["y"] // CELL_M)), it)
    keys = list(cells)
    with ThreadPoolExecutor(WORKERS) as pool:
        infos = list(pool.map(lambda k: feature_info(cells[k]["lat"], cells[k]["lon"]), keys))
    by_cell = {f"{k[0]}_{k[1]}": info for k, info in zip(keys, infos)}
    tile_dates = {}
    for it in items:
        info = by_cell.get(f"{int(it['x'] // CELL_M)}_{int(it['y'] // CELL_M)}")
        tile_dates[it["tile_id"]] = info["aktualnosc"] if info else None
    (OUT_DIR / "ortho_dates.json").write_text(json.dumps({"cell_m": CELL_M, "cells": by_cell, "tiles": tile_dates}, ensure_ascii=False))
    print(f"cells {len(keys)}, missing {sum(v is None for v in infos)}")
    print(Counter((v["seria"], v["aktualnosc"]) for v in infos if v).most_common(20))


if __name__ == "__main__":
    main()
