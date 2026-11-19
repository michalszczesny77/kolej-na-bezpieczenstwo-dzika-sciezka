import json
import sys

from PIL import Image, ImageDraw

from common import OUT_DIR
from crops import load_crop

CELL = 300
COLS = 4


def sheet(items, out_path, captions=None):
    rows = (len(items) + COLS - 1) // COLS
    canvas = Image.new("RGB", (COLS * CELL, rows * (CELL + 18)), "white")
    draw = ImageDraw.Draw(canvas)
    for i, it in enumerate(items):
        x, y = (i % COLS) * CELL, (i // COLS) * (CELL + 18)
        canvas.paste(load_crop(it, CELL), (x, y + 18))
        draw.text((x + 4, y + 3), captions[i] if captions else it["tile_id"], fill="black")
    canvas.save(out_path, quality=88)


if __name__ == "__main__":
    index_file, start, count, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    items = json.loads((OUT_DIR / index_file).read_text())[start:start + count]
    sheet(items, out, [f"{start + i} {it['tile_id']}" for i, it in enumerate(items)])
