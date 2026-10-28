"""QObject bridge between the vision thread and the QML UI."""
from PySide6.QtCore import Property, QEvent, QObject, QPointF, Qt, Signal
from PySide6.QtGui import QGuiApplication, QImage, QMouseEvent
from PySide6.QtQml import QmlElement

from .commentary import Commentator
from .frameitem import FrameItem

QML_IMPORT_NAME = "PiVision"
QML_IMPORT_MAJOR_VERSION = 1


class FrameBus(QObject):
    frame = Signal(QImage)


FRAME_BUS = FrameBus()


@QmlElement
class CameraView(FrameItem):
    """Shows the latest (already mirrored) camera frame, scaled by the GPU."""

    def __init__(self, parent=None):
        super().__init__(parent)
        FRAME_BUS.frame.connect(self.set_image)


class Backend(QObject):
    modeChanged = Signal()
    effectChanged = Signal()
    visionChanged = Signal()
    cursorChanged = Signal()
    goHome = Signal()

    def __init__(self, worker, presenter=None):
        super().__init__()
        self.worker = worker
        self.presenter = presenter
        self.commentator = Commentator()
        self.window = None
        self._mode = "home"
        self._vision = {}
        self._cursor = (0.5, 0.5)
        self._cursor_visible = False
        self._pinching = False
        worker.frameReady.connect(FRAME_BUS.frame)
        worker.stateReady.connect(self._on_state)

    def attach_window(self, window):
        self.window = window
        window.widthChanged.connect(self._update_view)
        window.heightChanged.connect(self._update_view)
        self._update_view()

    def _update_view(self):
        w, h = self.window.width(), self.window.height()
        if w > 0 and h > 0:
            # Frames are rendered at view size; cap work on large monitors.
            scale = min(1.0, 1024 / max(w, h))
            self.worker.view_size = (int(w * scale) // 2 * 2, int(h * scale) // 2 * 2)
            if self.presenter is not None:
                self.presenter.window_aspect = w / h

    # ---- properties --------------------------------------------------------
    def _get_mode(self):
        return self._mode

    def _set_mode(self, m):
        if m != self._mode:
            self._mode = m
            self.worker.mode = m
            self.modeChanged.emit()
            self._comment(self.commentator.on_screen(m))

    mode = Property(str, _get_mode, _set_mode, notify=modeChanged)

    def _get_effect(self):
        return self.worker.face_effect

    def _set_effect(self, e):
        if e != self.worker.face_effect:
            self.worker.face_effect = e
            self.effectChanged.emit()
            self._comment(self.commentator.on_effect(e))

    faceEffect = Property(str, _get_effect, _set_effect, notify=effectChanged)
    vision = Property("QVariantMap", lambda s: s._vision, notify=visionChanged)
    cursorX = Property(float, lambda s: s._cursor[0], notify=cursorChanged)
    cursorY = Property(float, lambda s: s._cursor[1], notify=cursorChanged)
    cursorVisible = Property(bool, lambda s: s._cursor_visible, notify=cursorChanged)
    pinching = Property(bool, lambda s: s._pinching, notify=cursorChanged)
    pinchLevel = Property(float, lambda s: s._vision.get("pinchLevel", 0.0), notify=cursorChanged)
    homeProgress = Property(float, lambda s: s._vision.get("homeProgress", 0.0), notify=cursorChanged)

    # ---- vision updates ----------------------------------------------------
    def _comment(self, line):
        if line and self.presenter is not None:
            self.presenter.say(*line)

    def _on_state(self, state):
        self._vision = state
        self.visionChanged.emit()
        self._comment(self.commentator.on_vision(state))
        cur = state.get("cursor")
        was_visible = self._cursor_visible
        self._cursor_visible = cur is not None
        if cur is not None:
            self._cursor = cur
        self._pinching = bool(state.get("pinching"))
        self.cursorChanged.emit()
        if self.window is not None:
            self._inject(state.get("click"), cur, was_visible)
        if state.get("home"):
            self.goHome.emit()

    def _inject(self, click, cur, was_visible):
        """Replay the air cursor as real mouse events so every QML control just works."""
        w, h = self.window.width(), self.window.height()
        if cur is None:
            if was_visible:  # park the pointer off-screen to clear hover states
                self._send(QEvent.Type.MouseMove, QPointF(-50, -50), Qt.MouseButton.NoButton)
            if click == "release":
                self._send(QEvent.Type.MouseButtonRelease, QPointF(-50, -50), Qt.MouseButton.LeftButton)
            return
        pos = QPointF(cur[0] * w, cur[1] * h)
        self._send(QEvent.Type.MouseMove, pos, Qt.MouseButton.NoButton)
        if click == "press":
            self._send(QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton)
        elif click == "release":
            self._send(QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.LeftButton)

    def tap(self, nx, ny):
        """Synthesise a touch-style tap at normalised window coordinates."""
        pos = QPointF(nx * self.window.width(), ny * self.window.height())
        for etype, button, buttons in ((QEvent.Type.MouseMove, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton),
                                       (QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
                                       (QEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)):
            QGuiApplication.sendEvent(self.window, QMouseEvent(etype, pos, self.window.mapToGlobal(pos), button,
                                                               buttons, Qt.KeyboardModifier.NoModifier))

    def _send(self, etype, pos, button):
        held = self._pinching if etype != QEvent.Type.MouseButtonRelease else False
        buttons = Qt.MouseButton.LeftButton if held else Qt.MouseButton.NoButton
        ev = QMouseEvent(etype, pos, self.window.mapToGlobal(pos), button, buttons,
                         Qt.KeyboardModifier.NoModifier)
        QGuiApplication.sendEvent(self.window, ev)
