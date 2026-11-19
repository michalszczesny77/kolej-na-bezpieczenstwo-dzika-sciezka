import json
import random
import sys

import numpy as np
from scipy.spatial import cKDTree

from common import DATA_DIR, OUT_DIR, to_2180

N_NEG = 600
MIN_DIST_M = 150
SEED = 7
HARD_DIST_M = 25
HARD_N = 150


def known_points():
    pts = [(o[0], o[1]) for o in json.loads((OUT_DIR / "official_points.json").read_text())]
    pts += [(p["x"], p["y"]) for p in json.loads((OUT_DIR / "positives_index.json").read_text()) if p.get("in_bbox", True)]
    return np.array(pts)


def random_negatives():
    scan = json.loads((OUT_DIR / "scan_index.json").read_text())
    tree = cKDTree(known_points())
    dist, _ = tree.query(np.array([(s["x"], s["y"]) for s in scan]))
    pool = [s for s, d in zip(scan, dist) if d > MIN_DIST_M]
    neg = random.Random(SEED).sample(pool, N_NEG)
    (OUT_DIR / "negatives_index.json").write_text(json.dumps(neg))
    print(f"scan {len(scan)}, eligible (> {MIN_DIST_M} m) {len(pool)}, sampled {len(neg)}")


def platform_points():
    data = json.loads((DATA_DIR / "raw" / "wro_platforms.json").read_text())
    return np.array([to_2180(g["lon"], g["lat"]) for el in data["elements"] if el["type"] == "way"
                     for g in el.get("geometry", [])])


def hard_negatives():
    scan = json.loads((OUT_DIR / "scan_index.json").read_text())
    xy = np.array([(s["x"], s["y"]) for s in scan])
    off = json.loads((OUT_DIR / "official_points.json").read_text())
    grade = np.array([(o[0], o[1]) for o in off if o[2] in ("underpass", "overpass")])
    d_grade, _ = cKDTree(grade).query(xy)
    d_plat, _ = cKDTree(platform_points()).query(xy)
    rng = random.Random(SEED)
    bridges = [s for s, d in zip(scan, d_grade) if d <= HARD_DIST_M]
    platforms = [s for s, d in zip(scan, d_plat) if d <= HARD_DIST_M]
    picked = {s["tile_id"]: dict(s, hard="grade_separated") for s in rng.sample(bridges, min(HARD_N, len(bridges)))}
    for s in rng.sample(platforms, min(HARD_N, len(platforms))):
        picked.setdefault(s["tile_id"], dict(s, hard="platform"))
    review = json.loads((OUT_DIR / "labels_top40_round1.json").read_text())["labels"]
    by_id = {s["tile_id"]: s for s in scan}
    for tid, lab in review.items():
        if lab == "false_positive":
            picked.setdefault(tid, dict(by_id[tid], hard="round1_false_positive"))
    out = list(picked.values())
    (OUT_DIR / "hard_negatives_index.json").write_text(json.dumps(out))
    print(f"hard negatives: grade-separated pool {len(bridges)}, platform pool {len(platforms)}, total {len(out)}")


if __name__ == "__main__":
    hard_negatives() if sys.argv[1:] == ["hard"] else random_negatives()
