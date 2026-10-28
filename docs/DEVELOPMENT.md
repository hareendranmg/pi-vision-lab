# Development

## Working from a PC

Edit on your PC, then sync to the Pi and restart the app. The `run.sh` watchdog relaunches it in about 3 s:

```bash
PI=pi@192.168.10.17
rsync -a --exclude __pycache__ app qml assets run.sh $PI:pi_ai_demo/
ssh $PI 'pkill -f "^\.venv/bin/python -m app\.main"'
ssh $PI 'tail -f ~/.cache/pi_vision_lab.log'
```

## Remote control and screenshots

The app listens on a local Unix socket, `/tmp/pi_vision_lab.sock` (`app/control.py`, owner-only). `tools/ctl.py` sends
commands, one per argument:

```bash
python3 tools/ctl.py "screen face" "effect crown" "state"
python3 tools/ctl.py "tap 0.27 0.5"          # tap at normalised window coordinates
python3 tools/ctl.py "frame /tmp/raw.jpg"    # raw camera frame
WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000 grim /tmp/screen.png   # exactly what's on the display
```

| Command | Effect |
|---|---|
| `screen <home\|objects\|face\|color>` | switch screen |
| `effect <masquerade\|crown\|shades\|glam\|iceeyes\|mesh\|none>` | Face Magic effect |
| `tap <x> <y>` | press and release at normalised coordinates (the same path as touch) |
| `shot <png>` | grab the app window |
| `frame <jpg>` | save the un-mirrored camera frame |
| `state` | JSON of the latest vision state |

## Running without a camera or display

```bash
# Loop a still photo instead of the camera, in a window
.venv/bin/python -m app.main --windowed --fake-camera testimg/face.png
# Headless: cycle through every screen and save screenshots
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  .venv/bin/python -m app.main --fake-camera testimg/face.png --shots /tmp/shots
```

## Test tools

| Tool | Purpose |
|---|---|
| `tools/test_vision.py img…` | Run hands, faces and objects on stills, print timings, save annotated copies |
| `tools/test_fx.py out.jpg img…` | Render every Face Magic effect on stills into one contact sheet |
| `tools/face_landmarks.py img out.npy` | Save 478 face-mesh landmarks (used by the presenter pipeline) |
| `tools/ctl.py cmd…` | Remote-control client (above) |

## Code tour

```
app/
  main.py         args, Qt app, QML engine, wiring, --shots mode
  engine.py       VisionWorker: camera, crop, models per screen, overlays, state
  vision/common.py  anchors, SSD decode + weighted NMS, letterbox, rotated ROI crop
  vision/hands.py   palm detection + 21-point landmarks with tracking
  vision/faces.py   face detection (tiled search) + 478-point mesh + expressions
  vision/objects.py EfficientDet-Lite0 (post-processed export)
  gesture.py      One Euro cursor, debounced pinch, fist hold, pose names
  face_fx.py      Face Magic effects
  color.py        colour naming
  backend.py      Backend QObject (QML properties, mouse injection), CameraView
  frameitem.py    GPU texture QQuickItem
  presenter.py    clip preload/player, choreography state machine, PresenterView
  commentary.py   what the presenter says
  control.py      test-control socket
qml/
  Main.qml        window, camera background, screen loader, presenter, air cursor
  screens/        HomeScreen, ObjectsScreen, FaceScreen, ColorScreen
  components/     Tile, PillButton, AirCursor, Presenter (+ bubble), TopBar, Icon, …
```

## Common changes

- **New Face Magic effect:** add a branch in `FaceFx.draw()` (`app/face_fx.py`), add the name to `EFFECTS`, add a pill in `qml/screens/FaceScreen.qml` and a line in `EFFECT` (`app/commentary.py`). Preview it with `tools/test_fx.py`.
- **New photo prop:** add a transparent PNG to `assets/`, record its anchor points in `assets/assets.json`, and the licence in `assets/CREDITS.md`.
- **Gesture tuning:** the thresholds are constants at the top of `app/gesture.py` (`PINCH_DOWN/UP`, `ACTIVE`, `FIST_HOLD_S`, …).
- **Presenter placement or size:** `HOME_X`, `HEIGHT_FRAC` and `LEAVE_AFTER_S` in `app/presenter.py`.
- **Inference threads:** environment variable `PIV_THREADS` (default 3).

## Branches

`main` is tested, deployable code. `development` is the integration branch. Do feature work on branches from
`development`, merge it back through pull requests, and promote `development` to `main` after testing on a Pi.
