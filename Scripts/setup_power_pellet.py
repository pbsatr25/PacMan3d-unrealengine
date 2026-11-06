"""
Setup otomatis bagian 6 (Power Pellet & Scared Mode) untuk PacMan3D.

Yang dikerjakan script ini:
  - Tahap 1 : menduplikat /Game/PelletPickUps/BP_Food menjadi BP_PowerPellet
              dan memperbesar Static Mesh + Sphere trigger-nya.
              (Logika overlap & skor dari BP_Food ikut terbawa.)
  - Tahap 2 : variabel Boolean "IsScared" (default False) di BP_Ghost.
  - Tahap 3 : material biru MI_Ghost_Scared (duplikat material tubuh hantu,
              DiffuseColor diganti biru) + Game Mode Override di LVL_PacMan
              diset ke BP_ThirdPersonGameMode.
  - Mencetak index material tubuh hantu di Output Log (dipakai di Set Material).

Yang TIDAK dikerjakan (node graph, lihat panduan):
  - Event Flashing, Activate Scared Mode, Branch IsScared, Random Delay.
  - Menaruh BP_PowerPellet di level.

Jalankan: Tools > Execute Python Script... > pilih file ini.
Aman dijalankan ulang.
"""

import unreal

FOOD_BP = "/Game/PelletPickUps/BP_Food"
POWER_BP = "/Game/PelletPickUps/BP_PowerPellet"
POWER_SCALE = 2.5

GHOST_BP = "/Game/Characters/Ghost/BP_Ghost"
GHOST_MESH = (
    "/Game/Characters/Ghost/pacman-ghost-orange-20261105T004040Z-1-001/"
    "pacman-ghost-orange/source/Ghost_ORANGE"
)
SCARED_MAT = "/Game/Characters/Ghost/MI_Ghost_Scared"
SCARED_COLOR = unreal.LinearColor(0.02, 0.08, 1.0, 1.0)

GAME_MODE_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode"
LEVEL_PATH = "/Game/LVL_PacMan"

EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
MEL = unreal.MaterialEditingLibrary
log = unreal.log
warn = unreal.log_warning


def subobject_object(data, bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    if hasattr(lib, "get_object_for_blueprint"):
        return lib.get_object_for_blueprint(data, bp)
    return lib.get_object(data)


def bp_components(bp):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        obj = subobject_object(lib.get_data(h), bp)
        if isinstance(obj, unreal.ActorComponent):
            yield obj


def save(asset):
    EAL.save_loaded_asset(asset, only_if_is_dirty=False)


# ---------------------------------------------------------------- Tahap 1
def setup_power_pellet():
    if EAL.does_asset_exist(POWER_BP):
        log(f"[Power] {POWER_BP} sudah ada, ukuran tidak diubah lagi.")
        return
    bp = EAL.duplicate_asset(FOOD_BP, POWER_BP)
    if bp is None:
        raise RuntimeError(f"Gagal menduplikat {FOOD_BP}")

    scaled = []
    for comp in bp_components(bp):
        if isinstance(comp, (unreal.StaticMeshComponent, unreal.SphereComponent)):
            s = comp.get_editor_property("relative_scale3d")
            comp.set_editor_property(
                "relative_scale3d",
                unreal.Vector(s.x * POWER_SCALE, s.y * POWER_SCALE, s.z * POWER_SCALE),
            )
            scaled.append(comp.get_name())
    BEL.compile_blueprint(bp)
    save(bp)
    log(f"[Power] BP_PowerPellet dibuat, skala x{POWER_SCALE}: {scaled}")


# ---------------------------------------------------------------- Tahap 2
def setup_is_scared():
    bp = EAL.load_asset(GHOST_BP)
    if bp is None:
        raise RuntimeError(f"{GHOST_BP} tidak ada. Jalankan setup_ghost.py dulu.")
    if BEL.add_member_variable(bp, "IsScared", BEL.get_basic_type_by_name("bool")):
        log("[Ghost] Variabel IsScared ditambahkan.")
    else:
        log("[Ghost] Variabel IsScared sudah ada.")
    BEL.compile_blueprint(bp)
    unreal.get_default_object(bp.generated_class()).set_editor_property("IsScared", False)
    save(bp)


# ---------------------------------------------------------------- Tahap 3 (material)
def colorfulness(c):
    return max(c.r, c.g, c.b) - min(c.r, c.g, c.b)


def setup_scared_material():
    mesh = EAL.load_asset(GHOST_MESH)
    slots = mesh.get_editor_property("static_materials")

    # Tubuh = slot dengan warna paling "berwarna" (oranye), mata = putih/hitam
    best_idx, best_score, body_mat = 0, -1.0, None
    for i, slot in enumerate(slots):
        mat = slot.get_editor_property("material_interface")
        color = None
        if isinstance(mat, unreal.MaterialInstanceConstant):
            color = MEL.get_material_instance_vector_parameter_value(mat, "DiffuseColor")
        score = colorfulness(color) if color else 0.0
        log(f"[Material] Index {i}: {mat.get_name() if mat else None}, DiffuseColor={color}")
        if score > best_score:
            best_idx, best_score, body_mat = i, score, mat
    log(f"[Material] >>> Tubuh hantu = Element Index {best_idx} ({body_mat.get_name()}). "
        "Pakai index ini di node Set Material.")

    if EAL.does_asset_exist(SCARED_MAT):
        log(f"[Material] {SCARED_MAT} sudah ada.")
        return
    mi = EAL.duplicate_asset(body_mat.get_path_name().split(".")[0], SCARED_MAT)
    MEL.set_material_instance_vector_parameter_value(mi, "DiffuseColor", SCARED_COLOR)
    MEL.set_material_instance_vector_parameter_value(mi, "AmbientColor", SCARED_COLOR)
    MEL.update_material_instance(mi)
    save(mi)
    log(f"[Material] {SCARED_MAT} (biru) dibuat.")


# ---------------------------------------------------------------- Tahap 3 (World Settings)
def setup_game_mode_override():
    gm = EAL.load_asset(GAME_MODE_BP)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(LEVEL_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ws = world.get_world_settings()
    ws.set_editor_property("default_game_mode", gm.generated_class())
    les.save_current_level()
    log("[GameMode] LVL_PacMan GameMode Override = BP_ThirdPersonGameMode")


def main():
    setup_power_pellet()
    setup_is_scared()
    setup_scared_material()
    setup_game_mode_override()
    log("[Setup] Bagian 6 selesai. Lanjutkan node graph secara manual (lihat panduan).")


main()
