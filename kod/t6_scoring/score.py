import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "dane"
T3_DIR = ROOT / "t3_exposure"
CANDIDATES = DATA / "candidates.geojson"
ANNOTATED = DATA / "exposure" / "candidates_t3.geojson"
HAZARD = DATA / "rail_hazard.geojson"
INTERVENTIONS = DATA / "interventions.json"
ATTRACTORS = DATA / "exposure" / "attractors.geojson"
HIGHWAY_TILES = DATA / "raw" / "wro_highways_tiles"
PLATFORMS = DATA / "raw" / "wro_platforms.json"
OUT_GEOJSON = DATA / "ranking.geojson"
OUT_CSV = DATA / "ranking.csv"
OUT_SENS = DATA / "t6_sensitivity.json"
CRS = "EPSG:2180"

HAZARD_RADIUS_M = 30
TOP_N = 20
PLACE_RADIUS_M = 300

DESTINATION_GROUPS = {
    "transport": ("station", "stop"),
    "school": ("school",),
    "shop": ("shop",),
    "workplace": ("workplace",),
    "allotments": ("allotments",),
    "park": ("park",),
    "sport": ("sport",),
    "residential": ("residential",),
}

BASE = {
    "w_exposure": 1.0,
    "w_detour": 1.0,
    "w_hazard": 1.0,
    "detour_lo_m": 100.0,
    "detour_hi_m": 1500.0,
    "vmax_ref_kmh": 160.0,
    "exposure_ref_pct": 95.0,
    "trains_ref_pct": 95.0,
    # 95th percentiles from the first 86 candidates, fixed so that dropping the
    # geometric_intersection rule (decision 17.11.2026) does not move the scale
    "exposure_ref": 30090.7,
    "trains_ref": 146.0,
    "hz_speed": 0.4,
    "hz_trains": 0.4,
    "hz_tracks": 0.2,
    "tracks_cap": 3,
    "yard_min_tracks": 5,
    "yard_detour_cap": 0.5,
    "exposure_transform": "sqrt",
}


def annotated_candidates():
    if not ANNOTATED.exists():
        sys.path.insert(0, str(T3_DIR))
        from annotate import annotate
        annotate(str(CANDIDATES), str(ANNOTATED))
    return gpd.read_file(ANNOTATED)


def attach_hazard(cand):
    hz = gpd.read_file(HAZARD).to_crs(CRS)
    pts = cand.to_crs(CRS)
    tree = shapely.STRtree(hz.geometry.values)
    rows = []
    for geom in pts.geometry.values:
        idx = tree.query(geom, predicate="dwithin", distance=HAZARD_RADIUS_M)
        if len(idx) == 0:
            rows.append({"hz_found": False})
            continue
        seg = hz.iloc[idx]
        nearest = seg.iloc[int(np.argmin(shapely.distance(seg.geometry.values, geom)))]
        vmax = seg["vmax_kmh"].where(seg["vmax_kmh"] > 0).max()
        rows.append({
            "hz_found": True,
            "line_nearest": line_str(nearest["line_no"]),
            "lines_30m": ";".join(sorted({line_str(v) for v in seg["line_no"].dropna()})),
            "vmax_kmh": None if pd.isna(vmax) else float(vmax),
            "vmax_nearest_kmh": nearest["vmax_kmh"],
            "trains_per_day": float(seg["trains_per_day_corridor"].max()),
            "trains_per_day_nearest": nearest["trains_per_day_corridor"],
            "trains_per_day_sat": float(seg["trains_per_day_corridor_sat"].max()),
            "vmax_freight_kmh": seg["vmax_freight_kmh"].max(),
        })
    out = pd.DataFrame(rows, index=cand.index)
    osm_speed = pd.to_numeric(cand["rail_maxspeed"], errors="coerce")
    missing = ~out["hz_found"]
    out.loc[missing, "line_nearest"] = cand.loc[missing, "rail_ref"].where(cand["rail_ref"] != "")
    out.loc[missing, "vmax_kmh"] = osm_speed[missing]
    out.loc[missing, "trains_per_day"] = 0.0
    out["vmax_source"] = np.where(out["hz_found"], "PLK zal. 2.1 (T2)",
                                  np.where(out["vmax_kmh"].notna(), "OSM maxspeed (bocznica)", "brak"))
    return out


def line_str(v):
    if pd.isna(v):
        return None
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def load_highways():
    ways = {}
    for path in sorted(HIGHWAY_TILES.glob("*.json")):
        for el in json.loads(path.read_text())["elements"]:
            if el["type"] == "way" and el["id"] not in ways and len(el.get("geometry", [])) >= 2:
                ways[el["id"]] = el
    return ways


def project_coords(geometry):
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    xs, ys = tr.transform([p["lon"] for p in geometry], [p["lat"] for p in geometry])
    return LineString(list(zip(xs, ys)))


STREET_CLASSES = {"residential", "tertiary", "secondary", "primary", "trunk", "unclassified", "living_street",
                  "pedestrian", "service", "tertiary_link", "secondary_link", "primary_link"}


def attach_context(cand):
    ways = load_highways()
    pts = cand.to_crs(CRS).geometry.values

    lit = []
    for osm_ids in cand["osm_ids"]:
        tags = [ways[int(s[4:])].get("tags", {}).get("lit") for s in osm_ids.split(";")
                if s.startswith("way/") and int(s[4:]) in ways and "highway" in ways[int(s[4:])].get("tags", {})]
        if "yes" in tags:
            lit.append("yes")
        elif "no" in tags:
            lit.append("no")
        else:
            lit.append("unknown")

    named = [(w["tags"]["name"], project_coords(w["geometry"])) for w in ways.values()
             if w.get("tags", {}).get("name") and w["tags"].get("highway") in STREET_CLASSES]
    street_tree = shapely.STRtree([g for _, g in named])
    street, street_d = [], []
    for p in pts:
        i = street_tree.nearest(p)
        street.append(named[i][0])
        street_d.append(round(float(named[i][1].distance(p))))

    plat_lines = [project_coords(el["geometry"]) for el in json.loads(PLATFORMS.read_text())["elements"]]
    plat_tree = shapely.STRtree(plat_lines)
    dist_platform = [round(float(plat_lines[plat_tree.nearest(p)].distance(p))) for p in pts]

    att = gpd.read_file(ATTRACTORS).to_crs(CRS)

    def nearest_of(mask, with_name=True):
        sub = att[mask & (att["name"].fillna("") != "")] if with_name else att[mask]
        tree = shapely.STRtree(sub.geometry.values)
        res = []
        for p in pts:
            i = tree.nearest(p)
            res.append((sub["name"].iloc[i], round(float(sub.geometry.iloc[i].distance(p)))))
        return res

    station = nearest_of(att["category"] == "station")
    school = nearest_of(att["category"] == "school", with_name=False)
    return pd.DataFrame({
        "lit": lit,
        "street": street, "street_m": street_d,
        "station": [s[0] for s in station], "station_m": [s[1] for s in station],
        "school_m": [s[1] for s in school],
        "dist_platform_m": dist_platform,
    }, index=cand.index)


def destination_kinds(df, side):
    kinds = []
    for group, cats in DESTINATION_GROUPS.items():
        kinds.append((sum(df[f"n_{c}_{side}"] for c in cats) > 0).astype(int).rename(group))
    return pd.concat(kinds, axis=1)


def base_frame():
    cand = annotated_candidates()
    df = cand.copy()
    df = df.join(attach_hazard(cand)).join(attach_context(cand))
    kinds_a, kinds_b = destination_kinds(df, "a"), destination_kinds(df, "b")
    df["dest_kinds_a"] = kinds_a.sum(axis=1)
    df["dest_kinds_b"] = kinds_b.sum(axis=1)
    df["dest_list_a"] = kinds_a.apply(lambda r: ",".join(k for k, v in r.items() if v), axis=1)
    df["dest_list_b"] = kinds_b.apply(lambda r: ",".join(k for k, v in r.items() if v), axis=1)
    df["cross_demand"] = df["pop_500m_a"] * df["dest_kinds_b"] + df["pop_500m_b"] * df["dest_kinds_a"]
    df["detour_m"] = df["detour_detour_m"]
    df["tracks_crossed"] = df["detour_tracks_crossed"].astype(int)
    df["hazard_tag_osm"] = df["sources"].str.contains("hazard_tag")
    pts = df.to_crs(CRS).geometry
    near = [int((pts.distance(p) <= 300).sum() - 1) for p in pts]
    df["other_candidates_300m"] = near
    return df


def ramp(x, lo, hi):
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def factors(df, p):
    exp_ref = np.percentile(df["cross_demand"], p["exposure_ref_pct"]) if "exposure_ref" not in p else p["exposure_ref"]
    rel = np.clip(df["cross_demand"] / exp_ref, 0, 1)
    if p["exposure_transform"] == "sqrt":
        e = np.sqrt(rel)
    elif p["exposure_transform"] == "log":
        e = np.clip(np.log1p(df["cross_demand"]) / np.log1p(exp_ref), 0, 1)
    else:
        e = rel

    d = ramp(df["detour_m"], p["detour_lo_m"], p["detour_hi_m"])
    yard = df["tracks_crossed"] >= p["yard_min_tracks"]
    d = np.where(yard, np.minimum(d, p["yard_detour_cap"]), d)

    tr_ref = np.percentile(df["trains_per_day"], p["trains_ref_pct"]) if "trains_ref" not in p else p["trains_ref"]
    s = np.clip(df["vmax_kmh"].fillna(0) / p["vmax_ref_kmh"], 0, 1)
    t = np.sqrt(np.clip(df["trains_per_day"] / tr_ref, 0, 1))
    k = np.minimum(df["tracks_crossed"], p["tracks_cap"]) / p["tracks_cap"]
    wsum = p["hz_speed"] + p["hz_trains"] + p["hz_tracks"]
    h = (p["hz_speed"] * s + p["hz_trains"] * t + p["hz_tracks"] * k) / wsum
    return {"E": np.asarray(e, float), "D": np.asarray(d, float), "H": np.asarray(h, float),
            "S": np.asarray(s, float), "T": np.asarray(t, float), "K": np.asarray(k, float),
            "exposure_ref": float(exp_ref), "trains_ref": float(tr_ref)}


def score(df, p):
    f = factors(df, p)
    w = p["w_exposure"] + p["w_detour"] + p["w_hazard"]
    log_prod = (p["w_exposure"] * np.log(np.maximum(f["E"], 1e-12)) + p["w_detour"] * np.log(np.maximum(f["D"], 1e-12))
                + p["w_hazard"] * np.log(np.maximum(f["H"], 1e-12)))
    s = 100 * np.exp(log_prod / w)
    s = np.where((f["E"] == 0) | (f["D"] == 0) | (f["H"] == 0), 0.0, s)
    return s, f


def ranks(s):
    return pd.Series(s).rank(ascending=False, method="min").astype(int).values


def spearman(a, b):
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def top_ids(ids, s, n=TOP_N):
    order = np.lexsort((ids, -s))
    return set(ids[order[:n]])


def group_places(xy, s, radius=PLACE_RADIUS_M):
    order = np.lexsort((np.arange(len(s)), -s))
    leader = np.full(len(s), -1)
    for i in order:
        if leader[i] >= 0:
            continue
        free = (leader < 0) & (np.hypot(*(xy - xy[i]).T) <= radius)
        leader[free] = i
    leaders = [i for i in order if leader[i] == i]
    place_rank = {ld: r + 1 for r, ld in enumerate(leaders)}
    return leader, np.array([place_rank[ld] for ld in leader])


def top_place_leaders(xy, s, n=TOP_N):
    leader, prank = group_places(xy, s)
    return sorted({int(ld) for ld, r in zip(leader, prank) if r <= n})


def place_matches(xy, base_leaders, leaders, radius=PLACE_RADIUS_M):
    return [b for b in base_leaders if min(np.hypot(*(xy[leaders] - xy[b]).T)) <= radius]


def sensitivity(df, base_score):
    ids = df["id"].values
    xy = np.column_stack([df.to_crs(CRS).geometry.x.values, df.to_crs(CRS).geometry.y.values])
    base_places = top_place_leaders(xy, base_score)
    base_top = top_ids(ids, base_score)
    place_hits = {b: 0 for b in base_places}
    place_hits_mc = {b: 0 for b in base_places}
    fixed = dict(BASE)
    f0 = factors(df, BASE)
    fixed["exposure_ref"], fixed["trains_ref"] = f0["exposure_ref"], f0["trains_ref"]
    numeric = ["w_exposure", "w_detour", "w_hazard", "detour_lo_m", "detour_hi_m", "vmax_ref_kmh", "exposure_ref",
               "trains_ref", "hz_speed", "hz_trains", "hz_tracks", "yard_detour_cap"]
    variants = []
    for key in numeric:
        for mult in (0.5, 1.5):
            p = dict(fixed)
            p[key] = fixed[key] * mult
            variants.append((f"{key} x{mult}", p))
    for cap in (2, 4):
        variants.append((f"tracks_cap={cap}", {**fixed, "tracks_cap": cap}))
    variants.append(("yard cap off", {**fixed, "yard_detour_cap": 1.0}))
    variants.append(("yard cap from 3 tracks", {**fixed, "yard_min_tracks": 3}))
    for tf in ("log", "linear"):
        variants.append((f"exposure transform {tf}", {**fixed, "exposure_transform": tf}))

    in_top = {i: 0 for i in ids}
    rows = []
    for name, p in variants:
        s, _ = score(df, p)
        top = top_ids(ids, s)
        for i in top:
            in_top[i] += 1
        matched = place_matches(xy, base_places, top_place_leaders(xy, s))
        for b in matched:
            place_hits[b] += 1
        rows.append({"variant": name, "top20_overlap": len(top & base_top),
                     "top20_places_overlap": len(matched),
                     "spearman": round(spearman(base_score, s), 3)})

    rng = np.random.default_rng(2026)
    mc_in_top = {i: 0 for i in ids}
    mc_overlap, mc_rho, mc_place = [], [], []
    n_mc = 2000
    for _ in range(n_mc):
        p = dict(fixed)
        for key in numeric:
            p[key] = fixed[key] * rng.uniform(0.5, 1.5)
        if p["detour_lo_m"] >= p["detour_hi_m"]:
            p["detour_lo_m"] = p["detour_hi_m"] / 2
        s, _ = score(df, p)
        top = top_ids(ids, s)
        for i in top:
            mc_in_top[i] += 1
        mc_overlap.append(len(top & base_top))
        matched = place_matches(xy, base_places, top_place_leaders(xy, s))
        for b in matched:
            place_hits_mc[b] += 1
        mc_place.append(len(matched))
        mc_rho.append(spearman(base_score, s))
    n_var = len(variants)
    stable = sorted([i for i in ids if in_top[i] == n_var])
    return {
        "variants": rows,
        "n_variants": n_var,
        "stable_top_all_variants": stable,
        "top20_share_one_at_a_time": {i: round(in_top[i] / n_var, 3) for i in ids if in_top[i]},
        "top20_places_stability": {ids[b]: {"one_at_a_time": round(place_hits[b] / n_var, 3),
                                            "monte_carlo": round(place_hits_mc[b] / n_mc, 3)} for b in base_places},
        "monte_carlo": {
            "n": n_mc,
            "rule": "all numeric parameters drawn independently from U(0.5, 1.5) x base",
            "top20_overlap_median": float(np.median(mc_overlap)),
            "top20_overlap_p05": float(np.percentile(mc_overlap, 5)),
            "top20_places_overlap_median": float(np.median(mc_place)),
            "top20_places_overlap_p05": float(np.percentile(mc_place, 5)),
            "spearman_median": round(float(np.median(mc_rho)), 3),
            "spearman_p05": round(float(np.percentile(mc_rho, 5)), 3),
            "top20_share": {i: round(mc_in_top[i] / n_mc, 3) for i in ids if mc_in_top[i]},
        },
    }


def interventions_catalog():
    return {i["id"]: i for i in json.loads(INTERVENTIONS.read_text())}


ASSUMED_QTY = {
    "I1_ogrodzenie_standard": (200, "2 x 100 m ogrodzenia kanalizującego (Clapperton: min. 100 m)"),
    "I15_bariera_zielen": (100, "100 m żywopłotu"),
    "I9_tablice": (2, "2 tablice, po jednej z każdej strony"),
}


def cost_text(item):
    lo, hi, unit = item["cost_pln_min"], item["cost_pln_max"], item["unit"]
    if lo is None:
        return None, None, "koszt nieustalony (brak publicznej ceny)"
    if item["id"] in ASSUMED_QTY:
        qty, note = ASSUMED_QTY[item["id"]]
        lo, hi = lo * qty, hi * qty
        return lo, hi, f"{fmt_pln(lo)}-{fmt_pln(hi)} zł (założenie: {note})"
    if lo == hi:
        return lo, hi, f"{fmt_pln(lo)} {unit}"
    return lo, hi, f"{fmt_pln(lo)}-{fmt_pln(hi)} {unit}"


def fmt_pln(v):
    return f"{v:,.0f}".replace(",", " ")


def assign_interventions(row):
    d, lvl, v, tr = row["detour_m"], row["exposure_level"], row["vmax_kmh"], row["tracks_crossed"]
    v = 0 if pd.isna(v) else v
    if d <= 300:
        return "R1", "I3_domkniecie_koncow_sciezki", "I15_bariera_zielen"
    if row["dist_platform_m"] <= 150:
        return "R7", "I13_przelozenie_dojscia_peron", "I4_maty_antywtargnieciowe"
    if lvl in ("mid", "high"):
        if v <= 160 and tr <= 3:
            return "R2", "I5_przejscie_kat_E", "I1_ogrodzenie_standard"
        return "R3/R4", "I6_kladka", "I1_ogrodzenie_standard"
    support = "I12_edukacja" if row["school_m"] <= 1000 else "I9_tablice"
    return "R9", "I11_patrol_sok", support


def build():
    df = base_frame()
    s, f = score(df, BASE)
    df["E_exposure"] = f["E"].round(3)
    df["D_detour"] = f["D"].round(3)
    df["H_hazard"] = f["H"].round(3)
    df["H_speed"] = f["S"].round(3)
    df["H_trains"] = f["T"].round(3)
    df["H_tracks"] = f["K"].round(3)
    df["score"] = s.round(1)
    df["rank"] = ranks(s)
    xy = np.column_stack([df.to_crs(CRS).geometry.x.values, df.to_crs(CRS).geometry.y.values])
    leader, prank = group_places(xy, s)
    df["place_rank"] = prank
    df["place_leader"] = leader == np.arange(len(df))
    df["place_members"] = [";".join(df["id"].values[leader == ld]) for ld in leader]
    df["exposure_level"] = pd.qcut(df["E_exposure"].rank(method="first"), 3, labels=["low", "mid", "high"]).astype(str)

    flags = []
    for _, r in df.iterrows():
        fl = []
        if 3 <= r["tracks_crossed"] < BASE["yard_min_tracks"]:
            fl.append("korytarz_wielotorowy")
        if r["tracks_crossed"] >= BASE["yard_min_tracks"]:
            fl.append("stacja_lub_grupa_torow_objazd_ograniczony")
        if not r["hz_found"]:
            fl.append("brak_toru_szlakowego_30m")
        elif r["trains_per_day"] == 0:
            fl.append("tylko_towarowe_ruch_nieznany")
        if pd.isna(r["vmax_kmh"]):
            fl.append("brak_vmax")
        if r["other_candidates_300m"] > 0:
            fl.append("ryzyko_przesuniecia")
        if r["hazard_tag_osm"]:
            fl.append("osm_hazard_illegal_crossing")
        flags.append(";".join(fl))
    df["flags"] = flags

    catalog = interventions_catalog()
    rules, prim, supp = zip(*df.apply(assign_interventions, axis=1))
    df["rule"], df["intervention_primary"] = rules, prim
    df["intervention_support"] = pd.Series(supp, index=df.index, dtype=object)
    for col in ("primary", "support"):
        costs = [cost_text(catalog[i]) if isinstance(i, str) else (None, None, None) for i in df[f"intervention_{col}"]]
        df[f"{col}_name"] = [catalog[i]["name_pl"] if isinstance(i, str) else None for i in df[f"intervention_{col}"]]
        df[f"{col}_cost_min_pln"] = [c[0] for c in costs]
        df[f"{col}_cost_max_pln"] = [c[1] for c in costs]
        df[f"{col}_cost_text"] = [c[2] for c in costs]
    df["sight_needed_m"] = (3 * df["vmax_kmh"]).round()

    sens = sensitivity(df, s)
    sens["base_params"] = BASE
    sens["exposure_ref"] = f["exposure_ref"]
    sens["trains_ref"] = f["trains_ref"]
    df["top20_share_mc"] = df["id"].map(sens["monte_carlo"]["top20_share"]).fillna(0.0)
    df["stable_top"] = df["id"].isin(sens["stable_top_all_variants"])
    OUT_SENS.write_text(json.dumps(sens, ensure_ascii=False, indent=1))

    df = df.sort_values(["rank", "id"])
    keep = ["id", "rank", "place_rank", "place_leader", "place_members", "score", "E_exposure", "D_detour", "H_hazard", "H_speed", "H_trains", "H_tracks",
            "exposure_level", "flags", "stable_top", "top20_share_mc",
            "lat", "lon", "sources", "highway_types", "street", "street_m", "station", "station_m",
            "line_nearest", "lines_30m", "vmax_kmh", "vmax_source", "vmax_freight_kmh", "trains_per_day",
            "trains_per_day_sat", "tracks_crossed",
            "detour_m", "detour_walk_m", "detour_straight_m", "detour_ratio", "legal_crossing_type", "legal_crossing_lat",
            "legal_crossing_lon", "pop_500m", "pop_500m_a", "pop_500m_b", "dest_kinds_a", "dest_kinds_b",
            "dest_list_a", "dest_list_b", "cross_demand", "lit", "dist_platform_m", "school_m", "other_candidates_300m",
            "nearest_official_m", "rule", "intervention_primary", "primary_name", "primary_cost_min_pln",
            "primary_cost_max_pln", "primary_cost_text", "intervention_support", "support_name",
            "support_cost_min_pln", "support_cost_max_pln", "support_cost_text", "sight_needed_m", "geoportal_url"]
    out = gpd.GeoDataFrame(df[keep], geometry=df.geometry, crs="EPSG:4326")
    if OUT_GEOJSON.exists():
        OUT_GEOJSON.unlink()
    pyogrio.write_dataframe(out, OUT_GEOJSON, driver="GeoJSON")
    out.drop(columns="geometry").to_csv(OUT_CSV, index=False)
    return out, sens


def main():
    out, sens = build()
    pd.set_option("display.width", 220)
    print(out[out["place_leader"]].sort_values("place_rank")[["place_rank", "rank", "id", "score", "E_exposure", "D_detour", "H_hazard", "detour_m", "vmax_kmh", "trains_per_day",
               "tracks_crossed", "flags", "intervention_primary"]].head(TOP_N).to_string(index=False))
    print(pd.DataFrame(sens["variants"]).to_string(index=False))
    mc = sens["monte_carlo"]
    print(f"MC: overlap median {mc['top20_overlap_median']} p05 {mc['top20_overlap_p05']}, "
          f"places median {mc['top20_places_overlap_median']} p05 {mc['top20_places_overlap_p05']}, "
          f"rho median {mc['spearman_median']} p05 {mc['spearman_p05']}")
    print("stable top:", sens["stable_top_all_variants"])


if __name__ == "__main__":
    main()
