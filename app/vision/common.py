"""Shared helpers for running MediaPipe-style models on LiteRT.

MediaPipe's own Python wheels require the ARMv8 AES extension, which the Pi 4
(BCM2711) lacks, so the detection -> ROI -> landmark pipeline is rebuilt here
on top of the same .tflite models.
"""
import math
from dataclasses import dataclass

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter


def load_model(path, threads=4):
    interp = Interpreter(model_path=str(path), num_threads=threads)
    interp.allocate_tensors()
    return interp


def outputs_by_name(interp):
    return {d["name"]: d["index"] for d in interp.get_output_details()}


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -80, 80)))


def as_probability(v):
    """Some landmark heads emit logits, others probabilities."""
    v = float(np.ravel(v)[0])
    return v if 0.0 <= v <= 1.0 else float(sigmoid(v))


def ssd_anchors(input_size, strides, offset=0.5):
    """MediaPipe SsdAnchorsCalculator (fixed anchor size, aspect ratio 1.0).

    Consecutive layers sharing a stride are merged into one feature map with
    two anchors per layer per cell.
    """
    centers = []
    i = 0
    while i < len(strides):
        j, per_cell = i, 0
        while j < len(strides) and strides[j] == strides[i]:
            per_cell += 2
            j += 1
        fm = math.ceil(input_size / strides[i])
        for y in range(fm):
            for x in range(fm):
                centers.extend([((x + offset) / fm, (y + offset) / fm)] * per_cell)
        i = j
    return np.array(centers, dtype=np.float32)


def letterbox(img, size):
    """Fit img into a size x size square with zero borders.

    Returns the square image and (scale, pad_x, pad_y) to map points back.
    """
    h, w = img.shape[:2]
    s = size / max(h, w)
    nw, nh = round(w * s), round(h * s)
    out = np.zeros((size, size, 3), img.dtype)
    px, py = (size - nw) // 2, (size - nh) // 2
    out[py:py + nh, px:px + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    return out, (s, px, py)


@dataclass
class Detection:
    score: float
    box: np.ndarray        # cx, cy, w, h in frame pixels
    keypoints: np.ndarray  # (K, 2) in frame pixels


def decode_ssd(raw_boxes, raw_scores, anchors, input_size, num_kp, threshold, lb, max_out=2):
    """Decode SSD regressors into frame-space detections with weighted NMS."""
    scores = sigmoid(raw_scores.reshape(-1))
    idx = np.where(scores > threshold)[0]
    if idx.size == 0:
        return []
    r = raw_boxes.reshape(-1, raw_boxes.shape[-1])[idx] / input_size
    a = anchors[idx]
    boxes = np.stack([r[:, 0] + a[:, 0], r[:, 1] + a[:, 1], r[:, 2], r[:, 3]], axis=1)
    kps = r[:, 4:4 + 2 * num_kp].reshape(-1, num_kp, 2) + a[:, None, :]
    sc = scores[idx]

    # Weighted NMS (MediaPipe default for BlazeFace / BlazePalm).
    order = np.argsort(-sc)
    dets = []
    while order.size and len(dets) < max_out:
        best = order[0]
        ious = _iou(boxes[best], boxes[order])
        group = order[ious > 0.3]
        w = sc[group][:, None]
        box = (boxes[group] * w).sum(0) / w.sum()
        kp = (kps[group] * w[:, :, None]).sum(0) / w.sum()
        dets.append((float(sc[best]), box, kp))
        order = order[ious <= 0.3]

    s, px, py = lb
    out = []
    for score, box, kp in dets:
        fb = np.array([(box[0] * input_size - px) / s, (box[1] * input_size - py) / s,
                       box[2] * input_size / s, box[3] * input_size / s])
        fk = np.stack([(kp[:, 0] * input_size - px) / s, (kp[:, 1] * input_size - py) / s], axis=1)
        out.append(Detection(score, fb, fk))
    return out


def _iou(b, bs):
    x0 = np.maximum(b[0] - b[2] / 2, bs[:, 0] - bs[:, 2] / 2)
    y0 = np.maximum(b[1] - b[3] / 2, bs[:, 1] - bs[:, 3] / 2)
    x1 = np.minimum(b[0] + b[2] / 2, bs[:, 0] + bs[:, 2] / 2)
    y1 = np.minimum(b[1] + b[3] / 2, bs[:, 1] + bs[:, 3] / 2)
    inter = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
    return inter / (b[2] * b[3] + bs[:, 2] * bs[:, 3] - inter + 1e-9)


def rotation_between(p0, p1, target):
    """MediaPipe ROI rotation: angle that turns p0->p1 into `target` radians."""
    r = target - math.atan2(-(p1[1] - p0[1]), p1[0] - p0[0])
    return (r + math.pi) % (2 * math.pi) - math.pi


@dataclass
class Roi:
    """Rotated square region in frame pixels."""
    cx: float
    cy: float
    size: float
    angle: float

    def axes(self):
        c, s = math.cos(self.angle), math.sin(self.angle)
        return np.array([c, s]), np.array([-s, c])

    def crop(self, img, out_size):
        ux, uy = self.axes()
        c = np.array([self.cx, self.cy])
        tl = c - self.size / 2 * ux - self.size / 2 * uy
        src = np.float32([tl, tl + self.size * ux, tl + self.size * uy])
        dst = np.float32([[0, 0], [out_size, 0], [0, out_size]])
        m = cv2.getAffineTransform(src, dst)
        return cv2.warpAffine(img, m, (out_size, out_size), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT)

    def to_frame(self, pts, out_size):
        """Map (N, 2+) crop-pixel points back to frame pixels."""
        ux, uy = self.axes()
        c = np.array([self.cx, self.cy])
        tl = c - self.size / 2 * ux - self.size / 2 * uy
        f = self.size / out_size
        xy = tl + np.outer(pts[:, 0] * f, ux) + np.outer(pts[:, 1] * f, uy)
        return xy


def roi_from_box(cx, cy, w, h, angle, scale, shift_y=0.0):
    ux, uy = Roi(0, 0, 0, angle).axes()
    c = np.array([cx, cy]) + uy * shift_y * h
    return Roi(float(c[0]), float(c[1]), max(w, h) * scale, angle)


def roi_from_points(pts, angle, scale, shift_y=0.0):
    """Rotated bounding box of pts in the ROI frame, then MediaPipe's rect transform."""
    ux, uy = Roi(0, 0, 0, angle).axes()
    u, v = pts @ ux, pts @ uy
    cu, cv_ = (u.min() + u.max()) / 2, (v.min() + v.max()) / 2
    w, h = u.max() - u.min(), v.max() - v.min()
    c = cu * ux + cv_ * uy
    return roi_from_box(c[0], c[1], w, h, angle, scale, shift_y)
