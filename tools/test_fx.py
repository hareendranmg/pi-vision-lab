"""Render every Face Magic effect on still photos into a contact sheet."""
import sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.face_fx import EFFECTS, FaceFx
from app.vision.faces import FaceTracker

ft, fx = FaceTracker(ROOT / "models/face_landmarker"), FaceFx(ROOT / "assets")
rows = []
for path in sys.argv[2:]:
    bgr = cv2.imread(path)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    ft.roi = None
    face = None
    for _ in range(12):
        face = ft.process(rgb) or face
    tiles = []
    for eff in EFFECTS[:-1]:
        img = bgr.copy()
        fx.draw(img, face.points, eff)
        x0, y0 = face.points.min(0); x1, y1 = face.points.max(0)
        s = (x1 - x0)
        crop = img[max(0, int(y0 - s * 0.9)):int(y1 + s * 0.3), max(0, int(x0 - s * 0.45)):int(x1 + s * 0.45)]
        crop = cv2.resize(crop, (300, int(300 * crop.shape[0] / crop.shape[1])))[:380]
        tile = np.zeros((390, 300, 3), np.uint8); tile[:crop.shape[0]] = crop
        cv2.putText(tile, eff, (6, 384), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        tiles.append(tile)
    rows.append(np.hstack(tiles))
cv2.imwrite(sys.argv[1], np.vstack(rows))
