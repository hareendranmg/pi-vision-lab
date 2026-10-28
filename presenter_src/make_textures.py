"""Build Rajaram's avatar textures from Rocketbox base textures and his photo.

    python3 make_textures.py

Body (Male_Adult_11): olive shirt -> light blue, jeans -> charcoal trousers,
arm skin -> his tone. Head (Male_Adult_14, already bald): skin -> his tone,
hair ring -> grey-white, then his face (with beard) warped onto the face area
using 478-point face-mesh landmarks found on both the photo and the texture
(landmarks come from the Pi's FaceTracker; see the .npy files).
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.spatial import Delaunay

HERE = Path(__file__).resolve().parent
R = HERE / "rajaram"
OUT = R / "Textures"

SHIRT_RGB = (172, 198, 232)    # pale blue, like the shirt in his photo
TROUSER_RGB = (58, 60, 66)     # charcoal
JAW = [234, 93, 132, 58, 172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323, 454]
CHEEKS = [50, 280, 101, 330]


def load_tga(p):
    return cv2.cvtColor(np.array(Image.open(p).convert("RGB")), cv2.COLOR_RGB2BGR)


def save_png(img, p):
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), img)


def pad(img, iters=12):
    """Bleed island colours into the empty background so texture filtering
    at UV seams never samples black (which shows up as dark seam lines)."""
    filled = img.max(2) > 12
    out = img.copy()
    for _ in range(iters):
        grown = cv2.dilate(out, np.ones((3, 3), np.uint8))
        newly = cv2.dilate(filled.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~filled
        out[newly] = grown[newly]
        filled |= newly
    return out


def brown_iris(img, centre=(538, 1907), radius=52):
    """Rocketbox's eyeball texture has grey-green irises; his are dark brown."""
    L = lab(img)
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    disc = ((xx - centre[0]) ** 2 + (yy - centre[1]) ** 2) < radius ** 2
    target = np.array([40.0, 136.0, 140.0])          # very dark brown in OpenCV Lab
    new = L.copy()
    new[..., 0] = np.where(disc, L[..., 0] * 0.32, L[..., 0])
    new[..., 1] = np.where(disc, target[1], L[..., 1])
    new[..., 2] = np.where(disc, target[2], L[..., 2])
    a = cv2.GaussianBlur(disc.astype(np.float32), (0, 0), 3)[..., None]
    return bgr(L * (1 - a) + new * a)


def lab(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)


def bgr(labimg):
    return cv2.cvtColor(np.clip(labimg, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def skin_mask(img):
    ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    m = cv2.inRange(ycc, (40, 135, 85), (255, 180, 135))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))


def transfer(img, mask, target_mean, target_std, strength=1.0):
    """Shift masked pixels' Lab statistics to the target (Reinhard colour transfer)."""
    L = lab(img)
    sel = mask > 0
    mu, sd = L[sel].mean(0), L[sel].std(0) + 1e-6
    out = (L - mu) / sd * (sd + (target_std - sd) * strength) + mu + (target_mean - mu) * strength
    a = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 3)[..., None]
    return bgr(L * (1 - a) + out * a)


def recolor(img, mask, rgb, detail=1.0):
    """Paint a flat colour but keep the fabric's folds (high-pass luminance)."""
    L = lab(img)
    lum = L[..., 0]
    hp = lum - cv2.GaussianBlur(lum, (0, 0), 12)
    shade = cv2.GaussianBlur(lum, (0, 0), 40)
    target = lab(np.uint8([[rgb[::-1]]]))[0, 0]
    sel = mask > 0
    rel = (shade - shade[sel].mean()) * 0.6
    new = np.dstack([target[0] + rel + hp * detail, np.full_like(lum, target[1]), np.full_like(lum, target[2])])
    a = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 2)[..., None]
    return bgr(L * (1 - a) + new * a)


def his_skin(photo, pts):
    """Lab mean/std of his cheek skin."""
    L = lab(photo)
    samples = []
    face_w = np.linalg.norm(pts[234] - pts[454])
    for i in CHEEKS:
        x, y = pts[i].astype(int)
        r = max(3, int(face_w * 0.04))
        samples.append(L[y - r:y + r, x - r:x + r].reshape(-1, 3))
    s = np.vstack(samples)
    return s.mean(0), s.std(0)


def body(photo, ppts):
    img = load_tga(HERE / "Male_Adult_11/Textures/m001_body_color.tga")
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    alive = (img.max(2) > 18).astype(np.uint8) * 255
    jeans = cv2.inRange(hsv, (92, 35, 40), (125, 255, 255))
    jeans = cv2.morphologyEx(jeans, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    h, w = img.shape[:2]
    yy = np.mgrid[0:h, 0:w][0] / h
    # The base shirt is olive (hue ~33) - distinct from the blue jeans, the
    # brown shoes (hue < 20) and skin - so colour alone finds every shirt
    # island, including the narrow side panels next to the shoes.
    olive = cv2.inRange(hsv, (21, 25, 4), (48, 255, 170))
    shirt = cv2.morphologyEx(olive & ~jeans, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    shirt = cv2.morphologyEx(shirt, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # Skin lives on the arm/hand islands only; brown shoes sit in the same colour range.
    skin = skin_mask(img) & ~shirt
    skin[yy > 0.66] &= (cv2.inRange(hsv, (0, 0, 120), (30, 255, 255))[yy > 0.66])
    out = recolor(img, shirt, SHIRT_RGB, detail=1.4)
    out = recolor(out, jeans, TROUSER_RGB, detail=0.9)
    m, s = his_skin(photo, ppts)
    out = transfer(out, skin, m, s, strength=0.9)
    save_png(pad(out), OUT / "body_color.png")
    masks = np.dstack([shirt, jeans, skin])
    save_png(masks, R / "debug_body_masks.png")
    return out


def head(photo, ppts, hpts):
    img = load_tga(HERE / "Male_Adult_14/Textures/m012_head_color.tga")
    h, w = img.shape[:2]
    m, s = his_skin(photo, ppts)
    face_h = np.linalg.norm(hpts[10] - hpts[152])

    # Hair ring: darker-than-skin pixels away from the face, above the ears.
    L = lab(img)
    skin_L = np.median(L[skin_mask(img) > 0][:, 0])
    alive = img.max(2) > 18
    face_hull = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(face_hull, cv2.convexHull(hpts.astype(np.int32)), 255)
    face_zone = cv2.dilate(face_hull, np.ones((int(face_h * 0.15),) * 2, np.uint8)) > 0
    hair = alive & (L[..., 0] < skin_L - 18) & ~face_zone & (np.mgrid[0:h, 0:w][0] < hpts[152][1])
    hair = cv2.morphologyEx(hair.astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

    skin_all = (alive.astype(np.uint8) * 255) & ~hair
    out = transfer(img, skin_all, m, s, strength=0.95)
    # Grey-white hair keeping strand texture.
    L2 = lab(out)
    grey = np.dstack([np.clip(118 + (L[..., 0] - L[..., 0][hair > 0].mean()) * 1.3, 60, 185),
                      np.full((h, w), 128.0), np.full((h, w), 126.0)])
    a = cv2.GaussianBlur(hair.astype(np.float32) / 255, (0, 0), 9)[..., None] * 0.9
    out = bgr(L2 * (1 - a) + grey * a)

    # Face: piecewise-affine warp of the photo onto the texture's face, plus a
    # band below the jaw so the beard continues onto the neck.
    jaw_c_p, jaw_c_h = ppts[JAW].mean(0), hpts[JAW].mean(0)
    ext_p = [ppts[i] + (ppts[i] - jaw_c_p) * 0.18 + [0, 0.10 * np.linalg.norm(ppts[10] - ppts[152])] for i in JAW]
    ext_h = [hpts[i] + (hpts[i] - jaw_c_h) * 0.18 + [0, 0.10 * face_h] for i in JAW]
    src = np.vstack([ppts, ext_p]).astype(np.float32)
    dst = np.vstack([hpts, ext_h]).astype(np.float32)
    warped = np.zeros_like(out)
    for tri in Delaunay(dst).simplices:
        ts, td = src[tri], dst[tri]
        x, y, ww, hh = cv2.boundingRect(td)
        if ww < 1 or hh < 1:
            continue
        mtx = cv2.getAffineTransform(ts, np.float32(td - [x, y]))
        patch = cv2.warpAffine(photo, mtx, (ww, hh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        tm = np.zeros((hh, ww), np.uint8)
        cv2.fillConvexPoly(tm, (td - [x, y]).astype(np.int32), 255)
        roi = warped[y:y + hh, x:x + ww]
        roi[tm > 0] = patch[tm > 0]
    mask = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(dst.astype(np.int32)), 255)
    mask = cv2.erode(mask, np.ones((int(face_h * 0.04),) * 2, np.uint8))
    x, y, ww, hh = cv2.boundingRect(mask)
    center = (x + ww // 2, y + hh // 2)
    out = cv2.seamlessClone(warped, out, mask, center, cv2.NORMAL_CLONE)
    L3 = lab(out)
    skin_now = (alive & (hair == 0) & (L3[..., 0] < 200)).astype(np.float32)
    L3[..., 0] -= 14 * cv2.GaussianBlur(skin_now, (0, 0), 6)
    out = brown_iris(bgr(L3))
    save_png(pad(out), OUT / "head_color.png")
    save_png(np.dstack([hair, mask, face_hull]), R / "debug_head_masks.png")
    return out


def main():
    photo = cv2.imread(str(R / "rajaram_front.jpg"))
    ppts = np.load(R / "photo_landmarks.npy")[:, :2]
    hpts = np.load(R / "head_landmarks.npy")[:, :2]
    body(photo, ppts)
    head(photo, ppts, hpts)
    print("textures written to", OUT)


if __name__ == "__main__":
    main()
