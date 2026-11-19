import json
import math
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

from common import DATA_DIR, LINK_SCRIPT, OUT_DIR
from contact_sheet import sheet
from crops import load_crop

ROUNDS = (1, 2)
FIG_CELL = 360
FIG_COLS = 4
MERGE_M = 100
FIGURE = [
    ("scan_02890", "potwierdzone"), ("scan_01596", "potwierdzone"),
    ("scan_02495", "niepewne"), ("scan_04010", "niepewne"),
    ("scan_02242", "niepewne"), ("scan_02096", "fałszywy alarm: przepust"),
    ("scan_00624", "fałszywy alarm: stacja rozrządowa"), ("scan_03515", "fałszywy alarm: rurociąg nad torem"),
]


def load_json(name):
    return json.loads((OUT_DIR / name).read_text())


def geoportal_link(lat, lon):
    out = subprocess.run(["python3", str(LINK_SCRIPT), f"{lat:.7f}", f"{lon:.7f}"], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def review_sheets(round_no, out_dir):
    top = load_json(f"top_new_round{round_no}.json")
    for start in range(0, len(top), 16):
        chunk = top[start:start + 16]
        sheet(chunk, f"{out_dir}/round{round_no}_top_{start:02d}.jpg",
              [f"{start + i} {it['tile_id']} s={it['ai_score']:.2f}" for i, it in enumerate(chunk)])


def font(size):
    for name in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def figure(examples, out_path):
    rows = (len(examples) + FIG_COLS - 1) // FIG_COLS
    pad, cap = 8, 30
    canvas = Image.new("RGB", (FIG_COLS * (FIG_CELL + pad) + pad, rows * (FIG_CELL + cap + pad) + pad + 26), "white")
    draw = ImageDraw.Draw(canvas)
    f = font(16)
    for i, (it, label) in enumerate(examples):
        x = pad + (i % FIG_COLS) * (FIG_CELL + pad)
        y = pad + (i // FIG_COLS) * (FIG_CELL + cap + pad)
        img = load_crop(it, FIG_CELL)
        d = ImageDraw.Draw(img)
        c, r = FIG_CELL // 2, 22
        d.ellipse([c - r, c - r, c + r, c + r], outline=(255, 40, 40), width=3)
        canvas.paste(img, (x, y + cap))
        draw.text((x + 2, y + 6), f"{label} (wynik {it['ai_score']:.2f})", fill="black", font=f)
    draw.text((pad, canvas.height - 24), "Kadry 100 x 100 m, tor obrócony poziomo. Ortofotomapa: GUGiK, geoportal.gov.pl.",
              fill="black", font=font(14))
    canvas.save(out_path, quality=90)


def output():
    features, by_id, kept_xy = [], {}, []
    for round_no in ROUNDS:
        top = load_json(f"top_new_round{round_no}.json")
        review = load_json(f"labels_top40_round{round_no}.json")
        for rank, it in enumerate(top, 1):
            by_id[it["tile_id"]] = it
            lab = review["labels"][it["tile_id"]]
            if lab not in ("real", "unsure"):
                continue
            if any(math.dist((it["x"], it["y"]), q) <= MERGE_M for q in kept_xy):
                continue
            kept_xy.append((it["x"], it["y"]))
            props = {"id": None, "lat": round(it["lat"], 7), "lon": round(it["lon"], 7), "sources": ["ortho_ai"],
                     "ai_score": it["ai_score"], "ai_round": round_no, "ai_rank": rank, "verified_label": lab,
                     "verified_note": review["notes"].get(it["tile_id"], ""), "tile_id": it["tile_id"],
                     "rail_line_no": it.get("line_no"), "pop_500m": round(it["pop500"], 1),
                     "nearest_official_m": it["dist_official_m"], "nearest_t1_candidate_m": it["dist_t1_m"],
                     "ortho_date": it.get("ortho_date"), "geoportal_url": geoportal_link(it["lat"], it["lon"])}
            features.append(props)
    features.sort(key=lambda p: (p["verified_label"] != "real", -p["ai_score"]))
    for n, p in enumerate(features, 1):
        p["id"] = f"AI-{n:03d}"
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]}, "properties": p}
        for p in features]}
    (DATA_DIR / "candidates_ai.geojson").write_text(json.dumps(fc, ensure_ascii=False, indent=0))
    figure([(by_id[tid], label) for tid, label in FIGURE], DATA_DIR / "t1b_examples.jpg")
    print(f"wrote {len(features)} features ({sum(p['verified_label'] == 'real' for p in features)} real)")


if __name__ == "__main__":
    if sys.argv[1] == "sheets":
        review_sheets(int(sys.argv[2]), sys.argv[3])
    else:
        output()
