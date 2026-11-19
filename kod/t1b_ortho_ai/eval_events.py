import json
import sys

import numpy as np
from scipy.spatial import cKDTree

from common import OUT_DIR

N_NULL = 2000
SEED = 11
TOP_SHARE = 0.10


def max_within(tree, scores, centre, radius):
    idx = tree.query_ball_point(centre, radius)
    return (scores[idx].max(), len(idx)) if idx else (np.nan, 0)


def main(round_no):
    scan = json.loads((OUT_DIR / f"scan_scores_round{round_no}.json").read_text())
    events = [e for e in json.loads((OUT_DIR / "validation_events.json").read_text()) if e["in_bbox"]]
    xy = np.array([(s["x"], s["y"]) for s in scan])
    scores = np.array([s["ai_score"] for s in scan])
    tree = cKDTree(xy)
    thr = np.quantile(scores, 1 - TOP_SHARE)
    rng = np.random.default_rng(SEED)
    rows, pct, hit, hit_null = [], [], [], []
    for e in events:
        actual, n = max_within(tree, scores, (e["x"], e["y"]), e["radius"])
        if n == 0:
            rows.append({"id": e["id"], "radius_m": e["radius"], "n_tiles": 0})
            continue
        centres = xy[rng.integers(0, len(xy), N_NULL)]
        null = np.array([max_within(tree, scores, c, e["radius"])[0] for c in centres])
        p = float((null < actual).mean() + 0.5 * (null == actual).mean())
        pct.append(p)
        hit.append(actual >= thr)
        hit_null.append(float((null >= thr).mean()))
        rows.append({"id": e["id"], "radius_m": e["radius"], "n_tiles": n, "max_score": round(float(actual), 3),
                     "percentile_vs_random_rail": round(p, 3), "has_top10pct_tile": bool(actual >= thr),
                     "null_rate_top10pct": round(hit_null[-1], 3)})
    pct = np.array(pct)
    sims = rng.random((20000, len(pct))).mean(axis=1)
    hits_null_sim = (rng.random((20000, len(hit_null))) < np.array(hit_null)).sum(axis=1)
    summary = {"n_events_in_bbox": len(events), "n_events_with_tiles": len(pct),
               "mean_percentile": round(float(pct.mean()), 3),
               "p_value_mean_percentile_gt_0_5": round(float((sims >= pct.mean()).mean()), 4),
               "events_with_top10pct_tile": int(np.sum(hit)),
               "expected_under_random_rail": round(float(np.sum(hit_null)), 2),
               "p_value_hits": round(float((hits_null_sim >= np.sum(hit)).mean()), 4),
               "score_threshold_top10pct": round(float(thr), 3)}
    (OUT_DIR / f"events_check_round{round_no}.json").write_text(json.dumps({"summary": summary, "events": rows}, indent=1))
    print(json.dumps(summary, indent=1))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(int(sys.argv[1]))
