import json
import sys
import time

import numpy as np
import torch
from transformers import AutoModel

from common import OUT_DIR, tile_path
from crops import load_crop

MODEL = "facebook/dinov2-small"
INPUT_PX = 448
PATCH = 14
CENTER_FRAC = 0.375
BATCH = 16
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def to_tensor(img):
    arr = (np.asarray(img, dtype=np.float32) / 255 - MEAN) / STD
    return torch.from_numpy(arr.transpose(2, 0, 1))


def flips(t):
    return [t, t.flip(-1), t.flip(-2), t.flip(-1).flip(-2)]


def features(model, batch, device):
    with torch.no_grad():
        out = model(pixel_values=batch.to(device)).last_hidden_state.float().cpu()
    n = INPUT_PX // PATCH
    cls = out[:, 0]
    patches = out[:, 1:].reshape(len(batch), n, n, -1)
    lo, hi = round(n * (0.5 - CENTER_FRAC / 2)), round(n * (0.5 + CENTER_FRAC / 2))
    centre = patches[:, lo:hi, lo:hi].mean(dim=(1, 2))
    return torch.cat([cls, patches.mean(dim=(1, 2)), centre], dim=1)


def embed(items, out_path):
    cache = dict(np.load(out_path)) if out_path.exists() else {}
    todo = [it for it in items if it["tile_id"] not in cache and tile_path(it["tile_id"]).exists()]
    print(f"cached {len(cache)}, to embed {len(todo)}")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = AutoModel.from_pretrained(MODEL).to(device)
    model.train(False)
    t0 = time.time()
    for start in range(0, len(todo), BATCH):
        chunk = todo[start:start + BATCH]
        tensors = [to_tensor(load_crop(it, INPUT_PX)) for it in chunk]
        stacked = torch.stack([f for t in tensors for f in flips(t)])
        feats = features(model, stacked, device).reshape(len(chunk), 4, -1).mean(dim=1).numpy()
        for it, f in zip(chunk, feats):
            cache[it["tile_id"]] = f
        if (start // BATCH) % 25 == 0:
            print(f"{start + len(chunk)}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
    np.savez(out_path, **cache)
    print(f"done in {time.time() - t0:.0f}s on {device}")


if __name__ == "__main__":
    items = []
    for name in sys.argv[1:]:
        items += json.loads((OUT_DIR / name).read_text())
    embed(items, OUT_DIR / "embeddings_dinov2s.npz")
