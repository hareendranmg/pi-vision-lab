#!/bin/sh
# One-shot installer for Pi Vision Lab on a Raspberry Pi 4/5 running
# Raspberry Pi OS (Debian 13 "trixie", 64-bit, desktop) with a camera attached.
#
#   git clone https://github.com/hareendranmg/pi-vision-lab.git ~/pi_ai_demo
#   cd ~/pi_ai_demo && ./setup.sh
#
# Safe to re-run. Uses sudo for apt and raspi-config only.
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"
step() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }

step "System packages (camera stack, Python venv)"
sudo apt-get update -q
sudo apt-get install -y -q python3-picamera2 python3-venv python3-pil curl rpicam-apps

step "Python environment (.venv, sees apt's picamera2/libcamera/numpy)"
[ -d .venv ] || python3 -m venv --system-site-packages .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

step "AI models and sample photos"
sh scripts/download_models.sh

step "Camera check"
if rpicam-hello --list-cameras 2>&1 | grep -q "Available cameras"; then
    rpicam-hello --list-cameras 2>&1 | sed -n '2,3p'
else
    echo "WARNING: no camera detected - check the ribbon cable (the app needs one)."
fi

step "Kiosk: desktop auto-login, no screen blanking, autostart"
sudo raspi-config nonint do_boot_behaviour B4   # boot to desktop, auto-login
sudo raspi-config nonint do_blanking 1          # never blank the screen
mkdir -p "$HOME/.config/autostart"
sed "s#@APP_DIR@#$APP_DIR#g" deploy/pi-vision-lab.desktop > "$HOME/.config/autostart/pi-vision-lab.desktop"
chmod +x run.sh scripts/*.sh

step "Headless VNC resolution (only applies when no display is connected)"
mkdir -p "$HOME/.config/kanshi"
if ! grep -q "profile headless" "$HOME/.config/kanshi/config" 2>/dev/null; then
    cat deploy/kanshi-headless.conf >> "$HOME/.config/kanshi/config"
fi

step "Done"
echo "Reboot to start the kiosk:  sudo reboot"
echo "Or try it now in a window:  ./run.sh --windowed"
