"""Names the colour at a point of the camera frame."""
import cv2
import numpy as np

NAMED = {
    "Red": "#e53935", "Crimson": "#a3122a", "Pink": "#ff80ab", "Hot Pink": "#ff3d9a",
    "Orange": "#fb8c00", "Coral": "#ff7f50", "Peach": "#ffcc99", "Gold": "#f4c430",
    "Yellow": "#fdd835", "Lime": "#b2ff59", "Green": "#43a047", "Forest Green": "#1b5e20",
    "Olive": "#808000", "Mint": "#98ff98", "Teal": "#00897b", "Turquoise": "#40e0d0",
    "Cyan": "#00bcd4", "Sky Blue": "#87ceeb", "Blue": "#1e88e5", "Navy": "#1a237e",
    "Indigo": "#3f51b5", "Purple": "#8e24aa", "Violet": "#b388ff", "Lavender": "#d1c4e9",
    "Magenta": "#d500f9", "Brown": "#795548", "Tan": "#d2b48c", "Beige": "#f5f5dc",
    "White": "#fafafa", "Silver": "#c0c0c0", "Grey": "#808080", "Charcoal": "#36454f", "Black": "#111111",
}


def _lab(rgb_list):
    arr = np.array(rgb_list, dtype=np.uint8).reshape(-1, 1, 3)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(float)


_NAMES = list(NAMED)
_LABS = _lab([tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in NAMED.values()])


def sample_at(bgr, cx, cy):
    """Median colour of a small patch around (cx, cy) pixels, with its nearest name (CIELAB distance)."""
    h, w = bgr.shape[:2]
    r = max(6, min(h, w) // 30)
    cx, cy = int(np.clip(cx, r, w - r)), int(np.clip(cy, r, h - r))
    patch = bgr[cy - r:cy + r, cx - r:cx + r].reshape(-1, 3)
    b, g, rr = (int(v) for v in np.median(patch, axis=0))
    lab = _lab([(rr, g, b)])[0]
    name = _NAMES[int(np.argmin(np.linalg.norm(_LABS - lab, axis=1)))]
    return {"r": rr, "g": g, "b": b, "hex": "#%02x%02x%02x" % (rr, g, b), "name": name}
