#!/bin/sh
# Download the AI models (all Apache-2.0, from Google) into models/ and unpack
# the MediaPipe .task bundles into the plain .tflite files the app loads.
set -e
cd "$(dirname "$0")/.."
mkdir -p models
B=https://storage.googleapis.com/mediapipe-models
get() { [ -s "models/$2" ] || { echo "  $2"; curl -sSfL --retry 3 -o "models/$2" "$1"; }; }

get "$B/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task" hand_landmarker.task
get "$B/face_landmarker/face_landmarker/float16/latest/face_landmarker.task" face_landmarker.task
# EfficientDet-Lite0 with built-in NMS and the COCO label map (Raspberry Pi example model).
get "https://storage.googleapis.com/download.tensorflow.org/models/tflite/task_library/object_detection/rpi/lite-model_efficientdet_lite0_detection_metadata_1.tflite" efficientdet_lite0_pp.tflite

for t in hand_landmarker face_landmarker; do
    mkdir -p "models/$t"
    python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "models/$t.task" "models/$t"
done

# Sample photos used by --fake-camera and the test tools.
mkdir -p testimg
[ -s testimg/hands.jpg ] || curl -sSfL -o testimg/hands.jpg https://storage.googleapis.com/mediapipe-tasks/hand_landmarker/woman_hands.jpg
[ -s testimg/face.png ] || curl -sSfL -o testimg/face.png https://storage.googleapis.com/mediapipe-assets/business-person.png
echo "Models ready in models/"
