import json
import sys
import time

import numpy as np
from scipy.spatial import cKDTree
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from baseline import line_score
from common import OUT_DIR

GROUP_CELL_M = 2000
N_FOLDS = 5
C = 0.05
SEEDS = range(5)
EXCLUDE_M = 50
NMS_M = 100
TOP_N = 40


def load_json(name):
    return json.loads((OUT_DIR / name).read_text())


def model(c=C):
    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=5000, class_weight="balanced"))


def precision_at(y, s, k):
    order = np.argsort(-s)[:k]
    return float(y[order].mean())


def metrics(y, s):
    return {"roc_auc": round(roc_auc_score(y, s), 3), "avg_precision": round(average_precision_score(y, s), 3),
            "p_at_10": round(precision_at(y, s, 10), 2), "p_at_20": round(precision_at(y, s, 20), 2),
            "p_at_40": round(precision_at(y, s, 40), 2), "n_pos": int(y.sum()), "n_neg": int((1 - y).sum())}


def training_set(round_no):
    labels = load_json("labels_positives.json")["labels"]
    extra_labels = load_json("labels_extra_positives.json")["labels"]
    pos = [dict(p, kind="pos") for p in load_json("positives_index.json") if labels[p["tile_id"]] == "pos"]
    pos += [dict(p, kind="pos") for p in load_json("extra_positives_index.json") if extra_labels.get(p["tile_id"]) == "pos"]
    neg_drop = set(load_json("labels_negatives.json")["drop"])
    neg = [dict(n, kind="random_neg") for n in load_json("negatives_index.json") if n["tile_id"] not in neg_drop]
    if round_no >= 2:
        have = {n["tile_id"] for n in neg}
        neg += [dict(n, kind="hard_neg") for n in load_json("hard_negatives_index.json") if n["tile_id"] not in have]
    items = pos + neg
    y = np.array([1] * len(pos) + [0] * len(neg))
    groups = np.array([hash((int(it["x"] // GROUP_CELL_M), int(it["y"] // GROUP_CELL_M))) for it in items])
    return items, y, groups


def oof_scores(X, y, groups, c=C):
    oof_all = np.zeros((len(SEEDS), len(y)))
    for si, seed in enumerate(SEEDS):
        cv = StratifiedGroupKFold(N_FOLDS, shuffle=True, random_state=seed)
        for tr, te in cv.split(X, y, groups):
            oof_all[si, te] = model(c).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return oof_all


def summarize(y, oof_all, masks):
    per_seed = [metrics(y, o) for o in oof_all]
    out = {"roc_auc_per_seed": [m["roc_auc"] for m in per_seed],
           "avg_precision_per_seed": [m["avg_precision"] for m in per_seed],
           "p_at_20_per_seed": [m["p_at_20"] for m in per_seed]}
    oof = oof_all.mean(axis=0)
    for name, mask in masks.items():
        out[name] = metrics(y[mask], oof[mask])
    return out


def nms(items, scores, dist):
    order = np.argsort(-scores)
    kept, pts = [], []
    for i in order:
        p = (items[i]["x"], items[i]["y"])
        if all(np.hypot(p[0] - q[0], p[1] - q[1]) > dist for q in pts):
            kept.append(i)
            pts.append(p)
    return kept


def main(round_no):
    t0 = time.time()
    emb = np.load(OUT_DIR / "embeddings_dinov2s.npz")
    items, y, groups = training_set(round_no)
    X = np.stack([emb[it["tile_id"]] for it in items])
    kind = np.array([it["kind"] for it in items])
    in_bbox = np.array([it.get("in_bbox", True) for it in items])
    print(f"round {round_no} train: {int(y.sum())} pos ({int(y[in_bbox].sum())} in Wroclaw bbox), "
          f"{int((kind == 'random_neg').sum())} random neg, {int((kind == 'hard_neg').sum())} hard neg, "
          f"{len(set(groups))} spatial groups")

    masks = {"all": np.ones(len(y), bool), "wroclaw_only": in_bbox, "pos_vs_random_neg": kind != "hard_neg"}
    if round_no >= 2:
        masks["pos_vs_hard_neg"] = kind != "random_neg"
    oof_all = oof_scores(X, y, groups)
    report = {"round": round_no, "C": C, "cv": summarize(y, oof_all, masks)}
    base = np.array([line_score(it) for it in items])
    report["baseline_line_filter"] = {k: metrics(y[m], base[m]) for k, m in masks.items()}
    report["C_sensitivity_roc_auc_seed0"] = {
        str(c): round(roc_auc_score(y, oof_scores(X, y, groups, c)[0]), 3) for c in (0.005, 0.05, 0.5)}
    print(json.dumps(report, indent=1))

    final = model().fit(X, y)
    scan = [s for s in load_json("scan_index.json") if s["tile_id"] in emb.files]
    scores = final.predict_proba(np.stack([emb[s["tile_id"]] for s in scan]))[:, 1]
    oof = oof_all.mean(axis=0)
    oof_by_id = {it["tile_id"]: o for it, o in zip(items, oof)}
    scores = np.array([oof_by_id.get(s["tile_id"], sc) for s, sc in zip(scan, scores)])
    dates = load_json("ortho_dates.json")["tiles"]
    for s, sc in zip(scan, scores):
        s["ai_score"] = round(float(sc), 4)
        s["ortho_date"] = dates.get(s["tile_id"])

    official_tree = cKDTree(np.array([(o[0], o[1]) for o in load_json("official_points.json")]))
    t1_tree = cKDTree(np.array([(p["x"], p["y"]) for p in load_json("positives_index.json") if p.get("in_bbox", True)]))
    xy = np.array([(s["x"], s["y"]) for s in scan])
    d_off, _ = official_tree.query(xy)
    d_t1, _ = t1_tree.query(xy)
    for s, a, b in zip(scan, d_off, d_t1):
        s["dist_official_m"] = round(float(a), 1)
        s["dist_t1_m"] = round(float(b), 1)
    (OUT_DIR / f"scan_scores_round{round_no}.json").write_text(json.dumps(scan))

    reviewed = set()
    for r in range(1, round_no):
        reviewed |= set(load_json(f"labels_top40_round{r}.json")["labels"])
    new_mask = (d_off > EXCLUDE_M) & (d_t1 > EXCLUDE_M) & np.array([s["tile_id"] not in reviewed for s in scan])
    new_items = [s for s, m in zip(scan, new_mask) if m]
    new_scores = scores[new_mask]
    top = [new_items[i] for i in nms(new_items, new_scores, NMS_M)[:TOP_N]]
    (OUT_DIR / f"top_new_round{round_no}.json").write_text(json.dumps(top, indent=0))

    near_off = d_off <= EXCLUDE_M
    report["scan"] = {"n_tiles": len(scan), "n_new_eligible": int(new_mask.sum()),
                      "mean_score_within_50m_official": round(float(scores[near_off].mean()), 3),
                      "mean_score_new_eligible": round(float(new_scores.mean()), 3),
                      "share_ge_0_5_new_eligible": round(float((new_scores >= 0.5).mean()), 3),
                      "top40_score_range": [top[-1]["ai_score"], top[0]["ai_score"]]}
    report["runtime_s"] = round(time.time() - t0, 1)
    (OUT_DIR / f"cv_report_round{round_no}.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report["scan"], indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]))
