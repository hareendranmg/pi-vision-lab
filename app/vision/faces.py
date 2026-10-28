"""Single-face tracker: BlazeFace detection + 478-point face mesh, plus
geometric expression scores derived from the mesh."""
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .common import (as_probability, decode_ssd, letterbox, load_model, outputs_by_name,
                     roi_from_box, roi_from_points, rotation_between, ssd_anchors)

DET_SIZE = 128
LM_SIZE = 256

# Mesh indices used for expressions and AR anchors (subject's right = image left).
R_EYE_OUT, R_EYE_IN, L_EYE_IN, L_EYE_OUT = 33, 133, 362, 263
R_EYE_TOP, R_EYE_BOT, L_EYE_TOP, L_EYE_BOT = 159, 145, 386, 374
R_BROW, L_BROW = 105, 334
LIP_TOP, LIP_BOT, MOUTH_R, MOUTH_L = 13, 14, 61, 291
NOSE_TIP, FOREHEAD, CHIN = 1, 10, 152
# Sparse subset of the mesh drawn as the "AI sees you" dot overlay.
MESH_DOTS = list(range(0, 468, 3))


@dataclass
class Face:
    points: np.ndarray            # (478, 2) frame pixels, un-mirrored
    score: float
    scores: dict = field(default_factory=dict)
    emotion: str = "neutral"


class FaceTracker:
    def __init__(self, model_dir: Path, threads=4):
        self.det = load_model(model_dir / "face_detector.tflite", threads)
        self.lm = load_model(model_dir / "face_landmarks_detector.tflite", threads)
        self.anchors = ssd_anchors(DET_SIZE, [8, 16, 16, 16])
        self._det_in = self.det.get_input_details()[0]["index"]
        dout = outputs_by_name(self.det)
        self._det_boxes, self._det_scores = dout["regressors"], dout["classificators"]
        self._lm_in = self.lm.get_input_details()[0]["index"]
        names = outputs_by_name(self.lm)
        self._lm_pts, self._lm_presence = names["Identity"], names["Identity_1"]
        self.roi = None
        self._scan = 0
        self._smile_base = None

    def process(self, rgb):
        if self.roi is None:
            self.roi = self._detect(rgb)
            if self.roi is None:
                return None
        crop = self.roi.crop(rgb, LM_SIZE)
        self.lm.set_tensor(self._lm_in, (crop.astype(np.float32) / 255.0)[None])
        self.lm.invoke()
        presence = as_probability(self.lm.get_tensor(self._lm_presence))
        if presence < 0.5:
            self.roi = None
            return None
        raw = self.lm.get_tensor(self._lm_pts).reshape(478, 3)
        pts = self.roi.to_frame(raw, LM_SIZE)
        angle = rotation_between(pts[R_EYE_OUT], pts[L_EYE_OUT], 0.0)
        self.roi = roi_from_points(pts, angle, scale=1.5)
        face = Face(pts, presence)
        face.scores, face.emotion = self._expressions(pts)
        return face

    @staticmethod
    def _regions(h, w):
        """Full frame plus a 3x2 grid of overlapping square tiles.

        The short-range detector sees the frame at 128x128, so a face across
        the room is only ~12 px wide; the tiles zoom in ~2.5x.
        """
        side = int(h * 0.6)
        xs = np.linspace(0, w - side, 3).astype(int)
        ys = np.linspace(0, h - side, 2).astype(int)
        return [(0, 0, w, h)] + [(x, y, side, side) for y in ys for x in xs]

    def _detect(self, rgb):
        # One region per frame while searching: ~5 ms instead of ~35 ms for all seven.
        regions = self._regions(*rgb.shape[:2])
        x0, y0, w, h = regions[self._scan % len(regions)]
        self._scan += 1
        sq, lb = letterbox(rgb[y0:y0 + h, x0:x0 + w], DET_SIZE)
        self.det.set_tensor(self._det_in, (sq.astype(np.float32) / 127.5 - 1.0)[None])
        self.det.invoke()
        dets = decode_ssd(self.det.get_tensor(self._det_boxes)[0], self.det.get_tensor(self._det_scores)[0],
                          self.anchors, DET_SIZE, 6, 0.5, lb, max_out=1)
        if not dets:
            return None
        d = dets[0]
        d.box[:2] += (x0, y0)
        d.keypoints += (x0, y0)
        angle = rotation_between(d.keypoints[0], d.keypoints[1], 0.0)
        return roi_from_box(d.box[0], d.box[1], d.box[2], d.box[3], angle, scale=1.5)

    def _expressions(self, p):
        # Work in a face-aligned frame so head roll doesn't affect the scores.
        eye_vec = p[L_EYE_OUT] - p[R_EYE_OUT]
        iod = float(np.linalg.norm(eye_vec)) + 1e-6
        roll = math.atan2(eye_vec[1], eye_vec[0])
        c, s = math.cos(-roll), math.sin(-roll)
        q = (p - p[NOSE_TIP]) @ np.array([[c, s], [-s, c]]) / iod

        mouth_open = float(np.linalg.norm(q[LIP_BOT] - q[LIP_TOP]))
        mouth_w = float(np.linalg.norm(q[MOUTH_L] - q[MOUTH_R]))
        lip_mid_y = (q[LIP_TOP][1] + q[LIP_BOT][1]) / 2
        corner_lift = float(lip_mid_y - (q[MOUTH_L][1] + q[MOUTH_R][1]) / 2)
        smile_raw = corner_lift * 2.0 + mouth_w
        # Neutral faces measure ~0.49, broad smiles ~0.72. Start from a neutral
        # prior and adapt to this person's resting mouth: quickly downwards,
        # very slowly upwards so a constant smile doesn't become "neutral".
        if self._smile_base is None:
            self._smile_base = 0.50
        rate = 0.05 if smile_raw < self._smile_base else 0.002
        self._smile_base = max(0.42, self._smile_base + rate * (smile_raw - self._smile_base))

        def ear(top, bot, a, b):
            return float(np.linalg.norm(q[top] - q[bot]) / (np.linalg.norm(q[a] - q[b]) + 1e-6))

        r_ear = ear(R_EYE_TOP, R_EYE_BOT, R_EYE_OUT, R_EYE_IN)
        l_ear = ear(L_EYE_TOP, L_EYE_BOT, L_EYE_OUT, L_EYE_IN)
        brow = float(((q[R_EYE_TOP][1] - q[R_BROW][1]) + (q[L_EYE_TOP][1] - q[L_BROW][1])) / 2)

        clamp = lambda v: max(0.0, min(1.0, v))
        scores = {
            "happy": clamp((smile_raw - self._smile_base - 0.06) / 0.12),
            "surprised": clamp((brow - 0.42) / 0.15) * 0.5 + clamp((mouth_open - 0.12) / 0.25) * 0.5,
            "mouthOpen": clamp((mouth_open - 0.06) / 0.3),
            "eyesClosed": clamp((0.22 - (r_ear + l_ear) / 2) / 0.1),
            "wink": clamp((abs(r_ear - l_ear) - 0.08) / 0.1) if min(r_ear, l_ear) < 0.18 else 0.0,
        }
        if scores["wink"] > 0.6:
            emotion = "winking"
        elif scores["surprised"] > 0.6:
            emotion = "surprised"
        elif scores["happy"] > 0.55:
            emotion = "happy"
        elif scores["eyesClosed"] > 0.7:
            emotion = "sleepy"
        elif scores["mouthOpen"] > 0.6:
            emotion = "talking"
        else:
            emotion = "neutral"
        return scores, emotion
