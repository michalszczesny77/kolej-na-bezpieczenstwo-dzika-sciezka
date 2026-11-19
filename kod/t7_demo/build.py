import base64
import csv
import io
import json
import math
import re
import sys
import urllib.request
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT.parent / "dane"
OUT_DIR = ROOT.parent / "demo"
VENDOR = HERE / "vendor"
TEMPLATE = HERE / "template.html"

sys.path.insert(0, str(ROOT / "t6_scoring"))
from cards import CROSSING_PL, DEST_PL, lines_text, rule_note  # noqa: E402

TOP_N = 20
CROP_PX = 560
MAX_BYTES = 15 * 1024 * 1024

CDN = "https://cdn.jsdelivr.net/npm/"
LEAFLET = {"leaflet.js": "leaflet@1.9.4/dist/leaflet.js", "leaflet.css": "leaflet@1.9.4/dist/leaflet.css"}
LATIN = ("U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,"
         "U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD")
LATIN_EXT = ("U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,"
             "U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF")
FONTS = [
    ("IBM Plex Sans", "ibm-plex-sans@5.1.0", "ibm-plex-sans", 400),
    ("IBM Plex Sans", "ibm-plex-sans@5.1.0", "ibm-plex-sans", 600),
    ("IBM Plex Mono", "ibm-plex-mono@5.1.0", "ibm-plex-mono", 400),
]

PRIMARY_SHORT = {
    "I5_przejscie_kat_E": "legalne przejście kat. E",
    "I6_kladka": "kładka dla pieszych",
    "I7_tunel_pieszy": "przejście podziemne",
    "I13_przelozenie_dojscia_peron": "nowe dojście do peronu",
    "I11_patrol_sok": "patrol SOK",
    "I3_domkniecie_koncow_sciezki": "domknięcie ścieżki",
}
OUTCOME_PL = {"killed": "zabity", "injured": "ranny"}
LABEL_PL = {"real": "ścieżka potwierdzona na zdjęciu", "unsure": "niepewne"}
ETAP0_DEFAULT = "Etap 0 (od zaraz): patrol SOK 18-23 + pomiar ruchu przed/po."
ETAP0_KEEP = " Patrol zostaje do czasu wykonania rozwiązania głównego."
R0 = {"name": "Tablice z informacją o mandacie (2 szt.)", "cost": "600-4 000 zł"}
KM_POINT_MAX_M = 150


def fetch(rel, name):
    path = VENDOR / name
    if not path.exists():
        VENDOR.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(CDN + rel, timeout=60) as resp:
            path.write_bytes(resp.read())
    return path


def font_css():
    rules = []
    for family, pkg, stem, weight in FONTS:
        for subset, rng in (("latin", LATIN), ("latin-ext", LATIN_EXT)):
            file = f"{stem}-{subset}-{weight}-normal.woff2"
            b64 = base64.b64encode(fetch(f"@fontsource/{pkg}/files/{file}", file).read_bytes()).decode()
            rules.append(f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{weight};font-display:swap;"
                         f"src:url(data:font/woff2;base64,{b64}) format('woff2');unicode-range:{rng};}}")
    return "\n".join(rules)


def is_missing(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def num(v, digits=0):
    return f"{v:,.{digits}f}".replace(",", " ").replace(".", ",")


def dist(m):
    return f"{num(m)} m" if m < 1000 else f"{num(m / 1000, 1)} km"


def plural(n, one, few, many):
    n = int(n)
    if n == 1:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def dest_text(lst):
    if not lst:
        return "brak celów w OSM"
    return ", ".join(DEST_PL.get(k, k) for k in lst.split(","))


def measure(name, cost_text):
    name = name.replace(" (nudge)", "")
    cost, _, note = (cost_text or "koszt nieustalony").partition(" (")
    if cost.startswith("koszt nieustalony"):
        return {"name": name, "cost": "koszt do ustalenia", "costNote": ""}
    return {"name": name, "cost": cost, "costNote": note[:-1] if note.endswith(")") else note}


def title_case(text):
    def word(w):
        return w if re.fullmatch(r"W[A-Z]{1,2}\d?", w) else w.capitalize()
    return "; ".join(" ".join(word(w) for w in part.split(" ")) for part in (text or "").split(";"))


def safe_rule_note(r):
    if r.intervention_primary == "I6_kladka":
        return ("Ponad 3 tory lub ponad 160 km/h: kat. E z systemem przejazdowym albo kładka/tunel; "
                "ponad 160 km/h tylko kładka/tunel (Dz.U. 2025 poz. 1105, § 5 i § 11). "
                "Kładka lub tunel to nasz wybór projektowy; koszt kat. E z systemem przejazdowym do ustalenia.")
    if r.intervention_primary == "I13_przelozenie_dojscia_peron":
        return f"Kandydat {num(r.dist_platform_m)} m od peronu (próg: 150 m)."
    if r.intervention_primary == "I3_domkniecie_koncow_sciezki":
        return ("Objazd do 300 m: ogrodzenie kierujące ruch do istniejącego legalnego przejścia. "
                "Efekt z badania fińskiego: o 94,6% mniej przejść na dobę (1 miejsce, 11 dni).")
    if r.intervention_primary == "I5_przejscie_kat_E" and r.sight_needed_m is None:
        note = rule_note(SimpleNamespace(**{**vars(r), "sight_needed_m": 0}))
        return note.replace("L2 = 3 x Vr = 0 m", "L2 = 3 x Vr (prędkość nieznana)")
    return rule_note(r)


def card_lines(n, pid):
    path = next(iter((DATA / "top20").glob(f"{n:02d}_{pid}.md")), None)
    if not path:
        return {}
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        for key in ("Etap 0", "Ilustracja koszt-korzyść"):
            if line.startswith(f"- {key}"):
                found[key] = line[2:].strip()
    return found


def crop_data_uri(n, pid):
    path = DATA / "top20" / f"{n:02d}_{pid}.jpg"
    if not path.exists():
        return None
    img = Image.open(path).convert("RGB")
    img.thumbnail((CROP_PX, CROP_PX))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def site_record(p, n_candidates, rails_gj):
    r = SimpleNamespace(**{k: (None if is_missing(v) else v) for k, v in p.items()})
    top = r.place_rank if r.place_leader and r.place_rank and r.place_rank <= TOP_N else None
    trains = int(r.trains_per_day or 0)
    tracks = int(r.tracks_crossed or 0)
    vmax = "prędkość nieznana" if r.vmax_kmh is None else f"{int(r.vmax_kmh)} km/h"
    lines = lines_text(r)
    line_set = set((r.lines_30m or r.line_nearest or "").split(";")) - {""}
    km = line_km(r.lat, r.lon, line_set, rails_gj)
    km_text = ""
    if km is not None:
        km_text = km_label(*km[1:])
        if len(line_set) > 1:
            km_text += f" (linia {km[0]})"

    e_short = f"{num(r.pop_500m or 0)} mieszkańców w 500 m"
    e_detail = (f"Strona A: {num(r.pop_500m_a or 0)} mieszk., cele: {dest_text(r.dest_list_a)}. "
                f"Strona B: {num(r.pop_500m_b or 0)} mieszk., cele: {dest_text(r.dest_list_b)}.")
    if r.detour_m is None:
        d_short, d_detail = "objazd nieznany", ""
    else:
        d_short = f"legalnie {dist(r.detour_walk_m)} zamiast {dist(r.detour_straight_m)} na skróty"
        d_detail = f"Objazd {dist(r.detour_m)}, {num(r.detour_ratio, 1)} razy dłużej."
        if r.legal_crossing_type in CROSSING_PL:
            d_detail += f" Najbliższe legalne przejście: {CROSSING_PL[r.legal_crossing_type]}."
    h_short = (f"{trains} {plural(trains, 'pociąg pasażerski', 'pociągi pasażerskie', 'pociągów pasażerskich')} na dobę, {vmax}, "
               f"{tracks} {plural(tracks, 'tor', 'tory', 'torów')}")
    h_detail = "Rozkład ze środy 18.11.2026, wszystkie linie w promieniu 30 m. Ruch towarowy nieznany (brak danych publicznych)."

    from_card = card_lines(top, r.id) if top else {}
    etap0 = from_card.get("Etap 0") or ETAP0_DEFAULT + ("" if r.intervention_primary == "I11_patrol_sok" else ETAP0_KEEP)
    support = None
    if r.support_name:
        support = measure(r.support_name, r.support_cost_text)

    return {
        "id": r.id, "lat": round(r.lat, 6), "lon": round(r.lon, 6),
        "score": r.score or 0, "rank": r.rank, "place": r.place_rank, "leader": bool(r.place_leader), "top": top,
        "n": n_candidates,
        "title": r.street or "bez nazwy ulicy", "lines": lines, "km": km_text,
        "station": f"{r.station} ({dist(r.station_m)})" if r.station and r.station_m is not None else "",
        "members": [m for m in (r.place_members or "").split(";") if m and m != r.id],
        "E": r.E_exposure or 0, "D": r.D_detour or 0, "H": r.H_hazard or 0,
        "e": e_short, "eD": e_detail, "d": d_short, "dD": d_detail, "h": h_short, "hD": h_detail,
        "etap0": etap0,
        "primary": measure(r.primary_name, r.primary_cost_text),
        "short": PRIMARY_SHORT.get(r.intervention_primary, r.primary_name),
        "support": support,
        "r0": None if "I9_tablice" in (r.intervention_primary, r.intervention_support) else R0,
        "note": safe_rule_note(r),
        "geoportal": r.geoportal_url,
        "img": crop_data_uri(top, r.id) if top else None,
    }


def km_label(k0, k1):
    """Point km only when the PLK segment is short enough; otherwise the honest range."""
    lo, hi = sorted((k0, k1))
    if (hi - lo) * 1000 / 2 <= KM_POINT_MAX_M:
        return f"km ok. {num((lo + hi) / 2, 1)}"
    return f"km {num(lo, 1)}-{num(hi, 1)}"


KM_ANCHORS = json.loads((DATA / "km_anchors.json").read_text(encoding="utf-8"))
KM_TOLERANCE = 0.3


def km_at(line, lat, lon):
    """Point km from the line's anchors (milestones, stations); None if too far from them."""
    anc = KM_ANCHORS["lines"].get(str(line), [])
    kx = 111320 * math.cos(math.radians(lat))
    xy = lambda la, lo: ((lo - lon) * kx, (la - lat) * 111320)
    best = None
    for i in range(1, len(anc)):
        a, b = anc[i - 1], anc[i]
        if a[0] == b[0]:
            continue
        (ax, ay), (bx, by) = xy(a[1], a[2]), xy(b[1], b[2])
        l2 = (bx - ax) ** 2 + (by - ay) ** 2
        if l2 == 0:
            continue
        t = (-ax * (bx - ax) - ay * (by - ay)) / l2
        tc = min(max(t, 0.0), 1.0)
        d = math.hypot(ax + tc * (bx - ax), ay + tc * (by - ay))
        if best is None or d < best[0]:
            if (t < 0 and i > 1) or (t > 1 and i < len(anc) - 1):
                t = tc
            best = (d, a[0] + t * (b[0] - a[0]))
    return best[1] if best and best[0] <= KM_ANCHORS["max_gap_m"] else None


def line_km(lat, lon, lines, rails_gj):
    """(line, km, km) from anchors when they agree with the nearest PLK segment, else (line, km_from, km_to)."""
    kx = 111320 * math.cos(math.radians(lat))
    best = None
    for f in rails_gj["features"]:
        p = f["properties"]
        if p.get("line_no") not in lines or p.get("km_from") is None or p.get("km_to") is None:
            continue
        for x, y in f["geometry"]["coordinates"]:
            d = math.hypot((x - lon) * kx, (y - lat) * 111320)
            if best is None or d < best[0]:
                best = (d, p["line_no"], p["km_from"], p["km_to"])
    if not best or best[0] > 60:
        return None
    _, line, k0, k1 = best
    k = km_at(line, lat, lon)
    if k is not None and min(k0, k1) - KM_TOLERANCE <= k <= max(k0, k1) + KM_TOLERANCE:
        return line, k, k
    return line, k0, k1


def rail_records(gj):
    out, km = [], 0.0
    for f in gj["features"]:
        p, g = f["properties"], f["geometry"]
        if not g or g["type"] != "LineString":
            continue
        km += (p.get("length_m") or 0) / 1000
        out.append({"c": [[round(y, 5), round(x, 5)] for x, y in g["coordinates"]],
                    "l": p.get("line_no"), "n": title_case(p.get("line_name")), "v": p.get("vmax_kmh"),
                    "t": p.get("trains_per_day_corridor"), "tr": p.get("tracks"), "tk": p.get("track"),
                    "k": None if p.get("km_from") is None or p.get("km_to") is None
                    else [round(min(p["km_from"], p["km_to"]), 3), round(max(p["km_from"], p["km_to"]), 3)]})
    return out, km


XING_PL = {"level_crossing": "Przejazd kolejowo-drogowy", "crossing": "Przejście dla pieszych przez tory"}
XING_SNAP_M = 30
XING_HALF_M = 20


def crossing_records(rails_gj):
    """Legal crossings (OSM railway=level_crossing / crossing) as short track pieces (+-20 m) on the hazard lines."""
    from pyproj import Transformer
    from shapely.geometry import LineString, Point
    from shapely.ops import substring
    from shapely.strtree import STRtree

    fwd = Transformer.from_crs(4326, 2180, always_xy=True).transform
    back = Transformer.from_crs(2180, 4326, always_xy=True).transform
    lines = []
    for f in rails_gj["features"]:
        g = f["geometry"]
        if g and g["type"] == "LineString":
            lines.append(LineString([fwd(x, y) for x, y in g["coordinates"]]))
    tree = STRtree(lines)
    raw = json.loads((DATA / "raw" / "wro_crossings_hazard.json").read_text(encoding="utf-8"))
    out = []
    for e in raw["elements"]:
        tags = e.get("tags") or {}
        kind = tags.get("railway")
        if kind not in XING_PL or "lat" not in e:
            continue
        pt = Point(fwd(e["lon"], e["lat"]))
        pieces = []
        for i in tree.query(pt.buffer(XING_SNAP_M)):
            ln = lines[i]
            if ln.distance(pt) > XING_SNAP_M:
                continue
            m = ln.project(pt)
            seg = substring(ln, max(0, m - XING_HALF_M), min(ln.length, m + XING_HALF_M))
            if seg.length > 1:
                pieces.append([[round(c, 5) for c in back(x, y)[::-1]] for x, y in seg.coords])
        if pieces:
            out.append({"k": "p" if kind == "level_crossing" else "c", "s": pieces,
                        "lat": round(e["lat"], 5), "lon": round(e["lon"], 5)})
    return out


def accident_records():
    gj = json.loads((DATA / "validation.geojson").read_text(encoding="utf-8"))
    nearest = {}
    events_csv = DATA / "t6_validation_events.csv"
    if events_csv.exists():
        with events_csv.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                nearest[row["event_id"]] = row
    out = []
    for f in gj["features"]:
        p = f["properties"]
        if p.get("kind") != "accident" or not p.get("use_for_validation") or not f.get("geometry"):
            continue
        lon, lat = f["geometry"]["coordinates"]
        near = nearest.get(p["id"])
        near_text = ""
        if near and near.get("nearest_candidate"):
            place = near.get("nearest_place_rank")
            near_text = (f"Najbliższy kandydat: {near['nearest_candidate']}"
                         + (f" (miejsce {place} rankingu)" if place else "") + f", {near['nearest_m']} m.")
        killed = p.get("outcome") == "killed"
        out.append({
            "lat": round(lat, 3), "lon": round(lon, 3), "year": p.get("year") or str(p.get("date") or "")[:4],
            "outcome": OUTCOME_PL.get(p.get("outcome"), "skutek nieznany"), "killed": killed,
            "r": p.get("uncertainty_m") or 0,
            "lines": [str(x) for x in p.get("lines_at_point") or []], "near": near_text,
        })
    return out


def ai_records():
    path = DATA / "candidates_ai.geojson"
    if not path.exists():
        return []
    gj = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for f in gj.get("features", []):
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        t1m = p.get("nearest_t1_candidate_m")
        off = p.get("nearest_official_m")
        out.append({"id": p.get("id"), "lat": lat, "lon": lon, "s": p.get("ai_score"),
                    "real": p.get("verified_label") == "real", "off": None if off is None else round(off),
                    "label": LABEL_PL.get(p.get("verified_label"), p.get("verified_label")),
                    "line": p.get("rail_line_no"), "date": p.get("ortho_date"),
                    "t1": None if t1m is None else round(t1m), "geoportal": p.get("geoportal_url")})
    return out


def meta(sens, val, n_candidates, n_places, rail_km, accidents):
    acc = val.get("accidents", {})
    top = acc.get("top20_places", {}).get("event_radius", {})
    hits = round(top.get("observed", 0) * acc.get("n_events", 0))
    mc = sens.get("monte_carlo", {})
    base = sens.get("base_params", {})
    years = [a["year"] for a in accidents if a.get("year")]
    return {
        "candidates": n_candidates, "places": n_places, "railKm": round(rail_km),
        "accidents": len(accidents), "yearMin": min(years) if years else None, "yearMax": max(years) if years else None,
        "expRef": num(sens.get("exposure_ref", 0)), "trainsRef": num(sens.get("trains_ref", 0)),
        "detourLo": num(base.get("detour_lo_m", 0)), "detourHi": num(base.get("detour_hi_m", 0)),
        "vmaxRef": num(base.get("vmax_ref_kmh", 0)),
        "hz": [num(base.get(k, 0), 1) for k in ("hz_speed", "hz_trains", "hz_tracks")],
        "yardCap": num(base.get("yard_detour_cap", 0), 1), "yardTracks": base.get("yard_min_tracks"),
        "nVariants": sens.get("n_variants"), "mcN": mc.get("n"),
        "mcPlaces": num(mc.get("top20_places_overlap_median", 0)), "mcP05": num(mc.get("top20_places_overlap_p05", 0)),
        "valN": acc.get("n_events"), "valHits": hits, "valObs": num(100 * top.get("observed", 0)),
        "valRand": num(100 * top.get("random_mean", 0)), "valP": num(top.get("p_value", 0), 2),
        "valNoCand": acc.get("no_candidate_in_radius"),
    }


def build():
    ranking = json.loads((DATA / "ranking.geojson").read_text(encoding="utf-8"))
    sens = json.loads((DATA / "t6_sensitivity.json").read_text(encoding="utf-8"))
    val_path = DATA / "t6_validation.json"
    val = json.loads(val_path.read_text(encoding="utf-8")) if val_path.exists() else {}
    props = [f["properties"] for f in ranking["features"]]
    rails_gj = json.loads((DATA / "rail_hazard.geojson").read_text(encoding="utf-8"))
    sites = sorted((site_record(p, len(props), rails_gj) for p in props), key=lambda s: s["rank"] or 999)
    rails, rail_km = rail_records(rails_gj)
    accidents = accident_records()
    crossings = crossing_records(rails_gj)
    ai = ai_records()
    n_places = sum(1 for s in sites if s["leader"])
    data = {"sites": sites, "rails": rails, "accidents": accidents, "ai": ai, "crossings": crossings,
            "meta": meta(sens, val, len(sites), n_places, rail_km, accidents),
            "kmAnchors": KM_ANCHORS["lines"], "kmCheck": KM_ANCHORS["check"]}

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("/*__FONTS__*/", font_css())
            .replace("/*__ICONS__*/null", (VENDOR / "carbon-icons.json").read_text(encoding="utf-8"))
            .replace("/*__LEAFLET_CSS__*/", fetch(LEAFLET["leaflet.css"], "leaflet.css").read_text(encoding="utf-8"))
            .replace("/*__LEAFLET_JS__*/", re.sub(r"\n?//# sourceMappingURL=\S+", "", fetch(LEAFLET["leaflet.js"], "leaflet.js").read_text(encoding="utf-8")))
            .replace("/*__DATA__*/null", payload))
    bad = [hex(c) for c in (0x2013, 0x2014) if chr(c) in html]
    if bad:
        raise SystemExit(f"en/em dash found in output: {bad!r}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "Dzika_Sciezka_demo.html"
    out.write_text(html, encoding="utf-8")
    size = out.stat().st_size
    if size > MAX_BYTES:
        raise SystemExit(f"{out} is {size / 1e6:.1f} MB, over the 15 MB limit")
    print(f"{out}: {size / 1e6:.2f} MB | sites {len(sites)} (top-20 {sum(1 for s in sites if s['top'])}, "
          f"crops {sum(1 for s in sites if s['img'])}) | rail segments {len(rails)} | accidents {len(accidents)} "
          f"| AI candidates {len(ai)} | legal crossings {len(crossings)}")


if __name__ == "__main__":
    build()
