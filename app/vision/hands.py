"""Single-hand tracker: BlazePalm detection + 21-point hand landmarks.

Palm detection (~45 ms on a Pi 4) only runs while no hand is tracked; once a
hand is found, the next ROI is derived from the previous landmarks, so steady
tracking costs one landmark pass (~37 ms) per frame.
"""
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .common import (as_probability, decode_ssd, letterbox, load_model, outputs_by_name,
                     roi_from_box, roi_from_points, rotation_between, ssd_anchors)

DET_SIZE = 192
LM_SIZE = 224
PALM_IDX = [0, 1, 2, 3, 5, 6, 9, 10, 13, 14, 17, 18]

# Bone list for drawing the skeleton.
CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
               (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
               (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


@dataclass
class Hand:
    points: np.ndarray  # (21, 2) frame pixels, un-mirrored
    score: float
    right: float        # probability this is a right hand


class HandTracker:
    def __init__(self, model_dir: Path, threads=4):
        self.det = load_model(model_dir / "hand_detector.tflite", threads)
        self.lm = load_model(model_dir / "hand_landmarks_detector.tflite", threads)
        self.anchors = ssd_anchors(DET_SIZE, [8, 16, 16, 16])
        self._det_in = self.det.get_input_details()[0]["index"]
        dout = self.det.get_output_details()
        self._det_boxes = next(d["index"] for d in dout if d["shape"][-1] == 18)
        self._det_scores = next(d["index"] for d in dout if d["shape"][-1] == 1)
        self._lm_in = self.lm.get_input_details()[0]["index"]
        names = outputs_by_name(self.lm)
        self._lm_pts, self._lm_presence, self._lm_hand = names["Identity"], names["Identity_1"], names["Identity_2"]
        self.roi = None

    def process(self, rgb):
        if self.roi is None:
            self.roi = self._detect(rgb)
            if self.roi is None:
                return None
        hand = self._landmarks(rgb)
        if hand is None or hand.score < 0.5:
            self.roi = None
            return None
        angle = rotation_between(hand.points[0], hand.points[9], math.pi / 2)
        self.roi = roi_from_points(hand.points[PALM_IDX], angle, scale=2.0, shift_y=-0.1)
        return hand

    def _detect(self, rgb):
        sq, lb = letterbox(rgb, DET_SIZE)
        self.det.set_tensor(self._det_in, (sq.astype(np.float32) / 255.0)[None])
        self.det.invoke()
        dets = decode_ssd(self.det.get_tensor(self._det_boxes)[0], self.det.get_tensor(self._det_scores)[0],
                          self.anchors, DET_SIZE, 7, 0.5, lb, max_out=1)
        if not dets:
            return None
        d = dets[0]
        angle = rotation_between(d.keypoints[0], d.keypoints[2], math.pi / 2)
        return roi_from_box(d.box[0], d.box[1], d.box[2], d.box[3], angle, scale=2.6, shift_y=-0.5)

    def _landmarks(self, rgb):
        crop = self.roi.crop(rgb, LM_SIZE)
        self.lm.set_tensor(self._lm_in, (crop.astype(np.float32) / 255.0)[None])
        self.lm.invoke()
        raw = self.lm.get_tensor(self._lm_pts).reshape(21, 3)
        presence = as_probability(self.lm.get_tensor(self._lm_presence))
        right = as_probability(self.lm.get_tensor(self._lm_hand))
        return Hand(self.roi.to_frame(raw, LM_SIZE), presence, right)
