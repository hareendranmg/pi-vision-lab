#!/bin/sh
# Launch Pi Vision Lab full-screen and keep it running: it is restarted after a
# crash or a normal exit. Started at login by ~/.config/autostart/pi-vision-lab.desktop.
# Extra arguments are passed through (e.g. --windowed).
cd "$(dirname "$0")" || exit 1
LOG="$HOME/.cache/pi_vision_lab.log"
mkdir -p "$(dirname "$LOG")"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland}"
while true; do
    .venv/bin/python -m app.main "$@" >>"$LOG" 2>&1
    echo "$(date) app exited ($?), restarting in 3 s" >>"$LOG"
    sleep 3
done
