"""
Setup otomatis Tahap 5, 7, 8 (dan persiapan Tahap 6/9) untuk PacMan3D.

Yang dikerjakan script ini:
  - Tahap 5 : membuat /Game/Characters/Ghost/BP_Ghost (parent: Character)
              + komponen Static Mesh "GhostMesh" berisi Ghost_ORANGE,
              diskalakan otomatis agar pas di dalam kapsul.
  - Tahap 8 : Capsule Component -> Radius 78, Half Height 108.
  - Persiapan AI: Auto Possess AI = Placed in World or Spawned,
              AI Controller Class = AIController, hantu menghadap arah gerak.
  - Tahap 7 : memasang / menyesuaikan NavMeshBoundsVolume yang menyelimuti labirin
              di level /Game/LVL_PacMan.
  - Menaruh 4 hantu (Ghost_1..Ghost_4) di tengah labirin.
  - Bagian 3: komponen PawnSensing (sudut 170, hearing 0), komponen
              AttackCollider (Sphere, radius 120, overlap), dan variabel
              Integer "Lives" (default 3) di BP_ThirdPersonCharacter.

Yang TIDAK dikerjakan (harus dirangkai manual di editor, lihat panduan):
  - Tahap 4 : font WBP_HUD
  - Tahap 6 : Custom Event RandomRoam + AI MoveTo
  - Tahap 9 : Delay 5 detik di Event BeginPlay

Cara menjalankan (editor terbuka):
  Tools > Execute Python Script... > pilih file ini
  atau di Output Log (mode "Python"):
  py "D:/FILE KULIAH/TUGAS MATKUL/SEMESTER 5/Praktikum Pengembangan Game/PacMan3d-unrealengine/Scripts/setup_ghost.py"

Script aman dijalankan ulang: aset/aktor yang sudah ada dipakai ulang, bukan diduplikasi.
"""

import unreal

# ---------------------------------------------------------------- konfigurasi
GHOST_FOLDER = "/Game/Characters/Ghost"
GHOST_BP_NAME = "BP_Ghost"
GHOST_MESH_PATH = (
    "/Game/Characters/Ghost/pacman-ghost-orange-20261105T004040Z-1-001/"
    "pacman-ghost-orange/source/Ghost_ORANGE"
)
LEVEL_PATH = "/Game/LVL_PacMan"

CAPSULE_RADIUS = 78.0
CAPSULE_HALF_HEIGHT = 108.0
MESH_FILL = 0.95          # mesh mengisi 95% kapsul
GHOST_WALK_SPEED = 400.0
GHOST_COUNT = 4
GHOST_SPACING = 180.0
NAV_PADDING = 1.1         # NavMesh volume dibuat 10% lebih besar dari labirin

PERIPHERAL_VISION_ANGLE = 170.0   # setengah sudut pandang (180 = 360 derajat penuh)
ATTACK_RADIUS = 120.0             # sedikit lebih besar dari kapsul (R 78, HH 108)
PLAYER_BP_PATH = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
PLAYER_LIVES = 3

log = unreal.log
warn = unreal.log_warning


def subobject_object(sds_data, bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    if hasattr(lib, "get_object_for_blueprint"):
        return lib.get_object_for_blueprint(sds_data, bp)
    return lib.get_object(sds_data)


# ---------------------------------------------------------------- Tahap 5
def get_or_create_ghost_bp():
    full_path = f"{GHOST_FOLDER}/{GHOST_BP_NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(full_path):
        log(f"[Ghost] {full_path} sudah ada, dipakai ulang.")
        return unreal.EditorAssetLibrary.load_asset(full_path)

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Character)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        GHOST_BP_NAME, GHOST_FOLDER, unreal.Blueprint, factory
    )
    if bp is None:
        raise RuntimeError(f"Gagal membuat {full_path}")
    log(f"[Ghost] Membuat {full_path}")
    return bp


def get_or_add_component(bp, comp_class, name, attach_to_root=True):
    """Ambil komponen bertipe comp_class di BP; kalau belum ada, tambahkan."""
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)

    parent = handles[0]
    for h in handles:
        obj = subobject_object(lib.get_data(h), bp)
        if type(obj) is comp_class:
            return obj
        if attach_to_root and isinstance(obj, unreal.CapsuleComponent):
            parent = h

    params = unreal.AddNewSubobjectParams(
        parent_handle=parent, new_class=comp_class, blueprint_context=bp
    )
    new_handle, fail_reason = sds.add_new_subobject(params)
    if not lib.is_handle_valid(new_handle):
        raise RuntimeError(f"Gagal menambah {name}: {fail_reason}")
    sds.rename_subobject(new_handle, unreal.Text(name))
    log(f"[Ghost] Komponen {name} ditambahkan.")
    return subobject_object(lib.get_data(new_handle), bp)


def setup_ghost_mesh(bp, mesh):
    mesh_comp = get_or_add_component(bp, unreal.StaticMeshComponent, "GhostMesh")

    # Skala otomatis supaya mesh muat di kapsul (Tahap 5 + 8)
    bounds = mesh.get_bounds()
    o, e = bounds.origin, bounds.box_extent
    scale = MESH_FILL * min(
        CAPSULE_HALF_HEIGHT / max(e.z, 0.001),
        CAPSULE_RADIUS / max(e.x, e.y, 0.001),
    )
    # Taruh dasar mesh di dasar kapsul, center horizontal di tengah kapsul
    loc = unreal.Vector(
        -o.x * scale,
        -o.y * scale,
        -CAPSULE_HALF_HEIGHT - (o.z - e.z) * scale,
    )

    mesh_comp.set_editor_property("static_mesh", mesh)
    mesh_comp.set_editor_property("relative_scale3d", unreal.Vector(scale, scale, scale))
    mesh_comp.set_editor_property("relative_location", loc)
    # Tabrakan ditangani kapsul saja, supaya mesh tidak tersangkut dinding
    mesh_comp.set_collision_profile_name("NoCollision")
    log(f"[Ghost] Mesh scale = {scale:.3f}, location = {loc}")


def setup_pawn_sensing(bp):
    """Bagian 3 Tahap 1: penglihatan hantu."""
    ps = get_or_add_component(bp, unreal.PawnSensingComponent, "PawnSensing", attach_to_root=False)
    # Peripheral Vision Angle adalah setengah sudut; 170 = hampir 360 derajat
    ps.set_peripheral_vision_angle(PERIPHERAL_VISION_ANGLE)
    ps.set_editor_property("hearing_threshold", 0.0)
    ps.set_editor_property("los_hearing_threshold", 0.0)
    log(f"[Ghost] PawnSensing: angle={PERIPHERAL_VISION_ANGLE}, hearing=0")


def setup_attack_collider(bp):
    """Bagian 3 Tahap 5: zona serangan sedikit lebih besar dari hantu."""
    sphere = get_or_add_component(bp, unreal.SphereComponent, "AttackCollider")
    sphere.set_editor_property("sphere_radius", ATTACK_RADIUS)
    sphere.set_collision_profile_name("OverlapAllDynamic")
    sphere.set_editor_property("generate_overlap_events", True)
    log(f"[Ghost] AttackCollider radius={ATTACK_RADIUS}")


def setup_player_lives():
    """Bagian 3 Tahap 4: variabel Integer Lives di BP_ThirdPersonCharacter."""
    bp = unreal.EditorAssetLibrary.load_asset(PLAYER_BP_PATH)
    if bp is None:
        warn(f"[Lives] {PLAYER_BP_PATH} tidak ditemukan, dilewati.")
        return
    bel = unreal.BlueprintEditorLibrary
    int_type = bel.get_basic_type_by_name("int")
    if bel.add_member_variable(bp, "Lives", int_type):
        log("[Lives] Variabel Lives ditambahkan.")
    else:
        log("[Lives] Variabel Lives sudah ada.")
    bel.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("Lives", PLAYER_LIVES)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False)
    log(f"[Lives] Default Lives = {PLAYER_LIVES}")


def setup_ghost_defaults(bp):
    cdo = unreal.get_default_object(bp.generated_class())

    # Tahap 8: ukuran kapsul
    capsule = cdo.get_editor_property("capsule_component")
    capsule.set_editor_property("capsule_radius", CAPSULE_RADIUS)
    capsule.set_editor_property("capsule_half_height", CAPSULE_HALF_HEIGHT)

    # Supaya AI MoveTo bisa jalan: hantu harus dikuasai AIController
    cdo.set_editor_property("auto_possess_ai", unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    cdo.set_editor_property("ai_controller_class", unreal.AIController.static_class())

    # Hantu menghadap arah gerak
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("orient_rotation_to_movement", True)
    move.set_editor_property("max_walk_speed", GHOST_WALK_SPEED)
    log(f"[Ghost] Capsule R={CAPSULE_RADIUS} HH={CAPSULE_HALF_HEIGHT}, AI possess diset.")


def compile_and_save(bp):
    if hasattr(unreal, "BlueprintEditorLibrary"):
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False)


# ---------------------------------------------------------------- Tahap 7 + penempatan
def maze_bounds(actors):
    """Bounding box labirin. Utamakan mesh hasil Cube Grid (_GENERATED)."""
    sm_actors = [a for a in actors if isinstance(a, unreal.StaticMeshActor)]

    def mesh_path(a):
        sm = a.static_mesh_component.get_editor_property("static_mesh")
        return sm.get_path_name() if sm else ""

    maze = [a for a in sm_actors if "/_GENERATED/" in mesh_path(a)] or sm_actors
    if not maze:
        raise RuntimeError("Tidak ada StaticMeshActor di level, tidak bisa menghitung area labirin.")

    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for a in maze:
        origin, ext = a.get_actor_bounds(False)
        if max(ext.x, ext.y, ext.z) > 100000:   # abaikan objek raksasa (sky, dsb.)
            continue
        for i, (c, x) in enumerate(((origin.x, ext.x), (origin.y, ext.y), (origin.z, ext.z))):
            lo[i] = min(lo[i], c - x)
            hi[i] = max(hi[i], c + x)
    log(f"[Nav] Area labirin dari {len(maze)} aktor: min={lo} max={hi}")
    return lo, hi


def setup_nav_volume(eas, actors, lo, hi):
    center = unreal.Vector((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    size = [(hi[i] - lo[i]) * NAV_PADDING for i in range(3)]
    size[2] = max(size[2], 600.0)   # cukup tinggi untuk lantai + kapsul hantu

    vol = next((a for a in actors if isinstance(a, unreal.NavMeshBoundsVolume)), None)
    if vol is None:
        vol = eas.spawn_actor_from_class(unreal.NavMeshBoundsVolume, center)
        log("[Nav] NavMeshBoundsVolume baru dipasang.")
    else:
        log("[Nav] NavMeshBoundsVolume sudah ada, ukurannya disesuaikan.")

    # Brush default volume = kubus 200 x 200 x 200
    vol.set_actor_location(center, False, False)
    vol.set_actor_scale3d(unreal.Vector(size[0] / 200, size[1] / 200, size[2] / 200))
    vol.set_actor_label("NavMeshBounds_Maze")


def place_ghosts(eas, actors, bp, lo, hi):
    ghost_class = bp.generated_class()
    existing = [a for a in actors if a.get_class() == ghost_class]
    if existing:
        log(f"[Ghost] Sudah ada {len(existing)} hantu di level, tidak menambah lagi.")
        return

    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    z = lo[2] + CAPSULE_HALF_HEIGHT + 20
    start = -GHOST_SPACING * (GHOST_COUNT - 1) / 2
    for i in range(GHOST_COUNT):
        loc = unreal.Vector(cx + start + i * GHOST_SPACING, cy, z)
        g = eas.spawn_actor_from_class(ghost_class, loc)
        g.set_actor_label(f"Ghost_{i + 1}")
    log(f"[Ghost] {GHOST_COUNT} hantu ditaruh di sekitar ({cx:.0f}, {cy:.0f}). "
        "Geser ke kandang bila perlu.")


# ---------------------------------------------------------------- main
def main():
    mesh = unreal.EditorAssetLibrary.load_asset(GHOST_MESH_PATH)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Mesh hantu tidak ditemukan: {GHOST_MESH_PATH}")

    bp = get_or_create_ghost_bp()
    setup_ghost_mesh(bp, mesh)
    setup_pawn_sensing(bp)
    setup_attack_collider(bp)
    compile_and_save(bp)
    setup_ghost_defaults(bp)     # setelah compile, supaya CDO sudah terbaru
    compile_and_save(bp)
    setup_player_lives()

    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(LEVEL_PATH)
    actors = eas.get_all_level_actors()
    lo, hi = maze_bounds(actors)
    setup_nav_volume(eas, actors, lo, hi)
    place_ghosts(eas, actors, bp, lo, hi)
    les.save_current_level()

    log("[Setup] Selesai. Lanjutkan Tahap 4, 6, 9 secara manual (lihat panduan).")


main()
