"""COCO object detection with EfficientDet-Lite0 (post-processed TFLite export)."""
import zipfile
from pathlib import Path

import cv2
import numpy as np

from .common import load_model


class ObjectDetector:
    def __init__(self, model_path: Path, threshold=0.45, threads=4):
        self.it = load_model(model_path, threads)
        self.threshold = threshold
        # The label map ships inside the .tflite as a zip-appended metadata file.
        with zipfile.ZipFile(model_path) as z:
            self.labels = z.read("labelmap.txt").decode().splitlines()
        inp = self.it.get_input_details()[0]
        self._in, self._size = inp["index"], int(inp["shape"][1])
        outs = self.it.get_output_details()
        self._boxes = next(d["index"] for d in outs if len(d["shape"]) == 3)
        self._count = next(d["index"] for d in outs if len(d["shape"]) == 1)
        self._pair = [d["index"] for d in outs if len(d["shape"]) == 2]
        self._classes_idx = None

    def process(self, rgb):
        """Return [{label, score, x0, y0, x1, y1}] with coordinates normalised to rgb."""
        self.it.set_tensor(self._in, cv2.resize(rgb, (self._size, self._size))[None])
        self.it.invoke()
        a, b = (self.it.get_tensor(i)[0] for i in self._pair)
        if self._classes_idx is None:
            # Class ids are whole numbers, scores are not; decide once we can tell.
            if np.any(a != np.round(a)):
                self._classes_idx = 1
            elif np.any(b != np.round(b)):
                self._classes_idx = 0
        classes, scores = (b, a) if self._classes_idx == 1 else (a, b)
        boxes = self.it.get_tensor(self._boxes)[0]
        n = int(self.it.get_tensor(self._count)[0])
        out = []
        for i in range(min(n, len(scores))):
            if scores[i] < self.threshold:
                continue
            cid = int(classes[i])
            label = self.labels[cid] if 0 <= cid < len(self.labels) else str(cid)
            if label == "???":
                continue
            y0, x0, y1, x1 = np.clip(boxes[i], 0.0, 1.0)
            out.append({"label": label, "score": float(scores[i]),
                        "x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1)})
        return out
