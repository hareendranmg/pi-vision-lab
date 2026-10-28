"""Save 478-point face-mesh landmarks of an image as .npy (for presenter_src/make_textures.py).

    python3 tools/face_landmarks.py photo.jpg out.npy

Works on photos and on the unwrapped Rocketbox head texture (a TGA is fine).
Needs the models from scripts/download_models.sh and ai-edge-litert.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.vision.faces import FaceTracker  # noqa: E402


def main(src, dst):
    img = cv2.cvtColor(np.array(Image.open(src).convert("RGB")), cv2.COLOR_RGB2BGR)
    scale = min(1.0, 1400 / max(img.shape[:2]))
    small = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    ft, face = FaceTracker(ROOT / "models" / "face_landmarker"), None
    for _ in range(40):  # detection, then let landmark tracking settle
        face = ft.process(rgb) or face
    if face is None:
        sys.exit(f"no face found in {src}")
    np.save(dst, face.points / scale)
    print(f"{src}: {len(face.points)} landmarks -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
