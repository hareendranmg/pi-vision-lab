"""Rajaram, the on-screen presenter: plays pre-rendered 3D clips and choreographs them.

States: away -> walking_in -> turning_in -> idle <-> talking -> turning_out ->
walking_out -> away. Clips are transparent PNG sequences rendered by
presenter_src/render_presenter.py. All frames (~0.7 GB) are decoded once in a
background thread at start-up so the UI thread never decodes PNGs, and they
are shown as GPU textures (see frameitem.py).
"""
import json
import random
import threading
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQml import QmlElement

from .frameitem import FrameItem

QML_IMPORT_NAME = "PiVision"
QML_IMPORT_MAJOR_VERSION = 1

FPS = 30
HEIGHT_FRAC = 0.76        # sprite height as a fraction of the window height
SPRITE_METRES = 2.37      # world height covered by the sprite (85 mm lens at 8.4 m)
WALK_SPEED = 1.25         # m/s, matches the walk cycle so feet don't slide
HOME_X, OFF_X = 0.86, 1.18
LEAVE_AFTER_S = 25


class _Bus(QObject):
    frame = Signal(QImage)


BUS = _Bus()

# Clips most needed first, so he can walk in while the rest still load.
LOAD_ORDER = ["walk_in", "turn_in", "idle", "talk1", "talk2", "present", "excited", "wave", "turn_out", "walk_out"]


@QmlElement
class PresenterView(FrameItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        BUS.frame.connect(self.set_image)


def _load(path):
    return QImage(str(path)).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


class Presenter(QObject):
    moved = Signal()
    changed = Signal()

    def __init__(self, clip_dir: Path):
        super().__init__()
        meta = json.loads((clip_dir / "clips.json").read_text())
        self.aspect = meta["size"][0] / meta["size"][1]
        self.frames = {name: sorted((clip_dir / name).glob("[0-9]*.png")) for name in meta["clips"]}
        self.cache = {}
        threading.Thread(target=self._preload, daemon=True).start()
        self.window_aspect = 800 / 480
        self.state, self.x = "away", OFF_X
        self.clip, self.i, self.loop = None, 0, True
        self.fade_from, self.fade = QImage(), 0.0
        self.queue = deque(maxlen=2)
        self.bubble, self.bubble_until = "", 0.0
        self.last_activity = time.monotonic()
        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / FPS))
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    # ---- QML properties ----
    xPos = Property(float, lambda s: s.x, notify=moved)
    shown = Property(bool, lambda s: s.state != "away", notify=changed)
    bubbleText = Property(str, lambda s: s.bubble, notify=changed)
    spriteAspect = Property(float, lambda s: s.aspect, constant=True)
    heightFrac = Property(float, lambda s: HEIGHT_FRAC, constant=True)

    def say(self, text, gesture="talk"):
        self.queue.append((text, gesture))
        self.last_activity = time.monotonic()
        if self.state in ("away", "walking_out", "turning_out"):
            self._play("walk_in")
            self.state = "walking_in"
            self.changed.emit()

    # ---- playback ----
    def _preload(self):
        order = [c for c in LOAD_ORDER if c in self.frames] + [c for c in self.frames if c not in LOAD_ORDER]
        for clip in order:
            for i, path in enumerate(self.frames[clip]):
                if (clip, i) not in self.cache:
                    self.cache[(clip, i)] = _load(path)

    def _image(self, clip, i):
        img = self.cache.get((clip, i))
        if img is None:  # not preloaded yet
            img = self.cache[(clip, i)] = _load(self.frames[clip][i])
        return img

    def _frame(self):
        """Current frame, cross-faded from the previous clip for a few frames after a cut."""
        img = self._image(self.clip, self.i)
        if self.fade <= 0 or self.fade_from.isNull():
            return img
        out = QImage(img.size(), QImage.Format.Format_ARGB32_Premultiplied)
        out.fill(0)
        p = QPainter(out)
        p.setOpacity(self.fade)
        p.drawImage(0, 0, self.fade_from)
        p.setOpacity(1.0 - self.fade)
        p.drawImage(0, 0, img)
        p.end()
        return out

    def _play(self, clip, loop=True):
        if self.clip is not None and clip != self.clip:
            self.fade_from, self.fade = self._image(self.clip, self.i), 1.0
        self.clip, self.i, self.loop = clip, 0, loop

    def _finished(self):
        return not self.loop and self.i >= len(self.frames[self.clip]) - 1

    def _tick(self):
        now = time.monotonic()
        if self.state == "away" or self.clip is None:
            return
        n = len(self.frames[self.clip])
        self.i = (self.i + 1) % n if self.loop else min(self.i + 1, n - 1)
        self.fade = max(0.0, self.fade - 1 / 6)

        # Screen-width fraction per frame for a WALK_SPEED stride.
        step = WALK_SPEED / SPRITE_METRES * HEIGHT_FRAC / self.window_aspect / FPS
        s, x0, shown0, bubble0 = self.state, self.x, self.state != "away", self.bubble
        if s == "walking_in":
            self.x = max(HOME_X, self.x - step)
            if self.x <= HOME_X:
                self.state = "turning_in"
                self._play("turn_in", loop=False)
        elif s == "turning_in" and self._finished():
            self._idle()
        elif s == "idle":
            if self.queue:
                self._talk(*self.queue.popleft())
            elif now - self.last_activity > LEAVE_AFTER_S:
                self.state = "turning_out"
                self._play("turn_out", loop=False)
        elif s == "talking":
            if self.clip == "wave" and self._finished():
                self._play(random.choice(["talk1", "talk2"]))
            if now > self.bubble_until:
                self.bubble = ""
                self.last_activity = now
                self._idle()
        elif s == "turning_out" and self._finished():
            self.state = "walking_out"
            self._play("walk_out")
        elif s == "walking_out":
            self.x = min(OFF_X, self.x + step)
            if self.x >= OFF_X:
                self.state, self.clip = "away", None
        if self.clip is not None:
            BUS.frame.emit(self._frame())
        # Only notify QML about what actually changed.
        if self.x != x0:
            self.moved.emit()
        if (self.state != "away") != shown0 or self.bubble != bubble0:
            self.changed.emit()

    def _idle(self):
        self.state = "idle"
        self._play("idle")

    def _talk(self, text, gesture):
        self.state = "talking"
        self.bubble = text
        self.bubble_until = time.monotonic() + 1.6 + 0.065 * len(text)
        clip = {"talk": random.choice(["talk1", "talk2"]), "present": "present",
                "excited": "excited", "wave": "wave"}.get(gesture, "talk1")
        self._play(clip, loop=clip != "wave")
