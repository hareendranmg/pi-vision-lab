"""Pi Vision Lab: full-screen, gesture-driven AI demo for a Raspberry Pi 4."""
import argparse
import os
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windowed", action="store_true", help="run in a window instead of full screen")
    ap.add_argument("--fake-camera", type=Path, help="loop a still image instead of the Pi camera")
    ap.add_argument("--shots", type=Path, help="cycle through every screen, save screenshots there, then quit")
    ap.add_argument("--size", default="800x480", help="window size for --windowed/--shots")
    args = ap.parse_args()

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from .backend import Backend  # registers CameraView with QML
    from .control import ControlServer
    from .engine import VisionWorker
    from .presenter import Presenter  # registers PresenterView with QML

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Pi Vision Lab")
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    worker = VisionWorker(ROOT / "models", args.fake_camera)
    clips = ROOT / "assets" / "presenter"
    presenter = Presenter(clips) if (clips / "clips.json").exists() else None
    backend = Backend(worker, presenter)

    kiosk = not (args.windowed or args.shots)
    w, h = (int(v) for v in args.size.split("x"))
    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("presenter", presenter)
    ctx.setContextProperty("kiosk", kiosk)
    ctx.setContextProperty("startSize", [w, h])
    engine.load(str(ROOT / "qml" / "Main.qml"))
    if not engine.rootObjects():
        sys.exit(1)
    win = engine.rootObjects()[0]
    backend.attach_window(win)
    if kiosk:
        app.setOverrideCursor(Qt.CursorShape.BlankCursor)
    control = ControlServer(win, backend)  # noqa: F841 (kept alive for the app's lifetime)
    worker.start()
    backend._comment(backend.commentator.on_screen("home"))

    if args.shots:
        args.shots.mkdir(parents=True, exist_ok=True)
        screens = ["home", "objects", "face", "color"]

        def step(i=0):
            if i >= len(screens):
                app.quit()
                return
            win.setProperty("screen", screens[i])
            QTimer.singleShot(4000, lambda: (win.grabWindow().save(str(args.shots / f"{i}_{screens[i]}.png")),
                                             step(i + 1)))
        QTimer.singleShot(5000, step)

    # Let Python handle Ctrl+C while the Qt event loop runs.
    tick = QTimer()
    tick.start(250)
    tick.timeout.connect(lambda: None)

    code = app.exec()
    worker.requestInterruption()
    worker.wait(3000)
    del engine  # tear QML down while `backend` is still alive
    sys.exit(code)


if __name__ == "__main__":
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    main()
