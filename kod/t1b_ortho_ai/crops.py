from PIL import Image

from common import FETCH_HALF_M, FETCH_PX, TILE_PX, tile_path

CROP_HALF_M = 50


def load_crop(item, size=TILE_PX):
    img = Image.open(tile_path(item["tile_id"])).convert("RGB")
    img = img.rotate(-item["bearing"], resample=Image.BICUBIC, center=(FETCH_PX / 2, FETCH_PX / 2))
    half_px = FETCH_PX / 2 * CROP_HALF_M / FETCH_HALF_M
    c = FETCH_PX / 2
    img = img.crop((round(c - half_px), round(c - half_px), round(c + half_px), round(c + half_px)))
    return img.resize((size, size), Image.BICUBIC) if img.size[0] != size else img
