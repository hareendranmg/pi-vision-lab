"""Local test-control socket (/tmp/pi_vision_lab.sock), one command per line:

  screen <home|objects|face|color>       switch screen
  tap <x> <y>                            tap at normalised window coords (0..1)
  effect <name>                          Face Magic effect (masquerade, crown, shades, glam, iceeyes, mesh, none)
  shot <path.png>                        save a screenshot of the window
  frame <path.jpg>                       save the raw (un-mirrored) camera frame
  state                                  JSON of the latest vision state
"""
import json

from PySide6.QtNetwork import QLocalServer

SOCKET = "/tmp/pi_vision_lab.sock"


class ControlServer:
    def __init__(self, win, backend):
        self.win, self.backend = win, backend
        QLocalServer.removeServer(SOCKET)
        self.server = QLocalServer()
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.listen(SOCKET)
        self.server.newConnection.connect(self._accept)
        self._clients = []

    def _accept(self):
        sock = self.server.nextPendingConnection()
        self._clients.append(sock)
        sock.readyRead.connect(lambda: self._read(sock))
        sock.disconnected.connect(lambda: self._clients.remove(sock))

    def _read(self, sock):
        while sock.canReadLine():
            line = bytes(sock.readLine()).decode().strip()
            try:
                reply = self._handle(*line.split())
            except Exception as e:  # report bad commands to the caller
                reply = f"error: {e}"
            sock.write((reply + "\n").encode())
            sock.flush()

    def _handle(self, cmd, *args):
        b = self.backend
        if cmd == "screen":
            self.win.setProperty("screen", args[0])
        elif cmd == "effect":
            b.faceEffect = args[0]
        elif cmd == "tap":
            b.tap(float(args[0]), float(args[1]))
        elif cmd == "shot":
            return "ok" if self.win.grabWindow().save(args[0]) else "error: save failed"
        elif cmd == "frame":
            import cv2
            frame = b.worker.snapshot()
            return "ok" if frame is not None and cv2.imwrite(args[0], frame) else "error: no frame"
        elif cmd == "state":
            return json.dumps({"screen": self.win.property("screen"), "vision": b._vision})
        else:
            return f"error: unknown command {cmd}"
        return "ok"
