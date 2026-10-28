"""Send commands to a running Pi Vision Lab: python3 tools/ctl.py "screen face" "shot /tmp/a.png" """
import socket
import sys

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect("/tmp/pi_vision_lab.sock")
    f = s.makefile("rw")
    for cmd in sys.argv[1:]:
        f.write(cmd + "\n")
        f.flush()
        print(f.readline().rstrip())
