"""
Membersihkan model skin Pac-Man di Blender lalu mengekspor FBX siap-Unreal.

Jalankan (tanpa membuka jendela Blender), dari folder proyek:
  "D:/Blender 5.1.2/blender.exe" -b --disable-autoexec --factory-startup \
      --python Scripts/blender/export_skins.py -- <BlackMonster|LilEvil>

Input : SourceArt/Skins/<Skin>/source/<file>.blend   (file asli, tidak diubah)
Output: SourceArt/Skins/<Skin>/SK_<Skin>.blend       (versi bersih, untuk diedit lagi)
        SourceArt/Skins/<Skin>/SK_<Skin>.fbx         (diimpor ke Unreal)

Yang dilakukan:
  - hapus objek yang bukan bagian karakter (mis. 'Cube'),
  - terapkan semua modifier & shape key (pose diam), kecuali Armature,
  - mata/tanduk yang ditempel ke tulang (bone parent) diikat ulang dengan weight,
  - ukuran & titik pusat disamakan dengan Pac-Man Classic (TARGET_HEIGHT, CLASSIC_CENTER_UE_CM),
  - material procedural diganti warna polos bernama M_<Skin>_<Bagian>,
  - animasi yang dipakai diberi nama A_<Skin>_<Nama>, sisanya dibuang,
  - armature dinamai 'Armature' (supaya Unreal tidak menambah root bone ekstra).
"""

import os
import sys

import bpy
from mathutils import Matrix, Vector

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SKIN_ROOT = os.path.join(PROJECT, "SourceArt", "Skins")
# Tinggi model (meter; 1 m = 100 cm di Unreal). 1.935 m membuat radius bounds sama dengan
# Pac-Man Classic (/Game/PacMan/pacman_eat, radius 169.5 cm). Ukuran HARUS dibakar di sini,
# bukan lewat skala impor Unreal: skala impor tidak ikut diterapkan ke animasi yang sudah ada,
# sehingga model mengecil saat animasi diputar.
TARGET_HEIGHT = 1.935
# Pusat bounds Pac-Man Classic di ruang lokal mesh Unreal (cm), dari log import_skins.py.
# Komponen Mesh di BP karakter digeser/diputar supaya titik INI jatuh di tengah kapsul,
# jadi pusat skin harus berada di titik yang sama. Unreal (x, y, z) cm = Blender (x, -y, z) m * 100.
CLASSIC_CENTER_UE_CM = (0.0226, -6.213, 101.448)
TARGET_CENTER = Vector((CLASSIC_CENTER_UE_CM[0], -CLASSIC_CENTER_UE_CM[1], CLASSIC_CENTER_UE_CM[2])) / 100.0

SKINS = {
    "BlackMonster": {
        "source": "monstedr.blend",
        "delete": ["Cube"],
        "fallback_bone": "mouth.L",
        # nama material asli -> (bagian, warna dasar RGB, kekuatan emission)
        "materials": {
            "red monster": ("Body", (0.02, 0.02, 0.025), 0.0),
            "TEETH.003": ("Teeth", (1.0, 1.0, 1.0), 0.0),
            "Material.061": ("MouthInside", (0.0, 0.0, 0.0), 0.0),
            "EyeWhite.004": ("Eye", (1.0, 0.05, 0.02), 3.0),
            "Material.007": ("Pupil", (0.0, 0.0, 0.0), 0.0),
        },
        "no_material": ("Horn", (0.9, 0.85, 0.7), 0.0),
        "actions": {"Walk.006": "Walk", "walk strong big": "WalkStrong"},
    },
    "LilEvil": {
        "source": "lil evil.blend",
        "delete": [],
        "fallback_bone": "mouth.L",
        "materials": {
            "Material.001": ("Body", (0.8, 0.013, 0.0), 0.0),
            "TEETH.003": ("Teeth", (1.0, 1.0, 1.0), 0.0),
            "EyeWhite.003": ("Eye", (0.0, 0.0, 0.0), 0.0),
            "Material.004": ("Pupil", (0.0, 0.0, 0.0), 0.0),
            "Pacman Devil.001": ("Horn", (0.02, 0.02, 0.02), 0.0),
        },
        "no_material": ("Horn", (0.02, 0.02, 0.02), 0.0),
        "actions": {"Walk.002": "Walk"},
    },
}


def log(msg):
    print(f"[export_skins] {msg}", flush=True)


def action_fcurves(action):
    """F-curve dari action biasa maupun layered action (Blender 4.4+)."""
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    yield from bag.fcurves
    if hasattr(action, "fcurves"):
        yield from action.fcurves


def flat_material(name, color, emission):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.45
    if emission > 0:
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    mat.diffuse_color = (*color, 1.0)
    return mat


def main(skin):
    cfg = SKINS[skin]
    folder = os.path.join(SKIN_ROOT, skin)
    src = os.path.join(folder, "source", cfg["source"])
    try:
        bpy.ops.wm.open_mainfile(filepath=src, load_ui=False)
    except RuntimeError as err:
        # File tetap terbuka; Blender hanya melapor & membuang data rusak (mis. shape key yatim)
        if os.path.basename(bpy.data.filepath) != cfg["source"]:
            raise
        log(f"peringatan saat membuka {cfg['source']} (diabaikan): {str(err).splitlines()[0]}")
    scene = bpy.context.scene

    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    for name in cfg["delete"]:
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name])
    meshes = [o for o in scene.objects if o.type == "MESH" and o.parent == arm]
    for o in [o for o in scene.objects if o.type == "MESH" and o not in meshes]:
        log(f"hapus objek di luar karakter: {o.name}")
        bpy.data.objects.remove(o)

    # --- 1. bekukan geometri dalam pose diam (modifier + shape key)
    arm.data.pose_position = "REST"
    info = {}
    for o in meshes:
        info[o.name] = {
            "bone": o.parent_bone if o.parent_type == "BONE" else "",
            "skinned": any(m.type == "ARMATURE" for m in o.modifiers),
        }
        for m in o.modifiers:
            if m.type == "ARMATURE":
                m.show_viewport = False
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        world = o.matrix_world.copy()
        new_mesh = bpy.data.meshes.new_from_object(
            o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        o.modifiers.clear()
        if o.data.shape_keys:
            o.shape_key_clear()
        o.data = new_mesh
        o.parent = None
        o.matrix_world = world
        o.data.transform(o.matrix_world)       # terapkan transform ke vertex
        o.matrix_world = Matrix.Identity(4)

    # --- 2. normalkan ukuran: tinggi 1 m, pusat di origin
    pts = [v.co for o in meshes for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    factor = TARGET_HEIGHT / (hi.z - lo.z)
    fix = (Matrix.Translation(TARGET_CENTER) @ Matrix.Scale(factor, 4)
           @ Matrix.Translation(-(lo + hi) / 2))
    for o in meshes:
        o.data.transform(fix)
    arm_scale = arm.matrix_world.to_scale()
    bone_scale = factor * (sum(arm_scale) / 3)   # skala lokasi pose bone ikut berubah
    arm_world = fix @ arm.matrix_world
    arm.data.transform(arm_world)
    arm.matrix_world = Matrix.Identity(4)
    arm.data.pose_position = "POSE"
    log(f"tinggi asli {hi.z - lo.z:.3f} m -> {TARGET_HEIGHT} m (faktor {factor:.4f})")

    # --- 3. ikat semua mesh ke armature dengan weight
    bone_names = {b.name for b in arm.data.bones}
    for o in meshes:
        weighted = any(len(v.groups) for v in o.data.vertices)
        if not info[o.name]["skinned"] or not weighted:
            bone = info[o.name]["bone"]
            if bone not in bone_names:
                bone = cfg["fallback_bone"]
            o.vertex_groups.clear()
            vg = o.vertex_groups.new(name=bone)
            vg.add(range(len(o.data.vertices)), 1.0, "REPLACE")
            log(f"{o.name}: diikat penuh ke tulang '{bone}'")
        o.parent = arm
        o.matrix_parent_inverse = Matrix.Identity(4)
        mod = o.modifiers.new("Armature", "ARMATURE")
        mod.object = arm

    # --- 4. material warna polos
    made = {}

    def get_mat(part, color, emission):
        key = f"M_{skin}_{part}"
        if key not in made:
            made[key] = flat_material(key, color, emission)
        return made[key]

    for o in meshes:
        if not o.data.materials:
            o.data.materials.append(get_mat(*cfg["no_material"]))
            continue
        for i, m in enumerate(o.data.materials):
            part = cfg["materials"].get(m.name if m else "", None) or cfg["no_material"]
            o.data.materials[i] = get_mat(*part)

    # --- 5. animasi
    keep = {}
    for old, new in cfg["actions"].items():
        act = bpy.data.actions.get(old)
        if act:
            act.name = f"A_{skin}_{new}"
            act.use_fake_user = True
            keep[act.name] = act
    for act in list(bpy.data.actions):
        if act.name not in keep:
            bpy.data.actions.remove(act)
    for act in keep.values():
        for fc in action_fcurves(act):
            if fc.data_path.endswith(".location") or fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.co.y *= bone_scale
                    kp.handle_left.y *= bone_scale
                    kp.handle_right.y *= bone_scale
    ad = arm.animation_data or arm.animation_data_create()
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    first = next(iter(keep.values()), None)
    if first:
        ad.action = first
        if hasattr(ad, "action_slot") and first.slots:
            ad.action_slot = first.slots[0]
        scene.frame_start, scene.frame_end = (int(f) for f in first.frame_range)
    log(f"animasi: {list(keep)}")

    # --- 6. rapikan nama & simpan
    arm.name = "Armature"
    arm.data.name = f"SKEL_{skin}"
    for i, o in enumerate(meshes):
        o.name = f"SK_{skin}_{i}"
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(folder, f"SK_{skin}.blend"), compress=True)

    for o in scene.objects:
        o.select_set(o is arm or o in meshes)
    bpy.context.view_layer.objects.active = arm
    fbx = os.path.join(folder, f"SK_{skin}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx, use_selection=True, object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z", axis_up="Y", mesh_smooth_type="FACE",
        use_mesh_modifiers=True, add_leaf_bones=False,
        primary_bone_axis="Y", secondary_bone_axis="X", armature_nodetype="NULL",
        use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=True,
        bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
        path_mode="AUTO")
    log(f"SELESAI {skin}: {fbx}")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(SKINS)
    for name in args:
        main(name)
