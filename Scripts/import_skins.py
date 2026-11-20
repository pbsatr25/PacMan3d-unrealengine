"""
Mengimpor skin Pac-Man (hasil Scripts/blender/export_skins.py) ke Unreal.

  SourceArt/Skins/<Skin>/SK_<Skin>.fbx  ->  /Game/PacMan/Skins/<Skin>/
      SK_<Skin>          Skeletal Mesh
      SKEL_<Skin>        Skeleton
      A_<Skin>_Walk ...  Animation Sequence
      M_<Skin>_...       Material (warna polos dari Blender)

Ukuran sudah dibakar di FBX (sama dengan Pac-Man Classic), jadi impor selalu skala 1.
Skala impor Unreal sengaja TIDAK dipakai: skala itu tidak ikut ke animasi yang
sudah ada, sehingga model mengecil saat animasi diputar.

Aman dijalankan ulang: FBX diimpor ke folder sementara, lalu aset lama di folder
tujuan digantikan lewat 'consolidate' (semua referensi, mis. node di
BP_ThirdPersonCharacter, otomatis pindah ke aset baru), baru diberi nama final.

Jalankan: Tools > Execute Python Script... > pilih file ini.
"""

import os
import re

import unreal

SKINS = ["BlackMonster", "LilEvil"]
CLASSIC_MESH = "/Game/PacMan/pacman_eat"
DEST_ROOT = "/Game/PacMan/Skins"

EAL = unreal.EditorAssetLibrary
log = unreal.log
warn = unreal.log_warning

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())


def make_pipeline():
    p = unreal.InterchangeGenericAssetsPipeline()
    p.set_editor_property("import_offset_uniform_scale", 1.0)
    common = p.get_editor_property("common_meshes_properties")
    common.set_editor_property("force_all_mesh_as_type", unreal.InterchangeForceMeshType.IFMT_SKELETAL_MESH)
    mesh = p.get_editor_property("mesh_pipeline")
    mesh.set_editor_property("import_static_meshes", False)
    mesh.set_editor_property("import_skeletal_meshes", True)
    mesh.set_editor_property("create_physics_asset", False)
    mesh.set_editor_property("import_morph_targets", False)
    p.get_editor_property("animation_pipeline").set_editor_property("import_animations", True)
    p.get_editor_property("material_pipeline").set_editor_property("import_materials", True)
    return p


def import_fbx(fbx, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    stack = unreal.InterchangePipelineStackOverride()
    stack.add_pipeline(make_pipeline())
    task.set_editor_property("options", stack)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])


def assets_in(folder):
    if not EAL.does_directory_exist(folder):
        return []
    out = []
    for p in EAL.list_assets(folder, recursive=False):
        a = EAL.load_asset(p.split(".")[0])
        if a is not None:
            out.append(a)
    return out


def path_of(asset):
    return asset.get_path_name().split(".")[0]


def final_name(skin, asset, anim_count):
    """Nama final aset, atau None kalau aset tidak dipakai (dihapus)."""
    name = asset.get_name()
    if isinstance(asset, unreal.SkeletalMesh):
        return f"SK_{skin}"
    if isinstance(asset, unreal.Skeleton):
        return f"SKEL_{skin}"
    if isinstance(asset, unreal.AnimSequence):
        m = re.search(rf"A_{skin}_([A-Za-z0-9]+)$", name)
        if m:
            return f"A_{skin}_{m.group(1)}"
        return f"A_{skin}_Walk" if anim_count == 1 else name
    if isinstance(asset, unreal.MaterialInterface):
        return name
    return None  # PhysicsAsset, redirector, dll.


ORDER = [unreal.AnimSequence, unreal.SkeletalMesh, unreal.MaterialInterface, unreal.Skeleton]


def import_skin(skin, classic):
    fbx = os.path.join(PROJECT, "SourceArt", "Skins", skin, f"SK_{skin}.fbx")
    if not os.path.isfile(fbx):
        warn(f"[Skin] {fbx} tidak ada. Jalankan export_skins.py di Blender dulu.")
        return
    dest = f"{DEST_ROOT}/{skin}"
    tmp = f"{DEST_ROOT}/_Import_{skin}"
    if EAL.does_directory_exist(tmp):
        EAL.delete_directory(tmp)

    import_fbx(fbx, tmp)
    new_assets = assets_in(tmp)
    if not any(isinstance(a, unreal.SkeletalMesh) for a in new_assets):
        raise RuntimeError(f"Impor {skin} gagal: tidak ada Skeletal Mesh. Cek Output Log.")
    new_anims = sum(isinstance(a, unreal.AnimSequence) for a in new_assets)
    old_anims = sum(isinstance(a, unreal.AnimSequence) for a in assets_in(dest))

    # kelompokkan aset lama di folder tujuan menurut nama finalnya
    old_by_name = {}
    for a in assets_in(dest):
        fn = final_name(skin, a, old_anims)
        if fn:
            old_by_name.setdefault((fn, a.get_class().get_name()), []).append(a)

    for cls in ORDER:
        for a in [x for x in new_assets if isinstance(x, cls)]:
            fn = final_name(skin, a, new_anims)
            olds = old_by_name.pop((fn, a.get_class().get_name()), [])
            if olds:
                # referensi ke aset lama (mis. default node di BP) dipindah ke aset baru
                EAL.consolidate_assets(a, olds)
                log(f"[Skin]    {fn}: {len(olds)} aset lama digantikan (referensi dipertahankan)")
            target = f"{dest}/{fn}"
            if EAL.does_asset_exist(target):
                EAL.delete_asset(target)
            EAL.rename_asset(path_of(a), target)

    # sisa aset lama yang tidak punya pengganti + isi folder sementara
    for (fn, _), olds in old_by_name.items():
        for a in olds:
            warn(f"[Skin]    aset lama tanpa pengganti dibiarkan: {a.get_name()}")
    # simpan semua yang berubah (aset baru + paket yang referensinya dipindah, mis. BP karakter)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
    EAL.save_directory(dest, only_if_is_dirty=False, recursive=True)
    EAL.delete_directory(tmp)   # sisa redirector folder sementara

    sk = EAL.load_asset(f"{dest}/SK_{skin}")
    r = sk.get_bounds().sphere_radius
    ratio = r / classic.get_bounds().sphere_radius if classic else 1.0
    log(f"[Skin] {skin}: radius {r:.1f} cm = {ratio:.3f} x Classic")
    if classic:
        o, co = sk.get_bounds().origin, classic.get_bounds().origin
        off = unreal.Vector(o.x - co.x, o.y - co.y, o.z - co.z)
        log(f"[Skin] {skin}: pusat {o} vs Classic {co} -> selisih {off}")
        if max(abs(off.x), abs(off.y), abs(off.z)) > 5.0:
            warn(f"[Skin] {skin}: pusat bergeser >5 cm dari Classic. Kirim baris ini untuk dikoreksi "
                 "(CLASSIC_CENTER_UE_CM di export_skins.py).")
    if abs(ratio - 1.0) > 0.03:
        warn(f"[Skin] {skin}: ukuran beda {ratio:.3f}x dari Classic. Ubah TARGET_HEIGHT di "
             f"export_skins.py menjadi {1.935 / ratio:.3f}, ekspor ulang, lalu impor lagi.")
    for a in sorted(assets_in(dest), key=lambda x: x.get_class().get_name()):
        log(f"[Skin]    {a.get_class().get_name():<26} {a.get_name()}")


def unlock_referencers():
    """File dari Git LFS 'lockable' bisa read-only; buka supaya referensinya bisa disimpan."""
    import stat
    for rel in ("Content/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset",
                "Content/UI/Widgets/WBP_Customize.uasset"):
        full = os.path.join(PROJECT, rel)
        if os.path.isfile(full) and not os.access(full, os.W_OK):
            os.chmod(full, stat.S_IWRITE | stat.S_IREAD)
            log(f"[Skin] Atribut read-only dilepas: {rel}")


def main():
    unlock_referencers()
    classic = EAL.load_asset(CLASSIC_MESH)
    if classic:
        log(f"[Skin] Pac-Man Classic: radius {classic.get_bounds().sphere_radius:.1f} cm")
    for skin in SKINS:
        import_skin(skin, classic)
    log("[Setup] Impor skin selesai. Cek /Game/PacMan/Skins/ di Content Browser.")


main()
