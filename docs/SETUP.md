# Setting up a Pi

## Hardware

| Item | Tested with | Notes |
|---|---|---|
| Board | Raspberry Pi 4 Model B, 8 GB | 4 GB should work: the presenter preload uses ~0.7 GB, the app ~1.5 GB in total. A Pi 5 runs faster. |
| Camera | Camera Module 3 **Wide** (IMX708) | Any libcamera camera works; the wide lens suits a kiosk. Autofocus is set to continuous. |
| Display | Official Raspberry Pi DSI touch display (800×480) or any HDMI monitor | The layout scales to any resolution; designed at 800×480, also tested at 1920×1080 |
| Power | Official 15 W / 27 W supply | Under-voltage throttles the CPU and halves the frame rate (`vcgencmd get_throttled` should print `0x0`) |
| Storage | 32 GB microSD | ~1 GB for the app, models and presenter clips |

Mount the camera **above or below the screen, facing the visitor**. Hands and faces track best at 0.5–1.5 m.

## Operating system

Flash **Raspberry Pi OS (64-bit) with desktop**, Debian 13 "trixie", using Raspberry Pi Imager.
Set the username to `pi` (any name works) and enable SSH. The desktop must be the default **labwc** (Wayland) session.

## Install

```bash
git clone https://github.com/hareendranmg/pi-vision-lab.git ~/pi_ai_demo
cd ~/pi_ai_demo
./setup.sh
sudo reboot
```

What `setup.sh` does. It's safe to re-run, and it asks for your password for `sudo`:

| Step | Details |
|---|---|
| System packages | `python3-picamera2 python3-venv python3-pil curl rpicam-apps` |
| Python env | `.venv` created with `--system-site-packages` (keeps apt's picamera2/libcamera/numpy), then `pip install -r requirements.txt`: `ai-edge-litert`, `opencv-contrib-python`, `PySide6-Essentials` |
| Models | `scripts/download_models.sh` fetches the hand landmarker, face landmarker and EfficientDet-Lite0 from Google (~31 MB) and unpacks the `.task` bundles; also two sample photos into `testimg/` |
| Camera check | `rpicam-hello --list-cameras` |
| Kiosk | `raspi-config`: boot to desktop with auto-login (B4), screen blanking off; installs `~/.config/autostart/pi-vision-lab.desktop` → `run.sh` |
| Headless VNC | Appends a kanshi profile so the virtual screen is 800×480 when no display is connected |

After the reboot the Pi logs in automatically, and about 20 s after power-on the app fills the screen.
Rajaram walks in a few seconds later, once his frames are loaded.

## Displays

- **Official 7" DSI touch display (original):** detected automatically (`display_auto_detect=1` in `/boot/firmware/config.txt`).
- **Touch Display 2:** add the overlay for your size to `/boot/firmware/config.txt`, for example `dtoverlay=vc4-kms-dsi-ili9881-7inch`, then reboot.
- **HDMI monitor:** plug in and boot; the app runs full-screen at the monitor's resolution.

## Kiosk control

`run.sh` keeps the app running: it restarts 3 s after any exit. Logs go to `~/.cache/pi_vision_lab.log`.

```bash
# stop the kiosk (e.g. to use the desktop)
pkill -f pi_ai_demo/run.sh; pkill -f "python -m app.main"
# start it again
~/pi_ai_demo/run.sh &
# run in a window instead (for development)
~/pi_ai_demo/run.sh --windowed
# disable autostart
rm ~/.config/autostart/pi-vision-lab.desktop
```

## Remote viewing (VNC)

Raspberry Pi OS ships **WayVNC**, which mirrors the active display. Enable it with `sudo raspi-config` →
Interface Options → VNC if it's off. Connect with RealVNC Viewer to `<pi-ip>:5900` and log in as the Pi user.
With no monitor attached, the kanshi profile makes the virtual screen 800×480, so you see the touch-display layout.

## Troubleshooting

| Symptom | Check |
|---|---|
| App doesn't start at boot | `cat ~/.cache/pi_vision_lab.log`; `ls ~/.config/autostart/`; is auto-login on (`raspi-config` → System → Boot / Auto Login → Desktop Autologin)? |
| Black screen, "no camera" | `rpicam-hello --list-cameras`; reseat the ribbon cable (contacts facing the board on a Pi 4) |
| `Illegal instruction` / SIGILL | Something imported `mediapipe`. It isn't used and doesn't run on a Pi 4; `pip uninstall mediapipe` |
| Low frame rate | `vcgencmd get_throttled` (under-voltage or heat); close other apps; check `top -H` for other processes |
| Cursor doesn't appear | Good, even light on the hand; keep it 0.5–1.5 m from the camera; palm facing the camera |
| Faces not found from far away | They are found, but it takes up to ~1 s while the detector scans its zoom tiles |
| Rajaram missing | `assets/presenter/clips.json` must exist; the log shows any loading error |
| QML errors | Run `./run.sh --windowed` from a terminal to see them directly |
