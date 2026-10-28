"""Turns hand landmarks into an air cursor, pinch clicks and named gestures.

Accuracy notes (hand tracking runs at ~8-14 fps on the Pi 4):
- Hand size is measured from several palm bones, so tilting the hand toward
  the camera doesn't shrink the scale and trigger false pinches.
- A pinch must be seen on 2 consecutive frames to press and 2 to release.
- While pinched the cursor is frozen where it was ~120 ms before the fingers
  started closing, so the click lands on what you were aiming at.
- A thumb resting along the index finger isn't a pinch: the thumb tip must be
  nearer the index *tip* than the index middle joint.
- "Hold a fist" tolerates the odd misread frame instead of restarting.
"""
import math
import time
from collections import deque

import numpy as np

# Area of the camera frame mapped to the full screen, so users needn't reach the edges.
ACTIVE = (0.12, 0.10, 0.88, 0.80)  # x0, y0, x1, y1 (normalised, mirrored view)
PINCH_DOWN, PINCH_UP = 0.26, 0.40   # thumb-index gap / hand size, with hysteresis
PINCH_NEAR = 0.50                    # gap at which the cursor starts filling
FRAMES_TO_PRESS, FRAMES_TO_RELEASE = 2, 2
AIM_LOOKBACK_S = 0.12
FIST_HOLD_S = 1.0
FIST_GRACE_S = 0.35                  # a non-fist blip shorter than this doesn't reset the hold


class OneEuro:
    """One Euro filter: smooth when still, responsive when moving fast."""

    def __init__(self, min_cutoff=0.9, beta=0.03, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x = self.dx = self.t = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        x = np.asarray(x, dtype=float)
        if self.x is None:
            self.x, self.dx, self.t = x, np.zeros_like(x), t
            return x
        dt = max(t - self.t, 1e-3)
        dx = (x - self.x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx = a_d * dx + (1 - a_d) * self.dx
        cutoff = self.min_cutoff + self.beta * np.linalg.norm(self.dx) * 100
        a = self._alpha(cutoff, dt)
        self.x = a * x + (1 - a) * self.x
        self.t = t
        return self.x

    def reset(self):
        self.x = self.dx = self.t = None


def hand_size(p):
    """Robust hand scale: wrist->middle knuckle and the knuckle span, whichever is larger."""
    d = lambda a, b: float(np.linalg.norm(p[a] - p[b]))
    return max(d(0, 9), d(5, 17) * 1.25, d(0, 5) * 1.05) + 1e-6


def curled(p):
    """How many of the four fingers are folded towards the palm."""
    centre = p[[0, 5, 9, 13, 17]].mean(0)
    size = hand_size(p)
    return sum(np.linalg.norm(p[tip] - centre) < size * 0.62 for tip in (8, 12, 16, 20))


def pinch_gap(p):
    """Thumb-index tip gap relative to hand size; inf when the thumb rests by the index's middle joint."""
    d = lambda a, b: float(np.linalg.norm(p[a] - p[b]))
    if d(4, 8) > d(4, 6):
        return float("inf")
    return d(4, 8) / hand_size(p)


def classify(p):
    """Name a static hand pose from 21 landmarks (any orientation)."""
    d = lambda a, b: float(np.linalg.norm(p[a] - p[b]))
    size = hand_size(p)
    ext = {f: d(tip, 0) > d(pip, 0) * 1.12
           for f, (tip, pip) in {"index": (8, 6), "middle": (12, 10), "ring": (16, 14), "pinky": (20, 18)}.items()}
    thumb_out = d(4, 17) > d(3, 17) * 1.08 and d(4, 5) > size * 0.45
    n = sum(ext.values())

    if pinch_gap(p) < PINCH_DOWN:
        return "ok" if ext["middle"] and ext["ring"] and ext["pinky"] else "pinch"
    if curled(p) >= 4 and not thumb_out:
        return "fist"
    if n == 0 and thumb_out:
        if p[4][1] < p[0][1] - size * 0.4:
            return "thumbs up"
        if p[4][1] > p[0][1] + size * 0.4:
            return "thumbs down"
        return "fist"
    if n == 4:
        return "open palm"
    if ext["index"] and ext["middle"] and n == 2:
        return "peace"
    if ext["index"] and ext["pinky"] and n == 2:
        return "rock on"
    if ext["index"] and n == 1:
        return "pointing"
    return ""


class GestureInput:
    def __init__(self):
        self.filter = OneEuro()
        self.history = deque(maxlen=30)      # (time, smoothed cursor)
        self.pinching = False
        self.streak = 0                      # consecutive frames disagreeing with `pinching`
        self.frozen = None
        self.fist_since = None
        self.fist_last = 0.0
        self.home_cooldown = 0.0
        self.lost_at = 0.0
        self.cursor = None

    def _aim_before(self, t):
        """Cursor position from just before `t` (the moment the fingers began closing)."""
        for ts, pos in reversed(self.history):
            if ts <= t:
                return pos.copy()
        return self.history[0][1].copy() if self.history else None

    def update(self, hand, width, height):
        """hand: Hand in un-mirrored frame pixels. Returns an event dict."""
        now = time.monotonic()
        ev = {"present": hand is not None, "gesture": "", "click": None, "home": False,
              "pinch_level": 0.0, "home_progress": 0.0}
        if hand is None:
            if now - self.lost_at > 0.3:
                self.filter.reset()
                self.history.clear()
            if self.pinching:
                ev["click"] = "release"
                self.pinching, self.frozen = False, None
            self.streak = 0
            self.fist_since = None
            ev["cursor"] = None
            return ev
        self.lost_at = now
        p = hand.points
        # Mirror so moving your hand right moves the cursor right.
        norm = np.column_stack([1.0 - p[:, 0] / width, p[:, 1] / height])
        gap = pinch_gap(norm)

        # Aim with the midpoint of thumb and index tips: it barely moves when pinching.
        aim = (norm[4] + norm[8]) / 2
        x0, y0, x1, y1 = ACTIVE
        target = np.clip([(aim[0] - x0) / (x1 - x0), (aim[1] - y0) / (y1 - y0)], 0.0, 1.0)
        smooth = self.filter(target, now)
        self.history.append((now, smooth.copy()))

        # Debounced pinch state machine.
        wants = gap < PINCH_DOWN if not self.pinching else gap < PINCH_UP
        self.streak = self.streak + 1 if wants != self.pinching else 0
        if not self.pinching and self.streak >= FRAMES_TO_PRESS:
            self.pinching, self.streak = True, 0
            self.frozen = self._aim_before(now - AIM_LOOKBACK_S - 0.1)
            ev["click"] = "press"
        elif self.pinching and self.streak >= FRAMES_TO_RELEASE:
            self.pinching, self.streak = False, 0
            ev["click"] = "release"
        if self.pinching:
            self.cursor = self.frozen
        else:
            self.frozen = None
            self.cursor = smooth
        level = 0.0 if math.isinf(gap) else (PINCH_NEAR - gap) / (PINCH_NEAR - PINCH_DOWN)
        ev["pinch_level"] = 1.0 if self.pinching else float(np.clip(level, 0, 1))

        gesture = "pinch" if self.pinching else classify(p)
        ev["gesture"] = gesture
        # Hold-a-fist-to-go-home, tolerant of brief misreads.
        if gesture == "fist" and now >= self.home_cooldown:
            self.fist_since = self.fist_since or now
            self.fist_last = now
        elif self.fist_since and now - self.fist_last > FIST_GRACE_S:
            self.fist_since = None
        if self.fist_since:
            held = now - self.fist_since
            ev["home_progress"] = float(min(1.0, held / FIST_HOLD_S))
            if held >= FIST_HOLD_S:
                ev["home"] = True
                self.fist_since = None
                self.home_cooldown = now + 2.0
        ev["cursor"] = (float(self.cursor[0]), float(self.cursor[1]))
        ev["pinching"] = self.pinching
        return ev
