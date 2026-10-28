"""Camera capture + AI loop running on its own thread.

Every frame: hand tracking (always on, it drives the UI) plus the model for the
current screen. Models see the un-mirrored frame; everything sent to the UI is
mirrored so the screen behaves like a mirror.
"""
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .color import sample_at
from .face_fx import FaceFx
from .gesture import GestureInput
from .vision import faces as F
from .vision.faces import FaceTracker
from .vision.hands import CONNECTIONS, HandTracker
from .vision.objects import ObjectDetector

CAM_SIZE = (960, 540)


class Camera:
    def __init__(self, fake_image=None):
        self.fake = cv2.imread(str(fake_image)) if fake_image else None
        if self.fake is not None:
            # Letterbox to the camera's 16:9 so tests see the whole picture.
            h, w = self.fake.shape[:2]
            tw = max(w, int(h * 16 / 9))
            th = max(h, int(tw * 9 / 16))
            canvas = np.zeros((th, tw, 3), np.uint8)
            canvas[(th - h) // 2:(th - h) // 2 + h, (tw - w) // 2:(tw - w) // 2 + w] = self.fake
            self.fake = cv2.resize(canvas, CAM_SIZE, interpolation=cv2.INTER_AREA)
            return
        from libcamera import controls
        from picamera2 import Picamera2
        self.cam = Picamera2()
        # Full-FOV binned sensor mode scaled down; RGB888 arrives in BGR byte order.
        self.cam.configure(self.cam.create_video_configuration(
            main={"size": CAM_SIZE, "format": "RGB888"}, buffer_count=4))
        self.cam.start()
        try:
            self.cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except Exception:
            pass  # lenses without autofocus

    def read(self):
        if self.fake is not None:
            time.sleep(1 / 30)
            return self.fake.copy()
        return self.cam.capture_array("main")

    def close(self):
        if self.fake is None:
            self.cam.stop()


def crop_to_aspect(img, aspect):
    h, w = img.shape[:2]
    if w / h > aspect:
        nw = int(h * aspect)
        x = (w - nw) // 2
        return img[:, x:x + nw]
    nh = int(w / aspect)
    y = (h - nh) // 2
    return img[y:y + nh]


class VisionWorker(QThread):
    frameReady = Signal(QImage)
    stateReady = Signal(object)

    def __init__(self, model_dir: Path, fake_image=None):
        super().__init__()
        self.model_dir, self.fake_image = model_dir, fake_image
        self.mode = "home"
        self.face_effect = "masquerade"
        self.view_size = (800, 480)
        self.gestures = GestureInput()
        self._lock = threading.Lock()
        self._last_frame = None

    def snapshot(self):
        """Latest un-mirrored camera crop (what the screen shows, before mirroring)."""
        with self._lock:
            return None if self._last_frame is None else self._last_frame.copy()

    def run(self):
        # Fewer than 4 inference threads: with two models loaded, 4 each
        # oversubscribed the 4 cores and starved the UI/render threads.
        threads = int(os.environ.get("PIV_THREADS", "3"))
        hands = HandTracker(self.model_dir / "hand_landmarker", threads)
        faces = FaceTracker(self.model_dir / "face_landmarker", threads)
        objects = ObjectDetector(self.model_dir / "efficientdet_lite0_pp.tflite", threads=threads)
        found, frame_no, first_obj_frame = [], 0, 1
        fx = FaceFx(self.model_dir.parent / "assets")
        cam = Camera(self.fake_image)
        fps, last = 0.0, time.perf_counter()
        try:
            while not self.isInterruptionRequested():
                vw, vh = self.view_size
                bgr = crop_to_aspect(cam.read(), vw / vh)
                with self._lock:
                    self._last_frame = bgr
                H, W = bgr.shape[:2]
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                mode = self.mode

                hand = hands.process(rgb)
                ev = self.gestures.update(hand, W, H)
                state = {"hand": {"present": hand is not None, "gesture": ev["gesture"]},
                         "cursor": ev.get("cursor"), "pinching": ev.get("pinching", False),
                         "click": ev["click"], "home": ev["home"], "mode": mode,
                         "pinchLevel": round(ev["pinch_level"], 2), "homeProgress": round(ev["home_progress"], 2)}

                disp = cv2.resize(bgr, (vw, vh), interpolation=cv2.INTER_LINEAR)
                sx, sy = vw / W, vh / H

                frame_no += 1
                if mode != "objects":
                    found, first_obj_frame = [], frame_no + 1
                if mode == "objects":
                    # Detection (~70 ms) on alternate frames; boxes are reused in
                    # between so hand tracking keeps the full frame rate.
                    if frame_no % 2 == 0 or frame_no == first_obj_frame:
                        found = objects.process(rgb)
                    state["objects"] = [{"label": o["label"], "score": round(o["score"], 2),
                                         "x": 1.0 - o["x1"], "y": o["y0"],
                                         "w": o["x1"] - o["x0"], "h": o["y1"] - o["y0"]} for o in found]
                elif mode == "face":
                    face = faces.process(rgb)
                    state["face"] = self._face_state(face, W, H)
                    if face is not None:
                        fx.draw(disp, fx.smooth(face.points * [sx, sy]), self.face_effect)
                    else:
                        fx.reset()
                else:
                    faces.roi = None
                if mode == "color":
                    state["color"] = self._color_state(bgr, hand)

                if hand is not None:
                    self._draw_hand(disp, hand.points * [sx, sy], ev.get("pinching", False))

                disp = cv2.flip(disp, 1)
                img = QImage(disp.data, disp.shape[1], disp.shape[0], disp.strides[0],
                             QImage.Format.Format_BGR888).copy()
                now = time.perf_counter()
                fps = 0.9 * fps + 0.1 / max(now - last, 1e-3)
                last = now
                state["fps"] = round(fps, 1)
                self.frameReady.emit(img)
                self.stateReady.emit(state)
        finally:
            cam.close()

    def _color_state(self, bgr, hand):
        """Sample just beyond the index fingertip (so the finger itself isn't
        measured), or the frame centre when no hand is visible."""
        H, W = bgr.shape[:2]
        if hand is not None:
            tip, pip = hand.points[8], hand.points[6]
            target = tip + (tip - pip) * 1.4
            target = np.clip(target, [W * 0.03, H * 0.03], [W * 0.97, H * 0.97])
        else:
            target = np.array([W / 2, H / 2])
        prev = getattr(self, "_color_pt", None)
        self._color_pt = target if prev is None else prev + (target - prev) * 0.5
        x, y = self._color_pt
        return sample_at(bgr, x, y) | {"x": float(1.0 - x / W), "y": float(y / H), "tracking": hand is not None}

    @staticmethod
    def _face_state(face, W, H):
        if face is None:
            return {"present": False}
        p = face.points
        pt = lambda *idx: [float(1.0 - p[list(idx)][:, 0].mean() / W), float(p[list(idx)][:, 1].mean() / H)]
        eyes = sorted([pt(F.R_EYE_OUT, F.R_EYE_IN), pt(F.L_EYE_OUT, F.L_EYE_IN)])
        return {"present": True, "emotion": face.emotion,
                "scores": {k: round(v, 2) for k, v in face.scores.items()},
                "eyeA": eyes[0], "eyeB": eyes[1], "nose": pt(F.NOSE_TIP),
                "mouth": pt(F.LIP_TOP, F.LIP_BOT), "upperLip": pt(F.LIP_TOP, F.NOSE_TIP),
                "forehead": pt(F.FOREHEAD), "chin": pt(F.CHIN)}

    @staticmethod
    def _draw_hand(img, pts, pinching):
        color = (255, 120, 255) if pinching else (120, 255, 160)
        p = pts.astype(int)
        for a, b in CONNECTIONS:
            cv2.line(img, tuple(p[a]), tuple(p[b]), color, 2, cv2.LINE_AA)
        for x, y in p:
            cv2.circle(img, (x, y), 3, (255, 255, 255), -1, cv2.LINE_AA)
