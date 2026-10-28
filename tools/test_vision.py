"""Run the vision pipeline on still images and save annotated copies."""
import sys, time
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.vision.hands import HandTracker, CONNECTIONS
from app.vision.faces import FaceTracker, MESH_DOTS
from app.vision.objects import ObjectDetector

M = Path(__file__).resolve().parents[1] / "models"
hands, faces = HandTracker(M / "hand_landmarker"), FaceTracker(M / "face_landmarker")
objects = ObjectDetector(M / "efficientdet_lite0_pp.tflite")
for path in sys.argv[1:]:
    bgr = cv2.imread(path); rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    hands.roi = faces.roi = None
    for it in range(3):  # 1st pass detects, later passes exercise landmark tracking
        t = time.perf_counter(); h = hands.process(rgb); th = (time.perf_counter() - t) * 1000
        t = time.perf_counter(); f = faces.process(rgb); tf = (time.perf_counter() - t) * 1000
    t = time.perf_counter(); o = objects.process(rgb); to = (time.perf_counter() - t) * 1000
    print(f"{path}: hand={h is not None} {'%.2f' % h.score if h else ''} ({th:.0f}ms) "
          f"face={f is not None} {f.emotion if f else ''} ({tf:.0f}ms) objects={[x['label'] for x in o]} ({to:.0f}ms)")
    if h is not None:
        for a, b in CONNECTIONS:
            cv2.line(bgr, tuple(map(int, h.points[a])), tuple(map(int, h.points[b])), (0, 255, 0), 3)
    if f is not None:
        for i in MESH_DOTS:
            cv2.circle(bgr, tuple(map(int, f.points[i])), 2, (255, 200, 0), -1)
    H, W = bgr.shape[:2]
    for x in o:
        cv2.rectangle(bgr, (int(x["x0"] * W), int(x["y0"] * H)), (int(x["x1"] * W), int(x["y1"] * H)), (0, 0, 255), 2)
    cv2.imwrite(str(Path(path).with_suffix(".out.jpg")), bgr)
