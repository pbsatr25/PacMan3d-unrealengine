"""
Membuat Level 2 dan Level 3 (LVL_PacMan_02, LVL_PacMan_03) dari LVL_PacMan.

Cara kerja:
  1. Menduplikat /Game/LVL_PacMan, sehingga Level Blueprint (HUD), GameMode
     Override, cahaya, langit, NavMeshBoundsVolume, PlayerStart dan hantu ikut.
  2. Di level hasil duplikat:
     - dinding Cube Grid lama + semua pellet dihapus,
     - lantai diganti material gelap polos (bukan gambar labirin level 1),
     - dinding baru dibangun dari denah di maze_layouts.py dengan warna neon
       berbeda (Level 2 hijau, Level 3 merah),
     - pellet & power pellet ditaruh ulang, hantu dipindah ke kandang baru,
       PlayerStart dipindah, kecepatan hantu dinaikkan sesuai level.
  3. LVL_PacMan (level 1) TIDAK diubah sama sekali.

Material baru (di /Game/LevelPrototyping/Materials/):
  MI_Wall_LVL_PacMan_02 / _03 dan MI_Floor_LVL_PacMan_02 / _03
  (Material Instance dari M_Wall_Blue, hanya warnanya yang diganti).

Jalankan: Tools > Execute Python Script... > pilih file ini.
Level yang sudah ada dilewati. Untuk membangun ulang, hapus map-nya dulu di
Content Browser, atau ubah REBUILD_EXISTING = True.
"""

import os
import statistics
import sys

import unreal

# maze_layouts.py ada di folder yang sama dengan script ini
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Scripts")
if _here not in sys.path:
    sys.path.insert(0, _here)
sys.dont_write_bytecode = True   # jangan buat folder __pycache__ di Scripts/
import importlib
import maze_layouts
importlib.reload(maze_layouts)

SOURCE_LEVEL = "/Game/LVL_PacMan"
LEVEL_FOLDER = "/Game"
MAT_FOLDER = "/Game/LevelPrototyping/Materials"
WALL_PARENT = "/Game/LevelPrototyping/Materials/M_Wall_Blue"
CUBE_MESH = "/Engine/BasicShapes/Cube"          # kubus 100 x 100 x 100, pivot di tengah
FOOD_BP = "/Game/PelletPickUps/BP_Food"
POWER_BP = "/Game/PelletPickUps/BP_PowerPellet"
REBUILD_EXISTING = False
MAZE_TAG = "PacMaze"

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
log = unreal.log
warn = unreal.log_warning


# ---------------------------------------------------------------- material
def make_color_instance(name, color, glow=True):
    path = f"{MAT_FOLDER}/{name}"
    if EAL.does_asset_exist(path):
        mi = EAL.load_asset(path)
    else:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, MAT_FOLDER, unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, EAL.load_asset(WALL_PARENT))

    parent = EAL.load_asset(WALL_PARENT)
    vec_names = MEL.get_vector_parameter_names(parent)
    if not vec_names:
        warn(f"[Mat] {WALL_PARENT} tidak punya Vector Parameter; warna {name} tidak bisa diubah.")
    lc = unreal.LinearColor(color[0], color[1], color[2], 1.0)
    for pname in vec_names:
        MEL.set_material_instance_vector_parameter_value(mi, pname, lc)
    if not glow:
        for pname in MEL.get_scalar_parameter_names(parent):
            if "emiss" in str(pname).lower() or "glow" in str(pname).lower():
                MEL.set_material_instance_scalar_parameter_value(mi, pname, 0.0)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, only_if_is_dirty=False)
    log(f"[Mat] {name}: parameter {list(map(str, vec_names))} = {color}")
    return mi


# ---------------------------------------------------------------- helpers
def mesh_path(actor):
    if not isinstance(actor, unreal.StaticMeshActor):
        return ""
    sm = actor.static_mesh_component.get_editor_property("static_mesh")
    return sm.get_path_name() if sm else ""


def is_instance_of(actor, bp_path):
    if not EAL.does_asset_exist(bp_path):
        return False
    return actor.get_class() == EAL.load_asset(bp_path).generated_class()


def tag(actor, folder, label):
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.set_editor_property("tags", [unreal.Name(MAZE_TAG)])


# ---------------------------------------------------------------- satu level
def build_level(name, cfg, eas, les):
    grid = cfg["grid"]
    level_path = f"{LEVEL_FOLDER}/{name}"

    if EAL.does_asset_exist(level_path):
        if not REBUILD_EXISTING:
            log(f"[Level] {name} sudah ada, dilewati (REBUILD_EXISTING = False).")
            return
        les.load_level(level_path)
    else:
        # Level baru dengan LVL_PacMan sebagai template: Unreal memuat template ke
        # paket baru, menyimpannya di level_path, dan MEMBUKA level baru itu.
        if not les.new_level_from_template(level_path, SOURCE_LEVEL):
            raise RuntimeError(f"Gagal membuat {level_path} dari template {SOURCE_LEVEL}.")
        log(f"[Level] {name} dibuat dari template LVL_PacMan.")

    # Pengaman: jangan pernah mengubah level selain level tujuan (terutama level 1)
    current = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current_pkg = current.get_outermost().get_name() if current else ""
    if current_pkg != level_path:
        raise RuntimeError(
            f"Level yang terbuka '{current_pkg}', bukan '{level_path}'. "
            "Script dihentikan supaya level lain tidak ikut berubah.")

    actors = eas.get_all_level_actors()

    # --- ukuran & posisi labirin diambil dari dinding level 1 supaya pas
    old_walls = [a for a in actors if "/_GENERATED/" in mesh_path(a)]
    old_walls += [a for a in actors if MAZE_TAG in [str(t) for t in a.tags]
                  and isinstance(a, unreal.StaticMeshActor) and "Wall" in a.get_actor_label()]
    if old_walls:
        lo_x = min(a.get_actor_bounds(False)[0].x - a.get_actor_bounds(False)[1].x for a in old_walls)
        lo_y = min(a.get_actor_bounds(False)[0].y - a.get_actor_bounds(False)[1].y for a in old_walls)
        hi_x = max(a.get_actor_bounds(False)[0].x + a.get_actor_bounds(False)[1].x for a in old_walls)
        hi_y = max(a.get_actor_bounds(False)[0].y + a.get_actor_bounds(False)[1].y for a in old_walls)
        z_bottom = min(a.get_actor_bounds(False)[0].z - a.get_actor_bounds(False)[1].z for a in old_walls)
        z_top = max(a.get_actor_bounds(False)[0].z + a.get_actor_bounds(False)[1].z for a in old_walls)
    else:
        warn("[Level] Dinding lama tidak ditemukan, memakai ukuran default 4000 x 2000.")
        lo_x, lo_y, hi_x, hi_y, z_bottom, z_top = -2000, -1000, 2000, 1000, 0, 200
    rows, cols = len(grid), len(grid[0])
    cell = min((hi_x - lo_x) / cols, (hi_y - lo_y) / rows)
    wall_h = max(z_top - z_bottom, 100.0)
    log(f"[Level] Area labirin x[{lo_x:.0f},{hi_x:.0f}] y[{lo_y:.0f},{hi_y:.0f}] "
        f"z[{z_bottom:.0f},{z_top:.0f}] -> sel {cell:.0f} unit")

    def center(c, r):
        return lo_x + (c + 0.5) * cell, lo_y + (r + 0.5) * cell

    # --- posisi z pellet diambil dari pellet level 1
    pellets = [a for a in actors if is_instance_of(a, FOOD_BP) or is_instance_of(a, POWER_BP)]
    pellet_z = statistics.median(a.get_actor_location().z for a in pellets) if pellets else z_bottom + 50

    # --- hapus dinding lama + pellet lama
    eas.destroy_actors(old_walls + pellets)
    log(f"[Level] Dihapus: {len(old_walls)} dinding lama, {len(pellets)} pellet lama.")

    # --- material
    wall_mi = make_color_instance(f"MI_Wall_{name}", cfg["wall_color"])
    floor_mi = make_color_instance(f"MI_Floor_{name}", cfg["floor_color"], glow=False)

    # --- lantai: Plane terbesar diberi material gelap polos
    planes = [a for a in eas.get_all_level_actors() if mesh_path(a).startswith("/Engine/BasicShapes/Plane")]
    if planes:
        floor = max(planes, key=lambda a: a.get_actor_bounds(False)[1].x * a.get_actor_bounds(False)[1].y)
        floor.static_mesh_component.set_material(0, floor_mi)
        log(f"[Level] Lantai '{floor.get_actor_label()}' memakai {floor_mi.get_name()}.")
    else:
        warn("[Level] Lantai (Plane) tidak ditemukan; material lantai tidak diganti.")

    # --- dinding baru (sel berurutan per baris digabung jadi 1 aktor)
    cube = EAL.load_asset(CUBE_MESH)
    for (c, r, length) in maze_layouts.wall_runs(grid):
        x0, y = center(c, r)
        x = x0 + (length - 1) * cell / 2
        wall = eas.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(x, y, z_bottom + wall_h / 2))
        smc = wall.static_mesh_component
        smc.set_static_mesh(cube)
        smc.set_material(0, wall_mi)
        wall.set_actor_scale3d(unreal.Vector(length * cell / 100, cell / 100, wall_h / 100))
        tag(wall, "Maze/Walls", f"Wall_r{r}_c{c}")

    # --- pellet & power pellet
    food_cls = EAL.load_asset(FOOD_BP).generated_class()
    power_cls = (EAL.load_asset(POWER_BP).generated_class()
                 if EAL.does_asset_exist(POWER_BP) else food_cls)
    for (c, r) in maze_layouts.cells(grid, "."):
        x, y = center(c, r)
        tag(eas.spawn_actor_from_class(food_cls, unreal.Vector(x, y, pellet_z)),
            "Maze/Pellets", f"Pellet_r{r}_c{c}")
    for (c, r) in maze_layouts.cells(grid, "o"):
        x, y = center(c, r)
        tag(eas.spawn_actor_from_class(power_cls, unreal.Vector(x, y, pellet_z)),
            "Maze/PowerPellets", f"PowerPellet_r{r}_c{c}")

    # --- hantu: pindah ke kandang baru + kecepatan per level
    # BP_Ghost, BP_GhostPink, BP_GhostRed, dst. (semua kelas yang namanya diawali BP_Ghost)
    ghosts = [a for a in eas.get_all_level_actors()
              if a.get_class().get_name().startswith("BP_Ghost")]
    spots = maze_layouts.cells(grid, "G")
    for i, g in enumerate(ghosts):
        c, r = spots[i % len(spots)]
        x, y = center(c, r)
        offset = (i // len(spots)) * 40.0
        g.set_actor_location(unreal.Vector(x + offset, y, g.get_actor_location().z), False, False)
        g.get_editor_property("character_movement").set_editor_property(
            "max_walk_speed", cfg["ghost_speed"])
    log(f"[Level] {len(ghosts)} hantu dipindah ke kandang, Max Walk Speed = {cfg['ghost_speed']}.")

    # --- posisi awal Pac-Man
    (pc, pr), = maze_layouts.cells(grid, "P")
    px, py = center(pc, pr)
    starts = [a for a in eas.get_all_level_actors()
              if isinstance(a, unreal.PlayerStart)
              or a.get_class().get_name().startswith("BP_ThirdPersonCharacter")]
    for s in starts:
        s.set_actor_location(unreal.Vector(px, py, s.get_actor_location().z), False, False)
    if not starts:
        warn("[Level] PlayerStart tidak ditemukan; tambahkan manual di sel 'P'.")

    unreal.SystemLibrary.execute_console_command(current, "RebuildNavigation")
    if not les.save_current_level():
        raise RuntimeError(f"Gagal menyimpan {level_path}. Cek apakah filenya read-only.")
    info = maze_layouts.validate(name, grid)
    log(f"[Level] {name} selesai: {info['pellets']} pellet, {info['power']} power pellet, "
        f"{info['wall_actors']} dinding, {info['dead_ends']} jalan buntu.")


def main():
    for name, cfg in maze_layouts.LEVELS.items():
        info = maze_layouts.validate(name, cfg["grid"])
        if info["errors"]:
            raise RuntimeError(f"Denah {name} tidak valid: {info['errors']}")

    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    for name, cfg in maze_layouts.LEVELS.items():
        build_level(name, cfg, eas, les)
    les.load_level(SOURCE_LEVEL)
    log("[Setup] Level 2 & 3 selesai. Buka LVL_PacMan_02 / _03 lalu tekan P untuk cek NavMesh.")


main()
