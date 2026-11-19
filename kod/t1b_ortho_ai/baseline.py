import numpy as np
from scipy.ndimage import median_filter, uniform_filter1d

from crops import load_crop

BAND = 0.30
CENTRE_HALF = 0.15


def column_highpass(gray):
    profile = gray.mean(axis=0)
    return profile - median_filter(profile, size=41, mode="reflect")


def line_score(item):
    gray = np.asarray(load_crop(item).convert("L"), dtype=np.float32)
    h, w = gray.shape
    above = uniform_filter1d(column_highpass(gray[: int(h * BAND)]), 5)
    below = uniform_filter1d(column_highpass(gray[int(h * (1 - BAND)):]), 5)
    lo, hi = int(w * (0.5 - CENTRE_HALF)), int(w * (0.5 + CENTRE_HALF))
    both = np.minimum(above[lo:hi], below[lo:hi])
    return float(both.max())
