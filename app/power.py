"""Shut the Pi down from the kiosk UI.

The app runs inside the logged-in desktop session, so logind/polkit lets it
power off without a password (an SSH login is refused the same request).
PIV_SHUTDOWN_CMD overrides the command, e.g. ``PIV_SHUTDOWN_CMD=true`` to
exercise the whole UI flow without powering off.
"""
import os
import shlex
import subprocess
import threading

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

DEFAULT_CMD = "systemctl poweroff"
GOODBYE_MS = 2500  # time for the "Shutting down" screen and the presenter's wave


class Power(QObject):
    changed = Signal()
    _done = Signal(int, str)

    def __init__(self, presenter=None):
        super().__init__()
        self.presenter = presenter
        self._state, self._error = "idle", ""
        self._done.connect(self._finish)

    state = Property(str, lambda s: s._state, notify=changed)   # idle | shutting | failed
    error = Property(str, lambda s: s._error, notify=changed)

    @Slot()
    def shutdown(self):
        if self._state == "shutting":
            return
        self._state, self._error = "shutting", ""
        self.changed.emit()
        if self.presenter is not None:
            self.presenter.say("Goodbye! Shutting down now. See you next time.", "wave")
        QTimer.singleShot(GOODBYE_MS, self._run)

    @Slot()
    def reset(self):
        if self._state == "failed":
            self._state, self._error = "idle", ""
            self.changed.emit()

    def _run(self):
        cmd = shlex.split(os.environ.get("PIV_SHUTDOWN_CMD", DEFAULT_CMD))

        def work():
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                self._done.emit(r.returncode, (r.stderr or r.stdout).strip())
            except (OSError, subprocess.TimeoutExpired) as e:
                self._done.emit(1, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _finish(self, code, message):
        # On success the system is already going down: stay on the "Shutting down" screen.
        if code != 0:
            self._state = "failed"
            self._error = message or f"{DEFAULT_CMD} exited with code {code}"
            self.changed.emit()


def can_power_off():
    """Ask logind whether this process may power off: "yes", "challenge" (needs a password) or "no"."""
    try:
        r = subprocess.run(["busctl", "call", "org.freedesktop.login1", "/org/freedesktop/login1",
                            "org.freedesktop.login1.Manager", "CanPowerOff"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip().split(" ", 1)[-1].strip('"') if r.returncode == 0 else f"error: {r.stderr.strip()}"
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"error: {e}"
