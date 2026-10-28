"""Render the presenter's animation clips as transparent PNG frame sequences.

    blender -b -P render_presenter.py -- [--test] [--only clip,clip]

The presenter is Rajaram (used with his consent): a Rocketbox (MIT) hybrid of
Male_Adult_11's half-sleeve shirt body and Male_Adult_14's bald head, with
textures from make_textures.py (his face from a photo) and modelled
rectangular glasses. All clips share one camera and light rig so the app can
cut between them seamlessly.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "assets" / "presenter"
RES = (300, 540)
CLOSEUP = False

# The animations face the camera (-Y). He enters from screen-right walking
# left (yaw -90), turns left 90 deg to face the audience, and leaves by
# turning left again (now facing screen-right) and walking out (yaw +90).
# name: (animation file, yaw degrees, lock root in place, frames)
#   frames: "all", or (min, max) length of a seamless loop to search for.
# He stands at screen-right and the content is on the left, so while standing
# he's angled this many degrees towards screen-left (negative yaw), and the
# presenting gesture uses his right hand (towards screen-left).
ADDRESS = -15
CLIPS = {
    "idle":      ("m_idle_neutral_01", ADDRESS, False, (150, 240)),
    "talk1":     ("m_gestic_talk_neutral_01", ADDRESS, False, (150, 240)),
    "talk2":     ("m_gestic_talk_neutral_02", ADDRESS, False, (150, 240)),
    "excited":   ("m_gestic_talk_excited_01", ADDRESS, False, (120, 210)),
    "present":   ("m_gestic_presentation_right_01", ADDRESS, False, (120, 210)),
    "wave":      ("m_wave_01", ADDRESS, False, "all"),
    "walk_in":   ("m_walk_neutral_01", -90, True, "all"),
    "turn_in":   ("m_turn_left_90", -90 + ADDRESS, True, "all"),
    "turn_out":  ("m_turn_left_90", ADDRESS, True, "all"),
    "walk_out":  ("m_walk_neutral_01", 90, True, "all"),
}
LOOP_BONES = ["Bip01 Spine1", "Bip01 Neck", "Bip01 Head", "Bip01 L UpperArm", "Bip01 L Forearm",
              "Bip01 L Hand", "Bip01 R UpperArm", "Bip01 R Forearm", "Bip01 R Hand", "Bip01 Pelvis"]


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    if "--only" in a:
        only = a[a.index("--only") + 1].split(",")
    global CLOSEUP
    CLOSEUP = "--closeup" in a
    return "--test" in a or CLOSEUP, only


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.fps = 30
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.eevee.taa_render_samples = 32
    sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.37, 0.42, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.6

    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    sc.collection.objects.link(cam)
    cam.data.lens = 85
    cam.data.sensor_fit = "VERTICAL"
    cam.location = (0, -8.4, 1.0)
    look_at(cam, Vector((0, 0, 0.88)))
    sc.camera = cam
    if CLOSEUP:
        cam.location = (0, -1.6, 1.62)
        look_at(cam, Vector((0, 0, 1.6)))
        sc.render.resolution_x, sc.render.resolution_y = 600, 600

    def area(name, loc, energy, size, color=(1, 1, 1)):
        light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        light.data.energy, light.data.size, light.data.color = energy, size, color
        light.location = loc
        look_at(light, Vector((0, 0, 1.1)))
        sc.collection.objects.link(light)

    area("Key", (-2.5, -3.5, 3.0), 900, 2.5, (1.0, 0.96, 0.9))
    area("Fill", (3.0, -3.0, 1.6), 300, 3.0, (0.85, 0.9, 1.0))
    area("Rim", (1.5, 3.0, 2.8), 700, 1.5, (0.8, 0.9, 1.0))


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def _import(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    new = set(bpy.data.objects) - before
    arm = next(o for o in new if o.type == "ARMATURE")
    mesh = next(o for o in new if o.type == "MESH")
    for o in new:
        if o.type == "EMPTY":
            bpy.data.objects.remove(o)
    return arm, mesh


def _keep_material(mesh, keyword):
    """Delete the faces of `mesh` whose material name lacks `keyword`."""
    import bmesh
    idx = {i for i, s in enumerate(mesh.material_slots) if keyword in s.material.name}
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in idx], context="FACES")
    bm.to_mesh(mesh.data)
    bm.free()


def _texture(mat, path):
    img = bpy.data.images.load(str(path))
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    link = bsdf.inputs["Base Color"].links[0]
    link.from_node.image = img


def load_avatar():
    arm, body = _import(HERE / "Male_Adult_11" / "Male_Adult_11.fbx")
    arm14, head = _import(HERE / "Male_Adult_14" / "Male_Adult_14.fbx")
    _keep_material(body, "body")
    _keep_material(head, "head")
    # Re-bind the bald head to the half-sleeve body's skeleton (same Bip01 bone names).
    head.parent = arm
    for mod in head.modifiers:
        if mod.type == "ARMATURE":
            mod.object = arm
    bpy.data.objects.remove(arm14)
    tex = HERE / "rajaram" / "Textures"
    _texture(body.material_slots[0].material if "body" in body.material_slots[0].material.name
             else next(s.material for s in body.material_slots if "body" in s.material.name), tex / "body_color.png")
    _texture(next(s.material for s in head.material_slots if "head" in s.material.name), tex / "head_color.png")
    for m in bpy.data.materials:
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED"
    add_glasses(arm)
    return arm


def add_glasses(arm):
    """Rectangular metal-frame glasses, parented to the head bone."""
    import bmesh
    bpy.context.view_layer.update()
    pose = {b.name: arm.matrix_world @ b.head for b in arm.pose.bones}
    r_eye, l_eye = pose["Bip01 REye"], pose["Bip01 LEye"]
    centre = (r_eye + l_eye) / 2
    span = (l_eye - r_eye).length            # interpupillary distance
    lens_w, lens_h, bar = span * 0.82, span * 0.5, span * 0.03
    fwd = -0.55 * span                         # in front of the eyes (towards -Y, the camera)
    frame_mat = bpy.data.materials.new("glasses_frame")
    frame_mat.use_nodes = True
    bsdf = frame_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.055, 1)
    bsdf.inputs["Metallic"].default_value = 0.9
    bsdf.inputs["Roughness"].default_value = 0.25
    parts = []

    def box(name, size, loc, mat):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.active_object
        o.name = name
        o.scale = size
        o.data.materials.append(mat)
        parts.append(o)
        return o

    for side, eye in (("R", r_eye), ("L", l_eye)):
        c = Vector((eye.x, centre.y + fwd, eye.z - lens_h * 0.05))
        for dz in (lens_h / 2, -lens_h / 2):            # top and bottom rims
            box(f"rim_{side}", (lens_w + bar, bar, bar * (1.4 if dz > 0 else 0.9)), c + Vector((0, 0, dz)), frame_mat)
        for dx in (lens_w / 2, -lens_w / 2):            # side rims
            box(f"rim_{side}", (bar, bar, lens_h), c + Vector((dx, 0, 0)), frame_mat)
        # Temple arm from the outer rim back towards the ear.
        outer = c + Vector(((lens_w / 2) * (1 if eye.x > centre.x else -1), 0, lens_h * 0.35))
        box(f"temple_{side}", (bar * 0.8, span * 1.7, bar * 0.9), outer + Vector((0, span * 0.85, 0)), frame_mat)
    box("bridge", (span - lens_w + bar, bar, bar), Vector((centre.x, centre.y + fwd, centre.z + lens_h * 0.22)), frame_mat)

    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    glasses = bpy.context.active_object
    glasses.name = "Glasses"
    # Follow the head bone.
    world = glasses.matrix_world.copy()
    glasses.parent = arm
    glasses.parent_type = "BONE"
    glasses.parent_bone = "Bip01 Head"
    glasses.matrix_world = world
    return glasses


def load_driver(name):
    """Import an animation's own skeleton; it stays hidden and drives the avatar.

    Rocketbox animations are keyed on a T-pose rig while the avatar rests in an
    A-pose, so copying local bone rotations would leave the arms 45 degrees off.
    """
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(HERE / "anims" / f"{name}.fbx"))
    new = set(bpy.data.objects) - before
    src = next(o for o in new if o.type == "ARMATURE")
    for o in new:
        if o is not src:
            bpy.data.objects.remove(o)
    src.hide_render = True
    return src


def retarget(arm, src):
    """World-space retarget: each avatar bone copies its driver bone's world rotation."""
    for pb in arm.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        if pb.name not in src.pose.bones:
            continue
        c = pb.constraints.new("COPY_ROTATION")
        c.target, c.subtarget = src, pb.name
        c.target_space = c.owner_space = "WORLD"
        if pb.name == "Bip01 Pelvis":
            c = pb.constraints.new("COPY_LOCATION")
            c.target, c.subtarget = src, pb.name
            c.target_space = c.owner_space = "WORLD"


def find_loop(src, start, end, min_len, max_len):
    """Pick the window whose last pose best matches its first, for a seamless loop."""
    sc = bpy.context.scene
    poses = {}
    for f in range(start, end + 1):
        sc.frame_set(f)
        poses[f] = [(src.matrix_world @ src.pose.bones[b].matrix).to_quaternion() for b in LOOP_BONES]

    def dist(a, b):
        return sum(qa.rotation_difference(qb).angle for qa, qb in zip(poses[a], poses[b]))

    best = (float("inf"), start, min(end, start + max_len))
    for a in range(start, end - min_len + 1, 3):
        for b in range(a + min_len, min(end, a + max_len) + 1, 2):
            d = dist(a, b)
            if d < best[0]:
                best = (d, a, b)
    print(f"  loop {best[1]}-{best[2]} mismatch {best[0]:.3f} rad")
    return best[1], best[2]


def lock_in_place(src, start, end):
    """Pin the pelvis over the origin by counter-moving the driver skeleton.

    Pinned to (0, 0) rather than the first frame: clips start up to ~1 m off
    centre, and the yaw pivot would turn that into a sideways shift. Some
    clips carry their root motion on the object itself, so each frame's own
    object location is the base that gets corrected.
    """
    sc = bpy.context.scene
    pelvis = src.pose.bones["Bip01 Pelvis"]
    samples = []
    for f in range(start, end + 1):
        sc.frame_set(f)
        samples.append((f, src.location.copy(), (src.matrix_world @ pelvis.head).xy.copy()))
    for f, loc, p in samples:
        src.location = (loc.x - p.x, loc.y - p.y, loc.z)
        src.keyframe_insert("location", frame=f)


def main():
    test, only = args()
    setup_scene()
    arm = load_avatar()
    sc = bpy.context.scene
    manifest = {}
    for clip, (anim, yaw, in_place, span) in CLIPS.items():
        if only and clip not in only:
            continue
        src = load_driver(anim)
        retarget(arm, src)
        start, end = (int(v) for v in src.animation_data.action.frame_range)
        if in_place:
            lock_in_place(src, start, end)
        # Face the clip's direction by turning a parent; the clip keys its own root rotation.
        pivot = bpy.data.objects.new(f"yaw_{clip}", None)
        sc.collection.objects.link(pivot)
        pivot.rotation_euler.z = math.radians(yaw)
        src.parent = pivot
        if span != "all":
            start, end = find_loop(src, start, end, *span)
            end -= 1  # the matching frame is the next loop's first frame
        sc.frame_start, sc.frame_end = start, end
        manifest[clip] = end - start + 1
        out = OUT / clip
        out.mkdir(parents=True, exist_ok=True)
        frames = [start + (end - start) // 2] if test else range(start, end + 1)
        for f in frames:
            sc.frame_set(f)
            sc.render.filepath = str(out / (f"test" if test else f"{f - start:04d}"))
            bpy.ops.render.render(write_still=True)
        print(f"CLIP {clip}: {anim} frames {start}-{end} -> {out}")
        bpy.data.objects.remove(src)
        bpy.data.objects.remove(pivot)
    if not test:
        import json
        old = json.loads((OUT / "clips.json").read_text()) if (OUT / "clips.json").exists() else {}
        (OUT / "clips.json").write_text(json.dumps(old | {"fps": 30, "size": RES, "clips": old.get("clips", {}) | manifest}, indent=1))


if __name__ == "__main__":
    main()
