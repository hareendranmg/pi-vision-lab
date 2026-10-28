"""Photo-real face effects drawn into the camera frame from the 478-point mesh.

Mesh effects (makeup, eye colour, shades) recolour the person's own pixels so
lighting and texture stay real; photo props (mask, crown) are real cut-out
photographs warped to follow the head. All functions draw on an un-mirrored
BGR image with landmark points in that image's pixel coordinates.
"""
import json
import math
from pathlib import Path

import cv2
import numpy as np

from .vision import faces as F

LIPS_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
LIPS_INNER = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
R_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
L_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
R_LID, R_BROW = [33, 246, 161, 160, 159, 158, 157, 173, 133], [55, 65, 52, 53, 46]
L_LID, L_BROW = [362, 398, 384, 385, 386, 387, 388, 466, 263], [276, 283, 282, 295, 285]
R_IRIS, L_IRIS = (468, [469, 470, 471, 472]), (473, [474, 475, 476, 477])
R_CHEEK, L_CHEEK = 50, 280
R_TEMPLE, L_TEMPLE = 234, 454

EFFECTS = ["mesh", "masquerade", "crown", "shades", "glam", "iceeyes", "none"]


class FaceFx:
    def __init__(self, asset_dir: Path):
        meta = json.loads((asset_dir / "assets.json").read_text())
        self.props = {}
        for name in ("masquerade", "crown"):
            m = meta[name]
            img = cv2.imread(str(asset_dir / m["file"]), cv2.IMREAD_UNCHANGED)
            self.props[name] = (img, m)
        self._smooth = None

    def smooth(self, pts):
        """Damp landmark jitter (props otherwise shimmer) while following fast moves."""
        if self._smooth is None or self._smooth.shape != pts.shape:
            self._smooth = pts.copy()
            return pts
        move = np.linalg.norm(pts[1] - self._smooth[1])
        size = np.linalg.norm(pts[F.L_EYE_OUT] - pts[F.R_EYE_OUT]) + 1e-6
        a = float(np.clip(move / size * 4, 0.35, 1.0))
        self._smooth = self._smooth + a * (pts - self._smooth)
        return self._smooth

    def reset(self):
        self._smooth = None

    def draw(self, img, p, effect):
        if effect == "mesh":
            for i in F.MESH_DOTS:
                cv2.circle(img, (int(p[i][0]), int(p[i][1])), 1, (255, 230, 120), -1, cv2.LINE_AA)
        elif effect == "masquerade":
            self._mask(img, p)
        elif effect == "crown":
            self._crown(img, p)
        elif effect == "shades":
            self._shades(img, p)
        elif effect == "glam":
            self._glam(img, p)
        elif effect == "iceeyes":
            self._iris(img, p, (255, 225, 140))  # BGR icy blue

    # ---------------- photo props ----------------
    def _mask(self, img, p):
        asset, m = self.props["masquerade"]
        r_eye = p[[F.R_EYE_OUT, F.R_EYE_IN]].mean(0)  # subject's right eye = image left
        l_eye = p[[F.L_EYE_OUT, F.L_EYE_IN]].mean(0)
        _blend_similarity(img, asset, np.float32(m["left_eye"]), np.float32(m["right_eye"]), r_eye, l_eye)

    def _crown(self, img, p):
        asset, m = self.props["crown"]
        h, w = asset.shape[:2]
        across = p[L_TEMPLE] - p[R_TEMPLE]
        width = np.linalg.norm(across) * 1.05
        ux = across / (np.linalg.norm(across) + 1e-6)
        up = np.array([ux[1], -ux[0]])
        face_h = np.linalg.norm(p[F.FOREHEAD] - p[F.CHIN])
        base = p[F.FOREHEAD] + up * face_h * 0.12  # headband sits just above the forehead
        bc = np.float32(m["bottom_center"])
        _blend_similarity(img, asset, bc - [w / 2, 0], bc + [w / 2, 0],
                          base - ux * width / 2, base + ux * width / 2)

    # ---------------- mesh effects ----------------
    def _shades(self, img, p):
        """Tinted lenses shaped from the eye/brow region, with a metal frame."""
        eye_d = np.linalg.norm(p[F.L_EYE_OUT] - p[F.R_EYE_OUT])
        ux = (p[F.L_EYE_OUT] - p[F.R_EYE_OUT]) / (eye_d + 1e-6)
        uy = np.array([-ux[1], ux[0]])
        roll = math.degrees(math.atan2(ux[1], ux[0]))
        x0, y0, x1, y1 = _bbox(p[R_BROW + L_BROW + [R_TEMPLE, L_TEMPLE, F.NOSE_TIP]], img.shape, pad=int(eye_d * 0.2))
        roi = img[y0:y1, x0:x1]
        lens_a = np.zeros(roi.shape[:2], np.float32)
        frame = np.zeros(roi.shape[:2], np.uint8)
        centers = []
        # Lens outline: ~50 mm wide against a ~90 mm outer-eye-corner span, with a
        # flattened top edge (Wayfarer-like) and the outer top corner pulled out.
        t = np.linspace(0, 2 * np.pi, 48, endpoint=False)
        la, lb = eye_d * 0.285, eye_d * 0.235
        for c, side in ((p[R_EYE].mean(0), -1), (p[L_EYE].mean(0), 1)):
            c = c + uy * eye_d * 0.04 - [x0, y0]
            centers.append(c)
            lx, ly = np.cos(t), np.sin(t)
            ly = np.where(ly < 0, -np.abs(ly) ** 0.35, ly)            # flat top
            lx = lx + np.where((ly < -0.5) & (lx * side > 0), 0.12 * side, 0)  # outer top corner
            shape = c + np.outer(lx * la, ux) + np.outer(ly * lb, uy)
            cv2.fillPoly(lens_a, [shape.astype(np.int32)], 1.0, cv2.LINE_AA)
            cv2.polylines(frame, [shape.astype(np.int32)], True, 255, max(2, int(eye_d * 0.03)), cv2.LINE_AA)
        # Bridge and arms towards the temples.
        thick = max(2, int(eye_d * 0.028))
        a = centers[0] + ux * la * 0.9 - uy * lb * 0.55
        b = centers[1] - ux * la * 0.9 - uy * lb * 0.55
        cv2.line(frame, tuple(a.astype(int)), tuple(b.astype(int)), 255, thick, cv2.LINE_AA)
        for c, temple, sgn in ((centers[0], p[R_TEMPLE], -1), (centers[1], p[L_TEMPLE], 1)):
            s = c + sgn * ux * la * 1.1 - uy * lb * 0.6
            cv2.line(frame, tuple(s.astype(int)), tuple((temple - [x0, y0]).astype(int)), 255, thick, cv2.LINE_AA)

        # Smoked glass: the eye shows faintly through a dark tint, darker at the top
        # (gradient lens), with a soft sky reflection in the upper-outer corner.
        hh, ww = roi.shape[:2]
        gy, gx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        top = np.clip(((gx - centers[0][0]) * uy[0] + (gy - centers[0][1]) * uy[1]) / lb * 0.5 + 0.5, 0, 1)
        tint = np.array([28, 24, 20], np.float32) * (0.6 + 0.6 * top[..., None])  # cool-brown smoke
        refl = np.zeros((hh, ww), np.float32)
        for c, sgn in ((centers[0], -1), (centers[1], 1)):
            hc = c + sgn * ux * la * 0.4 - uy * lb * 0.45
            d2 = ((gx - hc[0]) ** 2 * 0.6 + (gy - hc[1]) ** 2 * 1.6) / (la * 0.5) ** 2
            refl += np.exp(-d2)
        alpha = cv2.GaussianBlur(lens_a, (0, 0), 1.0)[..., None]
        base = roi.astype(np.float32)
        glass = base * 0.16 + tint + np.array([255, 235, 215], np.float32) * (refl[..., None] * 0.35)
        out = base * (1 - alpha) + glass * alpha
        # Gunmetal frame, lighter along its upper edge.
        fa = cv2.GaussianBlur(frame.astype(np.float32) / 255, (0, 0), 0.7)[..., None]
        metal = np.array([62, 58, 55], np.float32) * (1.5 - top[..., None])
        out = out * (1 - fa) + metal * fa
        roi[:] = np.clip(out, 0, 255).astype(np.uint8)

    def _glam(self, img, p):
        eye_d = np.linalg.norm(p[F.L_EYE_OUT] - p[F.R_EYE_OUT])
        x0, y0, x1, y1 = _bbox(p, img.shape, pad=4)
        roi = img[y0:y1, x0:x1]
        o = np.array([x0, y0])
        layers = []
        # Lipstick: outer lip minus the mouth opening.
        lips = np.zeros(roi.shape[:2], np.float32)
        cv2.fillPoly(lips, [(p[LIPS_OUTER] - o).astype(np.int32)], 1.0, cv2.LINE_AA)
        cv2.fillPoly(lips, [(p[LIPS_INNER] - o).astype(np.int32)], 0.0, cv2.LINE_AA)
        layers.append((cv2.GaussianBlur(lips, (0, 0), max(1.0, eye_d * 0.015)) * 0.65, (40, 20, 175)))
        # Eyeshadow between lid and brow.
        shadow = np.zeros_like(lips)
        for lid, brow in ((R_LID, R_BROW), (L_LID, L_BROW)):
            poly = np.vstack([p[lid], p[brow][::-1] * 0.45 + p[lid][[0, 2, 4, 6, 8]][::-1] * 0.55])
            cv2.fillPoly(shadow, [(poly - o).astype(np.int32)], 1.0, cv2.LINE_AA)
        layers.append((cv2.GaussianBlur(shadow, (0, 0), eye_d * 0.05) * 0.45, (120, 40, 110)))
        # Blush.
        blush = np.zeros_like(lips)
        for i in (R_CHEEK, L_CHEEK):
            cv2.circle(blush, tuple((p[i] - o).astype(int)), int(eye_d * 0.22), 1.0, -1, cv2.LINE_AA)
        layers.append((cv2.GaussianBlur(blush, (0, 0), eye_d * 0.12) * 0.28, (130, 110, 235)))

        out = roi.astype(np.float32)
        lum = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255.0
        for alpha, color in layers:
            # Colour keeps the skin's shading: multiply the tint by local luminance.
            shaded = np.array(color, np.float32) * (0.45 + 1.1 * lum)
            a = alpha[..., None]
            out = out * (1 - a) + shaded * a
        # Eyeliner along the upper lids.
        roi[:] = np.clip(out, 0, 255).astype(np.uint8)
        for lid in (R_LID, L_LID):
            cv2.polylines(roi, [(p[lid] - o).astype(np.int32)], False, (20, 15, 15), max(1, int(eye_d * 0.02)), cv2.LINE_AA)

    def _iris(self, img, p, color):
        eye_d = np.linalg.norm(p[F.L_EYE_OUT] - p[F.R_EYE_OUT])
        for (ci, ring), contour in ((R_IRIS, R_EYE), (L_IRIS, L_EYE)):
            c = p[ci]
            r = float(np.mean(np.linalg.norm(p[ring] - c, axis=1)))
            x0, y0, x1, y1 = _bbox(p[contour], img.shape, pad=int(eye_d * 0.05))
            roi = img[y0:y1, x0:x1]
            o = np.array([x0, y0])
            iris = np.zeros(roi.shape[:2], np.float32)
            cv2.circle(iris, tuple((c - o).astype(int)), max(2, int(r)), 1.0, -1, cv2.LINE_AA)
            opening = np.zeros_like(iris)  # eyelids hide part of the iris
            cv2.fillPoly(opening, [(p[contour] - o).astype(np.int32)], 1.0, cv2.LINE_AA)
            a = cv2.GaussianBlur(iris * opening, (0, 0), max(0.8, r * 0.12))[..., None] * 0.85
            lum = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255.0
            tinted = np.array(color, np.float32) * np.clip(lum * 1.8 + 0.15, 0, 1.3)
            roi[:] = np.clip(roi.astype(np.float32) * (1 - a) + tinted * a, 0, 255).astype(np.uint8)


def _bbox(pts, shape, pad=0):
    h, w = shape[:2]
    x0, y0 = np.floor(pts.min(0)).astype(int) - pad
    x1, y1 = np.ceil(pts.max(0)).astype(int) + pad
    return max(0, x0), max(0, y0), min(w, x1), min(h, y1)


def _blend_similarity(img, asset, a0, a1, b0, b1):
    """Rotate/scale/translate `asset` so a0->b0 and a1->b1, alpha-blended into img."""
    va, vb = a1 - a0, b1 - b0
    s = np.linalg.norm(vb) / (np.linalg.norm(va) + 1e-6)
    ang = math.atan2(vb[1], vb[0]) - math.atan2(va[1], va[0])
    c, si = s * math.cos(ang), s * math.sin(ang)
    m = np.array([[c, -si, 0], [si, c, 0]], np.float32)
    m[:, 2] = b0 - m[:, :2] @ a0
    h, w = asset.shape[:2]
    corners = np.array([[0, 0], [w, 0], [0, h], [w, h]], np.float32) @ m[:, :2].T + m[:, 2]
    x0, y0, x1, y1 = _bbox(corners, img.shape, pad=1)
    if x1 <= x0 or y1 <= y0:
        return
    m[:, 2] -= [x0, y0]
    warped = cv2.warpAffine(asset, m, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    a = warped[:, :, 3:4].astype(np.float32) / 255.0
    roi = img[y0:y1, x0:x1]
    roi[:] = (roi.astype(np.float32) * (1 - a) + warped[:, :, :3].astype(np.float32) * a).astype(np.uint8)
