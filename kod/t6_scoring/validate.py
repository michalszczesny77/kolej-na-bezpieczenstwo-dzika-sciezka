import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "dane"
RANKING = DATA / "ranking.geojson"
VALIDATION = DATA / "validation.geojson"
HAZARD = DATA / "rail_hazard.geojson"
OUT_CSV = DATA / "t6_validation_events.csv"
OUT_JSON = DATA / "t6_validation.json"
CRS = "EPSG:2180"

TOP_N = 20
MIN_RADIUS_M = 100
FLAT_RADIUS_M = 300
BASELINE_NEAR_CANDIDATES_M = 1000
N_PERM = 10000
SEED = 2026


def usable_events():
    ev = gpd.read_file(VALIDATION)
    ev = ev[ev.geometry.notna()]
    mask = (ev["kind"] == "accident") & (ev["use_for_validation"] == True) & ev["precision"].isin(["exact", "approx"])
    ev = ev[mask & (ev["in_wro_bbox"] == True)].copy()
    ev["radius_m"] = np.maximum(pd.to_numeric(ev["uncertainty_m"], errors="coerce").fillna(MIN_RADIUS_M), MIN_RADIUS_M)
    return ev.to_crs(CRS)


def sample_rail_points(lines, n, rng):
    lengths = shapely.length(lines)
    cum = np.cumsum(lengths)
    pos = rng.uniform(0, cum[-1], n)
    idx = np.searchsorted(cum, pos)
    offset = pos - (cum[idx] - lengths[idx])
    pts = shapely.line_interpolate_point(lines[idx], offset)
    return np.column_stack([shapely.get_x(pts), shapely.get_y(pts)])


def hit_share(event_xy, radii, site_xy):
    d = np.hypot(event_xy[:, None, 0] - site_xy[None, :, 0], event_xy[:, None, 1] - site_xy[None, :, 1])
    return float(np.mean(d.min(axis=1) <= radii))


def permutation_test(observed, lines, radii, site_xy, rng):
    sims = np.empty(N_PERM)
    for k in range(N_PERM):
        sims[k] = hit_share(sample_rail_points(lines, len(radii), rng), radii, site_xy)
    return {"observed": round(observed, 3), "random_mean": round(float(sims.mean()), 3),
            "random_p95": round(float(np.percentile(sims, 95)), 3),
            "p_value": round(float((np.sum(sims >= observed) + 1) / (N_PERM + 1)), 4)}


def rank_test(ranks, mask, rng):
    ranks = np.asarray(ranks, float)
    mask = np.asarray(mask, bool)
    k = int(mask.sum())
    if k == 0:
        return None
    observed = ranks[mask].mean()
    sims = np.array([rng.choice(ranks, k, replace=False).mean() for _ in range(N_PERM)])
    return {"n": k, "mean_rank": round(float(observed), 1), "median_rank": float(np.median(ranks[mask])),
            "random_mean_rank": round(float(sims.mean()), 1),
            "p_value_better_than_random": round(float((np.sum(sims <= observed) + 1) / (N_PERM + 1)), 4)}


def main():
    rng = np.random.default_rng(SEED)
    rk = gpd.read_file(RANKING).to_crs(CRS)
    cand_xy = np.column_stack([rk.geometry.x.values, rk.geometry.y.values])
    n_cand = len(rk)
    summary = {"n_candidates": n_cand}

    hz_mask = rk["sources"].str.contains("hazard_tag").values
    summary["osm_hazard_tag_ranks"] = {
        "note": "score does not use the source field; these places are also a candidate source",
        "ids": rk.loc[hz_mask, "id"].tolist(),
        "ranks": rk.loc[hz_mask, "rank"].astype(int).tolist(),
        "in_top20": int((rk.loc[hz_mask, "rank"] <= TOP_N).sum()),
        "test": rank_test(rk["rank"].values, hz_mask, rng),
    }

    if not VALIDATION.exists():
        summary["accidents"] = "pending: validation.geojson not found"
        OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1))
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return

    ev = usable_events()
    ev_xy = np.column_stack([ev.geometry.x.values, ev.geometry.y.values])
    radii = ev["radius_m"].values
    dist = np.hypot(ev_xy[:, None, 0] - cand_xy[None, :, 0], ev_xy[:, None, 1] - cand_xy[None, :, 1])

    top_place = (rk["place_rank"] <= TOP_N).values
    top_cand = (rk["rank"] <= TOP_N).values
    rows = []
    for i, (_, e) in enumerate(ev.iterrows()):
        j = int(np.argmin(dist[i]))
        within = dist[i] <= radii[i]
        within300 = dist[i] <= FLAT_RADIUS_M
        rows.append({
            "event_id": e["id"], "date": e["date"], "precision": e["precision"], "radius_m": radii[i],
            "nearest_candidate": rk["id"].iloc[j], "nearest_m": round(float(dist[i, j])),
            "nearest_rank": int(rk["rank"].iloc[j]), "nearest_place_rank": int(rk["place_rank"].iloc[j]),
            "n_candidates_in_radius": int(within.sum()),
            "best_rank_in_radius": int(rk["rank"].values[within].min()) if within.any() else None,
            "top20_place_in_radius": bool((within & top_place).any()),
            "top20_place_in_300m": bool((within300 & top_place).any()),
            "any_candidate_in_300m": bool(within300.any()),
        })
    table = pd.DataFrame(rows)
    table.to_csv(OUT_CSV, index=False)

    hz = gpd.read_file(HAZARD).to_crs(CRS)
    lines_all = hz.geometry.values
    near_pool = shapely.union_all(shapely.buffer(shapely.points(cand_xy), BASELINE_NEAR_CANDIDATES_M))
    lines_near = np.array([g for g in shapely.intersection(lines_all, near_pool) if not g.is_empty and g.length > 0])
    lines_near = np.array([part for g in lines_near for part in getattr(g, "geoms", [g]) if part.length > 0])

    place_xy = cand_xy[top_place]
    top_xy = cand_xy[top_cand]
    flat = np.full(len(ev), float(FLAT_RADIUS_M))
    near_any = dist.min(axis=0)
    summary["accidents"] = {
        "filter": "kind=accident, use_for_validation, precision exact|approx, geometry present, in WRO bbox",
        "n_events": len(ev),
        "radius_rule": f"uncertainty_m per event, min {MIN_RADIUS_M} m",
        "no_candidate_in_radius": int((table["n_candidates_in_radius"] == 0).sum()),
        "no_candidate_in_300m": int((~table["any_candidate_in_300m"]).sum()),
        "candidates_matched_by_event_radius": int((dist <= radii[:, None]).any(axis=0).sum()),
        "top20_places": {
            "n_points": int(top_place.sum()),
            "event_radius": permutation_test(hit_share(ev_xy, radii, place_xy), lines_all, radii, place_xy, rng),
            "flat_300m": permutation_test(hit_share(ev_xy, flat, place_xy), lines_all, flat, place_xy, rng),
            "event_radius_baseline_near_candidates": permutation_test(
                hit_share(ev_xy, radii, place_xy), lines_near, radii, place_xy, rng),
        },
        "top20_candidates": {
            "event_radius": permutation_test(hit_share(ev_xy, radii, top_xy), lines_all, radii, top_xy, rng),
            "flat_300m": permutation_test(hit_share(ev_xy, flat, top_xy), lines_all, flat, top_xy, rng),
        },
        "all_candidates": {
            "event_radius": permutation_test(hit_share(ev_xy, radii, cand_xy), lines_all, radii, cand_xy, rng),
            "flat_300m": permutation_test(hit_share(ev_xy, flat, cand_xy), lines_all, flat, cand_xy, rng),
        },
        "rank_of_matched_candidates": {
            "event_radius": rank_test(rk["rank"].values, (dist <= radii[:, None]).any(axis=0), rng),
            "flat_300m": rank_test(rk["rank"].values, near_any <= FLAT_RADIUS_M, rng),
        },
        "baseline": f"{N_PERM} draws of {len(ev)} uniform points on T2 running track (all in bbox, and only within "
                    f"{BASELINE_NEAR_CANDIDATES_M} m of any candidate), same radii as the events",
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    pd.set_option("display.width", 220)
    print(table.to_string(index=False))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
